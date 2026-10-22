# Run with (from the project root):
#   venv/Scripts/python.exe -m manim -ql timeline_video/timeline_simulation.py TimelineVideo --disable_caching
# Swap -ql for -qm/-qh/-qk for higher quality. Reads timeline_config.json if
# present (see DEFAULT_CONFIG below), otherwise falls back to timeline_script.txt.
import json
import os
import sys
from pathlib import Path

# timeline_video/ is its own folder, but still reuses the shared reveal/theme/
# branding/TTS modules that live at the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from manim import *
from manim_voiceover import VoiceoverScene

from branding import build_intro_card, build_outro_card
from edge_tts_service import EdgeTTSService, resolve_narration_speed
from reveal_common import build_paragraph, font_size_for, is_portrait, speak_and_reveal
from stock_fetch import fetch_stock_image
from themes import get_theme
from timeline_format import parse_timeline_file, parse_timeline_text

HERE = Path(__file__).resolve().parent
SCRIPT_FILE = HERE / "timeline_script.txt"
CONFIG_FILE = HERE / "timeline_config.json"

DEFAULT_CONFIG = {
    "script_text": None,
    "voice": "en-US-AndrewNeural",
    "narration_speed": 1.0,
    "theme": "midnight",
    "orientation": "landscape",
    "show_intro": False,
    "channel_name": "",
    "episode_title": "",
    "show_outro": False,
    "outro_message": "Thanks for watching! Like and subscribe.",
    "handle": "",
    "pexels_api_key": None,
    "pixabay_api_key": None,
}

CAPTION_FONT_SIZE = 30
LABEL_FONT_SIZE = 36
CAPTION_SIDE_MARGIN = 0.8
CAPTION_SIDE_MARGIN_PORTRAIT = 0.3
CAPTION_PAD = 0.35
CAPTION_PAD_PORTRAIT = 0.25
CAPTION_MAX_HEIGHT = 2.4  # vertical budget for the caption block (Y-axis constant, same in both orientations)
CAPTION_BOTTOM_GAP = 0.5  # gap between caption box bottom and frame edge
BAR_SIDE_MARGIN = 0.8
BAR_SIDE_MARGIN_PORTRAIT = 0.3
BAR_TOP_MARGIN = 0.35
IMAGE_OVERSCAN = 1.15  # headroom around the frame so Ken Burns zoom/pan never shows an edge
ZOOM_RATE = 0.015      # fractional scale growth per second
PAN_RATE = 0.08        # units per second of horizontal drift


def load_timeline_config():
    config_dict = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config_dict.update(json.load(f))
    return config_dict


def make_ken_burns_updater(direction):
    def updater(mob, dt):
        mob.scale(1 + ZOOM_RATE * dt)
        mob.shift(direction * PAN_RATE * dt)

    return updater


def build_scene_background(image_path, theme):
    frame_w, frame_h = config.frame_width, config.frame_height

    if image_path:
        full_path = Path(image_path)
        if not full_path.is_absolute():
            full_path = HERE / full_path
        if full_path.exists():
            img = ImageMobject(str(full_path))
            img_aspect = img.pixel_width / img.pixel_height
            frame_aspect = frame_w / frame_h
            if img_aspect > frame_aspect:
                img.set(height=frame_h)
            else:
                img.set(width=frame_w)
            img.scale(IMAGE_OVERSCAN)
            img.move_to(ORIGIN)
            img.set_z_index(-10)
            return img

    bg = Rectangle(width=frame_w, height=frame_h, stroke_width=0)
    bg.set_fill(color=theme["bg_colors"], opacity=1)
    bg.set_z_index(-10)
    return bg


