#!/usr/bin/env python
"""
add_background_music.py

Standalone utility to mix a background music track under an already-rendered
video's narration (TTS voiceover) audio, automatically "ducking" (lowering)
the music while narration is speaking and letting it swell back up during
pauses. Companion to burn_subtitles.py - same CLI shape, same conventions.

Usage:
    venv/Scripts/python.exe add_background_music.py <video.mp4> <music_file> \
        [--output path] [--loop | --no-loop] [--duck-db N]

<video.mp4>   - an already-rendered video with a narration audio track.
<music_file>  - any audio file ffmpeg can read (mp3/wav/etc) to use as music.

If --output is omitted, it defaults to "<video_name>_with_music.mp4" next to
the input video.

--loop (default) repeats the music to fill the whole video if it's shorter
    than the video. --no-loop plays it once; if it's shorter than the video
    the rest is silence, if longer it's cut off at the video's end either way
    - the output duration always matches the input video exactly.

--duck-db controls how many dB quieter the music gets while narration is
    playing (default 18, a middle-of-the-road broadcast-ducking amount: audible
    and clearly subordinate to narration, but not slammed to silence).

Examples:
    venv/Scripts/python.exe add_background_music.py out.mp4 music.mp3
    venv/Scripts/python.exe add_background_music.py out.mp4 music.mp3 --no-loop
    venv/Scripts/python.exe add_background_music.py out.mp4 music.mp3 --duck-db 12 \
        --output out_with_music.mp4
"""

import argparse
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

# sidechaincompress's ratio is capped at 20:1 by ffmpeg itself; at that ratio
# a signal sitting X dB above the compressor's threshold gets pulled down by
# roughly X * (1 - 1/ratio) dB. We solve that equation for the threshold that
# should yield --duck-db of reduction once narration is active, using the
# narration track's peak level (stable to measure, via volumedetect) as the
# reference point for "active" loudness.
#
# The 0.65 constant below is an empirical correction, not derived from the
# compressor math above: sidechaincompress's RMS envelope follower (attack=5ms)
# tracks something closer to short-term peaks than to long-term RMS, so the
# naive (1 - 1/ratio) formula alone under-shoots. 0.65 was fit by rendering a
# real narrated clip, measuring actual dB reduction with ffmpeg's astats
# filter, and adjusting until measured ducking matched the requested
# --duck-db at the default (18 dB). It won't be exact for every narration
# track (different loudness/pacing shifts the result a little), but it keeps
# --duck-db a meaningful, monotonic knob: higher = more ducking.
RATIO = 20.0
EMPIRICAL_K = 0.65
ATTACK_MS = 5       # fast enough to duck right as a word starts
RELEASE_MS = 400     # slow enough that music doesn't flutter between words,
                      # only swells back up during real pauses

THRESHOLD_MIN = 0.000976563  # sidechaincompress's own valid range (~-60 dB)
THRESHOLD_MAX = 1.0          # (0 dB)


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


def get_narration_peak_db(ffmpeg: str, video_path: Path) -> float:
    """Peak (max_volume) of the video's narration track, via volumedetect."""
    result = run(
        [
            ffmpeg,
            "-i",
            str(video_path),
            "-map",
            "0:a",
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ]
    )
    match = re.search(r"max_volume:\s*(-?[\d.]+|-inf)\s*dB", result.stderr)
    if not match or match.group(1) == "-inf":
        print(
            "WARNING: could not measure narration loudness (track may be "
            "silent); assuming -20 dB as a fallback reference level.",
            file=sys.stderr,
        )
        return -20.0
    return float(match.group(1))


def compute_threshold(narration_peak_db: float, duck_db: float) -> float:
    effective_factor = 1 - (1 / RATIO)
    threshold_db = narration_peak_db - (duck_db / EMPIRICAL_K) * effective_factor
    threshold_db = max(-59.0, min(-0.5, threshold_db))
    threshold_linear = 10 ** (threshold_db / 20)
    return max(THRESHOLD_MIN, min(THRESHOLD_MAX, threshold_linear))


