# Video-IFBench Evaluation Code

This repository contains the public evaluation toolkit for **Video-IFBench**, a benchmark for video instruction following. The dataset is hosted on Hugging Face at [`Alexislhb/Video-IFBench`](https://huggingface.co/datasets/Alexislhb/Video-IFBench).

The release code is intentionally lightweight. It supports OpenAI-compatible model endpoints for both model inference and judging, so it can be used with OpenAI-style APIs, vLLM, SGLang, or other compatible servers.

## Installation

```bash
pip install -e .
```

## Dataset

By default, the runner downloads annotations and videos from Hugging Face:

```bash
video-ifbench-run --repo-id Alexislhb/Video-IFBench ...
```

If you have already downloaded the dataset, pass a local dataset root that contains `annotations/annotations.jsonl` and the `videos/` directory:

```bash
video-ifbench-run --dataset-root /path/to/Video-IFBench ...
```

## Run a model

```bash
video-ifbench-run \
  --repo-id Alexislhb/Video-IFBench \
  --output-dir outputs/my_model \
  --api-base http://localhost:8000/v1 \
  --model my-openai-compatible-model \
  --api-key EMPTY \
  --media-mode frames \
  --max-frames 32 \
  --max-video-long-side 720 \
  --resume
```

Each output file is a `*.response.json` record containing the model response and all metadata needed for scoring.

## Score responses

```bash
video-ifbench-score \
  --response-dir outputs/my_model \
  --output-json outputs/my_model/_instruction_following_report.json \
  --judge-api-base http://localhost:8001/v1 \
  --judge-model judge-model-name \
  --judge-api-key EMPTY
```

The scorer uses three judging stages:

1. task execution judging, which checks whether the active task was attempted;
2. LLM-based constraint judging for semantic/video-grounded constraints;
3. rule-based function judges for constraints that can be deterministically verified after an extraction step.

## Summarize main metrics

```bash
video-ifbench-summarize \
  --report outputs/my_model/_instruction_following_report.json \
  --model-name "MyModel" \
  --format latex
```

The main metrics are:

- **TCSR**: task-gated average constraint satisfaction rate;
- **TISR**: task-gated strict instruction satisfaction rate, requiring all tasks and constraints to pass.

## Notes

- The public runner currently supports OpenAI-compatible APIs only.
- The default media path samples video frames and sends them as image inputs. Use `--max-frames`, `--fps`, and `--max-video-long-side` to control frame extraction.
- The public dataset release is already cleaned to the final benchmark split, so no additional filtering flag is needed.
