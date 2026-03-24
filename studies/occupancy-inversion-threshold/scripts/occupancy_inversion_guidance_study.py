import numpy as np

from occupancy_inversion_pid_common import run_pid_inversion_study


def main():
    time = np.linspace(0.0, 140.0, 2600)
    config = {
        "family_slug": "missile_guidance",
        "family_label": "Simplified Missile Guidance / Autopilot Family",
        "file_prefix": "occupancy_inversion_guidance",
        "objective": "Probe the inversion phenomenon in a high-stakes guidance-style architecture using a simplified guidance/autopilot PID family.",
        "main_claim": "In this simplified guidance/autopilot family, the sensor-side metric can also flip before the true pairwise crossover.",
        "threshold_candidate": "Pairwise excess-penalty parity remains the strongest current crossover anchor in the guidance family.",
        "plant_poles": (0.9, 0.14),
        "sigma_target": 0.30,
        "extra_pole": 0.85,
        "time": time,
        "impulse_time": np.linspace(0.0, 180.0, 5200),
        "reference": 0.035 * time + 1.2 * np.sin(0.009 * time),
        "noise_levels": np.round(
            np.unique(
                np.concatenate(
                    [
                        np.arange(0.0, 0.081, 0.01),
                        np.arange(0.085, 0.151, 0.005),
                        np.arange(0.16, 0.181, 0.01),
                    ]
                )
            ),
            3,
        ),
        "trials_per_level": 170,
        "seed": 933000,
        "slow_band_limit": 0.035,
        "slow_band_grid": np.linspace(0.0, 0.12, 1500),
        "bandwidth_grid": np.logspace(-5, 2, 32000),
        "margin_grid": np.logspace(-5, 3, 45000),
    }
    run_pid_inversion_study(config)


if __name__ == "__main__":
    main()
