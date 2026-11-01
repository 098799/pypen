/* pypen's photo viewer (PYPEN-1): tap a photo and it fills the screen, to be
   pinched, zoomed and walked through — the museum's lightbox
   (~/museum/museum/static/base.js, "pinch-zoom lightbox"), cut down to what a
   pen page needs.

   It is a kit layer (_layer.js, KIT-LAYER): Back, Esc and ✕ close it, the
   page under it does not scroll, focus goes back to the photo. Its own: pinch,
   wheel and double-tap zoom, drag to look around, the flick down and the
   triple tap that close it, ‹ › and the sideways swipe along a group, the
   overview map while zoomed, ← → + − 0 on a keyboard.

   Markup, in any page (no script of its own needed, htmx swaps included):
     data-zoom="<url>"         a photo you can tap: it opens <url> (empty: its
                               own src). Gets role=button and tabindex here.
     data-zoom-group="g"       … opens group g: every [data-zoom-item="g"] on
                               the page, in order, at its own place in it, or
                               at the item marked .active, or at the first.
     data-zoom-item="g"        one picture of group g; its url is data-zoom-src,
                               data-zoom or data-img, else its own img's src.
     data-zoom-cap="…"         the caption (on the item; else the trigger's).
   The dialog is built on the first open and found again by id: htmx's history
   restore rewrites <body>, so nothing here holds on to an old element. */
