"""Owner-scoped, bounded, atomic batches of decoded image uploads."""
from io import BytesIO
import logging
from pathlib import Path
from uuid import uuid4
import warnings
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from app.models import LostItem, LostItemImage
from app.services.core import get_or_404, owner_only

UPLOAD_DIR = Path(__file__).resolve().parents[2] / 'uploads/lost_items'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 5 * 1024 * 1024
MAX_IMAGES = 5
FORMATS = {'JPEG': ('.jpg', {'image/jpeg'}), 'PNG': ('.png', {'image/png'}),
           'WEBP': ('.webp', {'image/webp'})}
logger = logging.getLogger(__name__)


def owned_item(db, item_id, user, *, allow_admin=False):
    item = get_or_404(db, LostItem, item_id, lock=True)
    owner_only(item, user, allow_admin=allow_admin)
    return item


def image_path(url):
    # Never trust a client-supplied path or the original filename.
    filename = url.rsplit('/', 1)[-1]
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


def upload_images(db, item_id, user, files):
    item = owned_item(db, item_id, user)
    if not files or len(item.images) + len(files) > MAX_IMAGES:
        raise HTTPException(422, 'An announcement can have at most 5 images')
    prepared = []
    for upload in files:
        data = upload.file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, 'Each image must be at most 5 MB')
        extension = validate_content(data, upload)
        image_id = uuid4().hex
        image = LostItemImage(id=image_id, url=f'/uploads/lost_items/{image_id}{extension}')
        prepared.append((image, data))

    item.images.extend(image for image, _ in prepared)
    db.flush()
    paths = []
    try:
        try:
            for image, data in prepared:
                path = image_path(image.url)
                with path.open('xb') as target:
                    paths.append(path)
                    target.write(data)
        except OSError as error:
            raise HTTPException(500, 'Unable to save images; no images were added') from error
        db.commit()
    except Exception:
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.exception('Unable to clean up an uncommitted upload')
        raise
    return item


def delete_image(db, item_id, user, image_id):
    item = owned_item(db, item_id, user, allow_admin=True)
    image = next((image for image in item.images if image.id == image_id), None)
    if image is None:
        raise HTTPException(404, 'Image not found on this announcement')
    remove_file(image.url)
    item.images.remove(image)
    db.commit()


def delete_item(db, item_id, user):
    item = owned_item(db, item_id, user, allow_admin=True)
    try:
        for image in list(item.images):
            remove_file(image.url)
            item.images.remove(image)
    except HTTPException:
        # Preserve the existing retry behavior for a disk error partway through.
        db.commit()
        raise
    db.delete(item)
    db.commit()


def remove_file(url):
    try:
        image_path(url).unlink(missing_ok=True)
    except OSError as error:
        raise HTTPException(500, 'Unable to remove image; please retry') from error
