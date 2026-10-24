#!/usr/bin/env python3
"""Ingest course material into a local knowledge base.

Cubbie reads a slide deck / lecture transcript / photo with its own abilities,
then hands the plain text to this script. The script chunks the text, tags each
chunk with its source, and appends it to the course's knowledge base. No network,
no API key; everything stays under the student's HOME.

Usage:
  python3 scripts/ingest.py --course BIO201 --source "Lecture 3" --file notes.txt
  python3 scripts/ingest.py --course BIO201 --source "Slides Ch5" --text "..."
  python3 scripts/ingest.py --sample        # ingest the bundled sample, no args needed
"""
import argparse
import json
import os
import re
import sys

BASE = os.environ.get("CLUTCH_HOME") or os.path.join(
    os.path.expanduser("~"), ".local", "share", "clutch"
)


def course_dir(course):
    d = os.path.join(BASE, re.sub(r"[^A-Za-z0-9_-]", "_", course))
    os.makedirs(d, exist_ok=True)
    return d


def chunk_text(text, max_chars=600):
    """Split on blank lines, then pack paragraphs into ~max_chars chunks."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) + 1 > max_chars and buf:
            chunks.append(buf.strip())
            buf = p
        else:
            buf = (buf + "\n" + p) if buf else p
    if buf.strip():
        chunks.append(buf.strip())
    return chunks


def ingest(course, source, text):
    cdir = course_dir(course)
    path = os.path.join(cdir, "chunks.jsonl")
    existing = 0
    if os.path.exists(path):
        with open(path) as f:
            existing = sum(1 for _ in f)
    chunks = chunk_text(text)
    with open(path, "a") as f:
        for i, c in enumerate(chunks):
            rec = {"id": f"{existing + i}", "source": source, "text": c}
            f.write(json.dumps(rec) + "\n")
    return len(chunks), existing + len(chunks)


SAMPLE_COURSE = "SAMPLE101"
SAMPLE_SOURCE = "Lecture 1 - Cell Energy"
SAMPLE_TEXT = """Glycolysis is the first stage of cellular respiration. It happens in the
cytoplasm and does not need oxygen. One molecule of glucose is split into two molecules
of pyruvate, producing a net gain of 2 ATP and 2 NADH.

The citric acid cycle (Krebs cycle) takes place in the mitochondrial matrix. Each turn
releases carbon dioxide and produces NADH, FADH2, and a small amount of ATP. The cycle
runs twice per glucose molecule.

The electron transport chain is located in the inner mitochondrial membrane. It uses the
NADH and FADH2 made earlier to pump protons and drive ATP synthase. This stage produces
the majority of the ATP from one glucose molecule, around 34 ATP.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course")
    ap.add_argument("--source")
    ap.add_argument("--file")
    ap.add_argument("--text")
    ap.add_argument("--sample", action="store_true")
    args = ap.parse_args()

    if args.sample:
        # Sample mode uses a separate course so it never mixes with real state.
        added, total = ingest(SAMPLE_COURSE, SAMPLE_SOURCE, SAMPLE_TEXT)
        print(f"OK: added {added} chunks to {SAMPLE_COURSE} ({total} total). [sample]")
        return 0

    if not args.course or not args.source:
        print("ERROR: --course and --source are required (or use --sample).")
        return 2

    if args.file:
        try:
            with open(args.file) as f:
                text = f.read()
        except OSError as e:
            print(f"ERROR: could not read file: {e}")
            return 2
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("ERROR: no text to ingest.")
        return 2

    added, total = ingest(args.course, args.source, text)
    print(f"OK: added {added} chunks from '{args.source}' to {args.course} "
          f"({total} chunks total).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
