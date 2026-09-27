# Automated Defensive Breakdown & Rotation Latency Engine — Build Plan

## Goal

Take basketball game footage, track every defender's position on the court over time, detect offensive triggers (passes and drives), and output a **latency score**: the time between an offensive trigger and the responsible secondary defender's recovery response. Surface the results in a dashboard coaches can use in place of manual film charting.

## Guiding principles

- **Get to an end-to-end result early.** A crude pipeline that produces a latency number on one clip beats a perfect detector with nothing downstream. Each phase ends with something runnable.
- **Start with the easiest version of each hard problem.** Our actual source footage is broadcast-style (pans, zooms, cuts), so Phase 2 targets that directly — but within it, start with the simplest technique that could work (anchor calibration + optical-flow propagation) before reaching for a trained model.
- **Everything downstream of Phase 2 works in court coordinates (feet), not pixels.** Latency and distance only mean something on the real court.
- **Validate against a human.** The metric is only useful if it agrees with what a coach sees on film.

---

## Phase 0 — Scoping, Data, and Metric Definition

**Objective:** Know exactly what you're measuring and have footage to measure it on.

Tasks:

- [x] Confirm footage access and usage terms. Have: `data/uconnVsMichState.mp4`, an 18-minute broadcast-camera clip (dead time trimmed), 640×360, ~30 fps (~33 ms timing resolution).
- [ ] Collect a starter set: pull 10–20 short (5–15 s) individual possession clips out of the full game for hand-charting and early development. Footage is broadcast-style (pans/zooms/cuts), not fixed-wide — Phase 2 is designed for this, see its notes.
- [ ] Write down precise definitions (put them in `docs/metrics.md`):
  - **Trigger events:** pass release (ball leaves passer's hands), drive initiation (ball handler gets past primary defender's hip / crosses a distance threshold toward the rim).
  - **Responsible defender:** e.g., on a drive, the nearest weak-side/low-man defender to the drive line; on a skip pass, the defender assigned to the receiver (closeout).
  - **Response onset:** first frame where the defender's velocity component toward the target exceeds a threshold (e.g., 3 ft/s) for N consecutive frames.
  - **Latency score:** `t_response_onset − t_trigger`. Optionally also *recovery time* = time to get within X ft of the target.
- [ ] Hand-chart 5–10 clips yourself (trigger frame, responder, onset frame). This becomes your first ground truth.

**Deliverable:** `docs/metrics.md`, a labeled clip folder, a small CSV of hand-charted events.
**Exit criteria:** You could explain to a coach exactly how a latency number is computed.

---

## Phase 1 — Project Skeleton & Video I/O

**Objective:** A clean repo you can iterate in.

Tasks:

- [x] Repo layout:

  ```
  src/
    io/          # video reading, frame extraction, caching
    calib/       # court detection + homography
    detect/      # player/ball detection
    track/       # multi-object tracking, team assignment
    events/      # pass/drive detection
    metrics/     # role assignment + latency
    viz/         # overlays, 2D court plots
  dashboard/
  data/          # raw clips, labels (gitignored)
  notebooks/
  tests/
  ```

- [x] Video reader with frame caching (`src/io/video.py`: `VideoReader`, `extract_frames`) and a simple overlay writer (`src/io/overlay.py`: `write_frame_number_overlay`).
- [x] Define core data structures: `Detection`, `Track`, `CourtPosition(t, x_ft, y_ft)`, `Event` (`src/types.py`).
- [x] Choose a per-frame output format: Parquet via pandas (decision recorded; not yet used, no per-frame data produced until Phase 2+).

**Deliverable:** Script that reads a clip and writes it back with frame numbers overlaid.
**Exit criteria:** Each future stage can read the previous stage's output file.

**Verified:** `scripts/phase1_overlay_demo.py` run against `data/uconnVsMichState.mp4`
(150-frame sample) — correct frame count, fps, and resolution in the output, frame
numbers visibly burned into a sample frame.

---

## Phase 2 — Court Calibration (Pixel → Court Coordinates)

**Objective:** Map any pixel on the floor to real (x, y) feet on a 94×50 court, for
a continuously moving/zooming **broadcast** camera (our actual source footage —
confirmed by inspecting frames seconds apart and seeing the framing/zoom change —
not the fixed tactical camera originally assumed).

**Prerequisite — shot/cut detection:** broadcast footage cuts between live game
action, replays, close-ups, crowd shots, and graphics. Detect hard cuts (frame-to-
frame histogram/pixel-difference thresholding) first; each continuous segment
between cuts is its own calibration unit, and non-game-action segments are flagged
and skipped rather than calibrated.

Tasks:

