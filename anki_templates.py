"""
Anki Flashcard Template Engine — Medical Terminology
====================================================
Generate styled, dark-mode-friendly HTML flashcards from MINIMAL content input.
You pass ~200 chars of content per card; this module emits the ~1,000+ chars of
repeated HTML. Cards render in Anki with "HTML enabled" in dark mode.

USAGE
-----
    from anki_templates import build_deck

    cards = [
        {"type": "definition", "q": "What is *cytology*?",
         "a": "The study of cells.",
         "detail": "From *cyt/o* (cell) + *-logy* (study of)."},
        {"type": "suffix", "part": "-emia", "a": "blood condition",
         "decompose": [("-em-", "blood (from *hem/o*)"), ("-ia", "condition")]},
    ]
    build_deck(cards, "deck.txt", tags=["med-term", "ch1"])

CARD CATEGORIES  (type key -> badge, accent color)
--------------------------------------------------
    definition      DEFINITION            sky     #7ec8e3
    concept         CONCEPT               teal    #6ecfcf
    compare         COMPARE & CONTRAST    coral   #f0776c
    key_list        KEY LIST              sage    #a8d5a2
    combining_form  COMBINING FORM        purple  #c4a7e7
    prefix          PREFIX                pink    #e8a0bf
    suffix          SUFFIX                gold    #e8c170
    deconstruction  WORD DECONSTRUCTION   purple  #c4a7e7
    word_building   BUILD A TERM          purple  #c4a7e7
    word_family     WORD FAMILY           teal    #6ecfcf
    clinical        CLINICAL CONTEXT      coral   #f0776c

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
}

# type key -> (BADGE LABEL, palette color name)
CATEGORIES = {
    "definition":     ("DEFINITION",          "sky"),
    "concept":        ("CONCEPT",             "teal"),
    "compare":        ("COMPARE & CONTRAST",  "coral"),
    "key_list":       ("KEY LIST",            "sage"),
    "combining_form": ("COMBINING FORM",      "purple"),
    "prefix":         ("PREFIX",              "pink"),
    "suffix":         ("SUFFIX",              "gold"),
    "deconstruction": ("WORD DECONSTRUCTION", "purple"),
    "word_building":  ("BUILD A TERM",        "purple"),
    "word_family":    ("WORD FAMILY",         "teal"),
    "clinical":       ("CLINICAL CONTEXT",    "coral"),
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
        maps.append(
            '<span style="color:' + a + ';font-weight:700">\u2022</span> '
            '<b style="color:' + a + '">' + str(token) + '</b> \u2014 '
            '<span style="color:' + BODY + '">' + markup(meaning, a) + '</span>'
        )
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
         "fig.", "no.", "cf.", "al.", "st.", "approx.", "inc.", "ph.d."}


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
            if token in _ABBR or is_initial or not next_is_break:
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
    """Fields: q, items[(label, desc)...], ex?, note?  |  badge?, color?."""
    a = _accent(d, "compare")
    fr = front(_badge(d, "compare"), a, markup(d["q"], a))
    parts = [compare_cards(d["items"], a)]
    if d.get("ex"):
        parts.append(example_box(d["ex"], a))
    if d.get("note"):
        parts.append(muted_note(d["note"], a))
    return fr, back("".join(parts))


def card_key_list(d):
    """Fields: q, items[(label, desc) | str ...], ordered?, ex?, note?
    |  badge?, color?."""
    a = _accent(d, "key_list")
    fr = front(_badge(d, "key_list"), a, markup(d["q"], a))
    parts = [list_box(d["items"], a, ordered=d.get("ordered", False))]
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
    pron?, note?  |  badge?, color?."""
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


