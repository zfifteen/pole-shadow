import numpy as np

from occupancy_inversion_pid_common import run_pid_inversion_study


def main():
    time = np.linspace(0.0, 360.0, 3200)
    config = {
        "family_slug": "powerplant_load_following",
        "family_label": "Power-Plant Load-Following Governor Family",
        "file_prefix": "occupancy_inversion_load_following",
        "objective": "Probe the inversion phenomenon in a domain-specific load-following architecture using a simplified turbine-governor PID family.",
        "main_claim": "In this simplified load-following architecture, the sensor-side metric can also flip before the true pairwise crossover.",
        "threshold_candidate": "Pairwise excess-penalty parity remains the strongest current crossover anchor in the load-following family.",
        "plant_poles": (0.45, 0.05),
        "sigma_target": 0.16,
        "extra_pole": 0.4,
        "time": time,
        "impulse_time": np.linspace(0.0, 420.0, 6000),
        "reference": 0.04 * time + 2.5 * np.sin(0.004 * time),
        "noise_levels": np.round(
            np.unique(
                np.concatenate(
                    [
                        np.arange(0.0, 0.081, 0.01),
                        np.arange(0.085, 0.146, 0.005),
                        np.arange(0.15, 0.201, 0.01),
                    ]
                )
            ),
            3,
        ),
        "trials_per_level": 160,
        "seed": 932000,
        "slow_band_limit": 0.02,
        "slow_band_grid": np.linspace(0.0, 0.08, 1400),
        "bandwidth_grid": np.logspace(-5, 1, 32000),
        "margin_grid": np.logspace(-5, 2, 45000),
    }
    run_pid_inversion_study(config)


if __name__ == "__main__":
    main()
