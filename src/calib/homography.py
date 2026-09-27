"""Pixel <-> court-feet homography: computing it, applying it, and an
interactive tool for clicking anchor points on a real frame.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from .court import COURT_KEYPOINTS, court_line_segments


def compute_homography(
    pixel_points: list[tuple[float, float]],
    court_points: list[tuple[float, float]],
) -> np.ndarray:
    """Compute the homography mapping pixel coordinates to court-feet
    coordinates from >=4 point correspondences."""
    if len(pixel_points) < 4 or len(pixel_points) != len(court_points):
        raise ValueError("Need >=4 pixel/court point pairs of equal length")
    src = np.array(pixel_points, dtype=np.float64)
    dst = np.array(court_points, dtype=np.float64)
    H, _ = cv2.findHomography(src, dst, method=0)
    if H is None:
        raise ValueError("Homography computation failed (degenerate points?)")
    return H


def project_point(H: np.ndarray, x: float, y: float) -> tuple[float, float]:
    """Map one pixel point through a homography to court-feet."""
    p = H @ np.array([x, y, 1.0])
    return (p[0] / p[2], p[1] / p[2])


def project_points(H: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Vectorized version of project_point. points: Nx2 array."""
    n = points.shape[0]
    homog = np.hstack([points, np.ones((n, 1))])
    projected = homog @ H.T
    return projected[:, :2] / projected[:, 2:3]


def save_homography(H: np.ndarray, path: str | Path) -> None:
    Path(path).write_text(json.dumps(H.tolist()))


def load_homography(path: str | Path) -> np.ndarray:
    return np.array(json.loads(Path(path).read_text()))


def click_points(frame: np.ndarray, labels: list[str]) -> list[tuple[float, float]]:
    """Open an interactive window and have the user click one pixel point per
    label, in order. Must be run somewhere with a display -- not usable
    headlessly. Left-click to place a point; the window closes automatically
    after the last label is placed.
    """
    clicked: list[tuple[float, float]] = []
    display = frame.copy()
    window = "Click court points (see terminal for which point is next)"

    def on_click(event, x, y, flags, userdata):
        if event == cv2.EVENT_LBUTTONDOWN and len(clicked) < len(labels):
            clicked.append((float(x), float(y)))
            cv2.circle(display, (x, y), 4, (0, 0, 255), -1)
            cv2.putText(
                display, labels[len(clicked) - 1], (x + 6, y - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA,
            )
            cv2.imshow(window, display)

    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_click)
    cv2.imshow(window, display)

    for label in labels:
        print(f"Click: {label}")

    while len(clicked) < len(labels):
        if cv2.waitKey(20) & 0xFF == 27:  # Esc aborts
            raise KeyboardInterrupt("Calibration aborted by user")

    cv2.waitKey(300)
    cv2.destroyWindow(window)
    return clicked


def render_verification_overlay(frame: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Project the standard court lines through the inverse homography and
    draw them on the frame, so alignment can be checked visually."""
    H_inv = np.linalg.inv(H)
    overlay = frame.copy()
    for segment in court_line_segments():
        pixel_pts = project_points(H_inv, segment)
        pixel_pts = pixel_pts.astype(np.int32)
        cv2.polylines(overlay, [pixel_pts], isClosed=False, color=(0, 255, 255), thickness=2)
    return overlay
