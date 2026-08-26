from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from tqdm import tqdm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Move videos to videos_mp4_org and rebuild videos as max-720p H.264 MP4 files.")
    parser.add_argument("--dataset-root", default="data/Video-IFBench")
    parser.add_argument("--source-dir-name", default="videos_mp4_org")
    parser.add_argument("--max-long-side", type=int, default=720)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--crf", type=int, default=23)
    parser.add_argument("--preset", default="veryfast")
    return parser.parse_args()


def run(cmd: Iterable[str]) -> str:
    return subprocess.check_output(list(cmd), text=True, stderr=subprocess.STDOUT).strip()


def probe_video(path: Path) -> Dict[str, Any]:
    raw = run([
        "ffprobe",
        "-hide_banner",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height",
        "-of",
        "json",
        str(path),
    ])
    stream = json.loads(raw)["streams"][0]
    return {"codec": stream["codec_name"], "width": int(stream["width"]), "height": int(stream["height"])}


def has_audio(path: Path) -> bool:
    raw = run([
        "ffprobe",
        "-hide_banner",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "default=nw=1:nk=1",
        str(path),
    ])
    return bool(raw.strip())


def ensure_link_or_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)


def transcode(src: Path, dest: Path, *, max_long_side: int, crf: int, preset: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.stem + ".tmp" + dest.suffix)
    if tmp.exists():
        tmp.unlink()
    scale = f"scale=w='min({max_long_side},iw)':h='min({max_long_side},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(src),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        scale,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(tmp),
    ]
    subprocess.check_call(cmd)
    tmp.replace(dest)


def annotation_paths(annotation_path: Path) -> list[str]:
    paths: list[str] = []
    with annotation_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                paths.append(str(json.loads(line)["video_path"]))
    return paths


def update_annotations(annotation_path: Path, path_map: Dict[str, str]) -> None:
    backup = annotation_path.with_suffix(annotation_path.suffix + ".bak_before_resize720")
    if not backup.exists():
        shutil.copy2(annotation_path, backup)
    tmp = annotation_path.with_suffix(annotation_path.suffix + ".tmp")
    changed = 0
    total = 0
    with annotation_path.open("r", encoding="utf-8") as src, tmp.open("w", encoding="utf-8") as out:
        for line in src:
            if not line.strip():
                continue
            total += 1
            record = json.loads(line)
            old_path = str(record["video_path"])
            new_path = path_map.get(old_path, old_path)
            if new_path != old_path:
                record["video_path"] = new_path
                changed += 1
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
    tmp.replace(annotation_path)
    print(f"annotations updated: {changed}/{total}")
    print(f"annotation backup: {backup}")


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be >= 1")

    dataset_root = Path(args.dataset_root)
    videos = dataset_root / "videos"
    source = dataset_root / args.source_dir_name
    annotations = dataset_root / "annotations" / "annotations.jsonl"

    if not annotations.exists():
        raise FileNotFoundError(annotations)
    if not source.exists():
        if not videos.exists():
            raise FileNotFoundError(videos)
        videos.rename(source)
        print(f"moved {videos} -> {source}")
    else:
        print(f"using existing source: {source}")
    videos.mkdir(parents=True, exist_ok=True)

    original_paths = annotation_paths(annotations)
    path_map = {path: str(Path(path).with_suffix(".mp4")) for path in original_paths}
    reverse: Dict[str, str] = {}
    for old, new in path_map.items():
        prior = reverse.get(new)
        if prior is not None and prior != old:
            raise RuntimeError(f"Annotation destination collision: {prior} and {old} both map to {new}")
        reverse[new] = old

    jobs: list[Tuple[Path, Path, str]] = []
    for old_path in tqdm(original_paths, desc="probe"):
        src = source / Path(old_path).relative_to("videos")
        dest = videos / Path(path_map[old_path]).relative_to("videos")
        if not src.exists():
            raise FileNotFoundError(src)
        info = probe_video(src)
        long_side = max(info["width"], info["height"])
        can_link = (
            src.suffix.lower() == ".mp4"
            and dest.suffix.lower() == ".mp4"
            and info["codec"] == "h264"
            and long_side <= args.max_long_side
        )
        jobs.append((src, dest, "link" if can_link else "transcode"))

    link_jobs = [(src, dest) for src, dest, kind in jobs if kind == "link"]
    transcode_jobs = [(src, dest) for src, dest, kind in jobs if kind == "transcode"]
    print(f"annotation videos: {len(jobs)} link/copy: {len(link_jobs)} transcode: {len(transcode_jobs)}")

    for src, dest in tqdm(link_jobs, desc="link/copy"):
        ensure_link_or_copy(src, dest)

    def one(item: Tuple[Path, Path]) -> str:
        src, dest = item
        if not dest.exists():
            transcode(src, dest, max_long_side=args.max_long_side, crf=args.crf, preset=args.preset)
        return str(dest)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(one, item) for item in transcode_jobs]
        for future in tqdm(as_completed(futures), total=len(futures), desc="transcode"):
            future.result()

    update_annotations(annotations, path_map)
    print(f"rebuilt videos directory: {videos}")


if __name__ == "__main__":
    main()
