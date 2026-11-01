/* The desk bar (kit README §4 Fleet UX "Desk", PYPEN-6).

   On a screen 900 px and wider the app's chrome is one 52 px bar (#hdr in
   _shell.html): the brand, the places as tabs, then what the page can do —
   Filter ▾, ⌕, ⋯ — on the right. The markup is the phone's, once. The tab
   bar sits in #hdr and app.css draws it both ways (the bar's tabs here, the
   fixed bottom bar on a phone), with its More button as the bar's ⋯. This
   script does the two things CSS cannot:

   - the page's chip row, marked [data-fold="<name>"] (the pens' rotation, the
     inks' filters), stays in the page but hidden, and a Filter button stands
     for it: it opens the same chips in a popover under it, and a chip there
     clicks the real one, so htmx, the URL and the filter-nav sync all work as
     on a phone. The button names what is on ("Filter Priority 1");
   - ⌕ opens a popover with the menu's search field, lent while it is open
     and handed back to the menu when it closes.

   It runs on load, on a width change, after every htmx swap (the page, and
   with it the chip row, is new) and after htmx's history restore (the body is
   rebuilt from a snapshot: nothing found earlier is kept, every node is looked
   up again). Below 900 px the Filter button goes and the chips show.

   The popovers are kit layers (_layer.js): Back, Esc and a click outside close
   them; lock: false, the page keeps scrolling. */
