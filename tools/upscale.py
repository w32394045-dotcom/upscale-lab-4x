#!/usr/bin/env python3
"""Tiled 4x super-resolution with an ONNX model (no GPU required).

The model expects NCHW float32 in 0..1 and returns 4x the size.  Tiles are cut
with an overlap and only the inner part of each tile is pasted back, so there are
no visible seams.

Usage:
  python upscale.py --indir input --outdir out --list list.txt \
      --model models/4x-UltraSharpV2_fp32_op17.onnx \
      --tile 256 --overlap 16 --threads 4 [--format png|jpg] [--max-pixels N]
"""
import argparse
import os
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort


def load_model(path, threads):
    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(path, sess_options=options,
                                   providers=["CPUExecutionProvider"])
    return session, session.get_inputs()[0].name


def upscale_tile(session, name, tile):
    x = np.transpose(tile[:, :, ::-1].astype(np.float32) / 255.0, (2, 0, 1))[None]
    x = np.ascontiguousarray(x)
    out = session.run(None, {name: x})[0]
    out = np.transpose(out[0], (1, 2, 0))
    return np.clip(out[:, :, ::-1] * 255.0, 0, 255).astype(np.uint8)


def upscale_image(session, input_name, image, tile, overlap, scale=4):
    height, width = image.shape[:2]
    out = np.zeros((height * scale, width * scale, 3), np.uint8)
    if tile <= 0 or (tile >= height and tile >= width):
        return upscale_tile(session, input_name, image)
    step = max(1, tile - overlap)
    tiles = 0
    for y0 in range(0, height, step):
        for x0 in range(0, width, step):
            y1 = min(y0 + tile, height)
            x1 = min(x0 + tile, width)
            patch = image[y0:y1, x0:x1]
            # the model is fully convolutional but keep a minimum size
            if patch.shape[0] < 8 or patch.shape[1] < 8:
                continue
            result = upscale_tile(session, input_name, patch)
            # valid (non-overlapping) area inside this tile, in output pixels
            left = 0 if x0 == 0 else overlap // 2
            top = 0 if y0 == 0 else overlap // 2
            right = (x1 - x0) if x1 >= width else (x1 - x0) - (overlap - overlap // 2)
            bottom = (y1 - y0) if y1 >= height else (y1 - y0) - (overlap - overlap // 2)
            oy0, ox0 = (y0 + top) * scale, (x0 + left) * scale
            oy1, ox1 = (y0 + bottom) * scale, (x0 + right) * scale
            out[oy0:oy1, ox0:ox1] = result[top * scale:bottom * scale,
                                           left * scale:right * scale]
            tiles += 1
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--list", default="", help="text file with image names, one per line")
    parser.add_argument("--model", default="models/4x-UltraSharpV2_fp32_op17.onnx")
    parser.add_argument("--tile", type=int, default=256)
    parser.add_argument("--overlap", type=int, default=16)
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--format", choices=("png", "jpg"), default="png")
    parser.add_argument("--color", action="store_true", help="keep 24-bit even for grey pages")
    parser.add_argument("--shard-tag", default="")
    args = parser.parse_args()

    threads = args.threads or (os.cpu_count() or 2)
    session, input_name = load_model(args.model, threads)
    print("threads=%d tile=%d overlap=%d model=%s"
          % (threads, args.tile, args.overlap, args.model), flush=True)

    if args.list:
        with open(args.list, "r", encoding="utf-8") as handle:
            names = [line.strip() for line in handle if line.strip()]
    else:
        names = sorted(os.listdir(args.indir))

    os.makedirs(args.outdir, exist_ok=True)
    started = time.time()
    total_tiles = 0
    for index, name in enumerate(names, 1):
        source = os.path.join(args.indir, name)
        image = cv2.imread(source, cv2.IMREAD_COLOR)
        if image is None:
            print("skip unreadable", name, flush=True)
            continue
        per_image = time.time()
        result = upscale_image(session, input_name, image, args.tile, args.overlap)
        stem = os.path.splitext(name)[0]
        extension = ".png" if args.format == "png" else ".jpg"
        target = os.path.join(args.outdir, stem + extension)
        if args.format == "png":
            # Manga scans are grey; a 1-channel PNG keeps full detail and is far
            # smaller than 24-bit.  Colour pages keep their colour.
            spread = int((result.max(axis=2).astype(np.int16)
                          - result.min(axis=2).astype(np.int16)).max())
            if spread <= 12 and not args.color:
                grey = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
                cv2.imwrite(target, grey, [int(cv2.IMWRITE_PNG_COMPRESSION), 6])
            else:
                cv2.imwrite(target, result, [int(cv2.IMWRITE_PNG_COMPRESSION), 6])
        else:
            cv2.imwrite(target, result, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        total_tiles += 1
        print("[%d/%d] %s %dx%d -> %dx%d in %.1fs"
              % (index, len(names), name, image.shape[1], image.shape[0],
                 result.shape[1], result.shape[0], time.time() - per_image), flush=True)
    print("done %d images in %.1f minutes" % (total_tiles, (time.time() - started) / 60.0),
          flush=True)


if __name__ == "__main__":
    sys.exit(main())
