# Settling-Time Blind Spot Hardening Plan

## Goal

Sharpen the study from “interesting matched-settling result” into a cleaner claim about what settling-time summaries miss and what slow-band deficit adds.

## Current Gap

The current study is already useful, but two things keep it from being fully settled:

- bandwidth also orders the current family perfectly
- the noise-robustness story is strong for command noise but weak for measurement noise

The next hardening pass needs to make the study’s true claim explicit rather than letting it drift toward a stronger claim than the evidence supports.

## Planned Work

### Follow-Up Study

- Keep the existing matched-settling family as baseline.
- Add one follow-up experiment designed to separate:
  - settling time
  - bandwidth
  - slow-band deficit

### Preferred Follow-Up

Use the following preference order:

1. Construct a family where settling-time summaries stay close while low-band shape changes more than bandwidth alone suggests.
2. If that is not feasible cleanly, add a summary-vs-task comparison across two families so slow-band deficit is judged on portability rather than uniqueness within one family.

### Implementation Shape

- Add a new script:
  - `scripts/latent_detector_followup_study.py`
- Keep the current `latent_detector_study.py` outputs intact.
- The follow-up study must report both clean-task ordering and nuisance-mode ordering.
- The study must directly compare:
  - settling time
  - bandwidth
  - slow-band deficit
  - any additional candidate metric only if it helps clarify the separation

## Required Outputs

- `runs/latest/data/latent_detector_followup_summary.json`
- `runs/latest/data/latent_detector_followup_metric_table.csv`
- `runs/latest/plots/latent_detector_followup_metric_roles.png`

The summary JSON must include:

- clean-regime rank fidelity for settling time
- clean-regime rank fidelity for bandwidth
- clean-regime rank fidelity for slow-band deficit
- a short machine-readable conclusion field stating one of:
  - `slow_band_adds_information_beyond_settling_time`
  - `slow_band_adds_information_beyond_settling_time_but_not_beyond_bandwidth`
  - `bandwidth_and_slow_band_are_effectively_equivalent_in_this_followup`

## Acceptance Criteria

- Demonstrate at least one case where settling-time summaries remain weak and slow-band deficit is more task-aligned than settling time.
- Make the relationship to bandwidth explicit rather than implicit.
- If bandwidth still fully captures the same ordering, revise the capsule framing toward:
  - “settling-time blind spot”
  - not “slow-band uniqueness”

## Failure Interpretation

If the follow-up cannot separate slow-band deficit from bandwidth in a meaningful way, that is still a useful outcome. The capsule should then be reframed as evidence that settling-time summaries are incomplete, while slow-band deficit remains one helpful low-band descriptor rather than a uniquely privileged detector.

## Assumptions and Defaults

- The current matched-settling study remains the baseline and is not replaced.
- The main objective is claim clarification, not metric maximalism.
- Only one follow-up study is in scope for this hardening pass.
- No technical-note edit should happen until the follow-up result clarifies whether the study still argues for slow-band uniqueness or only for a settling-time blind spot.
