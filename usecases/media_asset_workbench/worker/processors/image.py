"""
Image processor - runs on the EC2 worker against files accessed via S3 Files mount.
Uses standard file I/O; no S3 SDK calls needed because S3 Files exposes the bucket
as a POSIX filesystem at /mnt/assets.
"""
import os
import io
import json
import struct
import datetime

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


THUMBNAIL_SIZE = (320, 320)


def process_image(file_path: str) -> dict:
    result = {
        'processed': False,
        'width': None,
        'height': None,
        'format': None,
        'mode': None,
        'exif': {},
        'thumbnail_path': None,
        'tags': [],
        'error': None,
    }

    if not PIL_AVAILABLE:
        result['error'] = 'Pillow not installed'
        return result

    try:
        with Image.open(file_path) as img:
            result['width'] = img.width
            result['height'] = img.height
            result['format'] = img.format or os.path.splitext(file_path)[1].lstrip('.').upper()
            result['mode'] = img.mode

            # Extract EXIF
            exif_data = _extract_exif(img)
            result['exif'] = exif_data

            # Auto-tags from EXIF
            result['tags'] = _derive_tags(exif_data, img)

            # Generate thumbnail alongside the original (still on S3 Files mount)
            thumb_path = _make_thumbnail_path(file_path)
            _write_thumbnail(img, thumb_path)
            result['thumbnail_path'] = thumb_path
            result['processed'] = True

    except Exception as exc:
        result['error'] = str(exc)

    return result


def _extract_exif(img: 'Image.Image') -> dict:
    exif = {}
    try:
        for tag_id, value in img.getexif().items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            if isinstance(value, bytes):
                continue
            if isinstance(value, tuple):
                value = list(value)
            exif[tag_name] = value
    except Exception:
        pass
    return exif


def _derive_tags(exif: dict, img: 'Image.Image') -> list:
    tags = []
    make = exif.get('Make', '')
    model = exif.get('Model', '')
    if make or model:
        tags.append('camera')
        if make:
            tags.append(make.strip().lower().replace(' ', '-'))

    date_str = exif.get('DateTimeOriginal', '') or exif.get('DateTime', '')
    if date_str:
        try:
            dt = datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            tags.append(str(dt.year))
            tags.append(dt.strftime('%Y-%m'))
        except ValueError:
            pass

    w, h = img.width, img.height
    if w >= 3840:
        tags.append('4k')
    elif w >= 1920:
        tags.append('hd')

    if img.mode == 'RGBA':
        tags.append('transparency')

    return list(dict.fromkeys(tags))  # deduplicate, preserve order


def _make_thumbnail_path(original_path: str) -> str:
    base, ext = os.path.splitext(original_path)
    return f'{base}.thumb.jpg'


def _write_thumbnail(img: 'Image.Image', thumb_path: str) -> None:
    thumb = img.copy()
    thumb.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
    if thumb.mode in ('RGBA', 'P'):
        thumb = thumb.convert('RGB')
    thumb.save(thumb_path, 'JPEG', quality=80, optimize=True)
