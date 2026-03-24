# Occupancy Inversion Threshold

This study capsule probes a sharper failure mode than ordinary metric noise sensitivity: whether a sensor-side error metric can reverse the true ranking between two competing feedback designs before the true ranking itself changes sign.

Contents:

- [CONCEPT.md](./CONCEPT.md): the polished concept note.
- [SIGNIFICANCE-AND-IMPLICATIONS.md](./SIGNIFICANCE-AND-IMPLICATIONS.md): why the inversion result matters and what it implies for control practice.
- [PRIOR-ART-AND-NOVELTY.md](./PRIOR-ART-AND-NOVELTY.md): the closest prior-art scan and the current novelty boundary.
- [scripts/occupancy_inversion_study.py](./scripts/occupancy_inversion_study.py): the dedicated pairwise inversion probe.
- [scripts/occupancy_inversion_pid_generic_study.py](./scripts/occupancy_inversion_pid_generic_study.py): the second explicit-family replication.
- [scripts/occupancy_inversion_load_following_study.py](./scripts/occupancy_inversion_load_following_study.py): the domain-specific load-following replication.
- [scripts/occupancy_inversion_guidance_study.py](./scripts/occupancy_inversion_guidance_study.py): the high-stakes guidance/autopilot replication.
- [scripts/occupancy_inversion_metric_benchmark.py](./scripts/occupancy_inversion_metric_benchmark.py): the direct comparison against standard summaries.
- [runs/latest/plots/occupancy_inversion_true_vs_observed.png](./runs/latest/plots/occupancy_inversion_true_vs_observed.png): the main true-gap versus observed-gap crossover figure.
- [runs/latest/plots/occupancy_inversion_parity_ratio.png](./runs/latest/plots/occupancy_inversion_parity_ratio.png): the parity-ratio threshold view.
- [runs/latest/plots/occupancy_inversion_winner_probability.png](./runs/latest/plots/occupancy_inversion_winner_probability.png): the pairwise ranking-reliability plot.
- [runs/latest/plots/occupancy_inversion_pid_generic_true_vs_observed.png](./runs/latest/plots/occupancy_inversion_pid_generic_true_vs_observed.png): the second explicit-family crossover figure.
- [runs/latest/plots/occupancy_inversion_load_following_true_vs_observed.png](./runs/latest/plots/occupancy_inversion_load_following_true_vs_observed.png): the domain-specific load-following crossover figure.
- [runs/latest/plots/occupancy_inversion_guidance_true_vs_observed.png](./runs/latest/plots/occupancy_inversion_guidance_true_vs_observed.png): the high-stakes guidance/autopilot crossover figure.
- [runs/latest/plots/occupancy_inversion_metric_benchmark_auc.png](./runs/latest/plots/occupancy_inversion_metric_benchmark_auc.png): inversion-regime AUC against competing summaries.
- [runs/latest/data/occupancy_inversion_summary.json](./runs/latest/data/occupancy_inversion_summary.json): the machine-readable summary.
- [runs/latest/data/occupancy_inversion_pid_generic_summary.json](./runs/latest/data/occupancy_inversion_pid_generic_summary.json): the second explicit-family summary.
- [runs/latest/data/occupancy_inversion_load_following_summary.json](./runs/latest/data/occupancy_inversion_load_following_summary.json): the domain-specific load-following summary.
- [runs/latest/data/occupancy_inversion_guidance_summary.json](./runs/latest/data/occupancy_inversion_guidance_summary.json): the high-stakes guidance/autopilot summary.
- [runs/latest/data/occupancy_inversion_metric_benchmark_summary.json](./runs/latest/data/occupancy_inversion_metric_benchmark_summary.json): the cross-family benchmark summary.
- [runs/latest/data/occupancy_inversion_grid.csv](./runs/latest/data/occupancy_inversion_grid.csv): the aggregated pairwise noise-ladder data.
- [runs/latest/data/occupancy_inversion_trial_samples.csv](./runs/latest/data/occupancy_inversion_trial_samples.csv): the underlying Monte Carlo trial samples.

This capsule started as a focused pairwise probe in the explicit plant-plus-PI family. In that first positive case, `zeta = 0.15` versus `zeta = 0.707`, the observed sensor-side ranking flips at about `0.106` sensor-noise standard deviation, while the true pairwise crossover occurs later at about `0.124`. The best current threshold variable is not raw occupancy ratio by itself, but the pairwise excess-penalty parity ratio relative to the clean-regime advantage margin; at the observed inversion point, that ratio is about `0.85`.

The evidence set is now broader. A second explicit PID family reproduces the inversion in two pairs, with observed crossovers preceding true crossovers and parity ratios of about `0.86` and `0.90` at the observed threshold. A domain-specific power-plant load-following governor family also reproduces the effect in its strongest pair, with an observed crossover at about `0.128`, a true crossover at about `0.146`, and a parity ratio of about `0.88`. A high-stakes simplified missile-guidance / autopilot family now reproduces it as well in two pairs, with observed crossovers at about `0.091` and `0.153`, true crossovers later at about `0.105` and `0.170`, and parity ratios again in the `0.86` to `0.88` range. This means the inversion is no longer a single-family curiosity.

The benchmark pass also sharpened the threshold story. Across the current positive families, now including the guidance replication, the parity ratio achieves an inversion-regime AUC of about `0.999`, compared with about `0.896` for a standard sensor-noise burden summary, `0.715` for raw normalized noise power, `0.811` for bandwidth ratio, `0.621` for settling-time difference, and about `0.185` for phase-margin difference. At the observed crossing itself, the parity ratio clusters tightly across positive pairs with coefficient of variation about `0.019`, versus about `0.358` for sensor-noise burden and about `0.672` for normalized noise power.

The result is still bounded. Not every pair in every family inverts. That makes the capsule stronger, not weaker. The phenomenon remains pair-specific, but it now has cross-family and domain-specific support, plus a direct benchmark showing that the parity-style threshold organizes the inversion more cleanly than the standard summaries tested here.
