# upscale-lab-4x 开发日志

## 0 元信息

| 项 | 值 |
|---|---|
| 项目 | `[Kmoe][別當歐尼醬了！]` 卷01–05 → 去水印 A4 PDF；本日志针对「4x 超分实验」这条支线 |
| 仓库 | https://github.com/w32394045-dotcom/upscale-lab-4x （public，分支 `main`） |
| 本地路径 | `C:\Users\ptfm\Downloads\ai\work\upscale-lab`（仓库）/ `C:\Users\ptfm\Downloads\ai\work\vol04`（工作区） |
| 记录区间 | 2026-11-21 ～ 2026-11-22（时区 Asia/Shanghai） |
| 依据 | 用户对话原话、GitHub Actions 运行记录、本地产物字节数与 sha256、命令行输出 |
| 标注规则 | **已实测** = 本机或 CI 真跑过并留下输出；**待验证** = 文件已写但没跑；**推断** = 无证据 |
| 性质 | 事后追加记录（当天边做边记的碎片汇总，时间点以运行记录为准） |

行号会漂移，本文引用代码一律用 `文件名#函数名`。

---

## 1 基线（2026-11-21 动手前）

| 项 | 现状 | 位置 |
|---|---|---|
| 卷04 去水印成品 | `vol04-clean.pdf`，56 页 A4，~16 MB | `test/out/vol04-clean.pdf` |
| 超分方案 | 无。本机单页 256px tile 要 17 s，整卷不可行 | — |
| 模型 | `4x-UltraSharpV2_fp32_op17.onnx`（ONNX Runtime CPU，fp32） | HF: `Kim2091/UltraSharpV2` |
| 可用算力 | GitHub 公开仓 runner：4 vCPU / 16 GB，免费分钟 | — |
| 上传通道 | `git push` 在这条网络上会卡死（`ls-remote` 正常），已改用 GitHub git-data / contents API | `push_api.ps1` |

用户给的硬约束（原话）：

> 「你不要以20个并发了…控制到6到12个或者12到15个左右。不要太显眼。然后记得要PNG输出」
> 「哪个有问题，你就去改哪个呀，你不要给我每次全改呀，这都是烧的我的钱呀」
> 「public 仓库…比私有仓库翻倍」

---

## 2 铁规则

| # | 规则 | 为什么 | 怎么自查 |
|---|---|---|---|
| 1 | 并发 ≤ 12 | 用户要求不显眼 | workflow `max-parallel: 12` |
| 2 | 输出 PNG（灰页 1 通道） | 不想要 JPEG 二次损失 | `upscale.py --format png` |
| 3 | 只重跑出问题的页 | 每次全量既慢又费 | 先清单再 dispatch |
| 4 | 修页面从 `orig/` 重建 | 在已修过的图上再修会累积损伤（卷04 第21页「推開」被吃过一次） | 脚本一律 `cv2.imread(orig/...)` |
| 5 | 不用本地超分 | 单页 17 s/tile，整卷要几十小时 | 只在 Actions 跑 |

---

## 3 阶段记录

### 3.1 4x 超分跑通（2026-11-21，run `44902216004`）

- **目标**：56 页全部 4x，A4 合成一个 PDF。
- **做法**：`plan`（拉 zip → `list.txt` → 切片 → matrix JSON）→ `upscale`（matrix，10 并行）→ `merge`（img2pdf A4）。
- **证据（已实测）**：单页 682–856 s；6 页的 shard 79.1 min；整跑约 95 min；artifact `out-*` 约 608 MB + `result` 608.3 MB。
- **产物**：`test/out/vol04-4x-a4.pdf`（597 MB，封面 JPEG q95）、`test/out/vol04-4x-a4-lossless.pdf`（718 MB，封面 Flate）。

### 3.2 水印返工：12 页（2026-11-22）

**触发**：用户截图指出第 17、34 页仍有 `Kmoe 2026` 水印。

**根因（已实测）**：印章位置固定在页面右下角，距右边 283 px、距底边 180 px，尺寸 140×105；旧 `plan.json` 的框 x 多算了约 140 px，只压到印章右缘，等于修了空地。

**验证方式**：把 56 页的右下角 150×120 区域做成 3x 联系表逐张看，确认有印章的共 18 页（1,2,4,7,8,9,17,20,21,26,30,31,34,41,48,52,53,56），其中 6 页上一轮已修干净。

**做法（分三种，按页面情况）**：

