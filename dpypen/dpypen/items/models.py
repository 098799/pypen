import io
import secrets as _secrets
from datetime import date

from django.core.files.base import ContentFile
from django.db import models
from djmoney.models.fields import MoneyField
from PIL import Image, ImageOps

from dpypen.items import constants


def _random_media_path(prefix: str) -> str:
    # Random 16-byte URL-safe token -> ~22 chars. Keeps the filename
    # free of any pen/ink/usage id so the owner/guest authz on detail
    # pages isn't trivially bypassed by guessing the media URL.
    return f"{prefix}/{_secrets.token_urlsafe(16)}.jpg"

PHOTO_MAX_SIZE = 1800
THUMB_MAX_SIZE = 600
JPEG_QUALITY = 85

# Cap Pillow's decoder at 50MP — protects against decompression bombs
# from uploads or external AI responses. Default Pillow warns at 89MP
# and errors at ~178MP; single-threaded runserver OOMs on either.
Image.MAX_IMAGE_PIXELS = 50_000_000


def _process_image(source_file, max_size: int):
    img = Image.open(source_file)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return buf.getvalue()


class Brand(models.Model):
    def __str__(self):
        return f"{self.name}"

    name = models.CharField(max_length=64, blank=False, null=False, unique=True)
    nationality = models.CharField(max_length=64, choices=constants.NATIONALITIES, blank=False, null=False)


class Rotation(models.Model):
    def __str__(self):
        return (
            (f"Rotation {self.priority}, " if self.priority is not None else "")
            + f"{self.whos}, "
            + ("in use" if self.in_use else "defunct")
        )

    priority = models.IntegerField(blank=True, null=True)
    how_often = models.IntegerField(blank=False, null=False)
    whos = models.CharField(max_length=64, blank=False, null=False)
    in_use = models.BooleanField(blank=False, null=False)


def _share_token() -> str:
    import secrets
    return secrets.token_urlsafe(9)


class Pen(models.Model):
    def __str__(self):
        return f"{self.brand.name} {self.model}" + (f" {self.finish}" if self.finish else "")

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = _share_token()
        super().save(*args, **kwargs)

    share_token = models.CharField(max_length=32, unique=True, blank=True, default=_share_token)
    obtained = models.DateField(blank=False, null=False)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, blank=False, null=False)
    model = models.CharField(max_length=64, blank=False, null=False)
    finish = models.CharField(max_length=64, blank=True, null=True)
    filling = models.CharField(max_length=64, choices=constants.FILLING, blank=False, null=False)
    age = models.CharField(max_length=64, choices=constants.CLASSES, blank=False, null=False)
    obtained_from = models.CharField(max_length=64, blank=False, null=False)
    out = models.BooleanField(blank=False, null=False)
    price = MoneyField(max_digits=7, decimal_places=2, default_currency="PLN", blank=False, null=False)
    price_out = MoneyField(max_digits=5, decimal_places=2, default_currency="PLN", blank=True, null=True)
    rotation = models.ForeignKey(Rotation, on_delete=models.CASCADE, blank=False, null=False)


class Nib(models.Model):
    def __str__(self):
        return f"{self.material} {self.width} {self.cut}"

    width = models.CharField(max_length=64, blank=False, null=False)
    cut = models.CharField(max_length=64, choices=constants.NIB_CUTS, blank=False, null=False)
    material = models.CharField(max_length=64, choices=constants.NIB_MATERIALS, blank=False, null=False)


class Ink(models.Model):
    def __str__(self):
        return ("(sample) " if self.volume <= 5 else "") + f"{self.brand.name} " + (f"{self.line} " if self.line else "") + f"{self.name}"

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = _share_token()
        super().save(*args, **kwargs)

    share_token = models.CharField(max_length=32, unique=True, blank=True, default=_share_token)
    moi_url = models.URLField(blank=True)
    sampled_hex = models.JSONField(blank=True, default=list)
    obtained = models.DateField(blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, blank=False, null=False)
    line = models.CharField(max_length=64, blank=True, null=True)
    name = models.CharField(max_length=64, blank=False, null=False)
    color = models.CharField(max_length=64, choices=constants.COLORS, blank=False, null=False)
    obtained_from = models.CharField(max_length=64, blank=False, null=False)
    how = models.CharField(max_length=64, choices=constants.HOW, blank=False, null=False)
    price = MoneyField(max_digits=5, decimal_places=2, default_currency="PLN", blank=True, null=True)
    used_up = models.BooleanField(blank=True, null=True)
    used_up_when = models.DateField(blank=True, null=True)
    volume = models.IntegerField(blank=False, null=False)
    rotation = models.ForeignKey(Rotation, on_delete=models.CASCADE, blank=False, null=False)

    @property
    def swatch_bg(self) -> str:
        if self.sampled_hex and len(self.sampled_hex) >= 2:
            return "linear-gradient(135deg, " + ", ".join(self.sampled_hex) + ")"
        from dpypen.items.public import INK_COLOR_HEX
        return INK_COLOR_HEX.get(self.color, "#333")