def render_timeline(scene, scenes, theme):
    frame_w, frame_h = config.frame_width, config.frame_height
    accent = theme["accent_color"]
    portrait = is_portrait()
    font_size_caption = font_size_for(CAPTION_FONT_SIZE)
    font_size_label = font_size_for(LABEL_FONT_SIZE)
    caption_side_margin = CAPTION_SIDE_MARGIN_PORTRAIT if portrait else CAPTION_SIDE_MARGIN
    caption_pad = CAPTION_PAD_PORTRAIT if portrait else CAPTION_PAD
    bar_side_margin = BAR_SIDE_MARGIN_PORTRAIT if portrait else BAR_SIDE_MARGIN
    caption_max_width = frame_w - 2 * caption_side_margin - 2 * caption_pad

    bar_y = frame_h / 2 - BAR_TOP_MARGIN
    bar = Line(
        np.array([-frame_w / 2 + bar_side_margin, bar_y, 0]),
        np.array([frame_w / 2 - bar_side_margin, bar_y, 0]),
        color=accent, stroke_width=3,
    )
    bar.set_stroke(opacity=0.35)
    marker = Dot(radius=0.09, color=accent)
    marker.move_to(bar.get_left())
    scene.add(bar, marker)

    n = len(scenes)
    current_bg = None

    for i, sc in enumerate(scenes):
        progress = 0 if n == 1 else i / (n - 1)
        target = interpolate(bar.get_left(), bar.get_right(), progress)
        scene.play(marker.animate.move_to(target), run_time=0.5)

        bg = build_scene_background(sc["image"], theme)
        if current_bg is not None:
            scene.play(FadeOut(current_bg), FadeIn(bg))
        else:
            scene.play(FadeIn(bg))
        current_bg = bg

        is_image = isinstance(bg, ImageMobject)
        if is_image:
            bg.add_updater(make_ken_burns_updater(LEFT if i % 2 else RIGHT))

        fade_group = []

        label_group = None
        if sc["label"]:
            label_text = Text(sc["label"], font_size=font_size_label, color=WHITE, weight=BOLD)
            label_bg = RoundedRectangle(
                width=label_text.width + 2 * 0.3, height=label_text.height + 2 * 0.2,
                corner_radius=0.1, fill_color=BLACK, fill_opacity=0.55, stroke_width=0,
            )
            label_bg.move_to(label_text)
            label_group = Group(label_bg, label_text)
            label_group.to_corner(UL, buff=0.5)
            scene.play(FadeIn(label_group), run_time=0.4)
            fade_group.append(label_group)

        caption, words = build_paragraph(
            sc["text"], font_size_caption, caption_max_width, color=WHITE
        )
        if caption.height + 2 * caption_pad > CAPTION_MAX_HEIGHT:
            caption.scale((CAPTION_MAX_HEIGHT - 2 * caption_pad) / caption.height)

        caption_bg = RoundedRectangle(
            width=caption.width + 2 * caption_pad, height=caption.height + 2 * caption_pad,
            corner_radius=0.15, fill_color=BLACK, fill_opacity=0.55, stroke_width=0,
        )
        caption_bg.to_edge(DOWN, buff=CAPTION_BOTTOM_GAP)
        caption.move_to(caption_bg)
        scene.play(FadeIn(caption_bg), run_time=0.3)
        fade_group.append(caption_bg)
        fade_group.append(caption)

        speak_and_reveal(scene, sc["text"], words)
        scene.wait(0.5)

        if is_image:
            bg.clear_updaters()
        scene.play(*[FadeOut(m) for m in fade_group])

    if current_bg is not None:
        scene.play(FadeOut(current_bg))
    scene.play(FadeOut(bar), FadeOut(marker))


class TimelineVideo(VoiceoverScene):
    def __init__(self, **kwargs):
        # Scene.__init__ builds the camera (and its pixel buffer) from
        # config.pixel_width/height — by the time construct() runs, that's
        # already fixed. So the portrait resolution switch has to happen
        # here, before super().__init__(), not in construct().
        gui_config = load_timeline_config()
        if gui_config.get("orientation", "landscape") == "portrait":
            config.pixel_width = round(config.pixel_height * 9 / 16)
            config.frame_width = config.frame_height * 9 / 16
        super().__init__(**kwargs)

    def construct(self):
        gui_config = load_timeline_config()
        theme = get_theme(gui_config["theme"])
        narration_speed = resolve_narration_speed(gui_config.get("narration_speed", 1.0))
        self.set_speech_service(EdgeTTSService(voice=gui_config["voice"], global_speed=narration_speed))

        if gui_config["show_intro"]:
            intro = build_intro_card(
                gui_config["channel_name"] or "History Timeline",
                gui_config["episode_title"] or None,
            )
            self.play(Write(intro))
            self.wait(1.5)
            self.play(FadeOut(intro))

        if gui_config["script_text"]:
            scenes = parse_timeline_text(gui_config["script_text"])
        else:
            scenes = parse_timeline_file(SCRIPT_FILE)

        pexels_key = gui_config["pexels_api_key"] or os.environ.get("PEXELS_API_KEY")
        pixabay_key = gui_config["pixabay_api_key"] or os.environ.get("PIXABAY_API_KEY")
        for sc in scenes:
            if not sc["image"] and sc["search"]:
                sc["image"] = fetch_stock_image(
                    sc["search"],
                    orientation=gui_config["orientation"],
                    pexels_api_key=pexels_key,
                    pixabay_api_key=pixabay_key,
                )

        render_timeline(self, scenes, theme)

        if gui_config["show_outro"]:
            outro = build_outro_card(
                gui_config["outro_message"], gui_config["handle"] or None
            )
            self.play(FadeIn(outro))
            self.wait(1.5)
            self.play(FadeOut(outro))
