"""Gemini image-editing: turn a phone snap into a clean catalog-style shot."""

import io
import os

from google import genai
from google.genai import types
from PIL import Image


MODEL = "gemini-3.1-flash-image-preview"

_PROMPT_TEMPLATE = """You are EDITING the input photograph, not generating a new image.

SUBJECT IDENTIFICATION
The subject is a real, specific fountain pen currently owned by the user:
  • Brand and model: {title}
  • Filling mechanism: {filling}
  • Era: {era}

The input photo shows THIS EXACT PEN. Your output must show the SAME pen, unchanged.

WHAT TO PRESERVE (non-negotiable — this is an edit, not a redesign)
  • Keep every part of the pen pixel-faithful: cap, barrel, section, clip, finial,
    threading, nib, breather hole, tipping.
  • Preserve the nib exactly as shown — same shape, same size, same imprint, same
    material colour. Do NOT re-engrave it, add a logo, or change its shape.
  • Preserve the section exactly as shown — same length, same shape, no new patterns.
  • Preserve the body colour, finish (matte/gloss/striated/demo), material texture,
    any imprinted branding, any imperfections, scratches, or wear.
  • Do not add, remove, or reposition any hardware (bands, rings, filler knob).

WHAT TO CHANGE
  1. Remove the original background entirely.
  2. Replace with a warm off-white paper backdrop (#f2ead4), with a soft natural
     gradient for depth; paper-grain subtle.
  3. Add a realistic, soft drop shadow beneath the pen as if it rests on a desk.
  4. Centre and frame the pen comfortably; straighten only if clearly askew.
  5. Output a crisp 4:3 image, warmly lit.

If you cannot isolate the pen from the background with confidence, return the
original image unchanged rather than guessing."""


def _pen_title(pen) -> str:
    parts = [pen.brand.name, pen.model]
    if pen.finish:
        parts.append(pen.finish)
    return " ".join(parts)


def build_prompt(pen) -> str:
    return _PROMPT_TEMPLATE.format(
        title=_pen_title(pen),
        filling=pen.filling or "unknown",
        era=pen.age or "unknown",
    )


WRITING_SAMPLE_PROMPT = """You are given a photograph of a handwritten page containing
fountain-pen ink strokes on paper.

Produce a clean extraction of ONLY the hand-written ink marks, as if lifted off the page:

- Remove the paper entirely (including ruling, grid, lines, texture, lighting, shadow).
- Replace the paper with a neutral transparent-looking soft off-white (#f6efda) or keep
  the exact background visually neutral so the ink reads cleanly.
- Keep the ink strokes pixel-faithful: same shape, same shading, same pressure, same
  hue. Do NOT re-write, straighten, tidy or stylize anything.
- Do not change the wording, the handwriting style, or the layout of the strokes.
- Output a high-resolution clean image suitable as a writing-sample thumbnail.
- If the image does not contain legible ink strokes, return the input unchanged.

This is pure background removal for a calligraphy specimen. Preserve the ink."""


def generate_writing_sample(image_bytes: bytes, mime_type: str = "image/jpeg") -> bytes:
    return generate_catalog_shot(image_bytes, prompt=WRITING_SAMPLE_PROMPT, mime_type=mime_type)


SWATCH_PROMPT = """You are given a photograph of a hand-painted ink swatch, or an
ink-swatch photo lifted from a review site.

Extract the pure ink swatch for use as a reference thumbnail:

- Remove all paper, page texture, pen marks, labels, borders, and hands.
- Keep only the coloured ink area, showing its natural variations (sheen, shading,
  edges where the ink pools). Preserve the ink colour pixel-faithfully.
- Place the clean swatch on a soft off-white (#f6efda) background, centred, with
  generous margins.
- Output a well-lit, crisp image suitable as a swatch thumbnail.

This is a faithful colour specimen — do not change the hue or invent new marks."""


def generate_ink_swatch(image_bytes: bytes, mime_type: str = "image/jpeg") -> bytes:
    return generate_catalog_shot(image_bytes, prompt=SWATCH_PROMPT, mime_type=mime_type)


def generate_catalog_shot(image_bytes: bytes, prompt: str, mime_type: str = "image/jpeg") -> bytes:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
    )

    for candidate in (response.candidates or []):
        if not candidate.content or not candidate.content.parts:
            continue
        for part in candidate.content.parts:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                return _normalise(part.inline_data.data)

    text_parts = []
    for candidate in (response.candidates or []):
        for part in (candidate.content.parts or []):
            if getattr(part, "text", None):
                text_parts.append(part.text)
    raise RuntimeError("Gemini returned no image. " + " ".join(text_parts)[:400])


def _normalise(raw: bytes, max_size: int = 1800, quality: int = 88) -> bytes:
    img = Image.open(io.BytesIO(raw))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()
