#!/usr/bin/env python3
"""Find web photos of the pens that have none: the first half of `pen_photo_fill`.

Runs on p340, not in the app: it needs `ddgs` (DuckDuckGo image search), which the
site does not. Input is the JSON that `manage.py pen_photo_fill --list` prints on
bae; output is one folder per pen with up to N candidate photos and a meta.json.
Copy the folder to bae and run `pen_photo_fill --refs DIR` there: Gemini picks the
candidate that really shows the pen and turns it into the catalogue shot.

    ssh bae_llm '... manage.py pen_photo_fill --list' > pens.json
    python3 tools/pen_refs.py pens.json scratch/refs      # in a venv with ddgs
"""

import argparse
import concurrent.futures as cf
import hashlib
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from ddgs import DDGS
from PIL import Image

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
MIN_SIDE = 320


def query_for(pen: dict) -> str:
    model = re.sub(r"[()]", " ", pen["model"])
    parts = [pen["brand"], model]
    if pen.get("finish") and pen["finish"] != "None":
        parts.append(pen["finish"])
    return " ".join(" ".join(parts).split()) + " fountain pen"


def fetch(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read(12_000_000)
        img = Image.open(io.BytesIO(data))
        img.load()
        if min(img.size) < MIN_SIDE:
            return None
        img = img.convert("RGB")
        img.thumbnail((1800, 1800))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        return buf.getvalue()
    except Exception:
        return None


def search(query: str, n: int) -> list[dict]:
    for attempt in range(4):
        try:
            return list(DDGS().images(query, max_results=n * 2))
        except Exception as exc:
            print(f"  search retry {attempt + 1}: {exc}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pens")
    ap.add_argument("out")
    ap.add_argument("-n", type=int, default=6, help="candidates per pen")
    a = ap.parse_args()
    data = json.loads(Path(a.pens).read_text())
    out = Path(a.out)
    for pen in data["pens"]:
        d = out / str(pen["id"])
        if (d / "meta.json").exists():
            continue
        rejected = set(pen.get("rejected", []))
        q = query_for(pen)
        hits = [h for h in search(q, a.n) if h.get("image") and h["image"] not in rejected]
        with cf.ThreadPoolExecutor(8) as ex:
            blobs = list(ex.map(lambda h: fetch(h["image"]), hits))
        d.mkdir(parents=True, exist_ok=True)
        cands, seen = [], set()
        for h, blob in zip(hits, blobs):
            if not blob or len(cands) >= a.n:
                continue
            digest = hashlib.sha1(blob).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            name = f"c{len(cands)}.jpg"
            (d / name).write_bytes(blob)
            cands.append({"file": name, "url": h["image"], "page": h.get("url", ""), "title": h.get("title", "")[:200]})
        (d / "meta.json").write_text(json.dumps({"pen": pen, "query": q, "candidates": cands}, indent=1))
        print(f"{pen['id']:>4} {len(cands)} cand  {q}", file=sys.stderr)
        time.sleep(1.5)


if __name__ == "__main__":
    main()
