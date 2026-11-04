"""Give a photo to every pen that has none: web photos, restyled; else drawn from the name.

Two halves, because the image search runs on p340 (tools/pen_refs.py, it needs
`ddgs`) and Gemini's key lives here:

    manage.py pen_photo_fill --list > pens.json      # the pens with no photo
    python3 tools/pen_refs.py pens.json refs/        # on p340: candidates per pen
    manage.py pen_photo_fill --refs refs/            # here: pick, restyle, save

Per pen, a text model picks the candidate that shows this pen (or none), the
image model turns it into the catalogue shot on the house paper, and the photo is
saved with review="check": it waits on the owner at /next/pens/photos/check/.
With no fitting candidate the image model draws the pen from its name alone, and
the photo says so. A photo the owner marks wrong is deleted and its source goes
on RejectedPenPhoto, so no later run offers it again.
"""

import json
from pathlib import Path
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from dpypen.items import enhance
from dpypen.items.models import Pen, PenPhoto, RejectedPenPhoto


def _pens_without_photos():
    return (
        Pen.objects.annotate(n=Count("photos")).filter(n=0).select_related("brand", "rotation").order_by("rotation__priority", "brand__name", "model")
    )


class Command(BaseCommand):
    help = "Fill in a catalogue photo for every pen that has none."

    def add_arguments(self, parser):
        parser.add_argument("--list", action="store_true", help="Print the pens with no photo as JSON.")
        parser.add_argument("--refs", help="Folder from tools/pen_refs.py: one sub-folder per pen id.")
        parser.add_argument("--pen", type=int, action="append", dest="pens", help="Only this pen; repeatable.")
        parser.add_argument("--limit", type=int, default=0, help="Stop after N pens.")
        parser.add_argument("--no-draw", action="store_true", help="Never draw a pen from its name; leave it without a photo.")
        parser.add_argument("--dry-run", action="store_true", help="Judge only; save nothing.")
        parser.add_argument("--judge", choices=["gemini", "claude"], default="gemini", help="Which model picks the candidate.")
        parser.add_argument("--picks", help='JSON {"<pen id>": "<candidate file>"}: the choice made by hand, no judge.')
        parser.add_argument("--no-style", action="store_true", help="Keep the chosen web photo as it is (no Gemini); --restyle later.")
        parser.add_argument("--restyle", action="store_true", help="Make the catalogue shot for found web photos that have none yet.")

    def handle(self, *args, **o):
        if o["list"]:
            return self._list(o)
        if o["restyle"]:
            return self._restyle(o)
        if not o["refs"]:
            raise CommandError("give --list or --refs DIR")
        self._fill(Path(o["refs"]), o)

    def _list(self, o):
        qs = _pens_without_photos()
        if o["pens"]:
            qs = qs.filter(pk__in=o["pens"])
        rejected = {}
        for pen_id, url in RejectedPenPhoto.objects.values_list("pen_id", "source_url"):
            rejected.setdefault(pen_id, []).append(url)
        self.stdout.write(
            json.dumps(
                {
                    "pens": [
                        {
                            "id": p.pk,
                            "brand": p.brand.name,
                            "model": p.model,
                            "finish": p.finish or "",
                            "filling": p.filling or "",
                            "age": p.age or "",
                            "rejected": rejected.get(p.pk, []),
                        }
                        for p in qs
                    ]
                },
                indent=1,
            )
        )

    def _fill(self, root: Path, o):
        if not root.is_dir():
            raise CommandError(f"{root} is not a folder")
        qs = _pens_without_photos()
        if o["pens"]:
            qs = qs.filter(pk__in=o["pens"])
        pens = list(qs)
        if o["limit"]:
            pens = pens[: o["limit"]]
        self.stderr.write(f"{len(pens)} pen(s) without a photo; judge={enhance.JUDGE_MODEL} image={enhance.MODEL}")

        picks = json.loads(Path(o["picks"]).read_text()) if o["picks"] else None
        web = drawn = none = failed = 0
        for pen in pens:
            rejected = set(pen.rejected_photos.values_list("source_url", flat=True))
            meta_path = root / str(pen.pk) / "meta.json"
            cands = []
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                cands = [c for c in meta["candidates"] if c["url"] not in rejected]
            images = [(root / str(pen.pk) / c["file"]).read_bytes() for c in cands]
            try:
                if picks is not None:
                    # Chosen by looking at the contact sheets: {pen id: candidate file}.
                    files = [c["file"] for c in cands]
                    chosen = picks.get(str(pen.pk))
                    best, why = (files.index(chosen), "picked from the contact sheet") if chosen in files else (-1, "no pick")
                else:
                    judge = enhance.pick_reference_claude if o["judge"] == "claude" else enhance.pick_reference
                    best, why = judge(pen, images)
            except Exception as exc:  # noqa: BLE001
                best, why = -1, f"judge failed: {exc}"
            self.stderr.write(f"  {pen.pk:>4} {pen}: {len(cands)} cand, best={best} — {why}")
            if o["dry_run"]:
                continue
            try:
                if best >= 0:
                    c = cands[best]
                    host = urlparse(c.get("page") or c["url"]).netloc.removeprefix("www.")
                    if o["no_style"]:
                        self._save(pen, images[best], None, source_url=c["url"], note=f"Web photo from {host}"[:200])
                    else:
                        out = enhance.generate_catalog_shot(images[best], prompt=enhance.web_reference_prompt(pen))
                        self._save(pen, images[best], out, source_url=c["url"], note=f"Web photo from {host}, restyled by Gemini"[:200])
                    web += 1
                elif not o["no_draw"] and not o["no_style"] and RejectedPenPhoto.GENERATED not in rejected:
                    out = enhance.generate_from_name(pen)
                    self._save(pen, out, None, source_url="", note="Drawn by Gemini from the pen's name: not a photo of it")
                    drawn += 1
                else:
                    none += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.stderr.write(f"       FAILED {exc}")
        self.stdout.write(f"web {web}, drawn {drawn}, left without {none}, failed {failed}")

    def _restyle(self, o):
        """The web photos kept as they are (--no-style) get their catalogue shot."""
        qs = PenPhoto.objects.filter(review__in=["check", "ok"], image_styled="").exclude(source_url="").select_related("pen__brand")
        if o["pens"]:
            qs = qs.filter(pen_id__in=o["pens"])
        photos = list(qs[: o["limit"]] if o["limit"] else qs)
        made = failed = 0
        for ph in photos:
            self.stderr.write(f"  {ph.pen_id:>4} {ph.pen}")
            if o["dry_run"]:
                continue
            try:
                with ph.image.open("rb") as f:
                    raw = f.read()
                out = enhance.generate_catalog_shot(raw, prompt=enhance.web_reference_prompt(ph.pen))
                ph.set_styled(out, save=False)
                ph.source_note = (ph.source_note + ", restyled by Gemini")[:200]
                ph.save(update_fields=["image_styled", "styled_thumbnail", "source_note"])
                made += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.stderr.write(f"       FAILED {exc}")
        self.stdout.write(f"restyled {made}, failed {failed}, of {len(photos)}")

    def _save(self, pen, base: bytes, styled: bytes | None, *, source_url: str, note: str):
        photo = PenPhoto(pen=pen, kind="main", position=0, review="check", source_url=source_url, source_note=note)
        photo.image = ContentFile(base, name="photo.jpg")
        photo.save()
        if styled:
            photo.set_styled(styled)
