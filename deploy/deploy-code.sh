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
# /opt/pypen since 2026-11-01 (PYPEN-4): the code and the venv belong to root,
# the database (/opt/pypen/data) and the media to the `pypen` user the service
# runs as. Before that it all lived in /root and gunicorn ran as root.
# /root/pypen/dpypen/db.sqlite3 is a symlink to the live DB, for the backups.
APP=/opt/pypen
DEST=$APP/dpypen/
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/dpypen/"
DRY=""
[[ "${1:-}" == "--dry-run" ]] && DRY="--dry-run"

# The tests gate the deploy, dry run included. `ship` would do this for a p340
# app, but pypen runs on bae, so ship never sees it — until 2026-09-26 a red
# suite (say, a view that lost its login decorator) went straight to the
# public site. They run in the dev venv against a throwaway test database;
# the local db.sqlite3 is not touched.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if ! out=$(cd "$ROOT/dpypen" && "$ROOT/.devvenv/bin/python" manage.py test dpypen.items 2>&1); then
  echo "$out" | tail -40
  echo "TESTS FAILED — nothing was deployed"
  exit 1
fi
echo "$out" | grep -E '^Ran [0-9]+ tests'

# db.sqlite3, staticfiles/ and media/ are server-side state: never push them.
# .venv is built on bae and only changes when requirements.txt does.
# --chown: rsync -a kept p340's uid 1000 on every file, an owner bae does not
# have — whoever got that uid later could have rewritten the code root ran.
rsync -az --delete $DRY --chown=root:root \
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
# into STATIC_ROOT (nginx serves /var/www/pen-static) before the restart.
# settings.py load_dotenv()s /opt/pypen/secrets itself, so no sourcing here —
# and that file is not shell-safe anyway (unquoted $ and parens in the key).
#
# The remote shell needs its own `set -o pipefail`: the local one does not
# carry over ssh, so `collectstatic | tail -1` used to report tail's exit
# status and a failed collect went straight on to the restart. Every page
# resolves its assets through staticfiles.json, so restarting without a good
# manifest takes the whole site down rather than just serving stale CSS.
#
# The venv follows requirements.txt: a changed file is installed before the
# restart (it used to wait for someone to remember, see PyJWT in that file).
#
# Migrations run here too (they did not until 2026-08-27, and a new field
# 500'd every page touching it). They, and backfill_styled_thumbs (cheap once
# the twins exist; it keeps the pen wall off full-size art) and sized_copies
# (the page-size WebP copies, PYPEN-3: made ahead so no visitor waits for an
# encode, and the copies of deleted photos removed), run as `pypen`,
# so the database and the media they write stay that user's. clearsessions
# drops the expired sessions: nothing ever did, and on 1 Nov 2026 the live DB
# (and so every nightly copy on p340) carried 443 dead ones back to 2020 next
# to the 55 live ones (PYPEN-4). A deploy comes often enough. collectstatic
# and the bytecode are root's, like the code.
ssh "$REMOTE" 'set -euo pipefail; cd '"$APP"'/dpypen
  want=$(sha256sum requirements.txt | cut -c1-64)
  have=$(cat '"$APP"'/.venv/.requirements.sha256 2>/dev/null || true)
  if [[ "$want" != "$have" ]]; then
    '"$APP"'/.venv/bin/pip install -q -r requirements.txt 2>&1 | { grep -v notice || true; } | tail -3
    echo "$want" > '"$APP"'/.venv/.requirements.sha256
    echo "venv: requirements.txt installed"
  fi
  runuser -u pypen -- '"$APP"'/.venv/bin/python manage.py migrate --noinput | tail -3
  runuser -u pypen -- '"$APP"'/.venv/bin/python manage.py backfill_styled_thumbs | tail -1
  runuser -u pypen -- '"$APP"'/.venv/bin/python manage.py sized_copies | tail -1
  runuser -u pypen -- '"$APP"'/.venv/bin/python manage.py clearsessions
  '"$APP"'/.venv/bin/python manage.py collectstatic --noinput | tail -1
  '"$APP"'/.venv/bin/python -m compileall -q dpypen >/dev/null || true
  systemctl restart pypen && sleep 2 && systemctl is-active pypen'
code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 https://pen.grining.eu/)
echo "pen.grining.eu -> $code"
[[ "$code" == "200" ]] || { echo "DEPLOY LOOKS BROKEN"; exit 1; }
