"""Reusable intro/outro branding card builders for YouTube interview videos.

These functions build fully-positioned Mobjects for use as title / sign-off
cards. They assume the scene already has a dark background in place (see
interview_simulation.py's BG_COLORS gradient rectangle for the style this
was designed against) -- no background shape is added here.

The caller is responsible for animating the returned Mobject in/out
(e.g. Write, FadeIn, FadeOut) and for adding/removing it from the scene.
"""

from manim import *

ACCENT_COLOR = "#8e7cff"


def build_intro_card(channel_name, episode_title=None):
    """Build an intro / title card.

    Args:
        channel_name: str, shown large and prominent.
        episode_title: optional str, shown smaller below the channel name
            as a subtitle.

    Returns:
        A VGroup containing the title text, a thin accent line, and
        (optionally) the subtitle text, arranged vertically and centered
        on the origin.
    """
    title = Text(channel_name, font_size=64, color=WHITE, weight=BOLD)

    accent_line = Line(LEFT, RIGHT, color=ACCENT_COLOR, stroke_width=4)
    accent_line.set_width(min(title.width * 0.6, 4.0))

    parts = [title, accent_line]

    if episode_title:
        subtitle = Text(episode_title, font_size=32, color=GRAY_B)
        parts.append(subtitle)

    card = VGroup(*parts).arrange(DOWN, buff=0.35)
    card.move_to(ORIGIN)
    return card


def build_outro_card(message="Thanks for watching! Like and subscribe.", handle=None):
    """Build an outro / sign-off card.

    Args:
        message: str, the main sign-off text.
        handle: optional str, e.g. "@username", shown smaller below the
            message.

    Returns:
        A VGroup containing the message text and (optionally) the handle
        text, arranged vertically and centered on the origin.
    """
    main_text = Text(message, font_size=40, color=WHITE, weight=BOLD)
    if main_text.width > 11:
        main_text.scale_to_fit_width(11)

    parts = [main_text]

    if handle:
        handle_text = Text(handle, font_size=28, color=ACCENT_COLOR)
        parts.append(handle_text)

    card = VGroup(*parts).arrange(DOWN, buff=0.3)
    card.move_to(ORIGIN)
    return card
