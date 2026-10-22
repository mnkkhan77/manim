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
import sys
import tempfile
import time
from pathlib import Path

import streamlit as st

import generate_thumbnail
import qa_format
import question_bank
import sessions
from interview_simulation import STYLE_REGISTRY
from themes import THEMES

# --- Paths -------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = BASE_DIR / "venv" / "Scripts" / "python.exe"
GUI_CONFIG_PATH = BASE_DIR / "gui_config.json"

# timeline_video/ is a separate, experimental pipeline (see AGENTS.md) — its
# own folder, own config/script files, imported here only for the "Timeline
# (Testing)" tab below. It never touches the interview pipeline's files.
TIMELINE_DIR = BASE_DIR / "timeline_video"
TIMELINE_SCRIPT_PY = TIMELINE_DIR / "timeline_simulation.py"
TIMELINE_CONFIG_PATH = TIMELINE_DIR / "timeline_config.json"
TIMELINE_SCRIPT_FILE = TIMELINE_DIR / "timeline_script.txt"
sys.path.insert(0, str(TIMELINE_DIR))
import timeline_format
UPLOAD_DIR = BASE_DIR / "uploaded_backgrounds"
MUSIC_UPLOAD_DIR = BASE_DIR / "uploaded_music"
BG_VIDEO_UPLOAD_DIR = BASE_DIR / "uploaded_bg_videos"
ADD_MUSIC_SCRIPT = BASE_DIR / "add_background_music.py"
ADD_BG_VIDEO_SCRIPT = BASE_DIR / "add_background_video.py"
BURN_SUBTITLES_SCRIPT = BASE_DIR / "burn_subtitles.py"
EXPORT_DUAL_SCRIPT = BASE_DIR / "export_dual.py"
DUAL_EXPORT_DIR = BASE_DIR / "export_dual_output"
THUMBNAIL_DIR = BASE_DIR / "thumbnails"
FFMPEG_BIN = (
    "C:/Users/NIS/AppData/Local/Microsoft/WinGet/Packages/"
    "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
    "ffmpeg-9.0.2-full_build/bin"
)


@st.cache_resource
def detect_gpu_encoder():
    """Real probe for a working GPU video encoder (Intel Quick Sync), not
    just checking whether ffmpeg lists h264_qsv -- an encoder can be listed
    but fail to initialize without the matching hardware/drivers. Cached for
    the life of the Streamlit process so this only ever runs once.
    """
    env = os.environ.copy()
    env["PATH"] = FFMPEG_BIN + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory() as tmp:
        probe_path = Path(tmp) / "probe.mp4"
        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.1",
                    "-c:v", "h264_qsv", "-frames:v", "1", str(probe_path),
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except Exception:
            return False
        return result.returncode == 0 and probe_path.exists()


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
    "Alvaro (Spanish, Male)": "es-ES-AlvaroNeural",
    "Elvira (Spanish, Female)": "es-ES-ElviraNeural",
    "Henri (French, Male)": "fr-FR-HenriNeural",
    "Denise (French, Female)": "fr-FR-DeniseNeural",
    "Conrad (German, Male)": "de-DE-ConradNeural",
    "Katja (German, Female)": "de-DE-KatjaNeural",
    "Diego (Italian, Male)": "it-IT-DiegoNeural",
    "Isabella (Italian, Female)": "it-IT-IsabellaNeural",
    "Antonio (Portuguese-BR, Male)": "pt-BR-AntonioNeural",
    "Francisca (Portuguese-BR, Female)": "pt-BR-FranciscaNeural",
    "Madhur (Hindi, Male)": "hi-IN-MadhurNeural",
    "Swara (Hindi, Female)": "hi-IN-SwaraNeural",
    "Keita (Japanese, Male)": "ja-JP-KeitaNeural",
    "Nanami (Japanese, Female)": "ja-JP-NanamiNeural",
    "Yunyang (Mandarin, Male)": "zh-CN-YunyangNeural",
    "Xiaoxiao (Mandarin, Female)": "zh-CN-XiaoxiaoNeural",
}
VOICE_VALUE_TO_LABEL = {v: k for k, v in VOICE_OPTIONS.items()}

QUALITY_OPTIONS = {
    "Low (fast preview, 480p15)": {"flag": "-ql", "folder": "480p15"},
    "Medium (720p30)": {"flag": "-qm", "folder": "720p30"},
    "High (1080p60)": {"flag": "-qh", "folder": "1080p60"},
    "4K (2160p60, slow)": {"flag": "-qk", "folder": "2160p60"},
}

FORMAT_OPTIONS = ["mp4", "mov", "webm"]

SAME_AS_QUESTION = "Same as question voice"

style_names = list(STYLE_REGISTRY.keys())
REVEAL_STYLE_LABELS = {name: name.replace("_", " ").title() for name in style_names}

theme_names = list(THEMES.keys())

ORIENTATION_OPTIONS = {"Landscape (16:9)": "landscape", "Portrait (9:16)": "portrait"}
ORIENTATION_VALUE_TO_LABEL = {v: k for k, v in ORIENTATION_OPTIONS.items()}

DEFAULT_SCRIPT = (
    "Q: Tell me about yourself.\n"
    "A: I'm a backend engineer with a few years of experience building and "
    "maintaining web services, and I enjoy working closely with product teams "
    "to ship features end to end.\n"
)
DEFAULT_OUTRO_MESSAGE = "Thanks for watching! Like and subscribe."
TEMPLATE_PLACEHOLDER = "— Select a template —"

# Manim's rich-based logger hard-wraps long lines (including file paths) at a
# fixed column width even when stdout isn't a real terminal, inserting
# newlines + indentation padding mid-path. To parse the real path reliably we
# strip ALL whitespace from the log before matching (file paths here never
# contain spaces), rather than matching against the raw multi-line text.
FILE_READY_RE = re.compile(r"Filereadyat'([^']+)'")

st.set_page_config(page_title="Interview Video Generator", page_icon="🎬", layout="wide")


# --- Session-state defaults (so "New Video" / "Open" can reset or restore) -

