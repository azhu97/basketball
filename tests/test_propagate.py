"""Verify optical-flow propagation on a synthetic sequence with known camera
motion -- no real video needed. We build frames by translating a textured
image by known amounts, so the correct answer is known exactly, and check
that propagate_homography's output matches it.
"""

import cv2
import numpy as np

from src.calib.homography import compute_homography, project_point
from src.calib.propagate import propagate_homography


def _make_textured_frame(size=(360, 640)) -> np.ndarray:
    """Speckle pattern so goodFeaturesToTrack has real corners to find."""
    rng = np.random.default_rng(0)
    frame = rng.integers(0, 255, size=(*size, 3), dtype=np.uint8)
    frame = cv2.GaussianBlur(frame, (5, 5), 0)
    return frame


def _translate(frame: np.ndarray, dx: float, dy: float) -> np.ndarray:
    M = np.array([[1, 0, dx], [0, 1, dy]], dtype=np.float32)
    return cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))


def test_propagation_tracks_known_pure_translation():
    base = _make_textured_frame()
    shifts = [(0, 0), (3, 2), (6, 4), (9, 6), (12, 8)]  # cumulative pixel shifts
    frames = [_translate(base, dx, dy) for dx, dy in shifts]

    # Anchor homography: arbitrary well-conditioned pixel->court mapping.
    anchor_pixels = [(100, 100), (500, 100), (100, 300), (500, 300)]
    anchor_court = [(0, 0), (94, 0), (0, 50), (94, 50)]
    H_anchor = compute_homography(anchor_pixels, anchor_court)

    result = propagate_homography(H_anchor, frames)

    assert result.broke_down_at is None
    assert len(result.homographies) == len(frames)

    # A point that is stationary on the *court* moves in *pixel* space by
    # exactly -shift (since the camera/content translated by `shift`).
    # Check the anchor's own reference point still projects to the same
    # court location once we account for the known shift.
    ref_pixel = anchor_pixels[0]
    ref_court = project_point(H_anchor, *ref_pixel)

    for (dx, dy), H_t in zip(shifts, result.homographies):
        shifted_pixel = (ref_pixel[0] + dx, ref_pixel[1] + dy)
        projected = project_point(H_t, *shifted_pixel)
        assert np.allclose(projected, ref_court, atol=0.5), (dx, dy, projected, ref_court)


def test_propagation_reports_breakdown_on_blank_frames():
    # Blank frames have no trackable corners at all -- should report a
    # breakdown rather than silently producing garbage homographies.
    blank = np.zeros((360, 640, 3), dtype=np.uint8)
    frames = [blank.copy() for _ in range(5)]

    H_anchor = compute_homography(
        [(100, 100), (500, 100), (100, 300), (500, 300)],
        [(0, 0), (94, 0), (0, 50), (94, 50)],
    )
    result = propagate_homography(H_anchor, frames)
    assert result.broke_down_at is not None
