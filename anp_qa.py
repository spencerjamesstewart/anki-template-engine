"""Shared driver for OpenStax-style Q:/A: block input files.

Parses `Q: ... A: ...` flashcard blocks (with '# CHAPTER N' or '# UNIT N'
banner lines marking chapter boundaries) into card dicts for
anki_templates.build_deck,
applies a per-driver OVERRIDES table, runs the self-checks, and writes the
deck. Extracted from gen_anp_ch4_6.py / gen_anp.py, which were byte-identical
apart from the source path, output path, expected card count, and chapter
range.
"""
import os
import re
import sys
from collections import Counter

from anki_templates import build_deck, register_input

_CHAPTER_RE = re.compile(r"^#\s*(?:CHAPTER|UNIT)\s+(\d+)\b")


def _clean(s):
    """Strip whitespace and a single trailing semicolon."""
    s = s.strip()
    if s.endswith(";"):
        s = s[:-1].strip()
    return s


def _esc(s):
    """HTML-escape &, <, > only (the engine does not auto-escape). Quotes
    are left untouched, unlike html.escape(quote=True)."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _esc_value(v):
    """Recursively HTML-escape strings inside a field value: a plain string,
    or a list/tuple of strings and/or (label, desc) tuples."""
    if isinstance(v, str):
        return _esc(v)
    if isinstance(v, tuple):
        return tuple(_esc_value(x) for x in v)
    if isinstance(v, list):
        return [_esc_value(x) for x in v]
    return v


# ─── Parsing ──────────────────────────────────────────────────────────────────

def parse_flashcards(path):
    """Parse Q:/A: blocks into (q, a, chapter) tuples, in source order.
    Chapter banner lines ('# CHAPTER N ...') update the current chapter;
    all other '#' lines and blank lines are ignored. A Q: line with no
    intervening non-comment/non-blank line before the next A: line is
    paired with it; anything else is a parse error."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    cards = []
    current_chapter = None
    pending_q = None
    pending_chapter = None

    for lineno, raw in enumerate(lines, 1):
        s = raw.strip()
        if s == "":
            continue
        if s.startswith("#"):
            m = _CHAPTER_RE.match(s)
            if m:
                current_chapter = int(m.group(1))
            continue
        if s.startswith("Q: "):
            if pending_q is not None:
                sys.exit("ERROR: line %d: 'Q: %s' follows an unanswered "
                          "'Q: %s' with no 'A:' in between." % (lineno, s[3:], pending_q))
            pending_q = _clean(s[3:])
            pending_chapter = current_chapter
            continue
        if s.startswith("A: "):
            if pending_q is None:
                sys.exit("ERROR: line %d: stray 'A: %s' with no preceding 'Q:'."
                          % (lineno, s[3:]))
            a_text = _clean(s[3:])
            cards.append((pending_q, a_text, pending_chapter))
            pending_q = None
            pending_chapter = None
            continue
        sys.exit("ERROR: line %d: unrecognized line (not Q:, A:, blank, or "
                  "comment): %r" % (lineno, raw))

    if pending_q is not None:
        sys.exit("ERROR: end of file: 'Q: %s' has no matching 'A:'." % pending_q)

    return cards


# ─── Card assembly ────────────────────────────────────────────────────────────

def apply_override(base, override):
    """Merge an OVERRIDES entry onto a base card. Override keys win, except
    'q' and 'tags' always survive from the base card. If the override
    supplies 'items' without supplying 'a', the base 'a' is dropped (the
    items replace it)."""
    card = dict(base)
    for k, v in override.items():
        if k in ("q", "tags"):
            continue
        card[k] = v
    if "items" in override and "a" not in override:
        card.pop("a", None)
    return card


def escape_card(card):
    """HTML-escape the free-text fields of a card in place."""
    for key in ("q", "a", "detail", "items"):
        if key in card:
            card[key] = _esc_value(card[key])
    return card


def front_key(card):
    """Whitespace-normalized, case-sensitive front key (matches
    gen_medterm.py's dedupe approach)."""
    raw = card.get("q") or ""
    return " ".join(raw.split())


def generate(driver_file, src_name, out_name, overrides,
             expected_count, chapters,
             deck_tags=("anatomy-physiology", "openstax-anp-2e"),
             chapter_tag_fmt="openstax-ch%d"):
    """Parse input/<src_name> into cards, apply `overrides`, run the self-checks,
    and write <out_name> next to `driver_file`."""
    here = os.path.dirname(os.path.abspath(driver_file))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    src_path = os.path.join(repo_root, "input", src_name)
    out = os.path.join(here, out_name)

    src = register_input(src_path)
    raw_cards = parse_flashcards(src)

    # self-check 1: parsed count matches '^Q: ' line count, and equals expected_count
    with open(src, encoding="utf-8") as f:
        q_line_count = sum(1 for line in f if line.startswith("Q: "))
    if len(raw_cards) != q_line_count:
        sys.exit("ERROR: parsed %d cards but found %d '^Q: ' lines."
                  % (len(raw_cards), q_line_count))
    if len(raw_cards) != expected_count:
        sys.exit("ERROR: parsed %d cards, expected %d." % (len(raw_cards), expected_count))

    # self-check 4: every OVERRIDES key must match exactly one real question
    q_counts = Counter(q for q, _a, _ch in raw_cards)
    bad_keys = [(key, q_counts.get(key, 0)) for key in overrides
                if q_counts.get(key, 0) != 1]
    if bad_keys:
        for key, n in bad_keys:
            print("ERROR: OVERRIDES key matched %d questions (expected 1): %r"
                  % (n, key), file=sys.stderr)
        sys.exit(1)

    cards = []
    for q, a, chapter in raw_cards:
        # self-check 3: every card must land in a known chapter
        if chapter not in chapters:
            sys.exit("ERROR: question %r has no valid chapter (got %r)."
                      % (q, chapter))
        base = {"type": "definition", "q": q, "a": a,
                "tags": [chapter_tag_fmt % chapter]}
        if q in overrides:
            base = apply_override(base, overrides[q])
        cards.append(escape_card(base))

    # self-check 5: no duplicate fronts
    seen = {}
    for card in cards:
        key = front_key(card)
        if key in seen:
            sys.exit("ERROR: duplicate front (key=%r): %r" % (key, card["q"]))
        seen[key] = True

    build_deck(cards, out, tags=list(deck_tags))

    dist = Counter(c["type"] for c in cards)
    print("Type distribution: %s"
          % ", ".join("%s: %d" % (t, n) for t, n in sorted(dist.items())),
          file=sys.stderr)
