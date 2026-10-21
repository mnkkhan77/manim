from manim import *

from reveal_common import THINKING_PAUSE, speak_and_reveal

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
    """Same word-wrap shape as reveal_common.build_paragraph, but builds each
    word with the fixed handwriting font (build_paragraph itself has no font
    parameter, so it can't produce marker-style glyphs -- mirrors the same
    local-rebuild approach style_terminal.py uses for its Consolas font)."""
    words = text.split()
    word_mobs = [Text(w, font=HAND_FONT, font_size=font_size, color=color) for w in words]

    lines, current_line, current_width = [], [], 0
    for wm in word_mobs:
        projected = current_width + wm.width + (word_buff if current_line else 0)
        if current_line and projected > max_width:
            lines.append(current_line)
            current_line, current_width = [wm], wm.width
        else:
            current_line.append(wm)
            current_width = projected
    if current_line:
        lines.append(current_line)

    line_groups = [VGroup(*line).arrange(RIGHT, buff=word_buff) for line in lines]
    paragraph = VGroup(*line_groups).arrange(DOWN, aligned_edge=LEFT, buff=line_buff)

    ordered_words = [wm for line in lines for wm in line]
    return paragraph, ordered_words


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

    for i, (question, answer) in enumerate(pairs, start=1):
        counter = Text(
            f"Question {i} / {len(pairs)}", font_size=22, color=COUNTER_COLOR
        )
        counter.to_corner(UR)
        scene.add(counter)

        q_paragraph, q_words = build_hand_paragraph(
            question, FONT_SIZE_Q, MAX_TEXT_WIDTH, color=MARKER_BLUE
        )
        q_paragraph.move_to(UP * 1.6)

        speak_and_reveal(scene, question, q_words)
        scene.wait(THINKING_PAUSE)

        a_paragraph, a_words = build_hand_paragraph(
            answer, FONT_SIZE_A, MAX_TEXT_WIDTH, color=MARKER_BLACK
        )
        a_paragraph.next_to(q_paragraph, DOWN, buff=0.9)
        if a_paragraph.height > 3.8:
            scale = 3.8 / a_paragraph.height
            a_paragraph.scale(scale)
            a_paragraph.next_to(q_paragraph, DOWN, buff=0.9)

        speak_and_reveal(scene, answer, a_words)
        scene.wait(1.0)

        scene.play(FadeOut(counter), FadeOut(q_paragraph), FadeOut(a_paragraph))
