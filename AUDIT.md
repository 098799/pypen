# pypen — audit

## UX pass (10 Nov 2026, burn p11102208)

**How.** The live site, read only (an owner session made on bae for the walk, writes refused in the page), headless
Chromium: 38 screens × phone 390×844 and desk 1440×900 × light and dark = 152 shots, plus a full-page phone shot of
each, and per screen: status, load time, tap targets under 40 px, text under 11 px, sideways scroll, page errors.
The flows that write (finish, new inking, Ink next, add pen/ink with empty fields, delete's confirm, Back to a
filtered list) on a copy of the newest backup on a spare port; offline on the live site with the worker on. Three
reviewers read the shots and the templates in parallel (desk + pens, inks + inkings + forms, stats + turns).
Shots: `shots/before/<mode>-<screen>.png` and `full-<screen>.png`, flows `shots/flows/`, in the job's scratchpad.

**Numbers.** Every screen 200 (404 for the two dead addresses), DOM ready 0.07–0.63 s, idle 0.57–1.17 s over the
internet; no page error, no failed asset, no sideways scroll on any screen in any mode. Text under 11 px: one chart
(7 labels at 10.9 px). Contrast of the greys: 5.5–6.3:1 light, 5.6–7:1 dark; charts sit on paper in both themes.
Taps: "finish a fill and ink the pen again" took ~7 taps + typing (Finish sent you to the inkings list); "Ink next"
from the desk takes 2 (tap the ink, Ink it); "add a pen with a photo" ~6 + a search.

Severity: **High** = a main task blocked, broken, or a chart that says the wrong thing; **Med** = friction or a kit
rule broken; **Low** = polish. Status at the end of the pass in the last column.

