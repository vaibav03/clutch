# Exam Mode — a Cubbie Skill

Exam Mode turns a student's own course material into a personal exam coach that
lives in their iMessage. Cubbie gathers the material into a private sandbox
knowledge base, teaches from it, runs adaptive quizzes, tracks readiness, and
(with the student's yes) calls to wake them on exam morning. Everything stays on
the student's own sandbox — no API keys, no accounts beyond the ones they already
connect to Cubbie.

## What it does (the phases)

1. **Set up a course** — Cubbie reads Canvas files, slides and pages, reads PDFs
   and photos the student sends, and transcribes lecture recordings, then feeds
   each one into the course knowledge base.
2. **Teach** — the student asks to learn a topic; Cubbie pulls the relevant
   material and explains it in plain language, citing the source.
3. **Adaptive quiz** — Cubbie writes fresh questions from the material and records
   results; a spaced-repetition engine decides what to ask next. Optional nightly
   check-in quiz.
4. **Lecture deep-dive** (add-on) — for a lecture video, Cubbie transcribes the
   audio, extracts key slide/board frames, keeps only what the slides didn't
   already cover, and adds concise notes to the knowledge base.
5. **Readiness + exam wake-up** — a 🟢/🟡/🔴 readiness report per topic, plus a
   scheduled call that wakes the student on exam morning with their weakest topics.

Academic integrity is built in: questions are generated new from the student's
own material, and Cubbie never completes graded work — it helps the student learn.

## Install (for a student)

Text the GitHub repo link to Cubbie and ask it to install the Skill:

```
https://github.com/<your-username>/exam-mode
```

Cubbie clones the repo, reads `SKILL.md`, and the Skill is available from the next
message. The core study tools need no setup. The lecture deep-dive add-on needs a
one-time install (Cubbie runs it from `SKILL.md`):

```bash
python3 -m venv ~/.local/share/venvs/exam-mode && ~/.local/share/venvs/exam-mode/bin/pip install imageio-ffmpeg==0.5.1
```

## Scripts

All scripts live in `scripts/`. The first three are Python standard library only
(no packages, no network); the fourth needs the ffmpeg add-on above.

| Script | What it does |
| --- | --- |
| `ingest.py` | Chunk a piece of text and add it to a course's knowledge base. |
| `search.py` | Rank and return the chunks most relevant to a topic (BM25). |
| `quiz.py` | `next` (pick due/new chunks), `record` (log right/wrong), `readiness` (per-topic 🟢/🟡/🔴). |
| `lecture_frames.py` | Extract key slide/board frames from a lecture video for Cubbie to read. |

State lives under `~/.local/share/exam-mode/<course>/` (or `$EXAM_MODE_HOME`).

## Test it (sample mode)

Every script has a `--sample` mode that uses a built-in `SAMPLE101` course and
never touches real state. Run from the Skill folder:

```bash
python3 scripts/ingest.py --sample
python3 scripts/search.py --sample
python3 scripts/quiz.py next --sample
python3 scripts/quiz.py readiness --sample
~/.local/share/venvs/exam-mode/bin/python scripts/lecture_frames.py --sample
```

`ingest.py --sample` first (it seeds `SAMPLE101`), then search/quiz/readiness
will have material to work with. The `lecture_frames.py` sample generates a tiny
test clip and extracts frames to confirm ffmpeg is working.
