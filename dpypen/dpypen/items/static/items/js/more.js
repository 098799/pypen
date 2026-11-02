/* Load more (kit README §14, PYPEN-7; README "Lists").

   A paged list is a [data-more-host="<name>"] holding [data-more-section]s,
   each with a [data-group] and its rows in [data-more-rows], and under them
   the nav from templates/items/_more.html. "Load more" is a plain ?offset=
   link; here it is fetched with X-Pypen-More: 1, and the server answers with
   the same list for the next rows only. Their first section joins the last
   one on the page when it is the same group (the server leaves its heading
   out); the others are added after it. The nav is replaced by the new one.

   - A second tap while one is loading does nothing.
   - A failed load says so in the kit's "could not load" block under the
     button (kitEmpty.fail, templates/items/_empty.html), with the cause and
     Try again; the button keeps its label, so a tap on it tries again too.
   - Listens on the document, so a page swapped in by hx-boost needs nothing.
   - Fires "pypen:more" when rows were added (the jump strip rebuilds). */
(function () {
  if (window.__pypenMore) return;
  window.__pypenMore = true;

  function rowsOf(section) { return section.querySelector("[data-more-rows]"); }

  function merge(host, got) {
    var nav = host.querySelector("[data-more-nav]");
    var sections = host.querySelectorAll("[data-more-section]");
    var last = sections[sections.length - 1];
    var added = [];
    Array.prototype.forEach.call(got.querySelectorAll("[data-more-section]"), function (sec, i) {
      var same = i === 0 && last && sec.getAttribute("data-group") === last.getAttribute("data-group")
                 && !sec.querySelector("[data-more-head]") && rowsOf(last) && rowsOf(sec);
      if (same) {
        var into = rowsOf(last);
        Array.prototype.slice.call(rowsOf(sec).children).forEach(function (row) {
          into.appendChild(document.adoptNode(row));
          added.push(row);
        });
      } else {
        var node = document.adoptNode(sec);
        host.insertBefore(node, nav || null);
        added.push(node);
      }
    });

    var fresh = got.querySelector("[data-more-nav]");
    if (fresh) {
      fresh = document.adoptNode(fresh);
      // The count runs from where this page began, not from the new rows.
      var a = nav && nav.querySelector("[data-more-start]"), b = fresh.querySelector("[data-more-start]");
      if (a && b) b.textContent = a.textContent;
      // "From the start" only when this page did not begin at the start.
      if (nav && !nav.querySelector("[data-more-first]")) {
        var f = fresh.querySelector("[data-more-first]");
        if (f) f.remove();
      }
      if (!fresh.querySelector("[data-more]") && !fresh.querySelector("[data-more-first]")) fresh = null;
    }
    if (nav) nav.remove();
    if (fresh) host.appendChild(fresh);
    if (window.htmx && htmx.process) added.forEach(function (n) { htmx.process(n); });
    return added;
  }

  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[data-more]");
    if (!a || e.defaultPrevented || e.button > 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
    var host = a.closest("[data-more-host]");
    if (!host) return;
    e.preventDefault();
    if (a.getAttribute("aria-busy") === "true") return;   // a double tap asks once
    a.setAttribute("aria-busy", "true");
    var label = a.getAttribute("data-label") || a.textContent;
    a.setAttribute("data-label", label);
    a.textContent = "Loading…";
    var nav = a.closest("[data-more-nav]");
    var oldFail = nav && nav.querySelector("[data-more-fail]");
    var name = host.getAttribute("data-more-host");

    fetch(a.href, { headers: { "X-Pypen-More": "1" }, credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw r;
        return r.text();
      })
      .then(function (html) {
        var doc = new DOMParser().parseFromString(html, "text/html");
        var got = doc.querySelector('[data-more-host="' + name + '"]');
        if (!got) throw new Error("no rows");
        var added = merge(host, got);
        var first = added[0];
        var link = first && (first.matches("a[href]") ? first : first.querySelector("a[href]"));
        if (link) link.focus({ preventScroll: true });
        document.dispatchEvent(new CustomEvent("pypen:more", { detail: { host: host } }));
      })
      .catch(function (err) {
        a.removeAttribute("aria-busy");
        a.textContent = label;
        if (!nav || !window.kitEmpty) { a.textContent = "Could not load — try again"; return; }
        var slot = oldFail || nav.appendChild(document.createElement("div"));
        slot.setAttribute("data-more-fail", "");
        kitEmpty.fail(slot, err, function () { a.click(); }, {title: "More rows not loaded", small: true,
          text: err && err.message === "no rows" ? "The answer had no rows in it." : undefined});
      });
  });
})();