WIDGET_DEFAULTS = {
    "k_voice_label": list(VOICE_OPTIONS.keys())[0],
    "k_answer_voice_label": SAME_AS_QUESTION,
    "k_theme": "midnight" if "midnight" in theme_names else theme_names[0],
    "k_reveal_style_label": REVEAL_STYLE_LABELS.get("stacked", list(REVEAL_STYLE_LABELS.values())[0]),
    "k_orientation_label": "Landscape (16:9)",
    "k_add_fillers": False,
    "k_filler_rate": 0.15,
    "k_quality_label": list(QUALITY_OPTIONS.keys())[0],
    "k_video_format": FORMAT_OPTIONS[0],
    "k_burn_captions": False,
    "k_caption_style_label": "Default (white)",
    "k_script_text": DEFAULT_SCRIPT,
    "k_show_intro": False,
    "k_channel_name": "",
    "k_episode_title": "",
    "k_show_outro": False,
    "k_outro_message": DEFAULT_OUTRO_MESSAGE,
    "k_handle": "",
    "k_video_label": "",
    "k_template_select": TEMPLATE_PLACEHOLDER,
}

for _key, _default in WIDGET_DEFAULTS.items():
    st.session_state.setdefault(_key, _default)
st.session_state.setdefault("_uploader_version", 0)

TIMELINE_DEFAULT_SCRIPT = (
    TIMELINE_SCRIPT_FILE.read_text(encoding="utf-8")
    if TIMELINE_SCRIPT_FILE.exists()
    else "LABEL: 1947\nIndia gains independence from British rule.\n"
)
st.session_state.setdefault("k_tl_script_text", TIMELINE_DEFAULT_SCRIPT)

TL_WIDGET_DEFAULTS = {
    "k_tl_voice_label": list(VOICE_OPTIONS.keys())[0],
    "k_tl_theme": "midnight" if "midnight" in theme_names else theme_names[0],
    "k_tl_orientation_label": "Landscape (16:9)",
    "k_tl_show_intro": False,
    "k_tl_channel_name": "",
    "k_tl_show_outro": False,
    "k_tl_outro_message": DEFAULT_OUTRO_MESSAGE,
    "k_tl_quality_label": list(QUALITY_OPTIONS.keys())[0],
    "k_tl_burn_captions": False,
    "k_tl_caption_style_label": "Default (white)",
    "k_tl_video_label": "",
}
for _key, _default in TL_WIDGET_DEFAULTS.items():
    st.session_state.setdefault(_key, _default)
st.session_state.setdefault("_tl_uploader_version", 0)


def _restore_timeline_session(entry):
    """Load a saved Timeline-tab history entry's settings back into its widgets."""
    config = entry["config"]
    render_settings = entry.get("render_settings", {})

    st.session_state["k_tl_script_text"] = config.get("script_text") or TIMELINE_DEFAULT_SCRIPT
    st.session_state["k_tl_voice_label"] = VOICE_VALUE_TO_LABEL.get(
        config.get("voice"), TL_WIDGET_DEFAULTS["k_tl_voice_label"]
    )
    st.session_state["k_tl_theme"] = config.get("theme", TL_WIDGET_DEFAULTS["k_tl_theme"])
    st.session_state["k_tl_orientation_label"] = ORIENTATION_VALUE_TO_LABEL.get(
        config.get("orientation", "landscape"), "Landscape (16:9)"
    )
    st.session_state["k_tl_show_intro"] = bool(config.get("show_intro", False))
    st.session_state["k_tl_channel_name"] = config.get("channel_name", "")
    st.session_state["k_tl_show_outro"] = bool(config.get("show_outro", False))
    st.session_state["k_tl_outro_message"] = config.get("outro_message", DEFAULT_OUTRO_MESSAGE)
    st.session_state["k_tl_video_label"] = entry.get("label", "")

    st.session_state["k_tl_quality_label"] = render_settings.get(
        "quality_label", TL_WIDGET_DEFAULTS["k_tl_quality_label"]
    )
    st.session_state["k_tl_burn_captions"] = bool(render_settings.get("burn_captions", False))
    st.session_state["k_tl_caption_style_label"] = render_settings.get(
        "caption_style_label", "Default (white)"
    )

    st.session_state["_tl_uploader_version"] += 1
    st.session_state["_tl_upload_note"] = (
        "This session originally used background music — re-upload it below "
        "if you want to render with it again."
        if render_settings.get("had_music") else None
    )

    video_path = sessions.get_video_path(entry)
    st.session_state["_tl_display_video_path"] = str(video_path)
    st.session_state["_tl_display_video_label"] = entry["label"]
    st.session_state["_tl_display_session_id"] = entry["id"]
    st.session_state.pop("_tl_thumbnail_path", None)


def _restore_session(entry):
    """Load a saved history entry's settings back into the live widgets."""
    config = entry["config"]
    render_settings = entry.get("render_settings", {})

    st.session_state["k_script_text"] = config.get("script_text") or DEFAULT_SCRIPT
    st.session_state["k_voice_label"] = VOICE_VALUE_TO_LABEL.get(
        config.get("voice"), WIDGET_DEFAULTS["k_voice_label"]
    )
    answer_voice_val = config.get("answer_voice")
    st.session_state["k_answer_voice_label"] = (
        SAME_AS_QUESTION
        if not answer_voice_val
        else VOICE_VALUE_TO_LABEL.get(answer_voice_val, SAME_AS_QUESTION)
    )
    st.session_state["k_theme"] = config.get("theme", WIDGET_DEFAULTS["k_theme"])
    st.session_state["k_reveal_style_label"] = REVEAL_STYLE_LABELS.get(
        config.get("reveal_style", "stacked"), WIDGET_DEFAULTS["k_reveal_style_label"]
    )
    st.session_state["k_orientation_label"] = ORIENTATION_VALUE_TO_LABEL.get(
        config.get("orientation", "landscape"), "Landscape (16:9)"
    )
    st.session_state["k_add_fillers"] = bool(config.get("add_fillers", False))
    st.session_state["k_filler_rate"] = config.get("filler_rate", 0.15)
    st.session_state["k_show_intro"] = bool(config.get("show_intro", False))
    st.session_state["k_channel_name"] = config.get("channel_name", "")
    st.session_state["k_episode_title"] = config.get("episode_title", "")
    st.session_state["k_show_outro"] = bool(config.get("show_outro", False))
    st.session_state["k_outro_message"] = config.get("outro_message", DEFAULT_OUTRO_MESSAGE)
    st.session_state["k_handle"] = config.get("handle", "")
    st.session_state["k_video_label"] = entry.get("label", "")

    st.session_state["k_quality_label"] = render_settings.get(
        "quality_label", WIDGET_DEFAULTS["k_quality_label"]
    )
    st.session_state["k_video_format"] = render_settings.get("video_format", FORMAT_OPTIONS[0])
    st.session_state["k_burn_captions"] = bool(render_settings.get("burn_captions", False))
    st.session_state["k_caption_style_label"] = render_settings.get(
        "caption_style_label", "Default (white)"
    )

    # File uploads can't be programmatically restored into a file_uploader
    # widget, so just clear whatever is currently uploaded by giving the
    # uploaders a fresh key.
    st.session_state["_uploader_version"] += 1
    st.session_state["_upload_note"] = (
        "This session originally used a background image, background video, "
        "and/or music — re-upload them below if you want to render with them again."
        if config.get("background_image")
        or render_settings.get("had_music")
        or render_settings.get("had_bg_video")
        else None
    )

    video_path = sessions.get_video_path(entry)
    st.session_state["_display_video_path"] = str(video_path)
    st.session_state["_display_video_label"] = entry["label"]
    st.session_state["_display_session_id"] = entry["id"]
    st.session_state.pop("_thumbnail_path", None)
    st.session_state.pop("_dual_export_paths", None)


