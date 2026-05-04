from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

from . import DEFAULT_REPO_ID
from .dataset import iter_instruction_cases, load_annotation_records, resolve_video_path
from .media import build_multimodal_user_content, sample_video_frames
from .openai_client import OpenAICompatibleClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an OpenAI-compatible model on Video-IFBench.")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--dataset-root", default=None, help="Local dataset root. If omitted, files are downloaded from Hugging Face.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--api-base", required=True, help="OpenAI-compatible base URL, e.g. http://localhost:8000/v1")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--model", required=True)
    parser.add_argument("--instruction-types", nargs="*", default=None, choices=["single", "multi", "selection", "nested"])
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--media-mode", choices=["frames", "video-url"], default="frames")
    parser.add_argument("--max-frames", type=int, default=32)
    parser.add_argument("--fps", type=float, default=None)
    parser.add_argument("--max-video-long-side", type=int, default=720)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout-sec", type=float, default=300.0)
    return parser.parse_args()


def build_messages(case, video_path: Path, args: argparse.Namespace) -> List[Dict[str, Any]]:
    system = "You are a helpful assistant for video understanding. Follow the user's instruction exactly."
    if args.media_mode == "frames":
        frames = sample_video_frames(video_path, max_frames=args.max_frames, fps=args.fps, max_long_side=args.max_video_long_side)
        user_content = build_multimodal_user_content(case.instruction, frames)
    else:
        user_content = [
            {"type": "text", "text": case.instruction},
            {"type": "video_url", "video_url": {"url": video_path.resolve().as_uri()}},
        ]
    return [{"role": "system", "content": system}, {"role": "user", "content": user_content}]


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    records = load_annotation_records(args.dataset_root, args.repo_id)
    cases = list(iter_instruction_cases(records, instruction_types=args.instruction_types, max_cases=args.max_cases))
    client = OpenAICompatibleClient(
        api_base=args.api_base,
        api_key=args.api_key,
        api_key_env=args.api_key_env,
        model=args.model,
        timeout=args.timeout_sec,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
    )
    for case in tqdm(cases, desc="Video-IFBench run"):
        out_path = out_dir / case.response_filename
        if args.resume and out_path.exists():
            continue
        started = time.time()
        try:
            video_path = resolve_video_path(case, dataset_root=args.dataset_root, repo_id=args.repo_id)
            messages = build_messages(case, video_path, args)
            response_text = client.chat(messages)
            payload: Dict[str, Any] = {
                "case_id": case.case_id,
                "response_text": response_text,
                "_meta": {
                    **case.to_meta(str(video_path)),
                    "runner": {
                        "model": args.model,
                        "api_base": args.api_base,
                        "media_mode": args.media_mode,
                        "max_frames": args.max_frames if args.media_mode == "frames" else None,
                        "fps": args.fps,
                        "max_video_long_side": args.max_video_long_side,
                        "elapsed_sec": round(time.time() - started, 3),
                    },
                },
            }
        except Exception as exc:
            payload = {
                "case_id": case.case_id,
                "response_text": "",
                "_meta": case.to_meta(),
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
