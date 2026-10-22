from manim import *

from reveal_common import THINKING_PAUSE, build_paragraph, font_size_for, speak_and_reveal

FONT_SIZE_Q = 28
FONT_SIZE_A = 28
BUBBLE_MAX_WIDTH = 5.5
PAD_X = 0.5
PAD_Y = 0.4
CORNER_RADIUS = 0.18

LEFT_BUFF = 0.6
RIGHT_BUFF = 0.6
GAP = 0.35

TOP_Y = 2.6
SAFE_BOTTOM = -3.3

BUBBLE_BLEND_ALPHA = 0.55
BUBBLE_FILL_OPACITY = 0.85


def render(scene, pairs, theme):
    frame_w = config.frame_width
    portrait = frame_w < config.frame_height
    if portrait:
        left_buff = 0.08 * frame_w
        right_buff = 0.08 * frame_w
        available_bubble_width = frame_w - left_buff - right_buff
        bubble_max_width = available_bubble_width - 2 * PAD_X
    else:
        bubble_max_width = BUBBLE_MAX_WIDTH
        left_buff = LEFT_BUFF
        right_buff = RIGHT_BUFF
    font_size_q = font_size_for(FONT_SIZE_Q)
    font_size_a = font_size_for(FONT_SIZE_A)

    bg_color = ManimColor(theme["bg_colors"][0])
    question_bubble_color = interpolate_color(
        bg_color, ManimColor(theme["question_color"]), BUBBLE_BLEND_ALPHA
    )
    answer_bubble_color = interpolate_color(
        bg_color, ManimColor(theme["accent_color"]), BUBBLE_BLEND_ALPHA
    )

    # `thread` only ever holds mobjects that are already genuinely visible in
    # the scene (popped-in bubble backgrounds, and paragraphs *after* their
    # words have been revealed). This matters: animating `.animate` on a
    # VGroup implicitly adds that whole mobject family to the scene, so if a
    # not-yet-revealed paragraph were a member, scrolling the thread would
    # prematurely surface its (still fully-opaque) word mobjects before their
    # word-by-word voiceover-synced reveal ever ran.
    thread = VGroup()
    counter = None

    def add_message(text, font_size, text_color, bubble_color, align_right):
        paragraph, words = build_paragraph(
            text, font_size, bubble_max_width, color=text_color
        )

        bubble_bg = RoundedRectangle(
            width=paragraph.width + 2 * PAD_X,
            height=paragraph.height + 2 * PAD_Y,
            corner_radius=CORNER_RADIUS,
            stroke_color=bubble_color,
            stroke_width=1.5,
            stroke_opacity=0.9,
        )
        bubble_bg.set_fill(color=bubble_color, opacity=0)
        paragraph.move_to(bubble_bg.get_center())

        if align_right:
            bubble_bg.to_edge(RIGHT, buff=right_buff)
        else:
            bubble_bg.to_edge(LEFT, buff=left_buff)
        paragraph.move_to(bubble_bg.get_center())

        if len(thread) == 0:
            target_top = TOP_Y
        else:
            target_top = thread.get_bottom()[1] - GAP
        shift_y = target_top - bubble_bg.get_top()[1]
        bubble_bg.shift(UP * shift_y)
        paragraph.shift(UP * shift_y)

        scene.add(bubble_bg)
        thread.add(bubble_bg)

        bottom_y = bubble_bg.get_bottom()[1]
        shift_amt = max(0.0, SAFE_BOTTOM - bottom_y)
        if shift_amt > 0:
            # Run the scroll-up and the bubble's fade-in as two SEPARATE
            # animations rather than simultaneous ones. `bubble_bg` is a
            # member of `thread`, so animating `thread` and `bubble_bg`
            # directly at the same time would create two independent
            # Transform snapshots of the same mobject -- the direct one's
            # captured (pre-shift) target silently cancels the group one's
            # position change for that mobject, desyncing the bubble
            # background from its text.
            scene.play(thread.animate.shift(UP * shift_amt), run_time=0.4)
            paragraph.shift(UP * shift_amt)
        scene.play(
            bubble_bg.animate.set_fill(opacity=BUBBLE_FILL_OPACITY),
            run_time=0.4,
        )

        voice = scene.answer_voice if align_right else scene.question_voice
        speak_and_reveal(scene, text, words, voice=voice)
        # Now that every word is genuinely visible, it's safe to fold the
        # paragraph into `thread` so later scrolls carry it along too.
        thread.add(paragraph)

    for i, (question, answer) in enumerate(pairs, start=1):
        if counter is not None:
            scene.remove(counter)
        counter = Text(
            f"Question {i} / {len(pairs)}", font_size=24, color=theme["accent_color"]
        )
        counter.to_corner(UR)
        counter.set_z_index(20)
        scene.add(counter)

        add_message(
            question, font_size_q, theme["question_color"], question_bubble_color,
            align_right=False,
        )
        scene.wait(THINKING_PAUSE)

        add_message(
            answer, font_size_a, theme["answer_color"], answer_bubble_color,
            align_right=True,
        )
        scene.wait(1.0)
