#!/bin/bash
# Deploy pypen *code* from p340 (canonical repo) to bae, which serves
# pen.grining.eu. The database and pen-media live only on bae and travel the
# other way, pulled nightly by ~/apps/ops/vps-db-backup.sh — this script must
# never touch them.
#
# Local is the source of truth. Reconciled 2026-08-18, when the running site
# had drifted far ahead of git; do not edit templates or views on bae again.
#
#   ./deploy/deploy-code.sh            deploy
#   ./deploy/deploy-code.sh --dry-run  show what would change, touch nothing
set -euo pipefail

REMOTE=bae_llm
DEST=/root/pypen/dpypen/
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/dpypen/"
DRY=""
[[ "${1:-}" == "--dry-run" ]] && DRY="--dry-run"

# db.sqlite3, staticfiles/ and media/ are server-side state: never push them.
# .venv is built on bae and only changes when requirements.txt does.
rsync -az --delete $DRY \
  --exclude '.venv' --exclude 'db.sqlite3' --exclude 'db.sqlite3.*' \
  --exclude 'staticfiles' --exclude 'media' \
  --exclude '__pycache__' --exclude '*.pyc' --exclude '.mypy_cache' \
  --exclude '*.~undo-tree~' --exclude '*.egg-info' --exclude '.pytest_cache' \
  --itemize-changes \
  "$SRC" "$REMOTE:$DEST"

if [[ -n "$DRY" ]]; then
  echo "(dry run — nothing was changed on $REMOTE)"
  exit 0
fi

# Vendored JS/CSS lives in the app's static dir, so it has to be collected
# into STATIC_ROOT (whitenoise serves from there) before the restart.
# settings.py load_dotenv()s /root/pypen/secrets itself, so no sourcing here —
# and that file is not shell-safe anyway (unquoted $ and parens in the key).
#
# The remote shell needs its own `set -o pipefail`: the local one does not
# carry over ssh, so `collectstatic | tail -1` used to report tail's exit
# status and a failed collect went straight on to the restart. That was
# survivable while filenames were unhashed. It no longer is — every page now
# resolves its assets through staticfiles.json, so restarting without a good
# manifest takes the whole site down rather than just serving stale CSS.
ssh "$REMOTE" 'set -euo pipefail; cd /root/pypen/dpypen \
  && /root/pypen/.venv/bin/python manage.py collectstatic --noinput | tail -1 \
  && systemctl restart pypen && sleep 2 && systemctl is-active pypen'
code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 https://pen.grining.eu/)
echo "pen.grining.eu -> $code"
[[ "$code" == "200" ]] || { echo "DEPLOY LOOKS BROKEN"; exit 1; }
