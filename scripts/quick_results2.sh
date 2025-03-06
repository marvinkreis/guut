#!/bin/sh

# Summarized the results of a run in CSV form.
# Usage: ./script run_dir [run_dir...]

echo project,preset,alive,killed
for d in *; do
    project=$(echo $d | rg '.*?_.*?_.*?_(.*)_[a-z0-9]{8}' -r '$1')
    preset=$(echo $d | rg '(.*?_.*?_.*?)_.*_[a-z0-9]{8}' -r '$1')
    mutants="$(jq -r '{alive: .alive_mutants | length, killed: .killed_mutants | length}' $d/result.json)"
    alive=$(echo $mutants | rg '.*"alive": ([0-9]+).*' -r '$1')
    killed=$(echo $mutants | head -n6 | rg '.*"killed": ([0-9]+).*' -r '$1')
    echo ${project},${preset},${alive},${killed}
done
