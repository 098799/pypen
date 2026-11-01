# pypen — audit

## Security (PYPEN-4, 1 Nov 2026)

The live app (pen.grining.eu, public on bae), end to end: the routes, sign-in,
uploads, the AI calls, the dependencies, the service on bae, nginx, and what a
browser keeps. A finding is either fixed (with its test, if code) or in the
list for Tomek at the end. Earlier pass: 25 Sep 2026, `tests_security.py`
(the admin password door, the dependency floors).

### The model, as it is now

- **One collection, one owner.** Google sign-in, only for the addresses in
  `ALLOWED_EMAILS` (one address on bae). Every signed-in user is a superuser
  and sees and changes everything. So "someone else's data" does not exist:
  there is no other owner whose photo a crafted request could send to the AI.
- **Guests** arrive on an invite link (`/i/<token>/`, 96 random bits, may
  expire or be revoked in the admin) and read everything; they never write
  (`tests_doors.py` walks every route, GET and POST).
- **A stranger** sees the landing page and the way in. The walls and the
  share links are closed too until `PUBLIC_SHOWCASE` is set.
- **Photos** (`/media/`) are served by nginx without a session. A photo is
  private by its name only: 128 random bits (`_random_media_path`); every one
  of the 591 files on bae has such a name, there is no directory listing
  (`/media/` and `/media/pen_photos/` answer 403), and `Referrer-Policy:
  same-origin` keeps the names out of other sites' logs. This is what lets a
  guest's page, a share link and the service worker show photos without a
  gate in front of nginx. Every upload is re-encoded to JPEG by Pillow, so no
  EXIF survives: all 591 files checked, none has EXIF or GPS.

### Fixed in this pass

| finding | fix | pinned by |
|---|---|---|
| The allowlist read only the address Google sent, not whether Google had verified it. A Google account made on a non-Gmail address can carry an address it never proved; given one of ours it would have been signed up as a new superuser. | `auth._verified_allowed`: allowlisted **and** `email_verified` | `GoogleMustVouchForTheAddress` |
| `ACCOUNT_LOGOUT_ON_GET = True`: any page on the internet could sign the owner out with `<img src=…/accounts/logout/>`. | Off. Sign out was already a POST in Settings. | `SigningOutForgetsTheDevice` |
| After Sign out or Leave, a shared phone still held the collection: the service worker's kept pages (Leave did not even send `KIT_FORGET`), the palette's recent searches in localStorage, the HTTP cache. | `Clear-Site-Data: "cache", "storage"` on both (`security.py`); Leave sends `KIT_FORGET` too and is a full navigation. The theme choice is forgotten with the rest. | `SigningOutForgetsTheDevice` |
| No Content-Security-Policy. | Sent on every answer; see the decision below. Also `Permissions-Policy` (no camera, microphone, place, payment, USB) and `Cache-Control: private` on every signed-in or guest page. | `EveryAnswerCarriesThePolicy` |
| A file Pillow cannot read (a PDF, a HEIC, a crafted file) was a 500 on every upload route, and lost the whole batch. Pillow only **warns** between `MAX_IMAGE_PIXELS` and twice that, so the 50 MP cap was really 100 MP. | `models.BadImage`; the warning is an error; the route names the bad file and keeps the rest. | `UploadsMustBePhotos` |
| The notebook import sent the upload to Anthropic as it came: the browser's claimed content type, the phone's EXIF (where the photo was taken), up to nginx's 25 MB (the API refuses over 5 MB after the wait). | Checked and re-encoded first (`normalised_jpeg`, ≤ 2400 px, JPEG). | `UploadsMustBePhotos` |
| `photos/…/rotate/` with a non-number was a 500; any angle but a quarter turn left black corners. | Only 90 / 180 / 270. | `UploadsMustBePhotos` |
| Two tooltips (History's Gantt, a pen's mini Gantt) put the stored nib name in with `innerHTML`. Only the owner writes it, but it is still markup from the database. | Text nodes. | — |
| The walls loaded Google Fonts (and told Google who looked), while the same faces are self-hosted for every other page. | `fonts.css`; `font-src 'self'` now holds it. | `test_the_walls_load_no_font_from_google` |
| pip-audit of bae's venv: pillow 12.3.0 (14 advisories, among them decoders every upload goes through), djangorestframework 3.17.2, pyasn1 0.6.4, certifi; dev tools pip, setuptools, pygments, pytest, black. `oauthlib` and `six` installed and unused. gunicorn in the venv by hand, not in `requirements.txt`. | New venv from `requirements.txt` with the floors raised; gunicorn pinned. pip-audit of the new venv: **no known vulnerabilities**. The deploy now installs `requirements.txt` whenever it changes. | `DependenciesAreAboveTheirAdvisories` |
| gunicorn ran **as root** from `/root/pypen` (REGISTRY rule 7). A hole in the app, Pillow or a dependency was root on bae, which serves nine other sites. | Moved to `/opt/pypen`, user `pypen` (system, no shell). Code and venv root-owned, read-only to it; it writes only `/opt/pypen/data` (the DB, 0750) and `/var/www/pen-media`. The unit adds `ProtectHome`, an empty capability set, `PrivateDevices`, `RestrictNamespaces`, `ConditionHost=bae-llm` (rule 6) and more (`deploy/pypen.service`). | — |
| The deploy's `rsync -a` gave every file p340's uid 1000, an owner bae does not have: whoever got that uid later could have rewritten code that root ran. | `--chown=root:root`. | — |
| Secrets file | `/opt/pypen/secrets` root:pypen 0640 (was root 0600, readable by root only, which the new user is not). | — |
| nginx had a rate limit on `/admin/` only. | `/accounts/` and `/i/`: 12 a minute per address, burst 10, then 429 (checked live: the 12th request got 429). `nosniff` on `/static/` and `/media/` too. The upstream is `127.0.0.1:8000`: `localhost` tried `[::1]` first and was refused on every request. | — |
| nginx had not reloaded since about 30 Oct: atlas's vhost changed a `limit_req` zone's key, which a reload cannot take (`[emerg]` in `/var/log/nginx-error.log`, while `systemctl reload` said OK). | One `systemctl restart nginx`; all nine sites answered 200 before and after. Atlas's waiting change is live with it. | — |

