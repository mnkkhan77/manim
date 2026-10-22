#!/usr/bin/env python
"""
add_background_video.py

Standalone utility to composite an already-rendered manim video (with an
alpha/transparent background, produced by rendering interview_simulation.py
with manim's -t/--transparent flag and gui_config.json's "background_video"
key set, see AGENTS.md) on top of a user-chosen looping background video.
Companion to add_background_music.py and burn_subtitles.py - same CLI shape,
same conventions.

Usage:
    venv/Scripts/python.exe add_background_video.py <foreground.mov> <background_video> \
        [--output path] [--loop | --no-loop]

<foreground.mov> - manim's transparent-background output (.mov with an
    alpha-bearing pixel format, e.g. argb/yuva420p - rendered with -t).
<background_video> - any video file ffmpeg can read, used as the backdrop
    behind the foreground's Q&A content.

If --output is omitted, it defaults to "<foreground_name>_with_bg_video.mp4"
next to the input foreground video.

--loop (default) repeats the background video to fill the whole foreground's
    duration if it's shorter. --no-loop plays it once; if it's shorter than
    the foreground the remainder is held on its last frame - the output
    duration always matches the foreground video exactly either way.

The foreground's own audio track (narration) is preserved unchanged; the
background video's audio (if any) is discarded.

Examples:
    venv/Scripts/python.exe add_background_video.py out.mov office_loop.mp4
    venv/Scripts/python.exe add_background_video.py out.mov office_loop.mp4 --no-loop \
        --output out_with_bg.mp4
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def find_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        print(
            f"ERROR: {name} was not found on PATH.\n"
            "Make sure ffmpeg (which bundles ffprobe) is installed and on "
            "PATH for this shell before running this script.",
            file=sys.stderr,
        )
        sys.exit(1)
    return path


def run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def get_duration(ffprobe: str, path: Path) -> float:
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    if result.returncode != 0 or not result.stdout.strip():
        print(f"ERROR: could not read duration of {path}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return float(result.stdout.strip())


def has_audio_stream(ffprobe: str, path: Path) -> bool:
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(path),
        ]
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def has_alpha(ffprobe: str, path: Path) -> bool:
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=pix_fmt",
            "-of",
            "csv=p=0",
            str(path),
        ]
    )
    pix_fmt = result.stdout.strip().lower()
    return "a" in pix_fmt and pix_fmt not in ("gray", "ya8")


def build_filter(loop: bool, video_duration: float) -> str:
    # scale2ref stretches the background (input 1) to the foreground's (input
    # 0) exact dimensions, same stretch-to-fit convention used for
    # "background_image" in interview_simulation.py.
    if loop:
        # -stream_loop -1 on the background input already makes it infinite;
        # shortest=1 then just stops the composite at the foreground's end.
        return (
            "[1:v][0:v]scale2ref=w=main_w:h=main_h[bg][fg];"
            "[bg][fg]overlay=shortest=1:format=auto[vout]"
        )
    return (
        f"[1:v]tpad=stop_mode=clone:stop_duration={video_duration:.6f}[bgpad];"
        "[bgpad][0:v]scale2ref=w=main_w:h=main_h[bg][fg];"
        "[bg][fg]overlay=format=auto[vout]"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Composite a manim transparent-background render on top of a "
            "looping background video via ffmpeg's overlay filter."
        )
    )
    parser.add_argument(
        "foreground",
        help="Path to the manim output with an alpha channel (rendered with -t).",
    )
    parser.add_argument("background", help="Path to the background video file.")
    parser.add_argument(
        "--output",
        default=None,
        help="Path to the output video. Defaults to "
        "'<foreground_name>_with_bg_video.mp4' next to the input video.",
    )
    loop_group = parser.add_mutually_exclusive_group()
    loop_group.add_argument(
        "--loop",
        dest="loop",
        action="store_true",
        default=True,
        help="Loop the background video to fill the foreground's duration if "
        "it's shorter (default).",
    )
    loop_group.add_argument(
        "--no-loop",
        dest="loop",
        action="store_false",
        help="Play the background video once; its last frame holds if it "
        "runs out before the foreground ends.",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Re-encode with Intel Quick Sync (h264_qsv) instead of the "
        "default CPU encoder (libx264). Faster on machines with Quick Sync "
        "support; silently unavailable otherwise, so only pass this if "
        "you've confirmed it works on this machine.",
    )
    args = parser.parse_args()

    foreground_path = Path(args.foreground)
    if not foreground_path.is_file():
        print(f"ERROR: foreground video not found: {foreground_path}", file=sys.stderr)
        sys.exit(1)

    background_path = Path(args.background)
    if not background_path.is_file():
        print(f"ERROR: background video not found: {background_path}", file=sys.stderr)
        sys.exit(1)

    if args.output is not None:
        output_path = Path(args.output)
    else:
        output_path = foreground_path.with_name(
            f"{foreground_path.stem}_with_bg_video.mp4"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = find_tool("ffmpeg")
    ffprobe = find_tool("ffprobe")

    if not has_alpha(ffprobe, foreground_path):
        print(
            f"ERROR: {foreground_path} has no alpha channel. Render "
            "interview_simulation.py with manim's -t/--transparent flag "
            "(and gui_config.json's \"background_video\" key set) first.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Foreground video: {foreground_path}")
    print(f"Background video: {background_path}")
    print(f"Output video:     {output_path}")
    print(f"Loop background:  {args.loop}")

    foreground_duration = get_duration(ffprobe, foreground_path)
    print(f"Foreground duration: {foreground_duration:.3f}s")

    cmd = [ffmpeg, "-y", "-i", str(foreground_path)]
    if args.loop:
        cmd += ["-stream_loop", "-1"]
    cmd += ["-i", str(background_path)]

    filter_complex = build_filter(args.loop, foreground_duration)

    cmd += ["-filter_complex", filter_complex, "-map", "[vout]"]
    if has_audio_stream(ffprobe, foreground_path):
        cmd += ["-map", "0:a"]
    if args.gpu:
        cmd += ["-c:v", "h264_qsv", "-pix_fmt", "nv12"]
    else:
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    cmd += [
        "-c:a",
        "aac",
        "-t",
        f"{foreground_duration:.6f}",
        str(output_path),
    ]

    print("Running ffmpeg...")
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("ERROR: ffmpeg failed while compositing background video.", file=sys.stderr)
        print("---- ffmpeg stderr (tail) ----", file=sys.stderr)
        stderr_tail = "\n".join(result.stderr.splitlines()[-40:])
        print(stderr_tail, file=sys.stderr)
        sys.exit(1)

    if not output_path.is_file():
        print(
            "ERROR: ffmpeg reported success but output file was not created.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Done. Video with background video written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
