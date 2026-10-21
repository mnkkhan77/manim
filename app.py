"""Streamlit GUI for rendering interview-practice videos with interview_simulation.py.

Run with:
    venv/Scripts/python.exe -m streamlit run app.py

This app wraps the manim CLI render so a non-technical user never has to touch
a terminal, edit JSON by hand, or run Python directly. It writes gui_config.json
(matching the schema read by interview_simulation.py's load_gui_config()) and
then runs `manim ... interview_simulation.py InterviewSimulation`, streaming
the render log live into the page.
"""

import json
import os
import re
import subprocess
from pathlib import Path

import streamlit as st

import qa_format
from interview_simulation import STYLE_REGISTRY
from themes import THEMES

# --- Paths -------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = BASE_DIR / "venv" / "Scripts" / "python.exe"
GUI_CONFIG_PATH = BASE_DIR / "gui_config.json"
UPLOAD_DIR = BASE_DIR / "uploaded_backgrounds"
MUSIC_UPLOAD_DIR = BASE_DIR / "uploaded_music"
ADD_MUSIC_SCRIPT = BASE_DIR / "add_background_music.py"
FFMPEG_BIN = (
    "C:/Users/NIS/AppData/Local/Microsoft/WinGet/Packages/"
    "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
    "ffmpeg-9.0.2-full_build/bin"
)

# --- Static option tables -----------------------------------------------

# Real edge-tts neural voice names (verified via `python -m edge_tts --list-voices`),
# spanning US/GB accents and both genders, with short human-friendly labels.
VOICE_OPTIONS = {
    "Andrew (US, Male, Warm & Conversational)": "en-US-AndrewNeural",
    "Aria (US, Female, Confident, News-style)": "en-US-AriaNeural",
    "Guy (US, Male, Energetic, News-style)": "en-US-GuyNeural",
    "Jenny (US, Female, Friendly & Comforting)": "en-US-JennyNeural",
    "Ryan (UK, Male, Friendly & Positive)": "en-GB-RyanNeural",
    "Sonia (UK, Female, Friendly & Positive)": "en-GB-SoniaNeural",
}

QUALITY_OPTIONS = {
    "Low (fast preview, 480p15)": {"flag": "-ql", "folder": "480p15"},
    "Medium (720p30)": {"flag": "-qm", "folder": "720p30"},
    "High (1080p60)": {"flag": "-qh", "folder": "1080p60"},
    "4K (2160p60, slow)": {"flag": "-qk", "folder": "2160p60"},
}

FORMAT_OPTIONS = ["mp4", "mov", "webm"]

DEFAULT_SCRIPT = (
    "Q: Tell me about yourself.\n"
    "A: I'm a backend engineer with a few years of experience building and "
    "maintaining web services, and I enjoy working closely with product teams "
    "to ship features end to end.\n"
)

# Manim's rich-based logger hard-wraps long lines (including file paths) at a
# fixed column width even when stdout isn't a real terminal, inserting
# newlines + indentation padding mid-path. To parse the real path reliably we
# strip ALL whitespace from the log before matching (file paths here never
# contain spaces), rather than matching against the raw multi-line text.
FILE_READY_RE = re.compile(r"Filereadyat'([^']+)'")

st.set_page_config(page_title="Interview Video Generator", page_icon="🎬", layout="wide")


# --- Sidebar: settings ----------------------------------------------------

st.sidebar.header("Settings")

voice_label = st.sidebar.selectbox("Voice", list(VOICE_OPTIONS.keys()), index=0)
voice = VOICE_OPTIONS[voice_label]
st.sidebar.caption("The narrator's voice for both questions and answers.")

theme_names = list(THEMES.keys())
default_theme_index = theme_names.index("midnight") if "midnight" in theme_names else 0
theme = st.sidebar.selectbox("Theme", theme_names, index=default_theme_index)
st.sidebar.caption("Background gradient and text colors. Ignored if a background image is uploaded.")

