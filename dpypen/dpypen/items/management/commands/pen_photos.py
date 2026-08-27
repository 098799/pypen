"""Generate the three catalogue shots for a pen from one base photograph.

Every variant is derived from a single source image, so two of the three ask
for a view the source may not contain. The prompts refuse rather than invent
(see enhance.VARIANT_PROMPTS); this command's job is to feed them, save what
comes back, and never touch a variant that already exists unless told to.
"""

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from dpypen.items import enhance
from dpypen.items.models import Pen, PenPhoto


class Command(BaseCommand):
    help = "Generate main/nib/capped catalogue shots for pens from an existing photo."

    def add_arguments(self, parser):
        parser.add_argument("--pen", type=int, action="append", dest="pens",
                            help="Pen id; repeatable. Omit to select by rotation.")
        parser.add_argument("--rotation", type=int,
                            help="Rotation priority to process (e.g. 2).")
        parser.add_argument("--variants", default=",".join(enhance.VARIANT_ORDER),
                            help="Comma-separated: main,nib,capped")
        parser.add_argument("--limit", type=int, default=0, help="Stop after N pens.")
        parser.add_argument("--redo", action="store_true",
                            help="Regenerate variants that already exist.")
        parser.add_argument("--dry-run", action="store_true",
                            help="List what would be generated and exit.")

    def handle(self, *args, **o):
        variants = [v.strip() for v in o["variants"].split(",") if v.strip()]
        unknown = [v for v in variants if v not in enhance.VARIANT_PROMPTS]
        if unknown:
            raise CommandError(f"unknown variant(s): {', '.join(unknown)}")

        qs = Pen.objects.select_related("brand", "rotation").prefetch_related("photos")
        if o["pens"]:
            qs = qs.filter(pk__in=o["pens"])
        elif o["rotation"] is not None:
            qs = qs.filter(rotation__priority=o["rotation"], rotation__in_use=True)
        else:
            raise CommandError("give --pen or --rotation")

        pens = [p for p in qs.order_by("brand__name", "model") if p.photos.all()]
        skipped = qs.count() - len(pens)
        if skipped:
            self.stderr.write(f"{skipped} pen(s) skipped: no base photograph to work from")
        if o["limit"]:
            pens = pens[: o["limit"]]

        self.stderr.write(f"model={enhance.MODEL} size={enhance.IMAGE_SIZE or 'default'}")

        made = failed = 0
        for pen in pens:
            have = {p.kind for p in pen.photos.all()}
            base = next((p for p in pen.photos.all() if p.image), None)
            if base is None:
                continue
            todo = [v for v in variants if o["redo"] or v not in have]
            if not todo:
                self.stderr.write(f"  {pen} — already complete")
                continue
            self.stderr.write(f"  {pen} — generating {', '.join(todo)}")
            if o["dry_run"]:
                continue
            raw = base.image.read()
            for kind in todo:
                try:
                    out = enhance.generate_catalog_shot(
                        raw, prompt=enhance.variant_prompt(pen, kind),
                        aspect_ratio="1:1" if kind == "nib" else "4:3",
                    )
                except Exception as exc:                       # noqa: BLE001
                    failed += 1
                    self.stderr.write(f"    {kind}: FAILED {exc}")
                    continue
                photo = PenPhoto(
                    pen=pen, kind=kind,
                    position=enhance.VARIANT_ORDER.index(kind),
                    source_note=base.source_note,
                )
                photo.image.save(f"{kind}.jpg", ContentFile(out), save=False)
                photo.save()
                # save() re-processes .image from the upload; the generated
                # frame is already the styled one, so record it as such.
                photo.image_styled.save(f"{kind}-styled.jpg", ContentFile(out), save=True)
                made += 1
                self.stderr.write(f"    {kind}: ok ({len(out)//1024}KB)")

        self.stdout.write(f"generated {made}, failed {failed}, pens {len(pens)}")
