> Version: 2026-07-13

## What Anki is for

Anki is the **cold-recall layer**: material that must be known without thinking — facts, names, classifications, word parts, values, pairings. Its input is usually a list the user already has and has already decided to memorize ("here are the drugs for the unit 5 exam — a card for each").

Anki is **not** the place for conceptual understanding, multi-step reasoning, or integrating ideas across sources. That work happens elsewhere. A card that can't be graded right-or-wrong in one beat does not belong here, no matter how important the idea is.

The default posture is therefore **narrow, not thorough**. When the user supplies a list, generate cards for the items on it. Do not expand scope, do not pad toward coverage, and do not add items the user didn't ask for. If the material seems to warrant more cards than the user asked for, say so and ask — don't just generate them.

## Creating Anki Flashcards

### Template engine

anki_templates.py owns all card styling and structure and is the single source of truth for how cards look. Don't restate or override its visual rules (colors, fonts, badges, callouts, lists, spacing, emphasis) anywhere else — not in individual cards, not in these instructions.

1. Author each card as compact structured content (a list of dicts — question, answer, examples, notes, etc.). Never hand-write per-card HTML; keeping styling boilerplate out of cards is the main token saving.
2. Pass the content to the engine, which applies all styling and writes the import file.
3. If cards should look different, change the engine — not individual cards. One-off HTML tweaks to a single card come only after the engine has generated it.

### Card types

Use the categories the engine defines — check it to see which exist and what content fields each accepts. If the material needs a missing category, add a builder to the engine rather than hand-rolling HTML, then use it. Keep one label and casing per category; don't introduce variants.

Two categories worth noting by name: `in_context` (badge IN CONTEXT, field `excerpt`) is for a term encountered inside a real artifact — a chart note, a commit message, a case excerpt, a passage. `alias` (badge ALIAS) is for one thing with two names: generic/brand, common/scientific, English/Latin, symbol/name.

### True/false cards

Trap cards are the one place the engine may add cards beyond the user's list, and only when the list itself contains a genuine trap: a look-alike or easily-swapped pair (hyper- vs hypo-, inter- vs intra-), a common misconception, or a claim that is almost-but-not-quite right. They drill the user's list harder; they do not expand it. **Ask before adding them** if the user didn't request them.

Front: a single assertion that gives nothing away. Verdict: True/False. Explanation: focus on why the other answer is wrong — usually more illuminating than restating the obvious.

### Tags

Every batch must be tagged. Tags have three axes:

- **Subject** (required) — e.g. `rust`, `medterm`, `ethics`.
- **Purpose** — what the cards are for, e.g. `unit-5-exam`, `final`.
- **Source** — what they were generated from, e.g. `lecture-12`, `openstax-ch7`.

Tags are kebab-case, lowercase, no spaces. If the user hasn't said what to tag with, ask a one-line follow-up — a mis-tagged or untagged batch is expensive to fix after import.

### Output

The engine emits a tab-separated .txt with `#separator:tab`, `#html:true`, and `#tags column:3` headers and no trailing semicolons. Each card line is `front<TAB>back<TAB>tags`, where `tags` is a space-separated list of tag strings.

Write every generated batch to the single Anki Cowork folder's `outbox/` folder — there is now one Anki project covering all subjects, not one per subject — inside a batch folder named `outbox/YYYY-MM-DD-<subject>-<slug>/` (e.g. `outbox/2026-07-13-pharm-unit-5/`). Never write generated files anywhere else, and never read `outbox/` contents as context. Batches are ephemeral: once imported into Anki, the batch folder is deleted. Nothing is written into the engine repo — drivers and decks live in the batch folder.

Generate a batch by authoring a driver script (a small Python file that builds the card list and calls `build_deck`) in the batch folder and running `./run.sh gen <driver>` — never by invoking the engine or the driver directly.

### Content conventions

- Atomicity: one gradeable idea per card — if you can't judge your recall as right or wrong in one beat, split the card. Depth should come from a sharper question, not from stacking several facts into one answer.
- Symbols: use Unicode for subscripts, superscripts, charges, arrows, and other simple symbols (H₂O, Ca²⁺, →) — renders everywhere with no setup. Reserve LaTeX/MathJax for genuinely mathematical content (fractions, complex expressions, multi-line equations); Anki uses \( \) and \[ \] delimiters, and MathJax can be unreliable on some mobile clients.
- Don't wrap answers in outer quotation marks; remove stray or doubled quotes. Emphasize key terms with the engine's accent-italics helper, not quotes.
- When extending an existing series, keep existing questions' wording stable: Anki matches imports on the first field, so stable wording means re-imports update notes instead of duplicating them.

### Choosing a card's shape

When the user gives a list of items without specifying what the card should ask, these are the shapes a card can take. Pick the one the material best supports — usually one card per item, occasionally two if the item genuinely has two distinct things worth knowing cold. This is a menu to choose from, **not a checklist to complete**. Never generate a card for every question form.

**Orientation questions** (substitute the term being studied for **X**):

1. What's the definition of X?
2. What's an example of X?
3. What are the different types of X?
4. What is X related to?
5. What can X be compared with?

**Expert questions** (fact-based subjects — large bodies of information to identify, classify, and explain):

- What is X made of?
- What are X's chemical, physical, and structural properties?
- How can X be identified?
- What process causes X?
- What other processes tend to happen at the same time as X?
- Where is X usually found?
- What else is usually found with or near X?
- What processes can cause X to change, and in what ways?
- What can I tell about the history of X?
