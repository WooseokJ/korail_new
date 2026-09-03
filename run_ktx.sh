#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
secrets_file="${KSKILL_SECRETS_FILE:-$HOME/.config/k-skill/secrets.env}"

if [[ -f "$secrets_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$secrets_file"
    set +a
fi

if [[ -z "${KSKILL_KTX_ID:-}" ]]; then
    read -r -p "Korail ID: " KSKILL_KTX_ID
fi

if [[ -z "${KSKILL_KTX_PASSWORD:-}" ]]; then
    read -r -s -p "Korail password: " KSKILL_KTX_PASSWORD
    printf '\n'
fi

if [[ -z "$KSKILL_KTX_ID" || -z "$KSKILL_KTX_PASSWORD" ]]; then
    printf '%s\n' "Korail ID and password are required." >&2
    exit 1
fi

if [[ "$#" -eq 0 ]]; then
    set -- --help
fi

exec /usr/local/bin/python3 "$project_dir/scripts/ktx_booking.py" "$@"