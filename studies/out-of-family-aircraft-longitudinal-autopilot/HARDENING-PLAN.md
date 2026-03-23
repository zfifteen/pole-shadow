# Out-of-Family Aircraft Longitudinal Autopilot Hardening Plan

## Execution Outcome

Completed on `2026-03-23`.

- Added a second-pass aircraft variant study with tighter pitch-transient retuning, a slower glide mission, and lower-frequency gust structure.
- The variant made the best `zeta` mobile, but the movement was outward toward a longer shadow rather than inward.
- No matched pair cleared the stronger `<= 15%` settling and `>= 3x` mission-IAE threshold, and the occupancy proxy still did not dominate raw nuisance power.

Current interpretation: this capsule remains a mission-sensitive boundary case rather than a full positive replication of the stronger saturation story.

## Goal

Determine whether the aircraft study can be strengthened into a stronger positive validation or should remain an intentional boundary-case result.

## Current Gap

The current aircraft study shows the core slow-mission-tracking idea, but it does not satisfy the stronger acceptance shape used elsewhere:

- no matched-pair support
- no nuisance-driven optimum movement
- occupancy proxy only marginally better than raw nuisance, and not by the target margin

The next pass needs to decide whether this is a tunable study-design issue or a real domain-specific limit.

## Planned Work

### Follow-Up Strategy

- Keep the current aircraft study as baseline.
- Add one second-pass aircraft variant study rather than replacing the current script or outputs.
- Use the variant to answer whether the aircraft domain can support:
  - tighter matched-transient separation
  - a nuisance-driven optimum shift
  - stronger occupancy-style behavior

### Preferred Variant Order

Implement these in order and stop as soon as the study becomes decision-complete:

1. Retune the controller family around a more tightly matched pitch-transient family.
2. Add one alternate primary mission that emphasizes slower geometry.
3. If needed, add a second nuisance pattern with stronger low-frequency gust structure.

### Concrete Variant Defaults

- Add a new script:
  - `scripts/aircraft_longitudinal_autopilot_variant_study.py`
- Keep the same aircraft model and cascaded autopilot architecture as the current baseline.
- Preferred alternate primary mission:
  - a shallower, longer-horizon glide profile or altitude-hold drift task
- Preferred extra nuisance pattern, only if needed:
  - lower-frequency gust shaping than the current baseline

### Decision Rule

- If the second-pass variant produces either:
  - one matched pair with `<= 15%` pitch-step settling difference and `>= 3x` mission `IAE` ratio, or
  - a clear nuisance-driven inward optimum movement,
  then promote the capsule to a stronger out-of-family validation.
- If the second-pass variant still shows no moving optimum and no strong occupancy advantage, keep the capsule framed explicitly as a boundary case.

## Required Outputs

- `runs/latest/data/aircraft_autopilot_variant_comparison_summary.json`
- `runs/latest/data/aircraft_autopilot_variant_environment_grid.csv`
- `runs/latest/plots/aircraft_autopilot_variant_matched_transient.png`
- `runs/latest/plots/aircraft_autopilot_variant_best_zeta_path.png`

The comparison summary must report:

- baseline-versus-variant best `zeta` by environment
- whether a matched pair was found
- best matched-pair settling gap
- best matched-pair mission `IAE` ratio
- occupancy-proxy versus raw-nuisance comparison
- final recommendation:
  - `promote_to_stronger_validation`
  - or `keep_as_boundary_case`

## Acceptance Criteria

Meet at least one of these:

- Produce one matched pair with `<= 15%` pitch-step settling difference and `>= 3x` mission `IAE` ratio.
- Produce a nuisance-driven inward movement of the preferred design in at least one nuisance ladder.
- If neither appears, explicitly confirm the aircraft domain as a stable negative/boundary result and update the capsule language accordingly.

## Failure Interpretation

If the second-pass aircraft variant still does not produce matched-pair support or optimum movement, do not keep searching for a third variant in the same pass. Treat that outcome as informative. The capsule should then remain in the repo as the controlled boundary case showing that the stronger environment-aware claims do not travel automatically into every realistic domain.

## Assumptions and Defaults

- The current aircraft script remains the baseline reference.
- Only one follow-up variant study is in scope for this hardening pass.
- Retuning the family is preferred before changing the mission or nuisance pattern.
- No technical-note changes should happen until the boundary-case decision is explicit.
