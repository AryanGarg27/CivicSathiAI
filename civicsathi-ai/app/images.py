"""Bounded decode, orientation correction and metadata-free image encoding."""
import base64
import binascii
import io
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 16_000_000
MIMES = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}


def normalize_image(encoded, mime):
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 2_500_000:
            raise ValueError('Photo must be no larger than 2.5 MB.')
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as original:
                if MIMES.get(original.format) != mime:
                    raise ValueError('Image contents do not match the selected file type.')
                if getattr(original, 'n_frames', 1) != 1:
                    raise ValueError('Please upload a still photograph, not an animation.')
                original.load()
                oriented = ImageOps.exif_transpose(original)
                oriented.thumbnail((1280, 1280))
                clean = Image.new('RGB', oriented.size, 'white')
                if 'A' in oriented.getbands():
                    clean.paste(oriented.convert('RGB'), mask=oriented.getchannel('A'))
                else:
                    clean.paste(oriented.convert('RGB'))
                output = io.BytesIO()
                clean.save(output, format='JPEG', quality=85)
                return output.getvalue(), 'image/jpeg'
    except (binascii.Error, UnidentifiedImageError, OSError,
            Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError('Invalid image or image dimensions too large.') from exc
