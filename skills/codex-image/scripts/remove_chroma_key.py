#!/usr/bin/env python3
"""Remove a flat chroma-key background from an image and emit RGBA output.

Designed as a local post-processing helper for the codex-image transparent
image workflow:

    1. Generate the subject on a flat solid chroma-key background
       (default #00ff00; use #ff00ff for green-dominant subjects).
    2. Run this script to convert the key color to alpha.

The flag surface follows the codex-image SKILL.md transparent-image guidance:

    --auto-key {border,top-left,top-right,bottom-left,bottom-right,center}
    --key #RRGGBB
    --transparent-threshold N      pixels closer than N to key -> fully transparent
    --opaque-threshold N           pixels farther than N from key -> fully opaque
    --soft-matte                   linear interpolation between the two thresholds
    --despill                      reduce key-color cast on retained pixels
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print(
        "Pillow is required. Install with: pip install pillow",
        file=sys.stderr,
    )
    raise SystemExit(2)


KeyColor = tuple[int, int, int]


def parse_hex_color(value: str) -> KeyColor:
    raw = value.lstrip("#")
    if len(raw) != 6:
        raise argparse.ArgumentTypeError(f"invalid hex color: {value}")
    try:
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid hex color: {value}") from exc


def sample_key_color(img: Image.Image, mode: str) -> KeyColor:
    width, height = img.size
    if mode == "border":
        strip = 2
        regions = [
            img.crop((0, 0, width, strip)),
            img.crop((0, height - strip, width, height)),
            img.crop((0, 0, strip, height)),
            img.crop((width - strip, 0, width, height)),
        ]
        rs, gs, bs = [], [], []
        for region in regions:
            for r, g, b in region.getdata():
                rs.append(r)
                gs.append(g)
                bs.append(b)
        return (_median(rs), _median(gs), _median(bs))

    patch = max(4, min(width, height) // 32)
    anchors = {
        "top-left": (0, 0),
        "top-right": (width - patch, 0),
        "bottom-left": (0, height - patch),
        "bottom-right": (width - patch, height - patch),
        "center": ((width - patch) // 2, (height - patch) // 2),
    }
    if mode not in anchors:
        raise SystemExit(f"unknown --auto-key mode: {mode}")
    x, y = anchors[mode]
    region = img.crop((x, y, x + patch, y + patch))
    rs, gs, bs = zip(*region.getdata())
    return (_median(list(rs)), _median(list(gs)), _median(list(bs)))


def _median(values: list[int]) -> int:
    s = sorted(values)
    return s[len(s) // 2]


def remove_chroma_key(
    src: Path,
    dst: Path,
    *,
    key: KeyColor,
    transparent_threshold: float,
    opaque_threshold: float,
    soft_matte: bool,
    despill: bool,
) -> None:
    img = Image.open(src).convert("RGB")
    width, height = img.size
    pixels = img.load()
    out = Image.new("RGBA", (width, height))
    out_pixels = out.load()

    kr, kg, kb = key
    span = max(1.0, opaque_threshold - transparent_threshold)

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            # Channel-weighted distance gives green keys a sharper falloff.
            dr = r - kr
            dg = g - kg
            db = b - kb
            distance = (dr * dr + dg * dg + db * db) ** 0.5

            if distance <= transparent_threshold:
                out_pixels[x, y] = (0, 0, 0, 0)
                continue
            if distance >= opaque_threshold or not soft_matte:
                alpha = 255
            else:
                alpha = int(round((distance - transparent_threshold) / span * 255))
                alpha = max(0, min(255, alpha))

            if despill and alpha > 0:
                r, g, b = _despill_pixel(r, g, b, key)

            out_pixels[x, y] = (r, g, b, alpha)

    out.save(dst)


def _despill_pixel(r: int, g: int, b: int, key: KeyColor) -> tuple[int, int, int]:
    kr, kg, kb = key
    # Identify which channel the key is dominated by, and clamp that channel
    # to the average of the other two so the spill is neutralized.
    dominant = max(range(3), key=lambda i: key[i])
    if dominant == 1:  # green key
        cap = (r + b) // 2
        if g > cap:
            g = cap
    elif dominant == 0:  # red key
        cap = (g + b) // 2
        if r > cap:
            r = cap
    else:  # blue key
        cap = (r + g) // 2
        if b > cap:
            b = cap
    return r, g, b


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument(
        "--key",
        type=parse_hex_color,
        help="explicit hex key color, e.g. #00ff00 (overrides --auto-key)",
    )
    ap.add_argument(
        "--auto-key",
        default="border",
        choices=["border", "top-left", "top-right", "bottom-left", "bottom-right", "center"],
        help="sample the key color from this region of the image",
    )
    ap.add_argument("--transparent-threshold", type=float, default=12.0)
    ap.add_argument("--opaque-threshold", type=float, default=64.0)
    ap.add_argument("--soft-matte", action="store_true")
    ap.add_argument("--despill", action="store_true")
    args = ap.parse_args(argv)

    if not args.input.is_file():
        print(f"input not found: {args.input}", file=sys.stderr)
        return 2

    img = Image.open(args.input).convert("RGB")
    key = args.key if args.key else sample_key_color(img, args.auto_key)

    remove_chroma_key(
        args.input,
        args.out,
        key=key,
        transparent_threshold=args.transparent_threshold,
        opaque_threshold=args.opaque_threshold,
        soft_matte=args.soft_matte,
        despill=args.despill,
    )
    print(f"wrote {args.out} (key=#{key[0]:02x}{key[1]:02x}{key[2]:02x})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
