# Run with:
#   venv/Scripts/python.exe -m manim -ql animation_scenes.py UpdaterExample
#   venv/Scripts/python.exe -m manim -ql animation_scenes.py CameraMoveExample
# (swap -ql for -qm/-qh/-qk for higher quality)
from manim import *


class UpdaterExample(Scene):
    def construct(self):
        dot = Dot(color=YELLOW)
        label = Text("Follow me", font_size=24)
        label.add_updater(lambda m: m.next_to(dot, UP))

        self.add(dot, label)
        self.play(dot.animate.shift(RIGHT * 3))
        self.play(dot.animate.shift(UP * 2))
        self.play(dot.animate.shift(LEFT * 3 + DOWN * 2))
        self.wait()


class CameraMoveExample(MovingCameraScene):
    def construct(self):
        squares = VGroup(*[Square() for _ in range(5)])
        squares.arrange(RIGHT, buff=1)

        self.play(Create(squares))
        self.play(self.camera.frame.animate.scale(0.5).move_to(squares[2]))
        self.play(self.camera.frame.animate.scale(2).move_to(squares))
        self.wait()
