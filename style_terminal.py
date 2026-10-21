from manim import *

from reveal_common import THINKING_PAUSE, speak_and_reveal

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


def build_terminal_chrome():
    bar = Rectangle(width=12, height=0.45, color=BAR_BG, fill_opacity=1, stroke_width=0)
    bar.to_edge(UP, buff=0)
    dots = VGroup(*[
        Dot(radius=0.07, color=c) for c in DOT_COLORS
    ]).arrange(RIGHT, buff=0.12)
    dots.move_to(bar.get_left() + RIGHT * 0.35)
    return VGroup(bar, dots)


def make_line_words(text, color, font_size=FONT_SIZE, max_width=MAX_WIDTH):
    words = text.split()
    mobs = [Text(w, font_size=font_size, color=color, font="Consolas") for w in words]
    lines, current, width = [], [], 0
    buff = 0.12
    for m in mobs:
        projected = width + m.width + (buff if current else 0)
        if current and projected > max_width:
            lines.append(current)
            current, width = [m], m.width
        else:
            current.append(m)
            width = projected
    if current:
        lines.append(current)
    line_groups = [VGroup(*ln).arrange(RIGHT, buff=buff) for ln in lines]
    block = VGroup(*line_groups).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
    ordered = [m for ln in lines for m in ln]
    return block, ordered


def render(scene, pairs, theme):
    background = Rectangle(
        width=config.frame_width, height=config.frame_height, stroke_width=0
    ).set_fill(color=TERM_BG, opacity=1)
    background.set_z_index(-10)
    scene.add(background)

    chrome = build_terminal_chrome()
    scene.add(chrome)

    cursor_template = Rectangle(width=0.14, height=FONT_SIZE / 420, fill_opacity=1, stroke_width=0, color=Q_COLOR)

    log = VGroup()

    for i, (question, answer) in enumerate(pairs, start=1):
        prompt = Text(f"Q{i}>", font_size=FONT_SIZE, color=PROMPT_COLOR, font="Consolas")
        q_block, q_words = make_line_words(question, Q_COLOR)
        q_line = VGroup(prompt, q_block).arrange(RIGHT, buff=0.18, aligned_edge=UP)

        a_block, a_words = make_line_words(answer, A_COLOR)

        entry = VGroup(q_line, a_block).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        log.add(entry)
        log.arrange(DOWN, aligned_edge=LEFT, buff=0.45)
        log.move_to(np.array([LOG_LEFT, LOG_TOP, 0]), aligned_edge=UL)

        if log.height > 6.3:
            shift_up = log.height - 6.3
            scene.play(log.animate.shift(UP * shift_up), run_time=0.4)

        scene.play(FadeIn(prompt), run_time=0.3)
        cursor = cursor_template.copy().next_to(prompt, RIGHT, buff=0.15)
        cursor.add_updater(lambda m, dt: m.set_opacity(1 if (scene.renderer.time % 1.0) < 0.5 else 0))
        scene.add(cursor)

        speak_and_reveal(scene, question, q_words)
        cursor.clear_updaters()
        scene.remove(cursor)
        scene.wait(THINKING_PAUSE)

        speak_and_reveal(scene, answer, a_words)
        scene.wait(1.0)
