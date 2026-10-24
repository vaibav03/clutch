#!/usr/bin/env python3
"""One-shot mock exam for the Clutch Cubbie Skill.

Unlike quiz.py's spaced daily drip, this builds a single *broad* practice exam
that samples across the whole course. The script can't call Cubbie, so it only
picks the chunks and holds the exam state: Cubbie reads the printed chunks,
writes the actual questions, administers them, and reports each result back here
with `grade` so mastery is updated and a scorecard is produced.

It never talks to Cubbie or the network; it reads chunks from disk, reads/writes
the mastery file, and prints plain text that Cubbie consumes.

Subcommands:
  generate   select up to N chunks maximizing breadth, print them + an IDS line,
             and save mock_exam.json so grade knows what was on the exam
  grade      update mastery for each answered item, print a scorecard, and clear
             the saved exam

State lives under $CLUTCH_HOME (default ~/.local/share/clutch), in a
per-course subfolder named after a slugified course name.

Usage:
  python3 scripts/mock_exam.py generate --course BIO201 --n 10
  python3 scripts/mock_exam.py generate --sample
  python3 scripts/mock_exam.py grade --course BIO201 --item 3 --result right \
                                      --item 7 --result wrong
  python3 scripts/mock_exam.py grade --course BIO201 --answers "3:right,7:wrong"
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta

BASE = os.environ.get("CLUTCH_HOME") or os.path.join(
    os.path.expanduser("~"), ".local", "share", "clutch"
)

SAMPLE_COURSE = "SAMPLE101"

# Leitner interval (in days) for each box index 0..5. Same rules as quiz.py:
# a right answer promotes (box+1, capped at 5), a wrong answer resets to box 0.
INTERVALS = [0, 1, 3, 7, 16, 35]
MAX_BOX = len(INTERVALS) - 1

STDOUT_BUDGET = 8000  # keep printed output comfortably under this many chars
MAX_CHARS_PER_CHUNK = 300  # truncate each chunk shown on the exam


def course_dir(course):
    """Slugified per-course folder under BASE (created if missing)."""
    d = os.path.join(BASE, re.sub(r"[^A-Za-z0-9_-]", "_", course))
    os.makedirs(d, exist_ok=True)
    return d


def chunks_path(cdir):
    return os.path.join(cdir, "chunks.jsonl")


def mastery_path(cdir):
    return os.path.join(cdir, "mastery.json")


def exam_path(cdir):
    return os.path.join(cdir, "mock_exam.json")


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
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip a corrupt line rather than crash
            if "text" in rec and "id" in rec:
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
    """Mutate a mastery item in place for a right/wrong answer (Leitner)."""
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


def truncate(text, limit=MAX_CHARS_PER_CHUNK):
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def id_sort_key(cid):
    """Numeric ids sort numerically; everything else falls back to the string."""
    try:
        return (0, int(cid), "")
    except (TypeError, ValueError):
        return (1, 0, str(cid))


def weakness_key(chunk, items):
    """Sort key where *smaller* means weaker / higher priority to test.

    Never-seen chunks come first, then lowest Leitner box, then id order. This
    is what fills the remaining exam slots after breadth is covered.
    """
    st = items.get(chunk["id"])
    never_seen = (st is None) or st.get("seen", 0) <= 0
    box = st.get("box", 0) if st else 0
    return (0 if never_seen else 1, box, id_sort_key(chunk["id"]))


def missing_chunks_message(cdir):
    """Shared one-liner when the course has no ingested chunks yet."""
    print(
        f"No chunks found at {chunks_path(cdir)}. "
        "Run ingest.py first to add course material."
    )


# --------------------------------------------------------------------------- #
# Breadth selection
# --------------------------------------------------------------------------- #
def select_breadth(chunks, items, n):
    """Pick up to n chunks maximizing breadth across sources.

    Phase 1: at least one chunk per distinct source (the weakest of each),
    taking sources in first-seen order until the slots run out.
    Phase 2: fill any remaining slots with the weakest chunks not yet chosen.
    """
    if n <= 0:
        return []

    # Group chunks by source, preserving first-seen source order.
    order = []
    by_source = {}
    for ch in chunks:
        src = ch.get("source", "?")
        if src not in by_source:
            by_source[src] = []
            order.append(src)
        by_source[src].append(ch)

    selected = []
    chosen_ids = set()

    # Phase 1 — one (weakest) chunk per source, breadth first.
    for src in order:
        if len(selected) >= n:
            break
        weakest = min(by_source[src], key=lambda c: weakness_key(c, items))
        selected.append(weakest)
        chosen_ids.add(weakest["id"])

    # Phase 2 — fill remaining slots with the weakest leftover chunks.
    if len(selected) < n:
        leftovers = [c for c in chunks if c["id"] not in chosen_ids]
        leftovers.sort(key=lambda c: weakness_key(c, items))
        for c in leftovers:
            if len(selected) >= n:
                break
            selected.append(c)
            chosen_ids.add(c["id"])

    return selected


# --------------------------------------------------------------------------- #
# Subcommand: generate
# --------------------------------------------------------------------------- #
def cmd_generate(args):
    course = SAMPLE_COURSE if args.sample else args.course
    if not course:
        print("ERROR: --course is required (or use --sample).")
        return 2

    cdir = course_dir(course)
    chunks = load_chunks(cdir)
    if not chunks:
        # A dry sample run (or a course with no material) must exit 0 cleanly.
        missing_chunks_message(cdir)
        return 0

    mastery = load_mastery(cdir)
    items = mastery["items"]

    n = args.n if args.n and args.n > 0 else 10
    selected = select_breadth(chunks, items, n)

    lines = []
    ids = []
    for ch in selected:
        ids.append(ch["id"])
        lines.append(f"[{ch['id']}] ({ch.get('source', '?')})")
        lines.append(truncate(ch.get("text", "")))
        lines.append("")

    # Respect the stdout budget: drop trailing items if we overflow, keeping at
    # least one. The saved exam and the IDS line only ever list what we printed.
    while len(selected) > 1:
        body = "\n".join(lines)
        ids_line = "IDS: " + ",".join(ids)
        if len(body) + len(ids_line) + 1 < STDOUT_BUDGET:
            break
        selected = selected[:-1]
        ids = ids[:-1]
        lines = lines[: len(selected) * 3]

    # Save the exam so grade knows exactly what was asked.
    exam = {
        "started": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ids": ids,
    }
    with open(exam_path(cdir), "w") as f:
        json.dump(exam, f, indent=2)
        f.write("\n")

    sys.stdout.write("\n".join(lines))
    print("IDS: " + ",".join(ids))
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: grade
# --------------------------------------------------------------------------- #
def parse_results(args):
    """Collect (id, result) pairs from --item/--result or --answers.

    Returns (pairs, error_message). Each result is validated to be
    'right' or 'wrong'; an invalid value yields an error (caller exits 2).
    """
    pairs = []

    if args.answers:
        for tok in args.answers.split(","):
            tok = tok.strip()
            if not tok:
                continue
            if ":" not in tok:
                return None, f"ERROR: bad answer '{tok}', expected 'id:right|wrong'."
            cid, _, res = tok.partition(":")
            cid, res = cid.strip(), res.strip().lower()
            if not cid:
                return None, f"ERROR: bad answer '{tok}', missing id."
            if res not in ("right", "wrong"):
                return None, f"ERROR: result for '{cid}' must be right|wrong, got '{res}'."
            pairs.append((cid, res))

    items = args.item or []
    results = args.result or []
    if items or results:
        if len(items) != len(results):
            return None, (
                "ERROR: --item and --result must be given in matching pairs "
                f"(got {len(items)} items, {len(results)} results)."
            )
        for cid, res in zip(items, results):
            res = res.strip().lower()
            if res not in ("right", "wrong"):
                return None, f"ERROR: result for '{cid}' must be right|wrong, got '{res}'."
            pairs.append((cid.strip(), res))

    return pairs, None


def cmd_grade(args):
    if not args.course:
        print("ERROR: --course is required.")
        return 2

    pairs, err = parse_results(args)
    if err:
        print(err)
        return 2
    if not pairs:
        print("ERROR: no results given. Use --item/--result pairs or --answers.")
        return 2

    cdir = course_dir(args.course)
    chunks = load_chunks(cdir) or []
    source_of = {ch["id"]: ch.get("source", "?") for ch in chunks}

    mastery = load_mastery(cdir)
    mitems = mastery["items"]
    today = date.today()

    # Update mastery and tally per source. Later duplicate answers for an id win
    # the tally but every answer still updates mastery (Leitner, in order).
    per_source = {}       # source -> [correct, total]
    source_order = []
    per_id_correct = {}
    for cid, res in pairs:
        correct = res == "right"
        item = mitems.get(cid)
        if item is None:
            item = new_item(today)
            mitems[cid] = item
        apply_result(item, correct, today)
        per_id_correct[cid] = correct

    # Build the scorecard from the final per-id verdict (unique ids).
    n_total = 0
    n_correct = 0
    for cid, correct in per_id_correct.items():
        src = source_of.get(cid, "?")
        if src not in per_source:
            per_source[src] = [0, 0]
            source_order.append(src)
        per_source[src][1] += 1
        n_total += 1
        if correct:
            per_source[src][0] += 1
            n_correct += 1

    save_mastery(cdir, mastery)

    # Clear the saved exam now that it has been graded.
    try:
        os.remove(exam_path(cdir))
    except OSError:
        pass

    pct = round(100 * n_correct / n_total) if n_total else 0
    print(f"Score: {n_correct}/{n_total} ({pct}%)")

    ratios = {}
    for src in source_order:
        c, t = per_source[src]
        sp = round(100 * c / t) if t else 0
        ratios[src] = (c / t) if t else 0.0
        print(f"  {src}: {c}/{t} ({sp}%)")

    # Weakest = the source(s) with the lowest ratio, unless everything was perfect.
    if ratios:
        lowest = min(ratios.values())
        if lowest >= 1.0:
            weak = []
        else:
            weak = [src for src in source_order if ratios[src] == lowest]
    else:
        weak = []
    print("Weakest: " + (", ".join(weak) if weak else "none"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="One-shot broad mock exam for Clutch."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("generate", help="build a broad mock exam")
    p_gen.add_argument("--course")
    p_gen.add_argument("--n", type=int, default=10)
    p_gen.add_argument("--sample", action="store_true")
    p_gen.set_defaults(func=cmd_generate)

    p_grade = sub.add_parser("grade", help="grade a completed mock exam")
    p_grade.add_argument("--course")
    p_grade.add_argument("--item", action="append",
                         help="chunk id (repeatable, paired with --result)")
    p_grade.add_argument("--result", action="append",
                         help="right|wrong (repeatable, paired with --item)")
    p_grade.add_argument("--answers",
                         help='comma list, e.g. "3:right,7:wrong"')
    p_grade.set_defaults(func=cmd_grade)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
