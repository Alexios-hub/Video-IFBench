# Video-IFBench Evaluation Code

This repository contains the public evaluation toolkit for **Video-IFBench**, a benchmark for video instruction following. The dataset is hosted on Hugging Face at [`Alexislhb/Video-IFBench`](https://huggingface.co/datasets/Alexislhb/Video-IFBench).

The release code is intentionally lightweight. It supports OpenAI-compatible model endpoints for both model inference and judging, so it can be used with OpenAI-style APIs, vLLM, SGLang, or other compatible servers.

## Installation

```bash
pip install -e .
```

## Dataset Preparation

Download the Video-IFBench dataset from Hugging Face before running evaluation:

```bash
huggingface-cli download Alexislhb/Video-IFBench \
  --repo-type dataset \
  --local-dir data/Video-IFBench
```

The downloaded directory is expected to contain the annotation file and video files used by the runner:

```text
data/Video-IFBench/
├── annotations/
│   └── annotations.jsonl
└── videos/
    └── <video files>
```

Use this directory as `--dataset-root` when running model inference.

## Run a model

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

Each output file is a `*.response.json` record containing the model response and all metadata needed for scoring.

If timestamped ASR files are available under `data/Video-IFBench/subtitles`, add `--use-asr` to append the paired transcript to the model input. Use `--subtitle-dir PATH` to point at a different subtitle directory.

If a run produced error response files, use `--resume --retry-errors` to rerun only those files. If a vLLM/Qwen endpoint fails on `video-url` inputs, switch to `--media-mode frames --max-frames 32` so videos are decoded client-side before sending requests.

## Score responses

```bash
video-ifbench-score \
  --response-dir outputs/model_name \
  --output-json outputs/model_name/_instruction_following_report.json \
  --judge-api-base http://localhost:8001/v1 \
  --judge-model judge_model_name \
  --concurrency 16
```

The scorer uses three judging stages:

1. task execution judging, which checks whether the active task was attempted;
2. LLM-based constraint judging for semantic/video-grounded constraints;
3. rule-based function judges for constraints that can be deterministically verified after an extraction step.

Scoring sends `chat_template_kwargs={"enable_thinking": false}` by default for judge calls. Use `--enable-thinking` to turn thinking back on, or `--thinking-mode auto` to omit the chat-template override for endpoints that do not accept it.

## Summarize main metrics

```bash
video-ifbench-summarize \
  --report outputs/model_name/_instruction_following_report.json \
  --model-name "model_name" \
  --format latex
```

The main metrics are:

- **TCSR**: task-gated average constraint satisfaction rate;
- **TISR**: task-gated strict instruction satisfaction rate, requiring all tasks and constraints to pass.

## Notes

- The public runner currently supports OpenAI-compatible APIs only.
- Model inference uses `--concurrency 32` by default.
- Model inference supports `--retry-errors` and `--retry-empty` with `--resume` for targeted reruns.
- Response scoring supports `--concurrency`; tune it to your judge server throughput.
- Response scoring disables Qwen/vLLM thinking by default to keep judge outputs JSON-only.
- The default media path passes each local video file as a `video_url` input. Use `--media-mode frames` together with `--fps`, `--max-frames`, and `--max-video-long-side` to send sampled frames instead.
- The public dataset release is already cleaned to the final benchmark split, so no additional filtering flag is needed.
