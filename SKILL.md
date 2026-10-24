---
name: exam-mode
description: Turns a student's course materials into a personal exam coach — use when a student is studying for an exam, wants to learn or review a topic, asks for a practice quiz, or needs an exam wake-up call. It grounds every explanation and quiz question in the student's own notes, slides and lecture recordings, and uses spaced repetition, so it adds material-based teaching and practice that the built-in study-plan-builder does not.
---

# Exam Mode

A study coach built on the student's own course material. Cubbie gathers the
material into a private sandbox knowledge base, teaches from it, runs adaptive
quizzes, tracks how ready the student is, and (with their yes) calls to wake them
on exam morning.

## When to use

- "Help me study for my BIO 201 midterm."
- "Teach me the Krebs cycle." / "Quiz me on chapter 5."
- "Am I ready for the exam?" / "Wake me up before my exam."
- The student sends notes, slides, a photo of the board, or a lecture recording
  and wants to study from it.

Use the built-in `study-plan-builder` instead when the student just wants a
day-by-day schedule and no material-based teaching or quizzing.

## Academic integrity (always)

- Generate NEW practice questions from the student's own material. Never reuse
  the text of a graded assignment, quiz or exam as a question.
- Never answer, solve or complete graded work for the student. Teaching them to
  understand it is fine; doing it for them is not.
- Ground every explanation in the material the scripts return. Cite the source
  (for example "slide 14" or "Lecture 3"). Do not invent the professor's content.

## Replies

Keep each reply to a few short lines, plain text, no Markdown symbols. One idea
per message. Lead with the answer. Put any link on its own line. Anything long (a
full study guide, a readiness report) goes in a document with a one-line summary
in the text. Ask one question at a time and suggest a default the student can
accept with "yes". Never send, schedule or call without the student's yes first.

## Setup

The core study tools (ingest, search, quiz) are Python standard library only —
no packages to install. Run them with the system `python3` from this Skill's
folder.

The lecture deep-dive add-on (phase 4) needs ffmpeg. Install a bundled copy once
into a virtual environment under HOME, which Cubbie keeps:

```bash
python3 -m venv ~/.local/share/venvs/exam-mode && ~/.local/share/venvs/exam-mode/bin/pip install imageio-ffmpeg==0.5.1
```

Run the lecture frame tool with that environment's Python (so it finds the
bundled ffmpeg):

```bash
~/.local/share/venvs/exam-mode/bin/python scripts/lecture_frames.py ...
```

If `~/.local/share/venvs/exam-mode/bin/python` is missing later, run the install
command again.

Use a short course tag for `<COURSE>` (for example `BIO201`); use the same tag
every time for the same class so its material stays together.

## Steps

### Phase 1 — Set up the course (gather material)

1. Decide the course tag with the student (for example `BIO201`).
2. Collect the material. For each piece:
   - Read the student's Canvas course files, slides, pages and readings. If
     Canvas is not connected, ask the student to connect it or to send the
     material directly, then continue with whatever you have.
   - Read any PDFs, notes or photos (such as a photo of the whiteboard) the
     student sends.
   - Transcribe any lecture recording or voice note the student sends to plain
     text.
3. Pass each piece's text to the knowledge base, one run per source, with a clear
   label for where it came from:

   ```bash
   python3 scripts/ingest.py --course <COURSE> --source "<label>" --file <path>
   ```

   Use `--text "<text>"` instead of `--file` when you already have the text
   (for example a transcript). The label is what gets cited later, so make it
   specific: "Slides Ch5", "Lecture 3", "Syllabus".
4. Tell the student what is now in their study set and offer to teach or quiz.

### Phase 2 — Teach a topic

1. When the student asks to learn or review something, pull up the relevant
   material:

   ```bash
   python3 scripts/search.py --course <COURSE> --query "<topic>"
   ```

2. Explain the returned chunks in plain language, in a few short texts. Cite the
   source for each point (for example "from slide 14"). Stay grounded in what the
   search returned — do not add content the professor did not cover.
3. Follow-up questions (typed or sent as a voice note) use the same search.
   Transcribe a voice note first, then search for its topic.

### Phase 3 — Adaptive quiz

1. Get the chunks that are due or new to quiz:

   ```bash
   python3 scripts/quiz.py next --course <COURSE>
   ```

   The output lists each chunk with its id and source, and ends with an `IDS:`
   line. The script picks what is due and spaces it out — you just ask and record.
2. For each chunk, WRITE one fresh question from that chunk's content and send it
   as its own short text. Wait for the student's answer.
3. Grade the answer against the chunk, briefly tell the student right or wrong
   and why, then record it using that chunk's id:

   ```bash
   python3 scripts/quiz.py record --course <COURSE> --item <ID> --result right|wrong
   ```

4. Offer a recurring check-in quiz. Ask what time and how often ("A quick nightly
   quiz at 8 pm?"), and only after the student says yes, set a scheduled check-in
   that runs the quiz again at that time.

### Phase 4 — Lecture deep-dive (add-on; needs the Setup install)

Use this when the student sends a lecture VIDEO.

1. Transcribe the video's audio to plain text.
2. Extract the key slide/board frames from the video:

   ```bash
   ~/.local/share/venvs/exam-mode/bin/python scripts/lecture_frames.py --course <COURSE> --source "<label>" --video <path>
   ```

   It prints how many frames it saved and their file paths.
3. As a background task, work through the saved frames in batches. Read each
   frame image and compare it to the slide material already in the knowledge
   base. Keep ONLY frames whose content is not already in the slides — things
   written on the board, live annotations, worked examples, demos.
4. Turn those net-new captures plus the transcript into concise notes and add
   them to the knowledge base:

   ```bash
   python3 scripts/ingest.py --course <COURSE> --source "<label> - lecture notes" --file <path>
   ```

   Then tell the student, in a line or two, what the lecture added beyond the
   slides.

### Phase 5 — Readiness and exam wake-up

1. Check readiness per topic:

   ```bash
   python3 scripts/quiz.py readiness --course <COURSE>
   ```

   It prints a 🟢/🟡/🔴 per source and the weakest topics. Turn that into one plain
   suggestion, for example "Spend your last hour on the electron transport chain —
   that's your weakest topic."
2. For the wake-up call, find the exam date and time (from Canvas or by asking the
   student) and remember it. Confirm it back to the student.
3. Offer the wake-up call and, only after the student says yes, set a scheduled
   check-in that calls the student on exam morning with their weakest topics, and
   calls again if they do not confirm they are up.

## When something fails

- Canvas not connected: tell the student Canvas isn't connected, ask them to
  connect it or send the material directly, and keep going with what you have.
- No material ingested yet (a search or quiz says there's no knowledge base):
  tell the student you need their notes/slides first, and run phase 1.
- A script errors or returns nothing useful: say that part didn't work and offer
  to try again; never make up the material, a question, or a readiness score.
- ffmpeg not installed (the lecture tool asks for it): run the Setup install
  command above, then try the lecture step again.
