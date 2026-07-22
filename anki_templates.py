"""
Anki Flashcard Template Engine
==============================
Generate styled, dark-mode-friendly HTML flashcards from MINIMAL content input,
for any subject. You pass ~200 chars of content per card; this module emits the
~1,000+ chars of repeated HTML. Cards render in Anki with "HTML enabled" in
dark mode.

USAGE
-----
    from anki_templates import build_deck

    cards = [
        {"type": "definition", "q": "What is *igneous rock*?",
         "a": "Rock formed from cooled, solidified magma or lava.",
         "tags": "geology"},
        {"type": "suffix", "part": "-ology", "a": "the study of",
         "decompose": [("-log-", "word, reason (from Greek *logos*)"), ("-y", "noun-forming suffix")],
         "tags": "etymology"},
    ]
    build_deck(cards, "deck.txt", tags=["sample"])

Tags are required: every card must end up with at least one tag, either
per-card or via the deck-wide `tags=` argument to `build_deck`.

CARD CATEGORIES
---------------
The CATEGORIES dict below is the source of truth for card types (badge label +
accent color); list them with:  python3 anki_templates.py --list-types

The true_false badge is deliberately a neutral slate so the front never hints
at the answer; the back colors itself green (TRUE) or red (FALSE).

Color = family of cognitive task; the badge label + layout disambiguate types
that share a color (purple = word-part assembly/disassembly; teal = rules &
relationships; coral = differentiation & application). Any card may override
with per-card "badge" and "color" keys ("color" accepts a palette name or hex).

INLINE MARKUP
-------------
In any free-text field, wrap a key term in *single asterisks* to render it in
accent-colored italics, e.g. "From *cyt/o* (cell)". (Double quotes ""like this""
work too.) Do NOT use double asterisks (**) — only single.

Every builder's accepted fields are documented in its own docstring.
"""

import os
import re

# ───────────────────────────────────────────────────────────────────────────
# PALETTE & CATEGORIES
# ───────────────────────────────────────────────────────────────────────────
PALETTE = {
    "sky":    "#7ec8e3",
    "coral":  "#f0776c",
    "sage":   "#a8d5a2",
    "gold":   "#e8c170",
    "purple": "#c4a7e7",
    "teal":   "#6ecfcf",
    "pink":   "#e8a0bf",
    "indigo": "#9b8cef",
    "slate":  "#8f9aa6",
    "rose":   "#e0728c",
}

# Verdict colors for true_false cards (fixed semantics: green = true, red = false)
TRUE_COLOR = "#a8d5a2"   # sage green
FALSE_COLOR = "#f0776c"  # coral red

# type key -> (BADGE LABEL, palette color name)
CATEGORIES = {
    "definition":     ("DEFINITION",          "sky"),
    "concept":        ("CONCEPT",             "teal"),
    "compare":        ("COMPARE & CONTRAST",  "coral"),
    "key_list":       ("KEY LIST",            "sage"),
    "argument":       ("ARGUMENT",            "indigo"),
    "position":       ("POSITION",            "gold"),
    "objection":      ("OBJECTION & REPLY",   "rose"),
    "distinction":    ("DISTINCTION",         "purple"),
    "combining_form": ("COMBINING FORM",      "purple"),
    "prefix":         ("PREFIX",              "pink"),
    "suffix":         ("SUFFIX",              "gold"),
    "deconstruction": ("WORD DECONSTRUCTION", "purple"),
    "word_building":  ("BUILD A TERM",        "purple"),
    "word_family":    ("WORD FAMILY",         "teal"),
    "in_context":     ("IN CONTEXT",          "coral"),
    "structure_function": ("STRUCTURE ↔ FUNCTION", "indigo"),
    "true_false":     ("TRUE / FALSE",        "slate"),
    "alias":          ("ALIAS",               "gold"),
}

FONT = "Georgia,serif"
BODY = "#dddddd"   # readable body text
MUTED = "#999999"  # muted notes / pronunciation
BOX = "#2a2a2a"    # dark box / pill background


# ───────────────────────────────────────────────────────────────────────────
# LOW-LEVEL HELPERS
# ───────────────────────────────────────────────────────────────────────────
def _hex(color):
    """Resolve a palette name or hex string to a hex code (default sky)."""
    if not color:
        return PALETTE["sky"]
    color = str(color)
    if color.startswith("#"):
        return color
    return PALETTE.get(color, color)


def _visible_len(text):
    """Length of text ignoring HTML tags and markup punctuation."""
    s = re.sub(r"<[^>]+>", "", str(text))
    s = s.replace("*", "").replace('"', "")
    return len(s)


def _strip_wrapping_quotes(s):
    """Drop one layer of surrounding straight/smart quotes, if present."""
    s = str(s).strip()
    pairs = [('"', '"'), ("'", "'"), ("\u201c", "\u201d"), ("\u2018", "\u2019")]
    for lq, rq in pairs:
        if len(s) >= 2 and s[0] == lq and s[-1] == rq:
            return s[1:-1].strip()
    return s


_STAR = re.compile(r"\*([^*]+)\*")
_DQUOTE = re.compile(r'""([^"]+)""')


def hl(term, accent):
    """Inline accent-colored italic highlight for a key term."""
    return '<i style="color:' + _hex(accent) + '">' + str(term) + "</i>"


def markup(text, accent):
    """Render *term* and ""term"" inside free text as accent italics."""
    if text is None:
        return ""
    a = _hex(accent)
    t = str(text)
    t = _STAR.sub(lambda m: hl(m.group(1), a), t)
    t = _DQUOTE.sub(lambda m: hl(m.group(1), a), t)
    return t


