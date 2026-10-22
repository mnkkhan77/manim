import random
import re

# Same markdown emphasis patterns reveal_common.py's _parse_markdown_words
# understands: **bold**, __bold__, ==highlight==, *italic*. Marked spans are
# copied through untouched — fillers are only ever inserted in the plain text
# around them, never inside one.
_MARKDOWN_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__|==(.+?)==|\*(.+?)\*")

_WORD_RE = re.compile(r"\S+")

_SENTENCE_END = (".", "?", "!")
_ARTICLES = {"a", "an", "the"}
_CLAUSE_STARTERS = {"and", "but", "so"}
_EDGE_PUNCT = ".,!?;:\"')"

FILLERS = ["um", "uh", "well", "you know", "I mean"]


def _strip_edge_punct(word):
    return word.strip(_EDGE_PUNCT)


def _split_markdown(text):
    """Split text into (chunk, is_marked) pieces. Marked pieces keep their
    original markers verbatim; unmarked pieces are everything in between."""
    pieces = []
    pos = 0
    for m in _MARKDOWN_RE.finditer(text):
        if m.start() > pos:
            pieces.append((text[pos:m.start()], False))
        pieces.append((m.group(0), True))
        pos = m.end()
    if pos < len(text):
        pieces.append((text[pos:], False))
    return pieces


def _classify_gap(cur, nxt):
    """Decide whether the gap between word `cur` and word `nxt` is a natural
    place to drop a filler, and if so, what kind."""
    cur_bare = _strip_edge_punct(cur).lower()
    if cur_bare in _ARTICLES:
        return None

    if cur.endswith(_SENTENCE_END) and nxt[:1].isupper():
        return "sentence"
    if cur.endswith(","):
        return "comma"

    nxt_bare = _strip_edge_punct(nxt).lower()
    if nxt_bare in _CLAUSE_STARTERS:
        return "clause"
    return None


def _demote_sentence_start(word):
    """A word that's no longer the first word of its sentence (because a
    filler now sits in front of it) reads more naturally lowercased, unless
    it's "I" or looks like a proper noun / acronym (kept as-is to be safe)."""
    if not word or _strip_edge_punct(word) == "I":
        return word
    first, rest = word[0], word[1:]
    if not first.isupper() or rest[:1].isupper():
        return word
    return first.lower() + rest


def _inject_fillers(segment, rng, rate):
    tokens = list(_WORD_RE.finditer(segment))
    if len(tokens) < 2:
        return segment

    token_texts = [t.group() for t in tokens]
    pieces = [segment[:tokens[0].start()]]
    for i in range(len(tokens) - 1):
        cur = token_texts[i]
        nxt = token_texts[i + 1]
        gap_ws = segment[tokens[i].end():tokens[i + 1].start()]

        kind = _classify_gap(cur, nxt)
        insert = kind is not None and rng.random() < rate

        if insert and kind == "clause":
            cur = cur + ","
        if insert and kind == "sentence":
            token_texts[i + 1] = _demote_sentence_start(nxt)

        pieces.append(cur)
        pieces.append(gap_ws)

        if insert:
            filler = rng.choice(FILLERS)
            if kind == "sentence":
                filler = filler[0].upper() + filler[1:]
            pieces.append(filler + ", ")

    pieces.append(token_texts[-1])
    pieces.append(segment[tokens[-1].end():])
    return "".join(pieces)


def add_fillers(text, rate=0.15, seed=None):
    """Returns a new string with natural filler words/pauses inserted into
    the given answer text, for a less scripted, more spontaneous-sounding
    narration. `rate` is roughly the probability of inserting a filler at
    each eligible insertion point. `seed` optionally makes it
    deterministic for testing."""
    if not text or rate <= 0:
        return text

    rng = random.Random(seed)
    out = []
    for chunk, is_marked in _split_markdown(text):
        out.append(chunk if is_marked else _inject_fillers(chunk, rng, rate))
    return "".join(out)


if __name__ == "__main__":
    # 1. rate=0 -> byte-identical to input.
    sample = "I spent three years at a logistics startup, and I mostly focused on backend reliability. It was intense."
    assert add_fillers(sample, rate=0) == sample
    print("[ok] rate=0 is identity")

    # 2. determinism with a fixed seed.
    multi = (
        "I started out as a self-taught developer, and I eventually landed a job at a small agency. "
        "After that, I moved into backend work, but I still enjoy touching the frontend sometimes. "
        "So, over time, I became the person people asked about performance issues."
    )
    out1 = add_fillers(multi, rate=0.3, seed=42)
    out2 = add_fillers(multi, rate=0.3, seed=42)
    assert out1 == out2
    print("[ok] same seed -> identical output")
    print("--- determinism sample ---")
    print(out1)

    # 3. markdown safety.
    md = "I'm **really good** at debugging *tricky* problems, especially around ==distributed systems==."
    md_out = add_fillers(md, rate=1.0, seed=7)
    assert "**really good**" in md_out
    assert "*tricky*" in md_out
    assert "==distributed systems==" in md_out
    assert md_out != md
    assert any(f in md_out for f in FILLERS)
    print("[ok] markdown spans survive intact, fillers still inserted")
    print("--- markdown before ---")
    print(md)
    print("--- markdown after ---")
    print(md_out)

    # 4. longer realistic answer, eyeball check.
    answer = (
        "I've been working as a backend engineer for about five years now. "
        "My focus has mostly been on distributed systems, and I spent the last two years "
        "leading a small team at a fintech company. We rebuilt our payments pipeline from "
        "scratch, but it wasn't a smooth process. So we had to migrate traffic gradually "
        "while keeping the old system running. I think the biggest lesson was that "
        "communication matters more than the code itself."
    )
    before = answer
    after = add_fillers(answer, rate=0.3, seed=1)
    print("--- realistic answer: before ---")
    print(before)
    print("--- realistic answer: after ---")
    print(after)

    after2 = add_fillers(answer, rate=0.3, seed=99)
    print("--- realistic answer: after (seed=99) ---")
    print(after2)
