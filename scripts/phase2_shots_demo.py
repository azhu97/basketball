"""Phase 2 prerequisite check: segment a broadcast clip into continuous shots.

Usage:
    python scripts/phase2_shots_demo.py <video> [--threshold 0.4] [--max-frames N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.calib.shots import segment_video


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("--threshold", type=float, default=0.4)
    args = parser.parse_args()

    segments = segment_video(args.video, threshold=args.threshold)
    print(f"{len(segments)} segments detected")
    for seg in segments:
        print(f"  frames [{seg.start_frame:6d}, {seg.end_frame:6d})  ({seg.n_frames} frames)")


if __name__ == "__main__":
    main()
