/* The charts' one tip, the reading of a line and the key's highlight (PYPEN-10).
   Markup only, so an hx-boost swap needs nothing: it listens on the document.

   Any element with data-tip-title (the calendar's days, the matrix's cells,
   a bar, a square of the month grid):
     data-tip-lead   the number, strong
     data-tip        more lines, one to a line
     data-tip-links  "Label|/url", one to a line

   A mouse: it shows on hover and follows the pointer's mark. A tap or a click: it
   stays, as a kit layer (lock: false, as the Gantt's popup): Back, Esc and a tap
   elsewhere close it. Stored names go in as text, never as markup. */
(function () {
  "use strict";

  function tip() {
    var t = document.getElementById("chartTip");
    if (t) return t;
    t = document.createElement("div");
    t.id = "chartTip";
    t.className = "chart-tip";
    t.setAttribute("role", "status");
    document.body.appendChild(t);
    return t;
  }

  function add(parent, cls, text) {
    var e = parent.appendChild(document.createElement("div"));
    e.className = cls;
    e.textContent = text;
    return e;
  }

  function fill(t, mark) {
    t.textContent = "";
    add(t, "ct-title", mark.getAttribute("data-tip-title"));
    var lead = mark.getAttribute("data-tip-lead");
    if (lead) add(t, "ct-lead", lead);
    (mark.getAttribute("data-tip") || "").split("\n").forEach(function (l) {
      if (l) add(t, "ct-line", l);
    });
    var links = (mark.getAttribute("data-tip-links") || "").split("\n").filter(Boolean);
    if (links.length) {
      var row = add(t, "ct-links", "");
      links.forEach(function (l) {
        var cut = l.indexOf("|");
        var a = row.appendChild(document.createElement("a"));
        a.textContent = l.slice(0, cut);
        a.href = l.slice(cut + 1);
      });
    }
  }

  function place(t, mark) {
    var r = mark.getBoundingClientRect();
    var w = t.offsetWidth, h = t.offsetHeight, m = 8;
    var left = Math.max(m, Math.min(innerWidth - w - m, r.left + r.width / 2 - w / 2));
    var top = r.bottom + m;
    if (top + h > innerHeight - m) top = Math.max(m, r.top - h - m);
    t.style.left = left + "px";
    t.style.top = top + "px";
  }

  function pinned() {
    var t = document.getElementById("chartTip");
    return t && window.kitLayer && kitLayer.isOpen(t);
  }

  function show(mark) {
    var t = tip();
    fill(t, mark);
    t.classList.add("open");
    place(t, mark);
  }

  function hide() {
    if (pinned()) return;
    var t = document.getElementById("chartTip");
    if (t) t.classList.remove("open");
  }

  document.addEventListener("pointerover", function (e) {
    if (e.pointerType !== "mouse" || pinned()) return;
    var mark = e.target.closest && e.target.closest("[data-tip-title]");
    if (mark) show(mark); else if (!(e.target.closest && e.target.closest("#chartTip"))) hide();
  });

  document.addEventListener("focusin", function (e) {
    if (pinned()) return;
    var mark = e.target.closest && e.target.closest("[data-tip-title]");
    if (mark && mark.matches(":focus-visible")) show(mark);
  });
  document.addEventListener("focusout", function (e) {
    if (e.target.closest && e.target.closest("[data-tip-title]")) hide();
  });

  document.addEventListener("click", function (e) {
    var mark = e.target.closest("[data-tip-title]");
    var t = document.getElementById("chartTip");
    if (!mark) {
      if (pinned() && !e.target.closest("#chartTip")) kitLayer.close(t);
      return;
    }
    show(mark);
    t = tip();
    if (!pinned() && window.kitLayer) {
      kitLayer.open(t, {
        name: "chart-tip", lock: false, focus: false,
        show: function () { t.classList.add("open"); },
        close: function () { t.classList.remove("open"); },
      });
    }
  });

  // A swap takes the marks away.
  document.addEventListener("htmx:beforeSwap", function () {
    var t = document.getElementById("chartTip");
    if (t && !pinned()) t.classList.remove("open");
  });

  /* The key: a tap keeps one ink family lit in its chart; a second tap, all. */
  document.addEventListener("click", function (e) {
    var key = e.target.closest(".fam-key");
    if (!key) return;
    var chart = key.closest("[data-stack-chart]");
    var on = key.getAttribute("aria-pressed") !== "true";
    chart.querySelectorAll(".fam-key").forEach(function (k) {
      k.setAttribute("aria-pressed", String(on && k === key));
    });
    var fam = on ? key.getAttribute("data-fam") : null;
    chart.classList.toggle("is-picked", on);
    chart.querySelectorAll(".bar-stack i").forEach(function (i) {
      i.classList.toggle("is-lit", i.getAttribute("data-fam") === fam);
    });
  });

  /* A line: a hairline at the finger or the pointer, the reading in the chart's
     subtitle. Arrow keys when it has focus. */
  var MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function read(chart, i) {
    var values = chart.getAttribute("data-values").split(",");
    i = Math.max(0, Math.min(values.length - 1, i));
    chart._i = i;
    var start = chart.getAttribute("data-start").split("-").map(Number);
    var step = +chart.getAttribute("data-step");
    var d = new Date(Date.UTC(start[0], start[1] - 1, start[2] + i * step));
    var cross = chart.querySelector("[data-line-cross]");
    cross.hidden = false;
    cross.style.left = (values.length > 1 ? 100 * i / (values.length - 1) : 0) + "%";
    var when = (step > 1 ? "" : d.getUTCDate() + " ") + MONTH[d.getUTCMonth()] + " " + d.getUTCFullYear();
    var n = values[i];
    chart.closest(".chart-box").querySelector("[data-line-read]").textContent = when + ": " + n + (n === "1" ? " pen" : " pens");
  }

  function at(chart, x) {
    var plot = chart.querySelector(".line-plot").getBoundingClientRect();
    var n = chart.getAttribute("data-values").split(",").length;
    read(chart, Math.round((x - plot.left) / plot.width * (n - 1)));
  }

  document.addEventListener("pointermove", function (e) {
    var chart = e.target.closest && e.target.closest("[data-line]");
    if (chart) at(chart, e.clientX);
  });
  document.addEventListener("pointerdown", function (e) {
    var chart = e.target.closest && e.target.closest("[data-line]");
    if (chart) at(chart, e.clientX);
  });
  document.addEventListener("keydown", function (e) {
    var chart = e.target.closest && e.target.closest("[data-line]");
    if (!chart || (e.key !== "ArrowLeft" && e.key !== "ArrowRight")) return;
    e.preventDefault();
    e.stopPropagation();
    var n = chart.getAttribute("data-values").split(",").length;
    var from = chart._i === undefined ? n - 1 : chart._i;
    read(chart, from + (e.key === "ArrowRight" ? 1 : -1));
  }, true);
})();
