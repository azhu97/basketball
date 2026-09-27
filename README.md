# Defensive Rotation Latency Engine

A pipeline that watches basketball broadcast footage, tracks every defender's
position on the court over time, detects offensive triggers (passes and
drives), and computes a **latency score** — how long the responsible defender
takes to react. The goal is to turn "the defense looked slow on that
possession" into a measurable number a coach can sort and filter by, in place
of manual film charting.

The full phased build plan — objectives, tasks, and exit criteria for each
stage — lives in [`plan.md`](plan.md). This README is a quick orientation;
`plan.md` is the source of truth for scope and sequencing.

## Status

- **Phase 0 (data & metrics):** source footage acquired
  (`data/uconnVsMichState.mp4`); `docs/metrics.md` defines triggers,
  responders, and the latency/recovery metrics. Hand-charted ground truth not
  started yet.
- **Phase 1 (video I/O):** done — frame reading/caching and an overlay writer.
- **Phase 2 (court calibration):** in progress. The source footage turned out
  to be real broadcast camera work (pans/zooms continuously), not a fixed
  tactical angle, so calibration is built per continuous camera segment:
  shot/cut detection, manual anchor-frame calibration, and optical-flow
  propagation across the rest of a segment. Core pipeline is built and
  verified on synthetic data and real footage; still needs a real anchor
  calibration clicked by hand.
- **Phases 3-9:** not started.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Running things

```bash
# Run tests
.venv/bin/python -m pytest tests/ -v

# Read a clip, burn frame numbers on it, write it back out
.venv/bin/python scripts/phase1_overlay_demo.py <input.mp4> <output.mp4>

# Segment a broadcast clip into continuous-camera shots
.venv/bin/python scripts/phase2_shots_demo.py <video.mp4>

# Interactively calibrate one anchor frame (opens a window -- needs a display)
.venv/bin/python scripts/calibrate_segment.py <video.mp4> --frame <idx> \
    --points <name1> <name2> <name3> <name4> --out <path.json>
```

## Project structure

```
.
├── plan.md                    # full phased build plan
├── docs/
│   └── metrics.md              # trigger/responder/latency definitions
├── src/
│   ├── types.py                 # shared data structures (Detection, Track, CourtPosition, Event)
│   ├── io/                      # video reading, frame caching, overlay writing
│   ├── calib/                   # court calibration: shot detection, homography, optical-flow propagation
│   ├── detect/                  # player/ball detection (not started)
│   ├── track/                   # multi-object tracking, team assignment (not started)
│   ├── events/                  # pass/drive event detection (not started)
│   ├── metrics/                 # role assignment + latency computation (not started)
│   └── viz/                     # overlays, 2D court plots (not started)
├── scripts/                    # runnable entry points for each phase's demo/tooling
├── tests/                      # unit tests (synthetic data -- no video or display needed)
├── dashboard/                   # coach-facing dashboard (not started)
├── data/                        # raw clips, calibration outputs -- gitignored except this structure
└── notebooks/                   # exploratory notebooks
```
