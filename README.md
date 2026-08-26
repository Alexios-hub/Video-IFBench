# Video-IFBench: Evaluating Instruction Following of Multimodal LLMs in Video Understanding Scenarios

<p align="center">
  <a href="https://scholar.google.com/citations?user=GcgqbCUAAAAJ&hl=zh-CN"><strong>Hongbo Liu</strong></a><sup>1,*</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=WRGF9B8AAAAJ"><strong>Peixian Chen</strong></a><sup>2,*</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=N_0VdSwAAAAJ"><strong>Sihan Liu</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=rQbW67AAAAAJ"><strong>Peiyuan Zhang</strong></a><sup>3</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=Bd6y_UsAAAAJ"><strong>Kai Zou</strong></a><sup>4</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=0dkD_dcAAAAJ"><strong>Dian Zheng</strong></a><sup>5</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=zBM8_XkAAAAJ"><strong>Xiaoxing Hu</strong></a><sup>3</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=kMui170AAAAJ"><strong>Yuhao Dong</strong></a><sup>6</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=C941xtsAAAAJ"><strong>Mengdan Zhang</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=29teR74AAAAJ"><strong>Yunhang Shen</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=LV8ejn8AAAAJ"><strong>Haoyu Cao</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=AjxoEpIAAAAJ"><strong>Wei Liu</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://github.com/Alexios-hub/Video-IFBench#no-profile" aria-disabled="true"><strong>Weibo Gu</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=IUtix9IAAAAJ"><strong>Xing Sun</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://github.com/Alexios-hub/Video-IFBench#no-profile" aria-disabled="true"><strong>Shengjie Zhao</strong></a><sup>1,&dagger;</sup>
</p>

<p align="center">
  <sup>1</sup>TJU &emsp;
  <sup>2</sup>Tencent Youtu Lab &emsp;
  <sup>3</sup>SJTU &emsp;
  <sup>4</sup>Tencent Hunyuan &emsp;
  <sup>5</sup>CUHK &emsp;
  <sup>6</sup>NTU
</p>

<p align="center">
  <sup>*</sup> Equal contribution &emsp;
  <sup>&dagger;</sup> Corresponding author
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Paper-arXiv%20pending-B31B1B?logo=arxiv" alt="Paper: arXiv pending">
  <a href="https://alexios-hub.github.io/Video-IFBench/">
    <img src="https://img.shields.io/badge/Project%20Page-Website-lightgrey?logo=googlechrome" alt="Project Page">
  </a>
  <a href="https://huggingface.co/datasets/Alexislhb/Video-IFBench">
    <img src="https://img.shields.io/badge/Dataset-HuggingFace-orange?logo=huggingface" alt="Dataset">
  </a>
</p>

<p align="center">
  <img src="docs/assets/paper/overview.webp" alt="Overview of the Video-IFBench construction and evaluation pipeline" width="100%">
</p>

## 🎬 Overview

**Video-IFBench** is a benchmark for evaluating instruction following in video understanding. The public release combines a final evaluation split with a lightweight toolkit for running and scoring multimodal LLMs through OpenAI-compatible endpoints.

Video-IFBench evaluates four instruction structures and separates task completion from fine-grained constraint satisfaction. Its evaluation protocol combines task-execution judging, semantic and video-grounded LLM judging, and deterministic rule-based checks.

## 🧩 Benchmark Design

### Instruction Structures

| Structure | Description |
|:---|:---|
| **Single** | A direct task paired with one or more response constraints. |
| **Multi** | Multiple requested operations or outputs composed within one instruction. |
| **Selection** | Conditional alternatives whose active branch is determined from video evidence. |
| **Nested** | Multi-level conditional instructions that require following the active reasoning path. |

### Evaluation Protocol

The scorer evaluates each response in three stages:

1. **Task execution judging** checks whether the active task was attempted.
2. **LLM-based constraint judging** evaluates semantic and video-grounded constraints.
3. **Rule-based function judging** deterministically verifies constraints after a structured extraction step.

The main metrics are:

- **TCSR:** the task-gated average constraint satisfaction rate.
- **TISR:** the task-gated strict instruction satisfaction rate, requiring all tasks and constraints to pass.

