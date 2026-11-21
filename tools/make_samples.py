#!/usr/bin/env python3
"""Generate synthetic manga-like sample pages (no third-party artwork in the repo).

Usage: python make_samples.py <out dir>
"""
import os
import sys

import cv2
import numpy as np


def page(index, width, height, seed):
    rng = np.random.RandomState(seed)
    img = np.full((height, width, 3), 255, np.uint8)
    cv2.rectangle(img, (0, 0), (width - 1, height - 1), (0, 0, 0), 4)
    cv2.rectangle(img, (20, 20), (width // 2 - 10, height // 2 - 10), (0, 0, 0), 3)
    cv2.rectangle(img, (width // 2 + 10, 20), (width - 20, height - 20), (0, 0, 0), 3)
    for offset in range(0, width // 2 - 40, 12):
        cv2.line(img, (22 + offset, 24), (22 + offset, height // 2 - 12), (0, 0, 0), 2)
    cx, cy = width // 4, height // 4
    cv2.circle(img, (cx, cy), 60, (25, 25, 25), 3)
    cv2.circle(img, (cx - 20, cy - 12), 8, (10, 10, 10), -1)
    cv2.circle(img, (cx + 20, cy - 12), 8, (10, 10, 10), -1)
    cv2.ellipse(img, (cx, cy + 26), (22, 12), 0, 0, 180, (10, 10, 10), 3)
    for _index in range(8):
        x = rng.randint(width // 2 + 30, width - 60)
        y = rng.randint(40, height - 60)
        cv2.rectangle(img, (x, y), (x + 40, y + 26), (230, 230, 230), -1)
        cv2.rectangle(img, (x, y), (x + 40, y + 26), (0, 0, 0), 2)
    cv2.putText(img, "SAMPLE PANEL %d" % index, (40, height - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    return img


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "input"
    os.makedirs(out_dir, exist_ok=True)
    pages = [(1, 760, 1080), (2, 1080, 760), (3, 900, 1200)]
    for index, width, height in pages:
        image = page(index, width, height, 7 + index)
        # a colour page keeps the colour path of the pipeline covered too
        if index == 3:
            image[:, :, 2] = np.clip(image[:, :, 2].astype(np.int16) + 60, 0, 255)
            image[:, :, 1] = np.clip(image[:, :, 1].astype(np.int16) + 20, 0, 255)
        cv2.imwrite(os.path.join(out_dir, "sample-%d.png" % index), image)
        print("sample-%d.png %dx%d" % (index, width, height))


if __name__ == "__main__":
    main()
