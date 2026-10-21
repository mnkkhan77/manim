"""Reusable karaoke-style caption reveal + animated progress bar helpers.

Both pieces are self-contained and depend only on `manim`. Two usage levels
are exposed for each:

  - A low-level `build_*_animation(...)` function that just *builds* and
    returns a Manim `Animation` (never calls `scene.play`). Use these when
    you want to compose several animations together (e.g. with
    `AnimationGroup`) so they play concurrently in a single `scene.play`
    call.
  - A high-level convenience function (`karaoke_reveal` / `animate_progress`)
    that builds the animation above and immediately plays it with
    `scene.play(...)`. Use these for simple, standalone usage.
"""

from manim import *

# ---------------------------------------------------------------------------
# Karaoke-style caption reveal
# ---------------------------------------------------------------------------

# Opacity used for words that haven't been "spoken" yet -- dim, but still
# faintly readable rather than fully invisible.
DIM_OPACITY = 0.2

# How much a word scales up during its brief "pop" highlight.
POP_SCALE = 1.15

# Fractions of a word's total duration spent on: the quick highlight pop,
# holding briefly at full highlight, then settling into the normal
# "already read" color. Must sum to <= 1.
POP_FRACTION = 0.3
HOLD_FRACTION = 0.2


def prepare_words(words, base_color=WHITE):
    """Put `words` into their initial "not yet read" dim state.

    Sets every word's color to `base_color` and its opacity to a low, but
    non-zero, value. Call this (or `karaoke_reveal`, which calls it for you)
    before the words' first frame is rendered, i.e. before the paragraph
    they belong to is added to the scene or the scene starts playing.
    """
    for word in words:
        word.set_color(base_color)
        word.set_opacity(DIM_OPACITY)
    return words


def _lerp(start, end, t):
    return start + (end - start) * t


def _make_word_updater(word, base_color, highlight_color):
    """Build the per-frame update function for a single word's pop -> hold
    -> settle cycle, driven by a single alpha in [0, 1] across its whole
    duration.

    Note: this directly mutates color/opacity/height every frame rather
    than going through Mobject.animate()/Transform. Chaining multiple
    `.animate(...)` calls on the *same* mobject before they are played (as
    we do here, one word gets a "pop" and a "settle" stage) runs into a
    Manim quirk where each new `.animate` access overwrites the mobject's
    shared `.target` attribute, so an earlier-built `.animate` animation
    can silently end up pointing at a later one's target. Driving
    everything from one plain update function sidesteps that entirely and
    is easy to reason about.
    """
    base_height = word.height

    def updater(mob, alpha):
        if alpha <= POP_FRACTION:
            local = smooth(alpha / POP_FRACTION) if POP_FRACTION > 0 else 1.0
            color = interpolate_color(base_color, highlight_color, local)
            opacity = _lerp(DIM_OPACITY, 1, local)
            height = _lerp(base_height, base_height * POP_SCALE, local)
        elif alpha <= POP_FRACTION + HOLD_FRACTION:
            color = highlight_color
            opacity = 1
            height = base_height * POP_SCALE
        else:
            settle_span = max(1 - POP_FRACTION - HOLD_FRACTION, 1e-6)
            local = smooth((alpha - POP_FRACTION - HOLD_FRACTION) / settle_span)
            color = interpolate_color(highlight_color, base_color, local)
            opacity = 1
            height = _lerp(base_height * POP_SCALE, base_height, local)

        mob.set_color(color)
        mob.set_opacity(opacity)
        mob.set_height(height)

    return updater


def build_karaoke_animation(words, durations, base_color=WHITE, highlight_color=YELLOW):
    """Build (but do not play) a single Succession that reveals `words`.

    Each word, in order, briefly pops to `highlight_color` (with a slight
    scale-up) as if it is currently being spoken, then settles into
    `base_color` at full opacity -- a normal, readable "already read" state.
    Words further down the list remain dim until their own turn.

    `durations` must be a list of per-word durations (seconds), the same
    length as `words`. The returned animation's total run time is the sum
    of `durations`.
    """
    if len(words) != len(durations):
        raise ValueError("words and durations must be the same length")

    per_word_animations = [
        UpdateFromAlphaFunc(
            word,
            _make_word_updater(word, base_color, highlight_color),
            run_time=max(duration, 0.001),
            rate_func=linear,
        )
        for word, duration in zip(words, durations)
    ]

    return Succession(*per_word_animations)


