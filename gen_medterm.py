#!/usr/bin/env python3
"""Driver: builds three medical-terminology decks (word parts, abbreviations,
eponyms) from input/glossary-cleaned.txt and input/abbreviations-cleaned.txt.

Run via: ./run.sh gen gen_medterm.py   (or `python3 gen_medterm.py` directly
from the repo root).
"""
import os
import sys

from anki_templates import build_deck, register_input

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(REPO_ROOT, "outbox",
                       "2026-07-15-medical-terminology-language-of-medicine")

GLOSSARY_PATH = os.path.join(REPO_ROOT, "input", "glossary-cleaned.txt")
ABBREV_PATH = os.path.join(REPO_ROOT, "input", "abbreviations-cleaned.txt")

COMMON_TAGS = ["medical-terminology", "the-language-of-medicine-glossary"]


def _clean(s):
    """Strip whitespace and a single trailing semicolon."""
    s = s.strip()
    if s.endswith(";"):
        s = s[:-1].strip()
    return s


# ─── Deck A: word parts ─────────────────────────────────────────────────────

def classify_part(part):
    """Classify a word-part front by its FIRST token's shape."""
    first_token = part.split(",")[0].strip()
    if first_token.startswith("-"):
        return "suffix"
    if first_token.endswith("-"):
        return "prefix"
    return "combining_form"


def parse_glossary(path):
    """Parse lines 2..(first blank before the second '##' header) of the
    glossary file: part<TAB>meaning. Stops at the second '##' header."""
    cards = []
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    header_count = 0
    for line in lines:
        if line.startswith("##"):
            header_count += 1
            if header_count >= 2:
                break
            continue
        if header_count == 0:
            continue  # before the first header
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 2:
            print("WARNING: skipping malformed glossary line: %r" % line,
                  file=sys.stderr)
            continue
        part = fields[0].strip()
        meaning = _clean(fields[1])
        if not part or not meaning:
            print("WARNING: skipping empty glossary entry: %r" % line,
                  file=sys.stderr)
            continue
        cls = classify_part(part)
        cards.append({"type": cls, "part": part, "a": meaning})
    return cards


# ─── Deck B: abbreviations ───────────────────────────────────────────────────

def parse_abbrev_sections(path):
    """Split abbreviations-cleaned.txt into named sections keyed by their
    '##' header text, each a list of raw TAB-split field rows."""
    sections = {}
    current_name = None
    current_rows = []
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    for line in lines:
        if line.startswith("##"):
            if current_name is not None:
                sections[current_name] = current_rows
            current_name = line
            current_rows = []
            continue
        if not line.strip():
            continue
        if current_name is None:
            continue
        current_rows.append(line.split("\t"))
    if current_name is not None:
        sections[current_name] = current_rows
    return sections


def _section_key(sections, prefix):
    for name in sections:
        if name.startswith(prefix):
            return name
    raise KeyError("no section found starting with %r among %r"
                    % (prefix, list(sections)))


def build_abbreviation_entries(sections):
    """Return a list of (front_q, meaning, note_or_None) tuples, one per raw
    row, from the Abbreviations / Symbols / Acronyms / Do-Not-Use sections.
    Merging by front happens later in the caller."""
    entries = []

    abbr_key = _section_key(sections, "## Abbreviations")
    symbol_key = _section_key(sections, "## Symbols")
    acronym_key = _section_key(sections, "## Acronyms")
    dnu_key = _section_key(sections, "## Do Not Use")

    for row in sections[abbr_key]:
        if len(row) < 2:
            print("WARNING: skipping malformed Abbreviations row: %r" % row,
                  file=sys.stderr)
            continue
        abbr, meaning = row[0].strip(), _clean(row[1])
        if not abbr or not meaning:
            print("WARNING: skipping empty Abbreviations row: %r" % row,
                  file=sys.stderr)
            continue
        q = "What does *%s* stand for?" % abbr
        entries.append((q, meaning, None))

    for row in sections[symbol_key]:
        if len(row) < 2:
            print("WARNING: skipping malformed Symbols row: %r" % row,
                  file=sys.stderr)
            continue
        sym, meaning = row[0].strip(), _clean(row[1])
        if not sym or not meaning:
            print("WARNING: skipping empty Symbols row: %r" % row,
                  file=sys.stderr)
            continue
        if sym.startswith("[symbol not captured]"):
            print("WARNING: skipping uncaptured symbol row: %r" % row,
                  file=sys.stderr)
            continue
        q = "What does the symbol *%s* mean?" % sym
        entries.append((q, meaning, None))

    for row in sections[acronym_key]:
        if len(row) < 2:
            print("WARNING: skipping malformed Acronyms row: %r" % row,
                  file=sys.stderr)
            continue
        acr, meaning = row[0].strip(), _clean(row[1])
        if not acr or not meaning:
            print("WARNING: skipping empty Acronyms row: %r" % row,
                  file=sys.stderr)
            continue
        q = "What does *%s* stand for?" % acr
        entries.append((q, meaning, None))

    for row in sections[dnu_key]:
        if len(row) < 2:
            print("WARNING: skipping malformed Do-Not-Use row: %r" % row,
                  file=sys.stderr)
            continue
        abbr = row[0].strip()
        reason = _clean(row[1]) if len(row) >= 2 else ""
        correction = _clean(row[2]) if len(row) >= 3 else ""
        if not abbr or not reason:
            print("WARNING: skipping empty Do-Not-Use row: %r" % row,
                  file=sys.stderr)
            continue
        q = "What does *%s* stand for?" % abbr
        note = ("Write *%s* instead." % correction) if correction else None
        entries.append((q, reason, note))

    return entries


