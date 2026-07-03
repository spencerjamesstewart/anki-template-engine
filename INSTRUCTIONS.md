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

Generate a batch by authoring a driver script (a small Python file that builds the card list and calls `build_deck`) in the batch folder and running `./run.sh gen <driver>` — never by invoking the engine or the driver directly.

### Content conventions

- Atomicity: one gradeable idea per card — if you can't judge your recall as right or wrong in one beat, split the card. Depth should come from a sharper question, not from stacking several facts into one answer.
- Symbols: use Unicode for subscripts, superscripts, charges, arrows, and other simple symbols (H₂O, Ca²⁺, →) — renders everywhere with no setup. Reserve LaTeX/MathJax for genuinely mathematical content (fractions, complex expressions, multi-line equations); Anki uses \( \) and \[ \] delimiters, and MathJax can be unreliable on some mobile clients.
- Don't wrap answers in outer quotation marks; remove stray or doubled quotes. Emphasize key terms with the engine's accent-italics helper, not quotes.
- When extending an existing series, keep existing questions' wording stable: Anki matches imports on the first field, so stable wording means re-imports update notes instead of duplicating them.

### Expert & orientation questions

Every subject has recurring question forms that experts ask about it (from *What Smart Students Know*, Adam Robinson). Information that answers one of these is the highest-priority card content — "the most popular test questions." Substitute the term being studied for **X**.

**How to apply when generating cards:**

- For each key term or concept, generate cards answering the five orientation questions plus the applicable subject-type expert questions — but only where the source material actually supplies an answer. Never pad or invent to complete the checklist.
- Prioritize: facts answering an expert or orientation question are medium-to-high priority; facts answering neither are usually low priority.
- Prefer card fronts phrased as the expert/orientation question itself, with the term substituted (e.g., "What process causes X?", "How can X be identified?").

**Orientation questions** (universal — default coverage checklist for any major term):

1. What's the definition of X?
2. What's an example of X?
3. What are the different types of X?
4. What is X related to?
5. What can X be compared with?

**Expert questions by subject type** — map the forms to the domain's equivalents (e.g., "what process causes X" ≈ mechanism or etiology; "found with or near X" ≈ structural relations, associations, co-occurrences):

*Type I — fact-based subjects* (large bodies of information to identify, classify, and explain):

- What is X made of?
- What are X's chemical, physical, and structural properties?
- How can X be identified?
- What process causes X?
- What other processes tend to happen at the same time as X?
- Where is X usually found?
- What else is usually found with or near X?
- What processes can cause X to change, and in what ways?
- What can I tell about the history of X?

*Type II — interpretation subjects* (works and texts to analyze; meaning, argument, personal response). These have many more expert questions than Type I. For literature, by category:

- **Character:** major and minor characters, roles and relationships; what each wants vs. truly needs; external and internal obstacles; stakes and risks each will accept; how much choice each has and their obligations; how each changes and what each learns; how we learn about them (actions, dialogue, thoughts).
- **Plot:** the initial event that sets the major character in pursuit of the goal; major plot points and how they tie together; chronological or not, and why; how obstacles escalate; subplots and their relation to the main plot; inevitability vs. destiny and chance; major conflicts; complete reversals of fortune.
- **Setting:** where and when it takes place, and whether that matters to the story.
- **Point of view:** whose POV and why; how it shapes what we know; what we know that the characters don't.
- **Theme:** the major theme; other themes; the overall moral or message.
- **Style:** meaning conveyed directly (description, narration) vs. indirectly (symbol, metaphor, irony, allegory, subtext); word choice and sentence structure; recurring images or symbols; contrasts and parallels.
- **Work as a whole:** genre and how representative of it; significance of the title; what it tells us about its time, the time depicted, our time; why this medium.
- **Author:** comparison with the author's other works; how other authors treated similar themes; whether the author identifies with any character; influence of the times; who influenced them and whom they influenced; traits that would identify other work by this author.

For non-literature Type II material, derive analogues — e.g., for argument-driven texts: What is the thesis? What is the argument for it? What are the strongest objections and replies? What does the position imply in concrete cases? How does it compare with rival positions?

*Type III — problem-solving subjects* (techniques over information; quantitative and symbolic material). While learning a concept or worked technique:

- What would I guess the answer or result should be?
- What is each step of the solution accomplishing?
- What's the pattern here?
- If this changes, what else will change?
- What happens at the extremes?
- Can I generalize this result?
- What are the special cases?
- How can this question be rephrased?
- What are the essential features of this problem?
- What other types of problems or techniques does this remind me of?
- How many different ways can I solve this problem?
- Can I derive the formula?
- How can I make this concept more tangible?

When solving on a test: What does this problem remind me of? What do I already know (givens, unknown, candidate equations)? How can I picture this?

**Deriving expert questions for a new subject:** textbooks don't list them. Scan the textbook introduction and especially chapter-summary/review questions; ignore the specifics and look for recurring general forms. A question form that recurs across chapters is an expert question.
