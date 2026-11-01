# pypen

> One of Tomek's tailnet apps. The rules every app follows start at [`~/apps/AGENTS.md`](/home/tgrining/apps/AGENTS.md) — it maps the registry (`~/apps/REGISTRY.md`: host, port, deploy line, backups) and the build kit (`~/apps/kit/README.md`) by topic. This README is only what is particular to this app.

What it is, where it runs and how it deploys: its row in `~/apps/REGISTRY.md`.
The agent notes for this repo are in `CLAUDE.md`.

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
Look (Theme, Install "Pens"), Keyboard (Keys, and a closed row with what
"m only" is for), Account (Admin, Sign out) — or Visiting (Leave) for a guest.
`app.css` maps the kit's colour names onto the paper (`.kit-set`).

- **No "p340 — all apps" row**: the site is public, the tailnet index is not.
- **Sign out is a POST** with the CSRF token (it was a GET link), so no other
  page can sign the owner out; it still tells the worker `KIT_FORGET`.

## Photo viewer

(PYPEN-1.) A pen's photos, an ink's swatches and the writing samples open full
screen on a tap: pinch, wheel or double-tap to zoom, drag to look around, ‹ ›
or a sideways swipe through the group, a flick down, ✕, Back or Esc to close.
It is the museum's lightbox (`~/museum/museum/static/base.js`, "pinch-zoom
lightbox") cut down, in `static/items/js/viewer.js`, loaded by `_shell.html`.

- **Markup only**: a page marks a photo `data-zoom` and its group
  `data-zoom-group` / `data-zoom-item`; the header of `viewer.js` has the rest.
  No page script, so an hx-boost swap needs nothing.
- **A kit layer** (`kitLayer.open`, a `<dialog>`): Back closes it and never
  leaves the page. The shell's own scroll-lock watcher lists `dialog.pv[open]`,
  or it would clear the kit's lock a microtask later; a new locking layer goes
  on that list too.
- The page's own image shows at once, the stored file (up to 2400 px; new uploads ≤ 1800, `PHOTO_MAX_SIZE`)
  replaces it in place.
- A writing sample no longer links to the fill's edit form (a guest met a
  sign-in page there); the owner gets a pencil on the tile instead.
- Probe: `python3 tools/viewer_probe.py` (throwaway DB copy, made-up photos).
