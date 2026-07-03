#!/bin/bash
# Entry point for Cowork sessions. Subcommands: update | validate <deck.txt> | sample
set -euo pipefail

cd "$(dirname "$0")"

usage() {
    cat <<'EOF'
Usage: ./run.sh <subcommand>

Subcommands:
  update              Pull the latest pushed version (fast-forward only).
  validate <deck.txt> Validate a generated deck file.
  sample              Build the sample deck and self-check it.
  -h, --help          Show this help.
EOF
}

cmd="${1:-}"

case "$cmd" in
    update)
        echo "Updating clone in $(pwd) (git pull --ff-only)..."
        if [ -n "$(git status --porcelain)" ]; then
            echo "ERROR: clone is dirty — fix manually (this clone must stay a read-only deployment)." >&2
            exit 1
        fi
        if ! git pull --ff-only; then
            echo "ERROR: clone has diverged from the remote — fix manually." >&2
            exit 1
        fi
        ;;
    validate)
        if [ $# -lt 2 ]; then
            echo "ERROR: validate needs a deck file: ./run.sh validate <deck.txt>" >&2
            exit 1
        fi
        echo "Validating $2..."
        python3 anki_templates.py --validate "$2"
        ;;
    sample)
        echo "Building sample deck and running self-check..."
        python3 anki_templates.py
        ;;
    -h|--help)
        usage
        ;;
    "")
        usage >&2
        exit 1
        ;;
    *)
        echo "ERROR: unknown subcommand '$cmd'" >&2
        usage >&2
        exit 1
        ;;
esac
