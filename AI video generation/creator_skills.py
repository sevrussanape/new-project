"""Local-first YouTube creator skill workflows for OfflineYouTubeStudio.

Language-model tasks use the user's local Ollama server only. Analytics and
transcript utilities are deterministic Python; they do not call external APIs.
"""
from __future__ import annotations

import csv
import json
import os
import re
import statistics
import urllib.error
import urllib.request
from collections import defaultdict
from typing import Any

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:4b")
MAX_SKILL_INPUT = 100_000

SKILLS: list[dict[str, str]] = [
    {"id": "yt-audit", "name": "Channel audit", "group": "Strategy", "mode": "local-ai",
     "description": "Audit titles, thumbnails, openings, consistency and retention; return the single highest-impact fix.",
     "hint": "Paste JSON with channel, recent_videos (title, thumbnail notes, opening transcript, publish date) and analytics/retention if available."},
    {"id": "yt-chapters", "name": "Video chapters", "group": "Production", "mode": "python",
     "description": "Create timestamped chapter drafts from SRT, VTT or Whisper JSON and validate YouTube chapter rules.",
     "hint": "Paste an SRT/VTT transcript or Whisper segments JSON. At least 30 seconds of transcript is needed for three valid chapters."},
    {"id": "yt-comment", "name": "Comment assistant", "group": "Community", "mode": "local-ai",
     "description": "Triage comments into questions, corrections, praise and bait; draft concise replies and suggest one pinned comment.",
     "hint": "Paste comments, one per line, optionally include your channel voice and context."},
    {"id": "yt-edit", "name": "Edit decision list", "group": "Production", "mode": "python",
     "description": "Find long pauses, filler-only cues and likely repeated starts in a timestamped transcript.",
     "hint": "Paste SRT, VTT or Whisper JSON. This creates edit suggestions only; it never modifies your video."},
    {"id": "yt-package", "name": "Title + thumbnail package", "group": "Discovery", "mode": "local-ai",
     "description": "Generate title/thumbnail pairs and lint them for clarity, duplication and truncation.",
     "hint": "Enter topic, audience, promise and optional thumbnail concept or channel voice. JSON or plain text accepted."},
    {"id": "yt-plan", "name": "Content calendar", "group": "Strategy", "mode": "local-ai",
     "description": "Build a realistic weekly or monthly upload plan around available hours and work already in progress.",
     "hint": "Include available hours, posting capacity, videos already half-made, audience and preferred formats."},
    {"id": "yt-retention", "name": "Retention analyzer", "group": "Analytics", "mode": "python",
     "description": "Read a YouTube Studio retention CSV and identify opening loss, steep drops and steady mid-video decline.",
     "hint": "Paste CSV with position and percentage-watching columns. Add duration_seconds if the position column is 0–100 percent."},
    {"id": "yt-script", "name": "Hook + script writer", "group": "Creation", "mode": "local-ai",
     "description": "Create five hook approaches, score them heuristically and draft a beat-by-beat spoken script with on-screen direction.",
     "hint": "Enter idea, target viewer, format, target duration, key facts/sources and channel voice."},
    {"id": "yt-seo", "name": "YouTube SEO pack", "group": "Discovery", "mode": "local-ai",
     "description": "Write a search-aligned description, a focused tag list and three target queries without inventing search volume.",
     "hint": "Enter topic, target viewer, primary keyword, related terms, title and useful links/resources."},
    {"id": "yt-shorts", "name": "Shorts repurposer", "group": "Repurposing", "mode": "local-ai",
     "description": "Find self-contained 20–55 second moments in a long-video transcript and suggest fresh Shorts hooks.",
     "hint": "Paste a timestamped SRT/VTT/Whisper transcript. Include original video aspect ratio if known."},
    {"id": "yt-viral", "name": "Viral outlier research", "group": "Research", "mode": "python",
     "description": "Rank candidate videos by views relative to each channel's own median, not by raw views alone.",
     "hint": "Paste JSON: [{\"channel\":\"Channel\",\"title\":\"Video title\",\"views\":12345,\"url\":\"https://...\",\"duration\":45}]. Aim for four or more videos per channel."},
]

SKILL_BY_ID = {item["id"]: item for item in SKILLS}

SYSTEM_PROMPT = (
    "You are the local YouTube Creator Studio assistant. Be specific, practical and honest. "
    "Never promise virality or claim an outcome is guaranteed. Never invent views, CTR, retention, "
    "search volume, sources, audience demographics or channel analytics. Clearly label hypotheses. "
    "Use only the information supplied by the user. When evidence is missing, state what is missing. "
    "Respect the creator's supplied voice and never publish, upload, reply or change an account."
)

FILLER_ONLY = re.compile(
    r"^[\s,.-]*((um+|uh+|er+|ah+|so|okay|ok|right|yeah|like|anyway|basically|"
    r"actually|you know|i mean|let me see|hold on)[\s,.-]*)+$", re.I
)
TIMESTAMP_LINE = re.compile(
    r"^\s*((?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*"
    r"((?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{1,3})"
)


def list_skills() -> dict[str, Any]:
    return {"skills": SKILLS, "model": DEFAULT_MODEL, "recommended_model": "qwen3.5:4b",
            "recommended_model_note": "Best quality starting point in this app: qwen3.5:4b (about 3.4 GB in Ollama). On a 4 GB GPU it may offload layers to system RAM; use qwen3.5:2b for a lighter/faster fallback. Close GPU-heavy apps and test response speed."}


