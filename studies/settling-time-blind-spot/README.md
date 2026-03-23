# Settling-Time Blind Spot

This study capsule explores a specific claim: systems that look nearly equivalent under settling-time summaries can still differ dramatically in slow-input tracking competence.

Contents:

- [CONCEPT.md](./CONCEPT.md): the polished concept note.
- [scripts/latent_detector_study.py](./scripts/latent_detector_study.py): the supporting computational study.
- [runs/latest/plots/latent_detector_metric_comparison.png](./runs/latest/plots/latent_detector_metric_comparison.png): the main comparison plot.
- [runs/latest/plots/latent_detector_noise_robustness.png](./runs/latest/plots/latent_detector_noise_robustness.png): the noise-robustness follow-up.
- [runs/latest/data/latent_detector_summary.json](./runs/latest/data/latent_detector_summary.json): the machine-readable summary.

The role of this study is to test whether a system-side low-band diagnostic can reveal hidden slow-tracking liability that ordinary settling-time summaries miss.
