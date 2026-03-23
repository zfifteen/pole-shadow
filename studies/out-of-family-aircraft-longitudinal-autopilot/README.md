# Out-of-Family Aircraft Longitudinal Autopilot

This study capsule is the first domain-specific aircraft validation of the project. Instead of prescribing a closed-loop template directly, it uses a modified F-8 longitudinal linearization, an elevator actuator lag, an altitude sensor lag, and a classical cascaded elevator autopilot for altitude and glide-profile tracking.

Contents:

- [CONCEPT.md](./CONCEPT.md): the polished concept note for what this study actually found.
- [AIRCRAFT-AUTOPILOT-HYPOTHESIS.md](./AIRCRAFT-AUTOPILOT-HYPOTHESIS.md): a paper-ready aircraft-autopilot hypothesis and significance statement.
- [scripts/aircraft_longitudinal_autopilot_study.py](./scripts/aircraft_longitudinal_autopilot_study.py): the supporting computational study.
- [scripts/aircraft_longitudinal_autopilot_variant_study.py](./scripts/aircraft_longitudinal_autopilot_variant_study.py): the second-pass aircraft variant study used to test whether the baseline boundary case could be tightened or overturned.
- [runs/latest/plots/aircraft_autopilot_family_overview.png](./runs/latest/plots/aircraft_autopilot_family_overview.png): the tuned family overview and nominal mission cost view.
- [runs/latest/plots/aircraft_autopilot_settling_blind_spot.png](./runs/latest/plots/aircraft_autopilot_settling_blind_spot.png): the transient-summary versus mission-cost comparison.
- [runs/latest/plots/aircraft_autopilot_noise_conditioned_optimum.png](./runs/latest/plots/aircraft_autopilot_noise_conditioned_optimum.png): the command-side and measurement-side nuisance ladder figure.
- [runs/latest/plots/aircraft_autopilot_shadow_mass_occupancy.png](./runs/latest/plots/aircraft_autopilot_shadow_mass_occupancy.png): the occupancy-proxy follow-up.
- [runs/latest/plots/aircraft_autopilot_pairwise_reliability.png](./runs/latest/plots/aircraft_autopilot_pairwise_reliability.png): the measurement-side pairwise reliability view.
- [runs/latest/plots/aircraft_autopilot_variant_matched_transient.png](./runs/latest/plots/aircraft_autopilot_variant_matched_transient.png): the second-pass matched-transient comparison.
- [runs/latest/plots/aircraft_autopilot_variant_best_zeta_path.png](./runs/latest/plots/aircraft_autopilot_variant_best_zeta_path.png): the baseline-versus-variant best-`zeta` path comparison.
- [runs/latest/data/aircraft_autopilot_summary.json](./runs/latest/data/aircraft_autopilot_summary.json): the machine-readable summary.
- [runs/latest/data/aircraft_autopilot_variant_comparison_summary.json](./runs/latest/data/aircraft_autopilot_variant_comparison_summary.json): the variant comparison summary.

This aircraft capsule is now a two-pass domain-specific validation rather than a single boundary test. The baseline run shows that the core slow-mission-tracking idea survives in a realistic cascaded elevator autopilot, but in a weaker form than it did in the plant-plus-PI capsule. In the clean regime, the best glide-profile design is `zeta = 0.2`, with `zeta = 0.15` and `zeta = 1.0` close behind, while `zeta = 0.25` and `zeta = 0.35` perform materially worse. The standard pitch-step settling summary is not useless in this family, but it is still incomplete: its clean-rank fidelity to glide-profile `IAE` is about `0.89`, while slow-band deficit is about `0.96`.

The second-pass variant makes the boundary more precise. After retuning the pitch family more tightly and switching to a slower glide mission with lower-frequency gust structure, the best design becomes mobile, but not in the same direction as the earlier saturation story. In the variant run, the optimum moves from `zeta = 0.2` toward `zeta = 0.15` as nuisance grows. That is an outward movement toward a longer shadow, not the inward movement seen in the plant-plus-PI and shadow-mass capsules. The aircraft family therefore does not replicate the current phase-transition claim cleanly, but it does show that the preferred temporal budget is mission- and tuning-sensitive rather than fixed by transient style alone.

The occupancy-style proxy remains the clearest limit here. In the baseline aircraft run it is only marginally above raw nuisance power, and in the second-pass variant raw nuisance power is slightly more aligned with excess penalty than `noise_power * shadow_mass_l2`. That is useful because it prevents overclaiming. The aircraft capsule sharpens the boundary of the project: slow-tracking diagnostics still matter in a realistic flight-control family, but the stronger “moving optimum” and “occupancy proxy dominates” claims are mission-sensitive and not yet portable without qualification.
