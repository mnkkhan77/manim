from manim import *

from caption_utils import (
    build_karaoke_animation,
    build_progress_animation,
    build_progress_bar,
    prepare_words,
)

SENTENCE = "This is how karaoke captions look"
FONT_SIZE = 48
WORD_BUFF = 0.35

# Made-up per-word durations (seconds), between 0.3 and 0.6s each.
DURATIONS = [0.4, 0.3, 0.45, 0.35, 0.6, 0.5]

BASE_COLOR = WHITE
HIGHLIGHT_COLOR = YELLOW


class CaptionProgressDemo(Scene):
    def construct(self):
        words_text = SENTENCE.split()
        assert len(words_text) == len(DURATIONS)

        words = [Text(w, font_size=FONT_SIZE) for w in words_text]
        sentence = VGroup(*words).arrange(RIGHT, buff=WORD_BUFF)
        sentence.move_to(UP * 0.5)

        # Put the words in their dim "not yet read" state before the first
        # frame is rendered.
        prepare_words(words, base_color=BASE_COLOR)
        self.add(sentence)

        bar = build_progress_bar(width=8, height=0.15, color=BLUE)
        bar.next_to(sentence, DOWN, buff=1.0)
        self.add(bar)

        total_duration = sum(DURATIONS)

        # Build both animations without playing them, then run them
        # concurrently inside a single AnimationGroup / scene.play call so
        # the progress bar fills in lockstep with the karaoke reveal.
        karaoke_anim = build_karaoke_animation(
            words, DURATIONS, base_color=BASE_COLOR, highlight_color=HIGHLIGHT_COLOR
        )
        progress_anim = build_progress_animation(bar, total_duration)

        self.play(AnimationGroup(karaoke_anim, progress_anim))
        self.wait(0.5)