## 📊 Main Results

### Table 1: Main Benchmark Results

TCSR and TISR are reported for each instruction structure and for the overall benchmark. Best results within each model group are in **bold**.

| Model | Single TCSR | Single TISR | Multi TCSR | Multi TISR | Selection TCSR | Selection TISR | Nested TCSR | Nested TISR | Overall TCSR | Overall TISR |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **Proprietary Models** |  |  |  |  |  |  |  |  |  |  |
| Gemini-3-Pro | **79.6** | **52.3** | **88.6** | **58.8** | **68.5** | **59.2** | **53.7** | **46** | **76.5** | **54.5** |
| Gemini-3-Flash | 76.7 | 49.2 | 87.6 | 56.4 | 63.9 | 54.8 | 39.9 | 30.7 | 72.2 | 49.5 |
| Doubao-Seed-2.0-Pro-260215 | 76.7 | 44.6 | 87.1 | 51.1 | 46.5 | 38.2 | 17.8 | 14.4 | 65.7 | 40.8 |
| GPT-5.4 | 72.8 | 34.7 | 82.4 | 43.2 | 21.1 | 16.9 | 12.1 | 7.6 | 57.4 | 30.0 |
| **Open-source Models (Instruct)** |  |  |  |  |  |  |  |  |  |  |
| Qwen2.5-Omni-3B | 35.2 | 11.6 | 34.0 | 8.6 | 7.7 | 5.4 | 6.5 | 4.5 | 25.8 | 8.6 |
| Qwen2.5-Omni-7B | 46.3 | 16.6 | 48.6 | 14.9 | 15.6 | 11.5 | 8.9 | 5.5 | 36.0 | 13.5 |
| Qwen3-Omni-30B-A3B-Instruct | 57.9 | 21.4 | 62.9 | 22.9 | 17.2 | 14.3 | 6.1 | 4.1 | 44.3 | 18.0 |
| Gemma-4-E4B-it | 56.8 | 22.1 | 67.5 | 29.9 | 11.9 | 8.2 | 6.0 | 3.8 | 45.1 | 19.5 |
| Gemma-4-26B-A4B-it | 71.6 | 35.7 | 79.2 | 41.1 | 22.7 | 19.4 | 7.1 | 4.5 | 55.6 | 29.7 |
| Gemma-4-31B-it | **75.8** | **43.0** | 82.1 | **44.4** | **29.9** | **25.4** | 13.8 | **10.0** | **60.4** | **35.4** |
| InternVL3.5-8B-Instruct | 53.4 | 19.1 | 63.6 | 21.8 | 16.3 | 10.1 | 7.6 | 3.5 | 43.1 | 16.0 |
| InternVL3.5-14B-Instruct | 56.2 | 19.1 | 66.3 | 22.6 | 18.6 | 12.5 | 6.2 | 3.5 | 45.1 | 16.6 |
| InternVL3.5-30B-A3B-Instruct | 57.0 | 19.2 | 65.9 | 24.8 | 21.2 | 13.8 | **16.2** | 9.6 | 47.4 | 18.5 |
| InternVL3.5-38B-Instruct | 61.0 | 24.5 | 71.8 | 27.1 | 18.5 | 12.7 | 14.6 | 8.4 | 49.8 | 20.8 |
| InternVL3.5-241B-A28B-Instruct | 64.5 | 24.6 | 75.3 | 32.2 | 16.0 | 12.3 | 13.6 | 10.4 | 51.7 | 22.7 |
| Qwen3-VL-4B-Instruct | 55.6 | 19.9 | 65.6 | 20.9 | 15.1 | 11.4 | 8.7 | 5.1 | 44.3 | 16.4 |
| Qwen3-VL-8B-Instruct | 60.1 | 23.5 | 68.9 | 24.7 | 17.8 | 13.0 | 13.5 | 8.5 | 48.0 | 19.6 |
| Qwen3-VL-30B-A3B-Instruct | 56.8 | 19.9 | 70.4 | 25.4 | 17.0 | 12.3 | 13.6 | 9.5 | 47.2 | 18.6 |
| Qwen3-VL-235B-A22B-Instruct | 67.5 | 31.9 | 78.0 | 35.1 | 19.5 | 14.5 | 8.6 | 6.0 | 53.1 | 25.8 |
| Qwen3.5-4B-Instruct | 54.6 | 22.0 | 65.5 | 23.3 | 15.2 | 8.8 | 7.9 | 4.0 | 43.9 | 17.3 |
| Qwen3.5-9B-Instruct | 57.8 | 22.6 | 70.0 | 27.3 | 16.2 | 12.4 | 8.1 | 5.0 | 46.6 | 19.6 |
| Qwen3.5-27B-Instruct | 66.7 | 29.1 | 77.8 | 33.8 | 23.0 | 18.0 | 11.7 | 6.9 | 54.0 | 25.2 |
| Qwen3.5-35B-A3B-Instruct | 56.7 | 25.7 | 75.2 | 33.4 | 17.5 | 12.4 | 7.5 | 5.0 | 48.0 | 22.6 |
| Qwen3.5-122B-A10B-Instruct | 62.7 | 29.1 | 79.8 | 36.8 | 20.3 | 14.5 | 9.5 | 5.5 | 52.5 | 25.3 |
| Qwen3.5-397B-A17B-Instruct | 70.1 | 36.5 | **83.2** | 40.8 | 24.3 | 18.9 | 12.2 | 7.9 | 57.3 | 30.4 |
| **Open-source Models (Thinking)** |  |  |  |  |  |  |  |  |  |  |
| Qwen3-Omni-30B-A3B-Think | 66.6 | 30.0 | 75.1 | 36.8 | 24.8 | 18.5 | 10.1 | 5.5 | 53.1 | 26.2 |
| Qwen3-VL-30B-A3B-Think | 60.7 | 23.9 | 68.2 | 31.3 | 22.2 | 17.1 | 8.5 | 5.5 | 47.9 | 22.0 |
| Qwen3-VL-235B-A22B-Think | 74.7 | 37.7 | 84.4 | 45.0 | 31.4 | 24.9 | 14.1 | 10.3 | 60.9 | 33.5 |
| InternVL3.5-8B-Think | 53.7 | 18.0 | 63.8 | 21.6 | 18.4 | 13.7 | 9.6 | 6.5 | 43.8 | 16.5 |
| InternVL3.5-14B-Think | 55.9 | 18.7 | 67.1 | 24.7 | 19.4 | 14.7 | 12.3 | 7.5 | 46.4 | 18.1 |
| InternVL3.5-30B-A3B-Think | 54.4 | 18.0 | 67.8 | 26.1 | 25.6 | 17.1 | 11.9 | 7.6 | 47.0 | 18.7 |
| InternVL3.5-38B-Think | 58.8 | 21.4 | 71.2 | 24.8 | 18.3 | 11.6 | 16.4 | 10.5 | 49.1 | 19.1 |
| InternVL3.5-241B-A28B-Think | 64.9 | 22.7 | 76.4 | 33.8 | 20.5 | 15.8 | 11.8 | 6.5 | 52.5 | 22.3 |
| Qwen3.5-9B-Think | 67.1 | 35.9 | 77.6 | 39.8 | 39.1 | 32.0 | 16.9 | 11.9 | 56.0 | 32.2 |
| Qwen3.5-27B-Think | 74.0 | 40.1 | 82.2 | 46.3 | 42.1 | 34.0 | 24.7 | 20.0 | 62.5 | 37.5 |
| Qwen3.5-35B-A3B-Think | 72.4 | 37.9 | 85.2 | 49.1 | 38.2 | 31.5 | 23.3 | 19.8 | 62.8 | 37.2 |
| Qwen3.5-122B-A10B-Think | 77.0 | 45.6 | 84.2 | 50.1 | 46.5 | 39.4 | 23.9 | 19.7 | 65.2 | 41.7 |
| Qwen3.5-397B-A17B-Think | **79.4** | **48.5** | **86.0** | **52.8** | **52.1** | **44.9** | **33.0** | **28.2** | **69.6** | **46.1** |