| # | sev | screen | finding (evidence) | fix | status |
|---|---|---|---|---|---|
| U1 | High | desk, pen | **Finish leaves the page**: always to the inkings list (behind More), so finishing and inking again was ~7 taps; Edit of a fill also ended on the list (`f1-after-finish.png`; `crud.usages_end`) | back to the page it came from (`backto.py`): the desk stays the desk, the pen's page then offers Ink this pen | |
| U2 | High | pen, ink | **The pen page is wider than a phone**: the hero grid's one auto column grows to the thumbnail strip (6 × 74 px), so the photo, "Share" and the numbers are cut at the right edge on every pen with 5+ photos (`phone-light-pen.png`; `next.css .rec-hero`) | `minmax(0, 1fr)` | |
| U3 | High | pen-add, ink-add | **No way to add a new brand**: Brand is a plain select and nothing outside the admin makes one (`full-pen-add.png`, `full-ink-add.png`) | "New brand" name + country on both forms | |
| U4 | High | inking-edit, ink | **The inking form leaves out used-up inks and samples** (≤ 5 ml): an old inking of a used-up ink cannot be saved (its ink shows "— choose —"), "Use this ink" on a sample opens an empty Ink field, a sample cannot be inked (`forms.UsageForm`) | keep the inking's own and the asked-for ink; used-up and samples in a lower group | |
| U5 | High | pen-add, ink-add, edits | **Add and Save land on the list** (127 pens, 98 inks), so the next step (a photo, a swatch, an inking) starts with a search; Save on an edit whose Back says "Back to the pen" went to the list too | Add and Save land on the record's page | |
| U6 | High | stats-rotation, supen | **Two answers to "past their turn"**: Rotation counts a pen over at 1× its turn (12 of 14 P0 "past"), supen at 5/4 (4 of 14), with the same words (`full-stats-rotation.png`, `full-supen.png`) | one rule (supen's, the owner's terminal command) | |
| U7 | High | stats-collection, stats-cupboard | **Year columns unreadable on a phone**: 21–22 columns of ~15 px, every label and value printed, so they run together (`'06'07'08…`, `117123123125…`) | label every 5th year when crowded, a value on the peak and the last only | |
| U8 | High | pen-edit, inking-edit, ink-edit | **"Take or choose a photo" cannot choose**: `capture="environment"` opens the camera only on iOS and Android, so a photo already in the library cannot go in | no `capture` on the edit pages (the needs-photos queue keeps it: it is a camera session) | |
| U9 | High | stats-pairs | **The matrix says "a darker square held ink longer" but the darkness is the ink's own colour**: a pink pair at 284 d is paler than a black one at 40 d (`desk-light-stats-pairs.png`) | one neutral ramp for the days; the ink's colour stays on the column dot | |
| U10 | Med | pens, inks, inkings | **Back to a filtered list empties the box**: the list stays filtered by "pilot", the box is blank, so the user does not see why (`f6-back-to-list.png`) | filter-nav fills the box from the address | |
| U11 | Med | pen-edit, ink-edit, inking-edit | Choosing a photo, swatch or sample posts at once and **throws away unsaved edits** above it | the picker warns and saves nothing while the form has changes | |
| U12 | Med | desk | **Ink next is ~2,000 px down** on a phone, under 7 fill cards of ~290 px (`full-desk.png`, 3,247 px) | compact fill cards on a phone | |
| U13 | Med | settings | **Sign out at 2.77:1** in light: `.kit-set { --bad: var(--bad) }` is a loop, so the kit's dark red is used | drop the line | |
| U14 | Med | pen-add, ink-add | Required fields unmarked; Filling and Colour say `---------`; "Bought from" required for a present; How it came has no default; Obtained no default (`full-ink-add.png`) | mark optional fields, `— choose —`, today and Bought by default | |
| U15 | Med | inking-add | No checks: Finished before Inked gives negative days; a pen already inked can be inked again with no word | `clean()`; the pen picker names a pen's open fill | |
| U16 | Med | desk, inkings, pick, ink, pen-edit | Tap targets under 44 px on the daily buttons: Finish/Edit 40 px on the desk, `is-small` 36 px (inkings, Ink it), photo tile buttons 36 px | 44 px | |
| U17 | Med | pens | In a pen row only the 23 px name opens the pen (52 small targets on the page) | the whole row is the link | |
| U18 | Med | ink | The ink page's h1 is "Black" (4 inks are "Blue Black"); Delete sits next to Edit and takes the inkings with no undo | h1 = brand + name; Delete with an Undo | |
| U19 | Med | supen, suink | Cut off from Stats (More lit, the way back at the end of a 6,000 px page); "Since" is raw days (`2164`); state by colour alone, the key at the bottom | a Turns chip in the Stats strip, Stats lit; days as ages; the key on top, a word for late | |
| U20 | Med | stats-collection | The scatter clamps the 5–6 PLN pens to x = 0, a dozen dots on one spot; ticks only from 50 | the true minimum and ticks at 10, 20 | |
| U21 | Med | stats-inkings | Rows print `63 2999 d` (two numbers, no word); 7 labels at 10.9 px; the heatmap is 960 px tall on a desk | `63 fills · 2,999 d`; short labels at 0.8 rem; a capped heatmap | |
| U22 | Med | stats, collection, cupboard | Three bar charts print no number at all | a value on the peak and the last bar | |
| U23 | Med | stats-calendar | 14 px days, no weekday heads, no mark for today | weekday heads, today ringed | |
| U24 | Med | import | Any failure says "Try again, or with a sharper photo", also when the API key is refused | say the reading is off when the key or credit fails | |
| U25 | Med | pens, needs-photos | Polish failing (Gemini credit empty since 4 Nov) is silent: the photo is saved unpolished, the toggle still promises it | a warning toast | |
| U26 | Med | offline | A tab tapped offline to a page never opened lights that tab and leaves the old page under it | | |
| U27 | Med | all | No kit header (`KIT-HEADER`): the page heads are the app's own, not sticky, h1 26–32 px; on a desk the bar has a `backdrop-filter` blur the kit forbids | | |
| U28 | Med | pen, ink, forms | Back links are plain links to the list, so a search, filter and place are lost (kit: back in history) | | |
| U29 | Med | inks | The sort select reads "Colour ▾" right above the colour chips, a filter look; toolbar ~190 px | | |
| U30 | Med | pick | Changing the pen is ~1,300 px down; "P0" jargon | | |
| U31 | Med | cupboard, timeline | Spectrum links 3 × 92 px, timeline bars 2 px: untappable | | |
| U32 | Low | desk, pens | "+" is New inking on the desk, Add pen on Pens; the camera badge only on the desk | | |
| U33 | Low | pens-search | The title stays "126 pens" while 8 show; no-match keeps a lone "All 0" chip | | |
| U34 | Low | desk-wide lists | Rows 1,130 px wide on a desk: buttons ~950 px from the name (pens, inkings, needs-photos, supen) | | |
| U35 | Low | photo-check | Says the empty answer twice; its button goes to All pens, not to the 23 that need a photo | | |
| U36 | Low | e404 | A missing pen gets the generic 404; Back does nothing on a pasted link | | |
| U37 | Low | import | "Read it" active before a photo is chosen | | |
| U38 | Low | stats | Small stacked bars look striped; the river has no scale; cupboard dumbbells no values; pairs names cut | | |
| U39 | Low | desk | The gauge's notch at 50 % and "P0" in Then are not explained | | |


