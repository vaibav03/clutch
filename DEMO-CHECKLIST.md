# exam-mode — test on a real Cubbie (phone checklist)

First publish the repo (your call — currently local/unpublished) and text its branch link to your own Cubbie.
Then walk these on your phone. Fill in a real course tag (e.g. BIO201) and one real set of slides/notes.

| # | Text Cubbie | Expect |
|---|---|---|
| 1 | The repo/branch link | Cubbie says what it's about to fetch and asks first (third-party code) |
| 2 | "yes" | Fetches the Skill, copies it in, reads SKILL.md. Core needs no packages |
| 3 | "set up BIO201 for my midterm" + send a slide PDF / snap notes | Cubbie reads them and ingests; says what's in your study set |
| 4 | "teach me <topic from those slides>" | Explains in plain words, **cites the source** (e.g. "from slide 14"), grounded in your material |
| 5 | A follow-up as a **voice note** | Transcribes it and answers from the same material |
| 6 | "quiz me on BIO201" | Asks one question per text from your material; grades; adapts next time |
| 7 | "am I ready?" | 🟢/🟡/🔴 per topic + "spend your last hour on X" |
| 8 | "wake me before my exam" → give/confirm the exam time | Asks first, then schedules a **call** on exam morning with weak topics |
| 9 | (next day) start a new chat, "quiz me again" | Remembers your past results; harder on what you knew, back to what you missed |
| 10 | (add-on) send a lecture **video**, after Setup install | Transcribes audio + extracts frames; keeps only board/annotation content not in slides; notes it |

## Two things to confirm (unknowns in the docs)
- **Does Cubbie hand a sent file's path to a script?** Needed for ingest/lecture_frames on files you text. If not, fall back to Cubbie reading the file and passing `--text`.
- **Are phone calls interactive?** Not needed for the wake-up (it calls, you confirm by text), but confirms the ceiling for a future live-quiz call.

## Setup note for the lecture add-on
Core (ingest/search/quiz) = stdlib, no install. Lecture frames needs, once:
`pip install imageio-ffmpeg==0.5.1` into a venv under HOME (the SKILL.md Setup section has the exact command).

When something fails: fix locally, re-run `python3 ../cubbie-hackathon-kit/skills/cubbie-skill-creator/scripts/validate_cubbie_skill.py .` and the sample commands, then re-text the link.
