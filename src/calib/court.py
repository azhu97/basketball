"""Standard NCAA court dimensions and known landmark points.

Coordinate system: x runs the 94 ft length of the court, y runs the 50 ft
width. Origin (0, 0) is one baseline/sideline corner.
"""

from __future__ import annotations

import numpy as np

COURT_LENGTH_FT = 94.0
COURT_WIDTH_FT = 50.0
LANE_WIDTH_FT = 12.0
FT_LINE_FROM_BASELINE_FT = 19.0
CENTER_CIRCLE_RADIUS_FT = 6.0

_LANE_Y_NEAR = (COURT_WIDTH_FT - LANE_WIDTH_FT) / 2  # 19.0
_LANE_Y_FAR = (COURT_WIDTH_FT + LANE_WIDTH_FT) / 2  # 31.0

# Named landmark points a person can click on, in (x_ft, y_ft). Pick whichever
# subset is visible in a given anchor frame -- doesn't need to be the same set
# every time.
COURT_KEYPOINTS: dict[str, tuple[float, float]] = {
    "baseline0_sideline0": (0.0, 0.0),
    "baseline0_sideline50": (0.0, COURT_WIDTH_FT),
    "baseline94_sideline0": (COURT_LENGTH_FT, 0.0),
    "baseline94_sideline50": (COURT_LENGTH_FT, COURT_WIDTH_FT),
    "halfcourt_sideline0": (COURT_LENGTH_FT / 2, 0.0),
    "halfcourt_sideline50": (COURT_LENGTH_FT / 2, COURT_WIDTH_FT),
    "ft_line0_edge0": (FT_LINE_FROM_BASELINE_FT, _LANE_Y_NEAR),
    "ft_line0_edge50": (FT_LINE_FROM_BASELINE_FT, _LANE_Y_FAR),
    "ft_line94_edge0": (COURT_LENGTH_FT - FT_LINE_FROM_BASELINE_FT, _LANE_Y_NEAR),
    "ft_line94_edge50": (COURT_LENGTH_FT - FT_LINE_FROM_BASELINE_FT, _LANE_Y_FAR),
    "ft_circle0_center": (FT_LINE_FROM_BASELINE_FT, COURT_WIDTH_FT / 2),
    "ft_circle94_center": (COURT_LENGTH_FT - FT_LINE_FROM_BASELINE_FT, COURT_WIDTH_FT / 2),
    "center_circle_center": (COURT_LENGTH_FT / 2, COURT_WIDTH_FT / 2),
}


def court_line_segments() -> list[np.ndarray]:
    """Polylines (each an Nx2 array of court-space points, in feet) for the
    standard court markings, for rendering a verification overlay."""
    y0, y1 = _LANE_Y_NEAR, _LANE_Y_FAR
    L, W = COURT_LENGTH_FT, COURT_WIDTH_FT
    ft0 = FT_LINE_FROM_BASELINE_FT
    ft94 = L - FT_LINE_FROM_BASELINE_FT

    segments = [
        np.array([[0, 0], [L, 0]]),  # sideline y=0
        np.array([[0, W], [L, W]]),  # sideline y=W
        np.array([[0, 0], [0, W]]),  # baseline x=0
        np.array([[L, 0], [L, W]]),  # baseline x=L
        np.array([[L / 2, 0], [L / 2, W]]),  # half-court line
        np.array([[0, y0], [ft0, y0], [ft0, y1], [0, y1]]),  # lane near x=0
        np.array([[L, y0], [ft94, y0], [ft94, y1], [L, y1]]),  # lane near x=L
    ]

    theta = np.linspace(0, 2 * np.pi, 40)
    for cx, cy in [(L / 2, W / 2)]:
        circle = np.stack(
            [cx + CENTER_CIRCLE_RADIUS_FT * np.cos(theta), cy + CENTER_CIRCLE_RADIUS_FT * np.sin(theta)],
            axis=1,
        )
        segments.append(circle)

    return segments
