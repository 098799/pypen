"""The app's side of the kit's lists (kit README §14, `lists.py` KIT-LISTS).

`lists.py` is the kit's byte copy and knows nothing of Django. This module is
the seam between the two, so every list in pypen pages, searches and answers
the same way:

- `fold()` is registered on every SQLite connection Django opens
  (`connection_created`, wired in `apps.ItemsConfig.ready`), so a search
  field is `fold(<column>)` in SQL and "zur" finds "Zürich".
- `search(qs, q, fields)` adds `lists.match_all`: every word of `q` must be
  in one of `fields`. A field is a column of the model (`"model"`) or of the
  row a foreign key points at (`"brand.name"`, a correlated subquery, so the
  WHERE stays plain and nothing goes into a GROUP BY).
- `page_args(request)` reads `?limit=&offset=`; a bad value raises
  `lists.ListError`, which `ListErrors` answers with a 422 (JSON under /api/,
  the error page otherwise).
- `heads(rows, key, prev)` marks the rows that open a group, so a page that
  starts in the middle of a group (Load more, a bookmarked offset) does not
  repeat its heading.

The Load more button is `templates/items/_more.html`; `static/items/js/more.js`
fetches the next page and appends it.
"""

from __future__ import annotations

from django.db.backends.signals import connection_created
from django.http import JsonResponse

from dpypen.items import lists
from dpypen.items.lists import LIMIT_DEFAULT, LIMIT_MAX, ListError, envelope  # noqa: F401  (re-exported)


def _register(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        lists.register(connection.connection)


def wire():
    """Called once from ItemsConfig.ready()."""
    connection_created.connect(_register, dispatch_uid="pypen-lists-fold")


def _expr(model, alias: str, path: list[str], depth: int = 0) -> str:
    """The SQL value of `path` (field names, foreign keys first) on the row
    `alias` of `model`; each foreign key is a correlated subquery."""
    field = model._meta.get_field(path[0])
    if len(path) == 1:
        return f'"{alias}"."{field.column}"'
    rel = field.related_model
    sub = f"lt{depth}"
    inner = _expr(rel, sub, path[1:], depth + 1)
    return (f'(SELECT {inner} FROM "{rel._meta.db_table}" AS "{sub}" '
            f'WHERE "{sub}"."{rel._meta.pk.column}" = "{alias}"."{field.column}")')


def column(model, field: str) -> str:
    """SQL for one searchable field, folded. `field` is a column of the model
    (`"model"`) or a path through foreign keys (`"brand.name"`,
    `"pen.brand.name"`)."""
    return f"fold({_expr(model, model._meta.db_table, field.split('.'))})"


def search(qs, q, fields: list[str]):
    """`qs` narrowed to the rows where every word of `q` is in some field."""
    if not lists.tokens(q):
        return qs
    where, args = lists.match_all(q, [column(qs.model, f) for f in fields])
    # match_all writes sqlite3's `?`; Django's raw SQL takes `%s`. The
    # fragment has no other `?` (the fields are column SQL from `column`).
    return qs.extra(where=[where.replace("?", "%s")], params=args)


def page_args(request, default: int = LIMIT_DEFAULT) -> tuple[int, int]:
    return lists.page_args(request.GET.get("limit"), request.GET.get("offset"), default=default)


def is_more(request) -> bool:
    """The Load more button asking for the next rows only."""
    return request.headers.get("X-Pypen-More") == "1"


def heads(rows: list, key, prev=None) -> list:
    """Set `row.head` on each row whose group (`key(row)`) differs from the
    row before it; `prev` is the group of the row before the first one."""
    last = prev
    for r in rows:
        g = key(r)
        r.group = g
        r.head = g != last
        last = g
    return rows


def sections(rows: list) -> list[dict]:
    """Rows already marked by `heads`, cut into runs of one group:
    [{"key", "head": bool, "rows": [...]}, ...]."""
    out: list[dict] = []
    for r in rows:
        if not out or r.head or out[-1]["key"] != r.group:
            out.append({"key": r.group, "head": r.head, "rows": []})
        out[-1]["rows"].append(r)
    return out


def window(qs, offset: int, limit: int):
    """(rows, prev): the page `[offset, offset+limit)` of `qs` in one query,
    plus the row just before it (None on the first page) so the page knows
    whether its first group continues from the last page."""
    if offset:
        got = list(qs[offset - 1 : offset + limit])
        return got[1:], (got[0] if got else None)
    return list(qs[:limit]), None


def more(request, offset: int, limit: int, total: int) -> dict:
    """What `_more.html` needs: the counts and the next page's URL."""
    shown_to = min(total, offset + limit)
    nxt = None
    if shown_to < total:
        params = request.GET.copy()
        params["offset"] = str(offset + limit)
        params.pop("page", None)
        nxt = request.path + "?" + params.urlencode()
    first = None
    if offset:
        params = request.GET.copy()
        params.pop("offset", None)
        qs = params.urlencode()
        first = request.path + (("?" + qs) if qs else "")
    return {"total": total, "start": offset + 1 if total else 0, "end": shown_to, "next": nxt, "first": first, "limit": limit, "offset": offset}


class ListErrors:
    """Middleware: a `ListError` from any view is a 422, not a 500."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exc):
        if not isinstance(exc, ListError):
            return None
        from dpypen.items.error_pages import unprocessable

        return unprocessable(request, str(exc))


def json_page(items: list, total: int, limit: int, offset: int) -> JsonResponse:
    resp = JsonResponse(envelope(items, total, limit, offset))
    resp["Cache-Control"] = "private, no-store"
    return resp


# The searchable fields of each thing, defined once (kit §14): the list
# pages, /search/, the palette and the JSON answers all search these.
PEN_FIELDS = ["brand.name", "model", "finish", "filling", "obtained_from"]
INK_FIELDS = ["brand.name", "name", "line", "color", "obtained_from"]
USAGE_FIELDS = ["pen.brand.name", "pen.model", "pen.finish", "ink.brand.name", "ink.name",
                "ink.line", "ink.color", "nib.width", "nib.cut", "nib.material"]


def vary(resp):
    """A list page answers a Load more fetch with a fragment at the same
    address, so a cache must keep the two apart."""
    from django.utils.cache import patch_vary_headers

    patch_vary_headers(resp, ("X-Pypen-More", "HX-Request"))
    return resp
