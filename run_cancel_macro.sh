#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_bin="$project_dir/.venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
    python_bin="/usr/local/bin/python3"
fi

read -r -p "Korail ID: " KSKILL_KTX_ID
read -r -s -p "Korail password: " KSKILL_KTX_PASSWORD
printf '\n'
export KSKILL_KTX_ID KSKILL_KTX_PASSWORD

read -r -p "Departure station: " dep
read -r -p "Arrival station: " arr
read -r -p "Date (YYYYMMDD): " travel_date
read -r -p "Start time (HHMMSS): " travel_time

exec "$python_bin" "$project_dir/scripts/cancel_ticket_macro.py" \
    "$dep" "$arr" "$travel_date" "$travel_time" --confirm "$@"
