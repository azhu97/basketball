"""Video reading and frame caching."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np


@dataclass
class VideoInfo:
    path: Path
    width: int
    height: int
    fps: float
    frame_count: int


class VideoReader:
    """Sequential frame access over a video file via cv2.VideoCapture."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._cap = cv2.VideoCapture(str(self.path))
        if not self._cap.isOpened():
            raise IOError(f"Could not open video: {self.path}")
        self.info = VideoInfo(
            path=self.path,
            width=int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=self._cap.get(cv2.CAP_PROP_FPS),
            frame_count=int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        )

    def frames(self) -> Iterator[tuple[int, np.ndarray]]:
        """Yield (frame_index, frame) for every frame, in order."""
        idx = 0
        while True:
            ok, frame = self._cap.read()
            if not ok:
                break
            yield idx, frame
            idx += 1

    def close(self) -> None:
        self._cap.release()

    def __enter__(self) -> "VideoReader":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def extract_frames(path: str | Path, out_dir: str | Path, every_n: int = 1) -> int:
    """Cache frames to disk as JPEGs for fast random access later, instead of
    re-decoding the video from the start each time. Returns frames written."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    with VideoReader(path) as reader:
        for idx, frame in reader.frames():
            if idx % every_n != 0:
                continue
            cv2.imwrite(str(out_dir / f"frame_{idx:06d}.jpg"), frame)
            written += 1
    return written
