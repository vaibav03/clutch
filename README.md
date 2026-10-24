# Clutch ⚡

### For when the exam's tomorrow and you still need to pull it off.

**Clutch turns your own course material into an exam coach that lives in your texts.**
It teaches you from your slides, quizzes you until it sticks, tells you exactly
where you stand — and calls your phone on exam morning so you actually show up.

> *"8am exam. alarm: ignored. second alarm: snoozed. Cubbie CALLING my phone like
> my mom when rent's due: not ignorable."*

A Cubbie Skill. No API keys, no new accounts, no app to download.

---

## How it works

1. **Send it everything.** Slides, PDFs, notes, a photo of the whiteboard, a lecture
   recording — or just let it pull your files from Canvas.
2. **Get taught back.** Ask about any topic and Clutch explains it from *your*
   material, citing the exact slide or lecture every time.
3. **Get quizzed.** Fresh questions written from your notes, with spaced repetition
   bringing back the one you got wrong three days ago — right when you thought you
   were free.
4. **Know where you stand.** 🔴 → 🟡 → 🟢 per topic, so your last hour goes where it
   counts.
5. **Wake up ready.** On exam morning, Clutch calls you with your weakest topics. Don't
   confirm you're up? It calls again.

**From red to ready.**

## Demo

See it in action: [`demo/index.html`](demo/index.html)

## What's inside

| Feature | What it does |
| --- | --- |
| **Your own knowledge base** | Reads Canvas files, slides, PDFs, photos and transcribed lectures into a private, per-course knowledge base. |
| **Teach me, your way** | Explains any topic from your material — in plain English, "like I'm 5", terse examiner style, or hyped up. |
| **Adaptive quiz** | New questions from your material, with spaced repetition choosing what to ask next. Optional nightly check-in. |
| **Mock exam** | A full practice exam covering the whole syllabus, optionally timed, with a graded scorecard and your weakest topics. |
| **"Am I ready?"** | A 🟢/🟡/🔴 readiness report per topic. |
| **Exam wake-up call** | A scheduled call on exam morning with your weakest topics, plus a second call if you don't confirm you're up. |
| **Lecture deep-dive** | Pulls the slide and board frames from a lecture video that go *beyond* the posted slides and adds them to your notes. |
| **Streaks + mastery** | Overall mastery %, topics locked in, study streak, and per-topic progress bars. |
| **Take it with you** | A Markdown study sheet (sendable as a PDF) and a flashcard CSV you can import into Anki or Quizlet. |

Every answer is grounded in your material and cited back to the source. No made-up
lecture content.

## Install

Text this link to Cubbie and ask it to install the Skill:

```
https://github.com/vaibav03/clutch
```

That's it. Cubbie clones the repo, reads `SKILL.md`, and Clutch is live from your next
message. The core study tools need zero setup (Python standard library only). Only
the lecture deep-dive add-on needs a one-time install, which Cubbie runs for you from
`SKILL.md`:

```bash
python3 -m venv ~/.local/share/venvs/clutch && ~/.local/share/venvs/clutch/bin/pip install imageio-ffmpeg==0.5.1
```

## For developers

### Scripts

All scripts live in `scripts/`. All are Python standard library only (no packages,
no network) except `lecture_frames.py`, which needs the ffmpeg add-on above.

| Script | What it does |
| --- | --- |
| `ingest.py` | Chunk a piece of text and add it to a course's knowledge base. |
| `search.py` | Rank and return the chunks most relevant to a topic (BM25). |
| `quiz.py` | `next` (pick due/new chunks), `record` (log right/wrong), `readiness` (per-topic 🟢/🟡/🔴). |
| `mock_exam.py` | `generate` (a broad, timed practice exam), `grade` (scorecard + weakest topics). |
| `stats.py` | `show` the progress dashboard: mastery %, locked-in count, streak, per-topic bars, due today. |
| `export.py` | `sheet` (Markdown study sheet), `flashcards` (Anki/Quizlet-importable CSV). |
| `lecture_frames.py` | Extract key slide/board frames from a lecture video for Cubbie to read. |

State lives under `~/.local/share/clutch/<course>/` (or `$CLUTCH_HOME`).

### Test it (sample mode)

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

## It won't do your homework

Clutch writes **new** practice questions from your own material and never completes
graded work for you. It'll call you at 7am and drill you until you're green, but the
A is yours to earn.
