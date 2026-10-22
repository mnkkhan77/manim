#!/usr/bin/env python
"""
burn_subtitles.py

Standalone utility to "burn in" (hardcode) an .srt subtitle file directly onto
the video frames of an mp4, using ffmpeg's libass-based `subtitles` video
filter. Useful for sharing clips on platforms that don't support separate
caption tracks, or for quickly previewing how captions would look.

Usage:
    venv/Scripts/python.exe burn_subtitles.py <path_to_video.mp4> [path_to_subtitles.srt] \
        [--output path_to_output.mp4] [--style default|bold|theme:<theme_name>]

If the .srt path is omitted, it is auto-derived by swapping the video's
extension for .srt in the same directory (the convention manim-voiceover
already uses).

If --output is omitted, it defaults to "<original_name>_captioned.mp4" in the
same directory as the input video.

`--style` accepts either one of the fixed presets ("default", "bold"), or
`theme:<theme_name>` (e.g. "theme:midnight", "theme:neon") to color the
captions using that theme's `accent_color` from themes.py, with a dark
outline for contrast, so burned-in captions can match the video's theme.

Examples:
    venv/Scripts/python.exe burn_subtitles.py media/videos/interview_simulation/480p15/InterviewSimulation.mp4
    venv/Scripts/python.exe burn_subtitles.py input.mp4 captions.srt --style bold
    venv/Scripts/python.exe burn_subtitles.py input.mp4 --output out.mp4 --style bold
    venv/Scripts/python.exe burn_subtitles.py input.mp4 --style theme:neon
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from themes import THEMES, get_theme

# ASS/libass force_style presets for the ffmpeg `subtitles` filter.
#
# Colours in libass/ASS are &HAABBGGRR& (alpha, blue, green, red; alpha 00 =
# fully opaque). Font names must be ones actually installed on the rendering
# machine's fontconfig setup, so we stick to ubiquitous Windows fonts.
STYLE_PRESETS = {
    "default": (
        "FontName=Arial,FontSize=14,PrimaryColour=&H00FFFFFF&,"
        "OutlineColour=&H00000000&,BorderStyle=1,Outline=1.5,Shadow=0,"
        "Alignment=2,MarginV=25"
    ),
    "bold": (
        "FontName=Arial,FontSize=22,Bold=1,PrimaryColour=&H0000FFFF&,"
        "OutlineColour=&H00000000&,BorderStyle=1,Outline=2.5,Shadow=1,"
        "Alignment=2,MarginV=35"
    ),
}

THEME_STYLE_PREFIX = "theme:"


def hex_to_ass_color(hex_color: str) -> str:
    """Convert a "#RRGGBB" hex string into an ASS/libass "&HAABBGGRR&" color.

    ASS colors are alpha-blue-green-red, each a 2-digit hex byte, with alpha
    00 meaning fully opaque (see STYLE_PRESETS above for the convention this
    matches, e.g. white "#FFFFFF" -> "&H00FFFFFF&").
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Expected a 6-digit hex color, got: {hex_color!r}")
    red = hex_color[0:2]
    green = hex_color[2:4]
    blue = hex_color[4:6]
    return f"&H00{blue}{green}{red}&".upper()


def build_force_style_for_theme(theme_name: str) -> str:
    """Build a force_style string using a theme's accent_color for the text,
    reusing the "default" preset's font/outline/layout settings."""
    theme = get_theme(theme_name)
    primary_colour = hex_to_ass_color(theme["accent_color"])
    return (
        f"FontName=Arial,FontSize=14,PrimaryColour={primary_colour},"
        "OutlineColour=&H00000000&,BorderStyle=1,Outline=1.5,Shadow=0,"
        "Alignment=2,MarginV=25"
    )


