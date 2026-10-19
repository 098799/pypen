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