style_names = list(STYLE_REGISTRY.keys())
REVEAL_STYLE_LABELS = {name: name.replace("_", " ").title() for name in style_names}
default_style_index = style_names.index("stacked") if "stacked" in style_names else 0
reveal_style_label = st.sidebar.selectbox(
    "Reveal style",
    [REVEAL_STYLE_LABELS[name] for name in style_names],
    index=default_style_index,
)
reveal_style = style_names[
    [REVEAL_STYLE_LABELS[name] for name in style_names].index(reveal_style_label)
]
st.sidebar.caption("How the question and answer text appears on screen.")

st.sidebar.subheader("Background image (optional)")
bg_upload = st.sidebar.file_uploader(
    "Upload a custom background", type=["png", "jpg", "jpeg"]
)
background_image_path = None
if bg_upload is not None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = UPLOAD_DIR / bg_upload.name
    with open(saved_path, "wb") as f:
        f.write(bg_upload.getbuffer())
    background_image_path = str(saved_path.resolve())
    st.sidebar.image(bg_upload, caption="Background preview", use_container_width=True)
    st.sidebar.caption("This image replaces the theme gradient as the video background.")
else:
    st.sidebar.caption("No image uploaded — the theme's gradient background will be used.")

st.sidebar.subheader("Background music (optional)")
music_upload = st.sidebar.file_uploader(
    "Upload a music track", type=["mp3", "wav", "m4a", "ogg"]
)
music_path = None
music_loop = True
if music_upload is not None:
    MUSIC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_music_path = MUSIC_UPLOAD_DIR / music_upload.name
    with open(saved_music_path, "wb") as f:
        f.write(music_upload.getbuffer())
    music_path = str(saved_music_path.resolve())
    st.sidebar.audio(music_upload)
    music_loop = st.sidebar.checkbox("Loop music to fill the video", value=True)
    st.sidebar.caption(
        "Music is mixed in after rendering and automatically ducked quieter "
        "while the narration is talking."
    )
else:
    st.sidebar.caption("No track uploaded — the video will have narration audio only.")

st.sidebar.subheader("Video quality")
quality_label = st.sidebar.selectbox(
    "Quality", list(QUALITY_OPTIONS.keys()), index=0
)
quality = QUALITY_OPTIONS[quality_label]
st.sidebar.caption("Low renders fastest — good for quick iteration. Higher quality takes longer.")

st.sidebar.subheader("Video format")
video_format = st.sidebar.selectbox("Format", FORMAT_OPTIONS, index=0)
st.sidebar.caption("mp4 is the safest default for uploading to most platforms.")


# --- Main area: script + intro/outro --------------------------------------

st.title("Interview Practice Video Generator")
st.write(
    "Paste your Q&A script, pick your settings in the sidebar, and click "
    "**Generate Video** — no terminal or code required."
)

st.subheader("Interview script")
st.caption(
    "Format: alternating `Q: ...` and `A: ...` lines, with each Q&A pair "
    "separated by a blank line. Example:\n\n"
    "```\nQ: What is your biggest strength?\n"
    "A: I'm good at breaking ambiguous problems into smaller pieces.\n```"
)
script_text = st.text_area(
    "Q&A script",
    value=DEFAULT_SCRIPT,
    height=280,
    label_visibility="collapsed",
)

col1, col2 = st.columns(2)

with col1:
    show_intro = st.checkbox("Include intro card")
    channel_name = ""
    episode_title = ""
    if show_intro:
        channel_name = st.text_input("Channel name", value="")
        episode_title = st.text_input("Episode title (optional)", value="")

with col2:
    show_outro = st.checkbox("Include outro card")
    outro_message = "Thanks for watching! Like and subscribe."
    handle = ""
    if show_outro:
        outro_message = st.text_input("Outro message", value=outro_message)
        handle = st.text_input("Handle (optional, e.g. @yourhandle)", value="")

