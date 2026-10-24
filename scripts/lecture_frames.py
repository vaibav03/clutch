#!/usr/bin/env python3
"""Extract key video frames from a lecture recording for the "exam-mode" Cubbie Skill.

Cubbie can transcribe a lecture's AUDIO, but it cannot see the video: slides,
whiteboard/blackboard writing, diagrams, and equations are invisible to an
audio-only transcript. This script bridges that gap. It uses ffmpeg to pull out
the visually distinct frames of a lecture video and saves them as JPEG images.

This script does NOT call Cubbie and does NOT do any AI itself. It only extracts
frames. Afterward, Cubbie READS each saved frame image with its own vision
ability and writes notes that fill the gaps the audio transcript missed
(on-screen equations, slide bullet points, board diagrams, and so on).

Extraction modes:
  - Default: scene-change detection. ffmpeg keeps a frame whenever the picture
    changes by more than a threshold, which lines up well with slide changes.
  - ``--interval N``: grab one frame every N seconds instead.

Output frames land under the exam-mode state directory:
    <state>/<course-slug>/frames/<source-slug>/frame_0001.jpg

Setup (only if ffmpeg is missing):  pip install imageio-ffmpeg
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Keep stdout well under the 8000-char budget: show at most this many paths.
MAX_PRINTED_PATHS = 40


def find_ffmpeg() -> str | None:
    """Locate an ffmpeg executable, preferring explicit config, then the
    bundled static build, then whatever is on PATH. Returns None if none found."""
    # 1. Explicit override via environment variable.
    env_ffmpeg = os.environ.get("EXAM_MODE_FFMPEG")
    if env_ffmpeg and Path(env_ffmpeg).exists():
        return env_ffmpeg

    # 2. The static ffmpeg bundled with imageio-ffmpeg, if that package is installed.
    try:
        import imageio_ffmpeg  # type: ignore

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except Exception:
        pass

    # 3. A system ffmpeg on PATH.
    return shutil.which("ffmpeg")


def install_hint() -> str:
    return (
        "ffmpeg was not found. Run the Setup command to install a bundled copy:\n"
        "    pip install imageio-ffmpeg"
    )


def slugify(value: str) -> str:
    """Turn an arbitrary label into a safe folder name."""
    slug = re.sub(r"[^A-Za-z0-9_-]", "_", value.strip())
    return slug or "untitled"


def state_home() -> Path:
    """Root directory where exam-mode keeps its data."""
    env_home = os.environ.get("EXAM_MODE_HOME")
    if env_home:
        return Path(env_home).expanduser()
    return Path.home() / ".local" / "share" / "exam-mode"


def frames_dir(course: str, source: str) -> Path:
    """<state>/<course-slug>/frames/<source-slug>/"""
    return state_home() / slugify(course) / "frames" / slugify(source)


def run_ffmpeg(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run ffmpeg quietly and return the completed process."""
    return subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def list_frames(out_dir: Path) -> list[Path]:
    return sorted(out_dir.glob("frame_*.jpg"))


def vfr_flag(ffmpeg: str) -> list[str]:
    """Return the ffmpeg flag that writes variable-frame-rate output.

    Scene-change selection drops frames, so the output must be VFR or ffmpeg
    would duplicate frames to keep a constant rate. Modern ffmpeg (5.1+) spells
    this ``-fps_mode vfr``; older builds use the now-removed ``-vsync vfr``. We
    prefer ``-fps_mode`` when the build advertises it and fall back otherwise.
    """
    try:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-h", "full"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if "-fps_mode" in result.stdout:
            return ["-fps_mode", "vfr"]
    except Exception:
        pass
    return ["-vsync", "vfr"]


