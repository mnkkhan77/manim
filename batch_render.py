# Run with:
#   venv/Scripts/python.exe batch_render.py <scripts_dir> [--quality ql|qm|qh|qk] [--theme THEME_NAME] [--voice VOICE_NAME]
"""Batch-render multiple interview-practice videos from a directory of Q&A script files.

Usage:
    venv/Scripts/python.exe batch_render.py <scripts_dir> [--quality ql|qm|qh|qk] [--theme THEME_NAME] [--voice VOICE_NAME]

For every ``*.txt`` file found directly inside ``<scripts_dir>`` (sorted
alphabetically), this script:
  1. Reads the file's content (expected to be in the same "Q: ...\\nA: ...\\n\\n"
     block format as interview_script.txt).
  2. Writes that content into gui_config.json's "script_text" field (along with
     the chosen theme/voice), overwriting the project's gui_config.json.
  3. Runs `manim` as a subprocess to render interview_simulation.py's
     InterviewSimulation scene.
  4. Parses manim's "File ready at '...'" output line to find the rendered
     video, then copies it into batch_output/<script_name>.mp4 so each
     video gets its own file instead of being overwritten by the next run.

A single file failing to render is logged and does not abort the rest of
the batch. A summary of successes/failures is printed at the end.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from qa_format import parse_qa_text

SCRIPT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = SCRIPT_DIR / "venv" / "Scripts" / "python.exe"
CONFIG_FILE = SCRIPT_DIR / "gui_config.json"
OUTPUT_DIR = SCRIPT_DIR / "batch_output"

# ffmpeg is installed via winget but not on PATH in a fresh shell.
FFMPEG_BIN = (
    r"C:\Users\NIS\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.2-full_build\bin"
)

# Mirrors interview_simulation.DEFAULT_CONFIG (kept standalone/duplicated here
# on purpose -- this script must not import interview_simulation.py).
DEFAULT_GUI_CONFIG = {
    "script_text": None,
    "voice": "en-US-AndrewNeural",
    "theme": "midnight",
    "background_image": None,
    "show_intro": False,
    "channel_name": "",
    "episode_title": "",
    "show_outro": False,
    "outro_message": "Thanks for watching! Like and subscribe.",
    "handle": "",
}

VALID_QUALITIES = ("ql", "qm", "qh", "qk")

FILE_READY_RE = re.compile(r"File ready at\s*'(.+?)'", re.DOTALL)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch-render interview simulation videos from a directory of Q&A .txt scripts."
    )
    parser.add_argument("scripts_dir", help="Directory containing one or more .txt Q&A script files")
    parser.add_argument(
        "--quality",
        choices=VALID_QUALITIES,
        default="ql",
        help="Manim render quality flag (default: ql)",
    )
    parser.add_argument(
        "--theme",
        default=DEFAULT_GUI_CONFIG["theme"],
        help=f"Theme name from themes.THEMES (default: {DEFAULT_GUI_CONFIG['theme']})",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_GUI_CONFIG["voice"],
        help=f"edge-tts voice name (default: {DEFAULT_GUI_CONFIG['voice']})",
    )
    return parser.parse_args()


def write_gui_config(script_text, theme, voice):
    config = dict(DEFAULT_GUI_CONFIG)
    config["script_text"] = script_text
    config["theme"] = theme
    config["voice"] = voice
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def render_one(quality):
    env = os.environ.copy()
    env["PATH"] = FFMPEG_BIN + os.pathsep + env.get("PATH", "")
    # Keep manim's rich-logging output from wrapping the "File ready at ..."
    # line across multiple terminal lines, which would break parsing.
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
    match = FILE_READY_RE.search(combined)
    if not match:
        return None
    raw_path = match.group(1).replace("\n", "").replace("\r", "").strip()
    return Path(raw_path)


def main():
    args = parse_args()

    scripts_dir = Path(args.scripts_dir)
    if not scripts_dir.is_dir():
        print(f"Error: '{scripts_dir}' is not a directory.")
        sys.exit(1)

    if not VENV_PYTHON.exists():
        print(f"Error: venv python not found at '{VENV_PYTHON}'.")
        sys.exit(1)

    txt_files = sorted(scripts_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in '{scripts_dir}'.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Back up whatever gui_config.json currently contains so we can restore
    # it once the batch is done, instead of leaving it pointed at the last
    # rendered script.
    original_config_bytes = CONFIG_FILE.read_bytes() if CONFIG_FILE.exists() else None

    total = len(txt_files)
    succeeded = []
    failed = []

    try:
        for idx, txt_path in enumerate(txt_files, start=1):
            name = txt_path.stem
            print(f"[{idx}/{total}] Rendering {txt_path.name}...")
            try:
                script_text = txt_path.read_text(encoding="utf-8")
                parse_qa_text(script_text)  # validate before spending time on a render

                write_gui_config(script_text, args.theme, args.voice)

                result = render_one(args.quality)

                if result.returncode != 0:
                    tail_lines = (result.stdout or "").splitlines()[-20:] + (result.stderr or "").splitlines()[-20:]
                    raise RuntimeError(
                        f"manim exited with code {result.returncode}\n" + "\n".join(tail_lines)
                    )

                output_path = find_output_path(result)
                if output_path is None:
                    raise RuntimeError(
                        "could not find \"File ready at '...'\" line in manim output"
                    )
                if not output_path.exists():
                    raise RuntimeError(f"manim reported output at '{output_path}' but it does not exist")

                dest_path = OUTPUT_DIR / f"{name}.mp4"
                shutil.copy2(output_path, dest_path)

                print(f"    Done -> {dest_path}")
                succeeded.append((txt_path.name, dest_path))
            except Exception as exc:  # noqa: BLE001 - want to keep batch going on any failure
                print(f"    FAILED: {exc}")
                failed.append((txt_path.name, str(exc)))
    finally:
        if original_config_bytes is not None:
            CONFIG_FILE.write_bytes(original_config_bytes)
        elif CONFIG_FILE.exists():
            CONFIG_FILE.unlink()

    print("\n" + "=" * 60)
    print(f"Batch render complete: {len(succeeded)}/{total} succeeded, {len(failed)}/{total} failed")
    if succeeded:
        print("\nSucceeded:")
        for fname, dest in succeeded:
            print(f"  - {fname} -> {dest}")
    if failed:
        print("\nFailed:")
        for fname, reason in failed:
            print(f"  - {fname}: {reason.splitlines()[0]}")

    sys.exit(0 if succeeded or not failed else 1)


if __name__ == "__main__":
    main()
