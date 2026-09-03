#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_bin="$project_dir/.venv/bin/python"
port="${KTX_WEB_PORT:-5001}"

if [[ ! -x "$python_bin" ]]; then
    python_bin="/usr/local/bin/python3"
fi

printf '%s\n' "KTX Finder: http://127.0.0.1:$port"
KTX_WEB_PORT="$port" exec "$python_bin" "$project_dir/web_app.py"
