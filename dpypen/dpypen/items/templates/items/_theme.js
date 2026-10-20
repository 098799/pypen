/* KIT-THEME: v1.1 2026-10-20
  The theme: Dark · Light · Auto, the same in every app. Spec: ~/apps/kit/README.md
  §4, "Theme". Canonical copy: ~/apps/kit/snippets/theme.js. Apps carry a
  byte-identical copy (fleet-check `kit` compares them): change this file, bump
  the stamp here and in `version` below, copy it out. Never edit a copy.

  Load it once in the <head>, after the theme-color meta and before the
  stylesheet, as a blocking script, so the first paint is already in the right
  theme: inline (a script element holding a Jinja or Django include of it, or the
  file read into the page by a stdlib server) or by src="/theme.js" where the
  CSP allows no inline script (witness). The app tells it, before, in a script:
    window.KITTHEME = {app: "pod", colors: {dark: "#0b0e14", light: "#f6f4f2"}};
  or, without an inline script, as data- attributes of the script tag:
    data-app="witness" data-dark="#101317" data-light="#ece8df"
  (this file holds no closing script tag, no HTML comment and no template
  syntax — brace-percent, double brace, brace-hash — so it inlines and
  includes as is; v1.1 took one out of this comment: Jinja included the
  file into itself)
  app      the key is localStorage['<app>Theme'], <app> = the registry's name
  colors   <meta name="theme-color"> per theme = the header's colour (optional)
  default  'dark' (the fleet's default), 'light' or 'auto'; another one than
           dark is written in the app's README with the reason
  legacy   older keys, read once while '<app>Theme' is empty ("chTheme", or
           "musTheme,theme" on the tag); their 'system'/'os' counts as auto.
           The old key is left as it was.
  labels   the chooser's words {group, dark, light, auto, note}; English by
           default (atlas and museum pass their own language)

  What it does:
    html[data-theme]       'dark' or 'light', auto already resolved: the one hook
                           for the app's CSS (dark in :root, light in
                           html[data-theme=light], or the other way round)
    html[data-theme-mode]  'dark', 'light' or 'auto': what was chosen
    color-scheme           on the root element, so form controls and scroll bars follow
    meta theme-color       colors[theme], every meta of that name (media= dropped)
    ?theme=dark|light|auto this load only, never stored (screenshots, links)
    auto                   follows the system live (matchMedia 'change')
    other tabs             a choice made in one tab repaints the others
    'kit:theme' event      on document, detail {mode, theme}, after a repaint
                           that changed something (a canvas drawn with theme
                           colours listens and redraws)

  The chooser: an empty element with data-kit-theme in the Settings row "Theme" (README §4:
  theme first). It becomes a segmented radio group Dark · Light · Auto
  (role=radiogroup, arrow keys, the choice marked with aria-checked) at
  DOMContentLoaded and after each `kit:softnav`; a panel drawn later calls
  kitTheme.mount(). Its look takes the app's --accent --panel --line --fg --dim
  --bg and nothing else; its CSS is a constructed sheet, so a CSP without
  'unsafe-inline' styles lets it in.

  API: kitTheme.mode() · kitTheme.theme() · kitTheme.set(mode) · kitTheme.mount(root)
*/
(function () {
  'use strict';
  if (window.kitTheme) return;
  var version = 'v1.1 2026-10-20';
  var C = window.KITTHEME || {};
  var tag = document.currentScript;
  var ds = (tag && tag.dataset) || {};
  var app = C.app || ds.app || 'app';
  var KEY = app + 'Theme';
  var MODES = ['dark', 'light', 'auto'];
  var colors = C.colors || (ds.dark || ds.light ? {dark: ds.dark, light: ds.light} : null);
  var legacy = C.legacy || (ds.legacy ? ds.legacy.split(',') : []);
  var root = document.documentElement;
  var media = window.matchMedia ? matchMedia('(prefers-color-scheme: light)') : null;

  function norm(v) {
    if (v === 'system' || v === 'os') return 'auto';
    return MODES.indexOf(v) >= 0 ? v : null;
  }
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function put(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  function stored() {
    var m = norm(get(KEY));
    if (m) return m;
    for (var i = 0; i < legacy.length; i++) {
      m = norm(get(legacy[i]));
      if (m) { put(KEY, m); return m; }
    }
    return null;
  }

  var mode = stored() || norm(C['default'] || ds['default']) || 'dark';
  try {
    var once = norm(new URLSearchParams(location.search).get('theme'));
    if (once) mode = once;
  } catch (e) {}

  function resolve(m) {
    if (m === 'auto') return media && media.matches ? 'light' : 'dark';
    return m;
  }

  var painted = null;
  function paint() {
    var t = resolve(mode);
    root.setAttribute('data-theme', t);
    root.setAttribute('data-theme-mode', mode);
    root.style.colorScheme = t;
    var col = colors && colors[t];
    if (col) {
      var metas = document.querySelectorAll('meta[name="theme-color"]');
      for (var i = 0; i < metas.length; i++) {
        metas[i].removeAttribute('media');
        metas[i].setAttribute('content', col);
      }
    }
    sync();
    var changed = painted && (painted.mode !== mode || painted.theme !== t);
    painted = {mode: mode, theme: t};
    if (changed) document.dispatchEvent(new CustomEvent('kit:theme', {detail: {mode: mode, theme: t}}));
  }

  function set(m) {
    m = norm(m);
    if (!m) return;
    mode = m;
    put(KEY, m);
    paint();
  }

  if (media) {
    var onSystem = function () { if (mode === 'auto') paint(); };
    if (media.addEventListener) media.addEventListener('change', onSystem);
    else if (media.addListener) media.addListener(onSystem);
  }
  window.addEventListener('storage', function (e) {
    if (e.key !== KEY) return;
    var m = norm(e.newValue);
    if (m && m !== mode) { mode = m; paint(); }
  });

  // --- the chooser -------------------------------------------------------
  var L = {group: 'Theme', dark: 'Dark', light: 'Light', auto: 'Auto',
           note: 'Auto follows the phone or computer.'};
  var lab = C.labels || {};
  for (var k in lab) if (Object.prototype.hasOwnProperty.call(lab, k)) L[k] = lab[k];
  var ICON = {
    dark: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
    light: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
    auto: '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none"/>'
  };
  var CSS =
    'div.kit-theme{display:inline-flex;gap:2px;padding:2px;margin:0;border-radius:10px;box-sizing:border-box;' +
      'max-width:100%;vertical-align:middle;background:var(--bg,#111);border:1px solid var(--line,#3a404a)}' +
    'div.kit-theme[role=radiogroup]>button{all:unset;box-sizing:border-box;display:inline-flex;align-items:center;' +
      'justify-content:center;gap:6px;min-height:36px;min-width:44px;padding:0 12px;border-radius:8px;cursor:pointer;' +
      'font:500 14px/1 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--dim,#9aa4b2);' +
      'white-space:nowrap;-webkit-tap-highlight-color:transparent}' +
    'div.kit-theme[role=radiogroup]>button>svg{width:16px;height:16px;flex:none;fill:none;stroke:currentColor;' +
      'stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}' +
    'div.kit-theme[role=radiogroup]>button[aria-checked=true]{color:var(--fg,#e8e8e8);background:var(--panel,#20242b);' +
      'box-shadow:inset 0 0 0 1px var(--accent,#6aa9ff)}' +
    'div.kit-theme[role=radiogroup]>button[aria-checked=true]>svg{color:var(--accent,#6aa9ff)}' +
    'div.kit-theme[role=radiogroup]>button:focus-visible{outline:2px solid var(--accent,#6aa9ff);outline-offset:1px}' +
    '@media (hover:hover) and (pointer:fine){div.kit-theme[role=radiogroup]>button:hover{color:var(--fg,#e8e8e8)}}' +
    '@media (max-width:360px){div.kit-theme[role=radiogroup]>button{padding:0 9px}' +
      'div.kit-theme[role=radiogroup]>button>svg{display:none}}';

  function style() {
    try {
      var sheet = new CSSStyleSheet();
      sheet.replaceSync(CSS);
      document.adoptedStyleSheets = document.adoptedStyleSheets.concat([sheet]);
    } catch (e) {
      var el = document.createElement('style');
      el.textContent = CSS;
      (document.head || root).appendChild(el);
    }
  }

  function sync() {
    var bs = document.querySelectorAll('div.kit-theme > button[data-mode]');
    for (var i = 0; i < bs.length; i++) {
      var on = bs[i].getAttribute('data-mode') === mode;
      bs[i].setAttribute('aria-checked', on ? 'true' : 'false');
      bs[i].tabIndex = on ? 0 : -1;
    }
  }

  function onKey(e) {
    var step = {ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1}[e.key];
    if (!step) return;
    e.preventDefault();
    var next = MODES[(MODES.indexOf(mode) + step + MODES.length) % MODES.length];
    set(next);
    var b = e.currentTarget.querySelector('button[data-mode="' + next + '"]');
    if (b) b.focus();
  }
  function onClick(e) {
    var b = e.target.closest && e.target.closest('button[data-mode]');
    if (b) set(b.getAttribute('data-mode'));
  }

  function mount(scope) {
    var spots = (scope || document).querySelectorAll('[data-kit-theme]');
    for (var s = 0; s < spots.length; s++) {
      if (spots[s].querySelector('div.kit-theme')) continue;
      var box = document.createElement('div');
      box.className = 'kit-theme';
      box.setAttribute('role', 'radiogroup');
      box.setAttribute('aria-label', L.group);
      box.title = L.note;
      for (var i = 0; i < MODES.length; i++) {
        var b = document.createElement('button');
        b.type = 'button';
        b.setAttribute('role', 'radio');
        b.setAttribute('data-mode', MODES[i]);
        b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + ICON[MODES[i]] + '</svg>';
        var span = document.createElement('span');
        span.textContent = L[MODES[i]];
        b.appendChild(span);
        box.appendChild(b);
      }
      box.addEventListener('click', onClick);
      box.addEventListener('keydown', onKey);
      spots[s].appendChild(box);
    }
    sync();
  }

  window.kitTheme = {
    version: version,
    key: KEY,
    mode: function () { return mode; },
    theme: function () { return resolve(mode); },
    set: set,
    mount: mount
  };

  style();
  paint();
  if (document.readyState === 'loading') {
    // a meta written after this script is painted here
    document.addEventListener('DOMContentLoaded', function () { painted = null; paint(); mount(); });
  } else {
    mount();
  }
  document.addEventListener('kit:softnav', function () { mount(); });
})();
