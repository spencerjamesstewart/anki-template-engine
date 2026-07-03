#!/bin/bash
# Entry point for Cowork sessions. Subcommands: update | gen <driver.py> | validate <deck.txt> | sample
set -euo pipefail

# Remember where the caller invoked us from: relative arguments (driver paths)
# must be resolved against it, because we immediately cd to the repo for git.
caller_pwd="$PWD"
cd "$(dirname "$0")"

usage() {
    cat <<'EOF'
Usage: ./run.sh <subcommand>

Subcommands:
  update              Pull the latest pushed version (fast-forward only).
  gen <driver.py>     Update, run a batch driver, validate every deck it wrote.
  validate <deck.txt> Validate a generated deck file.
  sample              Build the sample deck and self-check it.
  -h, --help          Show this help.
EOF
}

do_update() {
    echo "Updating clone in $(pwd) (git pull --ff-only)..."
    if [ -n "$(git status --porcelain)" ]; then
        echo "ERROR: clone is dirty — fix manually (this clone must stay a read-only deployment)." >&2
        exit 1
    fi
    if ! git pull --ff-only; then
        echo "ERROR: clone has diverged from the remote — fix manually." >&2
        exit 1
    fi
}

cmd="${1:-}"

case "$cmd" in
    update)
        do_update
        ;;
    gen)
        if [ $# -lt 2 ]; then
            echo "ERROR: gen needs a driver script: ./run.sh gen <driver.py>" >&2
            exit 1
        fi
        driver="$2"
        case "$driver" in
            /*) ;;
            *) driver="$caller_pwd/$driver" ;;
        esac
        if [ ! -f "$driver" ]; then
            echo "ERROR: driver not found: $driver" >&2
            exit 1
        fi
        driver_dir="$(cd "$(dirname "$driver")" && pwd)"
        driver="$driver_dir/$(basename "$driver")"
        repo_root="$(pwd)"

        do_update

        echo "Running driver $driver..."
        driver_out="$(mktemp)"
        trap 'rm -f "$driver_out"' EXIT
        # The driver runs in its own directory so relative output paths land in
        # the batch folder; PYTHONPATH lets it `import anki_templates` directly.
        if ! (cd "$driver_dir" && PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}" python3 "$driver") | tee "$driver_out"; then
            echo "ERROR: driver exited nonzero." >&2
            exit 1
        fi

        # build_deck prints "Generated <N> cards -> <path>" per deck written;
        # that line is the contract for discovering the driver's outputs.
        decks=()
        counts=()
        while IFS= read -r line; do
            n="${line#Generated }"
            n="${n%% *}"
            path="${line#* -> }"
            case "$path" in
                /*) ;;
                *) path="$driver_dir/$path" ;;
            esac
            decks+=("$path")
            counts+=("$n")
        done < <(grep -E '^Generated [0-9]+ cards -> ' "$driver_out" || true)

        if [ "${#decks[@]}" -eq 0 ]; then
            echo "ERROR: driver produced no deck via build_deck." >&2
            exit 1
        fi

        fail=0
        summary=""
        for i in "${!decks[@]}"; do
            if python3 "$repo_root/anki_templates.py" --validate "${decks[$i]}"; then
                status="OK"
            else
                status="VALIDATION FAILED"
                fail=1
            fi
            summary="$summary${decks[$i]}  ${counts[$i]} cards  $status"$'\n'
        done

        echo
        printf '%s' "$summary"
        exit "$fail"
        ;;
    validate)
        if [ $# -lt 2 ]; then
            echo "ERROR: validate needs a deck file: ./run.sh validate <deck.txt>" >&2
            exit 1
        fi
        deck="$2"
        case "$deck" in
            /*) ;;
            *) deck="$caller_pwd/$deck" ;;
        esac
        echo "Validating $deck..."
        python3 anki_templates.py --validate "$deck"
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
