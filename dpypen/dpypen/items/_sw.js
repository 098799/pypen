/* KIT-SW: v1.2 2026-10-26
  The service worker of every app: offline, and the pages kept on the phone.
  Spec: ~/apps/kit/README.md §4, "Offline". Canonical copy:
  ~/apps/kit/snippets/sw.js. Apps carry a byte-identical copy (fleet-check
  `kit` compares them): change this file, bump the stamp here and in
  `VERSION` below, copy it out. Never edit a copy.

  Why a piece of our own: 25 apps had 25 workers (AUDIT.md, 2026-10-26). Offline,
  five showed the browser's error page, two said "no such page", one showed its
  home page for any address, one answered its own health check with a page and
  so reloaded every 8 s; four cached error pages or JSON; three kept pages
  without a bound; five versions were hand-bumped constants, already forgotten.

  How an app uses it. The worker the page registers is the app's settings,
  then this file (the server puts the text in, or `importScripts`):

    self.KITSW = {
      app: "pod",                  // cache names 'kit-pod-pages', '-files', '-precache'
      build: "3f2a9c",             // changes on a deploy, so the worker's bytes do and
                                   // update.html can offer it (static folders: none)
      name: "pod",                 // the offline page's heading (default: app)
      where: "tailnet",            // "tailnet" (p340), "internet" (public on bae) or
                                   // "home" (a guest door on the home wifi)
      colors: {dark: {bg, fg, dim, accent, line}, light: {…}},
                                   // the offline page's look; only one key = one theme
      theme: "podTheme",           // the chooser's localStorage key (default '<app>Theme')
      lang: "en",                  // "en" | "pl" | "tr"; labels: {…} for single words
      precache: ["/offline-ok", "/static/app.css"],
                                   // fetched at install one by one into a cache that
                                   // holds just this list; a 404 is skipped, never fatal
      files: ["/static/"],         // path prefixes of same-origin files kept for offline
                                   // (CSS, JS, fonts, icons); ["/"] = every file
      skip: ["/api/"],             // path prefixes never touched (JSON, media, OAuth)
      shell: "/",                  // one-page apps: a navigation with no copy gets this
                                   // kept page, and the app draws the route offline
      takeover: false,             // true: a new worker takes over at install (no
                                   // update.html); else it waits for 'SKIP_WAITING'
      keep: ["pod-kept"],          // the app's own caches: activate leaves them alone
      max: {pages: 60, files: 400},
      wait: 0,                     // ms a page or a file waits for the network before
                                   // the kept copy is used (0: until it fails)
      bar: true,                   // false: no "Kept copy" bar (a kid's toy)
    };

  /sw.js goes out `no-cache`, as JavaScript, and is public in a gated app.

  What it does:
    pages    same-origin navigations: the network first. An ok HTML answer that is
             not a redirect, not no-store and not /login is kept, newest `max.pages`.
             The network fails (or slower than `wait`) → the copy of that address,
             with a bar "Kept copy from 14:05 · Try again"; else its precached copy;
             else the shell; else the offline page. A 502/503/504 (nginx: the app is down) → the copy, else
             the offline page. A 401 forgets every kept page
    files    `files` prefixes and `precache`: the network first (within `wait`) and
             kept; the copy when it fails or answers 5xx, the newest one first. A `?v=` URL is content-addressed (kit caching.py): the
             copy first. Never a page for a file: a miss offline is a network error
    never    writes, other origins, Range (audio, video), `skip`, everything else
    offline  a page in the app's colours and chosen theme: the app's name, why
             (p340 is not reachable — the tailnet, or no connection), Try again (also by itself when the
             phone is back online), and links to the pages kept here. 503, not kept
    update   'SKIP_WAITING' → skipWaiting(). activate deletes the origin's caches
             that are not a kit worker's (the old hand-made ones) and not in `keep`,
             then claims the open pages. 'KIT_FORGET' drops pages, files and the precache
             (sign-out)

  Hooks, in the app's part of the worker (after this file):
    kitSW.route(function (event, url) { return response | promise | undefined; })
             asked first for every GET of this origin, Range ones too (pod's kept
             audio, a board);
             undefined = the kit decides
      kitSW.offline(url) → the offline page for that URL, a Promise of a Response
    kitSW.keep(event, request, response) keeps a page; kitSW.withBar(copy) adds the bar
*/
(function () {
  'use strict';
  var VERSION = 'v1.2 2026-10-26';
  var C = self.KITSW || {};
  var APP = C.app || 'app';
  var PAGES = 'kit-' + APP + '-pages';
  var FILES = 'kit-' + APP + '-files';
  var PRE = 'kit-' + APP + '-precache';
  var MAX = Object.assign({pages: 60, files: 400}, C.max || {});
  var SKIP = C.skip || [];
  var FILE_PREFIXES = C.files || [];
  var SCOPE = new URL(self.registration.scope).pathname;
  var NEVER = ['/login', '/logout', SCOPE + 'login', SCOPE + 'logout'];   // the gate's pages: never kept
  var PRECACHE = (C.precache || []).map(function (u) { return new URL(u, self.location).href; });
  var KEEP = C.keep || [];
  var BAR_CSS = SCOPE + 'kit-sw-kept.css';
  var routes = [];

  var WORDS = {
    en: {tailnet: 'p340 is not reachable — is the phone on the tailnet?',
         internet: 'No connection — is the phone online?', again: 'Try again',
         home: 'Not reachable — is the phone on the home wifi?',
         kept: 'Kept on this device', title: 'offline', copy: 'Kept copy from %s', back: 'Back to %s',
         auto: 'It tries again by itself when the phone is back online.'},
    pl: {tailnet: 'p340 nie odpowiada — czy telefon jest w tailnecie?',
         internet: 'Brak połączenia — czy telefon jest online?', again: 'Spróbuj ponownie',
         home: 'Brak połączenia — czy telefon jest w domowym wifi?',
         kept: 'Zapisane na tym urządzeniu', title: 'offline', copy: 'Kopia z %s', back: 'Wróć do: %s',
         auto: 'Spróbuje sam, gdy telefon wróci do sieci.'},
    tr: {tailnet: 'p340 erişilemiyor — telefon tailnet’te mi?',
         internet: 'Bağlantı yok — telefon çevrimiçi mi?', again: 'Tekrar dene',
         home: 'Erişilemiyor — telefon ev wifi’sinde mi?',
         kept: 'Bu cihazda saklananlar', title: 'çevrimdışı', copy: '%s tarihli kopya', back: 'Geri: %s',
         auto: 'Telefon yeniden bağlanınca kendisi dener.'},
  };
  var LANG = WORDS[C.lang] ? C.lang : 'en';
  var L = Object.assign({}, WORDS[LANG], C.labels || {});

  function under(p, list) {
    for (var i = 0; i < list.length; i++) if (p === list[i] || p.indexOf(list[i]) === 0) return true;
    return false;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }
  function keepable(resp) {
    return !!resp && resp.status === 200 && !resp.redirected && resp.type === 'basic' &&
      !/no-store/i.test(resp.headers.get('Cache-Control') || '');
  }
  function html(resp) {
    return (resp.headers.get('Content-Type') || '').indexOf('text/html') === 0;
  }
  function noop() {}
  // An answer nobody reads holds its connection: six of them and every fetch
  // of the origin waits (health's no-store icons at install, 2026-10-26).
  function drop(resp) {
    try { if (resp && resp.body && !resp.bodyUsed) resp.body.cancel().catch(noop); } catch (e) {}
  }

  // Oldest out: Cache Storage lists keys in insertion order, so a key put
  // again is deleted first to move it to the end.
  function put(name, req, resp, max) {
    return caches.open(name).then(function (cache) {
      return cache.delete(req).then(function () { return cache.put(req, resp); })
        .then(function () { return cache.keys(); })
        .then(function (keys) {
          var out = [];
          for (var i = 0; i < keys.length - max; i++) out.push(cache.delete(keys[i]));
          return Promise.all(out);
        });
    }).catch(noop);
  }

  // A kept page remembers when; its own headers (no framing, CSP) stay.
  function stamped(resp) {
    var h = new Headers(resp.headers);
    h.set('X-Kit-Kept-At', String(Date.now()));
    return new Response(resp.body, {status: resp.status, statusText: resp.statusText, headers: h});
  }

  // Newest first: what the network gave since (pages, files) before what the
  // install fetched (precache). caches.match() would ask in creation order.
  function match(req, names) {
    var i = 0;
    function next() {
      if (i >= names.length) return Promise.resolve(undefined);
      return caches.open(names[i++]).then(function (c) { return c.match(req); })
        .then(function (hit) { return hit || next(); }, next);
    }
    return next();
  }

  function forget() {
    return Promise.all([caches.delete(PAGES), caches.delete(FILES), caches.delete(PRE)]).catch(noop);
  }

  // ---- the offline page and the kept-copy bar ----------------------------

  var DARK = {bg: '#0d1117', fg: '#e6edf3', dim: '#8b9bb0', accent: '#58a6ff', line: '#30363d'};
  var LIGHT = {bg: '#f6f7f9', fg: '#1b1f24', dim: '#57606a', accent: '#0969da', line: '#d0d7de'};

  function vars(c) {
    return '--bg:' + c.bg + ';--fg:' + c.fg + ';--dim:' + c.dim + ';--accent:' + c.accent + ';--line:' + c.line;
  }

  function keptPages() {
    return caches.open(PAGES).then(function (cache) {
      return cache.keys().then(function (keys) {
        return Promise.all(keys.slice(-8).reverse().map(function (req) {
          return cache.match(req).then(function (resp) {
            return resp ? resp.text() : '';
          }).then(function (text) {
            var m = /<title[^>]*>([^<]{1,160})<\/title>/i.exec(text);
            var u = new URL(req.url);
            return {href: u.pathname + u.search, title: m ? m[1].trim() : u.pathname};
          });
        }));
      });
    }).catch(function () { return []; });
  }

  function offlinePage(url) {
    var colors = C.colors || {}, d = colors.dark, l = colors.light;
    var only = d && !l ? 'dark' : (l && !d ? 'light' : '');   // a one-theme app
    var dark = Object.assign({}, DARK, d || l || {});
    var light = Object.assign({}, LIGHT, l || d || {});
    var name = C.name || APP;
    var key = C.theme || (APP + 'Theme');
    // A way back to the app's first page (its kept copy or shell), from any other address.
    var away = url && url.pathname !== SCOPE ? '<a class="alt" href="' + esc(SCOPE) + '">' +
      esc(L.back.replace('%s', name)) + '</a>' : '';
    return keptPages().then(function (kept) {
      // The titles come from the kept pages' own markup, so they are already
      // escaped text; the regex let no '<' through.
      var list = kept.length ? '<h2>' + esc(L.kept) + '</h2><ul>' + kept.map(function (k) {
        return '<li><a href="' + esc(k.href) + '">' + k.title + '</a></li>';
      }).join('') + '</ul>' : '';
      var body = '<!doctype html><html lang="' + LANG + '" data-theme="dark"><head><meta charset="utf-8">' +
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">' +
        '<meta name="theme-color" content="' + esc(dark.bg) + '">' +
        '<title>' + esc(name) + ' · ' + esc(L.title) + '</title>' +
        '<script>(function(){var m=' + JSON.stringify(only || 'dark') + ';try{m=localStorage.getItem(' +
        JSON.stringify(key) + ')||m}catch(e){}' +
        'if(m!=="dark"&&m!=="light")m=matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";' +
        (only ? 'm=' + JSON.stringify(only) + ';' : '') +
        'document.documentElement.setAttribute("data-theme",m);document.querySelector("meta[name=theme-color]")' +
        '.content=m==="light"?' + JSON.stringify(light.bg) + ':' + JSON.stringify(dark.bg) + '})()</script>' +
        '<style>:root{' + vars(dark) + ';color-scheme:dark}' +
        'html[data-theme=light]{' + vars(light) + ';color-scheme:light}' +
        'body{margin:0;min-height:100vh;min-height:100dvh;display:flex;align-items:center;justify-content:center;' +
        'padding:24px 16px calc(24px + env(safe-area-inset-bottom));box-sizing:border-box;background:var(--bg);' +
        'color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;text-align:center}' +
        'main{width:100%;max-width:24rem}h1{font-size:20px;margin:0 0 8px}p{color:var(--dim);margin:0 0 6px}' +
        'button{font:inherit;font-weight:600;min-height:44px;min-width:44px;margin:16px 0 4px;padding:10px 22px;' +
        'border-radius:10px;border:1px solid var(--accent);background:var(--accent);color:var(--bg);cursor:pointer}' +
        '.auto{font-size:13px}h2{font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;' +
        'color:var(--dim);margin:28px 0 6px}ul{list-style:none;margin:0;padding:0;text-align:left;' +
        'border-top:1px solid var(--line)}li{border-bottom:1px solid var(--line)}a{display:block;padding:12px 4px;' +
        'color:var(--fg);text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
        'a:hover,a:focus-visible{color:var(--accent)}a.alt{display:inline-flex;align-items:center;' +
        'min-height:44px;padding:0 18px;margin:4px 0 0;border:1px solid var(--line);border-radius:10px;' +
        'white-space:normal}</style></head>' +
        '<body><main id="kit-offline" data-kit-sw="' + VERSION + '"><h1>' + esc(name) + '</h1>' +
        '<p>' + esc(L[C.where] || L.tailnet) + '</p>' +
        '<button type="button" onclick="location.reload()">' + esc(L.again) + '</button>' + (away ? '<br>' + away : '') +
        '<p class="auto">' + esc(L.auto) + '</p>' + list + '</main>' +
        '<script>addEventListener("online",function(){location.reload()})</script></body></html>';
      return new Response(body, {status: 503, headers: {
        'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store',
        'X-Frame-Options': 'DENY', 'Content-Security-Policy': "frame-ancestors 'none'",
        'X-Content-Type-Options': 'nosniff'}});
    });
  }

  // The bar on a kept copy: plain markup and a stylesheet this worker answers,
  // so a page whose CSP allows no inline script or style shows it too.
  var BAR = '#kit-kept{position:fixed;z-index:2147483000;top:calc(8px + env(safe-area-inset-top));' +
    'left:50%;transform:translateX(-50%);max-width:calc(100vw - 32px);box-sizing:border-box;display:flex;' +
    'align-items:center;gap:10px;padding:4px 4px 4px 14px;border-radius:999px;background:#1f2328;color:#f0f3f6;' +
    'border:1px solid #57606a;box-shadow:0 4px 16px rgba(0,0,0,.35);font:600 13px/1.3 system-ui,-apple-system,' +
    '"Segoe UI",sans-serif;white-space:nowrap}#kit-kept span{overflow:hidden;text-overflow:ellipsis}' +
    '#kit-kept a{display:inline-flex;align-items:center;min-height:36px;padding:0 14px;border-radius:999px;' +
    'background:#f0f3f6;color:#1f2328;text-decoration:none}@media print{#kit-kept{display:none}}';

  function when(ms) {
    var t = new Date(ms), now = new Date();
    var opts = t.toDateString() === now.toDateString() ? {hour: '2-digit', minute: '2-digit'}
      : {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'};
    try { return t.toLocaleString(LANG, opts); } catch (e) { return t.toISOString().slice(0, 16).replace('T', ' '); }
  }

  function withBar(resp) {
    var at = Number(resp.headers.get('X-Kit-Kept-At')) || 0;
    if (!at || !html(resp) || C.bar === false) return Promise.resolve(resp);
    return resp.text().then(function (text) {
      var bar = '<link rel="stylesheet" href="' + BAR_CSS + '"><div id="kit-kept" role="status"><span>' +
        esc(L.copy.replace('%s', when(at))) + '</span><a href="">' + esc(L.again) + '</a></div>';
      var i = text.lastIndexOf('</body>');
      text = i < 0 ? text + bar : text.slice(0, i) + bar + text.slice(i);
      var h = new Headers(resp.headers);
      h.delete('Content-Length');
      return new Response(text, {status: 200, headers: h});
    });
  }

  // ---- strategies --------------------------------------------------------

  function late(promise, ms) {            // rejects after ms; the fetch goes on
    if (!ms) return promise;
    return new Promise(function (resolve, reject) {
      setTimeout(function () { reject(new Error('slow')); }, ms);
      promise.then(resolve, reject);
    });
  }

  function page(event, url) {
    var req = event.request;
    var live = fetch(req).then(function (resp) {
      if (resp.status === 401) event.waitUntil(caches.delete(PAGES).catch(noop));
      else if (keepable(resp) && html(resp) && !under(url.pathname, NEVER)) {
        event.waitUntil(put(PAGES, req, stamped(resp.clone()), MAX.pages));
      }
      if (resp.status >= 502 && resp.status <= 504) {   // nginx: the app is down or restarts
        drop(resp);
        return caches.match(req, {cacheName: PAGES}).then(function (hit) {
          return hit ? withBar(hit) : caches.match(req, {cacheName: PRE});
        }).then(function (hit) { return hit || offlinePage(url); });
      }
      return resp;
    });
    event.waitUntil(live.catch(noop));      // a slow answer still refreshes the copy
    return late(live, C.wait).catch(function () {
      return caches.match(req, {cacheName: PAGES}).then(function (hit) {
        if (hit) return withBar(hit);
        return caches.match(req, {cacheName: PRE});
      }).then(function (hit) {
        if (hit) return hit;
        var shell = C.shell ? match(new URL(C.shell, self.location).href, [PAGES, PRE]) : Promise.resolve();
        return shell.then(function (s) {
          // After `wait`, a slow network still beats the offline page.
          return s || live.catch(function () { return offlinePage(url); });
        });
      });
    });
  }

  function file(event, url) {
    var req = event.request;
    function fromNet() {
      return fetch(req).then(function (resp) {
        if (keepable(resp)) event.waitUntil(put(FILES, req, resp.clone(), MAX.files));
        if (resp.status >= 500) {                      // the app is down: the copy is better
          return match(req, [FILES, PRE]).then(function (h) {
            if (h) drop(resp);
            return h || resp;
          });
        }
        return resp;
      });
    }
    var hit = match(req, [FILES, PRE]);
    if (/[?&]v=/.test(url.search)) return hit.then(function (h) { return h || fromNet(); });
    var live = fromNet();
    event.waitUntil(live.catch(noop));
    return late(live, C.wait).catch(function () {
      return hit.then(function (h) { return h || live; });
    });
  }

  // ---- events ------------------------------------------------------------

  self.addEventListener('install', function (event) {
    event.waitUntil(caches.open(PRE).then(function (cache) {
      // What is no longer listed goes (an old ?v=, a page dropped from the list).
      return cache.keys().then(function (keys) {
        return Promise.all(keys.filter(function (k) { return PRECACHE.indexOf(k.url) < 0; })
          .map(function (k) { return cache.delete(k); }));
      }).then(function () { return cache; });
    }).then(function (cache) {
      return Promise.all(PRECACHE.map(function (u) {
        return fetch(u, {cache: 'no-cache'}).then(function (resp) {
          // The app listed it: kept even when no-store (health's icons).
          if (resp.status === 200 && !resp.redirected && resp.type === 'basic') return cache.put(u, resp);
          drop(resp);
        }).catch(noop);
      }));
    }).then(function () {
      if (C.takeover) return self.skipWaiting();
    }));
  });

  self.addEventListener('activate', function (event) {
    event.waitUntil(caches.keys().then(function (names) {
      return Promise.all(names.filter(function (n) {
        return n.indexOf('kit-') !== 0 && KEEP.indexOf(n) < 0;
      }).map(function (n) { return caches.delete(n); }));
    }).catch(noop).then(function () { return self.clients.claim(); }));
  });

  self.addEventListener('message', function (event) {
    var m = event.data && (event.data.type || event.data);
    if (m === 'SKIP_WAITING') self.skipWaiting();
    else if (m === 'KIT_FORGET') event.waitUntil(forget());
  });

  self.addEventListener('fetch', function (event) {
    var req = event.request;
    if (req.method !== 'GET') return;
    var url = new URL(req.url);
    if (url.origin !== self.location.origin) return;
    if (url.pathname === BAR_CSS) {
      return event.respondWith(new Response(BAR, {headers: {'Content-Type': 'text/css; charset=utf-8'}}));
    }
    for (var i = 0; i < routes.length; i++) {      // Range too: pod slices its kept audio
      var r = routes[i](event, url);
      if (r) return event.respondWith(Promise.resolve(r));
    }
    if (req.headers.has('Range') || under(url.pathname, SKIP)) return;
    if (req.mode === 'navigate') return event.respondWith(page(event, url));
    if (under(url.pathname, FILE_PREFIXES) || PRECACHE.indexOf(url.href) >= 0) {
      return event.respondWith(file(event, url));
    }
  });

  self.kitSW = {
    version: VERSION,
    route: function (fn) { routes.push(fn); },
    offline: offlinePage,
    forget: forget,
    // For a hook that answers pages itself (twitter's /unread, pod's episodes):
    keep: function (event, req, resp) {          // keep an ok page as the kit does
      if (keepable(resp) && html(resp)) event.waitUntil(put(PAGES, req, stamped(resp.clone()), MAX.pages));
    },
    withBar: withBar,                            // a kept copy, with its bar
    caches: {pages: PAGES, files: FILES, precache: PRE},
  };
})();
