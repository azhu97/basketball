"""Verify homography math on synthetic data -- no video or GUI needed.

The interactive clicking in src/calib/homography.py can't be tested here (it
needs a real display and a human), but the math it depends on can be: given a
known pixel<->court mapping, compute_homography should recover it, and
project_point/project_points should reproduce the known correspondences.
"""

import numpy as np
import pytest

from src.calib.court import COURT_KEYPOINTS
from src.calib.homography import compute_homography, project_point, project_points


def synthetic_pixel_points(court_points: np.ndarray, H_true_inv: np.ndarray) -> np.ndarray:
    """Map known court points backward through a made-up homography to get
    plausible 'pixel' coordinates, as if a camera had produced them."""
    return project_points(H_true_inv, court_points)


@pytest.fixture
def sample_court_points():
    names = [
        "baseline0_sideline0",
        "baseline0_sideline50",
        "ft_line0_edge0",
        "ft_line0_edge50",
        "halfcourt_sideline0",
    ]
    return np.array([COURT_KEYPOINTS[n] for n in names])


def test_compute_homography_recovers_known_mapping(sample_court_points):
    # An arbitrary but well-conditioned court -> pixel homography to fake a
    # camera's perspective (translate, scale, and a bit of perspective skew).
    H_court_to_pixel = np.array(
        [
            [8.0, 1.5, 50.0],
            [0.5, 6.0, 20.0],
            [0.001, 0.002, 1.0],
        ]
    )
    pixel_points = synthetic_pixel_points(sample_court_points, H_court_to_pixel)

    H_recovered = compute_homography(
        list(map(tuple, pixel_points)), list(map(tuple, sample_court_points))
    )

    reprojected = project_points(H_recovered, pixel_points)
    assert np.allclose(reprojected, sample_court_points, atol=1e-6)


def test_project_point_matches_project_points(sample_court_points):
    H_court_to_pixel = np.array(
        [
            [8.0, 1.5, 50.0],
            [0.5, 6.0, 20.0],
            [0.001, 0.002, 1.0],
        ]
    )
    pixel_points = synthetic_pixel_points(sample_court_points, H_court_to_pixel)
    H_recovered = compute_homography(
        list(map(tuple, pixel_points)), list(map(tuple, sample_court_points))
    )

    for px, py in pixel_points:
        single = project_point(H_recovered, px, py)
        batch = project_points(H_recovered, np.array([[px, py]]))[0]
        assert np.allclose(single, batch, atol=1e-9)


def test_compute_homography_rejects_too_few_points():
    with pytest.raises(ValueError):
        compute_homography([(0, 0), (1, 1), (2, 2)], [(0, 0), (1, 1), (2, 2)])
