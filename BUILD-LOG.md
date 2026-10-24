# Clutch — build log & tracker

Flagship Cubbie Skill: ingest course materials → sandbox knowledge base → teach → adaptive quiz → readiness → exam wake-up call. MVP first. Sandbox-only (no API keys). NOT to be published — local only until the user says otherwise.

## Shared contract (all scripts must follow)

- Python 3.12, **stdlib only** (no pip installs for MVP), no network.
- State dir: `$CLUTCH_HOME` or `~/.local/share/clutch/<course_slug>/` (slug = non-alphanumerics → `_`).
- Every script has a `--sample` mode using course `SAMPLE101`, never touching real state.
- Keep stdout < 8000 chars (Cubbie truncates). Exit 0 = ok, 2 = usage error.
- Scripts CANNOT call Cubbie. Cubbie passes text in; scripts print what Cubbie needs next.

### Data files
- `chunks.jsonl` — one per line: `{"id": str, "source": str, "text": str}`
- `mastery.json` — `{"items": {id: {"box": 0..5, "seen": int, "correct": int, "last_asked": "YYYY-MM-DD"|null, "next_due": "YYYY-MM-DD"}}, "updated": "YYYY-MM-DD"}`
  - Leitner intervals (days) by box: [0,1,3,7,16,35]. Right → box+1 (max 5). Wrong → box 0.

### Script interfaces
- `ingest.py --course --source (--file|--text|stdin) | --sample` ✅ DONE
- `search.py --course --query [--k 5] | --sample` → prints top chunks `[id] (source)\ntext`
- `quiz.py next --course [--n 5] | --sample` → prints due/new chunk ids + source + text (Cubbie writes the questions)
- `quiz.py record --course --item <id> --result right|wrong` → updates mastery, short confirm
- `quiz.py readiness --course | --sample` → per-source 🟢/🟡/🔴 + weakest topics

## Task tracker

| # | Task | Owner | Status |
|---|------|-------|--------|
| 1 | `scripts/ingest.py` | me | ✅ done |
| 2 | `scripts/search.py` (BM25) | subagent A | ✅ done, sample passes |
| 3 | `scripts/quiz.py` (next/record/readiness) | subagent B | ✅ done, sample passes |
| 4 | `SKILL.md` + `README.md` | subagent C | ✅ done, frontmatter valid, cmds verified |
| 4b | `scripts/lecture_frames.py` (ffmpeg scene-change) | subagent D | ✅ done, sample passes (ffmpeg found) |
| 5 | Validate (kit validator) + sample runs of all scripts | me | ✅ PASS — validator OK, no warnings; full e2e works |
| 6 | Demo checklist for testing on real Cubbie | me | ✅ done → DEMO-CHECKLIST.md |

## STATUS: MVP + feature pack complete & validated. Private repo: github.com/vaibav03/clutch (pushed).

## Feature pack (added after MVP, subagent-built, all tested)
| Piece | What | Status |
|---|---|---|
| `scripts/mock_exam.py` | breadth-covering timed mock exam (generate/grade) | ✅ |
| `scripts/stats.py` | gamified progress: mastery %, streak, per-topic bars | ✅ |
| `scripts/export.py` | study sheet (MD) + Anki/Quizlet flashcards (CSV) | ✅ |
| `evals/evals.json` | 6-scenario self-test (kit schema) | ✅ |
| `demo/index.html` | premium mock-iMessage product demo page (video target) | ✅ QA'd in browser |
| `SKILL.md` + `README.md` | integrated all features + teaching voice modes | ✅ validator OK |
| `VIDEO.md` | premium narration + demo-video run steps (user runs; needs ElevenLabs key) | ✅ |

Validator: `OK clutch` (only an informational "uncommitted changes" note, cleared on commit).
Next: test on a real Cubbie (DEMO-CHECKLIST.md); make the video (VIDEO.md); flip repo public to install/submit.

## Lecture add-on (phase 4) — refined per user
ffmpeg extracts scene-change frames → Cubbie reads each frame (vision) in a background task, batches → compares to slides already in KB → KEEPS ONLY frames with content not in slides (board work, live annotations, demos) → turns those + transcript into notes → ingests as source "<lecture> - lecture notes". Note: a Skill can't control Cubbie's internal subagents; SKILL.md requests background/batch processing instead.

## MVP scope
Phases ingest + teach (search) + adaptive quiz + readiness + wake-up (plain words in SKILL.md, no script). ffmpeg slide-frame extraction = post-MVP add-on. mem0 = not in MVP.

## Log
- Created folders, wrote ingest.py (chunks.jsonl format fixed), wrote this tracker. Launching subagents A/B/C in parallel.