# --- Sidebar: history + reset ---------------------------------------------

_reset_col1, _reset_col2 = st.sidebar.columns(2)

if _reset_col1.button(
    "🆕 New Video",
    use_container_width=True,
    help="Clear the script and the shown video so you can start writing a new "
    "one. Keeps your current voice/theme/style/quality settings.",
):
    st.session_state["k_script_text"] = ""
    st.session_state["k_video_label"] = ""
    st.session_state["k_template_select"] = TEMPLATE_PLACEHOLDER
    for _k in (
        "_display_video_path", "_display_video_label", "_display_session_id",
        "_thumbnail_path", "_dual_export_paths",
    ):
        st.session_state.pop(_k, None)
    st.rerun()

if _reset_col2.button(
    "♻️ Reset Settings",
    use_container_width=True,
    help="Reset every setting (voice, theme, style, quality, intro/outro, "
    "uploads, ...) back to default, along with the script and shown video.",
):
    for _key, _default in WIDGET_DEFAULTS.items():
        st.session_state[_key] = _default
    st.session_state["_uploader_version"] += 1
    for _k in (
        "_display_video_path", "_display_video_label", "_display_session_id",
        "_upload_note", "_thumbnail_path", "_dual_export_paths",
    ):
        st.session_state.pop(_k, None)
    st.rerun()

st.sidebar.subheader("📁 Previous videos")
history = sessions.list_sessions()
if not history:
    st.sidebar.caption("No videos generated yet.")
else:
    for entry in history:
        when = entry["created_at"].replace("T", " ")[:16]
        kind = entry.get("kind", "interview")
        kind_tag = " 🕰️" if kind == "timeline" else ""
        with st.sidebar.expander(f"{entry['label']}{kind_tag}  ·  {when}"):
            col_a, col_b = st.columns(2)
            # These two buttons must run (and, for Open, mutate session_state)
            # before any widget below is instantiated in this same script run
            # — Streamlit forbids writing to a widget's session_state key
            # after that widget has already been created this run.
            if col_a.button("Open", key=f"open_{entry['id']}", use_container_width=True):
                if kind == "timeline":
                    _restore_timeline_session(entry)
                else:
                    _restore_session(entry)
                st.rerun()
            if col_b.button("Delete", key=f"delete_{entry['id']}", use_container_width=True):
                sessions.delete_session(entry["id"])
                if kind == "timeline":
                    if st.session_state.get("_tl_display_session_id") == entry["id"]:
                        for _k in (
                            "_tl_display_video_path", "_tl_display_video_label",
                            "_tl_display_session_id", "_tl_thumbnail_path",
                        ):
                            st.session_state.pop(_k, None)
                elif st.session_state.get("_display_session_id") == entry["id"]:
                    for _k in (
                        "_display_video_path", "_display_video_label", "_display_session_id",
                        "_thumbnail_path", "_dual_export_paths",
                    ):
                        st.session_state.pop(_k, None)
                st.rerun()

st.sidebar.divider()


# --- Sidebar: settings ----------------------------------------------------

st.sidebar.header("Settings")

voice_label = st.sidebar.selectbox("Question voice", list(VOICE_OPTIONS.keys()), key="k_voice_label")
voice = VOICE_OPTIONS[voice_label]

answer_voice_label = st.sidebar.selectbox(
    "Answer voice", [SAME_AS_QUESTION] + list(VOICE_OPTIONS.keys()), key="k_answer_voice_label"
)
answer_voice = (
    None if answer_voice_label == SAME_AS_QUESTION else VOICE_OPTIONS[answer_voice_label]
)
st.sidebar.caption("Pick a different voice for answers to make it sound like two people.")

theme = st.sidebar.selectbox("Theme", theme_names, key="k_theme")
st.sidebar.caption("Background gradient and text colors. Ignored if a background image is uploaded.")

reveal_style_label = st.sidebar.selectbox(
    "Reveal style",
    [REVEAL_STYLE_LABELS[name] for name in style_names],
    key="k_reveal_style_label",
)
reveal_style = style_names[
    [REVEAL_STYLE_LABELS[name] for name in style_names].index(reveal_style_label)
]
st.sidebar.caption("How the question and answer text appears on screen.")

st.sidebar.subheader("Background image (optional)")
if st.session_state.get("_upload_note"):
    st.sidebar.caption(st.session_state["_upload_note"])
