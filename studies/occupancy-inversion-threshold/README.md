# Occupancy Inversion Threshold

This study capsule probes a sharper failure mode than ordinary metric noise sensitivity: whether a sensor-side error metric can reverse the true ranking between two competing feedback designs before the true ranking itself changes sign.

Contents:

- [CONCEPT.md](./CONCEPT.md): the polished concept note.
- [scripts/occupancy_inversion_study.py](./scripts/occupancy_inversion_study.py): the dedicated pairwise inversion probe.
- [runs/latest/plots/occupancy_inversion_true_vs_observed.png](./runs/latest/plots/occupancy_inversion_true_vs_observed.png): the main true-gap versus observed-gap crossover figure.
- [runs/latest/plots/occupancy_inversion_parity_ratio.png](./runs/latest/plots/occupancy_inversion_parity_ratio.png): the parity-ratio threshold view.
- [runs/latest/plots/occupancy_inversion_winner_probability.png](./runs/latest/plots/occupancy_inversion_winner_probability.png): the pairwise ranking-reliability plot.
- [runs/latest/data/occupancy_inversion_summary.json](./runs/latest/data/occupancy_inversion_summary.json): the machine-readable summary.
- [runs/latest/data/occupancy_inversion_grid.csv](./runs/latest/data/occupancy_inversion_grid.csv): the aggregated pairwise noise-ladder data.
- [runs/latest/data/occupancy_inversion_trial_samples.csv](./runs/latest/data/occupancy_inversion_trial_samples.csv): the underlying Monte Carlo trial samples.

This capsule is intentionally focused. It uses the explicit plant-plus-PI family from the stronger out-of-family study, strips away plant jitter, and runs a dense pure-sensor-noise ladder on three controller pairs. The main positive case is `zeta = 0.15` versus `zeta = 0.707`. In that pair, the observed sensor-side ranking flips at about `0.106` sensor-noise standard deviation, while the true pairwise crossover occurs later at about `0.124`. The best current threshold variable is not raw occupancy ratio by itself, but the pairwise excess-penalty parity ratio relative to the clean-regime advantage margin; at the observed inversion point, that ratio is about `0.85`.

The two control pairs, `0.25 vs 0.707` and `0.35 vs 0.707`, compress under noise but do not invert within the same ladder. That makes the study stronger, not weaker. The result is not “all high-persistence designs eventually mislead the sensor.” It is a pair-specific inversion phenomenon that appears in the most fragile clean-winner comparison and can therefore be studied as a real diagnostic threshold rather than a vague noise story.
