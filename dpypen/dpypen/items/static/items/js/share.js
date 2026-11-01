/* Share buttons (PYPEN-3): one copy for every page, loaded by _shell.html.

   Markup: <button data-share-url="/p/<token>/"> — a path or a full url.
   A tap opens the phone's share sheet; with none (a desk browser) the link
   goes to the clipboard and the kit's toast says so; with no clipboard, a
   prompt holds the link to copy by hand.

   It listens on the document, so a page brought in by an hx-boost swap needs
   nothing. Until PYPEN-3 the pen page, the ink page and the inks list each
   pasted their own copy, which bound every share button on the page again
   and, on a desk, wrote "copied" over the inks list's icon button and put
   back only its text: the icon was gone until a reload. */
(function () {
  if (window.pypenShare) return;
  window.pypenShare = true;

  function byHand(url) { prompt("Share link:", url); }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-share-url]");
    if (!btn) return;
    var url = new URL(btn.getAttribute("data-share-url"), location.origin).href;
    if (navigator.share) {
      navigator.share({ title: document.title, url: url }).catch(function () {});
    } else if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(url).then(function () {
        if (window.kitToast) kitToast("Link copied");
      }, function () { byHand(url); });
    } else {
      byHand(url);
    }
    // From a record's ⋯ menu: the menu has done its job (it stayed open).
    var menu = btn.closest(".overflow-panel");
    if (menu && window.kitLayer && kitLayer.isOpen(menu)) kitLayer.close(menu);
  });
})();
