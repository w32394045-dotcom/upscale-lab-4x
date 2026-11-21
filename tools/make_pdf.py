#!/usr/bin/env python3
"""Collect upscaled pages into one A4 PDF, keeping the original page order.

img2pdf embeds the JPEGs without recompressing them, so a big 4x page keeps its
detail and the whole job stays low on memory.
"""
import argparse
import os

import img2pdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--list", default="", help="ordered image list (one name per line)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--paper", default="A4", choices=("A4", "A5", "B5", "LETTER"))
    args = parser.parse_args()

    sizes = {"A4": (210, 297), "A5": (148, 210), "B5": (176, 250), "LETTER": (216, 279)}
    width_mm, height_mm = sizes[args.paper]

    if args.list:
        with open(args.list, "r", encoding="utf-8") as handle:
            stems = [os.path.splitext(line.strip())[0] for line in handle if line.strip()]
    else:
        stems = sorted(os.path.splitext(name)[0] for name in os.listdir(args.dir))

    paths = []
    for stem in stems:
        for extension in (".png", ".jpg", ".jpeg", ".webp"):
            candidate = os.path.join(args.dir, stem + extension)
            if os.path.exists(candidate):
                paths.append(candidate)
                break
        else:
            print("missing page:", stem)

    if not paths:
        raise SystemExit("no pages found")

    layout = img2pdf.get_layout_fun((img2pdf.mm_to_pt(width_mm), img2pdf.mm_to_pt(height_mm)))
    with open(args.out, "wb") as handle:
        handle.write(img2pdf.convert(paths, layout_fun=layout))
    size_mb = os.path.getsize(args.out) / (1024 * 1024)
    print("wrote %s (%d pages, %.1f MB)" % (args.out, len(paths), size_mb))


if __name__ == "__main__":
    main()
