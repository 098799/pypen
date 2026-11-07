"""Draw pypen's PNG icons from the SVGs in dpypen/dpypen/items/pwa.py.

    python3 tools/make_icons.py

Reads _NIB, _ICON_SVG and _ICON_MASKABLE from pwa.py (no Django needed) and
writes static/items/icons/: icon-192.png and icon-512.png from _ICON_SVG,
icon-maskable-512.png from _ICON_MASKABLE, apple-touch-icon.png (180, opaque,
the nib a little smaller). All are flat #f4ecd8, the manifest's
background_color, so the phone's splash shows the nib and no tile.
rsvg-convert draws them; PIL saves them again, so the bytes are stable.
"""
import ast
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PWA = ROOT / "dpypen" / "dpypen" / "items" / "pwa.py"
OUT = ROOT / "dpypen" / "dpypen" / "items" / "static" / "items" / "icons"


def svgs() -> dict:
    tree = ast.parse(PWA.read_text())
    keep = [n for n in tree.body if isinstance(n, ast.Assign)
            and getattr(n.targets[0], "id", "") in ("_NIB", "_ICON_SVG", "_ICON_MASKABLE")]
    ns: dict = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(PWA), "exec"), ns)
    return ns


def draw(svg: str, name: str, size: int) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "i.svg", Path(tmp) / "i.png"
        src.write_text(svg)
        subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), str(src), "-o", str(out)], check=True)
        im = Image.open(out)
        im.load()
    im.convert("RGB").save(OUT / name, optimize=True)


if __name__ == "__main__":
    s = svgs()
    draw(s["_ICON_SVG"], "icon-192.png", 192)
    draw(s["_ICON_SVG"], "icon-512.png", 512)
    draw(s["_ICON_MASKABLE"], "icon-maskable-512.png", 512)
    draw(s["_ICON_SVG"].replace("scale(1.24)", "scale(1.12)"), "apple-touch-icon.png", 180)
    print("icons written")
