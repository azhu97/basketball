"""Interactively calibrate one anchor frame of a broadcast segment.

Must be run on a machine with a display -- it opens a window for you to
click court landmarks on. Pick whichever named keypoints (see
src/calib/court.py COURT_KEYPOINTS) are actually visible in your frame; you
need at least 4, and they shouldn't be collinear.

Usage:
    python scripts/calibrate_segment.py <video> --frame 2000 \
        --points baseline0_sideline0 ft_line0_edge0 ft_line0_edge50 halfcourt_sideline0 \
        --out data/cache/anchor_2000.json

Outputs:
    <out>              the homography, as JSON (pixel -> court feet)
    <out>.overlay.jpg  the anchor frame with projected court lines drawn on
                       it, for visually checking the calibration
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from src.calib.court import COURT_KEYPOINTS
from src.calib.homography import click_points, compute_homography, render_verification_overlay, save_homography
from src.io.video import read_frame_at


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video")
    parser.add_argument("--frame", type=int, required=True, help="Frame index to use as the anchor")
    parser.add_argument("--points", nargs="+", required=True, help="Names from COURT_KEYPOINTS, in click order")
    parser.add_argument("--out", required=True, help="Output path for the homography JSON")
    args = parser.parse_args()

    unknown = [p for p in args.points if p not in COURT_KEYPOINTS]
    if unknown:
        raise SystemExit(f"Unknown keypoint name(s): {unknown}. See COURT_KEYPOINTS in src/calib/court.py")
    if len(args.points) < 4:
        raise SystemExit("Need at least 4 points")

    frame = read_frame_at(args.video, args.frame)

    pixel_points = click_points(frame, args.points)
    court_points = [COURT_KEYPOINTS[name] for name in args.points]

    H = compute_homography(pixel_points, court_points)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_homography(H, out_path)

    overlay = render_verification_overlay(frame, H)
    overlay_path = out_path.with_suffix(out_path.suffix + ".overlay.jpg")
    cv2.imwrite(str(overlay_path), overlay)

    print(f"Saved homography to {out_path}")
    print(f"Saved verification overlay to {overlay_path} -- check that the projected lines sit on the real ones")


if __name__ == "__main__":
    main()
