# Out-of-Family Aircraft Longitudinal Autopilot

This study capsule is the first domain-specific aircraft validation of the project. Instead of prescribing a closed-loop template directly, it uses a modified F-8 longitudinal linearization, an elevator actuator lag, an altitude sensor lag, and a classical cascaded elevator autopilot for altitude and glide-profile tracking.

Contents:

- [CONCEPT.md](./CONCEPT.md): the polished concept note for what this study actually found.
- [AIRCRAFT-AUTOPILOT-HYPOTHESIS.md](./AIRCRAFT-AUTOPILOT-HYPOTHESIS.md): a paper-ready aircraft-autopilot hypothesis and significance statement.
- [scripts/aircraft_longitudinal_autopilot_study.py](./scripts/aircraft_longitudinal_autopilot_study.py): the supporting computational study.
- [runs/latest/plots/aircraft_autopilot_family_overview.png](./runs/latest/plots/aircraft_autopilot_family_overview.png): the tuned family overview and nominal mission cost view.
- [runs/latest/plots/aircraft_autopilot_settling_blind_spot.png](./runs/latest/plots/aircraft_autopilot_settling_blind_spot.png): the transient-summary versus mission-cost comparison.
- [runs/latest/plots/aircraft_autopilot_noise_conditioned_optimum.png](./runs/latest/plots/aircraft_autopilot_noise_conditioned_optimum.png): the command-side and measurement-side nuisance ladder figure.
- [runs/latest/plots/aircraft_autopilot_shadow_mass_occupancy.png](./runs/latest/plots/aircraft_autopilot_shadow_mass_occupancy.png): the occupancy-proxy follow-up.
- [runs/latest/plots/aircraft_autopilot_pairwise_reliability.png](./runs/latest/plots/aircraft_autopilot_pairwise_reliability.png): the measurement-side pairwise reliability view.
- [runs/latest/data/aircraft_autopilot_summary.json](./runs/latest/data/aircraft_autopilot_summary.json): the machine-readable summary.

This aircraft study is best read as a mixed but valuable out-of-family validation. The framework survives in a narrower form than it did in the plant-plus-PI capsule. In the clean regime, the best glide-profile design is `zeta = 0.2`, with `zeta = 0.15` and `zeta = 1.0` close behind, while `zeta = 0.25` and `zeta = 0.35` perform materially worse. The standard pitch-step settling summary is not useless in this family, but it is still incomplete: its clean-rank fidelity to glide-profile `IAE` is about `0.89`, while slow-band deficit is about `0.96`, and near-matched pitch transients can still conceal mission-tracking gaps on the order of `10%` to `20%`.

The strongest negative result is that the nuisance-driven moving optimum does not appear in this aircraft run. Across both command-side and measurement-side ladders, the best design remains anchored at `zeta = 0.2`. The strongest positive result is narrower and still important: the lower-damping `zeta = 0.15` design consistently beats the more textbook `zeta = 0.707` design across the entire measurement-noise ladder, including the extreme regime. In other words, the aircraft family does not reproduce the earlier phase-transition story, but it still supports the claim that conventional robust-looking damping does not automatically imply better slow-mission tracking.

The occupancy-style proxy is also weaker here than in the previous out-of-family study. Its global Spearman correlation with excess glide-profile penalty is about `0.83`, only marginally above raw nuisance power. That is useful in its own right because it tells us the framework is not uniformly strong across domains. The aircraft capsule therefore sharpens the boundary of the project: slow-tracking diagnostics still matter in a realistic flight-control family, but the stronger “moving optimum” and “occupancy proxy dominates” claims are not yet portable without qualification.
