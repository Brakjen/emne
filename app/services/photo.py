import io
import uuid
from datetime import datetime, timezone

import boto3
from PIL import Image, ExifTags

from app.config import settings

THUMBNAIL_WIDTH = 400

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
        )
    return _s3_client


def _generate_key(find_id: str, suffix: str, ext: str = "jpg") -> str:
    return f"finds/{find_id}/{suffix}_{uuid.uuid4().hex[:8]}.{ext}"


def generate_thumbnail(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img = _auto_orient(img)
    ratio = THUMBNAIL_WIDTH / img.width
    new_height = int(img.height * ratio)
    img = img.resize((THUMBNAIL_WIDTH, new_height), Image.LANCZOS)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _auto_orient(img: Image.Image) -> Image.Image:
    try:
        exif = img._getexif()
        if exif:
            orientation_key = next(
                k for k, v in ExifTags.TAGS.items() if v == "Orientation"
            )
            orientation = exif.get(orientation_key)
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    except Exception:
        pass
    return img


def extract_exif_datetime(image_bytes: bytes) -> datetime | None:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img._getexif()
        if not exif:
            return None
        datetime_key = next(
            (k for k, v in ExifTags.TAGS.items() if v == "DateTimeOriginal"), None
        )
        if datetime_key and datetime_key in exif:
            dt_str = exif[datetime_key]
            return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
    except Exception:
        pass
    return None


def extract_exif_gps(image_bytes: bytes) -> tuple[float, float] | None:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img._getexif()
        if not exif:
            return None
        gps_key = next(
            (k for k, v in ExifTags.TAGS.items() if v == "GPSInfo"), None
        )
        if gps_key and gps_key in exif:
            gps_info = exif[gps_key]
            lat = _dms_to_decimal(gps_info[2], gps_info[1])
            lon = _dms_to_decimal(gps_info[4], gps_info[3])
            return (lat, lon)
    except Exception:
        pass
    return None


def _dms_to_decimal(dms: tuple, ref: str) -> float:
    degrees = float(dms[0])
    minutes = float(dms[1])
    seconds = float(dms[2])
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def upload_photo(image_bytes: bytes, find_id: str) -> tuple[str, str]:
    """Upload full image and thumbnail to S3. Returns (storage_key, thumbnail_key)."""
    s3 = _get_s3_client()

    storage_key = _generate_key(find_id, "full")
    thumbnail_key = _generate_key(find_id, "thumb")

    thumbnail_bytes = generate_thumbnail(image_bytes)

    s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=storage_key,
        Body=image_bytes,
        ContentType="image/jpeg",
    )
    s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=thumbnail_key,
        Body=thumbnail_bytes,
        ContentType="image/jpeg",
    )

    return storage_key, thumbnail_key


def delete_photo_files(storage_key: str, thumbnail_key: str) -> None:
    s3 = _get_s3_client()
    s3.delete_objects(
        Bucket=settings.s3_bucket_name,
        Delete={"Objects": [{"Key": storage_key}, {"Key": thumbnail_key}]},
    )


def delete_photo_files_bulk(keys: list[tuple[str, str]]) -> None:
    """Delete multiple photos' files in a single S3 call. keys = [(storage_key, thumbnail_key), ...]"""
    if not keys:
        return
    s3 = _get_s3_client()
    objects = []
    for storage_key, thumbnail_key in keys:
        objects.append({"Key": storage_key})
        objects.append({"Key": thumbnail_key})
    s3.delete_objects(
        Bucket=settings.s3_bucket_name,
        Delete={"Objects": objects},
    )


def get_photo_url(key: str) -> str:
    s3 = _get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": key},
        ExpiresIn=3600,
    )


def resolve_cover_photo(find) -> "object | None":
    """Return the Photo to use as the Find's thumbnail.

    Resolution order: explicitly chosen cover photo, else the oldest photo,
    else None. Requires ``find.photos`` to be loaded (ordered created_at desc).
    """
    if not find.photos:
        return None
    if find.cover_photo_id:
        for p in find.photos:
            if p.id == find.cover_photo_id:
                return p
    # photos are ordered newest-first, so the oldest is last
    return find.photos[-1]

