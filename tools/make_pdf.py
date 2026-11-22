#!/usr/bin/env python3
"""Collect upscaled pages into one A4 PDF, keeping the original page order.

Two modes:

* lossless (default) -- img2pdf passes the PNG's own zlib stream straight into
  the PDF (FlateDecode), so the 4x detail is kept byte for byte.
* lossy (--jpeg-quality N) -- every page is re-encoded as JPEG at quality N
  first; the file shrinks a lot at the cost of some ringing on line art.
"""
import argparse
import os
import shutil
import tempfile

import img2pdf


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--list", default="", help="ordered image list (one name per line)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--paper", default="A4", choices=("A4", "A5", "B5", "LETTER"))
    parser.add_argument("--jpeg-quality", type=int, default=0,
                        help="0 keeps the PNG streams (lossless); 1-100 re-encodes as JPEG")
    return parser.parse_args()


def ordered_paths(directory, list_file):
    if list_file:
        with open(list_file, "r", encoding="utf-8") as handle:
            stems = [os.path.splitext(line.strip())[0] for line in handle if line.strip()]
    else:
        stems = sorted(os.path.splitext(name)[0] for name in os.listdir(directory))

    paths = []
    for stem in stems:
        for extension in (".png", ".jpg", ".jpeg", ".webp"):
            candidate = os.path.join(directory, stem + extension)
            if os.path.exists(candidate):
                paths.append(candidate)
                break
        else:
            print("missing page:", stem)
    return paths


def main():
    args = parse_args()
    sizes = {"A4": (210, 297), "A5": (148, 210), "B5": (176, 250), "LETTER": (216, 279)}
    width_mm, height_mm = sizes[args.paper]

    paths = ordered_paths(args.dir, args.list)
    if not paths:
        raise SystemExit("no pages found")

    workdir = None
    if args.jpeg_quality > 0:
        from PIL import Image
        workdir = tempfile.mkdtemp(prefix="pages-jpg-")
        converted = []
        for path in paths:
            target = os.path.join(workdir, os.path.splitext(os.path.basename(path))[0] + ".jpg")
            with Image.open(path) as image:
                image.convert("RGB").save(target, "JPEG", quality=args.jpeg_quality,
                                          subsampling=0, optimize=True)
            converted.append(target)
        paths = converted
        print("re-encoded %d pages as JPEG q%d" % (len(paths), args.jpeg_quality))

    layout = img2pdf.get_layout_fun((img2pdf.mm_to_pt(width_mm), img2pdf.mm_to_pt(height_mm)))
    try:
        with open(args.out, "wb") as handle:
            handle.write(img2pdf.convert(paths, layout_fun=layout))
    finally:
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)

    size_mb = os.path.getsize(args.out) / (1024 * 1024)
    print("wrote %s (%d pages, %.1f MB)" % (args.out, len(paths), size_mb))


if __name__ == "__main__":
    main()