## Kit adherence (PYPEN-2, 1 Nov 2026)

`~/apps/kit/README.md` walked section by section against pypen. Each row:
**ok** (conforms), **fixed** (in this pass), **own** (deliberately different,
with the reason), **gap** (a ticket). Before this pass fleet-check `kit` knew
four copies (toast, layer, sw, settings) + theme.js; now nine, all byte equal.

### §1–§3: shape, fetching, auth

| kit | pypen | verdict |
|---|---|---|
| §1 FastAPI + Jinja, `app/` layout, stdlib sqlite | Django 5 + Django ORM, `dpypen/`, gunicorn on bae | own: the app predates the kit (2020); a rewrite buys nothing |
| §1 self-contained, no CDN | htmx and tom-select vendored, fonts self-hosted | ok |
| §2 anything that fetches | only the AI calls (notebook import, enhance), behind the owner | ok |
| §3 gate.py / sameorigin.py / harden.py | Google sign-in (allauth) + Django CSRF + `security.py` (no framing, CSP, nosniff, referrer) | own: the kit names pypen as the Django exception; same four headers on every answer, errors too |

### §4: phone-first UI and the Fleet UX table

| row | pypen | verdict |
|---|---|---|
| system fonts | EB Garamond / Cormorant / Inter, self-hosted | own: the paper look is the app |
| `viewport-fit=cover`, safe area | yes, tab bar padded | ok |
| Header (≤ 56 px, what the screen answers + freshness, ≤ 2 icons) | no app header: each page's own heading, a menu button that tucks away | **fixed** (PYPEN-6): Desk, Pens, Inks and Inkings open with a header row, title + "126 pens · 3 inked · last inked 2 mo ago", ≤ 2 icon buttons; the tucking button is gone. README "Desk bar and header row" |
| Bottom nav (3–5 tabs, ≥ 56 px, labels ≥ 11 px) | 5 tabs, icon + label, More | **fixed**: 54 → 56 px, labels 9.9 → 11 px |
| Settings (grouped rows, kit settings.html) | kit copy v1.2; Look, Pens, Keyboard, Account | ok; Settings sits behind More, not as the last tab: the five slots are Desk, Inkings, Pens, Inks, More (own) |
| Theme (kit theme.js) | kit copy; default auto | own: public site on paper, README "Theme" |
| New version (update.html) | none: the worker takes over at install, nothing told an open page | **fixed**: kit copy, `build` against `/api/version` |
| Toast (toast.html) | kit copy v1.2 | ok |
| Pull to refresh (pullrefresh.html) | none: an iPhone home-screen app could not reload | **fixed**: kit copy in the shell and both walls; the walls' `overscroll-behavior: none` removed (the kit forbids it) |
| Install nudge | Settings row only | **fixed**: PYPEN-5, museum's `#installbar` in `_installbar.html`, owner and guests |
| Desk (≥ 900 px, one 52 px bar) | pill nav inside the page + floating menu | **fixed** (PYPEN-6): brand, six tabs, Filter ▾, ⌕, ⋯; the tab bar's markup, drawn by CSS (no script moves it); anchored popovers, no dim; a record's verbs as labelled buttons |
| Keyboard (§6) | kit keys.html v1.2 | ok, see §6 |
| Offline (sw.js) | kit copy v1.3, `where: internet` | ok |
| 404 / errors | Django's bare "Not Found"; a boosted dead link did nothing | **fixed**, see §5.7 |
| Icons (PNG 192 + 512 + maskable, `"id": "/"`) | SVG only; the iPhone home-screen icon was an SVG link, which iOS ignores | **fixed**: committed PNGs, PNG apple-touch-icon, `id` |
| Names (one name) | "Grining Pens" everywhere: manifest, tile, titles `‹page› · Grining Pens`, offline page, keys, Install row (`pwa.APP_NAME`) | ok: PYPEN-9 |
| Between apps | a public app on bae, not in the tailnet index | n/a |
| Dialogs & sheets (layer.js) | kit copy v1.5: menu, ⋯ panels, gantt popup, viewer | ok; since PYPEN-8 the keyboard palette and `?` sheet are layers too (KEYS-LAYER v1.3), see §6 |
| What's new | none, though main-tier and growing | **fixed**: kit copy + whatsnew.py, `whatsnew.json` (photo viewer, pull to refresh), Settings row, palette, dot on More |
| Login | Google sign-in (allauth) | own: gate.py is for token apps |

