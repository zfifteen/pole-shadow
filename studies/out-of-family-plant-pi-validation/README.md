# Out-of-Family Plant + PI Validation

This study capsule is the first explicit out-of-family validation of the project. Instead of prescribing a second-order closed-loop transfer function directly, it uses a nominal plant,
`G_p(s) = 1 / ((s + 1.0)(s + 0.2))`, together with a matched-decay PI controller family,
`C(s) = K_p + K_i / s`.

Contents:

- [CONCEPT.md](./CONCEPT.md): the polished concept note.
- [scripts/plant_pi_out_of_family_study.py](./scripts/plant_pi_out_of_family_study.py): the supporting computational study.
- [runs/latest/plots/plant_pi_family_overview.png](./runs/latest/plots/plant_pi_family_overview.png): the nominal family overview.
- [runs/latest/plots/plant_pi_settling_blind_spot.png](./runs/latest/plots/plant_pi_settling_blind_spot.png): the matched-settling blind-spot plot.
- [runs/latest/plots/plant_pi_noise_conditioned_optimum.png](./runs/latest/plots/plant_pi_noise_conditioned_optimum.png): the command-side and measurement-side optimum-shift figure.
- [runs/latest/plots/plant_pi_shadow_mass_occupancy.png](./runs/latest/plots/plant_pi_shadow_mass_occupancy.png): the occupancy-proxy follow-up.
- [runs/latest/plots/plant_pi_pairwise_reliability.png](./runs/latest/plots/plant_pi_pairwise_reliability.png): the sensor-side pairwise reliability view.
- [runs/latest/data/plant_pi_summary.json](./runs/latest/data/plant_pi_summary.json): the machine-readable summary.

The role of this study is to ask whether the project's diagnostic story survives a materially different family. It does. In the clean regime, the `zeta = 0.15` and `zeta = 0.707` PI designs differ by only about `10.3%` in simulated `2%` settling time, yet they differ by about `21.6x` in slow `ramp+sine` tracking `IAE`. Step settling time is almost uninformative as a clean-rank detector in this family, with Spearman rank fidelity only about `0.02`, while slow-band deficit is perfect and shadow-mass metrics are perfectly inverse-ranked against slow-tracking cost.

The study also shows a strong noise-conditioned movement of the preferred design. Under command-side nuisance, the best damping ratio shifts from `0.15` in the clean regime to `0.25` in light noise and to `0.35` in the moderate and heavy regimes. Under measurement-side nuisance, the optimum moves from `0.15` to `0.20`, then to `0.25`, then to `0.35`. The strongest candidate explanatory variable in the run is the occupancy-style proxy `noise_power * shadow_mass_l2`, whose global Spearman correlation with excess slow-tracking penalty is about `0.84`, versus only about `0.34` for raw noise power alone.