(function () {
  if (window.pypenViewer) return;
  var MAXZ = 6;
  var dlg, img, cap, capT, capN, hint, prev, next, fail, map, mapImg, mapView;
  var items = [], idx = 0, gen = 0;
  var scale = 1, tx = 0, ty = 0, minScale = 1, natW = 0, natH = 0;
  var pointers = new Map(), lastDist = 0, lastMid = null, lastTap = 0;
  var tapChain = 0, tapChainT = 0, swipeX = 0, swipeY = 0, swipeT = 0;
  var capTimer = 0, hintTimer = 0, mapTimer = 0, mapW = 0;

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html) e.innerHTML = html;
    return e;
  }

  function build() {
    dlg = document.getElementById("pv");
    if (dlg && dlg._pv) return;
    if (!dlg) { dlg = el("dialog"); dlg.id = "pv"; document.body.appendChild(dlg); }
    dlg.className = "pv";
    dlg.setAttribute("aria-label", "Photo");
    dlg.innerHTML =
      '<img class="pv-img" alt="" draggable="false">' +
      '<div class="pv-cap" aria-live="polite"><span class="pv-t"></span><span class="pv-n"></span></div>' +
      '<button type="button" class="pv-close" aria-label="Close">✕</button>' +
      '<button type="button" class="pv-step pv-prev" aria-label="Previous photo" hidden>‹</button>' +
      '<button type="button" class="pv-step pv-next" aria-label="Next photo" hidden>›</button>' +
      '<div class="pv-map" aria-hidden="true"><img alt="" draggable="false"><i></i></div>' +
      '<div class="pv-fail" role="alert" hidden>The photo did not load. Check the connection, then open it again.</div>' +
      '<div class="pv-hint"><span class="t-touch">Pinch or double-tap to zoom · flick down to close</span>' +
      '<span class="t-desk">Scroll or double-click to zoom · ← → next · Esc to close</span></div>';
    img = dlg.querySelector(".pv-img");
    cap = dlg.querySelector(".pv-cap");
    capT = cap.querySelector(".pv-t");
    capN = cap.querySelector(".pv-n");
    hint = dlg.querySelector(".pv-hint");
    prev = dlg.querySelector(".pv-prev");
    next = dlg.querySelector(".pv-next");
    fail = dlg.querySelector(".pv-fail");
    map = dlg.querySelector(".pv-map");
    mapImg = map.querySelector("img");
    mapView = map.querySelector("i");
    dlg.querySelector(".pv-close").addEventListener("click", close);
    prev.addEventListener("click", function () { step(-1); });
    next.addEventListener("click", function () { step(1); });
    dlg.addEventListener("pointerdown", down);
    dlg.addEventListener("pointermove", move);
    dlg.addEventListener("pointerup", up);
    dlg.addEventListener("pointercancel", up);
    dlg.addEventListener("wheel", function (e) {
      e.preventDefault();
      zoomTo(scale * (e.deltaY < 0 ? 1.18 : 1 / 1.18), e.clientX, e.clientY);
    }, { passive: false });
    dlg.addEventListener("keydown", key);
    dlg._pv = true;
  }

  // ——— the view: where the photo sits and how large ———
  function zoomed() { return scale > minScale * 1.05; }
  function apply() {
    img.style.transform = "translate(" + tx + "px," + ty + "px) scale(" + scale + ")";
    dlg.classList.toggle("zoomed", zoomed());
    mapPaint();
  }
  // an axis that fits is centred; one that overflows may not show past the edge
  function clamp() {
    var vw = innerWidth, vh = innerHeight, w = natW * scale, h = natH * scale;
    tx = w <= vw ? (vw - w) / 2 : Math.min(0, Math.max(vw - w, tx));
    ty = h <= vh ? (vh - h) / 2 : Math.min(0, Math.max(vh - h, ty));
  }
  function fit() {
    if (!natW) return;
    minScale = Math.min(innerWidth / natW, innerHeight / natH);
    scale = minScale; clamp(); apply();
  }
  function zoomTo(f, cx, cy) {
    if (!natW) return;
    var ns = Math.max(minScale, Math.min(minScale * MAXZ, f));
    tx = cx - (cx - tx) * (ns / scale);
    ty = cy - (cy - ty) * (ns / scale);
    scale = ns; clamp(); apply();
  }
  function setSize(w, h) {
    natW = w; natH = h;
    img.style.width = w + "px"; img.style.height = h + "px";
    var box = innerWidth < 600 ? 96 : 150, k = Math.min(box / w, box / h);
    mapW = Math.round(w * k);
    map.style.width = mapW + "px"; map.style.height = Math.round(h * k) + "px";
  }

  // ——— the overview: the whole photo, and the part of it on screen ———
  function mapPaint() {
    if (!mapW) return;
    if (!(scale > minScale * 1.03)) { map.classList.remove("on"); return; }
    var k = mapW / (natW * scale);
    var x0 = Math.max(0, -tx), y0 = Math.max(0, -ty);
    var x1 = Math.min(natW * scale, innerWidth - tx), y1 = Math.min(natH * scale, innerHeight - ty);
    mapView.style.left = (x0 * k) + "px"; mapView.style.top = (y0 * k) + "px";
    mapView.style.width = ((x1 - x0) * k) + "px"; mapView.style.height = ((y1 - y0) * k) + "px";
    map.classList.add("on");
    hint.classList.remove("on");
    clearTimeout(mapTimer);
    mapTimer = setTimeout(function () { map.classList.remove("on"); }, 1500);
  }

  // ——— loading: what the page already shows first, the full file on top ———
  function show(i, quick) {
    idx = i;
    var it = items[i], g = ++gen;
    fail.hidden = true;
    natW = 0; mapW = 0; map.classList.remove("on");
    prev.hidden = items.length < 2 || i <= 0;
    next.hidden = items.length < 2 || i >= items.length - 1;
    capT.textContent = it.cap || "";
    capN.textContent = items.length > 1 ? (i + 1) + " of " + items.length : "";
    capShow();
    function stage(src, last) {
      var pic = new Image();
      pic.decoding = "async";
      pic.onload = function () {
        if (g !== gen) return;
        var w = pic.naturalWidth, h = pic.naturalHeight;
        if (!natW) { setSize(w, h); img.src = src; mapImg.src = src; fit(); img.style.opacity = ""; return; }
        if (w <= natW && src !== it.src) return;    // the small one came last
        // the larger file keeps the view: same place, same size on screen
        var k = natW / w;
        img.src = src; mapImg.src = src;
        setSize(w, h);
        minScale *= k; scale *= k; clamp(); apply();
      };
      pic.onerror = function () {
        if (g === gen && last && !natW) { fail.hidden = false; img.style.opacity = ""; }
      };
      pic.src = src;
    }
    if (quick && quick !== it.src) stage(quick, false);
    stage(it.src, true);
    [i - 1, i + 1].forEach(function (j) { if (items[j]) new Image().src = items[j].src; });
  }
  function step(d) {
    var j = idx + d;
    if (j < 0 || j >= items.length) return;
    img.style.opacity = ".3";
    show(j, items[j].thumb);
  }
  function capShow() {
    if (!capT.textContent && !capN.textContent) { cap.classList.remove("on"); return; }
    cap.classList.add("on");
    clearTimeout(capTimer);
    capTimer = setTimeout(function () { cap.classList.remove("on"); }, 2600);
  }

  // ——— open and close ———
  function urlOf(e) {
    var u = e.getAttribute("data-zoom-src") || e.getAttribute("data-zoom") || e.getAttribute("data-img");
    if (u) return u;
    var im = e.tagName === "IMG" ? e : e.querySelector("img");
    return im ? im.currentSrc || im.src : "";
  }
  function shownOf(e) {
    var im = e.tagName === "IMG" ? e : e.querySelector("img");
    return im && im.complete && im.naturalWidth ? im.currentSrc || im.src : null;
  }
  function itemOf(e, trigger) {
    return { src: urlOf(e), thumb: shownOf(e),
             cap: e.getAttribute("data-zoom-cap") || (trigger && trigger.getAttribute("data-zoom-cap")) || "" };
  }
  function open(trigger) {
    var g = trigger.getAttribute("data-zoom-group"), list = [], at = 0;
    if (g) {
      var els = Array.prototype.slice.call(document.querySelectorAll('[data-zoom-item="' + g + '"]'));
      list = els.map(function (e) { return itemOf(e, trigger); });
      at = els.indexOf(trigger);
      if (at < 0) {
        at = els.findIndex(function (e) { return e.classList.contains("active"); });
        // the trigger shows the picture already: up at once
        if (at >= 0) list[at].thumb = shownOf(trigger) || list[at].thumb;
      }
      if (at < 0) at = 0;
    }
    if (!list.length) list = [itemOf(trigger, trigger)];
    if (!list[at].src) return;
    build();
    items = list;
    kitLayer.open(dlg, { name: "photo", backdrop: false, close: shut,
                         focus: dlg.querySelector(".pv-close") });
    hint.classList.add("on");
    clearTimeout(hintTimer);
    hintTimer = setTimeout(function () { hint.classList.remove("on"); }, 2600);
    img.removeAttribute("src");
    show(at, list[at].thumb);
  }
  function close() { kitLayer.close(dlg); }
  function shut() {
    gen++;
    clearTimeout(capTimer); clearTimeout(hintTimer); clearTimeout(mapTimer);
    pointers.clear();
    dlg.classList.remove("zoomed");
    cap.classList.remove("on"); map.classList.remove("on");
    if (dlg.open) dlg.close();
    img.removeAttribute("src"); img.style.opacity = "";
  }

  // ——— touch and mouse ———
  function down(e) {
    if (e.target.closest("button")) return;
    try { dlg.setPointerCapture(e.pointerId); } catch (err) {}
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 2) {
      var p = Array.from(pointers.values());
      lastDist = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
      lastMid = { x: (p[0].x + p[1].x) / 2, y: (p[0].y + p[1].y) / 2 };
    } else if (pointers.size === 1) {
      var now = Date.now();
      tapChain = now - tapChainT < 350 ? tapChain + 1 : 1;
      tapChainT = now;
      if (tapChain >= 3) { tapChain = 0; close(); return; }
      if (now - lastTap < 300) {
        if (zoomed()) { scale = minScale; clamp(); apply(); }
        else zoomTo(minScale * 2.8, e.clientX, e.clientY);
        lastTap = 0;
      } else lastTap = now;
      swipeX = e.clientX; swipeY = e.clientY; swipeT = now;
    }
  }
  function move(e) {
    if (!pointers.has(e.pointerId)) return;
    var was = pointers.get(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 2) {
      var p = Array.from(pointers.values());
      var dist = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
      var mid = { x: (p[0].x + p[1].x) / 2, y: (p[0].y + p[1].y) / 2 };
      if (lastDist > 0) zoomTo(scale * (dist / lastDist), mid.x, mid.y);
      tx += mid.x - lastMid.x; ty += mid.y - lastMid.y;
      lastDist = dist; lastMid = mid; clamp(); apply();
    } else if (pointers.size === 1 && scale > minScale * 1.01) {
      tx += e.clientX - was.x; ty += e.clientY - was.y;
      clamp(); apply();
    }
  }
  function up(e) {
    var single = pointers.size === 1;
    pointers.delete(e.pointerId);
    if (pointers.size < 2) lastDist = 0;
    // at rest, a flick down closes and a sideways one walks the group
    if (single && scale <= minScale * 1.02 && Date.now() - swipeT < 500) {
      var dy = e.clientY - swipeY, dx = e.clientX - swipeX;
      if (Math.abs(dy) > 90 && Math.abs(dy) > Math.abs(dx) * 1.5) close();
      else if (Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy) * 1.5) step(dx < 0 ? 1 : -1);
    }
  }
  function key(e) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    var k = e.key, cx = innerWidth / 2, cy = innerHeight / 2;
    if (k === "+" || k === "=") zoomTo(scale * 1.5, cx, cy);
    else if (k === "-" || k === "_") zoomTo(scale / 1.5, cx, cy);
    else if (k === "0") fit();
    else if (k === "ArrowLeft" || k === "ArrowRight") {
      var d = k === "ArrowLeft" ? -1 : 1;
      if (zoomed()) { tx -= d * innerWidth * 0.25; clamp(); apply(); } else step(d);
    } else if (k === "ArrowUp" || k === "ArrowDown") {
      if (!zoomed()) return;
      ty -= (k === "ArrowUp" ? -1 : 1) * innerHeight * 0.25; clamp(); apply();
    } else return;
    e.preventDefault(); e.stopPropagation();
  }
  window.addEventListener("resize", function () {
    if (dlg && dlg.open && natW) { setSize(natW, natH); fit(); }
  });

  // ——— the photos on the page ———
  function arm() {
    document.querySelectorAll("[data-zoom]:not([tabindex])").forEach(function (e) {
      e.setAttribute("tabindex", "0");
      e.setAttribute("role", "button");
      if (!e.getAttribute("aria-label")) {
        var im = e.tagName === "IMG" ? e : e.querySelector("img");
        e.setAttribute("aria-label", "View " + ((im && im.alt) || "photo") + " full screen");
      }
    });
  }
  document.addEventListener("click", function (e) {
    var t = e.target.closest && e.target.closest("[data-zoom]");
    if (!t || e.button) return;
    e.preventDefault();
    open(t);
  });
  document.addEventListener("keydown", function (e) {
    if ((e.key !== "Enter" && e.key !== " ") || !e.target.matches || !e.target.matches("[data-zoom]")) return;
    e.preventDefault();
    open(e.target);
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arm);
  else arm();
  document.addEventListener("htmx:afterSettle", arm);
  document.addEventListener("htmx:historyRestore", arm);
  window.pypenViewer = { open: open, close: close };
})();
