"""Overlay writer: read a clip, draw on it, write it back out.

This is Phase 1's smoke test for the read -> process -> write loop that every
later visualization (boxes, IDs, court lines) reuses.
"""

from __future__ import annotations

from pathlib import Path

import cv2

from .video import VideoReader


def write_frame_number_overlay(
    input_path: str | Path,
    output_path: str | Path,
    max_frames: int | None = None,
) -> int:
    """Burn the frame index into the top-left corner of every frame.

    max_frames limits how many frames are processed (useful for quick
    previews on long files); None processes the whole clip. Returns the
    number of frames written.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with VideoReader(input_path) as reader:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(output_path),
            fourcc,
            reader.info.fps,
            (reader.info.width, reader.info.height),
        )
        if not writer.isOpened():
            raise IOError(f"Could not open video writer for: {output_path}")
        written = 0
        try:
            for idx, frame in reader.frames():
                if max_frames is not None and idx >= max_frames:
                    break
                cv2.putText(
                    frame,
                    f"frame {idx}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
                writer.write(frame)
                written += 1
        finally:
            writer.release()
    return written
