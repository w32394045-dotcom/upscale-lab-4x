# upscale-lab-4x

4x super-resolution of page scans on **GitHub Actions runners** (CPU only), with
an ONNX model. One dispatch fans the pages out over up to 10 parallel jobs and
merges everything into one A4 PDF.

Public repositories get **4 vCPU / 16 GB** runners and free minutes, which is why
this repo is public. The page images themselves only live here while a run is in
flight — put them in a release asset, run, then delete the release.

## Pipeline

```
plan      fetch images (zip URL, or synthetic samples) -> ordered list.txt -> N shard files -> matrix
upscale   one matrix job per shard: tile each page, run the ONNX model 4x, write PNG
merge     collect the shard outputs -> book-4x-a4.pdf (img2pdf, pages are not recompressed)
```

Model: [`4x-UltraSharpV2_fp32_op17.onnx`](https://huggingface.co/Kim2091/UltraSharpV2)
(49 MB, downloaded by the job and cached with `actions/cache`).

## Usage

1. Zip the pages and upload it somewhere the runner can download (e.g. a release
   asset of this repo: `Releases -> Draft a new release -> attach the zip`).
2. `Actions -> upscale4x -> Run workflow`:

| input | meaning |
| --- | --- |
| `input_url` | URL of the **zip** with the page images (empty = generate synthetic samples) |
| `shards` | parallel runners, 1–10 (keep it at ~10; each shard is one job) |
| `tile` | tile size, 256 is the CPU/memory sweet spot, `0` = whole page |
| `overlap` | tile overlap, 16 keeps the seams invisible |
| `make_pdf` | merge into `book-4x-a4.pdf` |

Outputs of a run:

* `out-<n>` — the 4x pages of that shard, PNG (grey pages are stored as one channel)
* `result` — `book-4x-a4.pdf`, one page per input image, in `list.txt` order

Name the files `0001.jpg`, `0002.jpg`, … before zipping: `list.txt` is a plain
sort of the names, so zero-padded prefixes fix the page order.

## Measured cost (public repo, 4 vCPU)

A 1086×1680 manga page becomes 4344×6720 and takes **11–14 minutes** of one
runner (`tile=256`, `overlap=16`, 4 threads). 56 pages over 10 parallel shards:
**~95 minutes wall clock**, ~608 MB of PNG + a ~608 MB A4 PDF.

Tuning notes:

* `tile` bigger → fewer boundary pastes but quadratic CPU cost; 256 was ~24 s per
  tile on these runners, 192 and 128 are not faster per pixel.
* `tile=0` (whole page) is the fastest per pixel but needs ~1.5 GB per page and
  makes one long step; only use it for small pages.
* Artifacts count toward the repo storage quota — delete old runs when done:
  `Actions -> the run -> artifacts` or `DELETE /repos/{owner}/{repo}/actions/artifacts/{id}`.

## Local use

```bash
pip install onnxruntime numpy opencv-python-headless pillow img2pdf
curl -L -o models/4x-UltraSharpV2_fp32_op17.onnx \
  https://huggingface.co/Kim2091/UltraSharpV2/resolve/main/4x-UltraSharpV2_fp32_op17.onnx

python3 tools/upscale.py --indir input --outdir out --list list.txt \
  --model models/4x-UltraSharpV2_fp32_op17.onnx --tile 256 --overlap 16 --threads 4
python3 tools/make_pdf.py --dir out --list list.txt --out book-4x-a4.pdf --paper A4
```

`tools/make_samples.py` writes three synthetic pages, so the whole pipeline can
be tried without any external input.

## Files

```
.github/workflows/upscale.yml   plan -> matrix -> merge
tools/upscale.py                tiled 4x inference (ONNX Runtime, CPU)
tools/split_shards.py           split list.txt into shard files + emit the matrix JSON
tools/make_pdf.py               A4 PDF from the upscaled pages (img2pdf, lossless embed)
tools/make_samples.py           dependency-free synthetic test pages
```

## Notes

* Tiles are cut with overlap and only the inner part of each tile is written back,
  so the output has no visible seams.
* 4x of a 1080×1680 page is 4320×6720, i.e. about A4 at 600 dpi — which is what
  the PDF layout targets.
* The workflow never commits images to git: inputs come from `input_url`, outputs
  are run artifacts.
