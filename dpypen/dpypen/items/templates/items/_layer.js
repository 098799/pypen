/* KIT-LAYER: v1.1 2026-10-30
  Overlays — sheets, modal dialogs, menus, viewers — behave the same in every
  app: Back closes the top one, one per swipe, and never leaves the app while
  one is open; the page under it does not scroll; Escape, a tap on the backdrop
  and a swipe down close it; focus goes in, stays in, and goes back to the
  button that opened it. Spec: ~/apps/kit/README.md §4, "Dialogs & sheets".
  Canonical copy: ~/apps/kit/snippets/layer.js. Apps carry a byte-identical
  copy (fleet-check `kit` compares them): change this file, bump the stamp here
  and in `version` below, copy it out. Never edit a copy.

  Load it in the <head>, before any script of the app's own that listens to
  popstate (this listener must run first): inline (a script element holding a
  Jinja or Django include of it, or the file read in by a stdlib server) or by
  src="/layer.js" (a static folder, a CSP without inline scripts). The file
  holds no closing script tag, no HTML comment and no template syntax.

  Open:   var h = kitLayer.open(el, {…})    el: an element or a selector
  Close:  h.close() · kitLayer.close(el) · kitLayer.close() (the top one)
          kitLayer.close(el, then): `then` runs once the layer is gone and its
          entry popped (a menu row's action, a link to follow, the next sheet)
  Or with no script: data-layer-open="#sheet" on a button opens it,
  data-layer-close on any element inside a layer closes that layer.

  Options of open (all optional):
    show      function(el): makes it visible (default: a <dialog> → showModal();
              another element → hidden = false and class "open")
    close     function(el, why): hides it (default: dialog.close(); else
              hidden = true and class "open" off). Runs exactly once per open,
              on every way out; never call history.back() in it.
    onClose   function(why): after it went. why = "back" (Back, ✕, Esc,
              backdrop, swipe, close()), "follow" (a link inside it was
              followed), "replaced" (open(…, {replace: true}) took its place)
    lock      false = the page under it keeps scrolling (an anchored menu, a
              panel beside a map)
    esc       false = Escape does not close it (a form that must not be lost,
              a game's end screen)
    backdrop  an element whose own taps close it (the dim layer behind a div
              sheet; a div sheet whose padding is its backdrop passes itself);
              for a <dialog> a tap outside its box closes it unless false
    swipe     an element (a sheet's grab handle or header): dragged down past
              90 px, or flicked, the sheet goes; less springs back
    focus     the element to focus in a div layer (default: el itself, which
              gets tabindex=-1); false = leave focus alone (a menu opened by a
              tap). A <dialog> focuses as the browser does.
    trap      false = Tab may leave a div layer with lock (it stays in by default)
    inert     an element made inert while the layer is open (the page's main
              element, so a screen reader stays in the sheet)
    restore   false = do not return focus to the opener
    links     false = a link inside it is followed with the layer left in
              history (default: the layers close first, then the link)
    replace   true = take the top layer's place and its history entry (one
              sheet swaps for another: Back then closes the new one and lands
              on the page, not on the first sheet)
    name      a word for `kit:layer` listeners and kitLayer.top()

  What it does:
    history   each open pushes one entry, {kitLayer: n} merged into the state
              under it (an app's own keys stay), same URL. Every way out but
              Back itself steps back through history; this listener closes on
              the pop and stops the event, so the app's popstate listeners
              (soft navigation, tabs) never see a pop that only closed a layer.
              Forward onto a closed layer steps off it. A reload with a layer
              open steps back off its entry (no dead Back). An open while a
              close still waits for its pop is held until the pop came. A
              <dialog> that closes by itself (a form method=dialog, Android's
              Back on a modal) gives its entry back too.
              Only a tap may add an entry (Chrome lets Back skip entries a page
              added on its own and leave the app): a layer opened without one
              (a report shown at load, a menu from a long-press timer) takes
              its entry at the next tap or key while it is still the top one
              (v1.1); until then Back leaves the page.
    lock      html.scroll-lock while any layer with lock is open (toast.html,
              pullrefresh.html and the apps' CSS read that class); the overlay's
              own scroller wants overscroll-behavior: contain in the app's CSS
    links     a link inside the top layer: the layers close (their entries
              go), then the link is followed, so Back from the next page lands
              on the page, not on a closed sheet. Soft navigation still takes it.
    event     'kit:layer' on document, detail {depth, name, open: true|false}
    What's new (whatsnew.html) keeps its own entries ({kitWn}); both live on
    one stack: its pops pass through this listener untouched.

  An app listener added before this file (it should not be) asks first:
    if (window.kitLayer && kitLayer.ownsPop()) return;

  API: kitLayer.open(el, o) · .close(el?, then?) · .isOpen(el) · .depth() ·
       .top() · .ownsPop() · .version
*/
(function () {
  'use strict';
  if (window.kitLayer) return;
  var version = 'v1.1 2026-10-30';
  var KEY = 'kitLayer';
  var root = document.documentElement;
  var stack = [];          // {el, o, opener, entry, ghost, leaving, thens}; the top is last
  var skip = 0;            // pops of our own history.go() still to come
  var held = [];           // opens waiting for a pending pop
  var follow = null;       // a link to follow once the layers are gone
  var CSS = 'html.scroll-lock,html.scroll-lock body{overflow:hidden}';

  try {
    var sheet = new CSSStyleSheet();
    sheet.replaceSync(CSS);
    document.adoptedStyleSheets = document.adoptedStyleSheets.concat([sheet]);
  } catch (e) {
    var st = document.createElement('style');
    st.textContent = CSS;
    (document.head || root).appendChild(st);
  }

  function lvl() { var s = history.state; return (s && typeof s[KEY] === 'number') ? s[KEY] : 0; }
  // What's new's log stands above ours: its entry is on top, not ours.
  function foreign() { var s = history.state; return !!(s && s.kitWn); }
  function entries() { var n = 0; stack.forEach(function (L) { if (L.entry) n++; }); return n; }
  function onTop() { return !foreign() && lvl() === entries(); }
  function pending() { return skip > 0 || stack.some(function (L) { return L.leaving; }); }
  function isDialog(el) { return !!el && el.tagName === 'DIALOG'; }
  function find(el) { for (var i = 0; i < stack.length; i++) if (stack[i].el === el) return i; return -1; }
  function live() { return stack.filter(function (L) { return !L.ghost; }); }
  function topLive() { var l = live(); return l[l.length - 1]; }
  function el$(x) { return typeof x === 'string' ? document.querySelector(x) : (x && x.el) || x; }
  function state(n) { var s = Object.assign({}, history.state); if (n) s[KEY] = n; else delete s[KEY]; return s; }
  function later(f) { setTimeout(f, 0); }
  function emit(L, open) {
    try {
      document.dispatchEvent(new CustomEvent('kit:layer', {detail: {depth: live().length, name: L.o.name || L.el.id || '', open: open}}));
    } catch (e) {}
  }
  function paint() {
    var ls = live();
    root.classList.toggle('scroll-lock', ls.some(function (L) { return L.o.lock !== false; }));
    stack.forEach(function (L) {
      var p = L.o.inert && el$(L.o.inert);
      if (p) p.inert = ls.some(function (M) { return el$(M.o.inert) === p; });
    });
  }
  function activated() { var u = navigator.userActivation; return !u || u.isActive; }

  function show(L) {
    var el = L.el, o = L.o;
    if (o.show) o.show(el);
    else if (isDialog(el)) { if (!el.open) { try { el.showModal(); } catch (e) { el.setAttribute('open', ''); } } }
    else { el.hidden = false; el.classList.add('open'); }
    if (!isDialog(el) && o.focus !== false) {
      var f = el$(o.focus) || el;
      if (f === el && !el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
      try { f.focus({preventScroll: true}); } catch (e) {}
    }
  }
  function hide(L, why) {
    var el = L.el, o = L.o;
    L.shutting = true;
    try {
      if (o.close) o.close(el, why);
      else if (isDialog(el)) { if (el.open) el.close(); }
      else { el.hidden = true; el.classList.remove('open'); }
    } finally { L.shutting = false; }
    if (L.swiped) { L.swiped = false; el.style.transform = ''; }
    var pi = el$(o.inert);
    if (pi) pi.inert = false;          // paint() sets it again for a layer still open
    var to = L.opener;
    if (o.restore !== false && to && to.isConnected && to !== document.body && !(topLive() && !topLive().el.contains(to))) {
      try { to.focus({preventScroll: true}); } catch (e) {}
    }
    if (o.onClose) { try { o.onClose(why); } catch (e) { later(function () { throw e; }); } }
  }
  function runThens(list) { list.forEach(function (f) { later(f); }); }
  // Close the layers until `n` entries are left (an entry-less one above them goes too), top first.
  function shutTo(n, why) {
    var thens = [];
    while (entries() > n) {
      var L = stack.pop();
      thens = thens.concat(L.thens || []);
      if (!L.ghost) { hide(L, why || L.why || 'back'); emit(L, false); }
    }
    paint();
    runThens(thens);
  }

  function open(x, o) {
    var el = el$(x);
    if (!el) return null;
    var i = find(el);
    if (i >= 0 && !stack[i].ghost && !stack[i].leaving) return stack[i].h;
    o = o || {};
    var h = {el: el, close: function (then) { close(el, then); }};
    // a close still waits for its pop (or this one is still on its way out)
    if (pending() || i >= 0) { held.push(function () { open(el, o); }); return h; }
    var L = {el: el, o: o, h: h, opener: document.activeElement, ghost: false, thens: []};
    var top = stack[stack.length - 1];
    if (o.replace && top && !top.ghost) {
      // take its place and its entry
      stack.pop();
      L.entry = top.entry; L.late = top.late; L.opener = top.opener;
      hide(top, 'replaced'); emit(top, false);
      L.thens = top.thens || [];
      stack.push(L);
    } else {
      L.entry = activated() && onTop();
      L.late = !L.entry;
      stack.push(L);
      if (L.entry) { try { history.pushState(state(entries()), ''); } catch (e) { L.entry = false; } }
    }
    show(L);
    if (isDialog(el) && !el.__kitLayer) {
      el.__kitLayer = true;
      // A dialog that closes by itself (form method=dialog, Esc, Android's Back
      // on a modal) gives back its entry.
      el.addEventListener('close', function () {
        var j = find(el);
        if (j >= 0 && !stack[j].shutting && !stack[j].ghost && !stack[j].leaving) close(el);
      });
    }
    if (o.swipe) swipe(L, el$(o.swipe));
    paint();
    emit(L, true);
    return h;
  }

  // Every way out but Back itself: step back through history, popstate closes.
  function close(x, then, why) {
    var i = x === undefined || x === null ? stack.length - 1 : find(el$(x));
    if (i < 0) { if (then) later(then); return; }
    var L = stack[i];
    if (then) L.thens.push(then);
    if (L.leaving || L.ghost) return;
    var n = 0;
    for (var k = i; k < stack.length; k++) if (stack[k].entry) n++;
    if (n && onTop()) {
      for (k = i; k < stack.length; k++) { stack[k].leaving = true; stack[k].why = why || stack[k].why; }
      history.go(-n);
    } else if (!n) {
      // no entry of ours above it: close at once
      var thens = [];
      for (k = stack.length - 1; k >= i; k--) {
        var M = stack.splice(k, 1)[0];
        thens = thens.concat(M.thens || []);
        if (!M.ghost) { hide(M, why || 'back'); emit(M, false); }
      }
      paint();
      runThens(thens);
    } else {
      // another entry stands above ours (What's new's log): close now, give
      // the entries back once they are on top again
      for (k = stack.length - 1; k >= i; k--) {
        M = stack[k];
        if (!M.ghost) { M.ghost = true; hide(M, why || 'back'); emit(M, false); }
      }
      paint();
    }
  }

  window.addEventListener('popstate', function (ev) {
    if (skip) { skip--; ev.stopImmediatePropagation(); flush(); return; }
    var at = lvl(), n = entries();
    if (at === n) { later(tidy); return; }                    // not a step through ours
    ev.stopImmediatePropagation();
    if (at > n) { skip++; history.go(n - at); return; }      // Forward onto a closed layer: step off it
    shutTo(at, follow ? 'follow' : null);
    if (!stack.length && follow) {
      var a = follow; follow = null;
      later(function () { a.__kitLayerGo = true; try { a.click(); } finally { a.__kitLayerGo = false; } });
    }
    flush();
  });
  function flush() { if (!pending()) { var q = held; held = []; q.forEach(function (f) { f(); }); } }
  // Ghosts (closed while another entry stood above them) give their entries
  // back once those are on top again.
  function tidy() {
    var g = 0;
    for (var i = stack.length - 1; i >= 0 && stack[i].ghost; i--) if (stack[i].entry) g++;
    if (g && onTop()) { for (i = stack.length - 1; i >= 0 && stack[i].ghost; i--) stack[i].leaving = true; history.go(-g); }
  }

  // A reload lands on the page, not in a layer: step back off the layer's
  // entries (same document, no load); stripping the key instead would leave a
  // same-URL entry, a Back that does nothing.
  if (lvl()) { skip++; history.go(-lvl()); }

  // A layer opened without a tap takes its entry at the next one (v1.1): the
  // event that ends a long press or the first tap after a report has activation.
  function lateEntries() {
    var i0 = -1;
    for (var i = 0; i < stack.length; i++) if (stack[i].late && !stack[i].ghost && !stack[i].leaving) { i0 = i; break; }
    if (i0 < 0 || pending() || !activated() || !onTop()) return;
    for (i = i0; i < stack.length; i++) if (stack[i].entry) { for (var j = i0; j < i; j++) stack[j].late = false; return; }
    for (i = i0; i < stack.length; i++) {
      var L = stack[i];
      if (!L.late || L.ghost) continue;
      L.late = false;
      try { history.pushState(state(entries() + 1), ''); L.entry = true; } catch (e) { return; }
    }
  }
  ['pointerup', 'touchend', 'keydown', 'click'].forEach(function (t) {
    window.addEventListener(t, function () { if (stack.length) lateEntries(); }, true);
  });

  function ownsPop() { return skip > 0 || lvl() !== entries(); }

  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape' || ev.defaultPrevented || ev.isComposing) return;
    var L = topLive();
    if (!L || L.o.esc === false) return;
    ev.preventDefault();
    ev.stopPropagation();
    close(L.el);
  }, true);
  // Esc on a modal <dialog> also fires cancel: keep a dialog with esc: false,
  // and let the keydown above close the others through history.
  document.addEventListener('cancel', function (ev) {
    var L = topLive();
    if (L && L.el === ev.target && (L.o.esc === false || L.leaving)) ev.preventDefault();
  }, true);

  // Focus stays in the top div layer with lock (a <dialog> keeps it natively).
  document.addEventListener('focusin', function (ev) {
    var L = topLive(), t = ev.target;
    if (!L || isDialog(L.el) || L.o.lock === false || L.o.trap === false || L.leaving) return;
    if (L.el.contains(t) || (t.closest && t.closest('#kit-toast,#kit-update,dialog[open]'))) return;
    var f = L.el.querySelector('[autofocus],button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])') || L.el;
    if (f === L.el && !L.el.hasAttribute('tabindex')) L.el.setAttribute('tabindex', '-1');
    try { f.focus({preventScroll: true}); } catch (e) {}
  });

  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!(t instanceof Element)) return;
    var opener = t.closest('[data-layer-open]');
    if (opener) { ev.preventDefault(); open(opener.getAttribute('data-layer-open')); return; }
    var L = topLive();
    if (!L || L.leaving) return;
    var closer = t.closest('[data-layer-close]');
    if (closer && L.el.contains(closer)) { ev.preventDefault(); close(L.el); return; }
    // the backdrop: a dim element behind a div sheet, or a dialog's outside
    var b = L.o.backdrop;
    if (b && b !== true && t === el$(b)) { close(L.el); return; }
    if (isDialog(L.el) && t === L.el && b !== false && (ev.clientX || ev.clientY)) {
      var r = L.el.getBoundingClientRect();
      if (ev.clientX < r.left || ev.clientX > r.right || ev.clientY < r.top || ev.clientY > r.bottom) close(L.el);
    }
  });
  // A link inside the top layer: close the layers first, then follow it.
  document.addEventListener('click', function (ev) {
    var a = ev.target instanceof Element && ev.target.closest('a[href]');
    if (!a || a.__kitLayerGo || ev.defaultPrevented) return;
    if (ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    if ((a.target && a.target !== '_self') || a.hasAttribute('download')) return;
    var L = topLive();
    if (!L || L.o.links === false || !L.el.contains(a) || !entries() || !onTop()) return;
    var href = a.getAttribute('href') || '';
    if (href.charAt(0) === '#' || /^javascript:/i.test(href)) return;
    ev.preventDefault();
    follow = a;
    close(stack[0].el);
  });

  // Swipe down on a handle: past 90 px, or a flick, the layer goes.
  function swipe(L, handle) {
    if (!handle || handle.__kitLayerSwipe) return;
    handle.__kitLayerSwipe = true;
    var el = L.el, y0 = 0, t0 = 0, dy = 0, on = false;
    handle.addEventListener('touchstart', function (e) {
      if (e.touches.length !== 1) return;
      on = true; y0 = e.touches[0].clientY; t0 = Date.now(); dy = 0;
      el.style.transition = 'none';
    }, {passive: true});
    handle.addEventListener('touchmove', function (e) {
      if (!on) return;
      dy = Math.max(0, e.touches[0].clientY - y0);
      el.style.transform = dy ? 'translateY(' + dy + 'px)' : '';
    }, {passive: true});
    function end() {
      if (!on) return;
      on = false; el.style.transition = '';
      var go = dy > 90 || (dy > 30 && dy / Math.max(1, Date.now() - t0) > 0.6);
      var j = find(el);
      if (go && j >= 0) { stack[j].swiped = true; el.style.transform = 'translateY(100%)'; close(el); }
      else el.style.transform = '';
    }
    handle.addEventListener('touchend', end);
    handle.addEventListener('touchcancel', end);
  }

  window.kitLayer = {
    version: version,
    open: open,
    close: function (x, then) { close(x, then); },
    isOpen: function (x) { var i = find(el$(x)); return i >= 0 && !stack[i].ghost && !stack[i].leaving; },
    depth: function () { return live().length; },
    top: function () { var L = topLive(); return L ? (L.o.name || L.el.id || '') : ''; },
    ownsPop: ownsPop,
  };
})();