### §5: the things that always break

| kit | pypen | verdict |
|---|---|---|
| §5.1 soft navigation (softnav.html) | htmx `hx-boost` into `#main` | own: works, with its own hooks (filter URLs, tab state, menus); swapping it is a rewrite of every page script |
| §5.2 overlay layering | kit layer | ok |
| §5.3 `no-cache` on every HTML answer | only `private` on a visitor's page, nothing on the landing page | **fixed**: `no-cache` on every page (`security.py`) |
| §5.3 hashed assets | Django's manifest storage | ok (own mechanism) |
| §5.4 HEAD | Django answers HEAD for GET | ok (checked live) |
| §5.5 SQLite threads | Django | ok |
| §5.6 pictures at the size drawn (webp.py) | the pen page ships the stored 1800–2400 px JPEG | **fixed** (PYPEN-3): kit copy, 1200 px WebP copies, README "Pictures at the size drawn" |
| §5.7 errors.py | — | **fixed**: kit copy for `describe()` / `wants_page()`; `items/error_pages.py` behind `handler404/403/400/500` and `CSRF_FAILURE_VIEW`: a page in the shell with Back and the desk (a stranger: the front page), JSON for a fetch, `/api/`, the JSON files and `/static/`; the 500 page needs no database; the shell swaps an error page in for a boosted link |

### §6: keyboard layer

`_keys.html` is the kit's KEYS-LAYER v1.2 (the current one; fleet-check
`keys` ok). The diff against the canonical file is the CONFIG block, the SHEET
table, the token map at the top of the style and the Django header, as §6
allows — and two lines outside them: the palette's placeholder and the `?`
sheet's line naming `~/apps/kit/KEYS.md` (a path shown on a public site).
This pass added the palette entry "What's new".
**Closed by PYPEN-8 (2026-11-01):** KEYS-LAYER v1.3 makes the placeholder
`CONFIG.placeholder` and pypen drops the KEYS.md line; `tests_scroll_lock.py`
`KeysCopy` now fails if the shared code differs from the kit's.

**The shell's scroll-lock watcher stays, changed.** The kit's keys.html
opens its palette and `?` sheet itself (class `on`), not through kitLayer, so
nothing else locks the page under them. It used to compute the lock from a
list (`#kpal.on,#khelp.on,dialog.pv[open]`) and so cleared the kit's lock a
microtask after the kit set it for any layer not on the list (PYPEN-1 had to
add the viewer). It now counts every `dialog:modal` too: the viewer and the
What's new log need no line, and a new modal layer cannot be forgotten. The
real fix is the kit's (keys.html v1.3 through kitLayer, copied to five apps):
PYPEN-8, which then removes the watcher. **Done 2026-11-01 (PYPEN-8):** the
palette and the `?` sheet are kit layers (Back closes them, the kit locks the
page), and the watcher is gone; `tools/layer_probe.py` and `live_walk.py`
check both.

### §7–§14