# ───────────────────────────────────────────────────────────────────────────
# STYLING PRIMITIVES  (every builder reuses these)
# ───────────────────────────────────────────────────────────────────────────
def front(badge, accent, question_inner):
    """Front wrapper: Georgia container + accent badge pill + question."""
    a = _hex(accent)
    return (
        '<div style="font-family:' + FONT + ';max-width:560px;margin:0 auto;'
        'line-height:1.6;color:' + BODY + ';font-size:16px">'
        '<span style="display:inline-block;background:' + BOX + ';color:' + a + ';'
        'border:1px solid ' + a + ';border-radius:999px;padding:3px 11px;'
        'font-size:0.7em;font-weight:600;letter-spacing:0.12em;'
        'text-transform:uppercase">' + badge + '</span>'
        '<div style="margin-top:14px;font-size:1.08em">' + question_inner + '</div>'
        '</div>'
    )


def back(inner):
    """Back wrapper: the same Georgia container."""
    return (
        '<div style="font-family:' + FONT + ';max-width:560px;margin:0 auto;'
        'line-height:1.6;color:' + BODY + ';font-size:16px">' + inner + '</div>'
    )


def answer_callout(lead, accent, body=None):
    """Answer in a callout box (dark bg, 3px accent left border, rounded).
    Short lead (<=55 visible chars) -> modest accent heading (600, ~1.05em);
    long lead -> readable #ddd body (~0.95em). Optional secondary body line."""
    a = _hex(accent)
    lead = _strip_wrapping_quotes(lead)
    if _visible_len(lead) <= 55:
        lead_html = (
            '<div style="color:' + a + ';font-weight:600;font-size:1.05em">'
            + markup(lead, a) + '</div>'
        )
    else:
        lead_html = (
            '<div style="color:' + BODY + ';font-size:0.95em">'
            + markup(lead, a) + '</div>'
        )
    parts = [lead_html]
    if body:
        parts.append(
            '<div style="color:' + BODY + ';font-size:0.95em;margin-top:8px">'
            + markup(body, a) + '</div>'
        )
    return (
        '<div style="background:' + BOX + ';border-left:3px solid ' + a + ';'
        'border-radius:6px;padding:12px 14px;margin:10px 0">'
        + "".join(parts) + '</div>'
    )


_NOTE_WORDS = ("remember", "note", "hint", "tip", "nb", "caution")
_ARROW_RE = re.compile(r"\s*\u2192\s*")           # → with optional spaces
_DASH_SPLITS = [" \u2014 ", " \u2013 ", " - ", ": "]  # em-, en-, hyphen, colon


def _is_note_word(item):
    low = str(item).strip().lower()
    for w in _NOTE_WORDS:
        if low == w or low.startswith(w + ":") or low.startswith(w + " "):
            return True
    return False


def _bold_leading(item, accent):
    """Bold the leading term of an example/list item in the accent color.
    Splits on the first arrow (re-emitted as ' → ') or a spaced dash/colon;
    otherwise bolds the first word."""
    a = _hex(accent)
    item = str(item)
    m = _ARROW_RE.search(item)
    if m:
        head = item[:m.start()].strip()
        rest = item[m.end():].strip()
        return ('<b style="color:' + a + '">' + markup(head, a) + '</b> \u2192 '
                + markup(rest, a))
    for sep in _DASH_SPLITS:
        if sep in item:
            head, rest = item.split(sep, 1)
            return ('<b style="color:' + a + '">' + markup(head.strip(), a)
                    + '</b>' + sep + markup(rest.strip(), a))
    bits = item.split(" ", 1)
    if len(bits) == 2:
        return ('<b style="color:' + a + '">' + markup(bits[0], a) + '</b> '
                + markup(bits[1], a))
    return '<b style="color:' + a + '">' + markup(item, a) + '</b>'


def example_box(ex, accent):
    """Example callout. List -> single-spaced bullets with bolded leading term,
    one <br> between items (never double). String -> plain prose, no bullet.
    Note-word asides (Remember/Note/Hint...) stay plain, not bulleted.
    Label EXAMPLE/EXAMPLES auto-pluralized."""
    a = _hex(accent)
    if isinstance(ex, (list, tuple)):
        rows = []
        n_examples = 0
        for it in ex:
            if _is_note_word(it):
                rows.append('<span style="color:' + BODY + ';font-style:italic">'
                            + markup(it, a) + '</span>')
            else:
                n_examples += 1
                rows.append('<span style="color:' + a + '">\u2022</span> '
                            + _bold_leading(it, a))
        inner = "<br>".join(rows)
        label = "EXAMPLES" if n_examples != 1 else "EXAMPLE"
    else:
        inner = '<span style="color:' + BODY + '">' + markup(ex, a) + '</span>'
        label = "EXAMPLE"
    return (
        '<div style="background:' + a + '14;border-left:3px solid ' + a + '40;'
        'border-radius:6px;padding:10px 12px;margin:10px 0">'
        '<div style="color:' + a + ';font-size:0.7em;font-weight:600;'
        'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px">'
        + label + '</div>' + inner + '</div>'
    )


def compare_cards(items, accent):
    """Each (label, desc) -> its own mini box: bold accent label, #ddd desc."""
    a = _hex(accent)
    out = []
    for label, desc in items:
        out.append(
            '<div style="background:' + BOX + ';border-left:3px solid ' + a + ';'
            'border-radius:6px;padding:10px 12px;margin:8px 0">'
            '<div style="color:' + a + ';font-weight:600">'
            + markup(label, a) + '</div>'
            '<div style="color:' + BODY + ';font-size:0.95em;margin-top:3px">'
            + markup(desc, a) + '</div></div>'
        )
    return "".join(out)


