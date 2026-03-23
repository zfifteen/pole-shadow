# Settling-Time Blind Spot

This study capsule explores a specific claim: systems that look nearly equivalent under settling-time summaries can still differ dramatically in slow-input tracking competence.

Contents:

- [CONCEPT.md](./CONCEPT.md): the polished concept note.
- [scripts/latent_detector_study.py](./scripts/latent_detector_study.py): the supporting computational study.
- [scripts/latent_detector_followup_study.py](./scripts/latent_detector_followup_study.py): the cross-family metric-role follow-up.
- [runs/latest/plots/latent_detector_metric_comparison.png](./runs/latest/plots/latent_detector_metric_comparison.png): the main comparison plot.
- [runs/latest/plots/latent_detector_noise_robustness.png](./runs/latest/plots/latent_detector_noise_robustness.png): the noise-robustness follow-up.
- [runs/latest/plots/latent_detector_followup_metric_roles.png](./runs/latest/plots/latent_detector_followup_metric_roles.png): the cross-family settling-versus-low-band role summary.
- [runs/latest/data/latent_detector_summary.json](./runs/latest/data/latent_detector_summary.json): the machine-readable summary.
- [runs/latest/data/latent_detector_followup_summary.json](./runs/latest/data/latent_detector_followup_summary.json): the follow-up clarification summary.

The role of this study is now more precise than when it began. The core result is that settling-time summaries can miss slow-tracking liability. The hardening follow-up keeps that claim strong while narrowing the stronger one: slow-band deficit consistently outperforms settling time as a clean-task ordering metric, but across the current follow-up families bandwidth remains nearly as informative. This capsule therefore supports a settling-time blind spot more strongly than a slow-band uniqueness claim.