def merge_abbreviation_entries(entries):
    """Group entries sharing the same front question; join distinct
    meanings with '; ', dedupe identical meanings, preserve first-seen
    order, and merge notes (keep whichever notes are present)."""
    order = []
    by_q = {}
    for q, meaning, note in entries:
        if q not in by_q:
            by_q[q] = {"meanings": [], "notes": []}
            order.append(q)
        bucket = by_q[q]
        if meaning not in bucket["meanings"]:
            bucket["meanings"].append(meaning)
        if note and note not in bucket["notes"]:
            bucket["notes"].append(note)

    cards = []
    for q in order:
        bucket = by_q[q]
        merged_meaning = _clean("; ".join(bucket["meanings"]))
        card = {"type": "alias", "q": q, "a": merged_meaning}
        if bucket["notes"]:
            card["note"] = " ".join(bucket["notes"])
        cards.append(card)
    return cards


# ─── Deck C: eponyms ─────────────────────────────────────────────────────────

def parse_eponym_entry(name, definition):
    """Split off the trailing '(named after: ...)' parenthetical (tolerating
    a stray extra closing paren in the source text) and shorten the
    remaining definition to its first sentence."""
    detail = None
    marker = "(named after:"
    idx = definition.find(marker)
    if idx != -1:
        body = definition[:idx].strip()
        named = definition[idx + len(marker):].strip()
        while named.endswith(")"):
            named = named[:-1].strip()
        detail = "Named after %s." % named
    else:
        body = definition.strip()

    first_sentence = body.split(". ")[0].strip()
    # Trim a lone trailing period left over from a single-sentence body only
    # if it would otherwise look odd; periods are fine, just no trailing ';'.
    answer = _clean(first_sentence)
    return answer, detail


def build_eponym_cards(sections):
    eponym_key = _section_key(sections, "## Eponyms")
    cards = []
    for row in sections[eponym_key]:
        if len(row) < 2:
            print("WARNING: skipping malformed Eponyms row: %r" % row,
                  file=sys.stderr)
            continue
        name = row[0].strip()
        definition = row[1].strip()
        if not name or not definition:
            print("WARNING: skipping empty Eponyms row: %r" % row,
                  file=sys.stderr)
            continue
        answer, detail = parse_eponym_entry(name, definition)
        if not answer:
            print("WARNING: skipping eponym with empty gist: %r" % row,
                  file=sys.stderr)
            continue
        card = {"type": "definition", "q": name, "a": answer}
        if detail:
            card["detail"] = detail
        cards.append(card)
    return cards


# ─── Cross-deck dedupe ────────────────────────────────────────────────────────

def front_key(card):
    """Approximate normalized front key for collision detection: the
    authored 'q', or 'part' for word-part types (auto-generated q).
    Whitespace-normalized only -- NOT case-folded, since case is
    semantically significant for medical abbreviations (e.g. 'ADD'
    attention-deficit disorder vs. 'add' adduction are distinct real
    entries, not duplicates)."""
    raw = card.get("q") or card.get("part") or ""
    return " ".join(raw.split())


def dedupe_across_decks(deck_lists):
    """Given [(deck_name, [cards...]), ...], drop cards whose front_key
    collides with one already kept (first occurrence wins, scanning decks
    in the given order). Logs drops to stderr. Returns new deck_lists."""
    seen = {}
    result = []
    for deck_name, cards in deck_lists:
        kept = []
        for card in cards:
            key = front_key(card)
            if key in seen:
                print("WARNING: dropping duplicate front in %r (key=%r); "
                      "already used by %r: %r"
                      % (deck_name, key, seen[key], card),
                      file=sys.stderr)
                continue
            seen[key] = deck_name
            kept.append(card)
        result.append((deck_name, kept))
    return result


def main():
    glossary_path = register_input(GLOSSARY_PATH)
    abbrev_path = register_input(ABBREV_PATH)

    os.makedirs(OUTDIR, exist_ok=True)

    word_part_cards = parse_glossary(glossary_path)

    sections = parse_abbrev_sections(abbrev_path)
    abbrev_entries = build_abbreviation_entries(sections)
    abbrev_cards = merge_abbreviation_entries(abbrev_entries)

    eponym_cards = build_eponym_cards(sections)

    deck_lists = dedupe_across_decks([
        ("word-parts", word_part_cards),
        ("abbreviations", abbrev_cards),
        ("eponyms", eponym_cards),
    ])
    word_part_cards = dict(deck_lists)["word-parts"]
    abbrev_cards = dict(deck_lists)["abbreviations"]
    eponym_cards = dict(deck_lists)["eponyms"]

    build_deck(word_part_cards,
               os.path.join(OUTDIR, "word-parts.txt"),
               tags=COMMON_TAGS + ["word-parts"])
    build_deck(abbrev_cards,
               os.path.join(OUTDIR, "abbreviations.txt"),
               tags=COMMON_TAGS + ["abbreviations"])
    build_deck(eponym_cards,
               os.path.join(OUTDIR, "eponyms.txt"),
               tags=COMMON_TAGS + ["eponyms"])


if __name__ == "__main__":
    main()