def list_box(items, accent, ordered=False):
    """Callout box of items. Markers (• or 1.) in accent. Tuple items ->
    bold label + ' — ' + #ddd desc; string items via leading-term bold."""
    a = _hex(accent)
    rows = []
    for i, it in enumerate(items, 1):
        marker = (str(i) + ".") if ordered else "\u2022"
        marker_html = ('<span style="color:' + a + ';font-weight:700">'
                       + marker + '</span> ')
        if isinstance(it, (list, tuple)) and len(it) == 2:
            label, desc = it
            rows.append(marker_html + '<b style="color:' + a + '">'
                        + markup(label, a) + '</b> \u2014 ' + markup(desc, a))
        else:
            rows.append(marker_html + _bold_leading(it, a))
    return (
        '<div style="background:' + BOX + ';border-left:3px solid ' + a + ';'
        'border-radius:6px;padding:12px 14px;margin:10px 0">'
        + "<br>".join(rows) + '</div>'
    )


def section_label(text, accent):
    """Small uppercase accent subheading with a subtle bottom rule."""
    a = _hex(accent)
    return (
        '<div style="color:' + a + ';font-size:0.72em;font-weight:600;'
        'letter-spacing:0.1em;text-transform:uppercase;'
        'border-bottom:1px solid ' + a + '40;margin:14px 0 6px;'
        'padding-bottom:3px">' + text + '</div>'
    )


def callout(inner, accent):
    """Generic callout box (dark bg, 3px accent left border, rounded)."""
    a = _hex(accent)
    return (
        '<div style="background:' + BOX + ';border-left:3px solid ' + a + ';'
        'border-radius:6px;padding:12px 14px;margin:10px 0">' + inner + '</div>'
    )


def muted_note(text, accent=MUTED):
    """Small muted (#999999) italic footnote; *markup* uses the card accent."""
    return (
        '<div style="color:' + MUTED + ';font-style:italic;font-size:0.9em;'
        'margin-top:8px">' + markup(text, accent) + '</div>'
    )


def pron_line(p):
    """Pronunciation line (muted italic)."""
    return ('<div style="color:' + MUTED + ';font-style:italic;font-size:0.85em;'
            'margin-top:2px">' + str(p) + '</div>')


def _breakdown(parts, accent):
    """Word-part family: a chip row (token + token + ...) plus a bulleted
    'token — meaning' mapping, inside one callout box."""
    a = _hex(accent)
    chips = []
    for token, _meaning in parts:
        chips.append(
            '<span style="display:inline-block;background:' + BOX + ';color:'
            + a + ';border:1px solid ' + a + '40;border-radius:4px;'
            'padding:2px 8px;font-weight:600">' + str(token) + '</span>'
        )
    chip_row = ('<span style="color:' + a + '"> + </span>').join(chips)
    maps = []
    for token, meaning in parts:
        row = ('<span style="color:' + a + ';font-weight:700">\u2022</span> '
               '<b style="color:' + a + '">' + str(token) + '</b>')
        if meaning:
            row += (' \u2014 <span style="color:' + BODY + '">'
                    + markup(meaning, a) + '</span>')
        maps.append(row)
    return (
        '<div style="background:' + BOX + ';border-left:3px solid ' + a + ';'
        'border-radius:6px;padding:12px 14px;margin:10px 0">'
        '<div style="margin-bottom:8px">' + chip_row + '</div>'
        + "<br>".join(maps) + '</div>'
    )


def _related_line(related, accent):
    """A 'Related' section: comma-joined accent terms."""
    a = _hex(accent)
    if isinstance(related, (list, tuple)):
        body = ", ".join(markup(r, a) for r in related)
    else:
        body = markup(related, a)
    return (section_label("Related", a)
            + '<div style="color:' + BODY + ';font-size:0.95em">' + body + '</div>')


_ABBR = {"u.s.", "e.g.", "i.e.", "etc.", "vs.", "dr.", "mr.", "mrs.", "ms.",
         "fig.", "no.", "cf.", "al.", "st.", "approx.", "inc.", "ph.d.",
         "pl.", "sing.", "sp.", "spp."}


def split_sentence_lead(text):
    """Split off the first sentence as a lead, protecting common abbreviations
    and single-letter initials. Returns (lead, remainder)."""
    s = str(text).strip()
    n = len(s)
    i = 0
    while i < n:
        if s[i] in ".!?":
            k = i - 1
            while k >= 0 and s[k] not in " \t":
                k -= 1
            token = s[k + 1:i + 1].lower()
            prev_word = s[k + 1:i]
            is_initial = len(prev_word) == 1 and prev_word.isalpha()
            next_is_break = (i + 1 >= n) or (s[i + 1] in " \t")
            inside_markup = s[:i + 1].count("*") % 2 == 1
            inside_parens = s[:i + 1].count("(") > s[:i + 1].count(")")
            if (token in _ABBR or is_initial or not next_is_break
                    or inside_markup or inside_parens):
                i += 1
                continue
            return s[:i + 1].strip(), s[i + 1:].strip()
        i += 1
    return s, ""


def _lead_body(d, lead_key="a", body_key="detail"):
    """Resolve (lead, body): if no explicit body and the answer is long,
    split off the first sentence as the lead."""
    lead = d.get(lead_key, "")
    body = d.get(body_key)
    if body is None and lead and _visible_len(lead) > 55:
        first, rest = split_sentence_lead(lead)
        if rest:
            return first, rest
    return lead, body


# ───────────────────────────────────────────────────────────────────────────
# CARD BUILDERS  (each returns (front_html, back_html))
# ───────────────────────────────────────────────────────────────────────────
def _accent(d, category):
    return _hex(d.get("color", CATEGORIES[category][1]))


def _badge(d, category):
    return d.get("badge", CATEGORIES[category][0])


