"""
Script format for timeline_simulation.py (documentary/history style videos).

Format (blank-line separated blocks):
    LABEL: 1947
    IMAGE: images/independence.jpg
    India had just emerged from two centuries of British rule. Streets
    filled with both celebration and uncertainty.

    LABEL: 1950
    SEARCH: indian constitution signing
    The Constitution of India came into effect, making it the world's
    largest democracy.

LABEL and IMAGE/SEARCH lines are all optional, and if present must come
before the narration text, in that order. IMAGE and SEARCH are mutually
exclusive per scene (IMAGE wins if both are given) — IMAGE points at a local
file (resolved relative to this file's directory, timeline_video/, if not
absolute), SEARCH instead fetches a free stock photo matching the given
query via stock_fetch.fetch_stock_image (requires a Pexels and/or Pixabay
API key configured; falls back to the theme gradient background, same as a
scene with no image, if no key is configured or the lookup fails). Narration
text may wrap onto multiple lines before the next blank line, and supports
the same inline markdown-style emphasis as the Q&A pipeline (**bold**,
__bold__, ==highlight==, *italic*), rendered via reveal_common.build_paragraph.
"""


def parse_timeline_text(raw):
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Script is empty.")

    scenes = []
    blocks = raw.split("\n\n")
    for i, block in enumerate(blocks, start=1):
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        idx = 0
        label = None
        image = None
        search = None

        if lines[idx].strip().upper().startswith("LABEL:"):
            label = lines[idx].split(":", 1)[1].strip()
            idx += 1
        if idx < len(lines) and lines[idx].strip().upper().startswith("IMAGE:"):
            image = lines[idx].split(":", 1)[1].strip()
            idx += 1
        elif idx < len(lines) and lines[idx].strip().upper().startswith("SEARCH:"):
            search = lines[idx].split(":", 1)[1].strip()
            idx += 1

        text = " ".join(line.strip() for line in lines[idx:] if line.strip())
        if not text:
            raise ValueError(f"Block {i}: no narration text found (got: {block!r}).")

        scenes.append({"label": label, "image": image, "search": search, "text": text})

    if not scenes:
        raise ValueError("No scenes found — check the format (see module docstring).")

    return scenes


def parse_timeline_file(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    return parse_timeline_text(raw)