st.divider()

generate_clicked = st.button("🎬 Generate Video", type="primary", use_container_width=True)

output_container = st.container()


def build_gui_config():
    return {
        "script_text": script_text if script_text.strip() else None,
        "voice": voice,
        "theme": theme,
        "reveal_style": reveal_style,
        "background_image": background_image_path,
        "show_intro": bool(show_intro),
        "channel_name": channel_name,
        "episode_title": episode_title,
        "show_outro": bool(show_outro),
        "outro_message": outro_message,
        "handle": handle,
    }


def expected_output_path():
    """Fallback path based on manim's known output folder layout."""
    return (
        BASE_DIR
        / "media"
        / "videos"
        / "interview_simulation"
        / quality["folder"]
        / f"InterviewSimulation.{video_format}"
    )


def run_render():
    config = build_gui_config()
    with open(GUI_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    cmd = [
        str(VENV_PYTHON),
        "-m",
        "manim",
        quality["flag"],
        "--format",
        video_format,
        "--disable_caching",
        "interview_simulation.py",
        "InterviewSimulation",
    ]

    env = os.environ.copy()
    env["PATH"] = FFMPEG_BIN + os.pathsep + env.get("PATH", "")

    log_lines = []
    log_box = output_container.empty()
    status_box = output_container.empty()
    status_box.info("Rendering... this can take anywhere from tens of seconds to a few minutes.")

    process = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in process.stdout:
        log_lines.append(line.rstrip("\n"))
        log_box.code("\n".join(log_lines[-200:]), language="text")

    returncode = process.wait()
    full_log = "\n".join(log_lines)
    # Collapse all whitespace/newlines before matching, since manim's console
    # output hard-wraps long lines (including file paths) with indentation.
    flattened_log = re.sub(r"\s+", "", full_log)

    if returncode == 0:
        status_box.success("Render complete!")
        match = FILE_READY_RE.search(flattened_log)
        output_path = Path(match.group(1)) if match else expected_output_path()

        if output_path.exists():
            final_path = output_path

            if music_path:
                mixed_path = output_path.with_name(
                    output_path.stem + "_with_music" + output_path.suffix
                )
                music_cmd = [
                    str(VENV_PYTHON),
                    str(ADD_MUSIC_SCRIPT),
                    str(output_path),
                    music_path,
                    "--output",
                    str(mixed_path),
                    "--loop" if music_loop else "--no-loop",
                ]
                status_box.info("Mixing in background music...")
                music_result = subprocess.run(
                    music_cmd,
                    cwd=str(BASE_DIR),
                    env=env,
                    capture_output=True,
                    text=True,
                )
                if music_result.returncode == 0 and mixed_path.exists():
                    final_path = mixed_path
                    status_box.success("Render complete, with music mixed in!")
                else:
                    status_box.warning(
                        "Render succeeded, but mixing in the music failed — "
                        "showing the version without music instead."
                    )
                    st.caption("```\n" + music_result.stdout[-1500:] + "\n```")

            st.video(str(final_path))
            with open(final_path, "rb") as f:
                st.download_button(
                    "Download video",
                    data=f.read(),
                    file_name=final_path.name,
                    mime=f"video/{video_format if video_format != 'mov' else 'quicktime'}",
                )
        else:
            st.error(
                f"Render reported success, but the output file could not be found at "
                f"{output_path}. Check the log above for the actual path."
            )
    else:
        status_box.error(f"Render failed (exit code {returncode}). See log tail below.")
        st.error("```\n" + "\n".join(log_lines[-40:]) + "\n```")


if generate_clicked:
    if not script_text.strip():
        st.error("Please enter a Q&A script before generating a video.")
    else:
        try:
            qa_format.parse_qa_text(script_text)
        except ValueError as e:
            st.error(f"Script format problem: {e}")
        else:
            run_render()
