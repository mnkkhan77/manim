import math
import random

from manim import *

from reveal_common import (
    FONT_SIZE_A,
    FONT_SIZE_Q,
    MAX_TEXT_WIDTH,
    THINKING_PAUSE,
    build_paragraph,
    speak_and_reveal,
)

AVATAR_RADIUS = 0.55
AVATAR_Y = 2.2
AVATAR_X = 3.3
WAVEFORM_GAP = 1.15
N_BARS = 7
BAR_SPACING = 0.17
BAR_MIN_HEIGHT = 0.08
BAR_MAX_HEIGHT = 0.9
DIM_OPACITY = 0.15
BRIGHT_OPACITY = 0.45
CAPTION_CENTER = DOWN * 1.3
CAPTION_MAX_HEIGHT = 3.0


def build_avatar(center, color, label):
    circle = Circle(
        radius=AVATAR_RADIUS,
        stroke_color=color,
        stroke_width=3,
        fill_color=color,
        fill_opacity=DIM_OPACITY,
    )
    circle.move_to(center)
    glyph = Text(label, font_size=28, color=color)
    glyph.move_to(center)
    ring = Circle(
        radius=AVATAR_RADIUS + 0.18,
        stroke_color=color,
        stroke_width=6,
        stroke_opacity=0,
    )
    ring.move_to(center)
    return circle, glyph, ring


def build_waveform(center, color):
    bars = VGroup()
    bottoms = []
    for i in range(N_BARS):
        x = (i - (N_BARS - 1) / 2) * BAR_SPACING
        bottom = center + RIGHT * x
        bar = Line(bottom, bottom + UP * BAR_MIN_HEIGHT, stroke_color=color, stroke_width=5)
        bars.add(bar)
        bottoms.append(bottom)
    return bars, bottoms


def make_bar_updater(bottom, flag):
    def updater(mob, dt):
        if flag["on"]:
            height = random.uniform(BAR_MIN_HEIGHT, BAR_MAX_HEIGHT)
        else:
            height = BAR_MIN_HEIGHT
        mob.put_start_and_end_on(bottom, bottom + UP * height)

    return updater


def make_ring_updater(scene, flag):
    def updater(mob, dt):
        if flag["on"]:
            t = scene.renderer.time
            pulse = 0.5 + 0.5 * math.sin(t * 6)
            mob.set_stroke(opacity=0.4 + 0.5 * pulse, width=5 + 3 * pulse)
        else:
            mob.set_stroke(opacity=0)

    return updater


def set_active(circle, flag, active):
    flag["on"] = active
    circle.set_fill(opacity=BRIGHT_OPACITY if active else DIM_OPACITY)


def fit_caption(paragraph):
    if paragraph.height > CAPTION_MAX_HEIGHT:
        paragraph.scale(CAPTION_MAX_HEIGHT / paragraph.height)
    paragraph.move_to(CAPTION_CENTER)


def render(scene, pairs, theme):
    q_center = LEFT * AVATAR_X + UP * AVATAR_Y
    a_center = RIGHT * AVATAR_X + UP * AVATAR_Y

    q_circle, q_glyph, q_ring = build_avatar(q_center, theme["question_color"], "Q")
    a_circle, a_glyph, a_ring = build_avatar(a_center, theme["answer_color"], "A")

    q_bars, q_bottoms = build_waveform(q_center + DOWN * WAVEFORM_GAP, theme["question_color"])
    a_bars, a_bottoms = build_waveform(a_center + DOWN * WAVEFORM_GAP, theme["answer_color"])

    scene.add(q_ring, a_ring, q_circle, a_circle, q_glyph, a_glyph, q_bars, a_bars)

    q_flag = {"on": False}
    a_flag = {"on": False}

    updated_mobjects = [q_ring, a_ring, *q_bars, *a_bars]

    q_ring.add_updater(make_ring_updater(scene, q_flag))
    a_ring.add_updater(make_ring_updater(scene, a_flag))
    for bar, bottom in zip(q_bars, q_bottoms):
        bar.add_updater(make_bar_updater(bottom, q_flag))
    for bar, bottom in zip(a_bars, a_bottoms):
        bar.add_updater(make_bar_updater(bottom, a_flag))

    counter = None

    try:
        for i, (question, answer) in enumerate(pairs, start=1):
            if counter is not None:
                scene.remove(counter)
            counter = Text(
                f"Question {i} / {len(pairs)}", font_size=24, color=theme["accent_color"]
            )
            counter.to_corner(UR)
            scene.add(counter)

            set_active(q_circle, q_flag, True)
            set_active(a_circle, a_flag, False)

            q_paragraph, q_words = build_paragraph(
                question, FONT_SIZE_Q, MAX_TEXT_WIDTH, color=theme["question_color"]
            )
            fit_caption(q_paragraph)

            speak_and_reveal(scene, question, q_words)
            set_active(q_circle, q_flag, False)
            scene.wait(THINKING_PAUSE)
            scene.play(FadeOut(q_paragraph))

            set_active(a_circle, a_flag, True)

            a_paragraph, a_words = build_paragraph(
                answer, FONT_SIZE_A, MAX_TEXT_WIDTH, color=theme["answer_color"]
            )
            fit_caption(a_paragraph)

            speak_and_reveal(scene, answer, a_words)
            set_active(a_circle, a_flag, False)
            scene.wait(1.0)

            scene.play(FadeOut(a_paragraph), FadeOut(counter))
            counter = None
    finally:
        for mob in updated_mobjects:
            mob.clear_updaters()
