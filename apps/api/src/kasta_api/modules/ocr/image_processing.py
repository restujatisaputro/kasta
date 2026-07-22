from __future__ import annotations

import math
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


@dataclass(frozen=True, slots=True)
class ProcessedImage:
    data: bytes
    content_type: str
    width: int
    height: int
    perceptual_hash: str


def preprocess_receipt_image(data: bytes) -> ProcessedImage:
    with Image.open(BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
        cropped = _content_crop(image)
        grayscale = ImageOps.grayscale(cropped)
        contrasted = ImageOps.autocontrast(grayscale, cutoff=1)
        contrasted = ImageEnhance.Contrast(contrasted).enhance(1.25)
        sharpened = contrasted.filter(ImageFilter.UnsharpMask(radius=1.4, percent=140, threshold=3))
        output = BytesIO()
        sharpened.save(output, format="JPEG", quality=90, optimize=True)
        return ProcessedImage(
            data=output.getvalue(),
            content_type="image/jpeg",
            width=sharpened.width,
            height=sharpened.height,
            perceptual_hash=perceptual_hash(sharpened),
        )


def perceptual_hash(image: Image.Image) -> str:
    pixels = _flattened_pixels(ImageOps.grayscale(image).resize((32, 32), Image.Resampling.LANCZOS))
    coefficients: list[float] = []
    for vertical in range(8):
        for horizontal in range(8):
            value = 0.0
            for y in range(32):
                for x in range(32):
                    value += (
                        pixels[y * 32 + x]
                        * math.cos((2 * x + 1) * horizontal * math.pi / 64)
                        * math.cos((2 * y + 1) * vertical * math.pi / 64)
                    )
            coefficients.append(value)
    median_source = sorted(coefficients[1:])
    median = median_source[len(median_source) // 2]
    bits = 0
    for coefficient in coefficients:
        bits = (bits << 1) | int(coefficient > median)
    return f"{bits:016x}"


def hash_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def _content_crop(image: Image.Image) -> Image.Image:
    grayscale = ImageOps.grayscale(image)
    border = [
        *_flattened_pixels(grayscale.crop((0, 0, grayscale.width, 1))),
        *_flattened_pixels(
            grayscale.crop((0, grayscale.height - 1, grayscale.width, grayscale.height))
        ),
        *_flattened_pixels(grayscale.crop((0, 0, 1, grayscale.height))),
        *_flattened_pixels(
            grayscale.crop((grayscale.width - 1, 0, grayscale.width, grayscale.height))
        ),
    ]
    background = sorted(border)[len(border) // 2]
    difference = grayscale.point(lambda value: 255 if abs(value - background) > 18 else 0)
    box = difference.getbbox()
    if box is None:
        return image
    left, top, right, bottom = box
    if (right - left) * (bottom - top) < image.width * image.height * 0.25:
        return image
    margin_x = max(8, image.width // 100)
    margin_y = max(8, image.height // 100)
    return image.crop(
        (
            max(0, left - margin_x),
            max(0, top - margin_y),
            min(image.width, right + margin_x),
            min(image.height, bottom + margin_y),
        )
    )


def _flattened_pixels(image: Image.Image) -> list[int]:
    return [
        int(value[0] if isinstance(value, tuple) else value) for value in image.get_flattened_data()
    ]