### Table 2: Scaling by Task and Constraint Count

The task pass rate stays comparatively stable as instructions include more tasks, whereas strict instruction following drops sharply as the number of constraints increases.

#### (a) Task Scaling on Single and Multi Instructions

| Model | 1–4 Tasks | 5–8 Tasks | 9+ Tasks |
|:--|--:|--:|--:|
| Gemini-3-Pro | 95.6 | 94.9 | 96.3 |
| Gemini-3-Flash | 93.9 | 95.7 | 94.3 |
| Qwen3.5-397B-A17B-Think | 95.5 | 92.6 | 95.8 |
| Gemma-4-31B-it | 90.5 | 92.5 | 91.8 |
| Qwen3-Omni-30B-A3B-Instruct | 84.5 | 81.0 | 76.9 |
| Gemma-4-E4B-it | 81.0 | 79.1 | 84.1 |

*Task pass rate (%).*

#### (b) Constraint Scaling on Single Instructions

| Model | 1–4 Constraints | 5–8 Constraints | 9+ Constraints |
|:--|--:|--:|--:|
| Gemini-3-Pro | 62.7 | 51.8 | 46.9 |
| Gemini-3-Flash | 59.3 | 47.5 | 46.9 |
| Qwen3.5-397B-A17B-Think | 58.2 | 43.9 | 42.5 |
| Gemma-4-31B-it | 53.7 | 39.6 | 29.2 |
| Qwen3-Omni-30B-A3B-Instruct | 40.1 | 11.5 | 3.5 |
| Gemma-4-E4B-it | 38.4 | 12.9 | 7.1 |

