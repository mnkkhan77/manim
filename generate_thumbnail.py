# Run with:
#   venv/Scripts/python.exe generate_thumbnail.py "Title text" [--subtitle "..."] [--theme midnight] [--output thumbnail.png]
"""Standalone YouTube thumbnail generator.

Draws a bold, theme-colored thumbnail image (gradient or solid background
pulled from themes.py) with a large title and an optional smaller subtitle,
sized for YouTube (1280x720 by default). Not wired into the manim render or
app.py -- a separate one-off tool, same pattern as burn_subtitles.py /
generate_metadata.py.

Usage:
    venv/Scripts/python.exe generate_thumbnail.py "Why is this interview question so hard?" \\
        --subtitle "Interview Practice" --theme midnight --output thumbnail.png

Examples:
    venv/Scripts/python.exe generate_thumbnail.py "Explain closures in JavaScript"
    venv/Scripts/python.exe generate_thumbnail.py "System Design: Rate Limiters" --theme neon --subtitle "Ep. 12"
"""

import argparse

from PIL import Image, ImageDraw, ImageFont

from themes import get_theme

BOLD_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/impact.ttf",
]


def _load_font(size):
    for path in BOLD_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_gradient(draw, width, height, colors):
    stops = len(colors) - 1
    for y in range(height):
        pos = y / max(height - 1, 1) * stops
        i = min(int(pos), stops - 1)
        local_t = pos - i
        c1, c2 = colors[i], colors[i + 1]
        r = round(c1[0] + (c2[0] - c1[0]) * local_t)
        g = round(c1[1] + (c2[1] - c1[1]) * local_t)
        b = round(c1[2] + (c2[2] - c1[2]) * local_t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _wrap_to_fit(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_title(draw, text, max_width, max_height, start_size=120, min_size=48):
    size = start_size
    while size >= min_size:
        font = _load_font(size)
        lines = _wrap_to_fit(draw, text, font, max_width)
        if len(lines) > 2:
            size -= 6
            continue
        line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
        total_height = line_height * len(lines) * 1.25
        if total_height <= max_height:
            return font, lines
        size -= 6
    font = _load_font(min_size)
    return font, _wrap_to_fit(draw, text, font, max_width)[:2]


def _draw_centered_text(draw, lines, font, center_x, top_y, fill, outline, line_spacing=1.25):
    bbox = font.getbbox("Ag")
    line_height = (bbox[3] - bbox[1]) * line_spacing
    y = top_y
    for line in lines:
        width = draw.textlength(line, font=font)
        x = center_x - width / 2
        if outline:
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
                draw.text((x + dx, y + dy), line, font=font, fill=outline)
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def generate_thumbnail(
    title,
    subtitle=None,
    theme_name="midnight",
    output_path="thumbnail.png",
    width=1280,
    height=720,
):
    theme = get_theme(theme_name)
    bg_colors = theme["bg_colors"]

    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)

    if isinstance(bg_colors, (list, tuple)) and len(bg_colors) >= 2:
        rgb_colors = [ImageDraw.ImageColor.getrgb(c) for c in bg_colors]
        _draw_gradient(draw, width, height, rgb_colors)
    else:
        color = bg_colors[0] if isinstance(bg_colors, (list, tuple)) else bg_colors
        draw.rectangle([0, 0, width, height], fill=ImageDraw.ImageColor.getrgb(color))

    accent = ImageDraw.ImageColor.getrgb(theme["accent_color"])
    bar_height = max(6, height // 80)
    draw.rectangle([0, 0, width, bar_height], fill=accent)
    draw.rectangle([0, height - bar_height, width, height], fill=accent)

    margin_x = round(width * 0.08)
    max_text_width = width - 2 * margin_x
    title_color = ImageDraw.ImageColor.getrgb(theme["question_color"])
    outline_color = (0, 0, 0)

    title_area_height = round(height * (0.55 if subtitle else 0.65))
    title_font, title_lines = _fit_title(draw, title, max_text_width, title_area_height)

    bbox = title_font.getbbox("Ag")
    line_height = (bbox[3] - bbox[1]) * 1.25
    total_title_height = line_height * len(title_lines)

    if subtitle:
        subtitle_font = _load_font(round(title_font.size * 0.35))
        sub_bbox = subtitle_font.getbbox("Ag")
        subtitle_height = (sub_bbox[3] - sub_bbox[1]) * 1.4
        block_height = total_title_height + subtitle_height
    else:
        block_height = total_title_height

    top_y = (height - block_height) / 2
    center_x = width / 2

    bottom_of_title = _draw_centered_text(
        draw, title_lines, title_font, center_x, top_y, title_color, outline_color
    )

    if subtitle:
        answer_color = ImageDraw.ImageColor.getrgb(theme["answer_color"])
        _draw_centered_text(
            draw, [subtitle], subtitle_font, center_x, bottom_of_title + round(height * 0.02),
            answer_color, outline_color,
        )

    image.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate a YouTube thumbnail.")
    parser.add_argument("title")
    parser.add_argument("--subtitle", default=None)
    parser.add_argument("--theme", default="midnight")
    parser.add_argument("--output", default="thumbnail.png")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()

    output_path = generate_thumbnail(
        args.title,
        subtitle=args.subtitle,
        theme_name=args.theme,
        output_path=args.output,
        width=args.width,
        height=args.height,
    )
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
