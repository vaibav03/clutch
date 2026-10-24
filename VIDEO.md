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

## 4. Narration script (~160 words, ~70s — first person, natural)

> It's 11pm. Exam's at 9. Five lectures I never rewatched. I'm cooked.
> So I texted Clutch. It pulled my slides and lectures straight from Canvas and built a
> study set out of my actual class. I asked it to explain the Krebs cycle — and it
> taught me from my own slides, and told me exactly which slide it came from.
> Then it started quizzing me. Whatever I missed, it brought back sooner — right when
> I thought I was free. Around 1am I asked, "am I ready?" It didn't sugarcoat it:
> green, green, red. So my last hour went straight to the red one.
> And then exam morning — it actually called me. Woke me up and ran my three weak
> spots one last time. It won't do your homework. It just makes sure you pull it off.
> That's Clutch.

On-screen hook (first 3 seconds): **"11pm. exam at 9. i'm cooked."** → cut to Clutch.
End card: **Clutch ⚡ — for when the exam's tomorrow.**

Scene cues (match the page scenes): "I'm cooked" hook, then the hero on "texted Clutch" → "pulled my slides… from Canvas" on scene 1 → "taught me from my own slides" on scene 2 → "started quizzing me" on scene 3 → "am I ready?… green, green, red" on scene 4 → "actually called me" on scene 5 → end card.

## 5. Deliver
Output lands at `demo-video/renders/final.mp4` (1080p, 30fps). Post it, then add the link to your hackathon submission (up to 5 extra social posts count too).
