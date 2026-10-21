from manim import *

from reveal_common import (
    FONT_SIZE_A,
    FONT_SIZE_Q,
    MAX_TEXT_WIDTH,
    THINKING_PAUSE,
    build_paragraph,
    speak_and_reveal,
)


def render(scene, pairs, theme):
    for i, (question, answer) in enumerate(pairs, start=1):
        counter = Text(
            f"Question {i} / {len(pairs)}", font_size=24, color=theme["accent_color"]
        )
        counter.to_corner(UR)
        scene.add(counter)

        q_paragraph, q_words = build_paragraph(
            question, FONT_SIZE_Q, MAX_TEXT_WIDTH, color=theme["question_color"]
        )
        q_paragraph.move_to(UP * 1.5)

        speak_and_reveal(scene, question, q_words)
        scene.wait(THINKING_PAUSE)

        scene.play(q_paragraph.animate.to_edge(UP).scale(0.7))

        a_paragraph, a_words = build_paragraph(
            answer, FONT_SIZE_A, MAX_TEXT_WIDTH, color=theme["answer_color"]
        )
        a_paragraph.next_to(q_paragraph, DOWN, buff=0.8)
        if a_paragraph.height > 4.5:
            scale = 4.5 / a_paragraph.height
            a_paragraph.scale(scale)
            a_paragraph.next_to(q_paragraph, DOWN, buff=0.8)

        speak_and_reveal(scene, answer, a_words)
        scene.wait(1.0)

        scene.play(FadeOut(counter), FadeOut(q_paragraph), FadeOut(a_paragraph))