| kit | pypen | verdict |
|---|---|---|
| §7 units, vhost, backups | bae: `/opt/pypen`, user `pypen`, its own unit; DB in the nightly backup | own (public app on bae), REGISTRY row |
| §8 `ship` | `deploy/deploy-code.sh`: tests gate, rsync, migrate, collectstatic | own (bae), as the kit allows |
| §9 `/healthz` | none | own: the kit lists pypen as "Django on bae, not watched" |
| §10 verifying | `tools/layer_probe.py`, `viewer_probe.py`, `kit_probe.py`, `lists_probe.py` on a DB copy | ok |
| §11 public | HSTS, CSP, secure cookies, `limit_req`, HTML 404 (now), HEAD, `robots.txt` (noindex) | ok |
| §12 sharp edges | tests on a throwaway DB, probes on a copy | ok |
| §13 README | numbers, decisions | ok |
| §14 lists | `lists.py` byte copy (fleet-check `kit`); pens, inks, inkings, /search/ paged 50 with Load more, `/api/pens|inks|usages` in the envelope, kit words and highlighter (PYPEN-7) | ok; pages, not page numbers: no screen needs a jump |

### Reading taken

The ticket says "fix what is cheap". Taken as: every kit snippet pypen did not
carry and could carry unchanged (update, pull to refresh, What's new, errors),
the small conformance numbers (tab bar, icons, `no-cache`), and the watcher.
Not cheap, so tickets: anything that changes how the screens are laid out
(desk bar, header, install bar), the list API, the name, and a change to a
canonical kit file that five other apps carry.

### Reuse pass (PYPEN-3, 1 Nov 2026)

What pypen carried twice, or by hand where the kit has a piece:

| what | before | now |
|---|---|---|
| kit `webp.py` | none; the pen page drew the stored JPEG | byte copy, in fleet-check `kit`; `sized.py` |
| kit `theme.js` | byte copy, but fleet-check did not compare any app's copy | `theme.js` in `KIT_SNIPPET_COPIES`: 19 copies, all equal |
| share script | pasted in the pen page, the ink page and the inks list; on a desk it wiped the list's icon button | `share.js`, once |
| samples strip, history rows, back link | a copy in each record page; the photo editor and Settings used `.pen-back` with no style at all | `app.css` |
| the walls | two standalone pages, same head, header, toggle, script, ~200 lines of the same CSS | `_wall.html` + `wall.css`; plus the update toast they lacked |
| fixed `style=""` | 74 in 18 templates | 0, and a test |

Every other kit snippet pypen can carry it carries (the table above). Not
carried, by decision: `softnav.html` (§5.1 own), `gate.py` / `sameorigin.py`
/ `harden.py` / `head.py` / `healthz.py` / `caching.py` (Django does each:
the §1–§3, §5 and §9 rows above). `lists.py` came with PYPEN-7 (§14).

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

### Third look (1 Nov 2026, burn p11011220)

A fresh read of the code paths the first two passes did not name: the
redirects, the search marks, the sessions in the database.

| finding | fix | pinned by |
|---|---|---|
| Undo checked its way back with `startswith("/")`. `/\evil.example` passes that, and browsers read it as `//evil.example`. The toast's form sends no `next`, so the way back is the Referer, a full URL: the check refused every one, and **every Undo landed on the dashboard** instead of the page it was pressed on. | Django's `url_has_allowed_host_and_scheme` against this host: back to the page, never off the site. | `UndoBringsItBack` (3 new) |
| A closed page sent the stranger to `/accounts/google/login/?next=<path>` with the path not quoted: a `&` in it ended `next`, and the rest (`process=connect`, …) became allauth's own parameters. | `redirect_to_login`, which quotes it. | `TheWayBackIsQuoted` |
| The search marks (`highlight`) matched in the escaped text, so "lt" or "amp" hit `&lt;` or `&amp;` and cut the entity: `&<mark>lt</mark>;` on the page. Not a way in (the terms never reach the markup unescaped), but broken text. | Match in the stored text, escape each piece. | `SearchMarksDoNotCutEntities` |
| Nothing ever ran `clearsessions`. The live DB held 498 sessions, 443 of them expired, back to Nov 2020, and each nightly copy on p340 carried them all. | The deploy runs `clearsessions` (as `pypen`). | — |

Checked and fine: `SOCIALACCOUNT_LOGIN_ON_GET` lets any page start a
Google sign-in, which only ever signs in the allowlisted owner as themself
(it is what the `LOGIN_URL` redirect needs). `socialaccount_socialtoken` is
empty: no Google token is kept. The nightly backups still arrive through the
`/root/pypen/dpypen/db.sqlite3` symlink (`pypen-7.db`, 1 Nov 00:20).
`admin.py`'s two `mark_safe` calls hold a number and a token the app made.

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