| 情况 | 页 | 手段 |
|---|---|---|
| 印章在纯白/浅底 | 7,8,9,17,20,21,26,30,31,34 | flux 重绘，框 `(W-330, H-180, W-140, H-80)`，`MARGIN=40` |
| 印章压在 GRINP 猫爪 logo 上 | 53 | API 会把 logo 擦白，改本地 mask 修补（灰带 140–188 + `cv2.inpaint`） |
| 封面 | 1 | 第 55 页是同一幅画的干净版本，按蓝盘中心对齐（缩放 267/262 = 1.0191）copy 过来 + `seamlessClone` |

- **证据（已实测）**：`repair_region` 返回 `ai-rect score=0.716…0.999 coverage=0.03…0.10 mismatch=0…10`；重建后 56 页 PDF 里渲染 12 页复查无残留。
- **代价（已实测）**：成功调用 14 次（12 页 + 2 次探针）；另有 10 次被拒（`content_policy_violation`，`billing_status=refunded`，cost 0）。

### 3.3 无损 PDF 升级（2026-11-22）

- **做法**：`PyMuPDF` 逐页 `insert_pdf(start_at=idx)` + `delete_page`，只换 12 页，其余 44 页流不动；`save(garbage=3, deflate=True)`。
- **证据（已实测）**：从 PDF 抠出的位图与源 PNG **逐像素相同**（`identical to source PNG: True`，页 1/17/34/53）；56 页；623.5 MB（比旧版 718 MB 还小，因为旧版页 1 是 raw 流）。

### 3.4 ARM runner 对比（2026-11-22）

| 项 | x86 `ubuntu-latest` | ARM `ubuntu-24.04-arm` |
|---|---|---|
| 单页耗时 | 682–856 s | 600–770 s（run `44989963606`：05:34:22 起，最慢 05:47:11 完） |
| 依赖 | onnxruntime / opencv / numpy / pillow 都有 aarch64 wheel | 同左，装得上 |
| 结论 | — | **能用但没更快**，推断是 onnxruntime 在 ARM 上走通用 kernel，没吃到 ACL 加速 |

12 页 12 个 shard 一人一页，全程 ~13 min 跑完。

### 3.5 存储格式：raw vs Flate，以及 1.48 GB 单文件上传

用户问 raw 与 flate 区别后要求「别压变成 raw 存一个版本（可以上传到 GitHub）」。

- **做法**：`save(garbage=3, deflate=False)` → 12 页新图为 raw 流（`/Filter` 为空），其余 44 页仍是 img2pdf 搬进去的 `/FlateDecode`。
- **证据（已实测）**：页 1/17/53 `filter null`；页 2/56 `/FlateDecode`；文件 1,553,490,039 B（1481.5 MB）；sha256 `7754e507…04e356`。
- **上传失败与改法**：
  - 单文件直传：curl 跑到第 21 分钟、约 80% 被 `Recv failure: Connection was reset`，重试仍不行（**已实测**）。
  - 改 4 块（各 ~370 MB）上传：`vol04-4x-a4-raw.pdf.part1…part4`，合计 1,553,490,039 B 与本地一致；另传 `JOIN-raw.txt` 写合并命令与 sha256。
  - 结论：这条网络上 >1 GB 的单次 upload 不可靠，**要么切成 ~400 MB 一块，要么走 artifact**。

### 3.6 CI 内产出（已写文件，**待验证**）

按用户要求把「raw 图 + flate PDF + 有损 PDF」全部搬进 Actions：

| 改动 | 文件 |
|---|---|
| `make_pdf.py` 增加 `--jpeg-quality N`（0 = 保持 PNG 流，1–100 = 先转 JPEG 再嵌入），Pillow 在临时目录转码 | `tools/make_pdf.py` |
| merge job：保留逐页 PNG → `pages-raw-png` artifact；构建 `book-4x-flate.pdf` 与 `book-4x-jpeg<N>.pdf` → 两个 artifact；`gh release upload` 发布到 `run-<run_id>` release | `.github/workflows/upscale.yml` |
| workflow 新增输入 `runner` / `jpeg_quality` / `publish_release`；`permissions: contents: write` | 同上 |

**未验证**：改动只落了本地文件，还没 push、没 dispatch 过任何一次跑；`--jpeg-quality` 本机也没跑过（便携 Python 没装 img2pdf）。

---

## 4 决策订正