| Accepting an invite was an hx-boost swap of `#main` only: the new guest kept the stranger's header, with no tab bar and no Leave, until a reload (found on the live walk). | The form is a full page load, like Sign out and Leave. | `test_accepting_an_invite_is_a_full_page_load` |

**GitHub's Dependabot** (the ticket said to start there) counted 47 alerts
at the push of this pass. Its list needs a GitHub sign-in, and p340 has none
(`gh` is not installed on p340, p14s or bae; no token; no browser profile has
a GitHub session; pushes go over an SSH key, which the API does not take). So
the same scan was done against OSV (api.osv.dev), which mirrors GitHub's
advisory database, over the two manifests Dependabot reads, with each `==`
pin and each `>=` floor at its floor, as Dependabot reads them:

| | `dpypen/requirements.txt` | `_archive/requirements.txt` |
|---|---|---|
| before this pass | 116 advisories: pillow 12.3.0 (59), PyJWT ≥2.13.0 (29), urllib3, cryptography, pyasn1, DRF, setuptools, black, pytest | 3: pandas ≥0.22.0, pytest ≥3.5.0 |
| after the venv bumps | 41: PyJWT, urllib3, cryptography — **floors** below a fix while bae ran fixed versions (2.15.1, 2.8.0, 50.0.2), so pip-audit of the venv was clean and Dependabot was not | 3 |
| now | **0** (floors raised to what bae runs) | **0** (floors raised; the old CLI is never installed) |

Lesson, in `requirements.txt` too: a `>=` floor is what Dependabot sees.
The one GitHub credential on the three hosts is the Copilot editor plugin's
sign-in (`~/.config/github-copilot/hosts.json`, p340). It was not used: it was
given to Copilot, not for reading a repository's security data.
**So the alert list itself is still unread — a step only Tomek can do.**
Tomek: after `gh auth login`, `gh api repos/098799/pypen/dependabot/alerts
--jq '.[]|select(.state=="open")'` should be empty; dismiss what is left as
"not used" if it is the archive.

