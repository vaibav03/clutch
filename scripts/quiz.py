#!/usr/bin/env python3
"""Adaptive-quiz engine for the Clutch Cubbie Skill.

Cubbie reads the course material, writes the actual questions, and reports how
the student did. This script owns only the *bookkeeping*: it holds per-chunk
mastery state and decides, using Leitner spaced repetition, which chunks are due
for review. It never talks to Cubbie or the network; it reads chunks from disk,
reads/writes a mastery file, and prints plain text that Cubbie consumes.

Subcommands:
  next       select up to N due/unseen chunks to quiz, print them + an IDS line
  record     update one chunk's mastery after a right/wrong answer
  readiness  summarize mastery per topic (source) with a traffic-light score

State lives under $CLUTCH_HOME (default ~/.local/share/clutch), in a
per-course subfolder named after a slugified course name.

Usage:
  python3 scripts/quiz.py next --course BIO201 --n 5
  python3 scripts/quiz.py next --sample
  python3 scripts/quiz.py record --course BIO201 --item 3 --result right
  python3 scripts/quiz.py readiness --course BIO201
  python3 scripts/quiz.py readiness --sample
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta

BASE = os.environ.get("CLUTCH_HOME") or os.path.join(
    os.path.expanduser("~"), ".local", "share", "clutch"
)

SAMPLE_COURSE = "SAMPLE101"

# Leitner interval (in days) for each box index 0..5. A higher box means the
# item is better known and gets reviewed less often.
INTERVALS = [0, 1, 3, 7, 16, 35]
MAX_BOX = len(INTERVALS) - 1

STDOUT_BUDGET = 8000  # keep printed output comfortably under this many chars


def course_dir(course):
    """Slugified per-course folder under BASE (created if missing)."""
    d = os.path.join(BASE, re.sub(r"[^A-Za-z0-9_-]", "_", course))
    os.makedirs(d, exist_ok=True)
    return d


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
            rec = json.loads(line)
            chunks.append(rec)
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


def save_mastery(cdir, mastery):
    mastery["updated"] = date.today().isoformat()
    with open(mastery_path(cdir), "w") as f:
        json.dump(mastery, f, indent=2)
        f.write("\n")


def next_due(box, today):
    """Date an item in the given box should next be reviewed."""
    return (today + timedelta(days=INTERVALS[box])).isoformat()


def apply_result(item, correct, today):
    """Mutate a mastery item in place for a right/wrong answer."""
    item["seen"] = item.get("seen", 0) + 1
    if correct:
        item["correct"] = item.get("correct", 0) + 1
        item["box"] = min(item.get("box", 0) + 1, MAX_BOX)
    else:
        item["box"] = 0
    item["last_asked"] = today.isoformat()
    item["next_due"] = next_due(item["box"], today)
    return item


def new_item(today):
    """A never-seen item placed in box 0 and immediately due."""
    return {
        "box": 0,
        "seen": 0,
        "correct": 0,
        "last_asked": None,
        "next_due": today.isoformat(),
    }


def truncate(text, limit=400):
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def missing_chunks_message(cdir):
    """Shared one-liner when the course has no ingested chunks yet."""
    print(
        f"No chunks found at {chunks_path(cdir)}. "
        "Run ingest.py first to add course material."
    )


# --------------------------------------------------------------------------- #
# Subcommand: next
# --------------------------------------------------------------------------- #
def cmd_next(args):
    course = SAMPLE_COURSE if args.sample else args.course
    if not course:
        print("ERROR: --course is required (or use --sample).")
        return 2

    cdir = course_dir(course)
    chunks = load_chunks(cdir)
    if chunks is None:
        missing_chunks_message(cdir)
        return 0

    mastery = load_mastery(cdir)
    items = mastery["items"]
    today = date.today()
    today_iso = today.isoformat()

    # Build a selectable record per chunk, keeping only due or never-seen ones.
    candidates = []
    for ch in chunks:
        cid = ch["id"]
        st = items.get(cid)
        if st is None:
            seen = False
            box = 0
            due = today_iso
        else:
            seen = st.get("seen", 0) > 0
            box = st.get("box", 0)
            due = st.get("next_due", today_iso)
            # Not seen yet (recorded but never asked) still counts as due.
            is_due = (not seen) or due <= today_iso
            if not is_due:
                continue
        candidates.append(
            {"chunk": ch, "never_seen": not seen, "box": box, "due": due}
        )

    # Priority: never-seen first, then lowest box, then earliest next_due.
    candidates.sort(
        key=lambda c: (not c["never_seen"], c["box"], c["due"], c["chunk"]["id"])
    )

    selected = candidates[: max(args.n, 0)]
    if not selected:
        print("Nothing due right now. Everything is scheduled for later.")
        print("IDS:")
        return 0

    lines = []
    ids = []
    for c in selected:
        ch = c["chunk"]
        ids.append(ch["id"])
        lines.append(f"[{ch['id']}] ({ch.get('source', '?')})")
        lines.append(truncate(ch.get("text", "")))
        lines.append("")

    # Respect the stdout budget: drop trailing items if we overflow. We always
    # keep at least the first item and always print an accurate IDS line.
    while len(selected) > 1:
        body = "\n".join(lines)
        ids_line = "IDS: " + ",".join(ids)
        if len(body) + len(ids_line) + 1 < STDOUT_BUDGET:
            break
        # Drop the last selected item (3 lines each) and its id.
        selected = selected[:-1]
        ids = ids[:-1]
        lines = lines[: len(selected) * 3]

    sys.stdout.write("\n".join(lines))
    print("IDS: " + ",".join(ids))
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: record
# --------------------------------------------------------------------------- #
def cmd_record(args):
    if not args.course:
        print("ERROR: --course is required.")
        return 2
    if not args.item or args.result not in ("right", "wrong"):
        print("ERROR: --item <id> and --result right|wrong are required.")
        return 2

    cdir = course_dir(args.course)
    mastery = load_mastery(cdir)
    items = mastery["items"]
    today = date.today()

    item = items.get(args.item)
    if item is None:
        item = new_item(today)
        items[args.item] = item

    apply_result(item, args.result == "right", today)
    save_mastery(cdir, mastery)

    mark = "correct" if args.result == "right" else "incorrect"
    print(
        f"Recorded {mark} for [{args.item}]: box {item['box']}, "
        f"seen {item['seen']}, next due {item['next_due']}."
    )
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: readiness
# --------------------------------------------------------------------------- #
def light(score):
    if score >= 0.7:
        return "\U0001F7E2"  # green
    if score >= 0.4:
        return "\U0001F7E1"  # yellow
    return "\U0001F534"  # red


def cmd_readiness(args):
    course = SAMPLE_COURSE if args.sample else args.course
    if not course:
        print("ERROR: --course is required (or use --sample).")
        return 2

    cdir = course_dir(course)
    chunks = load_chunks(cdir)
    if chunks is None:
        missing_chunks_message(cdir)
        return 0

    mastery = load_mastery(cdir)
    items = mastery["items"]

    # Aggregate per source (topic), preserving first-seen order.
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
        box = st.get("box", 0) if st else 0
        if st and st.get("seen", 0) > 0:
            s["seen"] += 1
        s["box_sum"] += box / MAX_BOX  # never-seen contributes 0

    rows = []
    for src in order:
        s = stats[src]
        score = s["box_sum"] / s["total"] if s["total"] else 0.0
        rows.append((src, score, s["seen"], s["total"]))

    for src, score, seen, total in rows:
        print(f"{light(score)} {src} ({round(score * 100)}% , seen {seen}/{total})")

    # Weakest = the red topics, or if none are red, the single lowest-scoring one.
    weak = [src for src, score, _, _ in rows if score < 0.4]
    if not weak and rows:
        lowest = min(r[1] for r in rows)
        weak = [src for src, score, _, _ in rows if score == lowest]
    print("Weakest: " + (", ".join(weak) if weak else "none"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Adaptive-quiz engine for Clutch.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_next = sub.add_parser("next", help="select chunks that are due for review")
    p_next.add_argument("--course")
    p_next.add_argument("--n", type=int, default=5)
    p_next.add_argument("--sample", action="store_true")
    p_next.set_defaults(func=cmd_next)

    p_rec = sub.add_parser("record", help="record a right/wrong answer")
    p_rec.add_argument("--course")
    p_rec.add_argument("--item")
    p_rec.add_argument("--result")
    p_rec.set_defaults(func=cmd_record)

    p_ready = sub.add_parser("readiness", help="per-topic mastery summary")
    p_ready.add_argument("--course")
    p_ready.add_argument("--sample", action="store_true")
    p_ready.set_defaults(func=cmd_readiness)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
