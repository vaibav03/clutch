# Clutch — a Cubbie Skill

**Your course material, turned into a personal exam coach that lives in your texts.**

Send Cubbie your slides, notes, photos of the board, and lecture recordings. Clutch
gathers them into a private knowledge base, then teaches, quizzes, and drills
you from *your own material* — citing the source every time — and (with your yes)
calls to wake you on exam morning. No API keys, no accounts beyond what you already
connect to Cubbie.

## Demo

See it in action: [`demo/index.html`](demo/index.html)

## Features

| Feature | What it does |
| --- | --- |
| **Ingest + knowledge base** | Reads Canvas files, slides, PDFs, photos and transcribed lectures into a private, per-course knowledge base. |
| **Teach + voice modes** | Explains any topic grounded in your material — in plain English, "like I'm 5", terse "exam-examiner" style, or hyped up. |
| **Adaptive quiz** | Fresh questions written from your material, with spaced repetition picking what to ask next. Optional nightly check-in. |
| **Mock exam** | A full, breadth-covering practice exam, optionally timed, with a graded scorecard and your weakest topics. |
| **Readiness** | A 🟢/🟡/🔴 report per topic so you know where to spend your last hour. |
| **Exam wake-up call** | A scheduled call on exam morning with your weakest topics — and a second call if you don't confirm you're up. |
| **Lecture deep-dive** | For a lecture video, pulls the slide/board frames that go *beyond* the posted slides and adds them to your notes. |
| **Progress + streaks** | Overall mastery %, chunks "locked in", study streak, and per-topic bars to keep you going. |
| **Export** | A Markdown study sheet (sendable as a PDF) and an Anki/Quizlet-importable flashcard CSV. |

Everything is grounded in the student's own material and cited back to the source.

## Install (for a student)

Text the GitHub repo link to Cubbie and ask it to install the Skill:

```
https://github.com/<your-username>/clutch
```

Cubbie clones the repo, reads `SKILL.md`, and the Skill is live from the next
message. The core study tools need no setup — they're Python standard library
only. Only the lecture deep-dive add-on needs a one-time install (Cubbie runs it
from `SKILL.md`):

```bash
python3 -m venv ~/.local/share/venvs/clutch && ~/.local/share/venvs/clutch/bin/pip install imageio-ffmpeg==0.5.1
```

## Scripts

All scripts live in `scripts/`. All are Python standard library only (no packages,
no network) except `lecture_frames.py`, which needs the ffmpeg add-on above.

| Script | What it does |
| --- | --- |
| `ingest.py` | Chunk a piece of text and add it to a course's knowledge base. |
| `search.py` | Rank and return the chunks most relevant to a topic (BM25). |
| `quiz.py` | `next` (pick due/new chunks), `record` (log right/wrong), `readiness` (per-topic 🟢/🟡/🔴). |
| `mock_exam.py` | `generate` (a broad, timed practice exam), `grade` (scorecard + weakest topics). |
| `stats.py` | `show` the progress dashboard — mastery %, locked-in count, streak, per-topic bars, due-today. |
| `export.py` | `sheet` (Markdown study sheet), `flashcards` (Anki/Quizlet-importable CSV). |
| `lecture_frames.py` | Extract key slide/board frames from a lecture video for Cubbie to read. |

State lives under `~/.local/share/clutch/<course>/` (or `$CLUTCH_HOME`).

## Test it (sample mode)

Every script has a `--sample` mode that uses a built-in `SAMPLE101` course and
never touches real state. Run from the Skill folder, `ingest.py --sample` first
(it seeds `SAMPLE101`):

```bash
python3 scripts/ingest.py --sample
python3 scripts/search.py --sample
python3 scripts/quiz.py next --sample
python3 scripts/quiz.py readiness --sample
python3 scripts/mock_exam.py generate --sample
python3 scripts/stats.py --sample
python3 scripts/export.py sheet --sample
python3 scripts/export.py flashcards --sample
~/.local/share/venvs/clutch/bin/python scripts/lecture_frames.py --sample
```

The `lecture_frames.py` sample generates a tiny test clip and extracts frames to
confirm ffmpeg is working.

## Academic integrity

Practice questions are generated new from the student's own material, and Cubbie
never completes graded work — it helps the student learn it.