def extract_frames(
    ffmpeg: str,
    video: Path,
    out_dir: Path,
    *,
    threshold: float,
    interval: float | None,
    max_frames: int,
) -> tuple[list[Path], bool]:
    """Extract frames from ``video`` into ``out_dir``.

    Returns (frame_paths, capped) where ``capped`` indicates output was limited
    by ``max_frames``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clear any stale frames from a previous run so counts stay accurate.
    for stale in list_frames(out_dir):
        stale.unlink()

    # Append a pixel-format conversion so the MJPEG encoder always gets a
    # format it accepts (some sources emit full-range YUV, which otherwise
    # errors out when writing JPEGs).
    fmt = "format=yuvj420p"

    if interval is not None:
        # One frame every N seconds.
        vf = f"fps=1/{interval},{fmt}"
        sync_args: list[str] = []
    else:
        # Scene-change detection: keep frames whose scene score exceeds threshold.
        # VFR output is required so dropped frames are not re-duplicated.
        vf = f"select='gt(scene,{threshold})',{fmt}"
        sync_args = vfr_flag(ffmpeg)

    pattern = str(out_dir / "frame_%04d.jpg")
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vf",
        vf,
        *sync_args,
        # Cap frames at the ffmpeg level so a long lecture stays light. Request
        # one extra so we can tell whether the cap actually clipped anything.
        "-frames:v",
        str(max_frames + 1),
        "-q:v",
        "3",
        pattern,
    ]

    result = run_ffmpeg(cmd)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}):\n{result.stdout.strip()}"
        )

    frames = list_frames(out_dir)

    capped = False
    if len(frames) > max_frames:
        capped = True
        for extra in frames[max_frames:]:
            extra.unlink()
        frames = frames[:max_frames]

    return frames, capped


def print_result(frames: list[Path], out_dir: Path, capped: bool) -> None:
    """Print the frame count and paths, staying under the stdout budget."""
    print(f"Extracted {len(frames)} frame(s).")
    if capped:
        print(
            f"Note: output was capped at {len(frames)} frames "
            "(more scene changes were detected). Use --max-frames to raise the cap."
        )
    print(f"Frames directory: {out_dir}")

    if len(frames) > MAX_PRINTED_PATHS:
        print(f"Showing the first {MAX_PRINTED_PATHS} of {len(frames)} paths:")
        shown = frames[:MAX_PRINTED_PATHS]
    else:
        shown = frames

    for frame in shown:
        print(frame)


def run_sample(ffmpeg: str | None) -> int:
    """Generate a tiny test video and extract frames from it.

    This must never hard-fail: if ffmpeg is missing we print the install hint
    and still exit 0 so the Skill's self-check stays green.
    """
    if ffmpeg is None:
        print(install_hint())
        print("(Sample skipped because ffmpeg is unavailable.)")
        return 0

    print(f"Using ffmpeg: {ffmpeg}")

    with tempfile.TemporaryDirectory(prefix="exam-mode-sample-") as tmp:
        tmp_path = Path(tmp)
        sample_video = tmp_path / "testsrc.mp4"

        # Generate a 3-second synthetic clip with ffmpeg's built-in test source.
        gen_cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=3:size=320x240:rate=10",
            str(sample_video),
        ]
        gen = run_ffmpeg(gen_cmd)
        if gen.returncode != 0:
            print("Failed to generate the sample video:")
            print(gen.stdout.strip())
            return 0  # sample must never hard-fail

        out_dir = tmp_path / "frames"
        try:
            frames, capped = extract_frames(
                ffmpeg,
                sample_video,
                out_dir,
                threshold=0.3,
                interval=1.0,  # one frame per second of the 3s clip
                max_frames=40,
            )
        except RuntimeError as exc:
            print("Sample extraction failed:")
            print(str(exc))
            return 0  # sample must never hard-fail

        print_result(frames, out_dir, capped)
        print("Sample OK: ffmpeg is working and frames were extracted.")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract key lecture video frames (slides, board writing, equations) "
            "so Cubbie can read them and fill gaps the audio transcript missed."
        )
    )
    parser.add_argument("--course", help="Course name (becomes a folder slug).")
    parser.add_argument(
        "--source", help="Label for this recording (becomes a folder slug)."
    )
    parser.add_argument("--video", help="Path to the lecture video file.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Scene-change sensitivity, 0-1 (default 0.3). Lower = more frames.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Grab one frame every N seconds instead of using scene detection.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=40,
        help="Cap on frames written (default 40) to keep long lectures light.",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Generate a tiny test video, extract frames from it, and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    ffmpeg = find_ffmpeg()

    # --sample is a self-check and handles its own ffmpeg-missing case (exit 0).
    if args.sample:
        return run_sample(ffmpeg)

    # Every other mode requires ffmpeg.
    if ffmpeg is None:
        print(install_hint())
        return 2

    # Validate required arguments.
    missing = [
        name
        for name, value in (
            ("--course", args.course),
            ("--source", args.source),
            ("--video", args.video),
        )
        if not value
    ]
    if missing:
        print(f"error: missing required argument(s): {', '.join(missing)}")
        print("usage: --course <name> --source <label> --video <path>")
        return 2

    video = Path(args.video).expanduser()
    if not video.exists():
        print(f"error: video file not found: {video}")
        return 2

    if args.interval is not None and args.interval <= 0:
        print("error: --interval must be greater than 0")
        return 2
    if args.max_frames <= 0:
        print("error: --max-frames must be greater than 0")
        return 2

    out_dir = frames_dir(args.course, args.source)

    try:
        frames, capped = extract_frames(
            ffmpeg,
            video,
            out_dir,
            threshold=args.threshold,
            interval=args.interval,
            max_frames=args.max_frames,
        )
    except RuntimeError as exc:
        print(f"error: {exc}")
        return 2

    print_result(frames, out_dir, capped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
