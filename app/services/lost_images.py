"""Owner-scoped, bounded, atomic batches of decoded image uploads."""
import asyncio
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import warnings
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from app.services.core import get_or_404, owner_only
from app.store import store

UPLOAD_DIR = Path(__file__).resolve().parents[2] / 'uploads/lost_items'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 5 * 1024 * 1024
MAX_IMAGES = 5
FORMATS = {'JPEG': ('.jpg', {'image/jpeg'}), 'PNG': ('.png', {'image/png'}),
           'WEBP': ('.webp', {'image/webp'})}
mutation_lock = asyncio.Lock()


def owned_item(item_id, actor_id):
    item = get_or_404(store.lost, item_id)
    owner_only(item, actor_id)
    return item


def image_path(image):
    # Never trust a client-supplied path or the original filename.
    filename = image['url'].rsplit('/', 1)[-1]
    if filename != Path(filename).name or '\\' in filename or filename in {'.', '..'}:
        raise HTTPException(422, 'Invalid stored image path')
    path = (UPLOAD_DIR / filename).resolve()
    if path.parent != UPLOAD_DIR.resolve():
        raise HTTPException(422, 'Invalid stored image path')
    return path


def validate_content(data, upload):
    suffix = Path(upload.filename or '').suffix.lower()
    if suffix not in {'.jpg', '.jpeg', '.png', '.webp'}:
        raise HTTPException(422, 'Supported image formats: JPG, JPEG, PNG, WebP')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                fmt = image.format
                if fmt not in FORMATS:
                    raise ValueError('Unsupported image format')
                if image.width * image.height > 20_000_000:
                    raise ValueError('Image dimensions exceed 20 megapixels')
                image.verify()
            # verify() alone does not decode all pixel data (e.g. truncated JPEG).
            with Image.open(BytesIO(data)) as image:
                image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise HTTPException(422, 'Invalid, damaged or excessively large image content') from error
    extension, mime_types = FORMATS[fmt]
    suffix_format = 'JPEG' if suffix in {'.jpg', '.jpeg'} else suffix[1:].upper()
    if suffix_format != fmt or upload.content_type not in mime_types:
        raise HTTPException(422, 'File extension, content type and image content must match')
    return extension


async def upload_images(item_id, actor_id, files):
    paths = []
    try:
        async with mutation_lock:
            item = owned_item(item_id, actor_id)
            images = item.get('images', [])
            if not files or len(images) + len(files) > MAX_IMAGES:
                raise HTTPException(422, 'An announcement can have at most 5 images')
            prepared = []
            for upload in files:
                data = await upload.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise HTTPException(413, 'Each image must be at most 5 MB')
                extension = validate_content(data, upload)
                image_id = uuid4().hex
                filename = image_id + extension
                prepared.append(({'id': image_id, 'url': f'/uploads/lost_items/{filename}'}, data))
            try:
                for image, data in prepared:
                    path = image_path(image)
                    with path.open('xb') as target:
                        paths.append(path)
                        target.write(data)
            except OSError as error:
                raise HTTPException(500, 'Unable to save images; no images were added') from error
            item['images'] = images + [image for image, _ in prepared]
            return item
    except BaseException:
        for path in paths:
            path.unlink(missing_ok=True)
        raise
    finally:
        for upload in files:
            await upload.close()


async def delete_image(item_id, actor_id, image_id):
    async with mutation_lock:
        item = owned_item(item_id, actor_id)
        images = item.get('images', [])
        image = next((image for image in images if image['id'] == image_id), None)
        if image is None:
            raise HTTPException(404, 'Image not found on this announcement')
        remove_file(image)
        item['images'] = [image for image in images if image['id'] != image_id]


async def delete_item(item_id, actor_id):
    async with mutation_lock:
        item = owned_item(item_id, actor_id)
        for image in list(item.get('images', [])):
            remove_file(image)
            # A disk error on a later image leaves a valid, retryable announcement.
            item['images'].remove(image)
        del store.lost[item_id]


def remove_file(image):
    try:
        image_path(image).unlink(missing_ok=True)
    except OSError as error:
        raise HTTPException(500, 'Unable to remove image; please retry') from error
