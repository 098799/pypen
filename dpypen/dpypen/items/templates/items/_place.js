/* KIT-PLACE: v1.1 2026-11-15
  Back lands where you left. A page Back takes from the browser's Back cache is
  as it was. One the browser loads again (iOS drops them often; then the kit
  worker's copy or the network) is put at a pixel while it is still short, and
  what comes after (pictures, late scripts, content-visibility) moves it; Safari
  has no scroll anchoring, so the page lands above or below the item you tapped.
  Spec: kit/README.md §4, "Back keeps the place". Lifted from burnlog's
  burnlogPlace (BURNLOG-22: Since 129 px off, Sessions 296 px, then 0-1 px).

  Canonical copy: ~/apps/kit/snippets/place.js. Apps carry a byte-identical
  copy (fleet-check `kit`): change this file, bump the stamp here, copy it out.
  Never edit a copy.

  How: each history entry keeps in history.state (kitPlaceY, kitPlaceAt) the
  link you tapped, else the first link or heading under the header (the one
  above it when the next is under the screen), and where it stood. Saved on a
  tap and 250 ms after a scroll; on pagehide only while that scroll save is
  still to come (v1.1: a measure there costs 30-50 ms of layout on a phone's
  page-loading press, and the tap's save already holds the place). Of two
  elements with one key, Back takes the same one by its index (v1.1: by the
  nearest place it took a help line's link of a row's href in tv). A Back or a reload
  (navigation type back_forward, reload) puts that element there again, at
  once, for 20 frames and on every resize of the page, until a touch, a wheel
  or a key, 5 s at most. history.scrollRestoration is 'manual'.

  Include it once, at the end of <body> or with `defer` (inline by a template
  include, or by a src where the CSP allows no inline script). Options, set
  before it runs, all optional:
    window.KITPLACE = {
      anchors: 'main a[href], main h2, main h3',  // what can hold the place
      header: '.kit-header',                      // the sticky bar the place is under
      skip: function () { return false; },        // true: this page restores itself
    };
  kitPlace.keep(fn): run fn (it adds or removes above the screen) and keep what
  is on the screen in place. kitPlace.save(extra): save now, with extra fields
  merged into history.state. kitPlace.go(state): restore from such a state (a
  list that loads its rows again first calls it when they are in).
  Not for an app with the kit's soft navigation (softnav.html keeps scroll per
  entry itself): it stands down when window.kitSoftNav exists.
  The file holds no literal script tag, no HTML comment and no template syntax.
*/
(function () {
  if (window.kitPlace || window.kitSoftNav) return;
  var O = window.KITPLACE || {}, SEL = O.anchors || 'main a[href], main h2, main h3', HDR = O.header || '.kit-header';
  var tapped = null;
  function key(el) { return el.tagName === 'A' ? el.getAttribute('href') : '#' + el.textContent.trim().slice(0, 60); }
  function same(k) { return Array.prototype.filter.call(document.querySelectorAll(SEL), function (el) { return key(el) === k; }); }
  // n of c: which of the elements with that key it is (a link can be on the page twice).
  function mark(el, r) {
    var k = key(el), all = same(k);
    return {k: k, top: Math.round(r.top), y: Math.round(r.top + scrollY), n: all.indexOf(el), c: all.length};
  }
  function at(any) {
    if (!any && tapped && document.contains(tapped)) {
      var t = tapped.getBoundingClientRect();
      if (t.height && t.bottom > 0 && t.top < innerHeight) return mark(tapped, t);
    }
    var h = document.querySelector(HDR), top = h ? Math.max(0, h.getBoundingClientRect().bottom) : 0;
    var list = document.querySelectorAll(SEL), prev = null;
    for (var i = 0; i < list.length; i++) {
      var r = list[i].getBoundingClientRect();
      if (!r.height || key(list[i]).length < 2) continue;                 // hidden, or an empty heading
      if (r.top >= top) return r.top < innerHeight || !prev ? mark(list[i], r) : mark(prev, prev.getBoundingClientRect());
      prev = list[i];
    }
    return prev && mark(prev, prev.getBoundingClientRect());
  }
  // The same one of the elements with that key when there are as many as before; else the
  // one nearest to where it was (under content-visibility those places are guesses: v1.1).
  function find(a) {
    var all = same(a.k), best = null, d = Infinity;
    if (a.c === all.length && all[a.n] && all[a.n].getBoundingClientRect().height) return all[a.n];
    all.forEach(function (el) {
      var r = el.getBoundingClientRect(), dd = Math.abs(r.top + scrollY - a.y);
      if (r.height && dd < d) { d = dd; best = el; }
    });
    return best;
  }
  function save(more) {
    if (document.documentElement.classList.contains('scroll-lock')) return;   // a sheet is open: the page is frozen
    try { history.replaceState(Object.assign({}, history.state, {kitPlaceY: Math.round(scrollY), kitPlaceAt: at()}, more), ''); } catch (e) {}
  }
  function go(st) {
    var a = st.kitPlaceAt, y = +st.kitPlaceY || 0, end = Date.now() + 5000, done = false, ro = null, n = 0;
    var evs = ['touchstart', 'pointerdown', 'wheel', 'keydown'];
    function quit() {
      done = true; if (ro) ro.disconnect();
      evs.forEach(function (ev) { removeEventListener(ev, quit, true); });
    }
    function fix() {
      if (done) return;
      if (Date.now() > end) { quit(); return; }
      var el = a && a.k && find(a), d = el ? el.getBoundingClientRect().top - a.top : 0;
      if (el) { if (Math.abs(d) >= 1) scrollBy(0, d); }
      else if (Math.abs(scrollY - y) > 1) scrollTo(0, y);
    }
    evs.forEach(function (ev) { addEventListener(ev, quit, {capture: true, passive: true}); });
    scrollTo(0, y); fix();
    (function frames() { fix(); if (!done && n++ < 20) requestAnimationFrame(frames); })();
    if ('ResizeObserver' in window) { ro = new ResizeObserver(fix); ro.observe(document.body); }
    addEventListener('load', fix);
  }
  function keep(fn) {
    var a = at(true);
    fn();
    var el = a && find(a);
    if (el) { var d = el.getBoundingClientRect().top - a.top; if (Math.abs(d) >= 1) scrollBy(0, d); }
  }
  window.kitPlace = {save: save, go: go, keep: keep, at: at, version: 'KIT-PLACE v1.1'};
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (a && a.matches(SEL)) tapped = a;
    save();
  }, true);
  var still = 0;
  function settled() { still = 0; save(); }
  addEventListener('scroll', function () { clearTimeout(still); still = setTimeout(settled, 250); }, {passive: true});
  addEventListener('pagehide', function () { if (still) { clearTimeout(still); settled(); } });
  var nav = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0]) || {}, st = history.state || {};
  var again = nav.type === 'back_forward' || nav.type === 'reload';
  if (again && (st.kitPlaceAt || st.kitPlaceY) && !(O.skip && O.skip())) go(st);
})();
