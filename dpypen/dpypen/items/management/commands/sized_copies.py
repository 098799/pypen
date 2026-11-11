"""Make the WebP copies the pages draw (sized.py, PYPEN-3), drop the orphans.

A page makes a missing copy itself on first view; this makes them ahead, so
no visitor waits for the encode, and removes the copies of photos that were
deleted, turned or replaced. Idempotent and cheap once the copies exist, so
the deploy runs it every time (as `pypen`, who owns the media).
"""
import sys

from django.core.management.base import BaseCommand

from dpypen.items import sized
from dpypen.items.models import InkSwatch, PenPhoto, WritingSample


class Command(BaseCommand):
    help = "Make the page-size WebP copies of photos, samples and swatches; remove orphans."

    def handle(self, *args, **opts):
        made = 0
        jobs = []
        rows = []
        for ph in PenPhoto.objects.all().iterator():
            jobs.append(ph.image_styled or ph.image)
            if ph.grid_file:
                rows.append(ph.grid_file)
        for model in (WritingSample, InkSwatch):
            for s in model.objects.all().iterator():
                jobs.append(s.image_clean or s.image)
        for field in jobs:
            if not field:
                continue
            try:
                if sized.url(field) != field.url:
                    made += 1
            except Exception as exc:  # one bad file must not stop the deploy
                print(f"{field.name}: {exc}", file=sys.stderr)
        for field in rows:  # the list rows' 240 px copies (sized.ROW_EDGE)
            try:
                sized.url(field, sized.ROW_EDGE)
            except Exception as exc:
                print(f"{field.name}: {exc}", file=sys.stderr)
        gone = sized.prune()
        self.stdout.write(f"sized copies: {made} of {len(jobs)} pictures drawn from a copy, {gone} orphans removed")
