# Run with:
#   venv/Scripts/python.exe export_bundle.py <script.txt> [--quality ql|qm|qh|qk] [--theme THEME_NAME] [--voice VOICE_NAME] [--answer-voice VOICE_NAME] [--reveal-style STYLE_NAME] [--output-dir DIR]
"""One-command "export bundle": render + metadata + subtitles in a single step.

Usage:
    venv/Scripts/python.exe export_bundle.py <script.txt> \\
        [--quality ql|qm|qh|qk] [--theme THEME_NAME] [--voice VOICE_NAME] \\
        [--answer-voice VOICE_NAME] [--reveal-style STYLE_NAME] [--output-dir DIR]

Takes a Q&A script in the same "Q: ...\\nA: ...\\n\\n" block format as
interview_script.txt and produces everything needed to upload the video, in
one go, instead of running render + generate_metadata.py + subtitle handling
as separate manual steps:
  1. Validates the script with qa_format.parse_qa_text -- a malformed script
     fails fast here, before the slow manim render is ever started.
  2. Writes gui_config.json with script_text set to the script's content,
     plus whichever of --theme/--voice/--answer-voice/--reveal-style were
     passed (anything not passed falls back to interview_simulation.py's own
     DEFAULT_CONFIG).
  3. Runs manim (InterviewSimulation) as a subprocess at the requested
     --quality (default "ql").
  4. Generates title/description/duration-estimate metadata for the same
     script (reusing generate_metadata.py's functions).
  5. Collects the rendered video, its auto-generated .srt subtitles, and a
     metadata.txt into export_bundle_output/<script_name>/ (or --output-dir).
  6. Zips that output directory into a single <script_name>.zip next to it.

Examples:
    venv/Scripts/python.exe export_bundle.py interview_script.txt
    venv/Scripts/python.exe export_bundle.py scripts/ml_basics.txt --quality qh --theme neon
    venv/Scripts/python.exe export_bundle.py scripts/ml_basics.txt --output-dir out/ml_basics
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from qa_format import parse_qa_text

SCRIPT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = SCRIPT_DIR / "venv" / "Scripts" / "python.exe"
CONFIG_FILE = SCRIPT_DIR / "gui_config.json"
OUTPUT_ROOT = SCRIPT_DIR / "export_bundle_output"

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
        description="Render a Q&A script and bundle video + subtitles + metadata into one zip, in one command."
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
        help="Directory to write the bundle into (default: export_bundle_output/<script_name>/)",
    )
    return parser.parse_args()


def write_gui_config(script_text, args):
    config = dict(DEFAULT_GUI_CONFIG)
    config["script_text"] = script_text
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


def main():
    args = parse_args()

    if not VENV_PYTHON.exists():
        fail("setup", f"venv python not found at '{VENV_PYTHON}'.")

    script_path = Path(args.script).resolve()
    if not script_path.is_file():
        fail("validation", f"script not found: '{script_path}'")

    script_text = script_path.read_text(encoding="utf-8")

    try:
        pairs = parse_qa_text(script_text)
    except ValueError as exc:
        fail("validation", f"'{script_path}' is not a valid Q&A script -- {exc}")

    print(f"[1/4] Script validated: {len(pairs)} Q&A pair(s) in '{script_path.name}'.")

    write_gui_config(script_text, args)
    print(f"[2/4] Rendering at -{args.quality} (this can take a while)...")

    try:
        result = run_render(args.quality)
    except OSError as exc:
        fail("render", f"could not launch manim subprocess -- {exc}")

    if result.returncode != 0:
        tail_lines = (result.stdout or "").splitlines()[-20:] + (result.stderr or "").splitlines()[-20:]
        fail("render", f"manim exited with code {result.returncode}\n" + "\n".join(tail_lines))

    output_path = find_output_path(result)
    if output_path is None:
        fail("render", "could not find \"File ready at '...'\" line in manim output")
    if not output_path.exists():
        fail("render", f"manim reported output at '{output_path}' but it does not exist")

    print(f"    Rendered -> {output_path}")

    print("[3/4] Generating metadata...")
    try:
        from generate_metadata import build_metadata_text

        metadata_text = build_metadata_text(pairs)
    except Exception as exc:  # noqa: BLE001 - surface any metadata failure clearly
        fail("metadata generation", str(exc))

    if args.output_dir is not None:
        output_dir = Path(args.output_dir).resolve()
    else:
        output_dir = OUTPUT_ROOT / script_path.stem

    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        video_dest = output_dir / f"video{output_path.suffix}"
        shutil.copy2(output_path, video_dest)

        srt_path = output_path.with_suffix(".srt")
        srt_dest = None
        if srt_path.exists():
            srt_dest = output_dir / "video.srt"
            shutil.copy2(srt_path, srt_dest)
        else:
            print(f"    WARNING: no subtitle file found at '{srt_path}' -- bundling without it.")

        metadata_dest = output_dir / "metadata.txt"
        metadata_dest.write_text(metadata_text, encoding="utf-8")
    except OSError as exc:
        fail("bundling output", str(exc))

    print(f"[4/4] Zipping bundle -> {output_dir}")
    zip_path = output_dir.parent / f"{output_dir.name}.zip"
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in sorted(output_dir.rglob("*")):
                if item.is_file():
                    zf.write(item, arcname=item.relative_to(output_dir.parent))
    except OSError as exc:
        fail("zipping output", str(exc))

    print("\n" + "=" * 60)
    print("Export bundle complete.")
    print(f"  Video:    {video_dest}")
    print(f"  Subtitles: {srt_dest if srt_dest else '(none found)'}")
    print(f"  Metadata: {metadata_dest}")
    print(f"  Folder:   {output_dir}")
    print(f"  Zip:      {zip_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