- [ ] **v0 (anchor + propagation):** Manually calibrate one anchor frame per
  continuous segment (click 4+ known court points, `cv2.findHomography`). Track
  background features frame-to-frame within the segment (`cv2.goodFeaturesToTrack`
  + Lucas-Kanade optical flow, restricted to non-player regions) and compose
  incremental transforms to propagate the homography forward without re-clicking
  every frame. Re-anchor periodically to correct drift.
- [ ] Render a top-down 2D court diagram and verify by projecting a few points back
  and forth.
- [ ] **v1 (learned keypoints, only if v0's drift/accuracy is a real blocker):**
  train a small keypoint-detection model on court landmarks (three-point arc,
  key/paint corners, baseline corners, center circle) for independent per-frame
  calibration with no drift. Needs labeled frames (Roboflow) — real training work,
  deferred unless v0 proves insufficient.

**Deliverable:** `calib/` module that, given a continuous game-action segment,
produces a per-frame homography (or explicitly marks the segment uncalibratable).
**Exit criteria:** Projected court lines track the real lines within a few pixels
across a full segment, not just at the anchor frame; known distances (e.g.,
free-throw line to baseline = 15 ft) measure correctly.

**Downstream note:** broadcast framing means not all 10 players are visible every
frame. This doesn't need new machinery — Phase 6's existing "no response detected"
breakdown flag already covers "responsible defender was off-screen when the
trigger happened."

---

## Phase 3 — Player & Ball Detection

**Objective:** Reliable per-frame boxes for players (and referees) and the ball.

Tasks:

- [ ] Baseline: pretrained YOLO (person class). Measure how often it misses players in collisions/screens.
- [ ] Label a few hundred frames (CVAT or Roboflow) with classes: `player`, `referee`, `ball`. Fine-tune YOLO.
- [ ] Filter out non-court detections (bench, crowd) by projecting foot points through the homography and dropping anything outside the court polygon.
- [ ] Use the **bottom-center of the bounding box** as the player's floor position.
- [ ] Ball detection: expect this to be the weakest link (small, blurred, occluded). Fine-tune a dedicated class and consider higher input resolution / tiled inference.

**Deliverable:** Detection output file per clip + overlay video.
**Exit criteria:** Player recall high enough that you rarely lose all 10 players; measured mAP on a held-out labeled set; ball detected in a usable fraction of frames.

---

## Phase 4 — Tracking, Team Assignment, and Identity

**Objective:** Turn per-frame boxes into continuous trajectories labeled offense/defense.

Tasks:

- [ ] Multi-object tracking with ByteTrack or BoT-SORT (both integrate easily with YOLO).
- [ ] Team assignment: crop torso region, cluster jersey colors (k-means into 2 teams + refs). Smooth team label over the track's lifetime.
- [ ] Handle ID switches in screens/pileups: re-ID embeddings, or simple court-space motion constraints (players can't teleport).
- [ ] Smooth trajectories in court space (Kalman filter or Savitzky–Golay) and compute velocity/acceleration — raw per-frame positions will be too noisy for onset detection.
- [ ] Ball trajectory: interpolate short gaps; associate ball to nearest player to estimate possession.
- [ ] (Stretch) Jersey number OCR to attach player names to tracks.

**Deliverable:** Per-clip table: `frame, track_id, team, x_ft, y_ft, vx, vy` plus ball positions, and a 2D top-down animation.
**Exit criteria:** On your starter clips, each defender keeps one ID for most of the possession; the top-down animation looks like the real play.

---

## Phase 5 — Offensive Event Detection

**Objective:** Automatically timestamp passes and drives.

Tasks:

- [ ] **Possession model:** assign ball to nearest offensive player within a distance threshold; possession changes between teammates = pass.
- [ ] **Pass release time:** frame where ball-to-passer distance starts increasing rapidly (ball velocity spike).
- [ ] **Drive detection:** ball handler's velocity toward the rim exceeds a threshold and they gain separation from their primary defender.
- [ ] Classify passes by type if useful (skip pass, swing, post entry) using court geometry.
- [ ] Compare detected event times to your hand-charted frames.

**Deliverable:** `events/` module producing a timeline of `Event(type, frame, actor_track_id)`.
**Exit criteria:** Most hand-charted events detected within a few frames of the human label; false positive rate you can live with.

---

## Phase 6 — Defensive Role Assignment & Latency Engine (Core Deliverable)

**Objective:** Compute the latency score.

Tasks:

- [ ] **Matchups:** assign each defender to an offensive player (nearest-in-court-space, smoothed over time, or Hungarian assignment per frame).
- [ ] **Responder selection per event** (rule-based first):
  - Drive → nearest help defender to the ball handler's projected path to the rim (low man / weak side).
  - Pass → defender assigned to the receiver (closeout); on a skip, also the rotating defender.
- [ ] **Response onset detection:** velocity projected onto the direction toward the target (ball handler, receiver, or help spot) crosses threshold for N frames.
- [ ] Compute metrics:
  - Latency (trigger → onset)
  - Recovery time (trigger → within X ft of target)
  - Optional: distance covered, closeout speed, spacing at time of catch
- [ ] Flag breakdowns: latency above a threshold, no response detected, or two defenders responding to the same target (miscommunication).
- [ ] Pick-and-roll coverage (stretch within phase): detect screens (screener near ball handler's defender), then measure hedge/switch/drop response timing.
- [ ] Unit tests on synthetic trajectories where you know the correct answer.

**Deliverable:** Per-event table: `event, trigger_frame, responder, onset_frame, latency_ms, recovery_ms, flag`.
**Exit criteria:** Pipeline runs end-to-end on a raw clip and outputs latency numbers.

---

## Phase 7 — Validation Against Human Charting

**Objective:** Prove the numbers are trustworthy.

Tasks:

- [ ] Expand the hand-charted set (ideally with a coach or someone who charts film) to 50+ events.
- [ ] Measure: event detection precision/recall, responder agreement (%), latency error (mean absolute error in ms), breakdown flag agreement.
- [ ] Error analysis: attribute failures to a stage (calibration, detection, tracking, event, role). Fix the worst stage first.
- [ ] Tune thresholds (onset velocity, N frames, distance cutoffs) on a dev set; report on a held-out test set.

**Deliverable:** `docs/evaluation.md` with metrics and failure examples.
**Exit criteria:** Latency within an agreed tolerance of human labels (e.g., ±100 ms) for most events, and coaches agree with most flagged breakdowns.

---

## Phase 8 — Coach-Facing Dashboard

**Objective:** Make the output usable without touching code.

Tasks:

- [ ] Start in **Streamlit** (fast iteration); move to React only if you need richer interaction.
- [ ] Views:
  - Possession list with flagged breakdowns
  - Synced video player + top-down court animation, jump-to-event
  - Per-player latency distribution and averages
  - Filters: event type, player, lineup, game, half
- [ ] Export: clip snippets of flagged events, CSV of metrics.
- [ ] Get feedback from an actual coach and iterate on what they actually look at.

**Deliverable:** Dashboard that loads a processed game and lets a coach review breakdowns.
**Exit criteria:** A coach can find the worst rotations in a game in minutes instead of hours.

---

## Phase 9 — Scale-Up (Stretch)

- [ ] Full-game batch processing: job queue, per-possession segmentation, caching intermediate outputs.
- [ ] Performance: GPU batching, lower-res detection + high-res ball crops, target near-real-time.
- [ ] Learned models to replace rules: e.g., a sequence model on trajectories to predict the "correct" responder or expected rotation, then score deviation from it.
- [ ] Aggregate reports across games (season trends per player/lineup).

---

## Milestone summary

| Milestone | Phases | Outcome |
| --- | --- | --- |
| M1: Metric defined | 0–1 | Definitions + labeled clips + repo |
| M2: Court space | 2 | Pixels map to feet |
| M3: Trajectories | 3–4 | 10 tracked players, top-down animation |
| M4: First latency number | 5–6 | End-to-end pipeline on one clip |
| M5: Trustworthy | 7 | Validated against human charting |
| M6: Usable | 8 | Coach-facing dashboard |
| M7: Production-ish | 9 | Full games at scale |

## Key risks

- **Ball tracking quality** — pass timing depends on it. Mitigation: dedicated ball model, interpolation, and falling back to possession-change timing.
- **Occlusion and ID switches** in screens and post play. Mitigation: court-space motion constraints, re-ID, smoothing.
- **Broadcast camera motion** — our source footage pans/zooms continuously, confirmed by inspecting frames seconds apart. Mitigation: Phase 2's anchor + optical-flow propagation approach (v0), with per-frame learned keypoints (v1) if drift proves too costly. Not deferred — this is now a Phase 2 problem, not a later stretch.
- **Partial court visibility** — broadcast framing means not all 10 players are visible every frame. Mitigation: treat an off-screen responsible defender as the existing "no response detected" breakdown flag (Phase 6) rather than building separate handling.
- **"Responsible defender" is a coaching judgment**, not purely geometric, and depends on the team's scheme. Mitigation: make rules configurable per scheme and validate with coaches.
- **Data access/licensing** for Synergy or team film. Resolve in Phase 0.
