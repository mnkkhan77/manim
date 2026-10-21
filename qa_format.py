"""
Shared Q&A script format used across the project: interview_simulation.py,
app.py, batch_render.py, and generate_metadata.py all parse this same format
through this module, so a malformed script fails the same way everywhere
instead of crashing differently (or silently) in each tool.

Format (blank-line separated blocks):
    Q: question text
    A: answer text, may wrap onto more lines before the next blank line

    Q: next question
    A: next answer

Question/answer text may use inline markdown-style emphasis, rendered by
styles that use reveal_common.build_paragraph (see AGENTS.md):
    **bold**, __bold__, ==highlight==, *italic*
"""


def parse_qa_text(raw):
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Script is empty.")

    pairs = []
    blocks = raw.split("\n\n")
    for i, block in enumerate(blocks, start=1):
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        if len(lines) < 2:
            raise ValueError(
                f"Block {i} is incomplete — expected a 'Q:' line followed by "
                f"an 'A:' line, got: {block!r}"
            )

        q_line, *rest = lines
        a_line = " ".join(rest)

        if ":" not in q_line or not q_line.strip().upper().startswith("Q"):
            raise ValueError(
                f"Block {i}: expected the first line to start with 'Q:', got: {q_line!r}"
            )
        if ":" not in a_line or not a_line.strip().upper().startswith("A"):
            raise ValueError(
                f"Block {i}: expected the answer line(s) to start with 'A:', got: {a_line!r}"
            )

        question = q_line.split(":", 1)[1].strip()
        answer = a_line.split(":", 1)[1].strip()

        if not question:
            raise ValueError(f"Block {i}: question text is empty after 'Q:'.")
        if not answer:
            raise ValueError(f"Block {i}: answer text is empty after 'A:'.")

        pairs.append((question, answer))

    if not pairs:
        raise ValueError("No Q/A pairs found — check the format (see module docstring).")

    return pairs


def parse_qa_file(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    return parse_qa_text(raw)
