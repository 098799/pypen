"""Answers kept until the database changes (kit README §5.10).

KIT-DBMEMO: v1 2026-11-08

The canonical copy is ~/apps/kit/py/dbmemo.py. Apps carry a byte-identical
copy (nothing may import across repos); `fleet-check` (check `kit`) warns when
a copy differs. Change the canonical file, bump the stamp, copy it out — never
edit a copy.

Why: a page that counts or ranks over the whole database (a board, trends,
a summary) did the same work on every request, though what it reads changes
a few times an hour. Six apps each wrote their own "keep it until the DB
changes" (health, twitter, atlas, lemma, pod, weekends), and the copies
learned different lessons one at a time:

  - health: a stat of the -wal file is no version: SQLite deletes the WAL
    when the last connection closes, so the key moved on every request.
    `PRAGMA data_version` on one connection kept open for it is the version.
  - health, twitter: at the size limit they emptied the whole store, so one
    burst of new keys threw away every answer.
  - twitter: keys that carry the hour or a query piled up under versions
    that never come back (+13 MB a day) until the store was full.
  - atlas, lemma: eight threads that missed at once each made the same
    answer, and their reads queued on the GIL (0.8 s -> 49 s, 679 MB).
    One thread makes it, the others wait for it.
  - pod, twitter: never keep an answer read inside a transaction: it may
    hold this connection's own write, which can still roll back.
  - all: read the version before making the answer, so a commit in the
    middle leaves it filed under an old version (one extra make, never a
    stale answer).
  - weekends: an answer that reads the clock needs a `ttl`; one that may lag
    a sweep's commits by a minute takes `grace`; a thread can build answers
    again ahead of the request (`refresh`).

One piece, stdlib only:

    from .dbmemo import Memo
    memo = Memo()                       # version: PRAGMA data_version
    rows = memo.get(con, "trends", lambda: make_trends(con), days, today)

  - `get(con, name, make, *key, ttl=None, grace=0)` returns `make()`, made
    again only when the database behind `con` changed since (or the answer
    is older than `ttl` seconds). `grace`: an answer younger than this is
    still given after a change. Both are the asker's of the moment (the
    last ask's are what `refresh` goes by). The value is shared between requests:
    callers must not change it (or pass `copy=` to Memo).
  - `call(con, fn, *args, ttl=None, grace=0, key=())` = `fn(con, *args)`,
    kept the same way; `refresh(connect)` can build these again off the
    request path (a thread every few seconds), because it knows how.
  - `version=`: what "changed" means. The default, `data_version(con)`,
    moves on every commit to the file by any connection or process. An app
    whose worker commits a heartbeat every minute counts its real changes
    itself (triggers into a counter table, a max rowid) and passes
    `version=lambda con: (scope, n)`; `scope` names the database (so two
    test databases never share an answer; "" = keep nothing), `n` is
    compared (None is a version like any other: an empty table's MAX).
  - `changed()` lets go of every answer: for writes the version does not
    see (a custom version that watches some tables only, a file beside the
    DB).
  - `peek` / `put` for a writer that knows what its own write did to an
    answer; `forget(match)` lets go of some (yesterday's); `clear()` for
    tests; `len(memo)`.
  - Nothing is kept for an in-memory database (it has no path) or from
    inside a transaction. The store holds `max` answers, the least recently
    used go first, and answers made at an old version are swept when a new
    one is stored.

Tests: python3 -m pytest ~/apps/kit/py -q
"""

import os
import sqlite3
import threading
import time
from collections import OrderedDict

__all__ = ["Memo", "data_version", "close_watchers"]

_WATCH_MAX = 8  # watched files (an app has 1-3; tests make one each)
_watch_lock = threading.Lock()
_watch: OrderedDict = OrderedDict()  # path -> (file identity, connection)


