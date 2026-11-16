#!/usr/bin/env python3
"""API-key-free YouTube niche research using public search results via yt-dlp.

This is a heuristic, not a prediction of virality. Research needs an internet connection;
all writing/inference after data collection can remain local through Ollama.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any
import json
import math
import re
import time

DEFAULT_NICHES = [
    ("Practical AI tools and automation", "AI tools tutorial"),
    ("Psychology and human behavior", "psychology human behavior explained"),
    ("Unusual history and mysteries", "history mysteries explained"),
    ("Space discoveries and astronomy", "space discoveries explained"),
    ("Science facts and everyday experiments", "surprising science facts explained"),
    ("Budget tech and smartphone tips", "budget tech smartphone tips"),
    ("Productivity and learning methods", "study productivity learning methods"),
    ("Money habits and personal finance basics", "personal finance money habits explained"),
    ("Animal behavior and wildlife facts", "animal behavior wildlife facts"),
    ("How things work and everyday engineering", "how things work engineering explained"),
]


def build_candidates(interest: str | None):
    interest = (interest or "").strip()
    if not interest:
        return [{"niche": name, "query": query} for name, query in DEFAULT_NICHES]
    variants = [
        (interest, interest),
        (f"Beginner guides in {interest}", f"{interest} beginner guide"),
        (f"Common mistakes in {interest}", f"{interest} common mistakes"),
        (f"Surprising facts about {interest}", f"{interest} surprising facts"),
        (f"Myths about {interest}", f"{interest} myths debunked"),
        (f"Practical tips in {interest}", f"{interest} practical tips"),
    ]
    return [{"niche": name, "query": query} for name, query in variants]


def _as_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _published_age_days(entry: dict[str, Any]) -> float | None:
    upload_date = str(entry.get("upload_date") or "")
    if re.fullmatch(r"\d{8}", upload_date):
        try:
            dt = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
            return max(0.5, (datetime.now(timezone.utc) - dt).total_seconds() / 86400)
        except ValueError:
            pass
    timestamp = entry.get("release_timestamp") or entry.get("timestamp")
    try:
        if timestamp:
            return max(0.5, (time.time() - float(timestamp)) / 86400)
    except (TypeError, ValueError):
        return None
    return None


def _extract_results(query: str, limit: int = 8) -> list[dict[str, Any]]:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("Missing yt-dlp. Run INSTALL.bat again or install it with: .venv\\Scripts\\python -m pip install yt-dlp") from exc

    options = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,
        "extract_flat": False,
        "noplaylist": True,
        "socket_timeout": 15,
        "retries": 1,
        "extractor_retries": 1,
        "playlistend": limit,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
    if not info:
        return []
    entries = info.get("entries") or []
    results = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        video_id = item.get("id")
        if not video_id:
            continue
        views = _as_int(item.get("view_count"))
        age = _published_age_days(item)
        duration = _as_int(item.get("duration"))
        results.append({
            "title": str(item.get("title") or "Untitled")[:240],
            "channel": str(item.get("channel") or item.get("uploader") or "Unknown channel")[:120],
            "url": str(item.get("webpage_url") or item.get("original_url") or f"https://www.youtube.com/watch?v={video_id}"),
            "views": views,
            "upload_date": item.get("upload_date"),
            "age_days": round(age, 1) if age is not None else None,
            "duration_seconds": duration,
            "views_per_day": round(views / max(age, 1.0), 1) if views is not None and age is not None else None,
        })
    return results


def score_candidate(candidate: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    useful = [r for r in results if r.get("views") is not None]
    velocities = [float(r["views_per_day"]) for r in useful if r.get("views_per_day") is not None]
    ages = [float(r["age_days"]) for r in useful if r.get("age_days") is not None]
    fresh_share = sum(age <= 30 for age in ages) / len(ages) if ages else None
    med_velocity = median(velocities) if velocities else 0.0
    p75_velocity = sorted(velocities)[min(len(velocities) - 1, int((len(velocities) - 1) * 0.75))] if velocities else 0.0
    valid_count = len(velocities)
    # Scores are normalized across the candidates in the current research snapshot later.
    return {
        **candidate,
        "results": results,
        "result_count": len(results),
        "metric_count": valid_count,
        "median_views_per_day": round(med_velocity, 1),
        "median_views": int(median([r["views"] for r in useful])) if useful else 0,
        "fresh_share": fresh_share,
        "p75_views_per_day": round(p75_velocity, 1),
        "breakout_ratio": round(p75_velocity / max(med_velocity, 1.0), 2) if velocities else 0,
        "score": 0,
        "demand_score": 0,
        "freshness_score": int(round(fresh_share * 100)) if fresh_share is not None else None,
        "breakout_score": 0,
        "confidence": "low" if valid_count < 3 or len(ages) < 3 else ("medium" if valid_count < 6 else "higher"),
    }


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if math.isclose(lo, hi):
        return [50.0 for _ in values]
    return [100.0 * (v - lo) / (hi - lo) for v in values]


def research_niches(interest: str | None = None, limit: int = 8, delay_seconds: float = 0.5):
    candidates = build_candidates(interest)
    scored = []
    errors = []
    print(f"Researching {len(candidates)} niche angles with public YouTube search (no API key)...")
    for index, candidate in enumerate(candidates, 1):
        print(f"  [{index}/{len(candidates)}] {candidate['niche']} ...", flush=True)
        try:
            results = _extract_results(candidate["query"], limit=limit)
            scored.append(score_candidate(candidate, results))
        except Exception as exc:
            errors.append(f"{candidate['query']}: {exc}")
            scored.append(score_candidate(candidate, []))
        if index < len(candidates):
            time.sleep(delay_seconds)

    if not any(row["metric_count"] for row in scored):
        details = "\n".join(errors[:3])
        raise RuntimeError("Could not collect usable YouTube search metrics. Check internet/YouTube access and try again." + ("\n" + details if details else ""))

    # Use log velocity to stop one massive outlier dominating the whole ranking.
    demand_raw = [math.log10(1 + row["median_views_per_day"]) for row in scored]
    demand_scores = _normalize(demand_raw)
    breakout_raw = [min(10.0, row["breakout_ratio"]) for row in scored]
    breakout_scores = _normalize(breakout_raw)
    for row, demand, breakout in zip(scored, demand_scores, breakout_scores):
        freshness = row["freshness_score"] if row["freshness_score"] is not None else 35.0
        row["demand_score"] = int(round(demand))
        row["breakout_score"] = int(round(breakout))
        row["score"] = int(round(0.55 * demand + 0.30 * freshness + 0.15 * breakout))
    # Favor candidates with actual sample coverage, while retaining the numeric score for transparency.
    scored.sort(key=lambda row: (row["metric_count"] >= 3, row["score"], row["median_views_per_day"]), reverse=True)
    result = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "method": "Public YouTube search results via yt-dlp; heuristic relative score from median views/day, fresh uploads, and breakout spread.",
        "interest": interest or "automatic multi-niche scan",
        "warning": "This is a relative snapshot, not a forecast or guarantee of high views. Search ranking is biased, metadata can be missing, and niche competition is not fully measurable without channel-level data.",
        "errors": errors,
        "ranked_niches": scored,
    }
    return result


def render_report(research: dict[str, Any]) -> str:
    lines = [
        "# YouTube Niche Research Report",
        "",
        f"Generated: {research.get('generated_at', 'unknown')}",
        f"Research scope: {research.get('interest', 'automatic scan')}",
        "",
        "> These scores compare the candidates in this scan only. They are not a promise of views or virality. Search results are biased, and competition is only partially observable.",
        "",
        "## Ranked opportunities",
        "",
        "| Rank | Niche / angle | Opportunity score | Median views/day | Fresh results (30d) | Sample | Confidence |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for i, row in enumerate(research.get("ranked_niches", []), 1):
        fresh = "n/a" if row["freshness_score"] is None else f"{row['freshness_score']}%"
        lines.append(f"| {i} | {row['niche']} | {row['score']}/100 | {row['median_views_per_day']:,.1f} | {fresh} | {row['metric_count']}/{row['result_count']} | {row['confidence']} |")
    for i, row in enumerate(research.get("ranked_niches", []), 1):
        lines.extend(["", f"## {i}. {row['niche']}", "", f"Search query: `{row['query']}`", "", "Sample videos:"])
        for item in sorted(row.get("results", []), key=lambda x: x.get("views") or 0, reverse=True)[:5]:
            views = f"{item['views']:,} views" if item.get("views") is not None else "views unavailable"
            velocity = f", {item['views_per_day']:,.1f} views/day (estimated)" if item.get("views_per_day") is not None else ""
            lines.append(f"- [{item['title']}]({item['url']}) — {views}{velocity}; channel: {item['channel']}")
    if research.get("errors"):
        lines.extend(["", "## Searches with errors", ""])
        lines.extend(f"- {e}" for e in research["errors"])
    lines.extend(["", "## Interpreting the score", "", "- Demand compares median estimated views per day within this scan.", "- Freshness is the share of results uploaded within the last 30 days when upload dates were available.", "- Breakout captures whether a few videos outperform the middle of the sample.", "- The score does not directly measure creator competition and does not guarantee future views.", ""])
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--interest", help="Narrow the scan to a broad subject; omit it to compare several niches")
    ap.add_argument("--limit", type=int, default=8, help="Search results per niche (5-15 recommended)")
    ap.add_argument("--out", default="niche_research_report.md", help="Markdown report path")
    args = ap.parse_args()
    data = research_niches(args.interest, max(5, min(15, args.limit)))
    Path(args.out).write_text(render_report(data), encoding="utf-8")
    Path(args.out).with_suffix(".json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nTop opportunity: {data['ranked_niches'][0]['niche']} (score {data['ranked_niches'][0]['score']}/100)")
    print(f"Report: {args.out}")

if __name__ == "__main__":
    main()
