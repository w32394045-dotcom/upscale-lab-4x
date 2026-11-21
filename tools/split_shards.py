#!/usr/bin/env python3
"""Split an ordered image list into N shard files (for the Actions matrix)."""
import argparse
import json
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", required=True)
    parser.add_argument("--shards", type=int, default=12)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--matrix-out", default="")
    args = parser.parse_args()

    with open(args.list, "r", encoding="utf-8") as handle:
        names = [line.strip() for line in handle if line.strip()]
    os.makedirs(args.out_dir, exist_ok=True)
    count = max(1, min(args.shards, len(names)))
    size = (len(names) + count - 1) // count
    chunks = [names[i:i + size] for i in range(0, len(names), size)]
    for index, chunk in enumerate(chunks, 1):
        with open(os.path.join(args.out_dir, "shard-%02d.txt" % index), "w",
                  encoding="utf-8") as handle:
            handle.write("\n".join(chunk) + "\n")
    matrix = {"shard": list(range(1, len(chunks) + 1))}
    print("shards=%d images=%d" % (len(chunks), len(names)))
    print(json.dumps(matrix))
    if args.matrix_out:
        with open(args.matrix_out, "w", encoding="utf-8") as handle:
            handle.write("matrix=" + json.dumps(matrix) + "\n")


if __name__ == "__main__":
    main()