def data_version(con):
    """(file, n): n moves whenever any connection, in this process or another,
    commits to the file behind `con`. Read on a connection of our own that
    never writes (a connection does not see its own commits in data_version).
    A file replaced under the same name (a restore, a test) is watched anew.
    `("", None)` for an in-memory or missing database: keep nothing.
    `con` may also be the file's path (an app that keeps no connection)."""
    if isinstance(con, (str, os.PathLike)):
        path = os.fspath(con)
    else:
        path = con.execute("PRAGMA database_list").fetchone()[2]
    if not path:
        return "", None
    try:
        st = os.stat(path)
    except OSError:
        return "", None
    ident = (st.st_dev, st.st_ino)
    with _watch_lock:
        hit = _watch.get(path)
        if hit is None or hit[0] != ident:
            if hit is not None:
                hit[1].close()
            w = sqlite3.connect(path, timeout=5, check_same_thread=False)
            w.execute("PRAGMA query_only=ON")
            hit = _watch[path] = (ident, w)
            while len(_watch) > _WATCH_MAX:
                _watch.popitem(last=False)[1][1].close()
        _watch.move_to_end(path)
        return path, (ident, hit[1].execute("PRAGMA data_version").fetchone()[0])


def close_watchers():
    """Close the watching connections (tests, shutdown)."""
    with _watch_lock:
        for _ident, w in _watch.values():
            w.close()
        _watch.clear()


class _Entry:
    __slots__ = ("n", "gen", "born", "used", "value", "ttl", "grace", "recipe")

    def __init__(self, n, gen, born, value, ttl, grace, recipe):
        self.n, self.gen, self.born, self.used = n, gen, born, born
        self.value, self.ttl, self.grace, self.recipe = value, ttl, grace, recipe

    def good(self, n, gen, now):
        if gen != self.gen:
            return False
        age = now - self.born
        if self.ttl is not None and age >= self.ttl:
            return False
        return n == self.n or age < self.grace


class _Flight:
    __slots__ = ("done", "ok", "value", "thread", "n", "gen")

    def __init__(self, n, gen):
        self.done = threading.Event()
        self.ok, self.value, self.thread = False, None, threading.get_ident()
        self.n, self.gen = n, gen


