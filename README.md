# pypen

> One of Tomek's tailnet apps. The rules every app follows start at [`~/apps/AGENTS.md`](/home/tgrining/apps/AGENTS.md) — it maps the registry (`~/apps/REGISTRY.md`: host, port, deploy line, backups) and the build kit (`~/apps/kit/README.md`) by topic. This README is only what is particular to this app.

What it is, where it runs and how it deploys: its row in `~/apps/REGISTRY.md`.
The agent notes for this repo are in `CLAUDE.md`.

## Name

One name, **Grining Pens** (kit §4 Fleet UX "Names", PYPEN-9): `pwa.APP_NAME`,
which the context processor hands every template as `app_name`. It is the
manifest's `name` and `short_name`, the apple title, the worker's offline page,
the keyboard layer's `name`, the Install row and the Settings group of the app's
own rows. Tab titles are `‹page› · Grining Pens`; the desk (the home screen) and
the front door are `Grining Pens` alone. Tomek left the choice to the agent:
"Pens" alone was thin in a public browser tab and gave "Pens · Pens" on /pens/,
"Grining Fountain Pens" (21 letters) was cut on a phone tile, which shows about
12. "Bureau" stays as a word in the prose ("No pens in the bureau yet",
"Wander the bureau"); it is not the app's name. A phone that installed the app
before keeps the old tile label until the app is added again (iOS) or Chrome
refreshes the manifest (Android, within a day or so).

## The new version

(PYPEN-11, "Fully implement a new version of pypen /next". Goals: beauty, functionality, statistics, reusing the
kit.) Read as: the whole app again, at the address `/next/`, next to the old one, on the same data, so Tomek can
try it before it takes over. The old page that had that address, Next inking, is now `/pick/`; `/next/?pen=` and
`?shuffle=` land on the new picker, `/next/pick/`. Settings there has "Open this version first" (a cookie per
device: `/dashboard/` 307s to `/next/`, so the home-screen tile opens it) and "Back to the old version".

- **One set of views, two faces** (`items/skin.py`). Everything that reads or writes the collection is the same
  view on both addresses, so a door, an undo, a photo's clean-up lands once. `skin.render` swaps `items/x.html`
  for `next/x.html` under `/next/`; `rehome` in `nextui/urls.py` keeps the view's redirects in the new version.
  The routes are a plain list added to `items/urls.py`, so `tests_doors` walks them too. Cutting over later means
  moving the paths and deleting the old templates.
- **What only the new version shows** is in `items/nextui/`: `enrich.py` (added on the way to a template: a list's
  history from one IN query, never per row), `views.py` (the desk, Stats), `stats.py` (the numbers), `color.py`.
- **Ink on paper.** Page: the bottle (dark) or a white pad (light). Every ink colour and chart sits on a paper
  plate in both themes (`--plate`): a black ink on a dark page vanishes, and real ink colours are data, so they
  are not re-stepped per theme as a chart palette would be. The one loud thing is the swab: a band of the ink's
  sampled colours through an SVG mask (`.swab`). Fonts: Alegreya and Alegreya Sans, self-hosted
  (`static/items/next/fonts`); Alegreya's old-style 1 reads as an I, so its digits come from the sister face.
- **The accent is an ink**: the newest coloured ink on the desk (`nextui/context.py`), lightened or darkened per
  theme to 4.6:1 against both papers (`color.accent`). A black or a grey has no colour to lend; then the next ink,
  then royal blue. A test holds the contrast for any ink.
- **The kit, unchanged**: layer, toast, empty, filters, update, pull to refresh, What's new, install, theme, settings,
  keys, worker. Both shells include the same `_shell_early`, `_shell_filternav`, `_shell_behave`, `_msgs` (cut out of
  the old shell), `deskbar.js`, `charts.js`, `more.js`, `viewer.js`. The palette keeps the old addresses, one list
  for both; `window.__nextUrl` in the new shell maps each to its twin.
- **Five tabs**: Desk, Pens, Inks, Stats, More. Inkings moved behind More to give the charts a place; the desk's
  Finish and New inking are what is used daily.
- **The desk's gauge**: days in against the median of this pen's own ended fills (the collection's while it has
  under two). Past twice that it asks whether to flush the pen.
