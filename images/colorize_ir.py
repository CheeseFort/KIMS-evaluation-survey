#!/usr/bin/env python3

import argparse
from pathlib import Path

import cv2
import numpy as np


SCALE = 4.5


def colorize(src: Path, dst: Path, colormap: int) -> None:
    ir = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)

    if ir is None:
        print(f"Skipping unreadable file: {src}")
        return

    if ir.ndim != 2:
        print(f"Skipping non-grayscale image: {src}")
        return

    if ir.dtype != np.uint16:
        print(f"Warning: {src} is {ir.dtype}, expected uint16")

    # Normalize to 8-bit.
    ir8 = cv2.normalize(
        ir, None, 0, 255, cv2.NORM_MINMAX
    ).astype(np.uint8)

    # Apply color map.
    colored = cv2.applyColorMap(ir8, colormap)

    # Upscale
    height, width = colored.shape[:2]
    enlarged = cv2.resize(
        colored,
        (round(width * SCALE), round(height * SCALE)),
        interpolation=cv2.INTER_LANCZOS4
    )

    dst.parent.mkdir(parents=True, exist_ok=True)

    # Save as JPEG.
    cv2.imwrite(
        str(dst),
        enlarged,
        [cv2.IMWRITE_JPEG_QUALITY, 95]
    )

    print(f"{src} -> {dst} ({width * SCALE}x{height * SCALE})")


def main():
    parser = argparse.ArgumentParser(
        description="Colorize, upscale, and convert 16-bit IR PNGs to JPEG"
    )

    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path,
                        default=Path("colorized"))
    parser.add_argument("--map", default="jet",
                        choices=["inferno", "jet", "turbo",
                                 "hot", "viridis", "magma"])

    args = parser.parse_args()

    maps = {
        "inferno": cv2.COLORMAP_INFERNO,
        "jet": cv2.COLORMAP_JET,
        "turbo": cv2.COLORMAP_TURBO,
        "hot": cv2.COLORMAP_HOT,
        "viridis": cv2.COLORMAP_VIRIDIS,
        "magma": cv2.COLORMAP_MAGMA,
    }

    if args.input.is_file():
        colorize(
            args.input,
            args.output.with_suffix(".jpg"),
            maps[args.map]
        )

    elif args.input.is_dir():
        for src in sorted(args.input.glob("*.png")):
            dst = args.output / f"{src.stem}.jpg"
            colorize(src, dst, maps[args.map])

    else:
        parser.error(f"Input does not exist: {args.input}")


if __name__ == "__main__":
    main()