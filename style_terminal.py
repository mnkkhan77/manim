from manim import *

from reveal_common import (
    DEFAULT_HIGHLIGHT_COLOR,
    THINKING_PAUSE,
    _parse_markdown_words,
    build_styled_paragraph,
    font_size_for,
    speak_and_reveal,
)

TERM_BG = "#0c0f0a"
BAR_BG = "#1a1f16"
PROMPT_COLOR = "#3f8f52"
Q_COLOR = "#58c46b"
A_COLOR = "#9fd4e8"
DOT_COLORS = ["#e2574c", "#e0b341", "#4cae4c"]

FONT_SIZE = 26
MAX_WIDTH = 10.5
LOG_TOP = 2.6
LOG_LEFT = -5.6


def build_terminal_chrome(bar_width=12):
    bar = Rectangle(width=bar_width, height=0.45, color=BAR_BG, fill_opacity=1, stroke_width=0)
    bar.to_edge(UP, buff=0)
    dots = VGroup(*[
        Dot(radius=0.07, color=c) for c in DOT_COLORS
    ]).arrange(RIGHT, buff=0.12)
    dots.move_to(bar.get_left() + RIGHT * 0.35)
    return VGroup(bar, dots)


def make_line_words(text, color, font_size=FONT_SIZE, max_width=MAX_WIDTH):
    parsed = _parse_markdown_words(text)
    return build_styled_paragraph(
        parsed, font_size, color, DEFAULT_HIGHLIGHT_COLOR, word_buff=0.12, line_buff=0.18,
        max_width=max_width, font="Consolas",
    )


def render(scene, pairs, theme):
    frame_w = config.frame_width
    portrait = frame_w < config.frame_height
    font_size = font_size_for(FONT_SIZE)
    if portrait:
        log_left = -frame_w / 2 + 0.3
        max_width = frame_w - 0.9
        bar_width = frame_w
    else:
        log_left = LOG_LEFT
        max_width = MAX_WIDTH
        bar_width = 12

    background = Rectangle(
        width=config.frame_width, height=config.frame_height, stroke_width=0
    ).set_fill(color=TERM_BG, opacity=1)
    background.set_z_index(-10)
    scene.add(background)

    chrome = build_terminal_chrome(bar_width=bar_width)
    scene.add(chrome)

    cursor_template = Rectangle(width=0.14, height=font_size / 420, fill_opacity=1, stroke_width=0, color=Q_COLOR)

    log = VGroup()

    for i, (question, answer) in enumerate(pairs, start=1):
        prompt = Text(f"Q{i}>", font_size=font_size, color=PROMPT_COLOR, font="Consolas")
        q_block, q_words = make_line_words(question, Q_COLOR, font_size=font_size, max_width=max_width)
        q_line = VGroup(prompt, q_block).arrange(RIGHT, buff=0.18, aligned_edge=UP)

        a_block, a_words = make_line_words(answer, A_COLOR, font_size=font_size, max_width=max_width)

        entry = VGroup(q_line, a_block).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        log.add(entry)
        log.arrange(DOWN, aligned_edge=LEFT, buff=0.45)
        log.move_to(np.array([log_left, LOG_TOP, 0]), aligned_edge=UL)

        if log.height > 6.3:
            shift_up = log.height - 6.3
            scene.play(log.animate.shift(UP * shift_up), run_time=0.4)

        scene.play(FadeIn(prompt), run_time=0.3)
        cursor = cursor_template.copy().next_to(prompt, RIGHT, buff=0.15)
        cursor.add_updater(lambda m, dt: m.set_opacity(1 if (scene.renderer.time % 1.0) < 0.5 else 0))
        scene.add(cursor)

        speak_and_reveal(scene, question, q_words, voice=scene.question_voice)
        cursor.clear_updaters()
        scene.remove(cursor)
        scene.wait(THINKING_PAUSE)

        speak_and_reveal(scene, answer, a_words, voice=scene.answer_voice)
        scene.wait(1.0)
