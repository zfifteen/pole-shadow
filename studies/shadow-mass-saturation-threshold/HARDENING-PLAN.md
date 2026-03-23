# Shadow-Mass Saturation Threshold Hardening Plan

## Execution Outcome

Completed on `2026-03-23`.

- Added an explicit plant-plus-PI replication study under this capsule.
- The moving-optimum story survived the replication.
- The occupancy proxy `noise_power * shadow_mass_l2` beat raw nuisance power by a wide margin globally and within both nuisance modes.

Current interpretation: this capsule now supports a real cross-family environment-aware finding rather than a synthetic-family-only effect.

## Goal

Replicate the moving-optimum and occupancy-proxy story in at least one explicit plant/controller family so the strongest version of the shadow-mass claim is no longer supported only by the synthetic second-order family.

## Current Gap

The current study shows a persuasive moving interior optimum and a strong occupancy-style proxy, but the result still lives mainly inside a synthetic family where shadow mass and damping are tightly coupled. The next hardening pass needs to determine whether the same story survives in an explicit control architecture.

## Planned Work

### Follow-Up Study

- Add one new explicit-family replication study under this capsule.
- Use the existing plant/controller shape from `out-of-family-plant-pi-validation` as the preferred first replication target.
- Do not replace the current synthetic-family study; keep it as baseline context.

### Implementation Shape

- Add a new script:
  - `scripts/shadow_mass_explicit_family_replication.py`
- Reuse the nominal plant and PI-controller family structure from `out-of-family-plant-pi-validation`.
- Keep the damping grid aligned with the existing explicit-family study unless a narrower subset is needed for stability.
- Use the same two nuisance ladders:
  - command-side nuisance
  - measurement-side nuisance
- Use the same Monte Carlo and bootstrap counts as the plant+PI study unless the explicit-family run proves too slow.

### Required Questions the Study Must Answer

- Does the best design still move inward under command-side nuisance?
- Does the best design still move inward under measurement-side nuisance?
- Does `noise_power * shadow_mass_l2` outperform raw nuisance power as a predictor of excess penalty?
- Does the longest-shadow design remain best only in the clean regime?

### Required Comparisons

- Compare `occupancy_proxy_l2` against:
  - raw nuisance power
  - damping ratio `zeta`
- Report best-`zeta` by environment.
- Report long-shadow gap versus the best design by environment.
- Report stability rate for every environment and `zeta`.

## Required Outputs

- `runs/latest/data/shadow_mass_explicit_family_summary.json`
- `runs/latest/data/shadow_mass_explicit_family_environment_grid.csv`
- `runs/latest/data/shadow_mass_explicit_family_best_path.csv`
- `runs/latest/plots/shadow_mass_explicit_family_sweet_spot.png`
- `runs/latest/plots/shadow_mass_explicit_family_occupancy.png`

The summary JSON must include:

- best `zeta` by environment
- bootstrap intervals for best `zeta`
- long-shadow gap versus best by environment
- global occupancy-proxy correlation
- per-mode occupancy-proxy correlation
- raw nuisance-power correlation for direct comparison
- stability-rate fields for every environment

## Acceptance Criteria

- An inward optimum shift appears in at least one explicit family nuisance ladder.
- `occupancy_proxy_l2` beats raw nuisance power by at least `0.10` globally or within at least one nuisance mode.
- Stability rates are reported for all regimes and no unstable cases are silently dropped.
- The follow-up study is strong enough to say either:
  - the moving-optimum story survives explicit families, or
  - the moving-optimum story is narrower than currently phrased.

## Failure Interpretation

If the explicit-family replication fails to show an inward optimum or fails to show a meaningful occupancy advantage, revise the capsule language toward:

> shadow-mass sweet spots are family-dependent and currently strongest in the synthetic second-order family

Do not continue to frame the result as a general saturation-threshold story if the explicit-family replication does not support it.

## Assumptions and Defaults

- Preferred first replication target: the existing plant+PI architecture.
- This hardening pass adds a new study inside the same capsule rather than replacing the original one.
- The concept note should only be revised after the explicit-family replication result is known.
- No technical-note edits should happen in the same implementation pass as this hardening experiment.
