# Feedback Measurement-Noise Phase Transition

This study capsule explores what happens when noise enters through the measurement channel inside a feedback architecture rather than being added directly to the commanded input.

Contents:

- [CONCEPT.md](./CONCEPT.md): the polished concept note.
- [scripts/feedback_measurement_noise_study.py](./scripts/feedback_measurement_noise_study.py): the supporting computational study.
- [runs/latest/plots/feedback_measurement_noise_phase_transition.png](./runs/latest/plots/feedback_measurement_noise_phase_transition.png): the phase-transition visualization.
- [runs/latest/plots/feedback_measurement_noise_pairwise_reliability.png](./runs/latest/plots/feedback_measurement_noise_pairwise_reliability.png): the observed-vs-true winner reliability plot.
- [runs/latest/data/feedback_measurement_noise_summary.json](./runs/latest/data/feedback_measurement_noise_summary.json): the machine-readable summary.

The role of this study is to show that the best damping ratio can move as the measurement-noise environment worsens, and that sensor-side rollout metrics can lag that shift.
