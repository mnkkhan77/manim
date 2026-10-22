# Run with:
#   venv/Scripts/python.exe export_dual.py <script.txt> [--quality ql|qm|qh|qk] [--theme THEME_NAME] [--voice VOICE_NAME] [--answer-voice VOICE_NAME] [--reveal-style STYLE_NAME] [--output-dir DIR]
"""Render the same Q&A script in both landscape (16:9) and portrait (9:16) in one command.

Usage:
    venv/Scripts/python.exe export_dual.py <script.txt> \\
        [--quality ql|qm|qh|qk] [--theme THEME_NAME] [--voice VOICE_NAME] \\
        [--answer-voice VOICE_NAME] [--reveal-style STYLE_NAME] [--output-dir DIR]

Takes a Q&A script in the same "Q: ...\\nA: ...\\n\\n" block format as
interview_script.txt and renders it twice -- once with
gui_config["orientation"] = "landscape" and once with "portrait" -- so a
long-form upload and a Shorts/Reels/TikTok cut come out of a single run
instead of hand-editing gui_config.json and re-rendering manually twice.
Every other setting (theme, voice, reveal_style, quality, script) is kept
identical between the two renders.

  1. Validates the script with qa_format.parse_qa_file -- a malformed script
     fails fast here, before either render is started.
  2. Writes gui_config.json with script_text set to the script's content,
     plus whichever of --theme/--voice/--answer-voice/--reveal-style were
     passed, and orientation set to "landscape", then runs manim.
  3. Rewrites gui_config.json with orientation set to "portrait" (everything
     else unchanged) and runs manim again.
  4. Collects each rendered video and its auto-generated .srt subtitles into
     export_dual_output/<script_name>/{landscape,portrait}.{mp4,srt}.

Examples:
    venv/Scripts/python.exe export_dual.py interview_script.txt
    venv/Scripts/python.exe export_dual.py scripts/ml_basics.txt --quality qh --theme neon
    venv/Scripts/python.exe export_dual.py scripts/ml_basics.txt --output-dir out/ml_basics
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from qa_format import parse_qa_file

SCRIPT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = SCRIPT_DIR / "venv" / "Scripts" / "python.exe"
CONFIG_FILE = SCRIPT_DIR / "gui_config.json"
OUTPUT_ROOT = SCRIPT_DIR / "export_dual_output"

# ffmpeg is installed via winget but not on PATH in a fresh shell.
FFMPEG_BIN = (
    r"C:\Users\NIS\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.2-full_build\bin"
)

# Mirrors interview_simulation.DEFAULT_CONFIG (kept standalone/duplicated here
# on purpose -- this script must not import interview_simulation.py, which
# pulls in the full manim/manim-voiceover stack just to read a dict).
DEFAULT_GUI_CONFIG = {
    "script_text": None,
    "voice": "en-US-AndrewNeural",
    "answer_voice": None,
    "theme": "midnight",
    "background_image": None,
    "reveal_style": "stacked",
    "orientation": "landscape",
    "add_fillers": False,
    "filler_rate": 0.15,
    "show_intro": False,
    "channel_name": "",
    "episode_title": "",
    "show_outro": False,
    "outro_message": "Thanks for watching! Like and subscribe.",
    "handle": "",
}

VALID_QUALITIES = ("ql", "qm", "qh", "qk")

# Manim's rich-based logger hard-wraps long lines (including file paths) at a
# fixed column width even when stdout isn't a real terminal, inserting
# newlines + indentation padding mid-path. To parse the real path reliably we
# strip ALL whitespace from the log before matching (file paths here never
# contain spaces), rather than matching against the raw multi-line text.
FILE_READY_RE = re.compile(r"Filereadyat'([^']+)'")


def fail(stage, message):
    print(f"ERROR [{stage}]: {message}", file=sys.stderr)
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Render a Q&A script in both landscape and portrait in one command."
    )
    parser.add_argument("script", help="Path to a Q&A script .txt file (same format as interview_script.txt)")
    parser.add_argument(
        "--quality",
        choices=VALID_QUALITIES,
        default="ql",
        help="Manim render quality flag (default: ql)",
    )
    parser.add_argument("--theme", default=None, help="Theme name from themes.THEMES (default: interview_simulation.py's own default)")
    parser.add_argument("--voice", default=None, help="edge-tts voice name for questions (default: interview_simulation.py's own default)")
    parser.add_argument("--answer-voice", default=None, help="edge-tts voice name for answers (default: same as --voice)")
    parser.add_argument("--reveal-style", default=None, help="Reveal style key from STYLE_REGISTRY (default: interview_simulation.py's own default)")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write landscape.mp4/portrait.mp4 into (default: export_dual_output/<script_name>/)",
    )
    return parser.parse_args()


def write_gui_config(script_text, args, orientation):
    config = dict(DEFAULT_GUI_CONFIG)
    config["script_text"] = script_text
    config["orientation"] = orientation
    if args.theme is not None:
        config["theme"] = args.theme
    if args.voice is not None:
        config["voice"] = args.voice
    if args.answer_voice is not None:
        config["answer_voice"] = args.answer_voice
    if args.reveal_style is not None:
        config["reveal_style"] = args.reveal_style
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def run_render(quality):
    env = os.environ.copy()
    env["PATH"] = FFMPEG_BIN + os.pathsep + env.get("PATH", "")
    env["COLUMNS"] = "1000"

    cmd = [
        str(VENV_PYTHON),
        "-m",
        "manim",
        f"-{quality}",
        "--disable_caching",
        "interview_simulation.py",
        "InterviewSimulation",
    ]
    return subprocess.run(
        cmd,
        cwd=str(SCRIPT_DIR),
        env=env,
        capture_output=True,
        text=True,
    )


def find_output_path(result):
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    flattened = re.sub(r"\s+", "", combined)
    match = FILE_READY_RE.search(flattened)
    if not match:
        return None
    return Path(match.group(1))


def render_orientation(script_text, args, orientation, step_label, output_dir):
    write_gui_config(script_text, args, orientation)
    print(f"{step_label} Rendering {orientation} at -{args.quality} (this can take a while)...")

    try:
        result = run_render(args.quality)
    except OSError as exc:
        fail("render", f"could not launch manim subprocess -- {exc}")

    if result.returncode != 0:
        tail_lines = (result.stdout or "").splitlines()[-20:] + (result.stderr or "").splitlines()[-20:]
        fail("render", f"manim exited with code {result.returncode} ({orientation})\n" + "\n".join(tail_lines))

    output_path = find_output_path(result)
    if output_path is None:
        fail("render", f"could not find \"File ready at '...'\" line in manim output ({orientation})")
    if not output_path.exists():
        fail("render", f"manim reported output at '{output_path}' but it does not exist ({orientation})")

    print(f"    Rendered -> {output_path}")

    video_dest = output_dir / f"{orientation}{output_path.suffix}"
    shutil.copy2(output_path, video_dest)

    srt_path = output_path.with_suffix(".srt")
    srt_dest = None
    if srt_path.exists():
        srt_dest = output_dir / f"{orientation}.srt"
        shutil.copy2(srt_path, srt_dest)
    else:
        print(f"    WARNING: no subtitle file found at '{srt_path}' -- skipping it for {orientation}.")

    return video_dest, srt_dest


def main():
    args = parse_args()

    if not VENV_PYTHON.exists():
        fail("setup", f"venv python not found at '{VENV_PYTHON}'.")

    script_path = Path(args.script).resolve()
    if not script_path.is_file():
        fail("validation", f"script not found: '{script_path}'")

    try:
        pairs = parse_qa_file(script_path)
    except ValueError as exc:
        fail("validation", f"'{script_path}' is not a valid Q&A script -- {exc}")

    script_text = script_path.read_text(encoding="utf-8")

    print(f"[1/3] Script validated: {len(pairs)} Q&A pair(s) in '{script_path.name}'.")

    if args.output_dir is not None:
        output_dir = Path(args.output_dir).resolve()
    else:
        output_dir = OUTPUT_ROOT / script_path.stem

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        fail("setup", f"could not create output directory '{output_dir}' -- {exc}")

    original_config_bytes = CONFIG_FILE.read_bytes() if CONFIG_FILE.exists() else None

    try:
        landscape_video, landscape_srt = render_orientation(
            script_text, args, "landscape", "[2/3]", output_dir
        )
        portrait_video, portrait_srt = render_orientation(
            script_text, args, "portrait", "[3/3]", output_dir
        )
    finally:
        if original_config_bytes is not None:
            CONFIG_FILE.write_bytes(original_config_bytes)
        elif CONFIG_FILE.exists():
            CONFIG_FILE.unlink()

    print("\n" + "=" * 60)
    print("Dual export complete.")
    print(f"  Landscape video:     {landscape_video}")
    print(f"  Landscape subtitles: {landscape_srt if landscape_srt else '(none found)'}")
    print(f"  Portrait video:      {portrait_video}")
    print(f"  Portrait subtitles:  {portrait_srt if portrait_srt else '(none found)'}")
    print(f"  Folder:              {output_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
