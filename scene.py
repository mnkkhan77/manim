# Run with:
#   venv/Scripts/python.exe -m manim -ql scene.py CreateCircle
#   venv/Scripts/python.exe -m manim -ql scene.py SquareToCircle
# (swap -ql for -qm/-qh/-qk for higher quality)
from manim import *


class CreateCircle(Scene):
    def construct(self):
        circle = Circle()
        circle.set_fill(PINK, opacity=0.5)
        self.play(Create(circle))


class SquareToCircle(Scene):
    def construct(self):
        circle = Circle()
        circle.set_fill(PINK, opacity=0.5)

        square = Square()
        square.rotate(PI / 4)

        self.play(Create(square))
        self.play(Transform(square, circle))
        self.play(FadeOut(square))
