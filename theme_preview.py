"""Visual preview scene for all color themes defined in themes.py.

Renders a single frame split into horizontal bands, one per theme, each
filled with that theme's background gradient and showing the theme name
(in question_color) and sample answer text (in answer_color), so contrast
and legibility can be checked at a glance.

Render with:
    manim -ql theme_preview.py ThemePreview --disable_caching
"""
from manim import *

from themes import THEMES


class ThemePreview(Scene):
    def construct(self):
        theme_names = list(THEMES.keys())
        n = len(theme_names)

        band_width = config.frame_width
        band_height = config.frame_height / n

        top_y = config.frame_height / 2

        for i, name in enumerate(theme_names):
            theme = THEMES[name]

            band_center_y = top_y - band_height * (i + 0.5)

            band = Rectangle(
                width=band_width,
                height=band_height,
                stroke_width=0,
            ).set_fill(color=theme["bg_colors"], opacity=1)
            band.move_to(UP * band_center_y)
            band.set_z_index(-10)
            self.add(band)

            title = Text(
                name.upper(),
                font_size=34,
                weight=BOLD,
                color=theme["question_color"],
            )
            sample = Text(
                "Sample answer text",
                font_size=26,
                color=theme["answer_color"],
            )

            text_group = VGroup(title, sample).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
            text_group.move_to(UP * band_center_y + LEFT * 2.0)

            accent_dot = Dot(radius=0.14, color=theme["accent_color"])
            accent_label = Text("accent", font_size=18, color=theme["accent_color"])
            accent_group = VGroup(accent_dot, accent_label).arrange(RIGHT, buff=0.15)
            accent_group.move_to(UP * band_center_y + RIGHT * 4.8)

            self.add(text_group, accent_group)

        self.wait(1)
