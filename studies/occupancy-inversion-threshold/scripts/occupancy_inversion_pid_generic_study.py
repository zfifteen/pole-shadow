import numpy as np

from occupancy_inversion_pid_common import run_pid_inversion_study


def main():
    time = np.linspace(0.0, 150.0, 2500)
    config = {
        "family_slug": "pid_generic",
        "family_label": "Generic Explicit PID Family",
        "file_prefix": "occupancy_inversion_pid_generic",
        "objective": "Replicate the inversion phenomenon in a second explicit plant-controller family using a PID-controlled second-order plant.",
        "main_claim": "In this generic PID family, the observed sensor-side metric can still flip before the true pairwise ranking changes sign.",
        "threshold_candidate": "The useful threshold variable remains pairwise excess-penalty parity relative to the clean-regime advantage margin.",
        "plant_poles": (1.0, 0.2),
        "sigma_target": 0.35,
        "extra_pole": 0.8,
        "time": time,
        "impulse_time": np.linspace(0.0, 150.0, 5000),
        "reference": 0.025 * time + 0.7 * np.sin(0.012 * time),
        "noise_levels": np.round(
            np.unique(
                np.concatenate(
                    [
                        np.arange(0.0, 0.081, 0.01),
                        np.arange(0.085, 0.136, 0.005),
                        np.arange(0.14, 0.161, 0.01),
                    ]
                )
            ),
            3,
        ),
        "trials_per_level": 180,
        "seed": 931000,
        "slow_band_limit": 0.05,
        "slow_band_grid": np.linspace(0.0, 0.25, 1500),
        "bandwidth_grid": np.logspace(-4, 2, 30000),
        "margin_grid": np.logspace(-4, 3, 45000),
    }
    run_pid_inversion_study(config)


if __name__ == "__main__":
    main()
