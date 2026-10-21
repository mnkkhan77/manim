# Run with:
#   venv/Scripts/python.exe -m manim -ql complex_shapes.py SierpinskiTriangle
#   venv/Scripts/python.exe -m manim -ql complex_shapes.py PolarRose
#   venv/Scripts/python.exe -m manim -ql complex_shapes.py BooleanOpShape
# (swap -ql for -qm/-qh/-qk for higher quality)
import math

from manim import *

SQRT3 = math.sqrt(3)


class SierpinskiTriangle(Scene):
    def construct(self):
        def sierpinski(order, size):
            triangle = Triangle(fill_opacity=1, color=BLUE).scale(size)
            if order == 0:
                return triangle

            small = sierpinski(order - 1, size / 2)
            top = small.copy().shift(UP * size / SQRT3)
            left = small.copy().shift(DOWN * size / (2 * SQRT3) + LEFT * size / 2)
            right = small.copy().shift(DOWN * size / (2 * SQRT3) + RIGHT * size / 2)
            return VGroup(top, left, right)

        fractal = sierpinski(4, 3)
        self.play(FadeIn(fractal))
        self.wait()


class PolarRose(Scene):
    def construct(self):
        axes = PolarPlane(size=5)
        rose = axes.plot_polar_graph(
            lambda theta: 2 * np.cos(3 * theta), [0, TAU], color=PINK
        )
        self.play(Create(axes))
        self.play(Create(rose), run_time=3)
        self.wait()


class BooleanOpShape(Scene):
    def construct(self):
        circle = Circle(radius=1.5, color=BLUE, fill_opacity=0.5).shift(LEFT)
        square = Square(side_length=2.3, color=RED, fill_opacity=0.5).shift(RIGHT * 0.5)

        self.play(Create(circle), Create(square))
        self.wait()

        union = Union(circle, square, color=GREEN, fill_opacity=0.7)
        union.shift(DOWN * 2.5)
        self.play(
            FadeOut(circle), FadeOut(square),
            FadeIn(union),
        )
        self.wait()
