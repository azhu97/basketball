# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A pipeline that watches basketball broadcast footage, tracks defenders on the
court over time, detects offensive triggers (passes, drives), and computes a
**latency score**: how long the responsible defender takes to react. The full
phased build plan, with objectives/tasks/exit-criteria per phase, lives in
`plan.md` — read it before starting work in a new phase; it is the source of
truth for scope and sequencing, not this file.

## Commands

```bash
# Environment (Python via venv, no CUDA -- Apple Silicon MPS backend when
# a phase needs GPU inference/training, e.g. later YOLO work)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Tests
.venv/bin/python -m pytest tests/ -v

# Phase 1: read a clip, burn frame numbers on it, write it back out
.venv/bin/python scripts/phase1_overlay_demo.py <input.mp4> <output.mp4> [--max-frames N]

# Phase 2: segment a broadcast clip into continuous-camera shots
.venv/bin/python scripts/phase2_shots_demo.py <video.mp4> [--threshold 0.4]

# Phase 2: interactively calibrate one anchor frame (opens a GUI window --
# must be run on a machine with a display, not headlessly)
.venv/bin/python scripts/calibrate_segment.py <video.mp4> --frame <idx> \
    --points <name1> <name2> <name3> <name4> --out <path.json>
```

## Architecture

**`src/` layout** (per `plan.md` Phase 1): `io/` video read/write, `calib/`
court detection + homography, `detect/` player/ball detection, `track/`
multi-object tracking, `events/` pass/drive detection, `metrics/` role
assignment + latency, `viz/` overlays and court plots. Shared row-level data
structures (`Detection`, `Track`, `CourtPosition`, `Event`) live in
`src/types.py`, not per-module, so every stage speaks the same schema.

**Per-stage data interchange:** Parquet (via pandas) is the decided format for
passing per-frame/per-track data between stages once later phases start
producing it — no stage should invent its own row format.

**Broadcast-first pivot (important, don't undo without reading `plan.md`
Phase 2):** the source footage (`data/uconnVsMichState.mp4`) is a real TV
broadcast camera — it pans and zooms continuously to follow the ball. This was
discovered by inspecting frames seconds apart and seeing the framing change.
The project originally assumed a fixed tactical/all-22 camera (one homography
per clip); that assumption is false for our actual footage, so Phase 2 was
redesigned around it instead of pretending otherwise. Concretely, this means:

- Calibration is **per continuous camera segment**, not per video file or even
  per possession — `src/calib/shots.py` finds segment boundaries via per-frame
  HSV histogram distance between consecutive frames (real editorial cuts *and*
  fast whip-pans both correctly count as boundaries, since both break
  optical-flow trackability regardless of whether they're an editorial cut).
- One frame per segment gets manually calibrated (`src/calib/homography.py`:
  click known court landmarks from `COURT_KEYPOINTS` in `src/calib/court.py`,
  `cv2.findHomography` computes the pixel→court mapping).
- The rest of the segment's frames get their homography via
  `src/calib/propagate.py`: Lucas-Kanade optical flow tracks background
  features frame-to-frame, RANSAC estimates each step's incremental transform
  (which also absorbs player-motion outliers without needing player masks,
  since Phase 3 detection doesn't exist yet), and transforms compose with the
  anchor homography. This is a promotion of what `plan.md` originally listed
  as a Phase 9 broadcast stretch goal, not a new invention.
- Not all 10 players are visible in every frame (broadcast framing crops the
  court). This is deliberately *not* handled with new machinery — Phase 6's
  existing "no response detected" breakdown flag already covers "responsible
  defender was off-screen when the trigger happened."

**Testing philosophy:** the interactive pieces (`click_points` in
`homography.py`, the whole of `calibrate_segment.py`) need a real display and
a human clicking — they can't be exercised by an agent. Everything else they
depend on (`compute_homography`, `project_point`/`project_points`,
`render_verification_overlay`, `propagate_homography`) is covered by
synthetic-data unit tests in `tests/`, so the math is verified independently
of the GUI step. When adding calibration/tracking code, keep that split:
push interactivity to the thinnest possible layer, keep the underlying math
testable without a display.

## Current status / where we left off

- **Phase 0:** footage acquired (`data/uconnVsMichState.mp4`, 18 min, 640×360,
  ~30fps, dead time already trimmed). `docs/metrics.md` written. Hand-charting
  ground-truth clips **not started yet**.
- **Phase 1:** done. `src/io/video.py`, `src/io/overlay.py`, `src/types.py`.
- **Phase 2:** v0 pipeline built and verified (shot detection, anchor
  calibration math, optical-flow propagation) — see `plan.md` Phase 2 for the
  detailed verification notes on each piece. **The one remaining step needs
  the user, not an agent:** actually run `scripts/calibrate_segment.py`
  interactively to click real anchor points on a real frame (frame 2000 of the
  long stable segment `[1202, 2929)` was suggested — check
  `data/cache/wide_shot_2000.jpg` if it still exists, or re-extract, to see
  which named `COURT_KEYPOINTS` are visible there) and confirm the resulting
  `*.overlay.jpg` actually lines up with the real court. Until that real
  calibration exists, Phase 2's exit criteria (projected lines track the real
  ones within a few pixels) is unverified against real data — only against
  synthetic anchors.
- **Phases 3+:** not started.

Debug/scratch images from this session's verification work live in
`data/cache/` (gitignored) — safe to delete, not load-bearing.