(function () {
  if (window.__deskbar) return;
  var DESK = matchMedia("(min-width: 900px)");
  var root = document.documentElement;

  function $(sel) { return document.querySelector(sel); }
  function hdr() { return document.getElementById("hdr"); }

  function closePops() {
    ["deskSearch", "deskFilter"].forEach(function (id) {
      var p = document.getElementById(id);
      if (p && window.kitLayer && kitLayer.isOpen(p)) kitLayer.close(p);
    });
  }

  function arrange() {
    var on = DESK.matches;
    root.classList.toggle("desk-on", on);
    if (!on) closePops();
    fold();
  }

  // ---- the Filter button ---------------------------------------------------
  function chipName(c) {
    // "Priority 1 · 21 pens" → "Priority 1"; else the chip's words without
    // its count ("Blue 12" → "Blue").
    var t = c.getAttribute("title");
    if (t) return t.split(" · ")[0].trim();
    var l = c.querySelector(".cc-label");
    return (l ? l.textContent : c.textContent).replace(/\s*\d+\s*$/, "").trim();
  }
  function chipsOf(host) {
    return [].slice.call(host.querySelectorAll("a, button"));
  }
  function isOn(c) {
    // "All" is on when nothing is: it is not a filter, so it names nothing.
    return c.classList.contains("on") && c.getAttribute("data-navval") !== "";
  }

  function fold() {
    var h = hdr();
    if (!h) return;
    var old = document.getElementById("deskFilterBtn");
    var host = $("#main [data-fold]");
    if (!DESK.matches || !host) {
      if (old) old.remove();
      return;
    }
    var name = host.getAttribute("data-fold") || "Filter";
    var on = chipsOf(host).filter(isOn).map(chipName);
    var b = old || document.createElement("button");
    if (!old) {
      b.type = "button";
      b.id = "deskFilterBtn";
      b.className = "db-filter";
      b.setAttribute("aria-haspopup", "true");
      b.setAttribute("aria-expanded", "false");
      b.setAttribute("aria-controls", "deskFilter");
      b.innerHTML = '<span class="db-f-name"></span><b></b><span class="db-chev" aria-hidden="true">▾</span>';
      var anchor = document.getElementById("deskSearchBtn") || h.lastElementChild;
      h.insertBefore(b, anchor);
    }
    b.querySelector(".db-f-name").textContent = "Filter";
    b.querySelector("b").textContent = on.length ? on.join(" · ") : "";
    b.classList.toggle("some", on.length > 0);
    b.setAttribute("aria-label", "Filter: " + name + (on.length ? " — " + on.join(", ") : ""));
    b.__host = host;
    b.__name = name;
  }

  // under its button, the right edges in line, inside the window
  function place(pop, btn) {
    var r = btn.getBoundingClientRect(), h = hdr().getBoundingClientRect();
    pop.style.top = (h.bottom + 6) + "px";
    pop.style.left = Math.max(8, Math.min(r.right - pop.offsetWidth, window.innerWidth - pop.offsetWidth - 8)) + "px";
  }

  function openFilter(btn) {
    var pop = document.getElementById("deskFilter"), host = btn.__host;
    if (!pop || !host) return;
    pop.innerHTML = "";
    var head = document.createElement("div");
    head.className = "db-pop-head";
    head.textContent = btn.__name;
    var wrap = document.createElement("div");
    // the host's own classes, so the chips look as they do on a phone
    wrap.className = host.className + " db-chips";
    chipsOf(host).forEach(function (c) {
      var x = document.createElement("button");
      x.type = "button";
      x.className = c.className;
      if (c.getAttribute("style")) x.setAttribute("style", c.getAttribute("style"));
      x.innerHTML = c.innerHTML;
      x.setAttribute("role", "menuitemcheckbox");
      x.setAttribute("aria-checked", c.classList.contains("on") ? "true" : "false");
      if (c.getAttribute("title")) x.title = c.getAttribute("title");
      x.addEventListener("click", function () {
        kitLayer.close(pop, function () { if (c.isConnected) c.click(); });
      });
      wrap.appendChild(x);
    });
    pop.appendChild(head);
    pop.appendChild(wrap);
    open(pop, btn, wrap.querySelector(".on") || wrap.firstChild);
  }

  function open(pop, btn, focusEl, after) {
    kitLayer.open(pop, {
      name: pop.id, lock: false, focus: focusEl || false,
      show: function () {
        pop.classList.add("open");
        place(pop, btn);
        btn.setAttribute("aria-expanded", "true");
      },
      close: function () {
        pop.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
        if (after) after();
      },
    });
  }

  function openSearch(btn) {
    var pop = document.getElementById("deskSearch"), form = document.getElementById("menuSearchForm");
    if (!pop || !form) return;
    pop.appendChild(form);
    var input = form.querySelector("input");
    open(pop, btn, input, function () {
      // back to the top of the menu, where a phone (and a narrowed window) has it
      var panel = document.getElementById("menuPanel");
      if (panel && form.parentNode !== panel) panel.insertBefore(form, panel.firstChild);
    });
    if (input) { input.focus(); input.select(); }
  }

  // ---- events (delegated: the buttons are replaced and moved) ---------------
  document.addEventListener("click", function (e) {
    var f = e.target.closest("#deskFilterBtn"), s = e.target.closest("#deskSearchBtn");
    var openPop = $(".desk-pop.open");
    if (f || s) {
      e.stopPropagation();
      var pop = document.getElementById(f ? "deskFilter" : "deskSearch");
      var wasOpen = openPop === pop;
      if (openPop) kitLayer.close(openPop);
      if (!wasOpen) (f ? openFilter : openSearch)(f || s);
      return;
    }
    if (openPop && !e.target.closest(".desk-pop")) kitLayer.close(openPop);
  });
  window.addEventListener("resize", function () {
    var p = $(".desk-pop.open");
    if (!p) return;
    var btn = document.getElementById(p.id === "deskFilter" ? "deskFilterBtn" : "deskSearchBtn");
    if (btn) place(p, btn);
  });

  DESK.addEventListener("change", function () {
    // the menu was placed for the other shape; let it go rather than float
    var panel = document.getElementById("menuPanel");
    if (panel && window.kitLayer && kitLayer.isOpen(panel)) kitLayer.close(panel);
    arrange();
  });
  document.addEventListener("htmx:beforeRequest", closePops);
  document.addEventListener("htmx:afterSettle", fold);
  document.addEventListener("htmx:historyRestore", arrange);
  document.addEventListener("pypen:more", fold);

  window.__deskbar = { arrange: arrange, fold: fold };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arrange);
  else arrange();
})();
