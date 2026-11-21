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
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b")
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
    return {"skills": SKILLS, "model": DEFAULT_MODEL, "recommended_model": "qwen3:4b",
            "recommended_model_note": "For this 4 GB VRAM / 32 GB RAM class of PC, try qwen3:4b Q4 first; it may partially offload to system RAM. Close GPU-heavy apps and test response speed."}


def _ollama_generate(prompt: str, *, model: str | None = None, timeout: int = 300) -> str:
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
        "options": {"temperature": 0.65, "num_ctx": 8192},
    }
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
            "and set OLLAMA_MODEL if needed. Suggested model for this hardware: qwen3:4b."
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
        for cell in row:
            cleaned = cell.strip().replace("%", "").replace(",", "")
            try:
                numbers.append(float(cleaned))
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


def _title_formula(title: str) -> str:
    lower = title.lower()
    if re.search(r"\b\d+\b", lower):
        return "Specific number or list"
    if lower.startswith(("how ", "how to ")):
        return "How-to / transformation"
    if lower.startswith("why ") or "why " in lower[:25]:
        return "Curiosity / explanation"
    if re.search(r"\b(vs\.?|versus|instead of|but)\b", lower):
        return "Contrast"
    if re.search(r"\b(i tried|i tested|my|journey|built|made)\b", lower):
        return "Personal experiment"
    return "Unclassified title pattern"


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
    "yt-package": """Create ten distinct YouTube title + thumbnail pairs for the supplied idea and audience. Make each title specific and truthful; avoid fake urgency, unsupported numbers and vague hype. The thumbnail must add a different piece of information rather than repeat the title and should use at most three short words. Rank the top three and explain each tradeoff. Include a thumbnail visual brief for the strongest pair. Apply approximate 40-character mobile and 60-character desktop display checks; these are heuristics, not guaranteed truncation points. Do not claim CTR predictions.""",
    "yt-plan": """Build a realistic weekly or monthly YouTube content plan based on the creator's actual available hours and work already in progress. Prefer one anchor video, one lower-effort upload and up to three Shorts repurposed from the anchor when capacity allows. Return a table with day, format, working title, viewer promise, existing assets, and estimated work hours. Total the hours and state what to drop first if the week becomes busy. Do not invent the best upload day; use analytics only if supplied.""",
    "yt-script": """Write a YouTube script that earns the click and sustains attention. First produce FIVE substantially different opening hooks using varied approaches (specific result, counter-intuition, problem, experiment, open loop). Give each a heuristic score out of 100 with a short reason; scores are editorial estimates, not predicted retention. Pick the strongest two. Then write the script beat by beat. The first 15 seconds must confirm the title promise, open a useful question and demonstrate a payoff. Mark every beat with [ON SCREEN: ...]. Avoid long intros, filler, fake claims and unverified statistics. Deliver the promised payoff and use one closing ask. Estimate runtime at 150 spoken words/minute.""",
    "yt-seo": """Create a useful YouTube SEO pack for the real viewer query. Write a two-line opening description that says exactly what the viewer gets using the supplied target phrase naturally. Add resource links only when supplied, then a useful longer description, chapters only if supplied, and up to 15 relevant tags for disambiguation. End with three target search queries and check whether the title and first two description lines contain their main terms. Do not invent search-volume numbers or promise rankings; explain that tags are a weaker discovery signal than viewer satisfaction and packaging.""",
    "yt-shorts": """Find up to five self-contained Shorts inside the supplied timestamped transcript. Each candidate must be about 20–55 seconds, start with enough context to stand alone, contain a clear turn/payoff and end on a complete line. For each provide start/end timecodes, exact opening words, why it works alone, a NEW hook, different first-two-second on-screen text, a suggested loop point and a vertical crop note. Do not invent transcript quotes or timestamps. If timestamps are not present or too few suitable spans exist, say so rather than guessing.""",
}


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
        transcript = parsed.get("transcript", "") if isinstance(parsed, dict) else source
        result = run_chapters(transcript, target)
        lines = [f"Valid YouTube chapters: {'YES' if result['valid'] else 'NO'}", ""]
        lines += [f"{c['timestamp']} {c['draft_title']}  ({c['duration_seconds']:.1f}s)" for c in result["chapters"]]
        lines += ["", result["note"]]
        return {"skill": skill, "title": SKILL_BY_ID[skill]["name"], "engine": "python", "result": "\n".join(lines), "data": result}
    if skill == "yt-edit":
        floor = parsed.get("floor", 0.45) if isinstance(parsed, dict) else 0.45
        transcript = parsed.get("transcript", "") if isinstance(parsed, dict) else source
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
    elif skill == "yt-audit":
        prompt = AI_PROMPTS[skill] + "\n\nChannel evidence supplied by creator:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
    elif skill == "yt-comment":
        prompt = AI_PROMPTS[skill] + "\n\nComments and optional creator voice:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
    elif skill == "yt-package":
        prompt = AI_PROMPTS[skill] + "\n\nVideo brief:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
    elif skill == "yt-plan":
        prompt = AI_PROMPTS[skill] + "\n\nCreator capacity and content inventory:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
    elif skill == "yt-seo":
        prompt = AI_PROMPTS[skill] + "\n\nVideo metadata and audience:\n" + (json.dumps(parsed, ensure_ascii=False, indent=2) if not isinstance(parsed, str) else parsed)
    elif skill == "yt-shorts":
        cues = parse_transcript(parsed.get("transcript", "") if isinstance(parsed, dict) else source)
        transcript = "\n".join(f"{_format_time(a)} --> {_format_time(b)} | {text}" for a, b, text in cues)
        prompt = AI_PROMPTS[skill] + "\n\nTimestamped source transcript:\n" + transcript
    else:
        raise ValueError("This creator skill is not implemented.")
    output = _ollama_generate(prompt, model=model)
    return {"skill": skill, "title": SKILL_BY_ID[skill]["name"], "engine": "ollama",
            "model": model or DEFAULT_MODEL, "result": output,
            "note": "Generated locally through Ollama. Review factual claims and edit before publishing."}
