"""The What's new log as a list API, by the kit's list rules (README §14).

KIT-WHATSNEW-PY: v2 2026-09-28

The canonical copy is ~/apps/kit/py/whatsnew.py. Apps carry a byte-identical
copy (fleet-check `kit` compares them): change this file, bump the stamp, copy
it out — never edit a copy. Stdlib only, no framework: a FastAPI route, an
http.server handler or anything else calls `answer()` with the query string.

The log itself stays a file in the repo (`whatsnew.json`, kit README §4). This
module answers questions about it:

    GET /whatsnew.json                       the whole file, as before
    GET /whatsnew.json?limit=10              a page: {"items","total","limit","offset"}
        &offset=0                            (limit 1..50, default 10; over 50 is an error)
        &q=dark theme                        every word must match title or use; case and
                                             accents are ignored ("zur" finds "Zürich")
        &sort=-date | date                   newest first by default; within a day, the
                                             file's order (it is newest first), so the
                                             last one written is on top
        &since=2026-08-01                    entries on or after a date
        &exclude_id=a&exclude_id=b           "Unread": leave out what this viewer has read
        &id=a&id=b                           resolve these entries

    status, body = answer(doc, query_string)   # 200 or 422, a dict to send as JSON

Why a server answer for a file of a few dozen entries: the log grows with every
feature, it is read on a phone, and every list in the fleet works one way (§14).
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qs

DEFAULT_LIMIT = 10
MAX_LIMIT = 50
MAX_Q = 255
MAX_TOKENS = 8
MAX_IDS = 200
SORTS = {"-date": True, "date": False}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class QueryError(ValueError):
    """A parameter the API refuses (the caller answers 422)."""


def fold(text: str) -> str:
    """Case- and accent-free form used on both sides of a search."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def tokens(q: str) -> list[str]:
    q = (q or "").strip()
    if len(q) > MAX_Q:
        raise QueryError(f"q is longer than {MAX_Q} characters")
    return [fold(t) for t in q.split()][:MAX_TOKENS]


def _one(params: dict, name: str, default: str = "") -> str:
    got = params.get(name) or [default]
    return got[-1]


def query(entries: list[dict], q: str = "", sort: str = "-date", since: str = "",
          exclude_ids: list[str] | None = None, ids: list[str] | None = None,
          limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict:
    """One page of the log, filtered, searched and sorted (the §14 envelope)."""
    if sort not in SORTS:
        raise QueryError(f"sort must be one of {', '.join(SORTS)}")
    if not 1 <= limit <= MAX_LIMIT:
        raise QueryError(f"limit must be 1..{MAX_LIMIT}")
    if offset < 0:
        raise QueryError("offset must be 0 or more")
    if since and not DATE.match(since):
        raise QueryError("since must be YYYY-MM-DD")
    if len(exclude_ids or []) > MAX_IDS or len(ids or []) > MAX_IDS:
        raise QueryError(f"at most {MAX_IDS} ids")
    words = tokens(q)
    # Each entry keeps its place in the file: entries carry a day, not a time, and
    # the file is newest first, so within a day its order is the only clock.
    pos = {id(e): i for i, e in enumerate(entries or [])}
    out = [e for e in entries if isinstance(e, dict) and e.get("id") and e.get("title") and e.get("date")]
    if ids:
        wanted = set(ids)
        out = [e for e in out if e["id"] in wanted]
    if exclude_ids:
        skip = set(exclude_ids)
        out = [e for e in out if e["id"] not in skip]
    if since:
        out = [e for e in out if str(e["date"])[:10] >= since]
    if words:
        out = [e for e in out if all(w in fold(f"{e.get('title', '')} {e.get('use', '')}") for w in words)]
    newest = SORTS[sort]
    # Date, then the place in the file, both in the same direction: pages never
    # shuffle. It was the id until v2 (2026-09-28), which put a day's entries in
    # the alphabet's order — the newest was as likely at the bottom as on top.
    out.sort(key=lambda e: (str(e["date"]), -pos[id(e)]), reverse=newest)
    return {"items": out[offset:offset + limit], "total": len(out), "limit": limit, "offset": offset}


def answer(doc: dict, query_string: str) -> tuple[int, dict]:
    """(status, JSON body) for GET /whatsnew.json?<query_string>. Without list
    parameters it is the file as it is, so older clients keep working."""
    params = parse_qs(query_string or "", keep_blank_values=True)
    list_keys = {"limit", "offset", "q", "sort", "since", "exclude_id", "id"}
    if not list_keys & params.keys():
        return 200, doc
    try:
        try:
            limit = int(_one(params, "limit", str(DEFAULT_LIMIT)))
            offset = int(_one(params, "offset", "0"))
        except ValueError:
            raise QueryError("limit and offset must be whole numbers") from None
        page = query(doc.get("entries") or [], q=_one(params, "q"), sort=_one(params, "sort", "-date"),
                     since=_one(params, "since"), exclude_ids=[i for i in params.get("exclude_id", []) if i],
                     ids=[i for i in params.get("id", []) if i], limit=limit, offset=offset)
    except QueryError as e:
        return 422, {"detail": str(e)}
    return 200, {"app": doc.get("app"), **page}
