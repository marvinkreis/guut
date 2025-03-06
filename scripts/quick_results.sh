#!/usr/bin/env bash

# Summarized the results of a run in text form.
# Usage: ./script run_dir [run_dir...]

# Strict bash
set -euo pipefail
IFS=$'\n\t'

for d in "$@"; do
    (
        cd "${d}"/loops
        killed_mutants="$(fd test.py | wc -l)"
        total_mutants="$(ls | wc -l)"
        alive_mutants=$(( total_mutants - killed_mutants ))

        echo $d
        echo 'Mutants:'
        printf "  total:  %d\n" "$total_mutants"
        printf "  alive:  %d\n" "$alive_mutants"
        printf "  killed: %d\n" "$killed_mutants"
        echo
    )
done
