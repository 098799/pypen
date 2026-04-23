"""Rename existing pen photos / ink swatches / writing samples to
random filenames so the owning pen/ink/usage id is no longer
recoverable from the media URL.

Idempotent: only touches files whose stored path still contains a
numeric id segment (the legacy layout). Run with --dry-run first.
"""

from __future__ import annotations

import re
import secrets as _secrets
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from dpypen.items.models import InkSwatch, PenPhoto, WritingSample


LEGACY_SEGMENT = re.compile(r"(pen_photos|writing_samples|ink_swatches)/(\d+)/")


def _is_legacy(stored_name: str) -> bool:
    return bool(LEGACY_SEGMENT.search(stored_name or ""))


def _new_name(stored_name: str) -> str:
    m = LEGACY_SEGMENT.search(stored_name)
    if not m:
        return stored_name
    prefix = m.group(1)
    ext = Path(stored_name).suffix or ".jpg"
    return f"{prefix}/{_secrets.token_urlsafe(16)}{ext}"


class Command(BaseCommand):
    help = "Rename legacy pen-id/ink-id/usage-id media paths to random tokens."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        media_root = Path(settings.MEDIA_ROOT)
        total = renamed = missing = 0

        def process(instance, field_name):
            nonlocal total, renamed, missing
            field = getattr(instance, field_name)
            if not field or not field.name:
                return
            total += 1
            if not _is_legacy(field.name):
                return
            old_abs = media_root / field.name
            if not old_abs.exists():
                self.stdout.write(self.style.WARNING(f"  MISSING file for {instance.__class__.__name__}#{instance.pk}.{field_name}: {field.name}"))
                missing += 1
                return
            new_name = _new_name(field.name)
            new_abs = media_root / new_name
            new_abs.parent.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"  {field.name}  ->  {new_name}")
            if not dry:
                old_abs.rename(new_abs)
                setattr(instance, field_name, new_name)
                instance.save(update_fields=[field_name])
            renamed += 1

        for cls, fields in [
            (PenPhoto, ["image", "thumbnail", "image_styled"]),
            (InkSwatch, ["image", "image_clean"]),
            (WritingSample, ["image", "image_clean"]),
        ]:
            self.stdout.write(self.style.NOTICE(f"\n== {cls.__name__} =="))
            for obj in cls.objects.all():
                for f in fields:
                    process(obj, f)

        msg = f"\nScanned {total} file-fields. Renamed {renamed}. Missing files: {missing}."
        self.stdout.write(self.style.SUCCESS(msg) if not dry else self.style.WARNING(msg + "  (dry-run, no changes written)"))
