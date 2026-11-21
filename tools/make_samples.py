#!/usr/bin/env python3
"""Generate synthetic manga-like sample pages (pure python, no deps, no artwork).

Writes plain RGB PNG files (zlib only) so the plan job needs nothing installed.

Usage: python3 make_samples.py <out dir>
"""
import os
import struct
import sys
import zlib


class Canvas(object):
    def __init__(self, width, height, background=255):
        self.width = width
        self.height = height
        self.pixels = bytearray([background]) * (width * height * 3)

    def set(self, x, y, value):
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 3
            self.pixels[offset:offset + 3] = bytes((value, value, value))

    def rect(self, x0, y0, x1, y1, value, thickness=1):
        for x in range(x0, x1 + 1):
            for t in range(thickness):
                self.set(x, y0 + t, value)
                self.set(x, y1 - t, value)
        for y in range(y0, y1 + 1):
            for t in range(thickness):
                self.set(x0 + t, y, value)
                self.set(x1 - t, y, value)

    def fill(self, x0, y0, x1, y1, value):
        for y in range(y0, y1 + 1):
            offset = (y * self.width + x0) * 3
            row = bytes((value, value, value)) * (x1 - x0 + 1)
            self.pixels[offset:offset + len(row)] = row

    def circle(self, cx, cy, radius, value, thickness=3):
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                distance = (x - cx) ** 2 + (y - cy) ** 2
                if (radius - thickness) ** 2 <= distance <= radius * radius:
                    self.set(x, y, value)


def write_png(path, canvas):
    def chunk(tag, data):
        payload = tag + data
        return (struct.pack(">I", len(data)) + payload
                + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF))

    raw = bytearray()
    stride = canvas.width * 3
    for y in range(canvas.height):
        raw.append(0)  # filter type 0
        raw += canvas.pixels[y * stride:(y + 1) * stride]
    header = struct.pack(">IIBBBBB", canvas.width, canvas.height, 8, 2, 0, 0, 0)
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n")
        handle.write(chunk(b"IHDR", header))
        handle.write(chunk(b"IDAT", zlib.compress(bytes(raw), 6)))
        handle.write(chunk(b"IEND", b""))


def page(width, height, index):
    canvas = Canvas(width, height)
    canvas.rect(0, 0, width - 1, height - 1, 0, 4)
    canvas.rect(20, 20, width // 2 - 10, height // 2 - 10, 0, 3)
    canvas.rect(width // 2 + 10, 20, width - 20, height - 20, 0, 3)
    for offset in range(22, width // 2 - 30, 12):
        for y in range(24, height // 2 - 12):
            canvas.set(offset, y, 0)
    canvas.circle(width // 4, height // 4, 60, 30, 3)
    canvas.fill(width // 4 - 26, height // 4 - 20, width // 4 - 14, height // 4 - 8, 10)
    canvas.fill(width // 4 + 14, height // 4 - 20, width // 4 + 26, height // 4 - 8, 10)
    canvas.fill(width // 4 - 20, height // 4 + 24, width // 4 + 20, height // 4 + 32, 15)
    for step in range(6):
        x = width // 2 + 40 + step * 70
        y = 60 + (step % 3) * 120
        canvas.fill(x, y, x + 40, y + 26, 230)
        canvas.rect(x, y, x + 40, y + 26, 0, 2)
    canvas.fill(40, height - 50, 40 + 8 * 22, height - 30, 40)
    return canvas


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "input"
    os.makedirs(out_dir, exist_ok=True)
    for index, (width, height) in enumerate(((760, 1080), (1080, 760), (900, 1200)), 1):
        canvas = page(width, height, index)
        path = os.path.join(out_dir, "sample-%d.png" % index)
        write_png(path, canvas)
        print("sample-%d.png %dx%d" % (index, width, height))


if __name__ == "__main__":
    main()
