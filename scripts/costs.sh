#!/usr/bin/env bash

# Strict bash
set -euo pipefail
IFS=$'\n\t'

if [[ "$1" == "--total" ]]; then
    only_total=true
    shift 1
else
    only_total=false
fi

if $only_total; then

    prompt_tokens=0;
    for b in $(jq 'map(.usage.prompt_tokens) | add // 0' "$@"); do
        prompt_tokens=$(( prompt_tokens + b ))
    done

    completion_tokens=0;
    for b in $(jq 'map(.usage.completion_tokens) | add // 0' "$@"); do
        completion_tokens=$(( completion_tokens + b ))
    done

    cached_tokens=0;
    for b in $(jq 'map(.usage.cached_tokens) | add // 0' "$@"); do
        cached_tokens=$(( cached_tokens + b ))
    done

    prompt_tokens_price="$(bc <<< "($prompt_tokens - $cached_tokens) * .00000015")"
    completion_tokens_price="$(bc <<< "$completion_tokens * .0000006")"
    cached_tokens_price="$(bc <<< "$cached_tokens * .000000075")"
    total_tokens_price="$(bc <<< "( ($prompt_tokens - $cached_tokens) * .00000015) + ($completion_tokens * .0000006) + ($cached_tokens * .000000075)")"

    echo 'Total'
    printf "  prompt:      %-9d %.4f$\n" "$prompt_tokens" "$prompt_tokens_price"
    printf "  completion:  %-9d %.4f$\n" "$completion_tokens" "$completion_tokens_price"
    printf "  cached:      %-9d %.4f$\n" "$cached_tokens" "$cached_tokens_price"
    printf "  total:       %-9d %.4f$\n" "$(( prompt_tokens + completion_tokens ))" "$total_tokens_price"

else

    sum_prompt_tokens=0
    sum_completion_tokens=0

    for x in "$@"; do
        echo "$(basename "${x}")"
        prompt_tokens=$(jq -r 'map(.usage.prompt_tokens) | add // 0' "$x")
        completion_tokens=$(jq -r 'map(.usage.completion_tokens) | add // 0' "$x")
        total_tokens=$(jq -r 'map(.usage.total_tokens) | add // 0' "$x")

        prompt_tokens_price="$(bc <<< "$prompt_tokens * .00000015")"
        completion_tokens_price="$(bc <<< "$completion_tokens * .0000006")"
        total_tokens_price="$(bc <<< "($prompt_tokens * .00000015) + ($completion_tokens * .0000006)")"

        sum_prompt_tokens=$(( sum_prompt_tokens + prompt_tokens ))
        sum_completion_tokens=$(( sum_completion_tokens + completion_tokens ))

        printf "  prompt:      %-9d %.4f$\n" "$prompt_tokens" "$prompt_tokens_price"
        printf "  completion:  %-9d %.4f$\n" "$completion_tokens" "$completion_tokens_price"
        printf "  total:       %-9d %.4f$\n" "$total_tokens" "$total_tokens_price"
        echo
    done

    sum_prompt_tokens_price="$(bc <<< "$sum_prompt_tokens * .00000015")"
    sum_completion_tokens_price="$(bc <<< "$sum_completion_tokens * .0000006")"
    sum_total_tokens_price="$(bc <<< "($sum_prompt_tokens * .00000015) + ($sum_completion_tokens * .0000006)")"

    echo '----------------------------------------'
    echo
    echo 'Total'
    printf "  prompt:      %-9d %.4f$\n" "$sum_prompt_tokens" "$sum_prompt_tokens_price"
    printf "  completion:  %-9d %.4f$\n" "$sum_completion_tokens" "$sum_completion_tokens_price"
    printf "  total:       %-9d %.4f$\n" "$(( sum_prompt_tokens + sum_completion_tokens ))" "$sum_total_tokens_price"

fi
