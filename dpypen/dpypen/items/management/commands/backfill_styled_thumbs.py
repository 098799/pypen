"""Build the 600px twin for every catalogue shot that predates the field.

The styled image is what every grid on the site shows, and it arrives from
Gemini at full size — the pen wall was sending ~10 MB of it to draw 200px
tiles. New shots get their twin in PenPhoto.set_styled(); this catches the
ones already in the database. Idempotent, so deploy can run it every time.
"""
import io
import sys

from django.core.management.base import BaseCommand
from django.db.models import Q

from dpypen.items.models import THUMB_MAX_SIZE, PenPhoto, _process_image
from django.core.files.base import ContentFile


class Command(BaseCommand):
    help = "Generate styled_thumbnail for photos that have a styled image but no twin."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="Rebuild twins that already exist.")

    def handle(self, *args, **opts):
        qs = PenPhoto.objects.exclude(image_styled="").exclude(image_styled=None)
        if not opts["force"]:
            # `__in=["", None]` silently matches nothing — a blank FileField is
            # "" and a null one is NULL, and neither compares equal inside IN.
            qs = qs.filter(Q(styled_thumbnail="") | Q(styled_thumbnail__isnull=True))
        done = failed = 0
        for photo in qs.iterator():
            try:
                photo.image_styled.open("rb")
                try:
                    data = photo.image_styled.read()
                finally:
                    photo.image_styled.close()
                base = photo.image_styled.name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                photo.styled_thumbnail = ContentFile(
                    _process_image(io.BytesIO(data), THUMB_MAX_SIZE),
                    name=f"{base}_t.jpg")
                photo.save(update_fields=["styled_thumbnail"])
                done += 1
            except Exception as exc:
                failed += 1
                print(f"photo {photo.pk}: {exc}", file=sys.stderr)
        self.stdout.write(f"styled thumbs: {done} built, {failed} failed")
