# Anki Template Engine

A zero-dependency (stdlib-only) Python module that turns compact card dicts
into a styled, tab-separated Anki import file via `build_deck(cards, output_path)`.

## Deployment model

Development happens elsewhere (Claude Code) and is pushed here. A single
canonical clone lives at `~/Documents/Claude/Projects/_tools/<repo-name>/` and
is attached to each Cowork project as an additional folder. That clone is a
read-only deployment: it only ever pulls, via `./run.sh update`, and must
always run the latest pushed version.

## Usage

```
./run.sh update              # fast-forward pull (fails loudly if dirty/diverged)
./run.sh sample              # build the sample deck + self-check (smoke test)
./run.sh validate <deck.txt> # validate a generated deck file
```

Direct engine access:

```
python3 anki_templates.py                 # build sample deck + self-check
python3 anki_templates.py --validate PATH # validate a deck file
python3 anki_templates.py --list-types    # list available card types
```

## Card authoring

See [INSTRUCTIONS.md](INSTRUCTIONS.md) for the universal card-authoring rules.
Its `> Version:` date is bumped on any meaningful content change, so downstream
batches can reference which instruction version produced them.
