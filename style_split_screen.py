from manim import *

from reveal_common import (
    FONT_SIZE_A,
    FONT_SIZE_Q,
    THINKING_PAUSE,
    build_paragraph,
    speak_and_reveal,
)

LABEL_FONT_SIZE = 20
COUNTER_FONT_SIZE = 22
TOP_MARGIN = 1.3
BOTTOM_MARGIN = 0.6
PANEL_SIDE_MARGIN = 1.3


def render(scene, pairs, theme):
    frame_w = config.frame_width
    frame_h = config.frame_height

    left_x = -frame_w / 4
    right_x = frame_w / 4
    panel_max_width = frame_w / 2 - PANEL_SIDE_MARGIN

    text_top_y = frame_h / 2 - TOP_MARGIN
    text_bottom_y = -frame_h / 2 + BOTTOM_MARGIN
    text_area_height = text_top_y - text_bottom_y
    text_center_y = (text_top_y + text_bottom_y) / 2

    accent = theme.get("accent_color", WHITE)

    # Persistent structural elements: divider, panel labels. These stay on
    # screen for the whole video and are never faded out between pairs.
    divider = Line(
        UP * (frame_h / 2), DOWN * (frame_h / 2), color=accent, stroke_width=2
    )
    divider.set_stroke(opacity=0.35)
    scene.add(divider)

    label_left = Text("INTERVIEWER", font_size=LABEL_FONT_SIZE, color=accent)
    label_left.move_to(np.array([left_x, frame_h / 2 - 0.55, 0]))
    label_right = Text("YOU", font_size=LABEL_FONT_SIZE, color=accent)
    label_right.move_to(np.array([right_x, frame_h / 2 - 0.55, 0]))
    scene.add(label_left, label_right)

    for i, (question, answer) in enumerate(pairs, start=1):
        counter = Text(
            f"Question {i} / {len(pairs)}", font_size=COUNTER_FONT_SIZE, color=accent
        )
        counter.move_to(np.array([0, frame_h / 2 - 0.3, 0]))
        scene.add(counter)

        q_paragraph, q_words = build_paragraph(
            question, FONT_SIZE_Q, panel_max_width, color=theme["question_color"]
        )
        q_paragraph.move_to(np.array([left_x, text_center_y, 0]))
        if q_paragraph.height > text_area_height:
            scale = text_area_height / q_paragraph.height
            q_paragraph.scale(scale)
            q_paragraph.move_to(np.array([left_x, text_center_y, 0]))

        speak_and_reveal(scene, question, q_words)
        scene.wait(THINKING_PAUSE)

        a_paragraph, a_words = build_paragraph(
            answer, FONT_SIZE_A, panel_max_width, color=theme["answer_color"]
        )
        a_paragraph.move_to(np.array([right_x, text_center_y, 0]))
        if a_paragraph.height > text_area_height:
            scale = text_area_height / a_paragraph.height
            a_paragraph.scale(scale)
            a_paragraph.move_to(np.array([right_x, text_center_y, 0]))

        speak_and_reveal(scene, answer, a_words)
        scene.wait(1.0)

        scene.play(FadeOut(counter), FadeOut(q_paragraph), FadeOut(a_paragraph))