**Second look, 1 Nov 2026 (burn p11011140).** Still no GitHub sign-in on
p340, p14s or bae (`gh` absent, no `~/.config/gh`). The one signal GitHub
gives without one is the push answer: while a repository has open alerts on
its default branch, every push prints `GitHub found N vulnerabilities on
098799/pypen's default branch`. The push of this note printed none (the
pass's first push printed 47). Read: no open alerts. It is a proxy, not the
list; the `gh api` call above stays the proof.

Then the source itself: the repository is public, and GitHub's dependency
graph (the data Dependabot raises its alerts from) is readable without a
sign-in at `api.github.com/repos/098799/pypen/dependency-graph/sbom`. The
graph built at 11:45 UTC on 1 Nov (after the floors were raised) lists 48
PyPI packages. 28 have a pinned version in the graph. The other 20 are
`>=` ranges, which the graph leaves unresolved, so each was taken at its
floor in the manifest. Checked against OSV, which mirrors GitHub's
advisory database: 76 name and version pairs, **0 advisories**. Every
package has a version in the graph or in a manifest. So Dependabot has
nothing to alert on.
Only the `/dependabot/alerts` endpoint itself needs a sign-in (401).

Left on GitHub, harmless: two Dependabot PRs from 2023 are still open,
#12 (ipython to 8.10.0) and #13 (Django 3.2.13 to 3.2.18). The repo now
pins ipython 8.27.0 and Django 6.0.8, so both are outdated. Closing them
needs a sign-in: Tomek, close them when you next use GitHub.

Re-checked live in the same pass, all as above: the headers (CSP,
Permissions-Policy, HSTS, `X-Frame-Options`), gunicorn as `pypen` on
`127.0.0.1:8000` only, `/opt/pypen/secrets` root:pypen 0640, the data
directory 0750, `/media/` and `/media/pen_photos/` 403, signup and password
reset 404, no debug page on a 404, nginx sets `X-Forwarded-Proto` itself on
every location (the app trusts it for HTTPS). Walked as owner (a one-hour
session made on bae, deleted after) at 390×844: 24 screens, all 200, no
console error, no CSP report, nothing wider than the phone. As a stranger:
every closed screen goes to Google, and the 13th try within the minute got
nginx's 429.

Checked and fine, nothing changed:

- `/admin/` sends a stranger to Google (25 Sep); allauth's own `/accounts/login/`
  takes no password (`SOCIALACCOUNT_ONLY`, new test); signup and password
  reset answer 404. Google's one-tap token route checks its double-submit
  cookie and goes through the same allowlist.
- gunicorn listens on `127.0.0.1:8000` only.
- Share tokens 72 random bits, invite tokens 96: too many to guess, rate
  limit or not (invites now have one).
- Every AI call (Gemini polish, swatch and sample clean copies, Claude's
  notebook read) is owner-only (`@login_required`) and reads a stored file that
  Pillow already re-encoded; Gemini's answer goes through Pillow again, under
  the same cap, before it is stored.
- No template marks stored text safe; `highlight` escapes before it marks.
- `manage.py check --deploy`: only HSTS and the HTTPS redirect, which nginx
  does (silenced, with the reason, in `settings.py`).
- Uploads: nginx caps a request at 25 MB; Django spills a file over 2.5 MB to
  a temporary file, so a large one does not sit in a worker's memory.

### Decision: CSP with inline script allowed, not a strict (nonce) policy

`script-src 'self' 'unsafe-inline'`, and everything else shut:
`default-src 'self'`, no other origin for scripts, styles, fonts, images,
fetches or workers (an injected script cannot send the collection away with
an `<img>` or a `fetch`), `object-src 'none'`, `base-uri 'self'`,
`form-action 'self' https://accounts.google.com`, `frame-ancestors 'none'`.

A nonce on every script was weighed and turned down, for now:

- the pages carry ~35 inline `<script>` blocks and ~20 `on…=` handlers, and
  several are inside the kit's byte-for-byte snippets (`_settings.html`,
  `_keys.html`, `_toast.html`) that the app may not edit — a nonce there is a
  kit change for every app;
- hx-boost swaps in each new page's scripts, which then need htmx's
  `inlineScriptNonce` kept in step with the first page's nonce;
- a missed one is a dead button on the live site, while what an injected
  script could reach is small (one collection, Django autoescapes, no `|safe`
  on stored text, the policy above stops it from sending anything out).

### For Tomek

1. **Photos by unguessable name, or behind the session?** Today a photo URL
   works for anyone who has it (a forwarded link, a screenshot of devtools).
   Writing samples show handwriting. Gating `/media/` (nginx `auth_request` or
   `X-Accel-Redirect`) would end that, and would cost the share links' photos
   for strangers once the showcase opens. My reading: keep it as it is while
   the photos are of pens and swatches.
2. **The old `admin` user** still has a usable password hash. No form takes it
   any more (tested), but a leaked database would hand over a crackable hash.
   Its last sign-in, 26 Sep 04:56 UTC, is the same minute as commit 4f56593,
   so an agent at work, not an outsider. `set_unusable_password()` cannot be
   undone, so it waits for a yes.
3. **A strict CSP** needs a nonce in the kit's snippets first: a fleet change.
4. **Left on bae, to delete when you are happy:** `/root/pypen` (the old tree,
   its venv, `db.sqlite3.pre-opt-20261101` — the DB as it was at the move),
   `/root/pypen.service.pre-opt-20261101`, `/etc/nginx/nginx.conf.bak-20261101-pypen4`.
   `/root/pypen/dpypen/db.sqlite3` is now a symlink to the live DB and must
   stay until `vps-db-backup.sh` and `grining-eu-backup.sh` read
   `/opt/pypen/data/db.sqlite3` directly.
