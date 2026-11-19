#!/usr/bin/env python3

import argparse
from pathlib import Path

import cv2


def downscale(src: Path, dst: Path):
    image = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)

    if image is None:
        print(f"Skipping unreadable image: {src}")
        return

    height, width = image.shape[:2]

    resized = cv2.resize(
        image,
        (round(width / 2), round(height / 2)),
        interpolation=cv2.INTER_AREA
    )

    dst.parent.mkdir(parents=True, exist_ok=True)

    if not cv2.imwrite(str(dst), resized, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        print(f"Failed to save: {dst}")
        return

    print(f"{src.name}: {width}x{height} -> "
          f"{resized.shape[1]}x{resized.shape[0]} -> {dst}")


def main():
    parser = argparse.ArgumentParser(
        description="Downscale RGB images to half size"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)

    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"Input does not exist: {args.input}")

    if args.input.is_file():
        downscale(args.input, args.output)

    elif args.input.is_dir():
        extensions = {".png", ".jpg", ".jpeg", ".bmp"}

        for src in sorted(args.input.rglob("*")):
            if src.is_file() and src.suffix.lower() in extensions:
                if not src.stem.endswith("_half"):
                    dst = args.output / f"{src.stem}_half.jpg"
                    downscale(src, dst)


if __name__ == "__main__":
    main()
