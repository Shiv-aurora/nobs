#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_tfvars
python - "${TFVARS_FILE}" <<'PY'
from pathlib import Path
import re, sys
text=Path(sys.argv[1]).read_text()
def value(name, default=None):
    m=re.search(rf'^\s*{re.escape(name)}\s*=\s*(?:"([^"]*)"|([^#\n]+))', text, re.M)
    if not m: return default
    return (m.group(1) if m.group(1) is not None else m.group(2)).strip()
budget=float(value('budget_amount_usd','25'))
disk=int(value('mattermost_disk_size_gb','20'))
machine=value('mattermost_machine_type','e2-small')
assert budget <= 25, f'budget_amount_usd exceeds $25: {budget}'
assert disk <= 30, f'disk exceeds 30GB: {disk}'
assert machine in {'e2-small','e2-medium'}, f'unapproved VM type: {machine}'
print(f'Cost profile accepted: ${budget:.2f}/month budget, {machine}, {disk}GB pd-standard, Cloud Run max=1/min=0.')
PY
