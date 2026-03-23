# Studies Hardening Roadmap

## Purpose

This roadmap exists to keep the next round of evidence hardening explicit, sequenced, and easy to follow without turning the study READMEs into planning documents.

The current goal is not to reopen every capsule. It is to harden the three studies that now control the credibility boundary of the project:

1. `shadow-mass-saturation-threshold`
2. `out-of-family-aircraft-longitudinal-autopilot`
3. `settling-time-blind-spot`

## Current Priority Order

### 1. Shadow-Mass Saturation Threshold

This is the highest-value next target because the current moving-optimum and occupancy-proxy story is strong, but it is still anchored mainly in synthetic second-order families. The next step is to determine whether that stronger story survives at least one explicit plant/controller family rather than remaining a powerful but narrow result.

### 2. Out-of-Family Aircraft Longitudinal Autopilot

This is the main boundary-case study. It already matters because it shows the framework does not simply win everywhere. The next step is to decide whether a second-pass aircraft variant turns it into a stronger positive validation or confirms that it should remain a scoped counterweight that marks the current limit of portability.

### 3. Settling-Time Blind Spot

This study is already useful, but it should be hardened after the first two because its latent-detector story is uneven across nuisance modes and because bandwidth still co-orders the current family. The next step is to sharpen exactly what the study proves and what slow-band deficit adds beyond the current matched-settling demonstration.

## Status Summary

### Shadow-Mass Saturation Threshold

Current status: hardened. The capsule now has both the original synthetic-family study and an explicit plant-plus-PI replication. The stronger environment-aware story survives the replication: the preferred design moves inward under both command-side and measurement-side nuisance, and the occupancy-style proxy outperforms raw nuisance power by a wide margin. Current interpretation: this is now a real cross-family finding, not just a synthetic-family curiosity.

### Out-of-Family Aircraft Longitudinal Autopilot

Current status: hardened as a boundary-setting capsule. The baseline study still acts as the core aircraft boundary case, and the second-pass variant now makes that boundary more precise. The aircraft optimum becomes mobile in the variant, but it moves outward toward a longer shadow rather than inward toward a shorter one, and the occupancy proxy still does not dominate raw nuisance power. Current interpretation: this is not a clean positive replication of the saturation story; it is a mission-sensitive counterweight that marks a real limit on portability.

### Settling-Time Blind Spot

Current status: hardened and clarified. The new cross-family follow-up shows that slow-band deficit consistently outperforms settling-time summaries as a clean-task ordering statistic, but bandwidth remains nearly as informative across the compared families. Current interpretation: this capsule now supports a strong settling-time blind spot claim and a weaker, more qualified slow-band claim.

## Sequence and Dependencies

- Start with `shadow-mass-saturation-threshold` because it is the highest-leverage opportunity to strengthen the project’s environment-aware claims in an explicit family.
- Use the result of that replication to inform the language used later in the aircraft and settling-time plans, especially around occupancy and portability.
- Run the second-pass aircraft study next so the repo has a firm answer on whether the aircraft capsule should be promoted or explicitly preserved as a boundary case.
- Harden `settling-time-blind-spot` last, because its current result is already useful and because its sharper framing depends partly on how much occupancy and portability survive in the other two efforts.

## Done Means

- [x] The shadow-mass story has been tested in at least one explicit plant/controller family.
- [x] The aircraft capsule has received one second-pass variant study with a clear yes/no decision on whether it becomes a stronger positive validation.
- [x] The settling-time blind-spot capsule has one follow-up experiment that cleanly states what settling time misses and what slow-band deficit adds.
- [x] Each of the three target capsules has an updated concept note or README language that matches the strengthened evidence.
- [x] The technical note can summarize these three studies without overstating portability or leaving the next implementer guessing what each study now means.

## Do Not Change Yet

The following capsules remain the current reference baselines and should not be reopened as part of this hardening pass:

- `foundation-pole-shadow`
- `feedback-measurement-noise-phase-transition`
- `out-of-family-plant-pi-validation`

Those studies already do their current jobs well enough. The purpose of this roadmap is to harden the weaker or more conditional parts of the evidence stack, not to restart the whole repo.
