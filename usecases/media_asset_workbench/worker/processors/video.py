"""
Video processor - runs ffprobe against files on the S3 Files mount.
ffprobe treats the mounted path as a regular file; no streaming from S3 needed.
"""
import os
import json
import subprocess
import datetime


def process_video(file_path: str) -> dict:
    result = {
        'processed': False,
        'duration_seconds': None,
        'width': None,
        'height': None,
        'codec': None,
        'fps': None,
        'bitrate_kbps': None,
        'audio_codec': None,
        'audio_channels': None,
        'thumbnail_path': None,
        'tags': [],
        'error': None,
    }

    probe = _ffprobe(file_path)
    if probe is None:
        result['error'] = 'ffprobe not available or failed'
        return result

    try:
        fmt = probe.get('format', {})
        result['duration_seconds'] = float(fmt.get('duration', 0)) or None
        bitrate = fmt.get('bit_rate')
        if bitrate:
            result['bitrate_kbps'] = int(bitrate) // 1000

        for stream in probe.get('streams', []):
            codec_type = stream.get('codec_type')
            if codec_type == 'video' and result['codec'] is None:
                result['codec'] = stream.get('codec_name')
                result['width'] = stream.get('width')
                result['height'] = stream.get('height')
                result['fps'] = _parse_fps(stream.get('r_frame_rate', ''))
            elif codec_type == 'audio' and result['audio_codec'] is None:
                result['audio_codec'] = stream.get('codec_name')
                result['audio_channels'] = stream.get('channels')

        result['tags'] = _derive_tags(result)

        # Extract a thumbnail frame at 10% of duration
        thumb_path = _extract_thumbnail(file_path, result['duration_seconds'])
        result['thumbnail_path'] = thumb_path
        result['processed'] = True

    except Exception as exc:
        result['error'] = str(exc)

    return result


def _ffprobe(file_path: str) -> dict | None:
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            file_path,
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return json.loads(out.stdout)
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return None


def _parse_fps(fps_str: str) -> float | None:
    try:
        num, den = fps_str.split('/')
        return round(int(num) / int(den), 2)
    except Exception:
        return None


def _extract_thumbnail(file_path: str, duration: float | None) -> str | None:
    base, _ = os.path.splitext(file_path)
    thumb_path = f'{base}.thumb.jpg'
    try:
        offset = max(0, (duration or 10) * 0.1)
        cmd = [
            'ffmpeg', '-y', '-ss', str(offset),
            '-i', file_path,
            '-vframes', '1',
            '-vf', 'scale=320:-2',
            '-q:v', '5',
            thumb_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)
        return thumb_path
    except Exception:
        return None


def _derive_tags(info: dict) -> list:
    tags = []
    w = info.get('width') or 0
    if w >= 3840:
        tags.append('4k')
    elif w >= 1920:
        tags.append('hd')
    elif w > 0:
        tags.append('sd')

    if info.get('audio_codec'):
        tags.append('has-audio')

    dur = info.get('duration_seconds') or 0
    if dur < 60:
        tags.append('short-clip')
    elif dur < 600:
        tags.append('medium-clip')
    else:
        tags.append('long-form')

    codec = info.get('codec', '')
    if codec:
        tags.append(codec)

    return tags
