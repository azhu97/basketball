# Metric Definitions

Precise definitions for the events and measurements the pipeline computes, per
Phase 0 of `plan.md`. Thresholds marked **(placeholder)** are starting points to be
tuned against hand-charted ground truth in Phase 7 — they are not final.

Timing resolution depends on source frame rate; at 30 fps, one frame = ~33 ms.

## Trigger events

- **Pass release** — the frame where the ball leaves the passer's hands. Detected as
  the frame where ball-to-passer distance starts increasing rapidly (a velocity
  spike in the ball's trajectory relative to the passer).
- **Drive initiation** — the frame where the ball handler gets past their primary
  defender's hip, or crosses a distance threshold **(placeholder: 3 ft of
  separation)** while moving toward the rim.

## Responsible defender

- **On a drive** — the nearest help/weak-side/low-man defender to the ball handler's
  projected path to the rim.
- **On a pass** — the defender matched up to the receiver (the closeout defender).
  On a skip pass, the rotating help defender is also a responder of interest.

Matchups (which defender is "assigned" to which offensive player) are computed via
nearest-in-court-space assignment, smoothed over time.

## Response onset

The first frame where the responsible defender's velocity, projected onto the
direction toward the target (ball handler, receiver, or help spot), exceeds a
threshold **(placeholder: 3 ft/s)** for **(placeholder: 3)** consecutive frames.

## Computed metrics

- **Latency** = `t_response_onset − t_trigger`
- **Recovery time** = time from trigger until the defender is within
  **(placeholder: 3 ft)** of the target
- **Optional**: distance covered, closeout speed, spacing at time of catch

## Breakdown flags

A possession is flagged when:

- Latency exceeds a threshold **(placeholder: TBD, tune in Phase 7)**
- No response is detected within a timeout window after the trigger
- Two defenders respond to the same target (a miscommunication/rotation error)

## Ground truth

Hand-charted clips (trigger frame, responder, onset frame) are logged to a CSV and
used to validate detection accuracy, responder agreement, and latency error (Phase 7).
None exist yet — first ground-truth clips are pending footage acquisition.