class Memo:
    """A store of answers keyed by (database, name, key); see the module doc."""

    def __init__(self, version=data_version, *, max=256, copy=None, clock=time.monotonic):
        self._version = version
        self.max = max
        self._copy = copy or (lambda v: v)
        self._clock = clock
        self._lock = threading.Lock()
        self._store: OrderedDict = OrderedDict()  # (scope, name, key) -> _Entry
        self._flights: dict = {}
        self._seen: dict = {}  # scope -> the newest n stored under it
        self._gen = 0

    def __len__(self):
        return len(self._store)

    # -- reading -------------------------------------------------------------

    def get(self, con, name, make, *key, ttl=None, grace=0.0):
        return self._get(con, name, key, make, ttl, grace, None)

    def call(self, con, fn, *args, ttl=None, grace=0.0, key=()):
        """`fn(con, *args)`, kept under fn's name, `args` and `key`."""
        return self._get(con, _name(fn), args + tuple(key),
                         lambda: fn(con, *args), ttl, grace, (fn, args))

    def peek(self, con, name, *key):
        """The kept answer if it is still good, else None. Nothing is made."""
        if getattr(con, "in_transaction", False):
            return None
        scope, n = self._version(con)
        if not scope:
            return None
        with self._lock:
            e = self._store.get((scope, name, key))
            if e is not None and e.good(n, self._gen, self._clock()):
                return self._copy(e.value)
        return None

    def _get(self, con, name, key, make, ttl, grace, recipe):
        if getattr(con, "in_transaction", False):
            return make()  # may read our own uncommitted write
        scope, n = self._version(con)  # before make(): see the module doc
        if not scope:
            return make()
        k = (scope, name, key)
        while True:
            with self._lock:
                gen, now = self._gen, self._clock()
                e = self._store.get(k)
                if e is not None:
                    e.ttl, e.grace = ttl, grace  # the asker says how fresh, now
                if e is not None and e.good(n, gen, now):
                    e.used = now
                    self._store.move_to_end(k)
                    return self._copy(e.value)
                fl = self._flights.get(k)
                lead = fl is None
                if lead:
                    fl = self._flights[k] = _Flight(n, gen)
            if lead:
                break
            if fl.thread == threading.get_ident():
                return make()  # make() asked for its own answer: no wait on ourselves
            fl.done.wait()
            if fl.ok and fl.n == n and fl.gen == self._gen:
                return self._copy(fl.value)
            # The leader failed, or made it at an older version than the one
            # this request read: try again (the store may have it by now).
        try:
            value = make()
            with self._lock:
                self._store_entry(k, _Entry(n, gen, self._clock(), value, ttl, grace, recipe))
            fl.value, fl.ok = value, True
            return self._copy(value)
        finally:
            with self._lock:
                self._flights.pop(k, None)
            fl.done.set()

    # -- writing -------------------------------------------------------------

    def put(self, con, name, value, *key, ttl=None, grace=0.0):
        """Keep `value` as the answer at the database's version now: for a
        writer that changed the answer itself (after its commit)."""
        if getattr(con, "in_transaction", False):
            return
        scope, n = self._version(con)
        if not scope:
            return
        with self._lock:
            self._store_entry((scope, name, key),
                              _Entry(n, self._gen, self._clock(), value, ttl, grace, None))

    def changed(self):
        """Every answer kept so far is out of date."""
        with self._lock:
            self._gen += 1
            self._store.clear()
            self._seen.clear()

    def clear(self):
        self.changed()

    def forget(self, match):
        """Let go of the answers for which `match(name, key)` is true (a
        day's answers after midnight). Returns how many."""
        with self._lock:
            gone = [k for k in self._store if match(k[1], k[2])]
            for k in gone:
                del self._store[k]
        return len(gone)

    def _store_entry(self, k, e):
        # Under self._lock.
        scope = k[0]
        if e.gen != self._gen:
            return  # changed() ran while it was being made
        if self._seen.get(scope, e.n) != e.n:
            # A new version for this scope: let go of what older ones made,
            # unless its grace still holds it (twitter's sweep, 2026-10-08).
            now = e.born
            for old in [x for x, v in self._store.items()
                        if x[0] == scope and v.n != e.n and now - v.born >= v.grace]:
                del self._store[old]
        self._seen[scope] = e.n
        self._store[k] = e
        self._store.move_to_end(k)
        while len(self._store) > self.max:
            self._store.popitem(last=False)

    # -- ahead of the request ------------------------------------------------

    def _due(self, con, e, now):
        _scope, n = self._version(con)
        age = now - e.born
        if e.ttl is not None and age >= e.ttl / 2:
            return True
        return n != e.n and age >= e.grace / 2

    def refresh(self, connect, idle=3600.0):
        """Build again, off the request path, what `call()` kept and a request
        would soon find too old: changed and past half its grace, or past half
        its ttl. Answers nobody asked for in `idle` seconds are dropped.
        `connect(scope)` opens a connection to that database (the scope is
        its path with the default version). Returns how many were built."""
        now = self._clock()
        with self._lock:
            items = list(self._store.items())
        built, cons = 0, {}
        try:
            for k, e in items:
                if now - e.used > idle:
                    with self._lock:
                        if self._store.get(k) is e:
                            del self._store[k]
                    continue
                if e.recipe is None:
                    continue
                con = cons.get(k[0])
                if con is None:
                    if not os.path.exists(k[0]):
                        with self._lock:  # its file is gone (a test's)
                            self._store.pop(k, None)
                        continue
                    con = cons[k[0]] = connect(k[0])
                if not self._due(con, e, now):
                    continue
                _scope, n = self._version(con)
                with self._lock:
                    gen = self._gen
                fn, args = e.recipe
                value = fn(con, *args)
                with self._lock:
                    fresh = _Entry(n, gen, self._clock(), value, e.ttl, e.grace, e.recipe)
                    fresh.used = e.used  # building is not asking
                    self._store_entry(k, fresh)
                built += 1
        finally:
            for con in cons.values():
                con.close()
        return built


def _name(fn):
    return getattr(fn, "__module__", "") + "." + getattr(fn, "__qualname__", repr(fn))
