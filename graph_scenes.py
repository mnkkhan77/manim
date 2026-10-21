# Run with:
#   venv/Scripts/python.exe -m manim -ql graph_scenes.py GraphExample
#   venv/Scripts/python.exe -m manim -ql graph_scenes.py BarChartExample
# (swap -ql for -qm/-qh/-qk for higher quality)
from manim import *


class GraphExample(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 9, 1],
            axis_config={"include_tip": True},
        )
        labels = axes.get_axis_labels(x_label="x", y_label="y")

        graph = axes.plot(lambda x: x**2, color=BLUE)
        graph_label = axes.get_graph_label(graph, label="x^2")

        self.play(Create(axes), Write(labels))
        self.play(Create(graph), Write(graph_label))
        self.wait()


class BarChartExample(Scene):
    def construct(self):
        chart = BarChart(
            values=[3, 7, 5, 9, 4],
            bar_names=["Jan", "Feb", "Mar", "Apr", "May"],
            y_range=[0, 10, 2],
            y_axis_config={"font_size": 24},
        )
        self.play(Create(chart))
        self.play(chart.animate.change_bar_values([5, 2, 8, 3, 9]))
        self.wait()