def build_filter(threshold: float, ratio: float) -> str:
    # sidechaincompress's output length is min(main, sidechain) - if the
    # narration track (sidechain) is shorter than the video (e.g. a silent
    # outro tail with no audio samples at all), looped music would otherwise
    # get cut off at the narration's end instead of continuing. apad the
    # narration branch first so it never becomes the limiting input; the
    # final -t on the ffmpeg command is what actually bounds everything.
    return (
        f"[0:a]apad,asplit=2[sc][narr];"
        f"[1:a][sc]sidechaincompress=threshold={threshold:.6f}:ratio={ratio}:"
        f"attack={ATTACK_MS}:release={RELEASE_MS}:makeup=1[duckedmusic];"
        f"[duckedmusic][narr]amix=inputs=2:duration=longest:"
        f"dropout_transition=0:normalize=0,apad[aout]"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Mix background music under a video's existing narration audio, "
            "ducking the music automatically while narration is speaking."
        )
    )
    parser.add_argument("video", help="Path to the input video (.mp4) with narration audio.")
    parser.add_argument("music", help="Path to the background music file (mp3/wav/etc).")
    parser.add_argument(
        "--output",
        default=None,
        help="Path to the output video. Defaults to "
        "'<video_name>_with_music.mp4' next to the input video.",
    )
    loop_group = parser.add_mutually_exclusive_group()
    loop_group.add_argument(
        "--loop",
        dest="loop",
        action="store_true",
        default=True,
        help="Loop the music to fill the entire video if it's shorter (default).",
    )
    loop_group.add_argument(
        "--no-loop",
        dest="loop",
        action="store_false",
        help="Play the music once; the rest of the video is silent if it runs out first.",
    )
    parser.add_argument(
        "--duck-db",
        type=float,
        default=18.0,
        help="How many dB quieter the music gets while narration plays (default: 18).",
    )
    args = parser.parse_args()

    if args.duck_db < 0:
        print("ERROR: --duck-db must be >= 0.", file=sys.stderr)
        sys.exit(1)

    video_path = Path(args.video)
    if not video_path.is_file():
        print(f"ERROR: input video not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    music_path = Path(args.music)
    if not music_path.is_file():
        print(f"ERROR: music file not found: {music_path}", file=sys.stderr)
        sys.exit(1)

    if args.output is not None:
        output_path = Path(args.output)
    else:
        output_path = video_path.with_name(f"{video_path.stem}_with_music.mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = find_tool("ffmpeg")
    ffprobe = find_tool("ffprobe")

    if not has_audio_stream(ffprobe, video_path):
        print(
            f"ERROR: {video_path} has no audio track to duck music against.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Input video:    {video_path}")
    print(f"Music file:     {music_path}")
    print(f"Output video:   {output_path}")
    print(f"Loop music:     {args.loop}")
    print(f"Duck amount:    {args.duck_db} dB")

    video_duration = get_duration(ffprobe, video_path)
    print(f"Video duration: {video_duration:.3f}s")

    if args.duck_db <= 0:
        ratio = 1.0
        threshold = 0.125  # irrelevant at ratio=1 (no gain reduction applied)
    else:
        print("Measuring narration loudness...")
        narration_peak_db = get_narration_peak_db(ffmpeg, video_path)
        print(f"Narration peak level: {narration_peak_db:.1f} dB")
        ratio = RATIO
        threshold = compute_threshold(narration_peak_db, args.duck_db)
        print(
            f"Compressor threshold: {threshold:.5f} linear "
            f"({20 * math.log10(threshold):.1f} dB)"
        )

    filter_complex = build_filter(threshold, ratio)

    cmd = [ffmpeg, "-y", "-i", str(video_path)]
    if args.loop:
        cmd += ["-stream_loop", "-1"]
    cmd += [
        "-i",
        str(music_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-t",
        f"{video_duration:.6f}",
        str(output_path),
    ]

    print("Running ffmpeg...")
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("ERROR: ffmpeg failed while mixing in background music.", file=sys.stderr)
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

    print(f"Done. Video with background music written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