bg_upload = st.sidebar.file_uploader(
    "Upload a custom background",
    type=["png", "jpg", "jpeg"],
    key=f"k_bg_upload_{st.session_state['_uploader_version']}",
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

st.sidebar.subheader("Background video (optional)")
bg_video_upload = st.sidebar.file_uploader(
    "Upload a looping background video",
    type=["mp4", "mov", "webm", "m4v"],
    key=f"k_bg_video_upload_{st.session_state['_uploader_version']}",
)
bg_video_path = None
bg_video_loop = True
if bg_video_upload is not None:
    BG_VIDEO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_bg_video_path = BG_VIDEO_UPLOAD_DIR / bg_video_upload.name
    with open(saved_bg_video_path, "wb") as f:
        f.write(bg_video_upload.getbuffer())
    bg_video_path = str(saved_bg_video_path.resolve())
    st.sidebar.video(bg_video_upload)
    bg_video_loop = st.sidebar.checkbox("Loop background video to fill the duration", value=True)
    st.sidebar.caption(
        "Overrides the theme gradient AND any background image — only one "
        "background can be active at a time. Rendering takes noticeably "
        "longer (manim renders with a transparent background first, then "
        "this is composited on top in a separate ffmpeg pass)."
    )
else:
    st.sidebar.caption("No video uploaded.")

st.sidebar.subheader("Background music (optional)")
music_upload = st.sidebar.file_uploader(
    "Upload a music track",
    type=["mp3", "wav", "m4a", "ogg"],
    key=f"k_music_upload_{st.session_state['_uploader_version']}",
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

st.sidebar.subheader("Captions (optional)")
burn_captions = st.sidebar.checkbox("Burn captions into the video", key="k_burn_captions")
caption_style = "default"
caption_style_label = "Default (white)"
if burn_captions:
    CAPTION_STYLE_OPTIONS = {
        "Default (white)": "default",
        "Bold (yellow)": "bold",
        "Match theme accent color": f"theme:{theme}",
    }
    caption_style_label = st.sidebar.selectbox(
        "Caption style", list(CAPTION_STYLE_OPTIONS.keys()), key="k_caption_style_label"
    )
    caption_style = CAPTION_STYLE_OPTIONS[caption_style_label]
    st.sidebar.caption(
        "Hardcodes the auto-generated subtitles onto the video frames. "
        "Re-encodes the video, so it's slower than the rest of the pipeline."
    )
else:
    st.sidebar.caption("Subtitles are still generated as a separate .srt file either way.")

st.sidebar.subheader("Orientation")
orientation_label = st.sidebar.selectbox(
    "Orientation", list(ORIENTATION_OPTIONS.keys()), key="k_orientation_label"
)
orientation = ORIENTATION_OPTIONS[orientation_label]
st.sidebar.caption("Portrait renders a tall 9:16 frame for Shorts/Reels/TikTok instead of widescreen.")

st.sidebar.subheader("Realism (optional)")
add_fillers_enabled = st.sidebar.checkbox("Add natural filler words (um, uh...)", key="k_add_fillers")
filler_rate = 0.15
if add_fillers_enabled:
    filler_rate = st.sidebar.slider("Filler frequency", 0.0, 1.0, step=0.05, key="k_filler_rate")
    st.sidebar.caption("Inserts natural-sounding fillers into answers only, never questions.")

st.sidebar.subheader("Video quality")
quality_label = st.sidebar.selectbox("Quality", list(QUALITY_OPTIONS.keys()), key="k_quality_label")
quality = QUALITY_OPTIONS[quality_label]
st.sidebar.caption("Low renders fastest — good for quick iteration. Higher quality takes longer.")

st.sidebar.subheader("Video format")
video_format = st.sidebar.selectbox("Format", FORMAT_OPTIONS, key="k_video_format")
st.sidebar.caption("mp4 is the safest default for uploading to most platforms.")

st.sidebar.subheader("Performance")
use_gpu = detect_gpu_encoder()
st.sidebar.caption(
    "⚡ GPU-accelerated encoding active (Intel Quick Sync) — measured ~40% "
    "faster than CPU encoding on this machine."
    if use_gpu else
    "No compatible GPU encoder detected — using CPU encoding."
)


# --- Main area: script + intro/outro --------------------------------------

tab_interview, tab_timeline = st.tabs(["🗣️ Interview Q&A", "🕰️ Timeline (Testing)"])

with tab_interview:
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
    with st.expander("✨ Text formatting (bold, italic, highlight)"):
        st.markdown(
            "Add emphasis anywhere in a question or answer and it'll show up "
            "styled on screen — the narration and subtitles still speak the "
            "plain words, never the symbols.\n\n"
            "| Type this | To get |\n"
            "|---|---|\n"
            "| `**bold**` or `__bold__` | **bold** text |\n"
            "| `*italic*` | *italic* text |\n"
            "| `==highlight==` | a highlighted word/phrase (accent color) |\n\n"
            "Example:\n"
            "```\nA: I'm a **backend engineer** who enjoys *solving hard "
            "problems* and has led ==three production migrations==.\n```"
        )
    _template_col1, _template_col2 = st.columns([4, 1])
    with _template_col1:
        st.selectbox(
            "Load a starter template (optional)",
            [TEMPLATE_PLACEHOLDER] + question_bank.list_templates(),
            key="k_template_select",
            label_visibility="collapsed",
        )
    with _template_col2:
        if st.button("Load template", use_container_width=True):
            if st.session_state["k_template_select"] == TEMPLATE_PLACEHOLDER:
                st.warning("Pick a template first.")
            else:
                st.session_state["k_script_text"] = question_bank.get_template(
                    st.session_state["k_template_select"]
                )
                st.rerun()

    script_text = st.text_area(
        "Q&A script",
        height=280,
        label_visibility="collapsed",
        key="k_script_text",
    )

    col1, col2 = st.columns(2)

    with col1:
        show_intro = st.checkbox("Include intro card", key="k_show_intro")
        channel_name = ""
        episode_title = ""
        if show_intro:
            channel_name = st.text_input("Channel name", key="k_channel_name")
            episode_title = st.text_input("Episode title (optional)", key="k_episode_title")

    with col2:
        show_outro = st.checkbox("Include outro card", key="k_show_outro")
        outro_message = DEFAULT_OUTRO_MESSAGE
        handle = ""
        if show_outro:
            outro_message = st.text_input("Outro message", key="k_outro_message")
            handle = st.text_input("Handle (optional, e.g. @yourhandle)", key="k_handle")

    st.text_input(
        "Name this video (optional, shown in your history list)",
        key="k_video_label",
        placeholder="e.g. Backend Engineer Practice #1",
    )

    st.divider()

    is_busy = st.session_state.get("_busy") is not None

    _gen_col1, _gen_col2 = st.columns(2)
    with _gen_col1:
        generate_clicked = st.button(
            "🎬 Generate Video", type="primary", use_container_width=True, disabled=is_busy
        )
    with _gen_col2:
        dual_export_clicked = st.button(
            "📤 Export Both Orientations (16:9 + 9:16)",
            use_container_width=True,
            disabled=is_busy,
        )

    output_container = st.container()


    def build_gui_config():
        return {
            "script_text": script_text if script_text.strip() else None,
            "voice": voice,
            "answer_voice": answer_voice,
            "theme": theme,
            "reveal_style": reveal_style,
            "orientation": orientation,
            "add_fillers": bool(add_fillers_enabled),
            "filler_rate": filler_rate,
            "background_image": background_image_path,
            "background_video": bg_video_path,
            "show_intro": bool(show_intro),
            "channel_name": channel_name,
            "episode_title": episode_title,
            "show_outro": bool(show_outro),
            "outro_message": outro_message,
            "handle": handle,
        }


    def derive_label(config):
        typed = st.session_state.get("k_video_label", "").strip()
        if typed:
            return typed
        try:
            pairs = (
                qa_format.parse_qa_text(config["script_text"])
                if config["script_text"]
                else qa_format.parse_qa_file("interview_script.txt")
            )
        except Exception:
            pairs = []
        if pairs:
            q = pairs[0][0].strip()
            return (q[:40] + "...") if len(q) > 40 else q
        return "Untitled video"


    def expected_output_path(render_format):
        """Fallback path based on manim's known output folder layout."""
        return (
            BASE_DIR
            / "media"
            / "videos"
            / "interview_simulation"
            / quality["folder"]
            / f"InterviewSimulation.{render_format}"
        )


    def run_render():
        config = build_gui_config()
        with open(GUI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # A background video requires manim to render with a transparent
        # background (-t) so it can be composited on top afterward -- that only
        # produces a .mov on this manim install (see AGENTS.md's "Background
        # video" section), so the user's chosen format is overridden here and
        # restored once add_background_video.py produces the final opaque mp4.
        render_format = "mov" if bg_video_path else video_format
        cmd = [
            str(VENV_PYTHON),
            "-m",
            "manim",
            quality["flag"],
            "--format",
            render_format,
            "--disable_caching",
            "interview_simulation.py",
            "InterviewSimulation",
        ]
        if bg_video_path:
            cmd.append("-t")
        elif use_gpu:
            # Transparent (-t) renders are forced to the qtrle codec for their
            # alpha channel, which GPU encoding can't produce -- only apply
            # GPU encoding on the normal (non-background-video) render path.
            cmd += ["--video-codec", "h264_qsv", "--pixel-format", "nv12"]

        env = os.environ.copy()
        env["PATH"] = FFMPEG_BIN + os.pathsep + env.get("PATH", "")

        log_lines = []
        status_box = output_container.empty()
        progress_bar = output_container.progress(0.0, text="Starting render...")
        log_expander = output_container.expander("Show detailed render log", expanded=False)
        log_box = log_expander.empty()
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

        start_time = time.time()
        for line in process.stdout:
            stripped = line.rstrip("\n")
            log_lines.append(stripped)
            log_box.code("\n".join(log_lines[-200:]), language="text")
            elapsed = time.time() - start_time
            # The real render duration isn't known upfront, so this is a capped
            # elapsed-time animation rather than an exact percentage -- honest
            # progress feedback without parsing manim's log for a real total.
            fraction = min(0.95, elapsed / 60)
            last_info = next((l.strip() for l in reversed(log_lines) if l.strip()), "")
            progress_bar.progress(fraction, text=f"Rendering... {elapsed:.0f}s elapsed — {last_info[:80]}")

        returncode = process.wait()
        full_log = "\n".join(log_lines)
        # Collapse all whitespace/newlines before matching, since manim's console
        # output hard-wraps long lines (including file paths) with indentation.
        flattened_log = re.sub(r"\s+", "", full_log)

        if returncode == 0:
            progress_bar.progress(1.0, text="Render complete!")
            status_box.success("Render complete!")
            match = FILE_READY_RE.search(flattened_log)
            output_path = Path(match.group(1)) if match else expected_output_path(render_format)

            if output_path.exists():
                final_path = output_path

                if bg_video_path:
                    composited_path = output_path.with_name(
                        output_path.stem + "_with_bg_video.mp4"
                    )
                    bg_video_cmd = [
                        str(VENV_PYTHON),
                        str(ADD_BG_VIDEO_SCRIPT),
                        str(output_path),
                        bg_video_path,
                        "--output",
                        str(composited_path),
                        "--loop" if bg_video_loop else "--no-loop",
                    ]
                    if use_gpu:
                        bg_video_cmd.append("--gpu")
                    status_box.info("Compositing background video...")
                    bg_video_result = subprocess.run(
                        bg_video_cmd,
                        cwd=str(BASE_DIR),
                        env=env,
                        capture_output=True,
                        text=True,
                    )
                    if bg_video_result.returncode == 0 and composited_path.exists():
                        final_path = composited_path
                        status_box.success("Render complete, background video composited!")
                    else:
                        status_box.warning(
                            "Render succeeded, but compositing the background video "
                            "failed — showing the plain transparent render instead."
                        )
                        st.caption(
                            "```\n" + bg_video_result.stdout[-1500:]
                            + bg_video_result.stderr[-1500:] + "\n```"
                        )

                if music_path:
                    mixed_path = final_path.with_name(
                        final_path.stem + "_with_music" + final_path.suffix
                    )
                    music_cmd = [
                        str(VENV_PYTHON),
                        str(ADD_MUSIC_SCRIPT),
                        str(final_path),
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

                if burn_captions:
                    srt_path = output_path.with_suffix(".srt")
                    if srt_path.exists():
                        captioned_path = final_path.with_name(
                            final_path.stem + "_captioned" + final_path.suffix
                        )
                        caption_cmd = [
                            str(VENV_PYTHON),
                            str(BURN_SUBTITLES_SCRIPT),
                            str(final_path),
                            str(srt_path),
                            "--output",
                            str(captioned_path),
                            "--style",
                            caption_style,
                        ]
                        if use_gpu:
                            caption_cmd.append("--gpu")
                        status_box.info("Burning in captions...")
                        caption_result = subprocess.run(
                            caption_cmd,
                            cwd=str(BASE_DIR),
                            env=env,
                            capture_output=True,
                            text=True,
                        )
                        if caption_result.returncode == 0 and captioned_path.exists():
                            final_path = captioned_path
                            status_box.success("Render complete, with captions burned in!")
                        else:
                            status_box.warning(
                                "Render succeeded, but burning in captions failed — "
                                "showing the version without burned-in captions instead."
                            )
                            st.caption("```\n" + caption_result.stdout[-1500:] + "\n```")
                    else:
                        st.warning(
                            f"Burn-captions was requested, but no subtitle file was found at "
                            f"{srt_path} — skipping."
                        )

                label = derive_label(config)
                render_settings = {
                    "quality_label": quality_label,
                    "video_format": video_format,
                    "burn_captions": bool(burn_captions),
                    "caption_style_label": caption_style_label,
                    "had_music": bool(music_path),
                    "had_bg_video": bool(bg_video_path),
                }
                session_id, dest_video = sessions.save_session(
                    config, final_path, label, render_settings
                )
                st.session_state["_display_video_path"] = str(dest_video)
                st.session_state["_display_video_label"] = label
                st.session_state["_display_session_id"] = session_id
                st.session_state["_busy"] = None
                st.rerun()
            else:
                st.error(
                    f"Render reported success, but the output file could not be found at "
                    f"{output_path}. Check the log above for the actual path."
                )
                st.session_state["_busy"] = None
                st.rerun()
        else:
            progress_bar.empty()
            status_box.error(f"Render failed (exit code {returncode}). See log tail below.")
            st.error("```\n" + "\n".join(log_lines[-40:]) + "\n```")
            st.session_state["_busy"] = None
            st.rerun()


    def run_dual_export():
        slug = re.sub(
            r"[^a-zA-Z0-9_-]+", "_",
            st.session_state.get("k_video_label", "").strip() or "dual_export",
        ).strip("_") or "dual_export"
        script_path = BASE_DIR / f"_dual_export_{slug}.txt"
        script_path.write_text(script_text, encoding="utf-8")

        output_dir = DUAL_EXPORT_DIR / slug
        cmd = [
            str(VENV_PYTHON), str(EXPORT_DUAL_SCRIPT), str(script_path),
            "--quality", quality["flag"].lstrip("-"),
            "--theme", theme,
            "--voice", voice,
            "--reveal-style", reveal_style,
            "--output-dir", str(output_dir),
        ]
        if answer_voice:
            cmd += ["--answer-voice", answer_voice]

        env = os.environ.copy()
        env["PATH"] = FFMPEG_BIN + os.pathsep + env.get("PATH", "")

        status_box = output_container.empty()
        status_box.info(
            "Exporting both orientations... this renders the video twice, "
            "so it takes roughly 2x as long as a single render."
        )
        log_expander = output_container.expander("Show detailed export log", expanded=False)

        try:
            result = subprocess.run(cmd, cwd=str(BASE_DIR), env=env, capture_output=True, text=True)
            log_expander.code(result.stdout[-4000:], language="text")
        finally:
            script_path.unlink(missing_ok=True)

        if result.returncode == 0:
            landscape = output_dir / "landscape.mp4"
            portrait = output_dir / "portrait.mp4"
            if landscape.exists() and portrait.exists():
                st.session_state["_dual_export_paths"] = {
                    "landscape": str(landscape), "portrait": str(portrait),
                }
                st.session_state["_busy"] = None
                st.rerun()
            else:
                status_box.error("Export reported success but the output files are missing.")
                st.session_state["_busy"] = None
                st.rerun()
        else:
            status_box.error("Dual export failed. See log above.")
            st.session_state["_busy"] = None
            st.rerun()


    if generate_clicked:
        if not script_text.strip():
            st.error("Please enter a Q&A script before generating a video.")
        else:
            try:
                qa_format.parse_qa_text(script_text)
            except ValueError as e:
                st.error(f"Script format problem: {e}")
            else:
                # Set the busy flag and rerun BEFORE doing the actual (slow)
                # work, rather than calling run_render() directly here: the
                # Generate/Export buttons above were already sent to the
                # browser as enabled for this run by the time we reach this
                # code, so disabling them only takes effect starting next
                # run -- this rerun is what makes that next run happen
                # before the long subprocess call blocks the script.
                st.session_state["_busy"] = "generate"
                st.rerun()
    elif dual_export_clicked:
        if not script_text.strip():
            st.error("Please enter a Q&A script before generating a video.")
        else:
            try:
                qa_format.parse_qa_text(script_text)
            except ValueError as e:
                st.error(f"Script format problem: {e}")
            else:
                st.session_state["_busy"] = "dual_export"
                st.rerun()
    elif st.session_state.get("_busy") == "generate":
        run_render()
    elif st.session_state.get("_busy") == "dual_export":
        run_dual_export()
    else:
        if st.session_state.get("_display_video_path"):
            display_path = Path(st.session_state["_display_video_path"])
            if display_path.exists():
                output_container.caption(f"Showing: {st.session_state.get('_display_video_label', '')}")
                output_container.video(str(display_path))
                suffix = display_path.suffix.lstrip(".")
                mime = f"video/{'quicktime' if suffix == 'mov' else suffix}"
                with open(display_path, "rb") as f:
                    output_container.download_button(
                        "Download video",
                        data=f.read(),
                        file_name=display_path.name,
                        mime=mime,
                        key="download_current",
                    )

                if output_container.button("🖼️ Generate thumbnail", key="gen_thumb_btn"):
                    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
                    thumb_path = THUMBNAIL_DIR / f"{display_path.stem}_thumbnail.png"
                    generate_thumbnail.generate_thumbnail(
                        title=st.session_state.get("_display_video_label") or "Interview Practice",
                        subtitle=channel_name or None,
                        theme_name=theme,
                        output_path=str(thumb_path),
                    )
                    st.session_state["_thumbnail_path"] = str(thumb_path)

                thumb_state_path = st.session_state.get("_thumbnail_path")
                if thumb_state_path and Path(thumb_state_path).exists():
                    output_container.image(thumb_state_path, caption="Thumbnail preview", width=400)
                    with open(thumb_state_path, "rb") as f:
                        output_container.download_button(
                            "Download thumbnail",
                            data=f.read(),
                            file_name=Path(thumb_state_path).name,
                            mime="image/png",
                            key="download_thumbnail",
                        )
            else:
                output_container.warning("That video's file is missing from disk.")

        dual_paths = st.session_state.get("_dual_export_paths")
        if dual_paths:
            output_container.divider()
            output_container.subheader("Dual orientation export")
            dcol1, dcol2 = output_container.columns(2)
            for col, key, label in (
                (dcol1, "landscape", "Landscape (16:9)"), (dcol2, "portrait", "Portrait (9:16)")
            ):
                p = Path(dual_paths[key])
                if p.exists():
                    col.caption(label)
                    col.video(str(p))
                    with open(p, "rb") as f:
                        col.download_button(
                            f"Download {label}", data=f.read(), file_name=p.name,
                            mime="video/mp4", key=f"dl_dual_{key}",
                        )
                else:
                    col.warning(f"{label} file missing.")

with tab_timeline:
    st.title("Timeline / History Video Generator (Testing)")
    st.caption(
        "Experimental — renders timeline_video/timeline_simulation.py. This tab "
        "has its own settings below (it ignores the sidebar, which belongs to "
        "the Interview tab)."
    )

    with st.expander("Script format help"):
        st.markdown(
            "Blank-line separated scenes. `LABEL:` and `IMAGE:` are both "
            "optional and must come before the narration text if present. "
            "`IMAGE:` paths are resolved relative to `timeline_video/`.\n\n"
            "```\nLABEL: 1947\nIMAGE: images/independence.jpg\n"
            "India had just emerged from two centuries of British rule...\n```"
        )

    timeline_script_text = st.text_area(
        "Timeline script", height=280, key="k_tl_script_text",
    )

    tl_col1, tl_col2, tl_col3 = st.columns(3)
    with tl_col1:
        tl_voice_label = st.selectbox(
            "Voice", list(VOICE_OPTIONS.keys()), key="k_tl_voice_label"
        )
        tl_voice = VOICE_OPTIONS[tl_voice_label]
    with tl_col2:
        tl_theme = st.selectbox("Theme", theme_names, key="k_tl_theme")
    with tl_col3:
        tl_orientation_label = st.selectbox(
            "Orientation", list(ORIENTATION_OPTIONS.keys()), key="k_tl_orientation_label"
        )
        tl_orientation = ORIENTATION_OPTIONS[tl_orientation_label]

    tl_col4, tl_col5 = st.columns(2)
    with tl_col4:
        tl_show_intro = st.checkbox("Include intro card", key="k_tl_show_intro")
        tl_channel_name = (
            st.text_input("Channel name", key="k_tl_channel_name") if tl_show_intro else ""
        )
    with tl_col5:
        tl_show_outro = st.checkbox("Include outro card", key="k_tl_show_outro")
        tl_outro_message = (
            st.text_input("Outro message", value=DEFAULT_OUTRO_MESSAGE, key="k_tl_outro_message")
            if tl_show_outro else DEFAULT_OUTRO_MESSAGE
        )

    st.subheader("Background music (optional)")
    if st.session_state.get("_tl_upload_note"):
        st.caption(st.session_state["_tl_upload_note"])
    tl_music_upload = st.file_uploader(
        "Upload a music track",
        type=["mp3", "wav", "m4a", "ogg"],
        key=f"k_tl_music_upload_{st.session_state['_tl_uploader_version']}",
    )
    tl_music_path = None
    tl_music_loop = True
    if tl_music_upload is not None:
        MUSIC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        tl_saved_music_path = MUSIC_UPLOAD_DIR / tl_music_upload.name
        with open(tl_saved_music_path, "wb") as f:
            f.write(tl_music_upload.getbuffer())
        tl_music_path = str(tl_saved_music_path.resolve())
        st.audio(tl_music_upload)
        tl_music_loop = st.checkbox("Loop music to fill the video", value=True, key="k_tl_music_loop")
    else:
        st.caption("No track uploaded — the video will have narration audio only.")

    st.subheader("Captions (optional)")
    tl_burn_captions = st.checkbox("Burn captions into the video", key="k_tl_burn_captions")
    tl_caption_style = "default"
    tl_caption_style_label = "Default (white)"
    if tl_burn_captions:
        TL_CAPTION_STYLE_OPTIONS = {
            "Default (white)": "default",
            "Bold (yellow)": "bold",
            "Match theme accent color": f"theme:{tl_theme}",
        }
        tl_caption_style_label = st.selectbox(
            "Caption style", list(TL_CAPTION_STYLE_OPTIONS.keys()), key="k_tl_caption_style_label"
        )
        tl_caption_style = TL_CAPTION_STYLE_OPTIONS[tl_caption_style_label]
    else:
        st.caption("Subtitles are still generated as a separate .srt file either way.")

    tl_quality_label = st.selectbox(
        "Quality", list(QUALITY_OPTIONS.keys()), key="k_tl_quality_label"
    )
    tl_quality = QUALITY_OPTIONS[tl_quality_label]

    st.text_input(
        "Name this video (optional, shown in history)",
        key="k_tl_video_label",
        placeholder="e.g. India History Timeline #1",
    )

    tl_generate_clicked = st.button(
        "🕰️ Generate Timeline Video", type="primary", key="tl_generate_btn"
    )
    tl_output_container = st.container()

    def build_timeline_config():
        return {
            "script_text": timeline_script_text if timeline_script_text.strip() else None,
            "voice": tl_voice,
            "theme": tl_theme,
            "orientation": tl_orientation,
            "show_intro": bool(tl_show_intro),
            "channel_name": tl_channel_name,
            "episode_title": "",
            "show_outro": bool(tl_show_outro),
            "outro_message": tl_outro_message,
            "handle": "",
        }

    def tl_derive_label(config):
        typed = st.session_state.get("k_tl_video_label", "").strip()
        if typed:
            return typed
        try:
            scenes = (
                timeline_format.parse_timeline_text(config["script_text"])
                if config["script_text"]
                else timeline_format.parse_timeline_file(TIMELINE_SCRIPT_FILE)
            )
        except Exception:
            scenes = []
        if scenes:
            first = scenes[0]
            if first.get("label"):
                return first["label"]
            text = first["text"].strip()
            return (text[:40] + "...") if len(text) > 40 else text
        return "Untitled timeline video"

    def run_timeline_render():
        tl_config = build_timeline_config()
        with open(TIMELINE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(tl_config, f, indent=2)

        cmd = [
            str(VENV_PYTHON), "-m", "manim", tl_quality["flag"], "--disable_caching",
            str(TIMELINE_SCRIPT_PY), "TimelineVideo",
        ]
        env = os.environ.copy()
        env["PATH"] = FFMPEG_BIN + os.pathsep + env.get("PATH", "")

        log_lines = []
        status_box = tl_output_container.empty()
        progress_bar = tl_output_container.progress(0.0, text="Starting render...")
        log_expander = tl_output_container.expander("Show detailed render log", expanded=False)
        log_box = log_expander.empty()
        status_box.info("Rendering... this can take anywhere from tens of seconds to a few minutes.")

        process = subprocess.Popen(
            cmd, cwd=str(BASE_DIR), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )

        start_time = time.time()
        for line in process.stdout:
            stripped = line.rstrip("\n")
            log_lines.append(stripped)
            log_box.code("\n".join(log_lines[-200:]), language="text")
            elapsed = time.time() - start_time
            fraction = min(0.95, elapsed / 60)
            last_info = next((l.strip() for l in reversed(log_lines) if l.strip()), "")
            progress_bar.progress(fraction, text=f"Rendering... {elapsed:.0f}s elapsed — {last_info[:80]}")

        returncode = process.wait()
        full_log = "\n".join(log_lines)
        flattened_log = re.sub(r"\s+", "", full_log)

        if returncode != 0:
            progress_bar.empty()
            status_box.error(f"Render failed (exit code {returncode}). See log tail below.")
            st.error("```\n" + "\n".join(log_lines[-40:]) + "\n```")
            return

        progress_bar.progress(1.0, text="Render complete!")
        status_box.success("Render complete!")
        match = FILE_READY_RE.search(flattened_log)
        output_path = Path(match.group(1)) if match else (
            BASE_DIR / "media" / "videos" / "timeline_simulation"
            / tl_quality["folder"] / "TimelineVideo.mp4"
        )
        if not output_path.exists():
            st.error(
                f"Render reported success, but the output file could not be found "
                f"at {output_path}. Check the log above for the actual path."
            )
            return

        final_path = output_path

        if tl_music_path:
            mixed_path = final_path.with_name(final_path.stem + "_with_music" + final_path.suffix)
            music_cmd = [
                str(VENV_PYTHON), str(ADD_MUSIC_SCRIPT), str(final_path), tl_music_path,
                "--output", str(mixed_path), "--loop" if tl_music_loop else "--no-loop",
            ]
            status_box.info("Mixing in background music...")
            music_result = subprocess.run(
                music_cmd, cwd=str(BASE_DIR), env=env, capture_output=True, text=True,
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

        if tl_burn_captions:
            srt_path = output_path.with_suffix(".srt")
            if srt_path.exists():
                captioned_path = final_path.with_name(
                    final_path.stem + "_captioned" + final_path.suffix
                )
                caption_cmd = [
                    str(VENV_PYTHON), str(BURN_SUBTITLES_SCRIPT), str(final_path), str(srt_path),
                    "--output", str(captioned_path), "--style", tl_caption_style,
                ]
                status_box.info("Burning in captions...")
                caption_result = subprocess.run(
                    caption_cmd, cwd=str(BASE_DIR), env=env, capture_output=True, text=True,
                )
                if caption_result.returncode == 0 and captioned_path.exists():
                    final_path = captioned_path
                    status_box.success("Render complete, with captions burned in!")
                else:
                    status_box.warning(
                        "Render succeeded, but burning in captions failed — "
                        "showing the version without burned-in captions instead."
                    )
                    st.caption("```\n" + caption_result.stdout[-1500:] + "\n```")
            else:
                st.warning(
                    f"Burn-captions was requested, but no subtitle file was found at "
                    f"{srt_path} — skipping."
                )

        label = tl_derive_label(tl_config)
        render_settings = {
            "quality_label": tl_quality_label,
            "burn_captions": bool(tl_burn_captions),
            "caption_style_label": tl_caption_style_label,
            "had_music": bool(tl_music_path),
        }
        session_id, dest_video = sessions.save_session(
            tl_config, final_path, label, render_settings, kind="timeline"
        )
        st.session_state["_tl_display_video_path"] = str(dest_video)
        st.session_state["_tl_display_video_label"] = label
        st.session_state["_tl_display_session_id"] = session_id
        st.session_state.pop("_tl_thumbnail_path", None)
        st.rerun()

    if tl_generate_clicked:
        if not timeline_script_text.strip():
            st.error("Please enter a timeline script before generating a video.")
        else:
            try:
                timeline_format.parse_timeline_text(timeline_script_text)
            except ValueError as e:
                st.error(f"Script format problem: {e}")
            else:
                run_timeline_render()
    else:
        tl_display_path = st.session_state.get("_tl_display_video_path")
        if tl_display_path and Path(tl_display_path).exists():
            tl_display_path = Path(tl_display_path)
            tl_output_container.caption(
                f"Showing: {st.session_state.get('_tl_display_video_label', '')}"
            )
            tl_output_container.video(str(tl_display_path))
            with open(tl_display_path, "rb") as f:
                tl_output_container.download_button(
                    "Download video", data=f.read(),
                    file_name=tl_display_path.name, mime="video/mp4",
                    key="tl_download_current",
                )

            if tl_output_container.button("🖼️ Generate thumbnail", key="tl_gen_thumb_btn"):
                THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
                tl_thumb_path = THUMBNAIL_DIR / f"{tl_display_path.stem}_thumbnail.png"
                generate_thumbnail.generate_thumbnail(
                    title=st.session_state.get("_tl_display_video_label") or "History Timeline",
                    subtitle=tl_channel_name or None,
                    theme_name=tl_theme,
                    output_path=str(tl_thumb_path),
                )
                st.session_state["_tl_thumbnail_path"] = str(tl_thumb_path)

            tl_thumb_state_path = st.session_state.get("_tl_thumbnail_path")
            if tl_thumb_state_path and Path(tl_thumb_state_path).exists():
                tl_output_container.image(tl_thumb_state_path, caption="Thumbnail preview", width=400)
                with open(tl_thumb_state_path, "rb") as f:
                    tl_output_container.download_button(
                        "Download thumbnail",
                        data=f.read(),
                        file_name=Path(tl_thumb_state_path).name,
                        mime="image/png",
                        key="tl_download_thumbnail",
                    )
        elif tl_display_path:
            tl_output_container.warning("That video's file is missing from disk.")
