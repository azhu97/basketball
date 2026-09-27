"""Phase 1 exit-criteria script: read a clip, write it back with frame
numbers overlaid.

Usage:
    python scripts/phase1_overlay_demo.py <input_video> <output_video> [--max-frames N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.io.overlay import write_frame_number_overlay


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to source video")
    parser.add_argument("output", help="Path to write the overlaid video")
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Only process the first N frames (for quick previews)",
    )
    args = parser.parse_args()

    written = write_frame_number_overlay(args.input, args.output, max_frames=args.max_frames)
    print(f"Wrote {written} frames to {args.output}")


if __name__ == "__main__":
    main()
