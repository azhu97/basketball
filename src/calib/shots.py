"""Shot/cut detection: split a video into continuous-camera segments.

Broadcast footage cuts between live game action, replays, close-ups, and
graphics. A per-frame camera calibration (Phase 2) only makes sense within one
continuous shot, so this has to run before any calibration work.

Approach: compare each frame's color histogram to the previous frame's. Within
a shot the distribution drifts gradually even with fast player motion; at a
hard cut it jumps sharply. No ML, no training data needed.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..io.video import VideoReader


@dataclass
class Segment:
    start_frame: int
    end_frame: int  # exclusive

    @property
    def n_frames(self) -> int:
        return self.end_frame - self.start_frame


def _frame_histogram(frame: np.ndarray) -> np.ndarray:
    """Normalized HSV histogram (hue + saturation channels)."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    return hist


def _histogram_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Bhattacharyya distance: 0 = identical, 1 = completely different."""
    return cv2.compareHist(a, b, cv2.HISTCMP_BHATTACHARYYA)


def detect_cuts(video_path: str, threshold: float = 0.4) -> list[int]:
    """Return frame indices where a hard cut starts (i.e. the first frame of
    a new shot). threshold is a Bhattacharyya distance cutoff — tune against
    real footage rather than trusting the default blindly."""
    cuts: list[int] = []
    prev_hist = None
    with VideoReader(video_path) as reader:
        for idx, frame in reader.frames():
            hist = _frame_histogram(frame)
            if prev_hist is not None:
                dist = _histogram_distance(prev_hist, hist)
                if dist > threshold:
                    cuts.append(idx)
            prev_hist = hist
    return cuts


def segment_video(video_path: str, threshold: float = 0.4, min_segment_len: int = 10) -> list[Segment]:
    """Split a video into continuous-camera segments at detected cuts,
    dropping segments shorter than min_segment_len frames (likely flash
    transitions or detection noise rather than real shots)."""
    with VideoReader(video_path) as reader:
        total_frames = reader.info.frame_count

    cuts = detect_cuts(video_path, threshold=threshold)
    boundaries = [0, *cuts, total_frames]

    segments = []
    for start, end in zip(boundaries, boundaries[1:]):
        if end - start >= min_segment_len:
            segments.append(Segment(start_frame=start, end_frame=end))
    return segments