def _ollama_generate(prompt: str, *, model: str | None = None, timeout: int = 300, json_mode: bool = False) -> str:
    if len(prompt) > 12_000:
        raise ValueError("This local model is configured for a 4,096-token context. Split long transcripts/comments into smaller parts and run the skill again.")
    selected = (model or DEFAULT_MODEL).strip()
    if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,120}", selected):
        raise ValueError("Invalid local Ollama model name.")
    body = {
        "model": selected,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.65, "num_ctx": 4096},
    }
    if json_mode:
        body["format"] = "json"
    request = urllib.request.Request(
        OLLAMA_URL + "/api/chat",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code == 404:
            raise RuntimeError(f"Ollama could not find model '{selected}'. Run: ollama pull {selected}") from exc
        raise RuntimeError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Local Ollama is not reachable. Start Ollama, download a local model, "
            "and set OLLAMA_MODEL if needed. Suggested model for this hardware: qwen3.5:4b."
        ) from exc
    except (TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Ollama timed out or returned invalid JSON. Try a smaller local model.") from exc
    text = ((result.get("message") or {}).get("content") or "").strip()
    if not text:
        raise RuntimeError("The local language model returned an empty response.")
    return text


def _parse_timestamp(value: str) -> float:
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp: {value}") from exc
    raise ValueError(f"Invalid timestamp: {value}")


def parse_transcript(source: str) -> list[tuple[float, float, str]]:
    """Parse SRT, VTT or Whisper-style JSON into (start, end, text) cues."""
    raw = source.strip()
    if not raw:
        raise ValueError("Paste a timestamped SRT, VTT or Whisper JSON transcript.")
    if raw.startswith("{") or raw.startswith("["):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Transcript JSON is invalid.") from exc
        segments = payload.get("segments", []) if isinstance(payload, dict) else payload
        if not isinstance(segments, list):
            raise ValueError("Whisper JSON must contain a segments array.")
        cues = []
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            try:
                start, end = float(seg["start"]), float(seg["end"])
            except (KeyError, TypeError, ValueError):
                continue
            text = str(seg.get("text") or "").strip()
            if text and end > start >= 0:
                cues.append((start, end, text))
        return sorted(cues)
    cues: list[tuple[float, float, str]] = []
    current: list[Any] | None = None
    for line in raw.splitlines():
        match = TIMESTAMP_LINE.match(line)
        if match:
            if current and current[2]:
                cues.append((current[0], current[1], " ".join(current[2])))
            current = [_parse_timestamp(match.group(1)), _parse_timestamp(match.group(2)), []]
        elif current is not None and line.strip() and not line.strip().isdigit() and not line.startswith("WEBVTT"):
            current[2].append(re.sub(r"<[^>]+>", "", line.strip()))
    if current and current[2]:
        cues.append((current[0], current[1], " ".join(current[2])))
    cues = [c for c in cues if c[1] > c[0] and c[2]]
    return sorted(cues)


STOP_WORDS = set(
    "the a an of for to in on and or is are was were be been with this that it as at by from "
    "you your i my we our they them he she but so if then than there here what which who how "
    "when where why not no yes do does did just really very like about into over out up down "
    "can could will would should have has had get got make made go going went one two".split()
)


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']{4,}", text.lower()) if w not in STOP_WORDS}


def _format_time(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def run_chapters(source: str, target: int = 7) -> dict[str, Any]:
    cues = parse_transcript(source)
    if len(cues) < 6:
        raise ValueError("At least six timestamped cues are needed to draft chapters.")
    target = max(3, min(12, int(target)))
    duration = cues[-1][1]
    if duration < 30:
        raise ValueError("The video must be at least 30 seconds long to create three valid 10-second chapters.")
    candidates = []
    for index in range(1, len(cues)):
        gap = max(0, cues[index][0] - cues[index - 1][1])
        before = " ".join(c[2] for c in cues[max(0, index - 12):index])
        after = " ".join(c[2] for c in cues[index:index + 12])
        kb, ka = _keywords(before), _keywords(after)
        union = kb | ka
        shift = 1 - (len(kb & ka) / len(union)) if union else 0
        candidates.append((gap * 1.6 + shift * 3.2, cues[index][0]))
    boundaries = [0.0]
    for _, timestamp in sorted(candidates, reverse=True):
        if len(boundaries) >= target:
            break
        if timestamp >= 10 and duration - timestamp >= 10 and all(abs(timestamp - picked) >= 10 for picked in boundaries):
            boundaries.append(timestamp)
    boundaries.sort()
    chapters = []
    for index, start in enumerate(boundaries):
        end = boundaries[index + 1] if index + 1 < len(boundaries) else duration
        section = " ".join(text for cue_start, cue_end, text in cues if cue_start < end and cue_end > start)
        words = sorted(_keywords(section), key=lambda word: (-section.lower().count(word), word))
        title = " ".join(word.capitalize() for word in words[:3]) or "Section"
        chapters.append({"start_seconds": round(start, 2), "timestamp": _format_time(start),
                         "draft_title": title, "duration_seconds": round(end - start, 2)})
    valid = len(chapters) >= 3 and chapters[0]["timestamp"] == "00:00" and all(c["duration_seconds"] >= 10 for c in chapters)
    return {"valid": valid, "duration_seconds": round(duration, 2), "chapters": chapters,
            "note": "Chapter names are keyword drafts: rewrite them as viewer-facing promises. Validity checks the 00:00 start, 3+ chapters and 10-second minimum."}


def _normal_words(text: str) -> list[str]:
    return re.sub(r"[^a-z ]", "", text.lower()).split()


def _merge_intervals(intervals: list[tuple[float, float]]) -> float:
    if not intervals:
        return 0.0
    intervals.sort()
    start, end = intervals[0]
    total = 0.0
    for next_start, next_end in intervals[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            total += end - start
            start, end = next_start, next_end
    return total + end - start


def run_edit(source: str, floor: float = 0.45) -> dict[str, Any]:
    if not 0.05 <= float(floor) <= 5:
        raise ValueError("Dead-air floor must be between 0.05 and 5 seconds.")
    cues = parse_transcript(source)
    if not cues:
        raise ValueError("No timestamped transcript cues were found.")
    cuts: list[dict[str, Any]] = []
    for index, (start, end, text) in enumerate(cues):
        if FILLER_ONLY.match(text):
            cuts.append({"kind": "FILLER", "start": start, "end": end, "reason": text[:48]})
        if index:
            previous_end = cues[index - 1][1]
            gap = start - previous_end
            if gap > floor:
                keep = floor / 2
                cuts.append({"kind": "DEAD", "start": round(previous_end + keep, 3),
                             "end": round(start - keep, 3), "reason": f"{gap:.2f}s gap"})
        if text.strip() and not FILLER_ONLY.match(text):
            previous = index - 1
            while previous >= 0 and (FILLER_ONLY.match(cues[previous][2]) or not cues[previous][2].strip()):
                previous -= 1
            if previous >= 0:
                first = _normal_words(cues[previous][2])[:5]
                second = _normal_words(text)[:5]
                if len(first) >= 3 and first == second:
                    cuts.append({"kind": "REPEAT", "start": cues[previous][0], "end": cues[previous][1],
                                 "reason": "Likely repeated opening: " + " ".join(first)})
    cuts = [c for c in cuts if c["end"] > c["start"]]
    cuts.sort(key=lambda item: item["start"])
    removed = _merge_intervals([(c["start"], c["end"]) for c in cuts])
    duration = cues[-1][1]
    return {"duration_seconds": round(duration, 2), "cue_count": len(cues), "cuts": cuts,
            "removed_seconds_estimate": round(removed, 2),
            "estimated_new_duration_seconds": round(max(0, duration - removed), 2),
            "warning": "Edit decision list only. Check every cut against the actual video; do not cut silent demos or intentional pauses blindly."}


def run_retention(source: str, duration_seconds: float | None = None) -> dict[str, Any]:
    rows = []
    for row in csv.reader(source.splitlines()):
        numbers = []
        for index, cell in enumerate(row):
            cleaned = cell.strip().replace("%", "").replace(",", "")
            try:
                numbers.append(_parse_timestamp(cleaned) if index == 0 and ":" in cleaned else float(cleaned))
            except ValueError:
                pass
        if len(numbers) >= 2:
            rows.append((numbers[0], numbers[1]))
    if len(rows) < 8:
        raise ValueError("Could not read at least eight data points from the pasted retention CSV.")
    rows.sort(key=lambda item: item[0])
    xs, ys = [r[0] for r in rows], [r[1] for r in rows]
    percent_axis = max(xs) <= 100.5
    duration = float(duration_seconds) if duration_seconds else None
    if duration is not None and duration <= 0:
        raise ValueError("Video duration must be positive.")
    cutoff = (30 / duration * 100) if percent_axis and duration else (10 if percent_axis else 30)
    start_value = ys[0] if ys[0] > 0 else 100.0
    hook_end = next((y for x, y in reversed(rows) if x <= cutoff), start_value)
    hook_loss = max(0.0, start_value - hook_end)
    changes = []
    for i in range(1, len(rows)):
        drop = ys[i - 1] - ys[i]
        span = max(0.0001, xs[i] - xs[i - 1])
        changes.append((drop / span, xs[i - 1], xs[i], drop))
    cliffs = []
    for rate, x0, x1, drop in sorted(changes, reverse=True):
        if drop <= 0.8 or len(cliffs) >= 5:
            continue
        time_value = ((x0 / 100) * duration) if percent_axis and duration else (x0 if not percent_axis else None)
        cliffs.append({"from": round(x0, 2), "to": round(x1, 2), "percentage_points_lost": round(drop, 2),
                       "loss_per_axis_unit": round(rate, 3),
                       "at_seconds": round(time_value, 1) if time_value is not None else None})
    middle = [max(0.0, change) for change, x0, _, _ in changes if x0 > cutoff]
    slide = statistics.mean(middle) if middle else 0.0
    if hook_loss < 25:
        verdict = "healthy"
    elif hook_loss < 40:
        verdict = "leaking"
    else:
        verdict = "severe"
    return {"data_points": len(rows), "start_retention": round(start_value, 2),
            "end_retention": round(ys[-1], 2), "hook_loss_first_30s_or_10pct": round(hook_loss, 2),
            "hook_verdict": verdict, "cliffs": cliffs, "average_mid_video_drop_per_step": round(slide, 3),
            "note": "This is descriptive analysis of the supplied export, not a causal explanation. Add a timestamped transcript to map drops to spoken content."}


HOOK_FORMULAS = [
    ("The Statistic", [r"\b\d+(\.\d+)?\s?%", r"\b\d+ (out of|in) \d+\b", r"\b\d{2,}(,\d{3})+\b"]),
    ("Someone Else's Result", [r"\bthis (channel|guy|creator|account)\b", r"\bwent from .* to\b", r"\bin (a|one|two|three|\d+) (week|month|year)s?\b"]),
    ("The Mistake", [r"\byou('re| are) (probably |still )?(doing|making)\b", r"\bthe (mistake|reason) (everyone|most people|nobody)\b", r"\bstop (doing )?\b"]),
    ("Contrarian Flip", [r"\beveryone (says|thinks|tells you)\b", r"\bis (actually )?wrong\b", r"\bnobody (tells|talks about)\b"]),
    ("The Reveal", [r"\bI('m| am) going to show you\b", r"\bhere('s| is) (the|exactly)\b", r"\bon screen\b"]),
    ("The Superlative", [r"\bthe (best|worst|fastest|easiest|only)\b", r"\bnumber one\b"]),
    ("The Clock", [r"\bin (the next )?\d+ (seconds|minutes|hours)\b", r"\bby the end of this video\b", r"\bunder \d+\b"]),
    ("I Tried It", [r"\bI (tried|spent|tested|let|gave)\b", r"\bfor \d+ (days|weeks|months)\b", r"\bso you don'?t have to\b"]),
    ("The Question", [r"^(why|how|what|when|should|can|do|does|is)\b", r"\?\s*$"]),
    ("Before and After", [r"\bbefore\b.*\bafter\b", r"\bthis was\b.*\bthis is\b", r"\bused to\b"]),
    ("The Teardown", [r"\b(broke|break|breaking) (it )?down\b", r"\bteardown\b", r"\banalys(ed|ed|is|e)\b", r"\bI pulled\b"]),
    ("The Stack", [r"\b\w+ (plus|\+) \w+\b", r"\bcombine\b", r"\btogether\b"]),
    ("The Warning", [r"\bdo not\b", r"\bdon'?t (upload|post|publish|start)\b", r"\bbefore you\b", r"\bstop\b"]),
    ("The List", [r"^\d+ \w+", r"\b(here are|these are) \d+\b"]),
    ("The Receipt", [r"\bthis is (the|my)\b", r"\bscreenshot\b", r"\bproof\b", r"\breceipts?\b"]),
    ("The Insider", [r"\b(nobody|almost nobody|most people) (knows?|opens?|uses?)\b", r"\bhidden\b", r"\bburied\b"]),
    ("The Impossible Claim", [r"\bwithout\b", r"\bnever\b", r"\bin one\b", r"\bzero\b"]),
    ("The Comparison", [r"\bvs\.?\b", r"\bversus\b", r"\bwhich (one )?(is|wins)\b", r"\bsame .* (three|two) ways\b"]),
    ("The Origin", [r"\bevery (video|post) .* starts\b", r"\bit all (starts|started)\b", r"\bthe (real )?reason\b"]),
    ("The Deadline", [r"\b(this|next) (week|month|year)\b", r"\bis changing\b", r"\bno longer\b", r"\bas of\b"]),
    ("The Direct Address", [r"^if you\b", r"\bfor (anyone|everyone|people) who\b", r"\byou specifically\b"]),
]

def _hook_formula(title: str) -> tuple[str, int]:
    best_name, best_hits = "Unclassified", 0
    for name, patterns in HOOK_FORMULAS:
        hits = sum(1 for pattern in patterns if re.search(pattern, title, re.I))
        if hits > best_hits:
            best_name, best_hits = name, hits
    return best_name, best_hits

HOOK_FILLER = {"basically", "actually", "literally", "just", "really", "very", "so", "kind", "sort", "like",
               "guys", "hey", "welcome", "today", "video", "subscribe", "channel"}
HOOK_VAGUE = {"amazing", "incredible", "insane", "crazy", "huge", "massive", "game", "changer", "secret",
              "powerful", "ultimate", "best", "revolutionary", "mind", "blowing", "unbelievable"}
HOOK_CONCRETE = re.compile(r"\b(\d[\d,.]*\s?(%|k|m|x|s|m|h)?|\$\d|\d+\s?(second|minute|hour|day|week|month|year)s?)\b", re.I)
HOOK_YOU = re.compile(r"\b(you|your|you're|youre|yourself)\b", re.I)
HOOK_STAKE = re.compile(r"\b(lose|lost|wasting|waste|quit|fail|broke|cost|risk|before|stop|never|die|dying|dead)\b", re.I)
HOOK_CURIOSITY = re.compile(r"\b(why|how|what|which|until|before|but|nobody|almost|except|reason|actually)\b", re.I)


def _score_hook(hook: str) -> dict[str, Any]:
    """Score specificity, address, stakes, curiosity and brevity as editorial diagnostics."""
    words = re.findall(r"[a-z0-9'%$.]+", hook.lower())
    if not words:
        return {"hook": hook, "score": 0, "band": "WEAK", "properties": {}, "formula": "Unclassified",
                "weakest_property": "specificity", "suggested_fix": "Write a complete spoken opening."}
    concrete_count = len(HOOK_CONCRETE.findall(hook))
    vague_count = sum(1 for word in words if word in HOOK_VAGUE)
    filler_count = sum(1 for word in words if word in HOOK_FILLER)
    uppercase_names = sum(1 for word in hook.split()[1:] if word[:1].isupper())
    specificity = max(0, min(100, 34 + concrete_count * 22 - vague_count * 16 - filler_count * 5 + min(18, 6 * uppercase_names)))
    you_count = len(HOOK_YOU.findall(hook))
    address = max(0, min(100, 26 + you_count * 20 + (30 if HOOK_YOU.search(" ".join(hook.split()[:6])) else 0)))
    stake_count = len(HOOK_STAKE.findall(hook))
    stakes = max(0, min(100, 22 + stake_count * 26 + (14 if HOOK_CONCRETE.search(hook) else 0)))
    curiosity_count = len(HOOK_CURIOSITY.findall(hook))
    curiosity = max(0, min(100, 24 + curiosity_count * 17 + (18 if hook.strip().endswith("?") else 0)
                           - (18 if re.search(r"\b(because|so that|which means)\b", hook, re.I) else 0)))
    count = len(words)
    if 9 <= count <= 24:
        brevity = 100
    elif count < 9:
        brevity = max(30, 100 - (9 - count) * 11)
    else:
        brevity = max(10, 100 - (count - 24) * 7)
    properties = {"specificity": specificity, "direct_address": address, "stakes": stakes,
                  "curiosity": curiosity, "brevity": brevity}
    score = round(0.6 * (sum(properties.values()) / len(properties)) + 0.4 * min(properties.values()))
    formula, hits = _hook_formula(hook)
    weakest = min(properties, key=properties.get)
    fixes = {
        "specificity": "replace an adjective with a verifiable number, name or date",
        "direct_address": "address the intended viewer in the first six words",
        "stakes": "make the real consequence clear",
        "curiosity": "leave an honest unanswered question",
        "brevity": "tighten toward 9–24 spoken words",
    }
    return {"hook": hook.strip(), "score": score,
            "band": "STRONG" if score >= 72 else "WORKABLE" if score >= 55 else "WEAK",
            "properties": properties, "formula": formula, "formula_matches": hits,
            "weakest_property": weakest, "suggested_fix": fixes[weakest]}


def _title_formula(title: str) -> str:
    return _hook_formula(title)[0]


def run_viral(source: str, minimum_multiple: float = 1.5) -> dict[str, Any]:
    if not 1.0 <= float(minimum_multiple) <= 1000:
        raise ValueError("Minimum view multiple must be between 1 and 1000.")
    try:
        payload = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ValueError("Viral research input must be valid JSON.") from exc
    videos = payload.get("videos", []) if isinstance(payload, dict) else payload
    if not isinstance(videos, list):
        raise ValueError("Provide a JSON array of video records or an object with a videos array.")
    by_channel: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in videos:
        if not isinstance(item, dict):
            continue
        channel = str(item.get("channel") or "").strip()
        title = str(item.get("title") or "").strip()
        try:
            views = max(0, int(item.get("views") or 0))
        except (TypeError, ValueError):
            continue
        if channel and title:
            by_channel[channel].append({**item, "views": views})
    outliers, skipped = [], []
    for channel, items in by_channel.items():
        if len(items) < 4:
            skipped.append({"channel": channel, "videos_collected": len(items), "reason": "Need at least four videos for a stable channel baseline."})
            continue
        median_views = statistics.median([v["views"] for v in items])
        if median_views <= 0:
            skipped.append({"channel": channel, "videos_collected": len(items), "reason": "Channel median views must be greater than zero."})
            continue
        for item in items:
            multiple = item["views"] / median_views
            if multiple >= float(minimum_multiple):
                outliers.append({"channel": channel, "title": item["title"], "views": item["views"],
                                 "channel_median_views": round(median_views), "multiple_of_median": round(multiple, 2),
                                 "title_pattern_guess": _title_formula(item["title"]), "url": str(item.get("url") or "")})
    outliers.sort(key=lambda item: item["multiple_of_median"], reverse=True)
    return {"outliers": outliers[:25], "skipped_channels": skipped,
            "total_channels": len(by_channel), "total_videos": sum(map(len, by_channel.values())),
            "minimum_multiple": float(minimum_multiple),
            "warning": "A title-pattern label is not proof of why a video performed well. Relative views are not causal evidence; compare topic, timing, audience and thumbnail too."}


def _lint_title(title: str, thumbnail: str = "") -> dict[str, Any]:
    words = re.findall(r"[a-z0-9']+", title.lower())
    issues, positives = [], []
    if len(title) > 100:
        issues.append("Exceeds YouTube's 100-character title limit.")
    if len(title) > 60:
        issues.append("May truncate in desktop search; consider shortening below 60 characters.")
    if len(title) > 40:
        issues.append("May truncate in some mobile surfaces; ensure the subject appears early.")
    vague = {"amazing", "incredible", "insane", "crazy", "ultimate", "best", "secret", "epic", "perfect"}
    if set(words) & vague:
        issues.append("Contains vague hype words; replace them with a concrete promise.")
    if thumbnail:
        overlap = set(words) & set(re.findall(r"[a-z0-9']+", thumbnail.lower()))
        if overlap:
            issues.append("Thumbnail repeats title words: " + ", ".join(sorted(overlap)))
        if len(thumbnail.split()) > 3:
            issues.append("Thumbnail text should be tested at feed size; aim for three words or fewer.")
    if len(title) <= 60:
        positives.append("Within the approximate desktop search display target.")
    return {"title": title, "characters": len(title), "issues": issues, "positives": positives}


AI_PROMPTS: dict[str, str] = {
    "yt-audit": """Audit the supplied YouTube channel evidence. Review the last titles as a set, thumbnail readability notes, first 15 seconds of the most recent openings, upload consistency and retention if supplied. Do not invent metrics or claim to have opened the channel URL. Return: (1) one biggest fix and a 7-day action, (2) three evidence-backed things already working, (3) what not to change yet, (4) missing evidence. Be direct and specific; do not dump twenty generic suggestions.""",
    "yt-comment": """Triage each supplied comment into Questions, Corrections, Praise or Bait, and count each category. Draft replies only for useful questions, valid corrections and a few specific praise comments. Keep each reply under 30 words, answer the actual question first, do not argue unverified facts, and do not reply to bait. Suggest exactly one comment to pin and explain why. Never publish replies.""",
    "yt-package": """Create exactly ten distinct YouTube title + thumbnail packages for the supplied idea and audience. Return ONLY valid JSON in this shape: {"packages":[{"title":"...","thumbnail_text":"up to 3 short words","thumbnail_visual_brief":"...","rationale":"..."}]}. Make every title specific and truthful; avoid fake urgency, unsupported numbers and vague hype. The thumbnail must add a different piece of information rather than repeat the title. Do not invent facts or CTR predictions. The application will independently lint each title/thumbnail pair for the 100-character hard title limit, approximate 60-character desktop and 40-character mobile display targets, vague hype, repeated words and thumbnail word count.""",
    "yt-plan": """Build a realistic weekly or monthly YouTube content plan based on the creator's actual available hours and work already in progress. Prefer one anchor video, one lower-effort upload and up to three Shorts repurposed from the anchor when capacity allows. Return a table with day, format, working title, viewer promise, existing assets, and estimated work hours. Total the hours and state what to drop first if the week becomes busy. Do not invent the best upload day; use analytics only if supplied.""",
    "yt-script": """Write a YouTube script that earns the click and sustains attention. Use the 21 hook approaches below as a formula library; choose five that suit this specific idea and do not force a weak fit. Return ONLY valid JSON with this shape: {"hooks":[{"formula":"formula name","text":"exact spoken opening","proof":"what must be shown or cited in the next 15 seconds"}],"beats":[{"time":"0:00-0:15","voiceover":"spoken narration","on_screen":"visual direction"}],"payoff":"the promised viewer payoff","closing_ask":"one closing ask","formula_rationale":"why the best formula fits"}. Include exactly five distinct hooks and at least three script beats. The first 15 seconds must confirm the title promise, open a question the viewer cannot close and prove the payoff exists. No fabricated statistics, named results, dates or sources. Formula library: The Statistic (verifiable number then consequence); Someone Else’s Result (named outcome then mechanism); The Mistake (a common checkable error); Contrarian Flip (accepted advice challenged with evidence); The Reveal (show a specific artifact early); The Superlative (best/worst/fastest with comparison); The Clock (bounded truthful payoff); I Tried It (first-person experiment with real stakes); The Question (viewer’s real search/comment question); Before and After (visual contrast); The Teardown (break down a real example with scope); The Stack (combine named tools for one outcome); The Warning (real cost the viewer risks); The List (exact counted set); The Receipt (show real evidence first); The Insider (truthful system insight, no fake access); The Impossible Claim (surprising claim proven immediately); The Comparison (two named options and a clear winner); The Origin (show where a real process/result began); The Deadline (real dated change); The Direct Address (name a narrow viewer). Apply each formula’s failure condition as a guardrail: evidence for numbers/results, show the artifact when promised, keep the time promise, use a real question, do not claim insider access, and never exaggerate deadlines.""",
    "yt-seo": """Create a useful YouTube SEO pack for the real viewer query. Write a two-line opening description that says exactly what the viewer gets using the supplied target phrase naturally. Add resource links only when supplied, then a useful longer description, chapters only if supplied, and up to 15 relevant tags for disambiguation. End with three target search queries and check whether the title and first two description lines contain their main terms. Do not invent search-volume numbers or promise rankings; explain that tags are a weaker discovery signal than viewer satisfaction and packaging.""",
    "yt-shorts": """Find up to five self-contained Shorts inside the supplied timestamped transcript. Each candidate must be about 20–55 seconds, start with enough context to stand alone, contain a clear turn/payoff and end on a complete line. For each provide start/end timecodes, exact opening words, why it works alone, a NEW hook, different first-two-second on-screen text, a suggested loop point and a vertical crop note. Do not invent transcript quotes or timestamps. If timestamps are not present or too few suitable spans exist, say so rather than guessing.""",
}


def _parse_model_json(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise RuntimeError("Local model did not return the requested JSON structure. Try again with a smaller prompt or model.")
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Local model returned malformed JSON. Try again.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Local model returned JSON, but it was not an object.")
    return payload


def _transcript_input(parsed: Any, original: str) -> str:
    if isinstance(parsed, dict):
        transcript = parsed.get("transcript")
        if isinstance(transcript, str) and transcript.strip():
            return transcript
    return original


def _parse_user_input(source: str) -> Any:
    raw = source.strip()
    if not raw:
        raise ValueError("Enter the information for this skill first.")
    if len(raw) > MAX_SKILL_INPUT:
        raise ValueError(f"Input is too large. Keep it under {MAX_SKILL_INPUT:,} characters.")
    if raw.startswith("{") or raw.startswith("["):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return raw


def run_skill(skill: str, source: str, *, model: str | None = None) -> dict[str, Any]:
    if skill not in SKILL_BY_ID:
        raise ValueError("Unknown creator skill.")
    if model is not None and not isinstance(model, str):
        raise ValueError("Model name must be text.")
    if not isinstance(source, str):
        raise ValueError("Skill input must be text.")
    parsed = _parse_user_input(source)
    if skill == "yt-audit" and isinstance(parsed, str) and re.fullmatch(r"https?://\S+", parsed.strip()):
        raise ValueError("This offline audit does not scrape channel URLs. Paste recent video titles, thumbnail notes, opening transcripts and available analytics.")
    if skill == "yt-chapters":
        target = parsed.get("target", 7) if isinstance(parsed, dict) else 7
        transcript = _transcript_input(parsed, source)
        result = run_chapters(transcript, target)
        lines = [f"Valid YouTube chapters: {'YES' if result['valid'] else 'NO'}", ""]
        lines += [f"{c['timestamp']} {c['draft_title']}  ({c['duration_seconds']:.1f}s)" for c in result["chapters"]]
        lines += ["", result["note"]]
        return {"skill": skill, "title": SKILL_BY_ID[skill]["name"], "engine": "python", "result": "\n".join(lines), "data": result}
    if skill == "yt-edit":
        floor = parsed.get("floor", 0.45) if isinstance(parsed, dict) else 0.45
        transcript = _transcript_input(parsed, source)
        result = run_edit(transcript, float(floor))
        lines = [f"Transcript length: {result['duration_seconds']:.1f}s · {result['cue_count']} cues",
                 f"Suggested cuts: {len(result['cuts'])} · estimated removal: {result['removed_seconds_estimate']:.1f}s",
                 f"Estimated new duration: {result['estimated_new_duration_seconds']:.1f}s", ""]
        lines += [f"{c['kind']:<7} {c['start']:.2f}s → {c['end']:.2f}s  {c['reason']}" for c in result["cuts"]]
        lines += ["", result["warning"]]
        return {"skill": skill, "title": SKILL_BY_ID[skill]["name"], "engine": "python", "result": "\n".join(lines), "data": result}
    if skill == "yt-retention":
        duration = parsed.get("duration_seconds") if isinstance(parsed, dict) else None
        csv_text = parsed.get("csv", "") if isinstance(parsed, dict) else source
        result = run_retention(csv_text, duration)
        lines = [f"Opening loss: {result['hook_loss_first_30s_or_10pct']:.1f} percentage points ({result['hook_verdict']})",
                 f"Retention: {result['start_retention']:.1f}% → {result['end_retention']:.1f}%",
                 f"Average mid-video drop per step: {result['average_mid_video_drop_per_step']:.3f}", "", "Largest drops:"]
        lines += [f"{c['percentage_points_lost']:.1f} points from {c['from']} to {c['to']}" +
                  (f" (about {c['at_seconds']:.0f}s)" if c["at_seconds"] is not None else "") for c in result["cliffs"]]
        lines += ["", result["note"]]
        return {"skill": skill, "title": SKILL_BY_ID[skill]["name"], "engine": "python", "result": "\n".join(lines), "data": result}
    if skill == "yt-viral":
        minimum = parsed.get("minimum_multiple", 1.5) if isinstance(parsed, dict) else 1.5
        data = parsed.get("videos", []) if isinstance(parsed, dict) else parsed
        result = run_viral(json.dumps(data), float(minimum))
        lines = [f"Ranked outliers: {len(result['outliers'])} · channels: {result['total_channels']} · videos: {result['total_videos']}", ""]
        lines += [f"{item['multiple_of_median']:.2f}× channel median | {item['views']:,} views | {item['channel']} — {item['title']}\n  Pattern guess: {item['title_pattern_guess']}" for item in result["outliers"]]
        if result["skipped_channels"]:
            lines += ["", "Skipped channels: " + "; ".join(f"{x['channel']} ({x['videos_collected']} videos)" for x in result["skipped_channels"])]
        lines += ["", result["warning"]]
        return {"skill": skill, "title": SKILL_BY_ID[skill]["name"], "engine": "python", "result": "\n".join(lines), "data": result}
    if skill == "yt-script":
        prompt = AI_PROMPTS[skill] + "\n\nCreator brief:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
        output = _ollama_generate(prompt, model=model, json_mode=True)
        package = _parse_model_json(output)
        hooks = package.get("hooks")
        if not isinstance(hooks, list) or len(hooks) != 5:
            raise RuntimeError("The local model must return exactly five hook candidates in JSON. Try again or use a stronger local model.")
        scored = []
        for candidate in hooks:
            if not isinstance(candidate, dict) or not str(candidate.get("text", "")).strip():
                continue
            report = _score_hook(str(candidate["text"]))
            report["proof"] = str(candidate.get("proof", "")).strip()
            scored.append(report)
        if len(scored) != 5:
            raise RuntimeError("The local model returned incomplete hook candidates. Try again.")
        scored.sort(key=lambda item: item["score"], reverse=True)
        lines = ["HOOK SCORECARD — deterministic editorial diagnostic, not a performance prediction", ""]
        for index, item in enumerate(scored, 1):
            lines.append(f"{index}. [{item['score']}/100 · {item['band']}] {item['hook']}")
            lines.append(f"   Formula: {item['formula']} ({item['formula_matches']} pattern matches)")
            lines.append("   Properties: " + ", ".join(f"{key} {value}/100" for key, value in item["properties"].items()))
            lines.append(f"   Improve: {item['suggested_fix']}")
            if item["proof"]:
                lines.append(f"   Proof needed: {item['proof']}")
            lines.append("")
        lines.append("TWO STRONGEST HOOKS")
        lines.append(f"1. {scored[0]['hook']}")
        lines.append(f"2. {scored[1]['hook']}")
        lines.append("")
        beats = package.get("beats")
        if not isinstance(beats, list) or len(beats) < 3:
            raise RuntimeError("The local model must return at least three script beats with voiceover and on-screen directions.")
        lines.append("SCRIPT — beat by beat")
        spoken_parts = []
        for index, beat in enumerate(beats, 1):
            if not isinstance(beat, dict):
                continue
            voiceover = str(beat.get("voiceover", "")).strip()
            on_screen = str(beat.get("on_screen", "")).strip()
            time_range = str(beat.get("time", "")).strip()
            if voiceover:
                spoken_parts.append(voiceover)
            lines.append(f"{index}. {time_range} {voiceover}")
            lines.append(f"   [ON SCREEN: {on_screen or 'Add a visual that supports the spoken point.'}]")
        script_text = " ".join(spoken_parts)
        runtime_seconds = round(len(re.findall(r"\b[\w'-]+\b", script_text)) / 150 * 60)
        lines.extend(["", f"Estimated spoken runtime: {runtime_seconds // 60}:{runtime_seconds % 60:02d} at 150 words/minute."])
        if package.get("payoff"):
            lines.append("PAYOFF: " + str(package["payoff"]))
        if package.get("closing_ask"):
            lines.append("CLOSE: " + str(package["closing_ask"]))
        if package.get("formula_rationale"):
            lines.append("FORMULA FIT: " + str(package["formula_rationale"]))
        lines.append("")
        lines.append("Review every factual claim and the proof required before recording.")
        return {"skill": skill, "title": SKILL_BY_ID[skill]["name"], "engine": "ollama+python",
                "model": model or DEFAULT_MODEL, "result": "\n".join(lines),
                "data": {"hooks": scored, "beats": beats, "estimated_runtime_seconds": runtime_seconds,
                         "payoff": package.get("payoff"), "closing_ask": package.get("closing_ask")}}
    elif skill == "yt-audit":
        prompt = AI_PROMPTS[skill] + "\n\nChannel evidence supplied by creator:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
    elif skill == "yt-package":
        prompt = AI_PROMPTS[skill] + "\n\nVideo brief:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
        output = _ollama_generate(prompt, model=model, json_mode=True)
        package = _parse_model_json(output)
        candidates = package.get("packages")
        if not isinstance(candidates, list) or len(candidates) != 10:
            raise RuntimeError("The local model must return exactly ten title/thumbnail packages in JSON. Try again.")
        checked = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            title = str(candidate.get("title", "")).strip()
            thumbnail = str(candidate.get("thumbnail_text", "")).strip()
            if not title:
                continue
            lint = _lint_title(title, thumbnail)
            lint["score"] = max(0, min(100, 100 - 14 * len(lint["issues"]) + 4 * len(lint["positives"])))
            lint["thumbnail_text"] = thumbnail
            lint["thumbnail_visual_brief"] = str(candidate.get("thumbnail_visual_brief", "")).strip()
            lint["rationale"] = str(candidate.get("rationale", "")).strip()
            checked.append(lint)
        if len(checked) < 3:
            raise RuntimeError("The local model returned too few usable title/thumbnail packages. Try again.")
        checked.sort(key=lambda item: item["score"], reverse=True)
        lines = ["TITLE + THUMBNAIL PACKAGES — rule-based editorial lint, not a CTR prediction", ""]
        for rank, item in enumerate(checked, 1):
            lines.append(f"{rank}. [{item['score']}/100] {item['title']}")
            lines.append(f"   Thumbnail: {item['thumbnail_text']}")
            if item["thumbnail_visual_brief"]:
                lines.append(f"   Visual brief: {item['thumbnail_visual_brief']}")
            if item["rationale"]:
                lines.append(f"   Rationale: {item['rationale']}")
            lines.append("   Checks: " + ("; ".join(item["issues"]) if item["issues"] else "No lint issues found."))
            lines.append("")
        lines.append("Top three are ranked by a simple lint score. Choose based on audience promise and truthful proof, then test with real audience data.")
        return {"skill": skill, "title": SKILL_BY_ID[skill]["name"], "engine": "ollama+python",
                "model": model or DEFAULT_MODEL, "result": "\n".join(lines), "data": {"packages": checked}}
    elif skill == "yt-comment":
        prompt = AI_PROMPTS[skill] + "\n\nComments and optional creator voice:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
    elif skill == "yt-plan":
        prompt = AI_PROMPTS[skill] + "\n\nCreator capacity and content inventory:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
    elif skill == "yt-seo":
        prompt = AI_PROMPTS[skill] + "\n\nVideo metadata and audience:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
    elif skill == "yt-shorts":
        cues = parse_transcript(_transcript_input(parsed, source))
        transcript = "\n".join(f"{_format_time(a)} --> {_format_time(b)} | {text}" for a, b, text in cues)
        prompt = AI_PROMPTS[skill] + "\n\nTimestamped source transcript:\n" + transcript
    else:
        raise ValueError("This creator skill is not implemented.")
    output = _ollama_generate(prompt, model=model)
    return {"skill": skill, "title": SKILL_BY_ID[skill]["name"], "engine": "ollama",
            "model": model or DEFAULT_MODEL, "result": output,
            "note": "Generated locally through Ollama. Review factual claims and edit before publishing."}
