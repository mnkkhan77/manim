import random
import re

from manim import *

FONT_SIZE_Q = 34
FONT_SIZE_A = 30
MAX_TEXT_WIDTH = 11
LINE_BUFF = 0.25
WORD_BUFF = 0.15

# Short beat of silence after a question finishes and before the answer
# starts, to simulate someone taking a breath before responding.
THINKING_PAUSE = 1.2

# Range for the random per-word timing jitter applied in word_weight(),
# so the word-by-word reveal doesn't look like a perfect metronome.
JITTER_RANGE = (0.85, 1.15)

DEFAULT_HIGHLIGHT_COLOR = "#FFD60A"

# Inline markdown-style emphasis supported in Q&A script text:
#   **bold**, __bold__, ==highlight==, *italic*
# Double-marker alternatives are tried before the single-star one so "**x**"
# isn't swallowed as two adjacent "*x*" matches.
_MARKDOWN_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__|==(.+?)==|\*(.+?)\*")


def _parse_markdown_words(text):
    """Split text into (word, style) pairs, where style is a dict that may
    contain 'bold', 'italic', and/or 'highlight', based on markdown-style
    emphasis markers. Markers themselves are stripped from the output."""
    words = []

    def add_plain(chunk):
        for w in chunk.split():
            words.append((w, {}))

    pos = 0
    for m in _MARKDOWN_RE.finditer(text):
        if m.start() > pos:
            add_plain(text[pos:m.start()])

        if m.group(1) is not None:
            style, inner = {"bold": True}, m.group(1)
        elif m.group(2) is not None:
            style, inner = {"bold": True}, m.group(2)
        elif m.group(3) is not None:
            style, inner = {"highlight": True}, m.group(3)
        else:
            style, inner = {"italic": True}, m.group(4)

        for w in inner.split():
            words.append((w, style))
        pos = m.end()

    if pos < len(text):
        add_plain(text[pos:])

    return words


def word_weight(word):
    if word.endswith((".", "?", "!")):
        base = 1.8
    elif word.endswith(","):
        base = 1.3
    else:
        base = 1.0
    return base * random.uniform(*JITTER_RANGE)


def build_paragraph(
    text, font_size, max_width, color=WHITE, word_buff=WORD_BUFF, line_buff=LINE_BUFF,
    highlight_color=DEFAULT_HIGHLIGHT_COLOR,
):
    parsed = _parse_markdown_words(text)
    word_mobs = [
        Text(
            w,
            font_size=font_size,
            color=highlight_color if style.get("highlight") else color,
            weight=BOLD if style.get("bold") else NORMAL,
            slant=ITALIC if style.get("italic") else NORMAL,
        )
        for w, style in parsed
    ]

    lines, current_line, current_width = [], [], 0
    for wm in word_mobs:
        projected = current_width + wm.width + (word_buff if current_line else 0)
        if current_line and projected > max_width:
            lines.append(current_line)
            current_line, current_width = [wm], wm.width
        else:
            current_line.append(wm)
            current_width = projected
    if current_line:
        lines.append(current_line)

    line_groups = [VGroup(*line).arrange(RIGHT, buff=word_buff) for line in lines]
    paragraph = VGroup(*line_groups).arrange(DOWN, aligned_edge=LEFT, buff=line_buff)

    ordered_words = [wm for line in lines for wm in line]
    return paragraph, ordered_words


def reveal_with_voiceover(scene, words, duration):
    weights = [word_weight(w.text) for w in words]
    total_weight = sum(weights)
    scene.play(LaggedStart(
        *[
            FadeIn(wm, run_time=max(0.05, duration * (w / total_weight)))
            for wm, w in zip(words, weights)
        ],
        lag_ratio=1,
        run_time=duration,
    ))


def speak_and_reveal(scene, text, words):
    """Run one voiceover block, revealing `words` in sync, and wait out any leftover audio."""
    with scene.voiceover(text=text) as tracker:
        reveal_with_voiceover(scene, words, tracker.duration)
        remaining = tracker.get_remaining_duration()
        if remaining > 0:
            scene.wait(remaining)