def card_clinical(d):
    """Fields: q, a (interpretation), detail?, chart? (chart-note text),
    related?, ex?, note?  |  badge?, color?."""
    a = _accent(d, "clinical")
    badge = _badge(d, "clinical")
    fr = front(badge, a, markup(d["q"], a))
    parts = []
    if d.get("chart"):
        parts.append(
            section_label("Chart note", a)
            + '<div style="background:' + BOX + ';border-left:3px solid ' + a + '40;'
            'border-radius:6px;padding:10px 12px;margin:6px 0;color:' + BODY + ';'
            'font-style:italic;font-size:0.95em">' + markup(d["chart"], a) + '</div>'
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
_BUILDERS = {
    "definition":     card_definition,
    "concept":        card_concept,
    "compare":        card_compare,
    "key_list":       card_key_list,
    "combining_form": card_combining_form,
    "prefix":         card_prefix,
    "suffix":         card_suffix,
    "deconstruction": card_deconstruction,
    "word_building":  card_word_building,
    "word_family":    card_word_family,
    "clinical":       card_clinical,
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


def build_deck(cards, output_path, tags=None):
    """Write an Anki tab-separated import file.

    Parameters
    ----------
    cards : list[dict]   each has a 'type' key plus that type's fields.
    output_path : str    path for the .txt import file.
    tags : str | list, optional   applied to every card (list joined by spaces).
    """
    lines = ["#separator:tab", "#html:true"]
    if tags:
        tagstr = " ".join(str(t) for t in tags) if isinstance(tags, (list, tuple)) else str(tags)
        lines.append("#tags:" + tagstr)
    for card in cards:
        fr, bk = build_card(card)
        lines.append(_oneline(fr) + "\t" + _oneline(bk))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Generated %d cards -> %s" % (len(cards), output_path))
    return output_path


# ───────────────────────────────────────────────────────────────────────────
# SAMPLE DECK + SELF-CHECKS  (run:  python3 anki_templates.py [out.txt])
# ───────────────────────────────────────────────────────────────────────────
SAMPLE_CARDS = [
    {"type": "definition",
     "q": "What is *cytology*?",
     "a": "The study of cells.",
     "detail": "From *cyt/o* (cell) + *-logy* (study of). It examines the "
               "structure, function, and formation of cells.",
     "ex": "A *cytologist* examines a Pap smear to detect abnormal cervical cells."},

    {"type": "concept",
     "q": "When is the combining vowel *o* kept, and when is it dropped?",
     "a": "Keep the combining vowel before a suffix that begins with a "
          "consonant; drop it before a suffix that begins with a vowel.",
     "ex": [
         "gastr/o + -scopy \u2192 gastroscopy (suffix starts with a consonant \u2192 keep o)",
         "gastr/o + -itis \u2192 gastritis (suffix starts with a vowel \u2192 drop o)",
         "Note: the combining vowel is always kept between two roots, even when "
         "the second root begins with a vowel.",
     ]},

    {"type": "compare",
     "q": "Distinguish the surgical suffixes *-ectomy*, *-otomy*, and *-ostomy*.",
     "items": [
         ("-ectomy", "excision \u2014 surgical *removal* of an organ or part (e.g. *appendectomy*)."),
         ("-otomy", "incision \u2014 *cutting into*; a temporary opening (e.g. *laparotomy*)."),
         ("-ostomy", "creation of a new, *permanent* opening, or *stoma* (e.g. *colostomy*)."),
     ],
     "note": "Hook: -ectomy = takE it out, -Otomy = Open (cut into), "
             "-ostomy = an Opening that stays."},

    {"type": "key_list",
     "q": "What are the four building blocks of a medical term?",
     "items": [
         ("Word root", "the foundation that carries the core meaning (e.g. *cardi* = heart)."),
         ("Combining vowel", "usually *o*; links a root to another root or to a suffix."),
         ("Suffix", "the word ending that modifies the meaning (e.g. *-itis* = inflammation)."),
         ("Prefix", "an element at the beginning that modifies the meaning (e.g. *peri-* = surrounding)."),
     ],
     "note": "A word root plus its combining vowel (e.g. *cardi/o*) is called a *combining form*."},

    {"type": "combining_form",
     "part": "cardi/o",
     "a": "heart",
     "pron": "/KAR-dee-oh/",
     "ex": [
         "cardi/o + -logy \u2192 cardiology (study of the heart)",
         "cardi/o + -megaly \u2192 cardiomegaly (enlargement of the heart)",
         "peri- + cardi/o + -um \u2192 pericardium (membrane surrounding the heart)",
     ],
     "related": ["cardiac", "myocardium", "tachycardia", "bradycardia"]},

    {"type": "prefix",
     "part": "peri-",
     "a": "surrounding, around",
     "ex": [
         "peri- + cardi/o + -um \u2192 pericardium (membrane surrounding the heart)",
         "peri- + oste/o + -um \u2192 periosteum (membrane around a bone)",
     ],
     "note": "Contrast with *endo-* (within) and *epi-* (above, upon)."},

    {"type": "suffix",
     "part": "-emia",
     "a": "blood condition",
     "decompose": [("-em-", "blood (from *hem/o*)"), ("-ia", "condition, state")],
     "ex": [
         "leuk/o + -emia \u2192 leukemia (cancerous increase in white blood cells)",
         "an- + -emia \u2192 anemia (deficiency of red blood cells)",
         "hyper- + glyc/o + -emia \u2192 hyperglycemia (high blood sugar)",
     ],
     "note": "*-emia* decomposes into the root *-em-* (blood) plus the base "
             "suffix *-ia* (condition)."},

    {"type": "deconstruction",
     "term": "electrocardiogram",
     "a": "A record of the electrical activity of the heart.",
     "parts": [
         ("electr/o", "electricity"),
         ("cardi/o", "heart"),
         ("-gram", "record (written or recorded image)"),
     ],
     "pron": "/eh-lek-troh-KAR-dee-oh-gram/",
     "note": "Commonly abbreviated *ECG* (or *EKG*, from the German *Elektrokardiogramm*)."},

    {"type": "word_building",
     "clue": "inflammation of the stomach",
     "term": "gastritis",
     "pron": "/gas-TRY-tis/",
     "parts": [("gastr", "stomach"), ("-itis", "inflammation")],
     "note": "The combining vowel *o* is dropped because the suffix *-itis* "
             "begins with a vowel."},

    {"type": "word_family",
     "root": "gastr/o",
     "members": [
         ("gastritis", "inflammation of the stomach"),
         ("gastrectomy", "surgical removal of all or part of the stomach"),
         ("gastroenterology", "study of the stomach and intestines"),
         ("gastromegaly", "enlargement of the stomach"),
         ("epigastric", "pertaining to the region above the stomach"),
     ],
     "note": "*gastr/o* = stomach; combine it with parts you know \u2014 "
             "*-itis*, *-ectomy*, *-logy*."},

    {"type": "clinical",
     "q": "A chart note reads *acute gastroenteritis*. What does it describe, "
          "and how does the term break down?",
     "chart": "Pt presents with N/V and diarrhea x2 days. Dx: acute gastroenteritis.",
     "a": "Sudden-onset inflammation of the stomach and intestines.",
     "detail": "Breaks down as *gastr/o* (stomach) + *enter/o* (intestines) + "
               "*-itis* (inflammation); *acute* signals rapid onset and a short course.",
     "related": ["N/V (nausea and vomiting)", "Dx (diagnosis)", "enteritis", "dehydration"]},
]


def _self_check(path):
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")
    body = [l for l in lines if l and not l.startswith("#")]
    fails = []

    if lines[0] != "#separator:tab":
        fails.append("first line is not '#separator:tab'")
    if lines[1] != "#html:true":
        fails.append("second line is not '#html:true'")

    if len(body) != len(SAMPLE_CARDS):
        fails.append("expected %d card lines, got %d" % (len(SAMPLE_CARDS), len(body)))

    for i, l in enumerate(body, 1):
        if l.count("\t") != 1:
            fails.append("card %d has %d tabs (expected exactly 1)" % (i, l.count("\t")))

    for i, l in enumerate(lines, 1):
        if l.endswith(";"):
            fails.append("line %d ends with a semicolon" % i)

    if "<br><br>" in text:
        fails.append("found a double <br><br>")

    for tok in re.findall(r"#([0-9a-fA-F]+)", text):
        if len(tok) not in (6, 8):
            fails.append("hex #%s has length %d (expected 6 or 8)" % (tok, len(tok)))

    for tag in ("div", "span", "i", "b"):
        opens = len(re.findall(r"<" + tag + r"(?:\s|>)", text))
        closes = len(re.findall(r"</" + tag + r">", text))
        if opens != closes:
            fails.append("unbalanced <%s>: %d open vs %d close" % (tag, opens, closes))

    for i, l in enumerate(body, 1):
        back_html = l.split("\t", 1)[1]
        if "border-left:3px solid" not in back_html:
            fails.append("card %d back is not inside a callout box" % i)

    return fails


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "medical_terminology_sample.txt"
    build_deck(SAMPLE_CARDS, out, tags=["med-term", "ch1", "basic-word-structure"])
    problems = _self_check(out)
    if problems:
        print("SELF-CHECK FAILED:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("Self-checks passed: %d categories, tab-separated, headers OK, "
          "no trailing ';', no <br><br>, hex 6/8 only, balanced tags, "
          "every answer boxed." % len(SAMPLE_CARDS))
