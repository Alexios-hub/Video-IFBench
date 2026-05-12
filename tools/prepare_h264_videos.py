from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from tqdm import tqdm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Move videos to videos_bak and rebuild videos with AV1 files transcoded to H.264 MP4.")
    parser.add_argument("--dataset-root", default="data/Video-IFBench")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--crf", type=int, default=23)
    parser.add_argument("--preset", default="veryfast")
    return parser.parse_args()


def run(cmd: Iterable[str]) -> str:
    return subprocess.check_output(list(cmd), text=True, stderr=subprocess.STDOUT).strip()


def codec_name(path: Path) -> str:
    return run([
        "ffprobe",
        "-hide_banner",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "default=nw=1:nk=1",
        str(path),
    ])


def rel_dest_for(src_rel: Path, codec: str, codec_by_rel: Dict[Path, str]) -> Optional[Path]:
    if codec != "av1":
        return src_rel
    mp4_rel = src_rel.with_suffix(".mp4")
    mp4_codec = codec_by_rel.get(mp4_rel)
    if mp4_codec and mp4_codec != "av1":
        return None
    return mp4_rel


def ensure_link(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)


def transcode_h264(src: Path, dest: Path, *, crf: int, preset: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.stem + ".tmp" + dest.suffix)
    if tmp.exists():
        tmp.unlink()
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
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-map",
        "0:a?",
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


def update_annotations(annotation_path: Path, path_map: Dict[str, str]) -> None:
    backup = annotation_path.with_suffix(annotation_path.suffix + ".bak_before_h264")
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
            old = str(record.get("video_path") or "")
            new = path_map.get(old, old)
            if new != old:
                record["video_path"] = new
                changed += 1
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
    tmp.replace(annotation_path)
    print(f"annotations updated: {changed}/{total} records changed")
    print(f"annotation backup: {backup}")


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be >= 1")

    dataset_root = Path(args.dataset_root)
    videos = dataset_root / "videos"
    videos_bak = dataset_root / "videos_bak"
    annotations = dataset_root / "annotations" / "annotations.jsonl"

    if not annotations.exists():
        raise FileNotFoundError(annotations)
    if not videos_bak.exists():
        if not videos.exists():
            raise FileNotFoundError(videos)
        videos.rename(videos_bak)
        print(f"moved {videos} -> {videos_bak}")
    else:
        print(f"using existing backup: {videos_bak}")

    videos.mkdir(parents=True, exist_ok=True)

    files = [p for p in sorted(videos_bak.rglob("*")) if p.is_file()]
    plan: list[Tuple[Path, Path, str]] = []
    path_map: Dict[str, str] = {}
    collisions: Dict[Path, Path] = {}

    codec_by_rel = {src.relative_to(videos_bak): codec_name(src) for src in tqdm(files, desc="ffprobe")}

    for src in files:
        rel = src.relative_to(videos_bak)
        codec = codec_by_rel[rel]
        dest_rel = rel_dest_for(rel, codec, codec_by_rel)
        if dest_rel is None:
            replacement = rel.with_suffix(".mp4")
            path_map[str(Path("videos") / rel)] = str(Path("videos") / replacement)
            continue
        prior = collisions.get(dest_rel)
        if prior is not None and prior != rel:
            raise RuntimeError(f"Destination collision: {prior} and {rel} both map to {dest_rel}")
        collisions[dest_rel] = rel
        plan.append((src, videos / dest_rel, codec))
        old_ann_path = str(Path("videos") / rel)
        new_ann_path = str(Path("videos") / dest_rel)
        if new_ann_path != old_ann_path:
            path_map[old_ann_path] = new_ann_path

    passthrough = [(src, dest) for src, dest, codec in plan if codec != "av1"]
    transcodes = [(src, dest) for src, dest, codec in plan if codec == "av1"]
    print(f"files: {len(plan)} passthrough: {len(passthrough)} av1_transcode: {len(transcodes)}")

    for src, dest in tqdm(passthrough, desc="link/copy passthrough"):
        ensure_link(src, dest)

    def one_transcode(item: Tuple[Path, Path]) -> Tuple[str, str]:
        src, dest = item
        if dest.exists():
            return (str(src), "exists")
        transcode_h264(src, dest, crf=args.crf, preset=args.preset)
        return (str(src), "transcoded")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(one_transcode, item) for item in transcodes]
        for future in tqdm(as_completed(futures), total=len(futures), desc="transcode av1"):
            future.result()

    update_annotations(annotations, path_map)
    print(f"rebuilt videos directory: {videos}")


if __name__ == "__main__":
    main()
