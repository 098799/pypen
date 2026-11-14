"""Draw pypen's PNG icons from the sign in dpypen/dpypen/items/kitpwa.py (_NIB).

    python3 tools/make_icons.py      (needs rsvg-convert)

The sign (kitpwa.py serves the same drawing as /icon.svg and /icon-maskable.svg):
one nib, the pen inked now, in a dashed ring, the rotation, with an oxblood
dot on it, the next pen due. pens, the catalogue, draws the same nib three
times.

Reads _NIB from kitpwa.py (no Django needed) and writes static/items/icons/:
icon-192.png and icon-512.png (scale 1), icon-maskable-512.png (0.75: the
sign inside 0.31 x the width, which Android 12+ keeps on the splash),
apple-touch-icon.png (180, 0.92: within 80 %). All are flat #f4ecd8, the
manifest's background_color, so the phone's splash shows the sign and no tile.
rsvg-convert renders, Pillow writes the PNG (byte-stable for one rsvg and Pillow).
"""

import ast
import io
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PWA = ROOT / "dpypen" / "dpypen" / "items" / "kitpwa.py"
OUT = ROOT / "dpypen" / "dpypen" / "items" / "static" / "items" / "icons"
BG = "#f4ecd8"


def nib() -> str:
    for node in ast.parse(PWA.read_text()).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "_NIB":
            return ast.literal_eval(node.value)
    raise SystemExit("_NIB not found in kitpwa.py")


def sign(scale: float) -> str:
    """The drawing in a 64-unit box, shrunk round its centre by scale (1 = the full icon).
    Its outer edge is the ring's: 26.5 units from the centre, 0.41 of the width at scale 1."""
    return f'<g transform="translate(32 32) scale({scale}) translate(-32 -32)">{nib()}</g>'


def svg(scale: float) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">' f'<rect width="64" height="64" fill="{BG}"/>{sign(scale)}</svg>\n'


def png(scale: float, size: int, name: str) -> None:
    raw = subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size)], input=svg(scale).encode(), capture_output=True, check=True).stdout
    Image.open(io.BytesIO(raw)).convert("RGB").save(OUT / name, optimize=True)


if __name__ == "__main__":
    png(1.0, 192, "icon-192.png")
    png(1.0, 512, "icon-512.png")
    png(0.75, 512, "icon-maskable-512.png")
    png(0.92, 180, "apple-touch-icon.png")
    print("icons written")
