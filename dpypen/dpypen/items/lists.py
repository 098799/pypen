"""Lists that grow: paging, search words, accent folding, the highlighter (kit README §14).

KIT-LISTS: v1 2026-10-01

The canonical copy is ~/apps/kit/py/lists.py. Apps carry a byte-identical copy
(nothing may import across repos); `fleet-check` (check `kit`) warns when a
copy differs. Change the canonical file, bump the stamp, copy it out — never
edit a copy.

Why: by 2026-10-01 burn had paged and searched lists app by app in ~80 jobs,
and museum, pod, twitter (twice) and health each wrote their own fold, word
cap, LIKE escape, limit check or highlighter. They had drifted: pod's
highlighter did not fold accents, so "zurich" found "Zürich" and marked
nothing; one copy refused a long query, the others cut it. Stdlib only, no
framework:

    from .lists import fold, register, tokens, like, match_all, highlight
    register(conn)                        # fold(x) in this connection's SQL
    where, args = match_all(q, ["fold(p.title)", "p.text_fold"])
    rows = conn.execute(f"SELECT … WHERE {where} ORDER BY …, p.id "
                        "LIMIT ? OFFSET ?", [*args, limit, offset])
    return envelope(items, total, limit, offset)

    limit, offset = page_args(qs.get("limit"), qs.get("offset"))  # ListError -> 422
    page = clamp_page(page, total, per)  # ?page=10**30 is the last page, not a 500
    Markup(highlight(text, q))           # escaped, every word in <mark>

FastAPI routes keep `Query(50, ge=1, le=LIMIT_MAX)`: it already answers 422.
"""

from __future__ import annotations

import html
import re
import unicodedata

Q_MAX = 255         # a longer query is cut, not refused
TOKENS_MAX = 8      # every word must match; words after the 8th are dropped
LIMIT_DEFAULT = 50
LIMIT_MAX = 100     # the most a caller may ask for; more is a 422


class ListError(ValueError):
    """A list parameter the API refuses (the caller answers 422)."""


def fold(s) -> str:
    """Case- and accent-free, the same on both sides of a search:
    NFKD, drop the combining marks, casefold. "durer" finds "Dürer"."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


def register(conn) -> None:
    """Make `fold(x)` callable in this sqlite3 connection's SQL (cheap, idempotent)."""
    conn.create_function("fold", 1, fold, deterministic=True)


def tokens(q) -> list[str]:
    """The search words of `q` as typed: trimmed, cut to Q_MAX characters,
    at most TOKENS_MAX. Fold them (or use `like`) before comparing."""
    return (q or "").strip()[:Q_MAX].split()[:TOKENS_MAX]


def like(tok: str) -> str:
    """A LIKE pattern for one word: folded, `\\ % _` escaped, `%…%`.
    Use it with `LIKE ? ESCAPE '\\'` against a folded column or `fold(col)`."""
    t = fold(tok).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{t}%"


def match_all(q, fields: list[str]) -> tuple[str, list[str]]:
    """(WHERE fragment, args): every word of `q` matches at least one of
    `fields`, SQL expressions that give folded text (`fold(a.name)`, a stored
    `text_fold` column). No words: ("1", [])."""
    parts, args = [], []
    for tok in tokens(q):
        pat = like(tok)
        parts.append("(" + " OR ".join(f"{f} LIKE ? ESCAPE '\\'" for f in fields) + ")")
        args += [pat] * len(fields)
    return (" AND ".join(parts) or "1"), args


def _int(value, name: str, default: int) -> int:
    if isinstance(value, (list, tuple)):          # parse_qs gives lists
        value = value[-1] if value else None
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ListError(f"{name} must be a whole number") from None


def page_args(limit=None, offset=None, default: int = LIMIT_DEFAULT,
              cap: int = LIMIT_MAX) -> tuple[int, int]:
    """(limit, offset) from raw query values (str, int, None, or a parse_qs
    list). limit 1..cap, offset ≥ 0; anything else raises ListError (422)."""
    lim = _int(limit, "limit", default)
    off = _int(offset, "offset", 0)
    if not 1 <= lim <= cap:
        raise ListError(f"limit must be 1..{cap}")
    if off < 0:
        raise ListError("offset must be 0 or more")
    return lim, off


def envelope(items: list, total: int, limit: int, offset: int) -> dict:
    """The one list answer: {"items", "total", "limit", "offset"}."""
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def clamp_page(page, total: int, per: int) -> int:
    """A 1-based page number between 1 and the last page. Anything that is not
    a number is page 1; a huge number is the last page (SQLite raises
    OverflowError on an OFFSET past 2**63, which was a 500)."""
    try:
        page = int(page)
    except (TypeError, ValueError):
        return 1
    last = max(1, -(-max(0, total) // max(1, per)))
    return min(max(1, page), last)


def _folded_with_map(text: str) -> tuple[str, list[int]]:
    """`fold(text)` plus, for each folded character, the index it came from."""
    out, where = [], []
    for i, ch in enumerate(text):
        for c in fold(ch):
            out.append(c)
            where.append(i)
    return "".join(out), where


def highlight(text, q) -> str:
    """`text` HTML-escaped, every word of `q` wrapped in <mark>. Matches the
    raw text accent-folded, like the search; longest word first; escapes every
    piece, and escapes even when there is no query. Returns str: a Jinja
    filter wraps it in markupsafe.Markup."""
    text = "" if text is None else str(text)
    words = sorted({fold(t) for t in tokens(q)} - {""}, key=len, reverse=True)
    if not words:
        return html.escape(text)
    folded, where = _folded_with_map(text)
    hits = [False] * len(text)
    for m in re.finditer("|".join(re.escape(w) for w in words), folded):
        for k in range(m.start(), m.end()):
            hits[where[k]] = True
    out, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and hits[j] == hits[i]:
            j += 1
        piece = html.escape(text[i:j])
        out.append(f"<mark>{piece}</mark>" if hits[i] else piece)
        i = j
    return "".join(out)
