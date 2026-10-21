from manim import *

from branding import build_intro_card, build_outro_card

BG_COLORS = ["#1b1033", "#2a1b4d", "#120c24"]


class BrandingDemo(Scene):
    def construct(self):
        background = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            stroke_width=0,
        ).set_fill(color=BG_COLORS, opacity=1)
        background.set_z_index(-10)
        self.add(background)

        intro = build_intro_card("Nasir's Interview Prep", episode_title="Episode 1: Behavioral Questions")
        self.play(Write(intro))
        self.wait(1.5)
        self.play(FadeOut(intro))

        placeholder = Text("...interview content would go here...", font_size=32, color=WHITE)
        self.play(FadeIn(placeholder))
        self.wait(1.0)
        self.play(FadeOut(placeholder))

        outro = build_outro_card(handle="@nasirs_prep")
        self.play(FadeIn(outro))
        self.wait(1.5)
        self.play(FadeOut(outro))