- **Stats** (no chart library: HTML and SVG from the server, kept four minutes under a key that changes with the data):
  - The river (`stats.river`): pens per ink colour per month, stacked, 16 real colours. The shape is smoothed over three
    months (raw it is all spikes); a finger reads the true month. One colour lights from its key.
  - A year against the last *up to today's date*, so a running year compares fairly.
  - Is each pen earning its keep: price (log) against days inked (root), PLN per day inked.
  - What you own against what you use, per colour; the cupboard's spectrum in OKLCH hue order; never inked; resting longest.
  - Rotation: per priority, how many are on time; how long a full round takes at this year's pace.
  - The calendar is twelve month blocks: the old strip of 53 weeks leaves a phone 6 px a day.
- `CH` in `constants.NATIONALITIES` means both Swiss and Chinese. Stats counts a brand Swiss only if it is
  Caran d'Ache (`stats.SWISS_BRANDS`).
- Probe: `python3 tools/next_probe.py` (DB copy; 390×844, then a desk; it writes, so never the live site).
  Tests: `tests_next.py`.

## Photos found for the pens nobody photographed

(Nov 2026.) 91 of 126 pens had no photo. `manage.py pen_photo_fill` gives each one a catalogue shot, with no
owner input; the owner checks them afterwards.

- **Two halves.** The image search needs `ddgs` (DuckDuckGo images), which the site does not; Gemini's key lives
  only on bae. So: `pen_photo_fill --list` on bae (the pens with no photo, and each one's rejected sources) →
  `tools/pen_refs.py pens.json refs/` on p340 (up to 6 candidate photos per pen, in a venv with `ddgs` and Pillow)
  → copy `refs/` to bae → `pen_photo_fill --refs refs/` there.
- **Per pen:** a text model (`JUDGE_MODEL`, gemini-3.8-flash) sees all candidates and picks the one that shows
  this model in this colour, whole, or none. Then the image model restyles it on the house paper
  (`WEB_REFERENCE_PROMPT`: watermarks, boxes and shop text go). The web photo is `image`, the shot is
  `image_styled`, as with an own photo and its catalogue shot. No fitting candidate: the image model draws the pen
  from its name (`generate_from_name`), and the note says it is not a photo.
- **Every one waits for a check.** `PenPhoto.review` is `""` for the owner's own photos, `"check"` for a found or
  drawn one, `"ok"` once checked. `/next/pens/photos/check/` lists them with Right and Wrong; the pen's page in the
  new version shows the same two buttons under a found photo, and the desk counts them. Wrong deletes the photo
  and its files and records the source in `RejectedPenPhoto` (a drawing as `gemini:text`), so `--list` hands the
  rejects to the next search and the next fill neither offers the same photo nor draws the pen again.
- **Without Gemini credit** (its prepay ran out on 4 Nov 2026 after 49 pens): `--judge claude --no-style` lets
  Claude (`CLAUDE_JUDGE_MODEL`, claude-opus-5-5 at low effort) pick, and keeps the web photo as it is, unstyled and
  never drawn. `pen_photo_fill --restyle` makes the catalogue shot for those later (checked ones too).
  Both Anthropic keys were invalid that day too, so the last 42 were picked by eye from contact sheets:
  `--picks picks.json` (`{"<pen id>": "c3.jpg"}`, the candidate's file, so a reject cannot shift it).
- Only the main shot is made. `pen_photos --pen N` can derive the nib and capped shots from a checked one.
- Tests: `tests_photocheck.py`.

## Filters and search

The kit's `filters.html` (stamp `KIT-FILTERS`), copied byte for byte to
`templates/items/_filters.html` and included by `_shell` and the inks wall: chips, box, sort on
/inks/, /pens/, /usages/, /search/, the Gantt, /pub/inks/ and the menu. Particular to pypen:

- **htmx does the requests.** A chip keeps its `href` and `hx-get`, with `hx-replace-url`, and
  every control of a list has `hx-sync` on the search form, which stays through the swap: a chip
  and a keystroke cannot race for one target. The filter-nav script at the end of `_shell` is the
  joint: it builds the path at request time from the address, drops empties and each field's
  `data-default`, and clears the kit's `aria-busy` when the answer comes.
- **No hidden fields in the search forms**: the form stays outside the swap, so a hidden field
  would go stale. Filter-nav adds what the address holds.
- **/search/ keeps real radio buttons and checkboxes** inside `label.kit-chip`. The label has
  `aria-current` for the kit's look.
- **The List/Grid switch is not a filter**: it keeps its look, and `inksView`/`pensView`.
- `tools/filters_probe.py` walks it in a phone browser, on a copy of the database.

## Inking charts

(PYPEN-10, "ink up history charts etc.".) Read as: charts of the history of ink-ups, how often,
how long, in what, plus small ones where a record has a history. `/history/inkings/` (a tab of
History), `?y=` narrows every chart to a year; `items/inkings.py` computes,
`templates/items/history_inkings.html` draws, `static/items/js/charts.js` answers.

- **An ink-up counts on the day it began.** A fill over New Year counts once. The one chart of
  days, "Pens inked at once", still sees a fill from the year before.
- **Sixteen ink colours fold into eight families in a stack** (`FAMILIES`, `.fam-*` in `app.css`, a
  step per theme, checked with the dataviz validator against both papers): a 20 px column of 16
  real ink colours is mud, and four of them are near black. "Colours" lists the 16 as they are.
- **No chart library**: HTML columns and one SVG line, from the server. Nothing waits for a script
  to draw; the script gives the tips, the line's reading and the key.
- **One tip** (`charts.js`, any `data-tip-title`): hover on a desk; a tap stays, as a kit layer, so
  Back, Esc and a tap elsewhere close it. The calendar's day and the matrix's cell use it too: they
  were mouse-only `title`s, a tap on a matrix cell left the page. Stored names go in as text.
- **See them**: a mark opens `/usages/?began=2024-08` (or `2024`), a colour `?color=Blue`, exact, so
  Blue is not Blue Black. `crud.usage_scope`; `/api/usages` takes them too; a wrong value is no filter.
- **A pen's and an ink's page** have `_year_bars.html`, signed-in only, from two years up.
- **History's cache key carries a stamp of the inkings** (`history._stamp`): the cache is per worker,
  so a new inking used to take up to 4 minutes to show, depending on the worker.
- Probe: `python3 tools/charts_probe.py` (DB copy; 390×844, then a desk). Tests: `tests_inkings.py`.

## Theme

The kit's `theme.js` (stamp `KIT-THEME`), copied byte for byte to
`dpypen/dpypen/items/templates/items/_theme.js` and inlined by
`templates/items/_theme_boot.html` (via the `kit_theme_js` tag, because the
snippet's header comment holds an `{% include %}` that the template engine
would run) into all four full pages: `_shell`, `landing`, `pens/wall`,
`inks/wall`. Key `pypenTheme`; the old `theme` key is read once.

- **Default `auto`, not the fleet's dark**: the site is public and its design is
  paper (cream page, navy ink), so a visitor's first view follows their system
  and is light on a light phone.
- The walls keep their one-tap sun/moon toggle in the header (they have no
  Settings row); it calls `kitTheme.set(…)`, so the choice is the same one.
- Their dark header colour is `#0a0907` (passed as `theme_dark`), the shell's
  `#13161c`; light is `#f4ecd8` everywhere.

## Settings

`/settings/` is the kit's grouped rows (kit README §4 "Settings", stamp
`KIT-SETTINGS`, BURNLOG-7): `kit/snippets/settings.html` copied byte for byte to
`dpypen/dpypen/items/templates/items/_settings.html` and included inside
`#main`, so an hx-boost swap brings its style along; the page script calls
`kitSettings.mount(main)` and `kitTheme.mount(main)` after each swap. Groups:
Look (Theme, Install "Grining Pens"), Grining Pens (What's new), Keyboard (Keys, and a closed row with what
"m only" is for), Account (Admin, Sign out) — or Visiting (Leave) for a guest.
`app.css` maps the kit's colour names onto the paper (`.kit-set`).

- **No "p340 — all apps" row**: the site is public, the tailnet index is not.
- **Sign out is a POST** with the CSRF token (it was a GET link), so no other
  page can sign the owner out; it still tells the worker `KIT_FORGET`.

## Install nudge

(PYPEN-5.) The kit's bar (`_install.html`, kit README §4 "Install") in this app's paper
(`app.css`), included through `templates/items/_installbar.html` by the shell for the owner and
guests only, so a stranger (the front page, the public cupboard, a wall) never meets it.
State in `localStorage['pypenInstallNudge']`.

- **No "second day of use" rule** (`days: 1`; the kit's default is 2): a guest on an
  invitation may come only once.
- Shell pages only: the walls stay standalone public pages without it.
- `?installdemo=1` shows it at once (screenshots). Test: `kit/snippets/tests/test_install.py`.

## Photo viewer

(PYPEN-1.) A pen's photos, an ink's swatches and the writing samples open full
screen on a tap: pinch, wheel or double-tap to zoom, drag to look around, ‹ ›
or a sideways swipe through the group, a flick down, ✕, Back or Esc to close.
It is the museum's lightbox (`~/museum/museum/static/base.js`, "pinch-zoom
lightbox") cut down, in `static/items/js/viewer.js`, loaded by `_shell.html`.

- **Markup only**: a page marks a photo `data-zoom` and its group
  `data-zoom-group` / `data-zoom-item`; the header of `viewer.js` has the rest.
  No page script, so an hx-boost swap needs nothing.
- **A kit layer** (`kitLayer.open`, a modal `<dialog>`): Back closes it and
  never leaves the page, and the kit sets `html.scroll-lock` under it. pypen
  has no lock code of its own: since KEYS-LAYER v1.3 (PYPEN-8) the keyboard
  palette and `?` sheet are kit layers too, so the shell's old scroll-lock
  watcher is gone.
- The page's own image shows at once, the stored file (up to 2400 px; new uploads ≤ 1800, `PHOTO_MAX_SIZE`)
  replaces it in place.
- A writing sample no longer links to the fill's edit form (a guest met a
  sign-in page there); the owner gets a pencil on the tile instead.
- Probe: `python3 tools/viewer_probe.py` (throwaway DB copy, made-up photos).

## Pictures at the size drawn

(PYPEN-3, kit §5.6.) A page draws a WebP copy, the viewer opens the stored
file. `items/sized.py` over the kit's `webp.py` (byte copy, KIT-WEBP):
`sized.url(field)` gives `/media/sized/1200/<stored name>.webp`, made on first
use and kept, or the stored file's url when no copy is smaller or the file is
not on disk. `PenPhoto.page_url` (the pen page's photo and its thumbs' swap)
and `tile_url` on a swatch or a writing sample use it; `full_url` /
`shown_url` stay what the viewer opens (`data-zoom`, `data-zoom-src`).

- **1200, not the ~900 the ticket guessed**: the kit's edge is CSS px × 3; the
  frame is ~360 CSS px on a phone, up to ~560 on a desk at 2×. On the live
  photos that is 16–29 KB against the stored 254–299 KB JPEG.
- **Samples and swatches too**: one tile to a row on a phone, so ~360 px wide;
  they drew the whole stored file before.
- **Grids keep their 600 px JPEG twins** (`grid_url`): already at the size a
  tile draws.
- `manage.py sized_copies` (the deploy runs it as `pypen`) makes the copies
  ahead and removes those whose photo is gone. A stored file is never
  rewritten under its name (a turn or an edit saves a new random name), so a
  copy never goes stale under nginx's `immutable`.

## Shared page pieces

(PYPEN-3.) One copy of each, so a fix lands once:

- **Share** (`static/items/js/share.js`, loaded by the shell): any
  `data-share-url` button. The phone's share sheet; on a desk the clipboard and
  the kit toast "Link copied"; else a prompt. It listens on the document, so a
  swapped page needs nothing.
- **Record pages** (`app.css` "Record pages"): `.back-link`, `.history-row`,
  `.samples-strip`, `.swatch-grid`; each detail page keeps only its own layout.
- **Walls**: `templates/items/_wall.html` + `static/items/css/wall.css`; a
  wall fills the blocks and keeps its tile's CSS. They get the shell's icons
  and the kit's update toast and pull to refresh, but no shell: they stay
  public, standalone, linked with `hx-boost="false"`.
- **No fixed `style=""`**: a fixed look is a class in `app.css`; inline stays
  only what the server knows per item (an ink's colour, a width in %).
  `tests_sized.NoFixedInlineStyle` holds it.

## Lists

(PYPEN-7, kit §14.) Everything that grows with use comes from the server 50
rows at a time, with **Load more** under it: `/pens/`, `/inks/` (and the
public `/pub/inks/`), the past inkings on `/usages/`, `/search/`. The kit's
`lists.py` (byte copy, KIT-LISTS) does the words, the accent fold, the limit
check and the highlighter; `items/listing.py` is the Django side.

- **Search**: every word must be in some field, accents fold ("zur" finds
  "Zürich"), `%` and `_` are plain text. The fields are defined once in
  `listing.py` (`PEN_FIELDS`, `INK_FIELDS`, `USAGE_FIELDS`) and used by the
  pages, `/search/`, the palette and the JSON. A field through a foreign key
  is a correlated subquery, so the WHERE stays plain. A match on where a pen
  or ink came from shows "from …" in its row, so a row is never there for no
  visible reason.
- **Groups**: a pen's rotation group and an ink's colour are ordinals in SQL,
  so paging keeps the order; the headings' and chips' counts come from one
  grouped query over the same filter (with a search, the ink chips count what
  matches). A page that starts inside a group gets no second heading;
  `static/items/js/more.js` puts its rows under the group above.
- **The desk** (inkings not ended) is not paged: there are never more than
  there are pens. It shows on the first page only.
- **`/search/`** shows 20 pens and 20 inks; Load more goes on with that kind
  alone (`type=pens`). "Most used" counts the inkings (it summed their ids).
- **JSON**: `/api/pens`, `/api/inks`, `/api/usages` (`state=active|past`),
  owner and guests, the same parameters and code as the pages, answered as
  `{"items", "total", "limit", "offset"}`. `?limit=` over 100, a negative or
  a non-number offset: 422, page or JSON (`listing.ListErrors`).
- **State in the URL**: `?q=&rot=&color=&sort=&view=&offset=`. Load more does
  not change the address (Back and htmx's history snapshot keep the rows); a
  link to `?offset=50` opens that page with "From the start". A new filter,
  sort or search drops `offset`.
- **Load more, not page numbers**: no list here is one a person jumps into the
  middle of; the inkings had numbered pages of 40 and lose them.
- Query count per page does not grow with the rows (`tests_lists.QueryCount`).
- Probe: `python3 tools/lists_probe.py` (backup copy, 390×844).

## Desk bar and header row

(PYPEN-6, kit §4 Fleet UX "Desk" and "Header".) From 900 px the chrome is one
52 px bar, `#hdr` in `_shell.html`: the brand, the tabs (Desk, Inkings, Pens,
Inks, History, Records), then Filter ▾, ⌕ and ⋯. Below 900 px it is the bottom
tab bar (it was below 720; the old 720–899 pill nav is gone, and with it the
floating menu button that showed on scroll).

- **One markup, no move**: `_tabbar.html` is included once, inside `#hdr`.
  `app.css` "Desk bar" draws it as the bar's tabs (its More button, wearing ⋯,
  absolute at the bar's right end; `.desk-tab` History and Records shown only
  there) and below 900 px gives `#hdr` no box, so the bar is the fixed tab bar
  of `tabbar.css`. Taken over pod's way (a script moves the nav in): nothing
  waits for a script, so the first paint has its tabs, and htmx's history
  snapshot cannot catch a half-moved bar. Nothing may give `#hdr` a
  transform, filter or backdrop-filter: the fixed tab bar and the popovers
  would be measured from it.
- **Filter ▾** (`static/items/js/deskbar.js`): a page marks its chip row
  `data-fold="<name>"` (the pens' rotation, the inks' filters). On a desk the
  row hides and the button opens the same chips in a popover; a chip there
  clicks the real one, so htmx, the URL and the filter-nav sync work as on a
  phone. The button names what is on ("Priority 1", "Used-up · Blue Black").
  Without the script the row stays in the page.
- **⌕** opens a popover with the menu's search field, lent while it is open.
- **⋯** is the menu, under the bar, without the places the bar has as tabs
  (`data-tab`) and without its search. A guest's name and Leave are in the
  menu now, on a phone too (they were in the pill nav only).
- All three are kit layers, `lock: false`: Back, Esc and a click outside close
  them, the page keeps scrolling.
- **A record's verbs** (a pen, an ink): on a desk the `⋯` panel is a row of
  labelled buttons (Suggest an ink, Edit, Share, Delete with its confirm).
- 900–1099 px: the brand is its mark alone, so the tabs and a named filter fit.
- A stranger (an error page, a shared pen) has no tab bar: the bar has the
  brand and ⋯, a phone has the corner button.
- **Header row** (`.page-head.hrow`): Desk, Pens, Inks and Inkings open with
  their title and one line of what they hold and how fresh, from
  `items/shelf.py` (a lazy context value: a page that does not print it runs
  no query): "126 pens · 3 inked · last inked 2 mo ago". The numbers are the
  collection's, not the filter's (the list's "1–50 of N" counts matches); the
  freshness is the newest inking. At most two icon buttons: Pens has Needs a
  photo and Add, Inks Share and Add, the Desk Needs a photo (a count badge;
  it was a fourth clause that wrapped the line) and New inking; Inkings keeps
  its two labelled verbs. The public ink cupboard prints no numbers.
- Probe: `python3 tools/desk_probe.py` (DB copy; 1440 px, a narrowed window,
  390×844).

## Kit pieces

`AUDIT.md` "Kit adherence" walks `~/apps/kit/README.md` section by section
(PYPEN-2). Byte copies, all in fleet-check `kit`: `_layer.js`, `_toast.html`,
`_settings.html`, `_theme.js`, `_sw.js`, `_update.html`, `_pullrefresh.html`,
`_whatsnew.html` (templates) and `errors.py`, `whatsnew.py`, `webp.py`,
`lists.py` (items/). `_keys.html` is in fleet-check `keys` (stamp only: it carries its
own CONFIG).

- **New version**: the worker takes over at install (`takeover`), so the
  update toast polls `build`: the page's `kit_build` (context processor
  `pwa.build_context`) against `GET /api/version` (open, `no-store`). Both are
  the worker's hash of the code, templates and static files.
- **Pull to refresh**: in the shell and both walls. The walls no longer set
  `overscroll-behavior: none` (the snippet switches the browser's pull off).
- **What's new**: `items/whatsnew.json`, newest on top, served by
  `pwa.whatsnew` (owner and guests, like the pages). Opened from Settings →
  Pens → What's new and the palette (`#whatsnew`, handled in `window.__go`);
  the dot sits on More (the desk bar's ⋯) and Settings in the menu.
  Shots in `static/items/whatsnew/`. A `data-new` id must be in the file
  (`tests_kit.py`).
- **Error pages** (`items/error_pages.py`): Django's `handler404/403/400`
  and `CSRF_FAILURE_VIEW` give `items/error.html` in the shell with Back and
  the desk (a stranger: the front page); `/api/`, the JSON files, `/static/`,
  `/media/` and a `fetch()` get `{"detail"}`. The 500 page needs no database
  and no static manifest. htmx swaps no 4xx/5xx, so the shell's
  `htmx:beforeSwap` takes these pages for a boosted navigation.
- **Icons**: committed PNGs in `static/items/icons/` (192, 512, 512
  maskable, 180 apple-touch), drawn from the SVGs in `pwa.py` with
  `rsvg-convert`. iOS takes only a PNG apple-touch-icon.
- Probe: `python3 tools/kit_probe.py` (DB copy, DEBUG off, 390×844 touch).

## Security

`AUDIT.md` holds the model (one owner, guests read, strangers see the door;
photos private by a 128-bit name) and every finding with its fix and test.
In short:

- **On bae** it lives in `/opt/pypen` and runs as user `pypen`: the code and
  the venv are root's, it writes only `/opt/pypen/data` (the DB) and
  `/var/www/pen-media`. `deploy/pypen.service` is a copy of the unit.
  `deploy-code.sh` installs `requirements.txt` when it changes and runs
  `migrate` as `pypen`.
- **Headers** (`items/security.py`): a CSP that allows inline script (why not a
  nonce: `AUDIT.md`), Permissions-Policy, `Cache-Control: private` on every
  signed-in or guest page, and `Clear-Site-Data` on Sign out and Leave.
- **Uploads** go through `models._process_image`: a file Pillow cannot read is
  named and skipped (`BadImage`), over 50 MP is refused, EXIF never survives.
- **Tests**: `tests_security.py` (and `tests_doors.py` for every route).
