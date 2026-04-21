from .image import process_image
from .video import process_video

SUPPORTED_EXTENSIONS = {
    'image': {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff', '.bmp'},
    'video': {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'},
}


def get_asset_type(path: str) -> str:
    import os
    ext = os.path.splitext(path)[1].lower()
    for asset_type, extensions in SUPPORTED_EXTENSIONS.items():
        if ext in extensions:
            return asset_type
    return 'other'


def process_asset(file_path: str, asset_type: str) -> dict:
    if asset_type == 'image':
        return process_image(file_path)
    if asset_type == 'video':
        return process_video(file_path)
    return {'processed': False, 'reason': f'no processor for type: {asset_type}'}
