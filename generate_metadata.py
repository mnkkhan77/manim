# Run with:
#   venv/Scripts/python.exe generate_metadata.py <script.txt> [--output metadata.txt]
"""Generate a YouTube title, description, and duration estimate from a Q&A script.

Usage:
    venv/Scripts/python.exe generate_metadata.py <script.txt> [--output metadata.txt]

Reads a plain-text interview script in the same "Q: ...\\nA: ...\\n\\n" block
format used by interview_script.txt and produces:
  - A suggested video TITLE (kept under ~70 characters).
  - A suggested DESCRIPTION with an intro line, a numbered list of the
    questions covered, and a closing call-to-action.
  - A rough ESTIMATED DURATION based on total word count and an assumed
    speaking rate.

This is intentionally pure, local, offline text-heuristics -- no ML models
and no network/API calls. It deliberately does NOT import interview_simulation
to avoid depending on its manim/voiceover stack.
"""

import argparse
import re
from collections import Counter
from pathlib import Path

from qa_format import parse_qa_file

WORDS_PER_MINUTE = 140

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for",
    "with", "is", "are", "your", "you", "i", "me", "my", "what", "whats",
    "what's", "do", "did", "does", "about", "that", "this", "it", "be",
    "can", "how", "why", "tell", "describe", "explain", "at", "as", "was",
    "were", "have", "has", "had", "not", "so", "if", "we", "us", "our",
    "from", "by", "would", "could", "should", "will", "when", "where",
    "who", "which", "than", "then", "them", "they", "their", "been",
    "being", "into", "out", "up", "down", "most", "some", "any", "all",
    "one", "like", "really", "think", "going", "want", "get", "got",
}


def _clean_word(word):
    return re.sub(r"[^a-zA-Z']", "", word).lower()


def _keywords(text):
    words = (_clean_word(w) for w in text.split())
    return {w for w in words if len(w) >= 4 and w not in STOPWORDS}


def build_title(pairs):
    n = len(pairs)
    questions = [q for q, _ in pairs]

    keyword_counts = Counter()
    for q in questions:
        keyword_counts.update(_keywords(q))

    # A "theme" is a keyword that shows up across more than one question.
    theme_words = [w for w, c in keyword_counts.items() if c >= 2]

    if theme_words:
        theme_words.sort(key=lambda w: (-keyword_counts[w], w))
        top = theme_words[:2]
        theme_str = " & ".join(w.capitalize() for w in top)
        title = f"{theme_str} Interview Questions ({n} Q&A)"
    else:
        title = f"Interview Practice: {n} Common Question{'s' if n != 1 else ''}"

    if len(title) > 70:
        title = title[:67].rstrip() + "..."
    return title


def build_description(pairs):
    n = len(pairs)
    lines = [
        f"In this video we walk through {n} common interview question{'s' if n != 1 else ''} "
        "with sample answers to help you prepare.",
        "",
        "What's covered:",
    ]
    for i, (question, _answer) in enumerate(pairs, start=1):
        lines.append(f"{i}. {question}")
    lines.append("")
    lines.append(
        "If this helped you prepare, like, subscribe, and drop a comment with "
        "questions you'd like to see covered next!"
    )
    return "\n".join(lines)


def estimate_duration(pairs):
    total_words = 0
    for question, answer in pairs:
        total_words += len(question.split())
        total_words += len(answer.split())
    total_seconds = round((total_words / WORDS_PER_MINUTE) * 60)
    minutes, seconds = divmod(total_seconds, 60)
    return f"~{minutes}m {seconds}s", total_words


def build_metadata_text(pairs):
    title = build_title(pairs)
    description = build_description(pairs)
    duration_str, total_words = estimate_duration(pairs)
    content = (
        f"TITLE:\n{title}\n\n"
        f"DESCRIPTION:\n{description}\n\n"
        f"ESTIMATED DURATION:\n{duration_str} (based on {total_words} words at ~{WORDS_PER_MINUTE} wpm)\n"
    )
    return content


def main():
    parser = argparse.ArgumentParser(
        description="Generate a YouTube title/description/duration estimate from a Q&A interview script."
    )
    parser.add_argument("script", help="Path to a Q&A script .txt file (same format as interview_script.txt)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: metadata.txt next to the input script)",
    )
    args = parser.parse_args()

    script_path = Path(args.script)
    if not script_path.is_file():
        print(f"Error: '{script_path}' not found.")
        raise SystemExit(1)

    try:
        pairs = parse_qa_file(script_path)
    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)

    content = build_metadata_text(pairs)

    output_path = Path(args.output) if args.output else script_path.parent / "metadata.txt"
    output_path.write_text(content, encoding="utf-8")

    print(content)


if __name__ == "__main__":
    main()
