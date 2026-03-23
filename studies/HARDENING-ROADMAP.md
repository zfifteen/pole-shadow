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

Current status: strong concept note plus a dedicated synthetic-family study with a visible moving interior optimum and an occupancy-style proxy that beats raw nuisance power. Current limitation: the strongest version of the claim is not yet replicated in an explicit plant/controller family, so portability remains open.

### Out-of-Family Aircraft Longitudinal Autopilot

Current status: useful domain-specific validation and boundary case. The core slow-mission-tracking idea survives, but the nuisance-driven optimum shift and strong occupancy advantage do not. Current limitation: the study needs one deliberate second pass so the repo can decide whether this capsule becomes a stronger positive validation or an intentionally preserved negative/boundary result.

### Settling-Time Blind Spot

Current status: strong matched-settling evidence that settling-time summaries can miss meaningful slow-tracking differences. Current limitation: the “slow-band deficit as latent detector” framing needs a cleaner separation from bandwidth and a clearer explanation of why the noise story is strong for command noise but weak for measurement noise.

## Sequence and Dependencies

- Start with `shadow-mass-saturation-threshold` because it is the highest-leverage opportunity to strengthen the project’s environment-aware claims in an explicit family.
- Use the result of that replication to inform the language used later in the aircraft and settling-time plans, especially around occupancy and portability.
- Run the second-pass aircraft study next so the repo has a firm answer on whether the aircraft capsule should be promoted or explicitly preserved as a boundary case.
- Harden `settling-time-blind-spot` last, because its current result is already useful and because its sharper framing depends partly on how much occupancy and portability survive in the other two efforts.

## Done Means

- [ ] The shadow-mass story has been tested in at least one explicit plant/controller family.
- [ ] The aircraft capsule has received one second-pass variant study with a clear yes/no decision on whether it becomes a stronger positive validation.
- [ ] The settling-time blind-spot capsule has one follow-up experiment that cleanly states what settling time misses and what slow-band deficit adds.
- [ ] Each of the three target capsules has an updated concept note or README language that matches the strengthened evidence.
- [ ] The technical note can summarize these three studies without overstating portability or leaving the next implementer guessing what each study now means.

## Do Not Change Yet

The following capsules remain the current reference baselines and should not be reopened as part of this hardening pass:

- `foundation-pole-shadow`
- `feedback-measurement-noise-phase-transition`
- `out-of-family-plant-pi-validation`

Those studies already do their current jobs well enough. The purpose of this roadmap is to harden the weaker or more conditional parts of the evidence stack, not to restart the whole repo.
