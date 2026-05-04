from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import List

from PIL import Image


def _resize_image(image: Image.Image, max_long_side: int) -> Image.Image:
    if max_long_side <= 0:
        return image.convert("RGB")
    w, h = image.size
    long_side = max(w, h)
    if long_side <= max_long_side:
        return image.convert("RGB")
    scale = max_long_side / float(long_side)
    return image.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS).convert("RGB")


def image_to_data_url(image: Image.Image, *, max_long_side: int = 720, quality: int = 85) -> str:
    image = _resize_image(image, max_long_side)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def sample_video_frames(video_path: str | Path, *, max_frames: int = 32, fps: float | None = None, max_long_side: int = 720) -> List[str]:
    """Return sampled video frames as JPEG data URLs."""
    import cv2

    path = str(video_path)
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    native_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if total <= 0:
        indices = list(range(max_frames))
    elif fps and native_fps > 0:
        step = max(1, int(round(native_fps / fps)))
        indices = list(range(0, total, step))[:max_frames]
    else:
        if max_frames <= 0:
            max_frames = 1
        if total <= max_frames:
            indices = list(range(total))
        else:
            indices = [round(i * (total - 1) / (max_frames - 1)) for i in range(max_frames)]
    frames: List[str] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if not ok:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        frames.append(image_to_data_url(image, max_long_side=max_long_side))
    cap.release()
    if not frames:
        raise RuntimeError(f"No frames sampled from video: {path}")
    return frames


def build_multimodal_user_content(instruction: str, frame_data_urls: List[str]) -> list:
    content = [{"type": "text", "text": instruction}]
    for url in frame_data_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    return content
