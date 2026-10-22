import random
import re

from manim import *

FONT_SIZE_Q = 34
FONT_SIZE_A = 30
LINE_BUFF = 0.25
WORD_BUFF = 0.15

# MAX_TEXT_WIDTH was tuned by eye as 11 units against the default landscape
# frame_width (128/9 ~= 14.222). Keeping it as a ratio of frame_width means
# build_paragraph's default max_width resolves to exactly 11 in landscape
# (unchanged behavior) and scales down correctly for a narrower portrait frame.
_MAX_TEXT_WIDTH_RATIO = 99 / 128


def is_portrait():
    return config.frame_width < config.frame_height


def font_size_for(base_size, portrait_scale=0.72):
    """Shrink a landscape-tuned font size for the narrower portrait frame, so
    roughly as many words still fit per line. No-op in landscape."""
    return int(base_size * portrait_scale) if is_portrait() else base_size

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


def strip_markdown(text):
    """Remove markdown emphasis markers, keeping the inner text. Used for TTS
    narration and subtitles, which should never speak or display literal
    **/__/==/* characters."""
    return " ".join(w for w, _ in _parse_markdown_words(text))


def build_paragraph(
    text, font_size, max_width=None, color=WHITE, word_buff=WORD_BUFF, line_buff=LINE_BUFF,
    highlight_color=DEFAULT_HIGHLIGHT_COLOR, font=None,
):
    if max_width is None:
        max_width = config.frame_width * _MAX_TEXT_WIDTH_RATIO
    parsed = _parse_markdown_words(text)
    return build_styled_paragraph(
        parsed, font_size, color, highlight_color, word_buff, line_buff, max_width, font=font
    )


def build_styled_paragraph(
    parsed, font_size, color, highlight_color, word_buff, line_buff, max_width, font=None,
):
    """Shared implementation behind `build_paragraph`, also used directly by
    styles that need a non-default font (style_terminal.py, style_whiteboard.py)
    instead of keeping their own near-duplicate word-wrap function.

    Builds each LINE as a single `Text` mobject (with per-word `t2c`/`t2w`/
    `t2s` spans for markdown styling) rather than arranging independent
    per-word `Text` mobjects. The latter is what this project used to do, and
    it has a real bug: Manim's `arrange()` centers each word's own bounding
    box, but words have different bounding-box heights depending on whether
    they contain ascenders/descenders (e.g. "a" vs "with" vs "years") -- so
    centering them together visibly floats short/ascender-free words above
    the rest of the line's true baseline. One `Text` per line lets Pango lay
    out the whole line with a single shared baseline, exactly like it would
    in any real paragraph of text. Word-level FadeIn targets are then taken
    as character-index slices of that Text (`Text.__getitem__` indexes the
    *rendered* string, i.e. whitespace-stripped, per Manim's own docs).
    """
    text_kwargs = {"font_size": font_size, "disable_ligatures": True}
    if font is not None:
        text_kwargs["font"] = font

    # Decide line-wrapping by measuring the actual candidate line text (one
    # throwaway Text per word, built on the running joined string) rather
    # than summing each word's width in isolation plus an estimated gap.
    # Those two numbers genuinely disagree -- for a ~170-character sentence
    # in Consolas, summed-words-plus-buff measured ~30 units while the real
    # joined-text Text measured ~33, an 11% gap from real inter-word spacing
    # (kerning/space-glyph width) not matching the buff estimate. Wrapping
    # off the smaller estimate let lines run past max_width in the real
    # render, pushing the tail of a line past the frame's right edge where
    # it's simply outside the camera's view -- invisible, not "cut off".
    # `word_buff` is kept as a small safety margin on top of real
    # measurement rather than the primary wrap signal.
    effective_max_width = max_width - word_buff

    lines, current_line, current_text = [], [], ""
    for w, style in parsed:
        candidate_text = f"{current_text} {w}" if current_text else w
        probe = Text(candidate_text, **text_kwargs)
        if current_line and probe.width > effective_max_width:
            lines.append(current_line)
            current_line, current_text = [(w, style)], w
        else:
            current_line.append((w, style))
            current_text = candidate_text
    if current_line:
        lines.append(current_line)

    line_mobjs = []
    ordered_words = []
    for line in lines:
        line_text = " ".join(w for w, _ in line)
        t2c, t2w, t2s = {}, {}, {}
        pos = 0
        for w, style in line:
            start, end = pos, pos + len(w)
            if style.get("highlight"):
                t2c[f"[{start}:{end}]"] = highlight_color
            if style.get("bold"):
                t2w[f"[{start}:{end}]"] = BOLD
            if style.get("italic"):
                t2s[f"[{start}:{end}]"] = ITALIC
            pos = end + 1  # +1 for the single joining space

        line_mobj = Text(line_text, color=color, t2c=t2c, t2w=t2w, t2s=t2s, **text_kwargs)
        word_slices = _split_line_into_words(line_mobj, len(line))
        for (w, _), word_slice in zip(line, word_slices):
            word_slice.text = w  # word_weight() reads this
            ordered_words.append(word_slice)
        line_mobjs.append(line_mobj)

    paragraph = VGroup(*line_mobjs).arrange(DOWN, aligned_edge=LEFT, buff=line_buff)
    return paragraph, ordered_words


def _split_line_into_words(line_mobj, n_words):
    """Partition a line Text's rendered glyphs into `n_words` left-to-right
    groups by detecting the gaps between words, rather than by indexing
    `line_mobj` at character positions computed from word lengths.

    That indexing approach was tried first and is unreliable: Manim/Pango
    doesn't guarantee one raw submobject per logical character. A dotted
    letter like "i" can render as two disjoint paths (dot + stem), and
    `disable_ligatures=True` (needed to stop "fi"/"fl"/"ffi" from silently
    merging into one glyph -- which would UNDER-count) makes this worse,
    consistently inflating the raw submobject count above the character
    count (confirmed empirically: a 44-character line rendered 49 raw
    submobjects). Any fixed per-word offset computed from word lengths then
    drifts out of alignment with the real glyph positions as soon as a line
    contains a character like that, silently handing some of one word's
    reveal animation to its neighbor -- which is what caused certain words
    (or their tails) to never be revealed at all in testing.
    Grouping by the actual rendered x-position gaps is immune to this: a
    word-separating space is a far bigger horizontal gap than the kerning
    between two letters of the same word, regardless of how many raw paths
    Pango happened to split any given glyph into.
    """
    chars = list(line_mobj)
    if n_words <= 1 or len(chars) <= 1:
        return [VGroup(*chars)]

    gaps = [
        (chars[i].get_left()[0] - chars[i - 1].get_right()[0], i)
        for i in range(1, len(chars))
    ]
    gaps.sort(key=lambda g: -g[0])
    boundaries = sorted(i for _, i in gaps[: n_words - 1])

    groups, start = [], 0
    for b in boundaries:
        groups.append(VGroup(*chars[start:b]))
        start = b
    groups.append(VGroup(*chars[start:]))
    return groups


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


def speak_and_reveal(scene, text, words, voice=None):
    """Run one voiceover block, revealing `words` in sync, and wait out any leftover audio.

    Pass `voice` (a manim_voiceover SpeechService instance) to switch the
    scene's narrator before this block — e.g. a different voice for
    questions vs answers. Omit it to keep whatever service is already set.
    """
    if voice is not None:
        scene.set_speech_service(voice)
    with scene.voiceover(text=strip_markdown(text)) as tracker:
        reveal_with_voiceover(scene, words, tracker.duration)
        remaining = tracker.get_remaining_duration()
        if remaining > 0:
            scene.wait(remaining)