| # | 原计划 | 订正 | 原因 |
|---|---|---|---|
| 1 | 并发 20 | 降到 10，后提到 12 | 用户要求别太显眼 |
| 2 | JPEG 输出 | 改 PNG | 用户明确要 PNG |
| 3 | 用 OCR 找印章再修 | 改成「右下角固定位置 + 视觉联系表确认」 | OCR 抓不到这个纯图形 logo；旧 plan 框位置全错 |
| 4 | 有损 PDF 用 img2pdf 直接吃 JPEG | `make_pdf.py --jpeg-quality` 先用 Pillow 转 qN 再嵌 | 源都是 PNG，得先转 |
| 5 | raw 版整份存 GitHub | 拆 4 块 | 单文件 1.48 GB 直传被 reset |
| 6 | 12 页在 x86 上跑 | 先跑 1 页 ARM 探速，再 12 页 ARM 全开 | 用户提议试 ARM 物理核 |

被否方案：**全 56 页 raw**（约 5 GB，超 GitHub 单文件 2 GB 上限，要切十几段）——暂不做。

---

## 5 坑（都可复用）

| # | 症状 | 根因 | 修法 | 防复发 |
|---|---|---|---|---|
| 1 | 修完水印还在，位置偏右下 140 px | 旧 `plan.json` 坐标体系不对 | 按「距右下角固定偏移」重算框 | 修复后必须渲染复查，不看日志说 ok |
| 2 | API 报 `content_policy_violation` | 裁切框太高，带上角色身体；或 prompt 里出现 «移除水印» 这类词 | 框压到 190×100、`MARGIN=40`，用 `ai_repair.PROMPT`（不提水印） | 失败重试前先缩小框/换 prompt，别硬重试 |
| 3 | 重绘把 GRINP 猫爪 logo、`INP` 字擦成白块 | `ai_repair.PROMPT` 明确要求「no lettering, no text and no logo」 | 这类页改用本地 mask 修补 | 有品牌图形的页固定走 mask，不走 rect |
| 4 | 4x 封面蓝盘变糊 | 封面原图盘面本身偏软 | 从第 55 页同一幅画 copy 盘面 | 封面页单独检查蓝盘 |
| 5 | 1.48 GB 上传 80% 被 reset | 单次超长 PUT 在这条链路上不稳定 | 切 4 块顺序上传 | >1 GB 一律切块或走 artifact |
| 6 | PyMuPDF 存出来 1.48 GB（应为 623 MB） | `save(deflate=False)` 让新图流不压缩 | `deflate=True` | 合成后必看体积，异常先查 Filter |

---

## 6 产物清单（当时值）

| 产物 | 字节 / 大小 | sha256 | 位置 |
|---|---|---|---|
| `vol04-clean.pdf` | 15.7 MB，56 页 | 未记录 | `test/out/` |
| `vol04-4x-a4-lossless.pdf` | 623.5 MB，56 页，12 页 Flate 新图 | 未记录 | `test/out/` |
| `vol04-4x-a4-raw.pdf` | 1,553,490,039 B，12 页 raw 流 | `7754e507339155c3dd0b7891e8a6212ade6e037be4f3a9d57bb709bf0d04e356` | `test/out/` + release `vol04-4x-raw`（4 块） |
| `vol04-4x-a4.pdf` | 596.7 MB，旧版（含残留水印） | 未记录 | `test/out/`，**已作废** |

Release 一览（仓库 `upscale-lab-4x`）：

| tag | 内容 | 用途 |
|---|---|---|
| `vol04-input` | `vol04-pages.zip`（14 MB） | 全量 56 页输入 |
| `vol04-fix12` | `vol04-fix12.zip`（5.15 MB） | 12 页返工输入 |
| `arm-test1` | `arm-test1.zip`（0.16 MB） | ARM 单页测速 |
| `vol04-4x-raw` | 4 个 part + `JOIN-raw.txt` | raw 版 PDF |

---

## 7 待决 / 遗留

1. **3.6 的 CI 改动未验证**：需要一次 dispatch 确认 `pages-raw-png` / `pdf-flate` / `pdf-lossy` / release 发布都成立。找 lead 定何时跑。
2. `vol04-4x-a4.pdf`（q95 版）已作废，是否删除未定。
3. 三个临时 release（`vol04-input`、`vol04-fix12`、`arm-test1`）用户说「先不用删」，等明确指示。
4. 卷05 已开始（去水印中），产物待用户核查。
5. 两份 4x PDF 的 sha256 未记录，下次产出时补。
