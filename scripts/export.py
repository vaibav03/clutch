#!/usr/bin/env python3
"""Export a course knowledge base into portable study materials.

Cubbie uses this to turn the chunks that ingest.py wrote into things a student
can actually carry around: a Markdown study sheet to read, and a CSV of
flashcards to import into Anki or Quizlet. Everything is built from the local
knowledge base; no network, no API key.

Usage:
  python3 scripts/export.py sheet --course BIO201 [--out sheet.md]
  python3 scripts/export.py flashcards --course BIO201 [--out cards.csv]
  python3 scripts/export.py sheet --sample          # export the bundled sample
  python3 scripts/export.py flashcards --sample      # export the bundled sample

Output files default to "<course_dir>/exports/<slug>_studysheet.md" and
"<course_dir>/exports/<slug>_cards.csv". Exit 0 on success (including a missing
sample), exit 2 on a usage error.
"""
import argparse
import csv
import json
import os
import re
import sys

BASE = os.environ.get("CLUTCH_HOME") or os.path.join(
    os.path.expanduser("~"), ".local", "share", "clutch"
)

SAMPLE_COURSE = "SAMPLE101"

# Keep the printed preview well under the 8000-char stdout budget.
PREVIEW_CHARS = 400


def slug(course):
    """Slug a course name to its subfolder name (matches ingest/search)."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", course)


def course_dir(course):
    """Return the course subfolder under BASE (not created here)."""
    return os.path.join(BASE, slug(course))


def load_chunks(course):
    """Read chunks.jsonl for a course. Returns (chunks, error_or_None)."""
    path = os.path.join(course_dir(course), "chunks.jsonl")
    if not os.path.exists(path):
        return [], f"No knowledge base for '{course}'. Run ingest.py first."
    chunks = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip a corrupt line rather than crash the export
            if "text" in rec:
                chunks.append(rec)
    return chunks, None


def group_by_source(chunks):
    """Group chunk records by their source, preserving first-seen order."""
    groups = {}
    for c in chunks:
        src = c.get("source", "unknown")
        groups.setdefault(src, []).append(c)
    return groups


def first_sentence(text):
    """Return the first sentence of a chunk (used for a flashcard prompt)."""
    text = " ".join(text.split())  # collapse whitespace/newlines
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    sentence = m.group(1).strip() if m else text.strip()
    if len(sentence) > 160:
        sentence = sentence[:157].rstrip() + "..."
    return sentence


def build_sheet(course, chunks):
    """Render a Markdown study sheet grouped by source."""
    lines = [f"# {course} — Study Sheet", ""]
    groups = group_by_source(chunks)
    for source, items in groups.items():
        lines.append(f"## {source}")
        lines.append("")
        for c in items:
            text = " ".join(c.get("text", "").split())
            if text:
                lines.append(f"- {text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_cards(chunks):
    """Build (front, back) flashcard rows from chunks."""
    rows = []
    for c in chunks:
        source = c.get("source", "unknown")
        text = " ".join(c.get("text", "").split())
        if not text:
            continue
        sentence = first_sentence(text) or "Explain this key idea"
        front = f"{source}: {sentence}"
        rows.append((front, text))
    return rows


def write_file(path, writer):
    """Ensure the parent dir exists, then call writer(open_file_handle)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer(f)


def default_out(course, name):
    """Default export path under the course's exports/ folder."""
    return os.path.join(course_dir(course), "exports", f"{slug(course)}_{name}")


def do_sheet(course, out):
    chunks, err = load_chunks(course)
    if err:
        print(err)
        return 0
    if not chunks:
        print(f"No material to export for '{course}'.")
        return 0
    out = out or default_out(course, "studysheet.md")
    content = build_sheet(course, chunks)
    write_file(out, lambda f: f.write(content))
    preview = content[:PREVIEW_CHARS].rstrip()
    if len(content) > PREVIEW_CHARS:
        preview += "..."
    print(f"OK: wrote study sheet to {out}")
    print(f"({len(chunks)} chunks across "
          f"{len(group_by_source(chunks))} sources)")
    print("--- preview ---")
    print(preview)
    return 0


def do_flashcards(course, out):
    chunks, err = load_chunks(course)
    if err:
        print(err)
        return 0
    rows = build_cards(chunks)
    if not rows:
        print(f"No material to export for '{course}'.")
        return 0
    out = out or default_out(course, "cards.csv")

    def writer(f):
        w = csv.writer(f)
        w.writerow(["front", "back"])
        w.writerows(rows)

    write_file(out, writer)
    print(f"OK: wrote flashcards to {out}")
    print(f"({len(rows)} cards, importable into Anki or Quizlet)")
    return 0


def resolve_course(args):
    """Return (course, out, error_or_None) honoring --sample.

    In sample mode, if the sample has not been ingested yet, the caller prints a
    friendly line and exits 0 rather than erroring.
    """
    if args.sample:
        path = os.path.join(course_dir(SAMPLE_COURSE), "chunks.jsonl")
        if not os.path.exists(path):
            return None, None, (
                "No sample knowledge base yet. "
                "Run 'python3 scripts/ingest.py --sample' first."
            )
        return SAMPLE_COURSE, args.out, None
    if not args.course:
        return None, None, "ERROR: --course is required (or use --sample)."
    return args.course, args.out, None


def main():
    ap = argparse.ArgumentParser(
        description="Export a course knowledge base into portable study "
                    "materials (Markdown study sheet or flashcard CSV)."
    )
    sub = ap.add_subparsers(dest="cmd")

    p_sheet = sub.add_parser("sheet", help="Write a Markdown study sheet.")
    p_sheet.add_argument("--course", help="Course name (slugged to a subfolder).")
    p_sheet.add_argument("--out", help="Output path (default under exports/).")
    p_sheet.add_argument("--sample", action="store_true",
                         help="Export the bundled SAMPLE101 course.")

    p_cards = sub.add_parser("flashcards",
                             help="Write an Anki/Quizlet-importable CSV.")
    p_cards.add_argument("--course", help="Course name (slugged to a subfolder).")
    p_cards.add_argument("--out", help="Output path (default under exports/).")
    p_cards.add_argument("--sample", action="store_true",
                         help="Export the bundled SAMPLE101 course.")

    args = ap.parse_args()

    if args.cmd not in ("sheet", "flashcards"):
        print("ERROR: choose a subcommand: 'sheet' or 'flashcards'.")
        return 2

    course, out, err = resolve_course(args)
    if err:
        print(err)
        # A friendly sample message is informational (exit 0); a missing
        # --course outside sample mode is a usage error (exit 2).
        return 0 if err.startswith("No sample") else 2

    if args.cmd == "sheet":
        return do_sheet(course, out)
    return do_flashcards(course, out)


if __name__ == "__main__":
    sys.exit(main())
