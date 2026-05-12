from pathlib import Path
from types import SimpleNamespace

from video_ifbench.run import build_messages, load_asr_text, resolve_subtitle_path


def test_load_asr_text_keeps_timestamps_and_drops_srt_indices(tmp_path):
    srt = tmp_path / "sample.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:02,500\nhello there\n\n2\n00:00:03,000 --> 00:00:04,000\nnext line\n",
        encoding="utf-8",
    )

    assert load_asr_text(srt) == "00:00:01,000 --> 00:00:02,500\nhello there\n00:00:03,000 --> 00:00:04,000\nnext line"


def test_resolve_subtitle_path_uses_dataset_subtitles_layout(tmp_path):
    dataset_root = tmp_path / "dataset"
    subtitle = dataset_root / "subtitles" / "general_education_science" / "youtube__abc.srt"
    subtitle.parent.mkdir(parents=True)
    subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\ntext\n", encoding="utf-8")
    case = SimpleNamespace(video_path="videos/general_education_science/youtube__abc.mp4")
    args = SimpleNamespace(dataset_root=str(dataset_root), subtitle_dir=None)

    assert resolve_subtitle_path(case, Path("/tmp/youtube__abc.mp4"), args) == subtitle


def test_build_messages_places_asr_between_video_and_instruction(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"")
    case = SimpleNamespace(instruction="Answer the question.")
    args = SimpleNamespace(media_mode="video-url", max_frames=None, fps=1.0, max_video_long_side=720)

    messages = build_messages(case, video, args, asr_text="00:00:00,000 --> 00:00:01,000\nhello")
    content = messages[1]["content"]

    assert content[0]["type"] == "video_url"
    assert content[1] == {"type": "text", "text": "ASR transcript:\n00:00:00,000 --> 00:00:01,000\nhello"}
    assert content[2] == {"type": "text", "text": "Answer the question."}
