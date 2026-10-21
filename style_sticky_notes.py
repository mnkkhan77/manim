from manim import *

from reveal_common import THINKING_PAUSE, build_paragraph, speak_and_reveal

# Fixed corkboard palette -- intentionally ignores the passed-in theme colors,
# same pattern as style_terminal.py's fixed green-on-black look.
BOARD_BG = "#4a3324"
BOARD_DOT_COLOR = "#3a2819"

Q_NOTE_COLOR = "#f2c14e"
Q_TEXT_COLOR = "#2a2410"
A_NOTE_COLOR = "#8fd3c7"
A_TEXT_COLOR = "#133029"
PIN_COLOR = "#b33a3a"
COUNTER_COLOR = "#f5f0e6"

FONT_SIZE_Q = 30
FONT_SIZE_A = 28
NOTE_MAX_WIDTH = 6.2
NOTE_PAD_X = 0.7
NOTE_PAD_Y = 0.55
NOTE_MAX_HEIGHT = 3.0

Q_ROTATION = -4 * DEGREES
A_ROTATION = 3 * DEGREES

Q_POSITION = UP * 1.9
A_POSITION = DOWN * 1.6


def build_corkboard_background():
    base = Rectangle(
        width=config.frame_width, height=config.frame_height, stroke_width=0
    ).set_fill(color=BOARD_BG, opacity=1)
    base.set_z_index(-10)

    dots = VGroup()
    x = -config.frame_width / 2 + 0.5
    while x < config.frame_width / 2:
        y = -config.frame_height / 2 + 0.5
        while y < config.frame_height / 2:
            dots.add(
                Dot(
                    point=np.array([x, y, 0]),
                    radius=0.035,
                    color=BOARD_DOT_COLOR,
                    fill_opacity=0.35,
                    stroke_width=0,
                )
            )
            y += 1.0
        x += 1.0
    dots.set_z_index(-9)

    return VGroup(base, dots)


def build_note(text, font_size, note_color, text_color, position, rotation):
    """Build word mobjects first, size a card to fit them, then group+rotate as one unit."""
    paragraph, words = build_paragraph(
        text, font_size, NOTE_MAX_WIDTH, color=text_color
    )

    if paragraph.height > NOTE_MAX_HEIGHT:
        scale = NOTE_MAX_HEIGHT / paragraph.height
        paragraph.scale(scale)

    card_width = paragraph.width + NOTE_PAD_X
    card_height = paragraph.height + NOTE_PAD_Y

    card = RoundedRectangle(
        width=card_width,
        height=card_height,
        corner_radius=0.15,
        fill_color=note_color,
        fill_opacity=1,
        stroke_color=note_color,
        stroke_width=2,
    )
    paragraph.move_to(card.get_center())

    pin = Dot(radius=0.09, color=PIN_COLOR, fill_opacity=1, stroke_width=0)
    pin.move_to(card.get_top())

    note = VGroup(card, paragraph, pin)
    note.move_to(position)
    note.rotate(rotation)

    return note, card, pin, paragraph, words


def render(scene, pairs, theme):
    board = build_corkboard_background()
    scene.add(board)

    for i, (question, answer) in enumerate(pairs, start=1):
        counter = Text(
            f"Question {i} / {len(pairs)}", font_size=24, color=COUNTER_COLOR
        )
        counter.to_corner(UR)
        scene.add(counter)

        q_note, q_card, q_pin, q_paragraph, q_words = build_note(
            question, FONT_SIZE_Q, Q_NOTE_COLOR, Q_TEXT_COLOR, Q_POSITION, Q_ROTATION
        )

        scene.play(FadeIn(VGroup(q_card, q_pin), scale=0.85), run_time=0.4)
        speak_and_reveal(scene, question, q_words)
        scene.wait(THINKING_PAUSE)

        a_note, a_card, a_pin, a_paragraph, a_words = build_note(
            answer, FONT_SIZE_A, A_NOTE_COLOR, A_TEXT_COLOR, A_POSITION, A_ROTATION
        )

        scene.play(FadeIn(VGroup(a_card, a_pin), scale=0.85), run_time=0.4)
        speak_and_reveal(scene, answer, a_words)
        scene.wait(1.0)

        scene.play(
            FadeOut(counter),
            FadeOut(q_note, shift=UP * 0.4),
            FadeOut(a_note, shift=UP * 0.4),
        )
