"""Propagate one anchor calibration across a segment via optical flow.

Once one frame in a segment is calibrated (an anchor homography, from
homography.py), we don't need to re-click every subsequent frame: track
distinctive background points frame-to-frame with Lucas-Kanade optical flow,
estimate the incremental camera transform from those correspondences, and
compose it with the anchor's homography. This is the standard video-
stabilization technique (frame-to-frame homography accumulation), not a novel
algorithm -- plan.md named it explicitly for this situation.

v0 limitation: without Phase 3's player detection yet, tracked feature points
aren't masked away from players. RANSAC in the transform estimation absorbs
most of that (background points vastly outnumber the ~10 small player regions
in a wide shot), but it isn't perfect -- revisit once player masks exist.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

LK_PARAMS = dict(
    winSize=(21, 21),
    maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
)
FEATURE_PARAMS = dict(maxCorners=200, qualityLevel=0.01, minDistance=10, blockSize=7)
MIN_TRACKED_POINTS = 30  # below this, propagation is considered lost -- re-anchor


@dataclass
class PropagationResult:
    homographies: list[np.ndarray]  # pixel -> court, one per successfully propagated frame
    broke_down_at: int | None  # index into the input frame list where tracking was lost


def _to_gray(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def propagate_homography(anchor_homography: np.ndarray, frames: list[np.ndarray]) -> PropagationResult:
    """frames[0] must be the already-calibrated anchor frame. Returns one
    homography per frame that was successfully propagated; if tracking is
    lost partway through, homographies stops there and broke_down_at records
    where, so the caller knows to re-anchor from that frame.
    """
    if not frames:
        return PropagationResult(homographies=[], broke_down_at=None)

    prev_gray = _to_gray(frames[0])
    points = cv2.goodFeaturesToTrack(prev_gray, mask=None, **FEATURE_PARAMS)

    homographies = [anchor_homography]
    cumulative = np.eye(3)  # maps pixel(anchor) -> pixel(current frame)
    broke_down_at = None

    for t in range(1, len(frames)):
        if points is None or len(points) < MIN_TRACKED_POINTS:
            broke_down_at = t
            break

        gray = _to_gray(frames[t])
        next_points, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, gray, points, None, **LK_PARAMS)
        status = status.reshape(-1).astype(bool)
        prev_matched = points[status]
        next_matched = next_points[status]

        if len(prev_matched) < MIN_TRACKED_POINTS:
            broke_down_at = t
            break

        step_transform, inlier_mask = cv2.findHomography(prev_matched, next_matched, cv2.RANSAC, 3.0)
        if step_transform is None:
            broke_down_at = t
            break

        cumulative = step_transform @ cumulative
        homographies.append(anchor_homography @ np.linalg.inv(cumulative))

        inlier_mask = inlier_mask.reshape(-1).astype(bool)
        points = next_matched[inlier_mask].reshape(-1, 1, 2).astype(np.float32)
        prev_gray = gray

        if len(points) < MIN_TRACKED_POINTS * 2:
            fresh = cv2.goodFeaturesToTrack(prev_gray, mask=None, **FEATURE_PARAMS)
            if fresh is not None:
                points = np.vstack([points, fresh])

    return PropagationResult(homographies=homographies, broke_down_at=broke_down_at)
