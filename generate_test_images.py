#!/usr/bin/env python3
"""Generate placeholder JPEGs for the scene survey dataset.

Creates:
    images/
      scene_01/
        rgb/01.jpg
        ir/01.jpg
        fusion_01/01.jpg
        fusion_02/01.jpg
      ...

Each image contains its relative file path as text.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


IMAGE_TYPES = ("rgb", "ir", "fusion_01", "fusion_02")


def load_font(size: int):
    """Use a common system font, with Pillow's default as a fallback."""
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_placeholder(path: Path, relative_path: str, width: int, height: int) -> None:
    image = Image.new("RGB", (width, height), (245, 245, 245))
    draw = ImageDraw.Draw(image)
    font = load_font(max(12, min(20, width // 18)))

    # Wrap the path to fit the image width.
    words = relative_path.split("/")
    lines: list[str] = []
    current = ""
    max_width = width - 24

    for word in words:
        candidate = word if not current else f"{current}/{word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_heights = [
        draw.textbbox((0, 0), line, font=font)[3] -
        draw.textbbox((0, 0), line, font=font)[1]
        for line in lines
    ]
    total_height = sum(line_heights) + 6 * (len(lines) - 1)
    y = max(8, (height - total_height) // 2)

    for line, line_height in zip(lines, line_heights):
        draw.text((12, y), line, fill=(20, 20, 20), font=font)
        y += line_height + 6

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="JPEG", quality=95, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate placeholder JPEGs for survey scenes."
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        default="images",
        help="Output image directory (default: images)",
    )
    parser.add_argument("--scenes", type=int, default=10)
    parser.add_argument("--min-images", type=int, default=1)
    parser.add_argument("--max-images", type=int, default=5)
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--height", type=int, default=180)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete the output directory first if it already exists.",
    )
    args = parser.parse_args()

    if args.scenes < 1:
        parser.error("--scenes must be at least 1")
    if args.min_images < 1 or args.max_images < args.min_images:
        parser.error("image count range must satisfy 1 <= min-images <= max-images")
    if args.width < 80 or args.height < 50:
        parser.error("image dimensions must be at least 80x50")

    output_dir = Path(args.output_dir)
    if args.clean and output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    rng = random.Random(args.seed)
    total = 0

    for scene_number in range(1, args.scenes + 1):
        scene_id = f"scene_{scene_number:02d}"

        for image_type in IMAGE_TYPES:
            count = rng.randint(args.min_images, args.max_images)

            for image_number in range(1, count + 1):
                relative_path = (
                    f"{output_dir.as_posix()}/{scene_id}/"
                    f"{image_type}/{image_number:02d}.jpg"
                )
                file_path = (
                    output_dir / scene_id / image_type /
                    f"{image_number:02d}.jpg"
                )
                make_placeholder(
                    file_path, relative_path, args.width, args.height
                )
                total += 1

    print(f"Created {total} JPEG images in: {output_dir}")
    print(f"Scenes: {args.scenes}")
    print(f"Image types per scene: {', '.join(IMAGE_TYPES)}")
    print(f"Images per scene/type: {args.min_images}-{args.max_images}")


if __name__ == "__main__":
    main()