*TISR (%).*

## 🚀 Getting Started

### Installation

```bash
git clone https://github.com/Alexios-hub/Video-IFBench.git
cd Video-IFBench
pip install -e .
```

### Dataset Preparation

Download the public evaluation split from [Hugging Face](https://huggingface.co/datasets/Alexislhb/Video-IFBench):

```bash
huggingface-cli download Alexislhb/Video-IFBench \
  --repo-type dataset \
  --local-dir data/Video-IFBench
```

The runner expects the following layout:

```text
data/Video-IFBench/
├── annotations/
│   └── annotations.jsonl
├── videos/
│   └── <video files>
└── subtitles/                 # optional timestamped ASR files
    └── <subtitle files>
```

Use this directory as `--dataset-root` when running inference.

### Run Inference

The public runner supports OpenAI-compatible endpoints, including OpenAI-style APIs, vLLM, SGLang, and other compatible servers.

```bash
video-ifbench-run \
  --dataset-root data/Video-IFBench \
  --output-dir outputs/model_name \
  --api-base http://localhost:8000/v1 \
  --model model_name \
  --media-mode video-url \
  --concurrency 32 \
  --resume
```

Each output file is a `*.response.json` record containing the model response and the metadata required for scoring.

If timestamped ASR files are available under `data/Video-IFBench/subtitles`, add `--use-asr` to append the paired transcript to the model input. Use `--subtitle-dir PATH` to point to another subtitle directory.

To retry only failed response files, use `--resume --retry-errors`. If a vLLM/Qwen endpoint does not accept `video-url` inputs, switch to `--media-mode frames --max-frames 32` to decode and sample frames locally.

### Score Responses

```bash
video-ifbench-score \
  --response-dir outputs/model_name \
  --output-json outputs/model_name/_instruction_following_report.json \
  --judge-api-base http://localhost:8001/v1 \
  --judge-model judge_model_name \
  --concurrency 16
```

Judge calls send `chat_template_kwargs={"enable_thinking": false}` by default. Use `--enable-thinking` to enable thinking, or `--thinking-mode auto` to omit this override for endpoints that do not accept it.

### Summarize Metrics

```bash
video-ifbench-summarize \
  --report outputs/model_name/_instruction_following_report.json \
  --model-name "model_name" \
  --format latex
```

The summarizer supports `latex`, `json`, and `csv` output formats.

### Usage Notes

- Model inference uses `--concurrency 32` by default.
- With `--resume`, use `--retry-errors` and `--retry-empty` for targeted reruns.
- Response scoring supports configurable `--concurrency`; tune it to the judge server throughput.
- Judge thinking is disabled by default to keep judge outputs JSON-only.
- The default media path sends each local video as a `video_url`. Frame mode additionally supports `--fps`, `--max-frames`, and `--max-video-long-side`.
- The public dataset is already cleaned to the final benchmark split; no additional filtering flag is required.

## 🗂️ Repository Structure

```text
Video-IFBench/
├── video_ifbench/
│   ├── run.py                 # inference runner
│   ├── score.py               # three-stage response scorer
│   ├── summarize.py           # metric report formatter
│   ├── metrics.py             # TCSR/TISR aggregation
│   ├── function_judges.py     # deterministic constraint judges
│   ├── dataset.py             # dataset loading and case iteration
│   ├── media.py               # video/frame input handling
│   └── openai_client.py       # OpenAI-compatible API client
├── tools/                     # optional video preparation utilities
├── tests/                     # metric, scoring, and ASR tests
├── docs/                      # static project page and assets
├── pyproject.toml
└── requirements.txt
```

## 📝 Citation

If this benchmark or toolkit is useful in your work, please cite the manuscript:

```bibtex
@misc{videoifbench2026,
  title  = {Video-IFBench: Evaluating Instruction Following of Multimodal LLMs in Video Understanding Scenarios},
  author = {Hongbo Liu and Peixian Chen and Sihan Liu and Peiyuan Zhang and Kai Zou and Dian Zheng and Xiaoxing Hu and Yuhao Dong and Mengdan Zhang and Yunhang Shen and Haoyu Cao and Wei Liu and Weibo Gu and Xing Sun and Shengjie Zhao},
  year   = {2026}
}
```

## 📄 License

The released [Video-IFBench dataset](https://huggingface.co/datasets/Alexislhb/Video-IFBench) is provided under the [CC BY-NC 4.0 license](https://creativecommons.org/licenses/by-nc/4.0/), as specified by its dataset card. This dataset license does not automatically apply to the evaluation code; consult the repository's code license once one is published.
<div align="center">

# Video-IFBench

### Evaluating Instruction Following of Multimodal LLMs in Video Understanding Scenarios

<p>
  <a href="https://openreview.net/forum?id=5X5p1XGhZE"><strong>Paper</strong></a> &nbsp;|&nbsp;
  <a href="https://alexios-hub.github.io/Video-IFBench/"><strong>Project Page</strong></a> &nbsp;|&nbsp;
  <a href="https://github.com/Alexios-hub/Video-IFBench"><strong>Code</strong></a> &nbsp;|&nbsp;
  <a href="https://huggingface.co/datasets/Alexislhb/Video-IFBench"><strong>Dataset</strong></a>
</p>

</div>

<p align="center">
  <img src="docs/assets/og.jpg" alt="Video-IFBench: instruction following for video understanding" width="100%">
</p>

## Overview

**Video-IFBench** is a benchmark for evaluating instruction following in video understanding. The public release combines a final evaluation split with a lightweight toolkit for running and scoring multimodal LLMs through OpenAI-compatible endpoints.

Video-IFBench evaluates four instruction structures and separates task completion from fine-grained constraint satisfaction. Its evaluation protocol combines task-execution judging, semantic and video-grounded LLM judging, and deterministic rule-based checks.

## Benchmark Design

### Instruction Structures

| Structure | Description |
|:---|:---|
| **Single** | A direct task paired with one or more response constraints. |
| **Multi** | Multiple requested operations or outputs composed within one instruction. |
| **Selection** | Conditional alternatives whose active branch is determined from video evidence. |
| **Nested** | Multi-level conditional instructions that require following the active reasoning path. |

### Evaluation Protocol

The scorer evaluates each response in three stages:

1. **Task execution judging** checks whether the active task was attempted.
2. **LLM-based constraint judging** evaluates semantic and video-grounded constraints.
3. **Rule-based function judging** deterministically verifies constraints after a structured extraction step.

The main metrics are:

- **TCSR:** the task-gated average constraint satisfaction rate.
- **TISR:** the task-gated strict instruction satisfaction rate, requiring all tasks and constraints to pass.

## Getting Started

### Installation

```bash
git clone https://github.com/Alexios-hub/Video-IFBench.git
cd Video-IFBench
pip install -e .
```

### Dataset Preparation

Download the public evaluation split from [Hugging Face](https://huggingface.co/datasets/Alexislhb/Video-IFBench):

```bash
huggingface-cli download Alexislhb/Video-IFBench \
  --repo-type dataset \
  --local-dir data/Video-IFBench
```

The runner expects the following layout:

```text
data/Video-IFBench/
├── annotations/
│   └── annotations.jsonl
├── videos/
│   └── <video files>
└── subtitles/                 # optional timestamped ASR files
    └── <subtitle files>
```

Use this directory as `--dataset-root` when running inference.

### Run Inference

The public runner supports OpenAI-compatible endpoints, including OpenAI-style APIs, vLLM, SGLang, and other compatible servers.

```bash
video-ifbench-run \
  --dataset-root data/Video-IFBench \
  --output-dir outputs/model_name \
  --api-base http://localhost:8000/v1 \
  --model model_name \
  --media-mode video-url \
  --concurrency 32 \
  --resume
```

Each output file is a `*.response.json` record containing the model response and the metadata required for scoring.

If timestamped ASR files are available under `data/Video-IFBench/subtitles`, add `--use-asr` to append the paired transcript to the model input. Use `--subtitle-dir PATH` to point to another subtitle directory.

To retry only failed response files, use `--resume --retry-errors`. If a vLLM/Qwen endpoint does not accept `video-url` inputs, switch to `--media-mode frames --max-frames 32` to decode and sample frames locally.

### Score Responses

```bash
video-ifbench-score \
  --response-dir outputs/model_name \
  --output-json outputs/model_name/_instruction_following_report.json \
  --judge-api-base http://localhost:8001/v1 \
  --judge-model judge_model_name \
  --concurrency 16
```

Judge calls send `chat_template_kwargs={"enable_thinking": false}` by default. Use `--enable-thinking` to enable thinking, or `--thinking-mode auto` to omit this override for endpoints that do not accept it.

### Summarize Metrics

```bash
video-ifbench-summarize \
  --report outputs/model_name/_instruction_following_report.json \
  --model-name "model_name" \
  --format latex
```

The summarizer supports `latex`, `json`, and `csv` output formats.

### Usage Notes

- Model inference uses `--concurrency 32` by default.
- With `--resume`, use `--retry-errors` and `--retry-empty` for targeted reruns.
- Response scoring supports configurable `--concurrency`; tune it to the judge server throughput.
- Judge thinking is disabled by default to keep judge outputs JSON-only.
- The default media path sends each local video as a `video_url`. Frame mode additionally supports `--fps`, `--max-frames`, and `--max-video-long-side`.
- The public dataset is already cleaned to the final benchmark split; no additional filtering flag is required.

## Repository Structure

```text
Video-IFBench/
├── video_ifbench/
│   ├── run.py                 # inference runner
│   ├── score.py               # three-stage response scorer
│   ├── summarize.py           # metric report formatter
│   ├── metrics.py             # TCSR/TISR aggregation
│   ├── function_judges.py     # deterministic constraint judges
│   ├── dataset.py             # dataset loading and case iteration
│   ├── media.py               # video/frame input handling
│   └── openai_client.py       # OpenAI-compatible API client
├── tools/                     # optional video preparation utilities
├── tests/                     # metric, scoring, and ASR tests
├── docs/                      # static project page and assets
├── pyproject.toml
└── requirements.txt
```

## Citation

If this benchmark or toolkit is useful in your work, please cite the manuscript:

```bibtex
@misc{videoifbench2026,
  title  = {Video-IFBench: Evaluating Instruction Following of Multimodal LLMs in Video Understanding Scenarios},
  author = {Anonymous Authors},
  year   = {2026},
  url    = {https://openreview.net/forum?id=5X5p1XGhZE}
}
```

## License

The released [Video-IFBench dataset](https://huggingface.co/datasets/Alexislhb/Video-IFBench) is provided under the [CC BY-NC 4.0 license](https://creativecommons.org/licenses/by-nc/4.0/), as specified by its dataset card. This dataset license does not automatically apply to the evaluation code; consult the repository's code license once one is published.
