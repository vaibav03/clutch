#!/usr/bin/env python3
"""Search a course knowledge base and print the most relevant chunks.

Cubbie uses this to pull up course material before teaching or quizzing a
student. It reads the chunks that ingest.py wrote, ranks them against a query
with BM25 (stdlib only, no network, no API key), and prints the top matches so
Cubbie has grounded material to work from.

Usage:
  python3 scripts/search.py --course BIO201 --query "krebs cycle" --k 5
  python3 scripts/search.py --sample        # search the bundled sample, no args needed

Output: for each hit, a header line "[<id>] (<source>)" followed by the chunk
text (truncated), with a blank line between hits. Exit 0 on success (including
"no results"), exit 2 on a usage error (missing --course/--query when not
using --sample).
"""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter

BASE = os.environ.get("EXAM_MODE_HOME") or os.path.join(
    os.path.expanduser("~"), ".local", "share", "exam-mode"
)

# BM25 parameters (standard defaults).
K1 = 1.5
B = 0.75

# Keep output well under the 8000-char stdout budget.
MAX_CHARS_PER_CHUNK = 500

# A small English stopword set; dropped before ranking so common words do not
# dominate the score.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "he", "in", "is", "it", "its", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "will", "with", "about", "into", "than",
    "then", "they", "them", "these", "those", "there", "their", "but", "not",
    "no", "do", "does", "did", "so", "if", "we", "you", "your", "i", "me",
    "my", "our", "us", "which", "who", "what", "when", "where", "how", "why",
    "can", "could", "would", "should", "may", "might", "also", "such", "each",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def course_dir(course):
    """Return the course subfolder under BASE (slugged, not created here)."""
    return os.path.join(BASE, re.sub(r"[^A-Za-z0-9_-]", "_", course))


def tokenize(text):
    """Lowercase, keep alphanumeric words, drop stopwords."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


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
                continue  # skip a corrupt line rather than crash the search
            if "text" in rec:
                chunks.append(rec)
    return chunks, None


def bm25_rank(query, chunks, k):
    """Score chunks against the query with BM25 and return the top k.

    Returns a list of (chunk, score) with score > 0, highest first.
    """
    q_terms = tokenize(query)
    if not q_terms or not chunks:
        return []

    # Tokenize the corpus once; keep per-chunk term frequencies and lengths.
    doc_tokens = [tokenize(c["text"]) for c in chunks]
    doc_tfs = [Counter(toks) for toks in doc_tokens]
    doc_lens = [len(toks) for toks in doc_tokens]
    n_docs = len(chunks)
    avg_len = (sum(doc_lens) / n_docs) if n_docs else 0.0

    # Document frequency per query term (count distinct terms once).
    df = {}
    for term in set(q_terms):
        df[term] = sum(1 for tf in doc_tfs if term in tf)

    # Smoothed BM25 idf; max(0, ...) keeps near-universal terms from going
    # negative and dragging scores below zero.
    idf = {}
    for term, d in df.items():
        idf[term] = max(0.0, math.log((n_docs - d + 0.5) / (d + 0.5) + 1.0))

    scored = []
    for i, tf in enumerate(doc_tfs):
        dl = doc_lens[i]
        denom_norm = K1 * (1 - B + B * (dl / avg_len if avg_len else 0.0))
        score = 0.0
        for term in q_terms:
            f = tf.get(term, 0)
            if not f:
                continue
            score += idf[term] * (f * (K1 + 1)) / (f + denom_norm)
        if score > 0:
            scored.append((chunks[i], score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def format_hits(hits):
    """Render ranked hits to a string within the stdout budget."""
    parts = []
    for chunk, _score in hits:
        cid = chunk.get("id", "?")
        source = chunk.get("source", "unknown")
        text = chunk.get("text", "").strip()
        if len(text) > MAX_CHARS_PER_CHUNK:
            text = text[:MAX_CHARS_PER_CHUNK].rstrip() + "..."
        parts.append(f"[{cid}] ({source})\n{text}")
    return "\n\n".join(parts)


def run_search(course, query, k):
    """Load, rank, and print. Always returns exit code 0."""
    chunks, err = load_chunks(course)
    if err:
        print(err)
        return 0
    hits = bm25_rank(query, chunks, k)
    if not hits:
        print("No matching material found.")
        return 0
    print(format_hits(hits))
    return 0


SAMPLE_COURSE = "SAMPLE101"
SAMPLE_QUERY = "krebs cycle"


def main():
    ap = argparse.ArgumentParser(
        description="Search a course knowledge base with BM25 and print the "
                    "most relevant chunks."
    )
    ap.add_argument("--course", help="Course name (slugged to a subfolder).")
    ap.add_argument("--query", help="The search query text.")
    ap.add_argument("--k", type=int, default=5,
                    help="Number of chunks to return (default 5).")
    ap.add_argument("--sample", action="store_true",
                    help="Search the bundled SAMPLE101 course for a fixed "
                         "query (no other args needed).")
    args = ap.parse_args()

    k = args.k if args.k and args.k > 0 else 5

    if args.sample:
        # A dry sample run must never error hard: if the sample has not been
        # ingested, say so clearly and exit 0.
        path = os.path.join(course_dir(SAMPLE_COURSE), "chunks.jsonl")
        if not os.path.exists(path):
            print(f"No sample knowledge base yet. "
                  f"Run 'python3 scripts/ingest.py --sample' first.")
            return 0
        return run_search(SAMPLE_COURSE, SAMPLE_QUERY, k)

    if not args.course or not args.query:
        print("ERROR: --course and --query are required (or use --sample).")
        return 2

    return run_search(args.course, args.query, k)


if __name__ == "__main__":
    sys.exit(main())