def pen_photo_path(instance, filename):
    return _random_media_path("pen_photos")


class PenPhoto(models.Model):
    class Meta:
        ordering = ["position", "-uploaded_at"]

    pen = models.ForeignKey(Pen, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=pen_photo_path)
    thumbnail = models.ImageField(upload_to=pen_photo_path, blank=True, null=True)
    image_styled = models.ImageField(upload_to=pen_photo_path, blank=True, null=True)
    position = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo of {self.pen} #{self.position}"

    def save(self, *args, **kwargs):
        if self.image and not self.pk:
            source = self.image
            large = _process_image(source, PHOTO_MAX_SIZE)
            thumb = _process_image(source, THUMB_MAX_SIZE)
            # Placeholder names — pen_photo_path() ignores them and assigns
            # a random filename, so the stored URL doesn't leak pen_id.
            self.image = ContentFile(large, name="photo.jpg")
            self.thumbnail = ContentFile(thumb, name="thumb.jpg")
        super().save(*args, **kwargs)


def writing_sample_path(instance, filename):
    return _random_media_path("writing_samples")


def ink_swatch_path(instance, filename):
    return _random_media_path("ink_swatches")


class InkSwatch(models.Model):
    class Meta:
        ordering = ["position", "-uploaded_at"]

    ink = models.ForeignKey("Ink", on_delete=models.CASCADE, related_name="swatches")
    image = models.ImageField(upload_to=ink_swatch_path)
    image_clean = models.ImageField(upload_to=ink_swatch_path, blank=True, null=True)
    position = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Swatch of {self.ink}"

    def save(self, *args, **kwargs):
        if self.image and not self.pk:
            source = self.image
            processed = _process_image(source, PHOTO_MAX_SIZE)
            self.image = ContentFile(processed, name="swatch.jpg")
        super().save(*args, **kwargs)


class WritingSample(models.Model):
    class Meta:
        ordering = ["-uploaded_at"]

    usage = models.ForeignKey("Usage", on_delete=models.CASCADE, related_name="samples")
    image = models.ImageField(upload_to=writing_sample_path)
    image_clean = models.ImageField(upload_to=writing_sample_path, blank=True, null=True)
    notes = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sample of {self.usage} #{self.pk}"

    def save(self, *args, **kwargs):
        if self.image and not self.pk:
            source = self.image
            processed = _process_image(source, PHOTO_MAX_SIZE)
            self.image = ContentFile(processed, name="sample.jpg")
        super().save(*args, **kwargs)


class InviteCode(models.Model):
    token = models.CharField(max_length=32, unique=True)
    label = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    visits = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.label or '(unlabeled)'} · {self.token[:8]}…"

    @classmethod
    def generate_token(cls) -> str:
        import secrets
        return secrets.token_urlsafe(12)

    def is_active(self, now=None):
        from django.utils import timezone
        now = now or timezone.now()
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < now:
            return False
        return True


class Usage(models.Model):
    def __str__(self):
        return f"{self.pen.brand.name} {self.pen.model} inked with {self.ink.brand.name} {self.ink.name} on {self.begin}"

    pen = models.ForeignKey(Pen, on_delete=models.CASCADE, blank=False, null=False)
    nib = models.ForeignKey(Nib, on_delete=models.CASCADE, blank=False, null=False)
    ink = models.ForeignKey(Ink, on_delete=models.CASCADE, blank=False, null=False)
    begin = models.DateField(blank=False, null=False, default=date.today)
    end = models.DateField(blank=True, null=True)
