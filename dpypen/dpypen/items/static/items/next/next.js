/* The new version's own behaviour (PYPEN-11). Everything listens on the document,
   so a page swapped in by hx-boost needs nothing. Markup only:

   [data-river]   the ink river: a finger or a pointer reads a month, under it.
   [data-river-key] a colour in its key: one tap lights it, a second all of them.
   [data-confirm] a form that asks first (a delete that cannot come back).
   [data-autosubmit] a file picker that sends its form as soon as it has a file.
   [data-shown-by="<id>"] a row that shows while that checkbox is on (Sold, Used up).
   [data-busy-on-submit] a form whose answer takes a while: its parent says so
                  (or the element its value names, e.g. ".compare").
   [data-reset-field="<id>" data-reset-value] a button that puts a field back.
   [data-preview="<img id>"] a file picker that shows the photo it holds.
   [data-tl-zoom] the timeline's Fit, 2×, 4×.
   .view-switch  the list or the grid on /pens/ and /inks/, kept per device
                  (pensView, inksView: the old version's keys).
*/
(function () {
  "use strict";
  if (window.__nextJs) return;
  window.__nextJs = true;

  /* ---- the river ---- */
  function riverData(r) {
    if (r._d) return r._d;
    var s = r.querySelector("script[type='application/json']");
    r._d = s ? JSON.parse(s.textContent) : null;
    return r._d;
  }
  function readRiver(r, x) {
    var plot = r.querySelector(".river-plot"), d = riverData(r);
    if (!plot || !d) return;
    var box = plot.getBoundingClientRect(), n = d.months.length;
    var i = Math.max(0, Math.min(n - 1, Math.round((x - box.left) / box.width * (n - 1))));
    r._i = i;
    var m = d.months[i], cross = r.querySelector(".river-cross"), out = r.querySelector(".river-read");
    cross.hidden = false;
    cross.style.left = (n > 1 ? 100 * i / (n - 1) : 0) + "%";
    out.textContent = "";
    var head = out.appendChild(document.createElement("b"));
    head.textContent = m[0];
    out.appendChild(document.createTextNode(", " + m[1] + (m[1] === 1 ? " pen" : " pens") + " inked"));
    var parts = m[2].slice().sort(function (a, b) { return b[1] - a[1]; }).slice(0, 4)
      .map(function (c) { return d.colors[c[0]].toLowerCase() + " " + c[1]; });
    if (parts.length) out.appendChild(document.createTextNode(": " + parts.join(", ")));
  }
  document.addEventListener("pointermove", function (e) {
    var r = e.target.closest && e.target.closest("[data-river]");
    if (r && e.target.closest(".river-plot")) readRiver(r, e.clientX);
  });
  document.addEventListener("pointerdown", function (e) {
    var r = e.target.closest && e.target.closest("[data-river]");
    if (r && e.target.closest(".river-plot")) readRiver(r, e.clientX);
  });
  document.addEventListener("keydown", function (e) {
    var r = e.target.closest && e.target.closest("[data-river]");
    if (!r || (e.key !== "ArrowLeft" && e.key !== "ArrowRight") || !e.target.matches(".river-plot")) return;
    e.preventDefault();
    e.stopPropagation();
    var d = riverData(r), box = r.querySelector(".river-plot").getBoundingClientRect();
    var i = r._i === undefined ? d.months.length - 1 : r._i + (e.key === "ArrowRight" ? 1 : -1);
    readRiver(r, box.left + box.width * Math.max(0, Math.min(d.months.length - 1, i)) / (d.months.length - 1));
  }, true);
  document.addEventListener("click", function (e) {
    var key = e.target.closest && e.target.closest("[data-river-key]");
    if (!key) return;
    var r = key.closest("[data-river]"), on = key.getAttribute("aria-pressed") !== "true";
    r.querySelectorAll("[data-river-key]").forEach(function (k) { k.setAttribute("aria-pressed", String(on && k === key)); });
    var name = key.getAttribute("data-river-key");
    r.classList.toggle("is-picked", on);
    r.querySelectorAll("path[data-c]").forEach(function (p) { p.classList.toggle("is-lit", on && p.getAttribute("data-c") === name); });
  });

  /* ---- forms ---- */
  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (f.hasAttribute("data-confirm") && !window.confirm(f.getAttribute("data-confirm"))) {
      e.preventDefault();
      e.stopImmediatePropagation();
      return;
    }
    if (f.hasAttribute("data-busy-on-submit")) {
      var sel = f.getAttribute("data-busy-on-submit");
      var host = (sel && document.querySelector(sel)) || f.closest("[data-busy-host]") || f;
      host.classList.add("is-busy");
    }
  }, true);
  document.addEventListener("change", function (e) {
    var t = e.target;
    if (t.hasAttribute && t.hasAttribute("data-autosubmit") && t.form) t.form.requestSubmit ? t.form.requestSubmit() : t.form.submit();
    if (t.type === "checkbox" && t.id) document.querySelectorAll('[data-shown-by="' + t.id + '"]').forEach(reveal);
    if (t.id === "polishAll") polish(t);
    if (t.hasAttribute && t.hasAttribute("data-preview")) preview(t);
  });
  function preview(input) {
    var img = document.getElementById(input.getAttribute("data-preview"));
    if (!img) return;
    if (img.src && img.src.indexOf("blob:") === 0) URL.revokeObjectURL(img.src);
    var file = input.files && input.files[0];
    img.hidden = !file;
    if (file) img.src = URL.createObjectURL(file);
  }

  /* ---- small buttons ---- */
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-reset-field]");
    if (b) {
      var field = document.getElementById(b.getAttribute("data-reset-field"));
      if (field) { field.value = b.getAttribute("data-reset-value"); field.focus(); }
      return;
    }
    var z = e.target.closest && e.target.closest("[data-tl-zoom]");
    if (z) {
      var plate = document.getElementById("tlPlate");
      if (!plate) return;
      var n = Number(z.getAttribute("data-tl-zoom")) || 1;
      var zoomed = plate.classList.contains("is-zoomed");
      var mid = (plate.scrollLeft + plate.clientWidth / 2) / (plate.scrollWidth || 1);
      plate.style.setProperty("--z", n);
      plate.classList.toggle("is-zoomed", n > 1);
      z.parentNode.querySelectorAll("[data-tl-zoom]").forEach(function (x) { x.setAttribute("aria-pressed", String(x === z)); });
      // from Fit, the newest years; from a zoom, the same years in the middle
      plate.scrollLeft = zoomed ? mid * plate.scrollWidth - plate.clientWidth / 2 : plate.scrollWidth;
      return;
    }
    var v = e.target.closest && e.target.closest('.view-switch a[data-navkey="view"]');
    if (v) {
      var key = location.pathname === "/inks/" ? "inksView" : location.pathname === "/pens/" ? "pensView" : null;
      var grid = (key === "pensView") === (v.getAttribute("data-navval") === "grid");
      if (key) try { localStorage.setItem(key, grid ? "grid" : "list"); } catch (err) {}
    }
  });
  /* The list or the grid as chosen last on this device, when the address does not say. */
  function keepView() {
    var key = location.pathname === "/inks/" ? "inksView" : location.pathname === "/pens/" ? "pensView" : null;
    if (!key || new URLSearchParams(location.search).has("view")) return;
    var saved = null;
    try { saved = localStorage.getItem(key); } catch (err) {}
    var want = key === "pensView" ? (saved === "grid" ? "grid" : "") : (saved === "list" ? "list" : "");
    if (!want) return;
    var u = new URL(location.href);
    u.searchParams.set("view", want);
    location.replace(u.toString());
  }
  function reveal(row) {
    var box = document.getElementById(row.getAttribute("data-shown-by"));
    if (box) row.hidden = !box.checked;
  }
  function polish(master) {
    document.querySelectorAll(".polish-flag").forEach(function (f) { f.checked = master.checked; });
    try { localStorage.setItem("polishNewShots", master.checked ? "1" : "0"); } catch (e) {}
  }
  function arrive() {
    keepView();
    // a search page opened with a query: the caret at its end, to go on typing
    var q = document.getElementById("searchQ");
    if (q && q.value && document.activeElement === q) { try { q.setSelectionRange(q.value.length, q.value.length); } catch (err) {} }
    document.querySelectorAll("[data-shown-by]").forEach(reveal);
    var master = document.getElementById("polishAll");
    if (master) {
      try { var s = localStorage.getItem("polishNewShots"); if (s !== null) master.checked = s === "1"; } catch (e) {}
      polish(master);
    }
  }
  document.addEventListener("htmx:afterSettle", arrive);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arrive);
  else arrive();

  /* ---- a pen's photos: a thumb shows in the big frame ---- */
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("[data-thumb]");
    if (!a) return;
    e.preventDefault();
    var main = document.getElementById("photoImg");
    if (!main) return;
    main.src = a.getAttribute("data-img");
    main.setAttribute("data-zoom", a.getAttribute("data-zoom-src"));
    a.parentNode.querySelectorAll("[data-thumb]").forEach(function (x) { x.removeAttribute("aria-current"); });
    a.setAttribute("aria-current", "true");
  });
})();
