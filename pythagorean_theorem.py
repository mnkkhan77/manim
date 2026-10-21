# Run with:
#   venv/Scripts/python.exe -m manim -qh pythagorean_theorem.py PythagoreanTheorem
# (swap -qh for -ql while iterating, -qk for final 4K export)
import numpy as np
from manim import *


def square_on_side(p1, p2, centroid, color):
    length = np.linalg.norm(p2 - p1)
    direction = (p2 - p1) / length
    normal = np.array([-direction[1], direction[0], 0])
    midpoint = (p1 + p2) / 2
    if np.dot(normal, midpoint - centroid) < 0:
        normal = -normal

    square = Square(side_length=length, color=color, fill_opacity=0.7)
    angle = np.arctan2(direction[1], direction[0])
    square.rotate(angle)
    square.move_to(midpoint + normal * length / 2)
    return square


class PythagoreanTheorem(Scene):
    def construct(self):
        title = Text("The Pythagorean Theorem", font_size=44)
        self.play(Write(title))
        self.wait()
        self.play(title.animate.to_edge(UP).scale(0.6))

        a, b = 1.8, 2.4
        p0, p1, p2 = np.array([0, 0, 0]), np.array([a, 0, 0]), np.array([a, b, 0])
        centroid = (p0 + p1 + p2) / 3

        triangle = Polygon(p0, p1, p2, color=WHITE, fill_opacity=0.1)

        right_angle = Square(side_length=0.25, color=WHITE)
        right_angle.move_to(p1, aligned_edge=UL).shift(LEFT * 0.125 + UP * 0.125)

        label_a = MathTex("a").next_to(Line(p0, p1), DOWN)
        label_b = MathTex("b").next_to(Line(p1, p2), RIGHT)
        label_c = MathTex("c").next_to(Line(p0, p2), UL, buff=0.1)

        square_a = square_on_side(p0, p1, centroid, BLUE)
        square_b = square_on_side(p1, p2, centroid, GREEN)
        square_c = square_on_side(p2, p0, centroid, RED)

        diagram = VGroup(
            triangle, right_angle, label_a, label_b, label_c,
            square_a, square_b, square_c,
        )
        diagram.move_to(LEFT * 3.3 + DOWN * 0.3)

        self.play(Create(triangle), Create(right_angle))
        self.play(Write(label_a), Write(label_b), Write(label_c))
        self.wait()
        self.play(FadeIn(square_a), FadeIn(square_b), FadeIn(square_c))
        self.wait()

        equation = MathTex("a^2", "+", "b^2", "=", "c^2", font_size=64)
        equation.set_color_by_tex("a^2", BLUE)
        equation.set_color_by_tex("b^2", GREEN)
        equation.set_color_by_tex("c^2", RED)
        equation.move_to(RIGHT * 3.3 + UP * 0.8)

        self.play(Write(equation))
        self.wait()

        numeric = MathTex("3^2", "+", "4^2", "=", "5^2", font_size=48)
        numeric.next_to(equation, DOWN, buff=0.6)
        self.play(FadeIn(numeric, shift=UP))
        self.wait()

        result = MathTex("9", "+", "16", "=", "25", font_size=48)
        result.move_to(numeric)
        self.play(TransformMatchingTex(numeric, result))
        self.wait(2)

        everything = VGroup(title, diagram, equation, result)
        self.play(FadeOut(everything))

        outro = Text("Thanks for watching!", font_size=48)
        self.play(Write(outro))
        self.wait(2)
        self.play(FadeOut(outro))
