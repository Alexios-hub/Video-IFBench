from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-errors", action="store_true", help="With --resume, rerun existing response files that contain an error field.")
    parser.add_argument("--retry-empty", action="store_true", help="With --resume, rerun existing response files whose response_text is empty.")
    parser.add_argument("--media-mode", choices=["frames", "video-url"], default="video-url")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--fps", type=float, default=1.0)
    parser.add_argument("--max-video-long-side", type=int, default=720)
    parser.add_argument("--subtitle-dir", default=None, help="Directory containing timestamped ASR .srt files. Defaults to DATASET_ROOT/subtitles when --dataset-root is set.")
    parser.add_argument("--use-asr", dest="use_asr", action="store_true", help="Append the paired timestamped ASR transcript to the model input when available.")
    parser.add_argument("--no-asr", dest="use_asr", action="store_false", help="Do not append ASR transcript text.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout-sec", type=float, default=300.0)
    parser.add_argument("--thinking-mode", choices=["disabled", "enabled", "auto"], default="disabled", help="Pass Qwen/vLLM enable_thinking chat-template kwargs for model calls. Default: disabled.")
    parser.add_argument("--enable-thinking", action="store_const", dest="thinking_mode", const="enabled", help="Shortcut for --thinking-mode enabled.")
    parser.add_argument("--disable-thinking", action="store_const", dest="thinking_mode", const="disabled", help="Shortcut for --thinking-mode disabled.")
    parser.set_defaults(use_asr=False)
    return parser.parse_args()


def thinking_chat_template_kwargs(mode: str) -> Optional[Dict[str, bool]]:
    if mode == "auto":
        return None
    if mode == "enabled":
        return {"enable_thinking": True}
    return {"enable_thinking": False}


def default_subtitle_dir(dataset_root: Optional[str]) -> Optional[Path]:
    if not dataset_root:
        return None
    return Path(dataset_root).expanduser() / "subtitles"


def resolve_subtitle_path(case, video_path: Path, args: argparse.Namespace) -> Optional[Path]:
    subtitle_dir = Path(args.subtitle_dir).expanduser() if args.subtitle_dir else default_subtitle_dir(args.dataset_root)
    if subtitle_dir is None:
        return None
    rel = Path(case.video_path)
    if rel.parts and rel.parts[0] == "videos":
        rel = Path(*rel.parts[1:])
    candidates = [
        subtitle_dir / rel.with_suffix(".srt"),
        subtitle_dir / video_path.parent.name / f"{video_path.stem}.srt",
        subtitle_dir / f"{video_path.stem}.srt",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_asr_text(asr_path: Optional[Path]) -> str:
    if asr_path is None or not asr_path.is_file():
        return ""
    lines: List[str] = []
    for raw_line in asr_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.isdigit():
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def build_messages(case, video_path: Path, args: argparse.Namespace, asr_text: str = "") -> List[Dict[str, Any]]:
    system = "You are a helpful assistant for video understanding. Follow the user's instruction exactly."
    asr_text = str(asr_text or "").strip()
    if args.media_mode == "frames":
        frames = sample_video_frames(video_path, max_frames=args.max_frames, fps=args.fps, max_long_side=args.max_video_long_side)
        if asr_text:
            user_content = [{"type": "image_url", "image_url": {"url": url}} for url in frames]
            user_content.append({"type": "text", "text": f"ASR transcript:\n{asr_text}"})
            user_content.append({"type": "text", "text": case.instruction})
        else:
            user_content = build_multimodal_user_content(case.instruction, frames)
    else:
        if asr_text:
            user_content = [
                {"type": "video_url", "video_url": {"url": video_path.resolve().as_uri()}},
                {"type": "text", "text": f"ASR transcript:\n{asr_text}"},
                {"type": "text", "text": case.instruction},
            ]
        else:
            user_content = [
                {"type": "text", "text": case.instruction},
                {"type": "video_url", "video_url": {"url": video_path.resolve().as_uri()}},
            ]
    return [{"role": "system", "content": system}, {"role": "user", "content": user_content}]


def should_skip_existing(out_path: Path, args: argparse.Namespace) -> bool:
    if not args.resume or not out_path.exists():
        return False
    if not args.retry_errors and not args.retry_empty:
        return True
    try:
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if args.retry_errors and payload.get("error"):
        return False
    if args.retry_empty and not str(payload.get("response_text") or "").strip():
        return False
    return True


def run_case(case, args: argparse.Namespace, out_dir: Path, client: OpenAICompatibleClient) -> None:
    out_path = out_dir / case.response_filename
    if should_skip_existing(out_path, args):
        return
    started = time.time()
    try:
        video_path = resolve_video_path(case, dataset_root=args.dataset_root, repo_id=args.repo_id)
        asr_path = resolve_subtitle_path(case, video_path, args) if args.use_asr else None
        asr_text = load_asr_text(asr_path) if args.use_asr else ""
        messages = build_messages(case, video_path, args, asr_text=asr_text)
        response_text = client.chat(messages)
        payload: Dict[str, Any] = {
            "case_id": case.case_id,
            "response_text": response_text,
            "_meta": {
                **case.to_meta(str(video_path)),
                "asr_path": str(asr_path) if asr_path is not None else None,
                "include_asr_input": bool(args.use_asr),
                "asr_text_included": bool(asr_text),
                "runner": {
                    "model": args.model,
                    "api_base": args.api_base,
                    "media_mode": args.media_mode,
                    "max_frames": args.max_frames if args.media_mode == "frames" else None,
                    "fps": args.fps,
                    "max_video_long_side": args.max_video_long_side,
                    "concurrency": args.concurrency,
                    "thinking_mode": args.thinking_mode,
                    "subtitle_dir": args.subtitle_dir or (str(default_subtitle_dir(args.dataset_root)) if default_subtitle_dir(args.dataset_root) is not None else None),
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


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    records = load_annotation_records(args.dataset_root, args.repo_id)
    cases = list(iter_instruction_cases(records, instruction_types=args.instruction_types, max_cases=args.max_cases))
    chat_template_kwargs = thinking_chat_template_kwargs(args.thinking_mode)
    client = OpenAICompatibleClient(
        api_base=args.api_base,
        api_key=args.api_key,
        api_key_env=args.api_key_env,
        model=args.model,
        timeout=args.timeout_sec,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        chat_template_kwargs=chat_template_kwargs,
    )
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(run_case, case, args, out_dir, client) for case in cases]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Video-IFBench run"):
            future.result()


if __name__ == "__main__":
    main()
