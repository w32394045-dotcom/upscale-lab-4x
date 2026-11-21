# upscale-lab-4x

Public-repo GitHub Actions lab for **4x super-resolution** of manga/comic page
scans with an ONNX model (CPU only). One dispatch fans the pages out over up to
10 parallel runners (public repos get 4 vCPU / 16 GB) and merges the result into
one A4 PDF.

## How it works

```
plan      fetch images (zip URL or samples/) -> ordered list -> N shard files -> matrix
upscale   matrix job per shard: tile the page, run the ONNX model 4x, paste tiles back
merge     collect shard outputs -> book-4x-a4.pdf (img2pdf, no recompression)
```

Model: [`4x-UltraSharpV2_fp32_op17.onnx`](https://huggingface.co/Kim2091/UltraSharpV2)
(downloaded in the job, cached with `actions/cache`).

## Run it

Actions -> **upscale4x** -> *Run workflow*:

| input | meaning |
| --- | --- |
| `input_url` | URL of a **zip** containing the page images (empty = generate synthetic samples) |
| `shards` | how many parallel runners (1鈥?0) |
| `tile` | tile size; 256 is a good CPU/memory compromise, 0 = whole page |
| `overlap` | tile overlap (16 keeps seams invisible) |
| `make_pdf` | merge into `book-4x-a4.pdf` |

Artifacts of the run:

* `out-<n>` 鈥?the upscaled pages of that shard (JPEG q92)
* `result` 鈥?`book-4x-a4.pdf` (A4 pages, 4x artwork, no page margins)

## Local use

```bash
pip install onnxruntime numpy opencv-python-headless pillow img2pdf
curl -L -o models/4x-UltraSharpV2_fp32_op17.onnx \
  https://huggingface.co/Kim2091/UltraSharpV2/resolve/main/4x-UltraSharpV2_fp32_op17.onnx

python tools/upscale.py --indir input --outdir out --list list.txt \
  --model models/4x-UltraSharpV2_fp32_op17.onnx --tile 256 --overlap 16 --threads 4
python tools/make_pdf.py --dir out --list list.txt --out book-4x-a4.pdf --paper A4
```

`list.txt` holds one image name per line; it defines the page order and lets the
shards be split without touching the images.

## Notes

* Tiles are cut with overlap and only the inner part of each tile is written back,
  so the output is seamless.
* `tile=0` sends whole pages through the model: fastest per pixel but the memory
  peak grows with the page size (a 1680x1080 page needs ~1.5 GB).
* 4x of a 1080x1680 page is 4320x6720 鈥?that is roughly A4 at 600 dpi, which is
  what the PDF layout targets.
* Only images you are allowed to process belong in an input zip.
