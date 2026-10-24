# Clutch — premium demo video (how to produce it)

The `demo-video` skill (in your `vaibav03/hackathon-skills` repo) turns a URL into a narrated, premium product video (ElevenLabs voice, ducked CC-BY music, camera/cursor on the words). It's `disable-model-invocation: true` and key-gated, so **you run it** — here's everything prepped.

A Track 1 video is **optional**; it only adds to your vote score if you post it (TikTok/Instagram).

## 1. One-time setup
- Node 24+, `ffmpeg` + `ffprobe` on PATH (you have ffmpeg).
- ElevenLabs key: put `ELEVENLABS_API_KEY=...` in `~/.config/demo-video/.env` (elevenlabs.io → Developers → API Keys). Free plan ~10k chars/month; one take ≈ 1,100.
- Install the plugin if it isn't already:
  `/plugin marketplace add vaibav03/hackathon-skills` then `/plugin install hackathon@hackathon-skills`

## 2. Serve the demo page (the recording target)
```bash
cd /Users/vaibav/Documents/projects/devhacks/exam-mode/demo
python3 -m http.server 8777
```
The page is at `http://localhost:8777/index.html`.

## 3. Make the video
```
/hackathon:demo-video http://localhost:8777/index.html
```
- Preview free first with `--dry-voice`, QA the contact sheet, then record once.
- When it asks for the script, use the draft below (or let it write one and tweak).

## 4. Premium narration draft (~165 words, ~70s — first person, natural)

> Okay — finals week. Five lectures, a stack of slides, no idea where to start.
> This is Clutch. You just text it your slides and your lecture recordings, and it
> quietly builds a study set out of your actual class. Then you can ask it anything —
> "explain the Krebs cycle" — and it teaches you from your own slides, and tells you
> exactly which one it pulled from. Honestly, the part I like most is it quizzes you on
> its own. A question shows up mid-day, you answer, and whatever you miss comes back
> sooner. The night before, you ask "am I ready?" and it's blunt about it — green,
> green, red — so your last hour goes where it counts. And then, exam morning? It
> actually calls you. Wakes you up, runs your three weak spots one more time. It
> coaches you — it never does the graded work for you. That's Clutch.

Scene cues (match the page scenes): intro on the hero → "text it your slides" on scene 1 → "teaches you… slide" on scene 2 → "quizzes you" on scene 3 → "am I ready… green green red" on scene 4 → "actually calls you" on scene 5 → end card.

## 5. Deliver
Output lands at `demo-video/renders/final.mp4` (1080p, 30fps). Post it, then add the link to your hackathon submission (up to 5 extra social posts count too).