def card_definition(d):
    """Fields: q, a, detail?, ex?, note?  |  badge?, color? override."""
    a = _accent(d, "definition")
    fr = front(_badge(d, "definition"), a, markup(d["q"], a))
    lead, body = _lead_body(d)
    parts = [answer_callout(lead, a, body)]
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_concept(d):
    """Fields: q, a, detail?, ex?, note?  |  badge?, color? override."""
    a = _accent(d, "concept")
    fr = front(_badge(d, "concept"), a, markup(d["q"], a))
    lead, body = _lead_body(d)
    parts = [answer_callout(lead, a, body)]
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_compare(d):
    """Fields: q; then ONE of —
      items[(label, desc)...]  -> each its own mini-box (side-by-side contrast)
      a (free text) + points[str...]?  -> a lead callout plus an optional
                                          bulleted list (prose-style comparison)
    plus optional ex?, note?  |  badge?, color?."""
    a = _accent(d, "compare")
    fr = front(_badge(d, "compare"), a, markup(d["q"], a))
    parts = []
    items = d.get("items")
    if items and all(isinstance(it, (list, tuple)) and len(it) == 2 for it in items):
        parts.append(compare_cards(items, a))
    else:
        if d.get("a"):
            lead, body = _lead_body(d)
            parts.append(answer_callout(lead, a, body))
        pts = d.get("points") or items
        if pts:
            parts.append(list_box(pts, a))
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_key_list(d):
    """Fields: q, items[(label, desc) | str ...], a? (lead before the list),
    ordered?, ex?, note?  |  badge?, color?."""
    a = _accent(d, "key_list")
    fr = front(_badge(d, "key_list"), a, markup(d["q"], a))
    parts = []
    if d.get("a"):
        parts.append(answer_callout(d["a"], a))
    parts.append(list_box(d["items"], a, ordered=d.get("ordered", False)))
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_word_part(d, _category="combining_form"):
    """Word-part card (serves combining_form / prefix / suffix).
    Fields: part (or term), a (meaning), q?, detail?, decompose?[(tok,mean)...],
    pron?, ex?, related?, note?  |  badge?, color? override.
    'decompose' splits a compound element into root + base parts
    (e.g. -emia -> -em- 'blood' + -ia 'condition')."""
    a = _accent(d, _category)
    badge = _badge(d, _category)
    part = d.get("part") or d.get("term") or ""
    if d.get("q"):
        q_inner = markup(d["q"], a)
    else:
        q_inner = ('<span style="color:' + a + ';font-weight:600;font-size:1.1em">'
                   + str(part) + '</span><br>What does this '
                   + CATEGORIES[_category][0].lower() + ' mean?')
    fr = front(badge, a, q_inner)
    parts = [answer_callout(d["a"], a, d.get("detail"))]
    if d.get("pron"):
        parts.append(pron_line(d["pron"]))
    if d.get("decompose"):
        parts.append(_breakdown(d["decompose"], a))
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("related"):
        parts.append(_related_line(d["related"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_combining_form(d):
    return card_word_part(d, "combining_form")


def card_prefix(d):
    return card_word_part(d, "prefix")


def card_suffix(d):
    return card_word_part(d, "suffix")


def card_deconstruction(d):
    """Fields: term, parts[(token, meaning)...], a? (overall meaning), q?,
    pron?, ex?, note?  |  badge?, color?."""
    a = _accent(d, "deconstruction")
    badge = _badge(d, "deconstruction")
    term = d.get("term", "")
    if d.get("q"):
        q_inner = markup(d["q"], a)
    else:
        q_inner = ('Break down the term:<br>'
                   '<span style="color:' + a + ';font-weight:600;font-size:1.1em">'
                   + str(term) + '</span>')
    fr = front(badge, a, q_inner)
    parts = []
    if d.get("a"):
        parts.append(answer_callout(d["a"], a))
    parts.append(_breakdown(d["parts"], a))
    if d.get("pron"):
        parts.append(pron_line(d["pron"]))
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_word_building(d):
    """Fields: clue, term, parts?[(token, meaning)...], pron?, note?
    |  badge?, color?."""
    a = _accent(d, "word_building")
    badge = _badge(d, "word_building")
    q_inner = ('Build a term meaning:<br>'
               '<span style="font-weight:600">' + markup(d["clue"], a) + '</span>')
    fr = front(badge, a, q_inner)
    parts = [answer_callout(d["term"], a)]
    if d.get("pron"):
        parts.append(pron_line(d["pron"]))
    if d.get("parts"):
        parts.append(_breakdown(d["parts"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_word_family(d):
    """Fields: root, members[(term, meaning) | str ...], q?, note?
    |  badge?, color?."""
    a = _accent(d, "word_family")
    badge = _badge(d, "word_family")
    root = d.get("root", "")
    if d.get("q"):
        q_inner = markup(d["q"], a)
    else:
        q_inner = ('Word family for:<br>'
                   '<span style="color:' + a + ';font-weight:600;font-size:1.1em">'
                   + str(root) + '</span>')
    fr = front(badge, a, q_inner)
    parts = [list_box(d["members"], a)]
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_in_context(d):
    """Fields: q, a (interpretation), detail?, excerpt? (excerpt text),
    related?, ex?, note?  |  badge?, color?."""
    a = _accent(d, "in_context")
    badge = _badge(d, "in_context")
    fr = front(badge, a, markup(d["q"], a))
    parts = []
    if d.get("excerpt"):
        parts.append(
            section_label("Excerpt", a)
            + '<div style="background:' + BOX + ';border-left:3px solid ' + a + '40;'
            'border-radius:6px;padding:10px 12px;margin:6px 0;color:' + BODY + ';'
            'font-style:italic;font-size:0.95em">' + markup(d["excerpt"], a) + '</div>'
        )
    lead, body = _lead_body(d)
    parts.append(answer_callout(lead, a, body))
    if d.get("related"):
        parts.append(_related_line(d["related"], a))
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


# ───────────────────────────────────────────────────────────────────────────
# DISPATCHER & DECK WRITER
# ───────────────────────────────────────────────────────────────────────────
def card_structure_function(d):
    """Fields: q, a, detail?, ex?, note?  |  badge?, color? override.
    Pairs an anatomical structure with what it does / how it works."""
    a = _accent(d, "structure_function")
    fr = front(_badge(d, "structure_function"), a, markup(d["q"], a))
    lead, body = _lead_body(d)
    parts = [answer_callout(lead, a, body)]
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_true_false(d):
    """A trick-resistant true/false card.

    Fields:
      q        the statement to judge (shown alone on the front).
      verdict  True or False  (bool, or the string 'true'/'false').
               'answer' is accepted as an alias.
      a        the explanation — focus on WHY the other answer is wrong / the
               subtlety being tested. 'explain' is accepted as an alias.
      detail?, ex?, note?  optional, as in other builders.
      badge?, color?       override the FRONT badge only.

    The front uses a neutral slate badge so it never hints at the answer. The
    back leads with a TRUE (green) or FALSE (red) verdict banner, then a 'Why'
    explanation colored to match the verdict. Verdict colors are fixed; the
    per-card 'color' override only affects the front badge."""
    if "verdict" not in d and "answer" not in d:
        raise ValueError("true_false card requires a 'verdict' (True/False)")

    front_accent = _accent(d, "true_false")
    fr = front(_badge(d, "true_false"), front_accent, markup(d["q"], front_accent))

    raw = d.get("verdict", d.get("answer"))
    if isinstance(raw, str):
        is_true = raw.strip().lower() in ("true", "t", "yes", "y", "1")
    else:
        is_true = bool(raw)
    vc = TRUE_COLOR if is_true else FALSE_COLOR
    label = "TRUE" if is_true else "FALSE"

    banner = (
        '<div style="background:' + BOX + ';border-left:3px solid ' + vc + ';'
        'border-radius:6px;padding:10px 14px;margin:10px 0">'
        '<span style="color:' + vc + ';font-weight:700;font-size:1.2em;'
        'letter-spacing:0.08em">' + label + '</span></div>'
    )
    parts = [banner]

    src = d if "a" in d else ({**d, "a": d["explain"]} if d.get("explain") else d)
    lead, body = _lead_body(src)
    if lead:
        parts.append(section_label("Why", vc))
        parts.append(answer_callout(lead, vc, body))
    if d.get("ex"):
        parts.append(example_box(d["ex"], vc))
    if d.get("note"):
        parts.append(muted_note(d["note"], vc))
    return fr, back("".join(parts))


def card_alias(d):
    """Two names for one thing (generic/brand, common/scientific, symbol/name).
    Fields: q (the name shown + which name is wanted), a (the answer name),
    detail?, ex?, note? (extra context)  |  badge?, color? override.
    Behaves like a definition card but carries the ALIAS badge (gold)."""
    a = _accent(d, "alias")
    fr = front(_badge(d, "alias"), a, markup(d["q"], a))
    lead, body = _lead_body(d)
    parts = [answer_callout(lead, a, body)]
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


# ── PHILOSOPHY / ETHICS BUILDERS ───────────────────────────────────────────
def card_argument(d):
    """Reconstruct an argument as numbered premises leading to a conclusion.
    Fields: q (prompt), premises[str | (label, text) ...], conclusion,
    ex?, note?  |  badge?, color? override.
    Premises render as an accent-numbered list; the conclusion sits in its own
    box prefixed with the 'therefore' sign (∴). Use (label, text) tuples to
    supply custom premise labels like '(1)' or 'P1'."""
    a = _accent(d, "argument")
    fr = front(_badge(d, "argument"), a, markup(d["q"], a))
    rows = []
    for i, p in enumerate(d["premises"], 1):
        if isinstance(p, (list, tuple)) and len(p) == 2:
            label, text = p
            rows.append('<span style="color:' + a + ';font-weight:700">'
                        + str(label) + '</span> '
                        '<span style="color:' + BODY + '">' + markup(text, a)
                        + '</span>')
        else:
            rows.append('<span style="color:' + a + ';font-weight:700">'
                        + str(i) + '.</span> '
                        '<span style="color:' + BODY + '">' + markup(p, a)
                        + '</span>')
    parts = [section_label("Premises", a), callout("<br>".join(rows), a)]
    parts.append(section_label("Conclusion", a))
    parts.append(callout(
        '<span style="color:' + a + ';font-weight:700;font-size:1.15em">'
        '∴ </span><span style="color:' + a + ';font-weight:600">'
        + markup(d["conclusion"], a) + '</span>', a))
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_position(d):
    """Attribute a view to a named thinker, with optional grounds.
    Fields: thinker, topic? (or q? override for the front), a (the view),
    detail? (grounds/reasoning), ex?, note?  |  badge?, color? override.
    Reads like a concept card but is tagged with a 'who' and closes with a
    right-aligned attribution line."""
    a = _accent(d, "position")
    badge = _badge(d, "position")
    thinker = d.get("thinker", "")
    if d.get("q"):
        q_inner = markup(d["q"], a)
    else:
        who = '<b style="color:' + a + '">' + str(thinker) + '</b>'
        topic = d.get("topic")
        if topic:
            q_inner = "What is " + who + "'s position on " + markup(topic, a) + "?"
        else:
            q_inner = "What is " + who + "'s position?"
    fr = front(badge, a, q_inner)
    lead, body = _lead_body(d)
    parts = [answer_callout(lead, a, body)]
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if thinker:
        parts.append('<div style="text-align:right;color:' + MUTED
                     + ';font-style:italic;font-size:0.85em;margin-top:6px">'
                     '— ' + str(thinker) + '</div>')
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_objection(d):
    """A claim, the objection raised against it, and the reply (dialectic).
    Fields: claim (or q? override for the front), objection, reply?, ex?, note?
    |  badge?, color? override.
    The objection renders in the card accent (tension); the reply in sage
    (green) to mark resolution. If you pass a custom q AND a claim, the claim
    is also restated in a box on the back."""
    a = _accent(d, "objection")
    badge = _badge(d, "objection")
    if d.get("q"):
        q_inner = markup(d["q"], a)
    else:
        claim = d.get("claim", "")
        q_inner = ('Consider the claim:<br>'
                   '<i style="color:' + a + '">' + markup(claim, a) + '</i><br>'
                   'What objection arises, and how might it be answered?')
    fr = front(badge, a, q_inner)
    parts = []
    if d.get("q") and d.get("claim"):
        parts.append(section_label("Claim", a))
        parts.append(callout('<span style="color:' + BODY + '">'
                             + markup(d["claim"], a) + '</span>', a))
    parts.append(section_label("Objection", a))
    parts.append(callout('<span style="color:' + BODY + '">'
                         + markup(d["objection"], a) + '</span>', a))
    if d.get("reply"):
        g = PALETTE["sage"]
        parts.append(section_label("Reply", g))
        parts.append(callout('<span style="color:' + BODY + '">'
                             + markup(d["reply"], g) + '</span>', g))
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_distinction(d):
    """Pin down the criterion separating two (or more) confused concepts.
    Fields: between (TermA, TermB) for an auto front, or q? override;
    criterion? (the dividing line, shown as the lead); items[(label, desc)...]
    (one mini-box per side); ex?, note?  |  badge?, color? override.
    Differs from 'compare' by foregrounding the single dividing criterion."""
    a = _accent(d, "distinction")
    badge = _badge(d, "distinction")
    if d.get("q"):
        q_inner = markup(d["q"], a)
    elif d.get("between"):
        joined = ('</b> vs <b style="color:' + a + '">').join(
            str(t) for t in d["between"])
        q_inner = 'Distinguish <b style="color:' + a + '">' + joined + '</b>.'
    else:
        q_inner = markup(d.get("a", ""), a)
    fr = front(badge, a, q_inner)
    parts = []
    if d.get("criterion"):
        parts.append(section_label("Dividing line", a))
        parts.append(answer_callout(d["criterion"], a))
    if d.get("items"):
        parts.append(compare_cards(d["items"], a))
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


_BUILDERS = {
    "definition":     card_definition,
    "structure_function": card_structure_function,
    "concept":        card_concept,
    "compare":        card_compare,
    "key_list":       card_key_list,
    "argument":       card_argument,
    "position":       card_position,
    "objection":      card_objection,
    "distinction":    card_distinction,
    "combining_form": card_combining_form,
    "prefix":         card_prefix,
    "suffix":         card_suffix,
    "deconstruction": card_deconstruction,
    "word_building":  card_word_building,
    "word_family":    card_word_family,
    "in_context":     card_in_context,
    "true_false":     card_true_false,
    "alias":          card_alias,
}


def build_card(card):
    """Route a card dict to its builder on the 'type' key. Returns (front, back)."""
    t = card.get("type")
    if t not in _BUILDERS:
        raise ValueError("Unknown card type %r. Valid types: %s"
                         % (t, ", ".join(sorted(_BUILDERS))))
    return _BUILDERS[t](card)


def _oneline(s):
    """Flatten a field to a single line and drop any trailing semicolon."""
    s = str(s).replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()
    if s.endswith(";"):
        s = s[:-1]
    return s


def _normalize_tags(value):
    """Normalize a tags value (list of strings, or a single space-separated
    string) into a list of strings. Raises ValueError if any tag has
    internal whitespace."""
    if value is None:
        return []
    if isinstance(value, str):
        raw = value.split()
    else:
        raw = list(value)
    out = []
    for t in raw:
        t = str(t)
        if any(c.isspace() for c in t):
            raise ValueError("tag %r contains whitespace" % t)
        out.append(t.lower())
    return out


def _merge_tags(deck_tags, card_tags):
    """Merge deck-wide tags (first) with per-card tags, deduping while
    preserving first-seen order."""
    merged = []
    seen = set()
    for t in deck_tags + card_tags:
        if t not in seen:
            seen.add(t)
            merged.append(t)
    return merged


def build_deck(cards, output_path, tags=None):
    """Write an Anki tab-separated import file.

    Parameters
    ----------
    cards : list[dict]   each has a 'type' key plus that type's fields, and
                          may have an optional 'tags' key (list of strings,
                          or a single space-separated string).
    output_path : str    path for the .txt import file.
    tags : list[str] | str, optional
                          deck-wide tags applied to every card, merged with
                          any per-card tags.

    Every card must end up with at least one tag (deck-wide and/or
    per-card); tags may not contain whitespace and are lowercased.
    """
    deck_tags = _normalize_tags(tags)
    lines = ["#separator:tab", "#html:true", "#tags column:3"]
    for card in cards:
        fr, bk = build_card(card)
        card_tags = _normalize_tags(card.get("tags"))
        merged = _merge_tags(deck_tags, card_tags)
        if not merged:
            raise ValueError("card of type %r has no tags (deck-wide or "
                             "per-card tags required)" % card.get("type"))
        lines.append(_oneline(fr) + "\t" + _oneline(bk) + "\t" + " ".join(merged))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Generated %d cards -> %s" % (len(cards), output_path))
    return output_path


def register_input(path):
    """Declare a source file the driver reads. Prints the ``Input: <abspath>``
    contract line run.sh uses to archive consumed inputs after a fully
    successful gen run, and returns the absolute path for the driver to open."""
    abspath = os.path.abspath(path)
    if os.path.isfile(abspath):
        print("Input: %s" % abspath)
        return abspath
    repo_root = os.path.dirname(os.path.abspath(__file__))
    archive_root = os.path.join(repo_root, "input", "archive")
    basename = os.path.basename(abspath)
    if os.path.isdir(archive_root):
        for dirpath, dirnames, filenames in os.walk(archive_root):
            dirnames.sort()  # deterministic first match
            if basename in filenames:
                archived = os.path.relpath(os.path.join(dirpath, basename), repo_root)
                raise FileNotFoundError(
                    "input file %r was already used to generate a batch and "
                    "moved to %s; move it back to input/ to regenerate."
                    % (basename, archived))
    raise FileNotFoundError("input file not found: %s" % abspath)


# ───────────────────────────────────────────────────────────────────────────
# SAMPLE DECK + SELF-CHECKS  (run:  python3 anki_templates.py [out.txt])
# ───────────────────────────────────────────────────────────────────────────
SAMPLE_CARDS = [
    {"type": "definition",
     "q": "What is *igneous rock*?",
     "a": "Rock formed by the cooling and solidification of magma or lava.",
     "detail": "Classified as *intrusive* (cooled slowly underground, "
               "coarse-grained, e.g. granite) or *extrusive* (cooled quickly "
               "at the surface, fine-grained, e.g. basalt).",
     "ex": "Obsidian is extrusive igneous rock that cooled so fast it formed "
           "volcanic glass instead of crystals.",
     "tags": "geology"},

    {"type": "combining_form",
     "part": "chron/o",
     "a": "time",
     "pron": "/KRON-oh/",
     "ex": [
         "chron/o + -logy → chronology (the study or record of events in time)",
         "syn- + chron/o + -ous → synchronous (happening at the same time)",
     ],
     "related": ["chronic", "anachronism"],
     "tags": "etymology"},

    {"type": "concept",
     "q": "How do you find the relative minor of a major key?",
     "a": "Count down three semitones (a minor third) from the major key's "
          "tonic; that note is the tonic of its relative minor.",
     "ex": "C major's relative minor is A minor — both share the same "
           "key signature (no sharps or flats).",
     "tags": "music-theory"},

    {"type": "prefix",
     "part": "sub-",
     "a": "under, below",
     "ex": [
         "sub- + marine → submarine (under the sea)",
         "sub- + terranean → subterranean (underground)",
     ],
     "note": "Contrast with *super-* (above, over).",
     "tags": "etymology"},

    {"type": "compare",
     "q": "Distinguish *ionic* and *covalent* bonds.",
     "items": [
         ("Ionic bond", "electrons are *transferred* from one atom to "
                        "another, creating oppositely charged ions that "
                        "attract (e.g. NaCl)."),
         ("Covalent bond", "electrons are *shared* between atoms (e.g. H2O)."),
     ],
     "note": "Ionic bonds typically form between a metal and a nonmetal; "
             "covalent bonds typically form between two nonmetals.",
     "tags": "chemistry"},

    {"type": "suffix",
     "part": "-ology",
     "a": "the study of",
     "decompose": [("-log-", "word, reason (from Greek *logos*)"),
                   ("-y", "noun-forming suffix")],
     "ex": [
         "geo + -ology → geology (the study of the earth)",
         "bi/o + -ology → biology (the study of life)",
     ],
     "tags": "etymology"},

    {"type": "key_list",
     "q": "What are the five French mother sauces?",
     "items": [
         ("Béchamel", "a white sauce made from a butter-and-flour roux plus milk."),
         ("Velouté", "a light stock-based sauce thickened with a roux."),
         ("Espagnole", "a brown sauce built on a dark roux and beef stock."),
         ("Tomato", "a sauce built from tomatoes, aromatics, and stock."),
         ("Hollandaise", "an emulsion of egg yolk and butter, acidified with lemon or vinegar."),
     ],
     "note": "Codified by chef Auguste Escoffier; nearly every classical "
             "French sauce derives from one of the five.",
     "tags": "cooking"},

    {"type": "deconstruction",
     "term": "photograph",
     "a": "An image recorded by the action of light.",
     "parts": [
         ("phot/o", "light"),
         ("-graph", "something written or recorded"),
     ],
     "pron": "/FOH-toh-graf/",
     "tags": "etymology"},

    {"type": "argument",
     "q": "Reconstruct the classic syllogism establishing Socrates is mortal.",
     "premises": ["All men are mortal.", "Socrates is a man."],
     "conclusion": "Socrates is mortal.",
     "note": "A valid deductive form: if both premises are true, the "
             "conclusion must be true.",
     "tags": "logic law"},

    {"type": "word_building",
     "clue": "the study of life",
     "term": "biology",
     "parts": [("bi/o", "life"), ("-logy", "study of")],
     "tags": "etymology"},

    {"type": "position",
     "thinker": "Nicolaus Copernicus",
     "topic": "the structure of the solar system",
     "a": "The Sun, not the Earth, sits at the center, with the planets "
          "— including Earth — orbiting it.",
     "detail": "Published in *De revolutionibus orbium coelestium* (1543), "
               "overturning the geocentric model that had dominated since Ptolemy.",
     "tags": "astronomy"},

    {"type": "word_family",
     "root": "phon/o",
     "members": [
         ("telephone", "a device for transmitting sound across distance"),
         ("symphony", "a sounding-together; a large-scale orchestral work"),
         ("phonetics", "the study of speech sounds"),
         ("megaphone", "a device that amplifies (makes 'large') the voice"),
     ],
     "tags": "etymology"},

    {"type": "objection",
     "claim": "A contract requires nothing more than an offer and an "
              "acceptance to be enforceable.",
     "objection": "Without *consideration* — something of value "
                  "exchanged by each party — a promise is generally not "
                  "legally binding.",
     "reply": "Courts will enforce a bare promise only under narrow "
              "exceptions, such as promissory estoppel, where one party "
              "reasonably relied on it to their detriment.",
     "tags": "law"},

    {"type": "in_context",
     "q": "A commit message says a function was made *idempotent*. What does "
          "that mean, and why would a commit call it out?",
     "excerpt": "fix: make retry handler idempotent so repeated webhook "
                "deliveries don't double-charge",
     "a": "An idempotent operation produces the same result no matter how "
          "many times it's applied.",
     "detail": "Callouts like this matter because webhooks, network "
               "retries, and at-least-once delivery systems can invoke a "
               "handler more than once for the same event.",
     "tags": "programming"},

    {"type": "structure_function",
     "q": "Describe a *flying buttress* and what it does.",
     "a": "An arched, external stone support that channels the outward "
          "thrust of a high vaulted ceiling down and away from the walls to "
          "a pier planted in the ground.",
     "ex": "Flying buttresses let Gothic cathedrals like Notre-Dame de Paris "
           "carry taller walls with thinner stone and far larger windows "
           "than earlier Romanesque buildings allowed.",
     "tags": "architecture"},

    {"type": "distinction",
     "between": ("affect", "effect"),
     "criterion": "Word class is the dividing line: *affect* is (almost "
                  "always) the verb, *effect* is (almost always) the noun.",
     "items": [
         ("affect", "verb — to influence something (e.g. 'the noise "
                    "affected his focus')."),
         ("effect", "noun — a result (e.g. 'the noise had no effect')."),
     ],
     "note": "Rare exceptions exist ('effect' as a verb meaning to bring "
             "about; 'affect' as a noun in psychology), but the verb/noun "
             "split covers nearly all everyday use.",
     "tags": "linguistics"},

    {"type": "true_false",
     "q": "A solution with a pH of 3 is more acidic than a solution with a pH of 5.",
     "verdict": True,
     "a": "The pH scale is logarithmic and runs opposite acidity's "
          "magnitude: lower pH means a higher concentration of H+ ions, "
          "i.e. more acidic. A pH of 3 is ten times more acidic than a pH "
          "of 4, and 100 times more acidic than a pH of 5.",
     "tags": "chemistry"},

    {"type": "alias",
     "q": "What is the common name for the star *Alpha Ursae Minoris*?",
     "a": "Polaris (the North Star).",
     "detail": "It sits almost exactly above Earth's rotational axis, so it "
               "appears nearly motionless in the night sky while other "
               "stars wheel around it.",
     "tags": "astronomy"},
]


def validate_deck(path, expected_cards=None):
    """Validate a generated deck file. Returns a list of problems (empty = pass).
    expected_cards: optional card count to assert (used by the sample path)."""
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")
    body = [l for l in lines if l and not l.startswith("#")]
    fails = []

    if lines[0] != "#separator:tab":
        fails.append("first line is not '#separator:tab'")
    if lines[1] != "#html:true":
        fails.append("second line is not '#html:true'")
    if len(lines) < 3 or lines[2] != "#tags column:3":
        fails.append("third line is not '#tags column:3'")

    if expected_cards is not None and len(body) != expected_cards:
        fails.append("expected %d card lines, got %d" % (expected_cards, len(body)))

    # front/back text scanned by the regex checks below (tags column excluded)
    fb_chunks = []

    for i, l in enumerate(body, 1):
        if l.count("\t") != 2:
            fails.append("card %d has %d tabs (expected exactly 2)" % (i, l.count("\t")))
            continue
        fr, bk, tags_field = l.split("\t")
        fb_chunks.append(fr)
        fb_chunks.append(bk)
        if not tags_field:
            fails.append("card %d has an empty tags field" % i)
        else:
            if "  " in tags_field:
                fails.append("card %d tags field has a double space" % i)
            if tags_field != tags_field.strip():
                fails.append("card %d tags field has leading/trailing space" % i)
        if "border-left:3px solid" not in bk:
            fails.append("card %d back is not inside a callout box" % i)

    fb_text = "\n".join(fb_chunks)

    for l in fb_chunks:
        if l.endswith(";"):
            fails.append("a front/back field ends with a semicolon")

    if "<br><br>" in fb_text:
        fails.append("found a double <br><br>")

    for tok in re.findall(r"#([0-9a-fA-F]+)", fb_text):
        if len(tok) not in (6, 8):
            fails.append("hex #%s has length %d (expected 6 or 8)" % (tok, len(tok)))

    for tag in ("div", "span", "i", "b"):
        opens = len(re.findall(r"<" + tag + r"(?:\s|>)", fb_text))
        closes = len(re.findall(r"</" + tag + r">", fb_text))
        if opens != closes:
            fails.append("unbalanced <%s>: %d open vs %d close" % (tag, opens, closes))

    return fails


# Backwards-compatible alias (pre-CLI name).
_self_check = validate_deck


def _run_sample(out):
    """Build the sample deck and self-check it. Returns an exit code."""
    import sys
    build_deck(SAMPLE_CARDS, out, tags=["sample"])
    problems = validate_deck(out, expected_cards=len(SAMPLE_CARDS))
    if problems:
        print("SELF-CHECK FAILED:")
        for p in problems:
            print("  -", p)
        return 1
    print("Self-checks passed: %d categories, tab-separated, headers OK, "
          "no trailing ';', no <br><br>, hex 6/8 only, balanced tags, "
          "every answer boxed." % len(SAMPLE_CARDS))
    return 0


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Anki template engine: build the sample deck, "
                    "validate a deck file, or list card types.")
    parser.add_argument("output", nargs="?", default="sample_deck.txt",
                        help="output path for the sample deck (default: %(default)s)")
    parser.add_argument("--validate", metavar="PATH",
                        help="validate an existing deck file and exit")
    parser.add_argument("--list-types", action="store_true",
                        help="print the available card types, one per line")
    args = parser.parse_args()

    if args.list_types:
        for key in CATEGORIES:
            print(key)
        sys.exit(0)

    if args.validate:
        problems = validate_deck(args.validate)
        if problems:
            print("VALIDATION FAILED: %s" % args.validate)
            for p in problems:
                print("  -", p)
            sys.exit(1)
        print("Validation passed: %s" % args.validate)
        sys.exit(0)

    sys.exit(_run_sample(args.output))
