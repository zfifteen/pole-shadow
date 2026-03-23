# Shadow-Mass Saturation Threshold

This study capsule explores the idea that shadow mass may have an environment-dependent optimum rather than a simple "more is always better" interpretation.

Contents:

- [CONCEPT.md](./CONCEPT.md): the current polished concept note.
- [scripts/shadow_mass_saturation_study.py](./scripts/shadow_mass_saturation_study.py): the first dedicated computational study for the concept.
- [scripts/shadow_mass_explicit_family_replication.py](./scripts/shadow_mass_explicit_family_replication.py): the explicit plant-plus-PI replication pass.
- [runs/latest/plots/shadow_mass_sweet_spot.png](./runs/latest/plots/shadow_mass_sweet_spot.png): the main moving-optimum visualization.
- [runs/latest/plots/shadow_mass_occupancy_proxy.png](./runs/latest/plots/shadow_mass_occupancy_proxy.png): the candidate saturation-proxy view.
- [runs/latest/plots/shadow_mass_explicit_family_sweet_spot.png](./runs/latest/plots/shadow_mass_explicit_family_sweet_spot.png): the out-of-family moving-optimum replication.
- [runs/latest/plots/shadow_mass_explicit_family_occupancy.png](./runs/latest/plots/shadow_mass_explicit_family_occupancy.png): the explicit-family occupancy-proxy view.
- [runs/latest/data/shadow_mass_saturation_summary.json](./runs/latest/data/shadow_mass_saturation_summary.json): the machine-readable study summary.
- [runs/latest/data/shadow_mass_explicit_family_summary.json](./runs/latest/data/shadow_mass_explicit_family_summary.json): the machine-readable replication summary.

The role of this study is now twofold: first to show the moving-optimum phenomenon in a dedicated synthetic family, and then to test whether the same story survives in an explicit plant-plus-PI-controller family. The combined result is strong: in both capsules, the preferred shadow-mass budget moves inward as nuisance grows, and the occupancy-style proxy `noise_power * shadow_mass_l2` outperforms raw nuisance power as a cross-environment detector of excess penalty.