def karaoke_reveal(scene, words, durations, base_color=WHITE, highlight_color=YELLOW):
    """Play a karaoke-style word-by-word reveal on an already-laid-out
    list of word Mobjects (e.g. the second return value of
    `interview_simulation.build_paragraph`).

    `scene` is the Scene instance this is called from (so it can call
    `scene.play(...)` internally). `words` must already be positioned in
    their final paragraph layout. `durations` is a list of per-word
    durations in seconds, the same length as `words`.

    This is a thin convenience wrapper around `prepare_words` +
    `build_karaoke_animation` + `scene.play`. If you need the reveal to run
    concurrently with another animation (e.g. a progress bar), use
    `build_karaoke_animation` directly inside your own `AnimationGroup`
    instead of calling this function.
    """
    prepare_words(words, base_color)

    not_yet_added = [w for w in words if w not in scene.mobjects]
    if not_yet_added:
        scene.add(*not_yet_added)

    scene.play(build_karaoke_animation(words, durations, base_color, highlight_color))


# ---------------------------------------------------------------------------
# Animated progress bar
# ---------------------------------------------------------------------------


def build_progress_bar(width=10, height=0.15, color=BLUE):
    """Build a simple horizontal progress bar.

    Returns a VGroup containing a background "track" rectangle and a
    foreground "fill" rectangle (starting at zero width), anchored so the
    fill's left edge sits on the track's left edge. The returned group also
    exposes `.track`, `.fill`, `.progress` (a ValueTracker in [0, 1]) and
    `.full_width` attributes so callers can build their own animations
    against it (see `build_progress_animation`).

    The bar can be freely repositioned (e.g. `bar.next_to(...)`) after
    creation -- the fill will keep tracking the track's (possibly moved)
    left edge.
    """
    track = Rectangle(
        width=width,
        height=height,
        stroke_width=1,
        stroke_color=GRAY_C,
        fill_color="#3a3a3a",
        fill_opacity=1,
    )
    fill = Rectangle(
        width=0.0001,
        height=height,
        stroke_width=0,
        fill_color=color,
        fill_opacity=1,
    )
    fill.move_to(track.get_left(), aligned_edge=LEFT)

    progress = ValueTracker(0)

    def _update_fill(mob):
        target_width = max(progress.get_value(), 0.0) * width
        target_width = max(target_width, 0.0001)
        mob.stretch_to_fit_width(target_width, about_edge=LEFT)
        # Re-anchor every frame so the fill tracks the track's left edge
        # even if the whole bar group gets moved after creation.
        mob.move_to(track.get_left(), aligned_edge=LEFT)

    fill.add_updater(_update_fill)

    bar = VGroup(track, fill)
    bar.track = track
    bar.fill = fill
    bar.progress = progress
    bar.full_width = width
    return bar


def build_progress_animation(bar, duration):
    """Build (but do not play) the animation that grows `bar` from empty
    to full over `duration` seconds, growing left-to-right.

    `bar` must be a Mobject produced by `build_progress_bar`. Resets the
    bar's progress to 0 before building the animation.
    """
    bar.progress.set_value(0)
    return bar.progress.animate(run_time=duration, rate_func=linear).set_value(1)


def animate_progress(scene, bar, duration):
    """Play `bar` (from `build_progress_bar`) growing smoothly from empty
    to full width over `duration` seconds, anchored so it grows
    left-to-right (the left edge stays fixed, only the right edge moves).

    `scene` is the Scene instance this is called from (so it can call
    `scene.play(...)` internally). If you need this to run concurrently
    with another animation, use `build_progress_animation` directly inside
    your own `AnimationGroup` instead of calling this function.
    """
    scene.play(build_progress_animation(bar, duration))