def resolve_force_style(style: str) -> str:
    """Resolve a --style value (a fixed preset name, or "theme:<name>") into
    a force_style string, exiting with a clear error if it's invalid."""
    if style in STYLE_PRESETS:
        return STYLE_PRESETS[style]
    if style.startswith(THEME_STYLE_PREFIX):
        theme_name = style[len(THEME_STYLE_PREFIX):]
        try:
            return build_force_style_for_theme(theme_name)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    available = ", ".join(sorted(STYLE_PRESETS.keys()))
    print(
        f"ERROR: invalid --style value: {style!r}\n"
        f"Expected one of: {available}, or 'theme:<name>' where <name> is "
        f"one of: {', '.join(sorted(THEMES.keys()))}",
        file=sys.stderr,
    )
    sys.exit(1)


def find_ffmpeg() -> str:
    """Return path to ffmpeg executable, or exit with a clear error."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        print(
            "ERROR: ffmpeg was not found on PATH.\n"
            "Make sure ffmpeg is installed and on PATH for this shell before "
            "running this script.",
            file=sys.stderr,
        )
        sys.exit(1)
    return ffmpeg_path


def escape_path_for_filter(path: Path) -> str:
    """
    Escape a filesystem path so it can be safely embedded as the argument of
    an ffmpeg `subtitles=...` filter on Windows.

    The ffmpeg filtergraph parser treats ':' as a key/value separator and
    special characters like '\\' and "'" also need care. The standard,
    verified-working fix is:
      1. Convert backslashes to forward slashes (ffmpeg/libav accepts
         forward slashes fine on Windows).
      2. Escape the drive-letter colon "C:" as "C\\:" so the filtergraph
         parser doesn't treat it as an option separator.
      3. Escape any literal single quotes (none expected here, but safe).
    """
    p = str(path.resolve())
    p = p.replace("\\", "/")
    p = p.replace(":", r"\:")
    return p


def build_filter(srt_path: Path, style: str) -> str:
    escaped_srt = escape_path_for_filter(srt_path)
    force_style = resolve_force_style(style)
    # force_style value is wrapped in single quotes per libass filter syntax.
    return f"subtitles='{escaped_srt}':force_style='{force_style}'"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Burn an .srt subtitle file into an mp4's video frames using ffmpeg."
    )
    parser.add_argument("video", help="Path to the input video (.mp4).")
    parser.add_argument(
        "srt",
        nargs="?",
        default=None,
        help="Path to the .srt subtitle file. If omitted, auto-derived from "
        "the video path by swapping its extension for .srt.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to the output video. Defaults to "
        "'<original_name>_captioned.mp4' next to the input video.",
    )
    parser.add_argument(
        "--style",
        default="default",
        help="Caption style to use: a fixed preset ('default', 'bold'), or "
        "'theme:<name>' to color captions using a themes.py theme's "
        "accent_color (e.g. 'theme:midnight', 'theme:neon'). "
        "(default: 'default').",
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

    video_path = Path(args.video)
    if not video_path.is_file():
        print(f"ERROR: input video not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    if args.srt is not None:
        srt_path = Path(args.srt)
    else:
        srt_path = video_path.with_suffix(".srt")
        print(f"No .srt path given; auto-derived: {srt_path}")

    if not srt_path.is_file():
        print(
            f"ERROR: subtitle file not found: {srt_path}\n"
            "Pass the .srt path explicitly as the second argument if it "
            "lives elsewhere, or check that manim-voiceover actually "
            "produced one alongside the video.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.output is not None:
        output_path = Path(args.output)
    else:
        output_path = video_path.with_name(f"{video_path.stem}_captioned.mp4")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = find_ffmpeg()

    vf = build_filter(srt_path, args.style)

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf,
    ]
    if args.gpu:
        cmd += ["-c:v", "h264_qsv", "-pix_fmt", "nv12"]
    cmd += ["-c:a", "copy", str(output_path)]

    print(f"Input video:    {video_path}")
    print(f"Subtitle file:  {srt_path}")
    print(f"Style preset:   {args.style}")
    print(f"Output video:   {output_path}")
    print("Running ffmpeg...")
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("ERROR: ffmpeg failed while burning in subtitles.", file=sys.stderr)
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

    print(f"Done. Captioned video written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
