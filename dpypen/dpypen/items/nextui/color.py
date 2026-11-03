"""Ink colours as numbers: OKLab for distance and hue, contrast for the accent.

The new version's accent is the ink on the desk (`accent`), so its lightness has
to be worked out, for each theme, against that theme's own paper. A yellow ink
would otherwise be an unreadable button in light, a blue-black one in dark.
"""

from __future__ import annotations

import math

# The new version's papers (static/items/next/next.css).
PAGE_LIGHT, PANEL_LIGHT = "#f4f5f7", "#ffffff"
PAGE_DARK, PANEL_DARK = "#131927", "#1c2436"
DEFAULT_INK = "#2d4a8f"  # royal blue, when the desk is empty or holds only blacks
MIN_CHROMA = 0.05


def to_rgb(hex_: str) -> tuple[float, float, float]:
    h = hex_.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def to_hex(rgb) -> str:
    return "#" + "".join(f"{round(max(0, min(1, c)) * 255):02x}" for c in rgb)


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklab(hex_: str) -> tuple[float, float, float]:
    r, g, b = (_lin(c) for c in to_rgb(hex_))
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l_, m, s))
    return (
        0.2104542553 * l_ + 0.793617785 * m - 0.0040720468 * s,
        1.9779984951 * l_ - 2.428592205 * m + 0.4505937099 * s,
        0.0259040371 * l_ + 0.7827717662 * m - 0.808675766 * s,
    )


def lch(hex_: str) -> tuple[float, float, float]:
    L, a, b = oklab(hex_)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def _from_oklch(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3
    return (
        4.0767416621 * l_ - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l_ + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l_ - 0.7034186147 * m + 1.707614701 * s,
    )


def oklch_hex(L, C, h) -> str:
    """The colour, its chroma reduced until it fits sRGB."""
    for _ in range(40):
        rgb = _from_oklch(L, C, h)
        if all(-0.0005 <= c <= 1.0005 for c in rgb):
            break
        C *= 0.95
    return to_hex(_gam(max(0.0, c)) for c in rgb)


def luminance(hex_: str) -> float:
    r, g, b = (_lin(c) for c in to_rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def distance(a: str, b: str) -> float:
    return math.dist(oklab(a), oklab(b))


def mean(hexes: list[str]) -> str:
    """The middle of a swatch's sampled colours."""
    labs = [to_rgb(h) for h in hexes]
    return to_hex(sum(c[i] for c in labs) / len(labs) for i in range(3))


def ink_hex(ink, table: dict) -> str:
    """One colour for an ink: what was sampled from its swatch, else its class."""
    if ink.sampled_hex:
        return mean(list(ink.sampled_hex))
    return table.get(ink.color, "#333333")


def spectrum_key(hex_: str):
    """Inks along the rainbow; the near-greys together at the end, dark last."""
    L, C, h = lch(hex_)
    if C < 0.035:
        return (1, -L, 0)
    return (0, round(h / 12), L)


def accent(hex_: str | None) -> dict:
    """{light, dark, on_light, on_dark}: this ink as the app's accent colour,
    readable (4.5:1) on both papers of each theme, buttons' words included."""
    L, C, h = lch(hex_ or DEFAULT_INK)
    C = min(max(C, 0.09), 0.17)
    light = None
    for i in range(0, 60):
        light = oklch_hex(max(0.2, min(L, 0.62) - i * 0.01), C, h)
        if contrast(light, PAGE_LIGHT) >= 4.6 and contrast(light, PANEL_LIGHT) >= 4.6:
            break
    dark = None
    for i in range(0, 60):
        dark = oklch_hex(min(0.95, max(L, 0.72) + i * 0.01), C, h)
        if contrast(dark, PAGE_DARK) >= 4.6 and contrast(dark, PANEL_DARK) >= 4.6:
            break
    return {"light": light, "dark": dark, "on_light": "#ffffff", "on_dark": PAGE_DARK}


def chromatic(hex_: str) -> bool:
    return lch(hex_)[1] >= MIN_CHROMA
