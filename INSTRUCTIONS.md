> Version: 2026-07-03

## Creating Anki Flashcards

### Template engine

anki_templates.py owns all card styling and structure and is the single source of truth for how cards look. Don't restate or override its visual rules (colors, fonts, badges, callouts, lists, spacing, emphasis) anywhere else — not in individual cards, not in these instructions.

1. Author each card as compact structured content (a list of dicts — question, answer, examples, notes, etc.). Never hand-write per-card HTML; keeping styling boilerplate out of cards is the main token saving.
2. Pass the content to the engine, which applies all styling and writes the import file.
3. If cards should look different, change the engine — not individual cards. One-off HTML tweaks to a single card come only after the engine has generated it.

### Card types

Use the categories the engine defines — check it to see which exist and what content fields each accepts. If the material needs a missing category, add a builder to the engine rather than hand-rolling HTML, then use it. Keep one label and casing per category; don't introduce variants.

### True/false cards

Proactively add `true_false` cards wherever the material has a trap: look-alike or easily-swapped word parts (hyper- vs hypo-, inter- vs intra-), common misconceptions, or claims that are almost-but-not-quite right. Front: a single assertion that gives nothing away. Verdict: True/False. Explanation: focus on why the other answer is wrong — usually more illuminating than restating the obvious.

### Output

The engine emits a tab-separated .txt with `#separator:tab` and `#html:true` headers and no trailing semicolons.

Write every generated batch to the project's `outbox/` folder, inside a date-prefixed batch folder (e.g. `outbox/2026-07-03-resp-meds/`). Never write generated files anywhere else, and never read `outbox/` contents as context. Batches are ephemeral: once imported into Anki, the batch folder is deleted.

### Content conventions

- Atomicity: one gradeable idea per card — if you can't judge your recall as right or wrong in one beat, split the card. Depth should come from a sharper question, not from stacking several facts into one answer.
- Symbols: use Unicode for subscripts, superscripts, charges, arrows, and other simple symbols (H₂O, Ca²⁺, →) — renders everywhere with no setup. Reserve LaTeX/MathJax for genuinely mathematical content (fractions, complex expressions, multi-line equations); Anki uses \( \) and \[ \] delimiters, and MathJax can be unreliable on some mobile clients.
- Don't wrap answers in outer quotation marks; remove stray or doubled quotes. Emphasize key terms with the engine's accent-italics helper, not quotes.
- When extending an existing series, keep existing questions' wording stable: Anki matches imports on the first field, so stable wording means re-imports update notes instead of duplicating them.
