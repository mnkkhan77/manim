from manim import *

from reveal_common import (
    DEFAULT_HIGHLIGHT_COLOR,
    THINKING_PAUSE,
    _parse_markdown_words,
    build_styled_paragraph,
    font_size_for,
    speak_and_reveal,
)

# Fixed whiteboard look -- intentionally ignores the passed-in theme colors,
# same pattern as style_terminal.py's fixed terminal look.
BOARD_BG = "#f6f4ee"
TRAY_LINE_COLOR = "#d8d4c8"
MARKER_BLUE = "#2457c5"
MARKER_BLACK = "#1c1c1c"
COUNTER_COLOR = "#b0aca0"

# "Segoe Print" is a genuine handwriting-style font confirmed present via
# manimpango.list_fonts() on this machine (Windows ships it by default).
# It reads as bold, legible marker/print handwriting rather than cursive,
# which suits an "answer written on a whiteboard" look better than a
# cursive script font would.
HAND_FONT = "Segoe Print"

FONT_SIZE_Q = 36
FONT_SIZE_A = 32
MAX_TEXT_WIDTH = 10.5
WORD_BUFF = 0.15
LINE_BUFF = 0.25


def build_hand_paragraph(text, font_size, max_width, color, word_buff=WORD_BUFF, line_buff=LINE_BUFF):
    """Thin wrapper around reveal_common.build_styled_paragraph with the fixed
    handwriting font (build_paragraph itself defaults to no font, so it can't
    produce marker-style glyphs on its own -- same reason style_terminal.py
    has its own thin wrapper for Consolas)."""
    parsed = _parse_markdown_words(text)
    return build_styled_paragraph(
        parsed, font_size, color, DEFAULT_HIGHLIGHT_COLOR, word_buff, line_buff,
        max_width, font=HAND_FONT,
    )


def build_whiteboard_background():
    board = Rectangle(
        width=config.frame_width, height=config.frame_height, stroke_width=0
    ).set_fill(color=BOARD_BG, opacity=1)
    board.set_z_index(-10)

    tray_line = Line(
        start=np.array([-config.frame_width / 2 + 0.6, -3.1, 0]),
        end=np.array([config.frame_width / 2 - 0.6, -3.1, 0]),
        color=TRAY_LINE_COLOR,
        stroke_width=3,
    )
    tray_line.set_z_index(-9)

    return VGroup(board, tray_line)


def render(scene, pairs, theme):
    background = build_whiteboard_background()
    scene.add(background)

    max_text_width = min(MAX_TEXT_WIDTH, 0.85 * config.frame_width)
    font_size_q = font_size_for(FONT_SIZE_Q)
    font_size_a = font_size_for(FONT_SIZE_A)

    for i, (question, answer) in enumerate(pairs, start=1):
        counter = Text(
            f"Question {i} / {len(pairs)}", font_size=22, color=COUNTER_COLOR
        )
        counter.to_corner(UR)
        scene.add(counter)

        q_paragraph, q_words = build_hand_paragraph(
            question, font_size_q, max_text_width, color=MARKER_BLUE
        )
        q_paragraph.move_to(UP * 1.6)

        speak_and_reveal(scene, question, q_words, voice=scene.question_voice)
        scene.wait(THINKING_PAUSE)

        a_paragraph, a_words = build_hand_paragraph(
            answer, font_size_a, max_text_width, color=MARKER_BLACK
        )
        a_paragraph.next_to(q_paragraph, DOWN, buff=0.9)
        if a_paragraph.height > 3.8:
            scale = 3.8 / a_paragraph.height
            a_paragraph.scale(scale)
            a_paragraph.next_to(q_paragraph, DOWN, buff=0.9)

        speak_and_reveal(scene, answer, a_words, voice=scene.answer_voice)
        scene.wait(1.0)

        scene.play(FadeOut(counter), FadeOut(q_paragraph), FadeOut(a_paragraph))
