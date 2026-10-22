from manim import *

from reveal_common import (
    FONT_SIZE_A,
    FONT_SIZE_Q,
    THINKING_PAUSE,
    build_paragraph,
    font_size_for,
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
    accent = theme.get("accent_color", WHITE)
    portrait = frame_w < frame_h
    font_size_q = font_size_for(FONT_SIZE_Q)
    font_size_a = font_size_for(FONT_SIZE_A)

    if portrait:
        # Two side-by-side panels would be too thin in a narrow 9:16 frame,
        # so stack them top (interviewer) / bottom (you) instead, split by a
        # horizontal divider through the middle.
        side_margin = 0.35
        panel_max_width = frame_w - 2 * side_margin
        q_x = a_x = 0.0

        divider = Line(
            LEFT * (frame_w / 2), RIGHT * (frame_w / 2), color=accent, stroke_width=2
        )
        divider.set_stroke(opacity=0.35)
        scene.add(divider)

        top_panel_top = frame_h / 2 - 0.9
        top_panel_bottom = 0.3
        bottom_panel_top = -0.3
        bottom_panel_bottom = -frame_h / 2 + BOTTOM_MARGIN

        q_text_area_height = top_panel_top - top_panel_bottom - 0.5
        q_text_center_y = (top_panel_top - 0.5 + top_panel_bottom) / 2
        a_text_area_height = bottom_panel_top - bottom_panel_bottom - 0.5
        a_text_center_y = (bottom_panel_top - 0.5 + bottom_panel_bottom) / 2

        label_left = Text("INTERVIEWER", font_size=LABEL_FONT_SIZE, color=accent)
        label_left.move_to(np.array([0, top_panel_top, 0]))
        label_right = Text("YOU", font_size=LABEL_FONT_SIZE, color=accent)
        label_right.move_to(np.array([0, bottom_panel_top, 0]))
        scene.add(label_left, label_right)

        counter_y = frame_h / 2 - 0.3
    else:
        left_x = -frame_w / 4
        right_x = frame_w / 4
        q_x, a_x = left_x, right_x
        panel_max_width = frame_w / 2 - PANEL_SIDE_MARGIN

        text_top_y = frame_h / 2 - TOP_MARGIN
        text_bottom_y = -frame_h / 2 + BOTTOM_MARGIN
        q_text_area_height = a_text_area_height = text_top_y - text_bottom_y
        q_text_center_y = a_text_center_y = (text_top_y + text_bottom_y) / 2

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

        counter_y = frame_h / 2 - 0.3

    for i, (question, answer) in enumerate(pairs, start=1):
        counter = Text(
            f"Question {i} / {len(pairs)}", font_size=COUNTER_FONT_SIZE, color=accent
        )
        counter.move_to(np.array([0, counter_y, 0]))
        scene.add(counter)

        q_paragraph, q_words = build_paragraph(
            question, font_size_q, panel_max_width, color=theme["question_color"]
        )
        q_paragraph.move_to(np.array([q_x, q_text_center_y, 0]))
        if q_paragraph.height > q_text_area_height:
            scale = q_text_area_height / q_paragraph.height
            q_paragraph.scale(scale)
            q_paragraph.move_to(np.array([q_x, q_text_center_y, 0]))

        speak_and_reveal(scene, question, q_words, voice=scene.question_voice)
        scene.wait(THINKING_PAUSE)

        a_paragraph, a_words = build_paragraph(
            answer, font_size_a, panel_max_width, color=theme["answer_color"]
        )
        a_paragraph.move_to(np.array([a_x, a_text_center_y, 0]))
        if a_paragraph.height > a_text_area_height:
            scale = a_text_area_height / a_paragraph.height
            a_paragraph.scale(scale)
            a_paragraph.move_to(np.array([a_x, a_text_center_y, 0]))

        speak_and_reveal(scene, answer, a_words, voice=scene.answer_voice)
        scene.wait(1.0)

        scene.play(FadeOut(counter), FadeOut(q_paragraph), FadeOut(a_paragraph))
