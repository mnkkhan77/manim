# Run with:
#   venv/Scripts/python.exe -m manim -ql text_scenes.py TextExample
#   venv/Scripts/python.exe -m manim -ql text_scenes.py MathTexExample
# (swap -ql for -qm/-qh/-qk for higher quality)
from manim import *


class TextExample(Scene):
    def construct(self):
        title = Text("Manim is Fun", font_size=48)
        subtitle = Text("Making videos with Python", font_size=28)
        subtitle.next_to(title, DOWN)

        self.play(Write(title))
        self.play(FadeIn(subtitle, shift=UP))
        self.wait()
        self.play(FadeOut(title), FadeOut(subtitle))


class MathTexExample(Scene):
    def construct(self):
        equation = MathTex(r"e^{i\pi} + 1 = 0")
        self.play(Write(equation))
        self.wait()

        transformed = MathTex(r"e^{i\pi} = -1")
        self.play(TransformMatchingTex(equation, transformed))
        self.wait()
