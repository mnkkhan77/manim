# Run with:
#   venv/Scripts/python.exe -m manim -ql interview_simulation.py InterviewSimulation --disable_caching
# Swap -ql for -qm/-qh/-qk for higher quality. Reads gui_config.json if present
# (see DEFAULT_CONFIG below and AGENTS.md), otherwise falls back to interview_script.txt.
import json
from pathlib import Path

from manim import *
from manim_voiceover import VoiceoverScene

import style_chat_bubbles
import style_podcast
import style_sticky_notes
import style_split_screen
import style_stacked
import style_terminal
import style_whiteboard
from branding import build_intro_card, build_outro_card
from edge_tts_service import EdgeTTSService, resolve_narration_speed
from filler_words import add_fillers
from qa_format import parse_qa_file, parse_qa_text
from themes import get_theme

SCRIPT_FILE = "interview_script.txt"
CONFIG_FILE = "gui_config.json"

STYLE_REGISTRY = {
    "stacked": style_stacked.render,
    "terminal": style_terminal.render,
    "chat_bubbles": style_chat_bubbles.render,
    "split_screen": style_split_screen.render,
    "sticky_notes": style_sticky_notes.render,
    "whiteboard": style_whiteboard.render,
    "podcast": style_podcast.render,
}

DEFAULT_CONFIG = {
    "script_text": None,
    "voice": "en-US-AndrewNeural",
    "answer_voice": None,
    "narration_speed": 1.0,
    "theme": "midnight",
    "background_image": None,
    "background_video": None,
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


def load_gui_config():
    config_dict = dict(DEFAULT_CONFIG)
    config_path = Path(CONFIG_FILE)
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config_dict.update(json.load(f))
    return config_dict


class InterviewSimulation(VoiceoverScene):
    def __init__(self, **kwargs):
        # Scene.__init__ builds the camera (and its pixel buffer) from
        # config.pixel_width/height — by the time construct() runs, that's
        # already fixed. So the portrait resolution switch has to happen
        # here, before super().__init__(), not in construct().
        gui_config = load_gui_config()
        if gui_config.get("orientation", "landscape") == "portrait":
            # 9:16. Keep pixel_height/frame_height as set by the -ql/-qm/-qh/-qk
            # quality flag and derive the narrower width from it, so the quality
            # flag still controls output resolution.
            config.pixel_width = round(config.pixel_height * 9 / 16)
            config.frame_width = config.frame_height * 9 / 16
        super().__init__(**kwargs)

    def construct(self):
        gui_config = load_gui_config()
        theme = get_theme(gui_config["theme"])

        narration_speed = resolve_narration_speed(gui_config.get("narration_speed", 1.0))
        self.question_voice = EdgeTTSService(voice=gui_config["voice"], global_speed=narration_speed)
        answer_voice_name = gui_config.get("answer_voice") or gui_config["voice"]
        self.answer_voice = (
            self.question_voice
            if answer_voice_name == gui_config["voice"]
            else EdgeTTSService(voice=answer_voice_name, global_speed=narration_speed)
        )
        self.set_speech_service(self.question_voice)

        bg_video_path = gui_config.get("background_video")
        bg_image_path = gui_config.get("background_image")
        if bg_video_path:
            # A background video is composited in afterward (see
            # add_background_video.py) over manim's own transparent output
            # (requires rendering with -t/--transparent) - draw nothing
            # opaque here so there's nothing to composite against but the
            # Q&A content itself.
            pass
        elif bg_image_path and Path(bg_image_path).exists():
            background = ImageMobject(bg_image_path)
            background.stretch_to_fit_width(config.frame_width)
            background.stretch_to_fit_height(config.frame_height)
            background.set_z_index(-10)
            self.add(background)

            overlay = Rectangle(
                width=config.frame_width,
                height=config.frame_height,
                stroke_width=0,
            ).set_fill(color=BLACK, opacity=0.45)
            overlay.set_z_index(-9)
            self.add(overlay)
        else:
            background = Rectangle(
                width=config.frame_width,
                height=config.frame_height,
                stroke_width=0,
            ).set_fill(color=theme["bg_colors"], opacity=1)
            background.set_z_index(-10)
            self.add(background)

        if gui_config["show_intro"]:
            intro = build_intro_card(
                gui_config["channel_name"] or "Interview Practice",
                gui_config["episode_title"] or None,
            )
            self.play(Write(intro))
            self.wait(1.5)
            self.play(FadeOut(intro))

        if gui_config["script_text"]:
            pairs = parse_qa_text(gui_config["script_text"])
        else:
            pairs = parse_qa_file(SCRIPT_FILE)

        if gui_config.get("add_fillers"):
            rate = gui_config.get("filler_rate", 0.15)
            pairs = [(q, add_fillers(a, rate=rate)) for q, a in pairs]

        style_name = gui_config.get("reveal_style", "stacked")
        render_style = STYLE_REGISTRY.get(style_name, style_stacked.render)
        render_style(self, pairs, theme)

        if gui_config["show_outro"]:
            outro = build_outro_card(
                gui_config["outro_message"], gui_config["handle"] or None
            )
            self.play(FadeIn(outro))
            self.wait(1.5)
            self.play(FadeOut(outro))
