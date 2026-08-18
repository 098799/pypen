"""Claude-vision notebook import — OCR a fountain-pen log page into structured inkings."""

import base64
import json
import os
from dataclasses import dataclass

import anthropic

from dpypen.items.models import Ink, Nib, Pen


MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


def _catalog_block() -> str:
    pens = "\n".join(f"  #{p.pk} — {p.brand.name} {p.model}{(' ' + p.finish) if p.finish else ''}"
                     for p in Pen.objects.select_related("brand").order_by("brand__name", "model"))
    inks = "\n".join(f"  #{i.pk} — {i.brand.name} {(i.line + ' ') if i.line else ''}{i.name}"
                     for i in Ink.objects.select_related("brand").order_by("brand__name", "line", "name"))
    nibs = "\n".join(f"  #{n.pk} — {n.material} {n.width} {n.cut}".strip()
                     for n in Nib.objects.order_by("material", "width", "cut"))
    return (
        f"## Pens\n{pens}\n\n"
        f"## Inks\n{inks}\n\n"
        f"## Nibs\n{nibs}"
    )


TOOL_SCHEMA = {
    "name": "record_inkings",
    "description": "Record one or more fountain-pen inkings extracted from the notebook page.",
    "input_schema": {
        "type": "object",
        "properties": {
            "inkings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pen_id": {"type": "integer", "description": "ID of the matching pen from the catalog, or 0 if uncertain"},
                        "pen_raw": {"type": "string", "description": "Exact text as written in the notebook"},
                        "ink_id": {"type": "integer", "description": "ID of the matching ink, or 0 if uncertain"},
                        "ink_raw": {"type": "string"},
                        "nib_id": {"type": "integer", "description": "ID of the matching nib, or 0 if uncertain"},
                        "nib_raw": {"type": "string"},
                        "begin": {"type": "string", "description": "YYYY-MM-DD, the start date of this inking"},
                        "end": {"type": ["string", "null"], "description": "YYYY-MM-DD or null if still inked"},
                        "confidence": {"type": "number", "description": "0..1 confidence in the extraction"},
                        "notes": {"type": "string", "description": "Freeform notes or uncertainty reasons"},
                    },
                    "required": ["pen_raw", "ink_raw", "begin", "confidence"],
                },
            }
        },
        "required": ["inkings"],
    },
}


SYSTEM = """You are extracting fountain-pen ink usage records from a hand-written notebook page.

Each entry on the page usually describes:
- a pen (sometimes just model, sometimes brand + model + finish)
- an ink (sometimes brand + name, sometimes just name)
- a nib (width, material, cut)
- a begin date (when the pen was filled)
- optionally an end date (when the pen was emptied / flushed)
- sometimes a short note

You will be given the catalog of pens, inks, and nibs that already exist in the system.
When a hand-written entry matches something in the catalog, set the corresponding id field.
If the entry is ambiguous or doesn't match anything in the catalog, set the id to 0 (zero) and
always preserve the original hand-written text in the *_raw field. Include confidence 0..1.

Dates: reconstruct full YYYY-MM-DD from context. If only a month/day is written, infer the year
from adjacent entries or the page header. If you truly can't determine a date, use today's date
and lower confidence.

Call the record_inkings tool exactly once."""


@dataclass
class ImportedInking:
    pen_id: int
    pen_raw: str
    ink_id: int
    ink_raw: str
    nib_id: int
    nib_raw: str
    begin: str
    end: str | None
    confidence: float
    notes: str


def extract_from_image(image_bytes: bytes, media_type: str = "image/jpeg") -> list[ImportedInking]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)
    catalog = _catalog_block()
    encoded = base64.standard_b64encode(image_bytes).decode("ascii")

    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[
            {"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": "Catalog:\n\n" + catalog, "cache_control": {"type": "ephemeral"}},
        ],
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "record_inkings"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": encoded},
                    },
                    {"type": "text", "text": "Extract every inking entry on this page. Match pens/inks/nibs to the catalog when confident."},
                ],
            }
        ],
    )

    for block in resp.content:
        if block.type == "tool_use" and block.name == "record_inkings":
            raw = block.input.get("inkings", [])
            out = []
            for item in raw:
                out.append(ImportedInking(
                    pen_id=int(item.get("pen_id") or 0),
                    pen_raw=item.get("pen_raw", ""),
                    ink_id=int(item.get("ink_id") or 0),
                    ink_raw=item.get("ink_raw", ""),
                    nib_id=int(item.get("nib_id") or 0),
                    nib_raw=item.get("nib_raw", ""),
                    begin=item.get("begin", ""),
                    end=item.get("end"),
                    confidence=float(item.get("confidence") or 0.0),
                    notes=item.get("notes", ""),
                ))
            return out

    raise RuntimeError("Claude did not return a tool call")
