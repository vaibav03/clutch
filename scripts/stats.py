#!/usr/bin/env python3
"""Gamified progress summary for the exam-mode Cubbie Skill.

Cubbie runs this when a student wants to see how far they've come. It reads the
course's chunks and mastery file and prints a tight, motivating dashboard:
overall mastery, how many chunks are "locked in", the current study streak,
a per-topic progress bar, the weakest topics, and how much is due today.

This script is strictly READ-ONLY: it never writes chunks, mastery, or any other
state. It takes no network and no API key; it just reads from disk and prints
plain text that Cubbie relays to the student.

Usage:
  python3 scripts/stats.py show --course BIO201
  python3 scripts/stats.py --sample
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta

BASE = os.environ.get("EXAM_MODE_HOME") or os.path.join(
    os.path.expanduser("~"), ".local", "share", "exam-mode"
)

SAMPLE_COURSE = "SAMPLE101"

MAX_BOX = 5  # boxes run 0..5; box/MAX_BOX is a chunk's fractional mastery
LOCKED_BOX = 4  # box >= this counts as "locked in"
BAR_WIDTH = 10

STDOUT_BUDGET = 8000  # keep printed output comfortably under this many chars


def course_dir(course):
    """Slugified per-course folder under BASE (NOT created — read-only tool)."""
    return os.path.join(BASE, re.sub(r"[^A-Za-z0-9_-]", "_", course))


def chunks_path(cdir):
    return os.path.join(cdir, "chunks.jsonl")


def mastery_path(cdir):
    return os.path.join(cdir, "mastery.json")


def load_chunks(cdir):
    """Read chunks.jsonl into a list of dicts, or return None if missing."""
    path = chunks_path(cdir)
    if not os.path.exists(path):
        return None
    chunks = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunks.append(json.loads(line))
    return chunks


def load_mastery(cdir):
    """Read mastery.json, tolerating a missing or empty file."""
    path = mastery_path(cdir)
    if not os.path.exists(path):
        return {"items": {}, "updated": None}
    with open(path) as f:
        data = json.load(f)
    data.setdefault("items", {})
    data.setdefault("updated", None)
    return data


def box_of(items, cid):
    """Current box for a chunk id; never-seen (no record) counts as 0."""
    st = items.get(cid)
    return st.get("box", 0) if st else 0


def bar(fraction):
    """A BAR_WIDTH-char progress bar: filled blocks over light shade."""
    filled = int(round(fraction * BAR_WIDTH))
    filled = max(0, min(BAR_WIDTH, filled))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def study_streak(items, today):
    """Consecutive days (ending today or yesterday) with any item last_asked.

    Returns the streak length; 0 means no active streak.
    """
    days = set()
    for st in items.values():
        la = st.get("last_asked")
        if la:
            days.add(la)
    if not days:
        return 0

    today_iso = today.isoformat()
    yesterday_iso = (today - timedelta(days=1)).isoformat()
    if today_iso in days:
        cursor = today
    elif yesterday_iso in days:
        cursor = today - timedelta(days=1)
    else:
        return 0  # most recent study day is too old to count as a streak

    streak = 0
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def cmd_show(args):
    course = SAMPLE_COURSE if args.sample else args.course
    if not course:
        print("ERROR: --course is required (or use --sample).")
        return 2

    cdir = course_dir(course)
    chunks = load_chunks(cdir)
    if not chunks:
        # Missing or empty chunks.jsonl: one clear line, still a clean exit.
        print(
            f"No progress yet for {course}. "
            "Run ingest.py and quiz.py first to build up some stats."
        )
        return 0

    mastery = load_mastery(cdir)
    items = mastery["items"]
    today = date.today()
    today_iso = today.isoformat()

    total = len(chunks)

    # Overall mastery: mean of box/5 across all chunks (never-seen = 0).
    mastery_sum = sum(box_of(items, ch["id"]) / MAX_BOX for ch in chunks)
    overall_pct = round(100 * mastery_sum / total)

    # Locked in: chunks sitting in box >= LOCKED_BOX.
    locked = sum(1 for ch in chunks if box_of(items, ch["id"]) >= LOCKED_BOX)

    # Due today: next_due <= today, with never-seen chunks counting as due.
    due = 0
    for ch in chunks:
        st = items.get(ch["id"])
        if not st or st.get("seen", 0) == 0:
            due += 1
        elif st.get("next_due", today_iso) <= today_iso:
            due += 1

    streak = study_streak(items, today)

    # Per-source aggregates (first-seen order preserved for stable ties).
    order = []
    stats = {}
    for ch in chunks:
        src = ch.get("source", "?")
        if src not in stats:
            stats[src] = {"total": 0, "seen": 0, "box_sum": 0.0}
            order.append(src)
        s = stats[src]
        s["total"] += 1
        st = items.get(ch["id"])
        if st and st.get("seen", 0) > 0:
            s["seen"] += 1
        s["box_sum"] += box_of(items, ch["id"]) / MAX_BOX

    rows = []
    for src in order:
        s = stats[src]
        frac = s["box_sum"] / s["total"] if s["total"] else 0.0
        rows.append((src, frac, s["seen"], s["total"]))

    # Weakest first; stable within equal scores by original order.
    rows.sort(key=lambda r: (r[1], order.index(r[0])))

    # ---- print the dashboard -------------------------------------------- #
    out = []
    out.append(f"=== {course} progress ===")
    out.append(f"Overall mastery: {overall_pct}%")
    out.append(f"Locked in: {locked}/{total} chunks (box {LOCKED_BOX}+)")
    if streak > 0:
        plural = "day" if streak == 1 else "days"
        out.append(f"Study streak: \U0001F525 {streak} {plural}")
    else:
        out.append("Study streak: no streak yet")
    out.append(f"Due today: {due}")
    out.append("")
    out.append("Per-topic (weakest first):")
    for src, frac, seen, tot in rows:
        out.append(f"  {bar(frac)} {round(frac * 100)}%  {src} (seen {seen}/{tot})")

    weakest = [src for src, _, _, _ in rows[:3]]
    out.append("")
    out.append("Weakest topics: " + (", ".join(weakest) if weakest else "none"))

    text = "\n".join(out)
    if len(text) > STDOUT_BUDGET:
        text = text[: STDOUT_BUDGET - 1].rstrip() + "…"
    print(text)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Gamified progress summary for exam-mode (read-only)."
    )
    # Allow a bare `--sample` as well as the explicit `show` subcommand.
    ap.add_argument("--course")
    ap.add_argument("--sample", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    p_show = sub.add_parser("show", help="print the progress dashboard")
    p_show.add_argument("--course")
    p_show.add_argument("--sample", action="store_true")
    p_show.set_defaults(func=cmd_show)

    args = ap.parse_args(argv)

    if args.cmd is None:
        # No subcommand: only valid invocation is a top-level --sample/--course.
        if not args.sample and not args.course:
            ap.print_usage()
            print("ERROR: use `show --course <name>` or `--sample`.")
            return 2
        return cmd_show(args)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
