"""Ready-made color theme presets for Manim scenes (e.g. interview_simulation.py).

Each theme is a dict with:
    "bg_colors":      list of 2-3 hex strings for a gradient background fill,
                       usable directly as `mobject.set_fill(color=[...], opacity=1)`.
    "question_color": hex string for question text, high contrast against bg.
    "answer_color":   hex string for answer text, high contrast against bg.
    "accent_color":   hex string for small UI elements (progress bar, counter, etc).

Usage:
    from themes import get_theme
    theme = get_theme("midnight")
    background.set_fill(color=theme["bg_colors"], opacity=1)
    question_text = Text(question, color=theme["question_color"])
"""

THEMES = {
    # The original dark navy/purple gradient from interview_simulation.py.
    # Proven to look good with yellow question text and white answer text.
    "midnight": {
        "bg_colors": ["#0f0c29", "#302b63", "#24243e"],
        "question_color": "#FFD60A",  # warm yellow
        "answer_color": "#FFFFFF",    # white
        "accent_color": "#9D8CFF",    # soft lavender accent
    },

    # Dark gray / near-black with a warm amber accent.
    "charcoal": {
        "bg_colors": ["#141414", "#232323", "#2e2e2e"],
        "question_color": "#FFB84D",  # warm amber
        "answer_color": "#F5F5F5",    # near-white
        "accent_color": "#FF8A00",    # vivid orange accent
    },

    # Light/clean theme: near-white gradient with dark navy/near-black text.
    "daylight": {
        "bg_colors": ["#FFFFFF", "#F1F3F6", "#E6E9F0"],
        "question_color": "#0B1F3A",  # dark navy
        "answer_color": "#1C1C1E",    # near-black
        "accent_color": "#1A73E8",    # saturated blue accent
    },

    # Near-black background with vivid cyan/magenta neon accents.
    "neon": {
        "bg_colors": ["#060608", "#0D0D12"],
        "question_color": "#00F5FF",  # vivid cyan
        "answer_color": "#FF2BD1",    # vivid magenta
        "accent_color": "#CCFF00",    # neon chartreuse accent
    },
}


def get_theme(name):
    """Return the theme dict registered under `name`.

    Raises ValueError with the list of available theme names if `name`
    is not a known theme.
    """
    try:
        return THEMES[name]
    except KeyError:
        available = ", ".join(sorted(THEMES.keys()))
        raise ValueError(
            f"Unknown theme '{name}'. Available themes: {available}"
        ) from None
