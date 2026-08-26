from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

from . import DEFAULT_REPO_ID


@dataclass(frozen=True)
class InstructionCase:
    case_id: str
    video_id: str
    video_path: str
    instruction_id: str
    instruction_key: str
    instruction_type: str
    instruction: str
    active_instruction: str
    constraints: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    language: str = ""
    duration_sec: Optional[float] = None

    @property
    def response_filename(self) -> str:
        safe_video = _safe_name(self.video_id)
        safe_key = _safe_name(self.instruction_key or self.instruction_type)
        return f"{safe_video}__{safe_key}.response.json"

    def to_meta(self, resolved_video_path: Optional[str] = None) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "video_id": self.video_id,
            "video_path": resolved_video_path or self.video_path,
            "dataset_video_path": self.video_path,
            "duration_sec": self.duration_sec,
            "instruction_id": self.instruction_id,
            "instruction_key": self.instruction_key,
            "instruction_type": self.instruction_type,
            "instruction": self.instruction,
            "active_instruction": self.active_instruction,
            "constraints": self.constraints,
            "tasks": self.tasks,
            "language": self.language,
        }


def _safe_name(value: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_") or "item"


def _annotation_path(dataset_root: Optional[Path], repo_id: str) -> Path:
    if dataset_root is not None:
        return Path(dataset_root).expanduser() / "annotations" / "annotations.jsonl"
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError("Install huggingface_hub or pass --dataset-root.") from exc
    return Path(hf_hub_download(repo_id=repo_id, repo_type="dataset", filename="annotations/annotations.jsonl"))


def load_annotation_records(dataset_root: Optional[str | Path] = None, repo_id: str = DEFAULT_REPO_ID) -> List[Dict[str, Any]]:
    root = Path(dataset_root).expanduser() if dataset_root else None
    path = _annotation_path(root, repo_id)
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def iter_instruction_cases(
    records: Sequence[Dict[str, Any]],
    *,
    instruction_types: Optional[Iterable[str]] = None,
    max_cases: Optional[int] = None,
) -> Iterator[InstructionCase]:
    allowed = {x.strip().lower() for x in instruction_types or [] if x.strip()}
    count = 0
    for record in records:
        for item in record.get("instructions", []) or []:
            inst_type = str(item.get("instruction_type") or item.get("instruction_key") or "").lower()
            if allowed and inst_type not in allowed:
                continue
            case = InstructionCase(
                case_id=str(item.get("instruction_id") or f"{record.get('video_id')}/{item.get('instruction_key')}") ,
                video_id=str(record.get("video_id") or ""),
                video_path=str(record.get("video_path") or ""),
                duration_sec=record.get("duration_sec"),
                instruction_id=str(item.get("instruction_id") or ""),
                instruction_key=str(item.get("instruction_key") or ""),
                instruction_type=inst_type,
                instruction=str(item.get("instruction") or ""),
                active_instruction=str(item.get("active_instruction") or item.get("instruction") or ""),
                constraints=list(item.get("constraints") or []),
                tasks=list(item.get("tasks") or []),
                language=str(item.get("language") or ""),
            )
            yield case
            count += 1
            if max_cases is not None and count >= max_cases:
                return


def resolve_video_path(case: InstructionCase, *, dataset_root: Optional[str | Path] = None, repo_id: str = DEFAULT_REPO_ID) -> Path:
    if dataset_root is not None:
        return Path(dataset_root).expanduser() / case.video_path
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError("Install huggingface_hub or pass --dataset-root.") from exc
    return Path(hf_hub_download(repo_id=repo_id, repo_type="dataset", filename=case.video_path))
