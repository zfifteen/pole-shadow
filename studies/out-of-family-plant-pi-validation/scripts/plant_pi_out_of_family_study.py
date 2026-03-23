import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import TransferFunction, freqresp, impulse, lsim


ROOT_DIR = Path(__file__).resolve().parents[3]
SHARED_PYTHON_DIR = ROOT_DIR / "shared" / "python"
RUN_DIR = Path(__file__).resolve().parents[1] / "runs" / "latest"

if str(SHARED_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_PYTHON_DIR))

from plot_theme import (
    FAST_COLOR,
    LIGHT_SHADOW_COLOR,
    MEMORY_COLOR,
    NOISE_COLOR,
    REFERENCE_COLOR,
    apply_plot_style,
    get_plot_dir,
    save_figure,
    style_panel,
    add_takeaway,
)


try:
    trapz = np.trapezoid
except AttributeError:
    trapz = np.trapz


DATA_DIR = RUN_DIR / "data"
PLOT_DIR = get_plot_dir(RUN_DIR / "plots")

SIGMA_TARGET = 0.35
P3_TARGET = 0.5
FAST_POLE_NOMINAL = 1.0
SLOW_POLE_NOMINAL = 0.2
TIME = np.linspace(0.0, 150.0, 2500)
IMPULSE_TIME = np.linspace(0.0, 150.0, 5000)
SLOW_BAND_LIMIT = 0.05
SLOW_BAND_GRID = np.linspace(0.0, 0.25, 1500)
BANDWIDTH_GRID = np.logspace(-4, 2, 30000)
BOOTSTRAP_SAMPLES = 1000
PAIRWISE_COMPARISONS = [(0.15, 0.707), (0.25, 0.707), (0.35, 0.707)]
ZETAS = [0.15, 0.20, 0.25, 0.35, 0.50, 0.707, 1.00]
LONG_SHADOW_ZETA = min(ZETAS)
MODE_COLORS = {
    "command": LIGHT_SHADOW_COLOR,
    "measurement": MEMORY_COLOR,
}
LEVEL_ORDER = ["clean", "light", "moderate", "heavy", "extreme"]
LEVEL_LABELS = {
    "clean": "Clean",
    "light": "Light",
    "moderate": "Moderate",
    "heavy": "Heavy",
    "extreme": "Extreme",
}
LEVEL_COLORS = {
    "clean": REFERENCE_COLOR,
    "light": "#f1a340",
    "moderate": MEMORY_COLOR,
    "heavy": FAST_COLOR,
    "extreme": NOISE_COLOR,
}
MATCHED_PAIR_COLOR = "#4c8eda"
SETTLING_COLOR = "#4d7c59"

MAIN_REFERENCE = 0.025 * TIME + 0.7 * np.sin(0.012 * TIME)
CLEAN_TESTS = [
    {
        "name": "ramp",
        "title": "Pure Slow Ramp",
        "reference": 0.025 * TIME,
    },
    {
        "name": "ramp_sine",
        "title": "Ramp + Low-Frequency Sine",
        "reference": MAIN_REFERENCE,
    },
    {
        "name": "slow_sine",
        "title": "Ultra-Slow Sine",
        "reference": 0.7 * np.sin(0.012 * TIME),
    },
]
ENVIRONMENTS = [
    {
        "name": "command_clean",
        "mode": "command",
        "level": "clean",
        "noise_std": 0.0,
        "fast_scale_range": (1.0, 1.0),
        "slow_scale_range": (1.0, 1.0),
        "trials": 1,
        "seed": 7601,
    },
    {
        "name": "command_light",
        "mode": "command",
        "level": "light",
        "noise_std": 0.03,
        "fast_scale_range": (0.95, 1.05),
        "slow_scale_range": (0.95, 1.05),
        "trials": 200,
        "seed": 7602,
    },
    {
        "name": "command_moderate",
        "mode": "command",
        "level": "moderate",
        "noise_std": 0.06,
        "fast_scale_range": (0.90, 1.10),
        "slow_scale_range": (0.85, 1.15),
        "trials": 200,
        "seed": 7603,
    },
    {
        "name": "command_heavy",
        "mode": "command",
        "level": "heavy",
        "noise_std": 0.10,
        "fast_scale_range": (0.85, 1.15),
        "slow_scale_range": (0.75, 1.25),
        "trials": 200,
        "seed": 7604,
    },
    {
        "name": "measurement_clean",
        "mode": "measurement",
        "level": "clean",
        "noise_std": 0.0,
        "fast_scale_range": (1.0, 1.0),
        "slow_scale_range": (1.0, 1.0),
        "trials": 1,
        "seed": 7701,
    },
    {
        "name": "measurement_light",
        "mode": "measurement",
        "level": "light",
        "noise_std": 0.02,
        "fast_scale_range": (0.95, 1.05),
        "slow_scale_range": (0.95, 1.05),
        "trials": 200,
        "seed": 7702,
    },
    {
        "name": "measurement_moderate",
        "mode": "measurement",
        "level": "moderate",
        "noise_std": 0.04,
        "fast_scale_range": (0.90, 1.10),
        "slow_scale_range": (0.85, 1.15),
        "trials": 200,
        "seed": 7703,
    },
    {
        "name": "measurement_heavy",
        "mode": "measurement",
        "level": "heavy",
        "noise_std": 0.08,
        "fast_scale_range": (0.85, 1.15),
        "slow_scale_range": (0.75, 1.25),
        "trials": 200,
        "seed": 7704,
    },
    {
        "name": "measurement_extreme",
        "mode": "measurement",
        "level": "extreme",
        "noise_std": 0.12,
        "fast_scale_range": (0.85, 1.15),
        "slow_scale_range": (0.75, 1.25),
        "trials": 200,
        "seed": 7705,
    },
]


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def decimal_key(value):
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "_")


def summarize(values):
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(array)),
        "std": float(np.std(array)),
        "p10": float(np.percentile(array, 10)),
        "median": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)),
    }


def rankdata(values):
    array = np.asarray(values, dtype=float)
    order = np.argsort(array)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(array), dtype=float)
    unique_values, inverse, counts = np.unique(array, return_inverse=True, return_counts=True)
    for unique_index, count in enumerate(counts):
        if count > 1:
            duplicate_positions = np.flatnonzero(inverse == unique_index)
            mean_rank = np.mean(ranks[duplicate_positions])
            ranks[duplicate_positions] = mean_rank
    return ranks


def spearman_corr(x_values, y_values):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    x_ranks = rankdata(x)
    y_ranks = rankdata(y)
    if float(np.std(x_ranks)) == 0.0 or float(np.std(y_ranks)) == 0.0:
        return None
    return float(np.corrcoef(x_ranks, y_ranks)[0, 1])


def percentile_ci(values):
    array = np.asarray(values, dtype=float)
    return {
        "low": float(np.percentile(array, 2.5)),
        "high": float(np.percentile(array, 97.5)),
    }


def bootstrap_mean_ci(values, seed):
    array = np.asarray(values, dtype=float)
    if len(array) == 0:
        return {"low": None, "high": None}
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(BOOTSTRAP_SAMPLES, len(array)))
    means = np.mean(array[indices], axis=1)
    return percentile_ci(means)


def bootstrap_probability_ci(boolean_values, seed):
    array = np.asarray(boolean_values, dtype=float)
    if len(array) == 0:
        return {"low": None, "high": None}
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(BOOTSTRAP_SAMPLES, len(array)))
    probabilities = np.mean(array[indices], axis=1)
    return percentile_ci(probabilities)


def plant_denominator(fast_scale=1.0, slow_scale=1.0):
    fast_pole = FAST_POLE_NOMINAL * fast_scale
    slow_pole = SLOW_POLE_NOMINAL * slow_scale
    return np.array([1.0, fast_pole + slow_pole, fast_pole * slow_pole], dtype=float), fast_pole, slow_pole


def design_pi_family(zeta):
    wn = SIGMA_TARGET / zeta
    k_p = wn**2 + 2.0 * zeta * wn * P3_TARGET - SLOW_POLE_NOMINAL
    k_i = wn**2 * P3_TARGET
    return {
        "zeta": float(zeta),
        "wn": float(wn),
        "k_p": float(k_p),
        "k_i": float(k_i),
    }


def build_closed_loop_system(k_p, k_i, fast_scale=1.0, slow_scale=1.0):
    plant_den, fast_pole, slow_pole = plant_denominator(fast_scale, slow_scale)
    a_1 = plant_den[1]
    a_0 = plant_den[2]
    numerator = np.array([k_p, k_i], dtype=float)
    denominator = np.array([1.0, a_1, a_0 + k_p, k_i], dtype=float)
    system = TransferFunction(numerator, denominator)
    return system, denominator, fast_pole, slow_pole


def simulate_output(system, reference_signal):
    _, output, _ = lsim(system, U=reference_signal, T=TIME)
    return np.asarray(output, dtype=float)


def step_response_metrics(system):
    unit_step = np.ones_like(TIME)
    response = simulate_output(system, unit_step)
    final_value = float(response[-1])
    peak_value = float(np.max(response))
    overshoot = 0.0
    if abs(final_value) > 1e-12:
        overshoot = max(0.0, (peak_value - final_value) / abs(final_value)) * 100.0

    lower = 0.1 * final_value
    upper = 0.9 * final_value
    rise_start = None
    rise_end = None
    for index, value in enumerate(response):
        if rise_start is None and value >= lower:
            rise_start = float(TIME[index])
        if rise_end is None and value >= upper:
            rise_end = float(TIME[index])
            break
    rise_time = None if rise_start is None or rise_end is None else float(rise_end - rise_start)

    settle_band = 0.02 * max(abs(final_value), 1e-12)
    violating = np.flatnonzero(np.abs(response - final_value) > settle_band)
    settling_time = 0.0 if len(violating) == 0 else float(TIME[violating[-1]])
    return {
        "step_final_value": final_value,
        "step_peak_value": peak_value,
        "step_overshoot_pct": float(overshoot),
        "step_rise_time_10_90": rise_time,
        "step_settling_time_2pct": settling_time,
        "step_response": response,
    }


def bandwidth_3db(system):
    _, response = freqresp(system, w=BANDWIDTH_GRID)
    magnitude = np.abs(response)
    crossing = np.where(magnitude <= 1.0 / np.sqrt(2.0))[0]
    return float(BANDWIDTH_GRID[crossing[0]]) if len(crossing) else float(BANDWIDTH_GRID[-1])


def slow_band_deficit(system):
    _, response = freqresp(system, w=SLOW_BAND_GRID)
    gap = np.abs(1.0 - response) ** 2
    mask = SLOW_BAND_GRID <= SLOW_BAND_LIMIT
    return float(trapz(gap[mask], SLOW_BAND_GRID[mask]))


def shadow_horizon(time_values, signal_values, epsilon):
    magnitude = np.abs(signal_values)
    peak = float(np.max(magnitude))
    if peak <= 0.0:
        return 0.0
    threshold = epsilon * peak
    above = magnitude > threshold
    if not np.any(above):
        return 0.0
    return float(time_values[np.max(np.flatnonzero(above))])


def shadow_metrics(system):
    impulse_time, impulse_response = impulse(system, T=IMPULSE_TIME)
    impulse_response = np.squeeze(np.asarray(impulse_response, dtype=float))
    abs_impulse = np.abs(impulse_response)
    return {
        "shadow_horizon_eps_0_02": shadow_horizon(impulse_time, impulse_response, 0.02),
        "shadow_mass_l1": float(trapz(abs_impulse, impulse_time)),
        "shadow_mass_l2": float(trapz(abs_impulse**2, impulse_time)),
        "impulse_peak": float(np.max(abs_impulse)),
    }


def tracking_metrics(output, reference):
    signed_error = np.asarray(output, dtype=float) - np.asarray(reference, dtype=float)
    abs_error = np.abs(signed_error)
    return {
        "iae": float(trapz(abs_error, TIME)),
        "ise": float(trapz(signed_error**2, TIME)),
        "peak_abs_error": float(np.max(abs_error)),
        "mean_abs_error": float(np.mean(abs_error)),
        "signed_error": signed_error,
        "abs_error": abs_error,
    }


def nominal_system_rows():
    rows = []
    for zeta in ZETAS:
        design = design_pi_family(zeta)
        system, denominator, fast_pole, slow_pole = build_closed_loop_system(design["k_p"], design["k_i"])
        poles = np.roots(denominator)
        step_metrics = step_response_metrics(system)
        shadow = shadow_metrics(system)
        rows.append({
            "zeta": float(zeta),
            "wn": design["wn"],
            "k_p": design["k_p"],
            "k_i": design["k_i"],
            "poles": poles,
            "system": system,
            "step_response": step_metrics["step_response"],
            "step_settling_time_2pct": step_metrics["step_settling_time_2pct"],
            "step_overshoot_pct": step_metrics["step_overshoot_pct"],
            "step_rise_time_10_90": step_metrics["step_rise_time_10_90"],
            "bandwidth_3db": bandwidth_3db(system),
            "slow_band_deficit_0_05": slow_band_deficit(system),
            "shadow_horizon_eps_0_02": shadow["shadow_horizon_eps_0_02"],
            "shadow_mass_l1": shadow["shadow_mass_l1"],
            "shadow_mass_l2": shadow["shadow_mass_l2"],
            "impulse_peak": shadow["impulse_peak"],
            "dominant_real_part": float(np.max(np.real(poles))),
            "stability_margin_d": float(-np.max(np.real(poles))),
            "step_final_value": step_metrics["step_final_value"],
            "fast_pole_nominal": float(fast_pole),
            "slow_pole_nominal": float(slow_pole),
        })
    return rows


def clean_tracking_rows(system_rows):
    rows = []
    lookup = {}
    for system_row in system_rows:
        zeta = system_row["zeta"]
        system = system_row["system"]
        lookup[zeta] = {}
        for test in CLEAN_TESTS:
            output = simulate_output(system, test["reference"])
            metrics = tracking_metrics(output, test["reference"])
            row = {
                "test_name": test["name"],
                "test_title": test["title"],
                "zeta": float(zeta),
                "iae": metrics["iae"],
                "ise": metrics["ise"],
                "peak_abs_error": metrics["peak_abs_error"],
                "mean_abs_error": metrics["mean_abs_error"],
            }
            rows.append(row)
            lookup[zeta][test["name"]] = row
    return rows, lookup


def run_environment_sweep(system_rows, clean_lookup):
    trial_rows = []
    grid_rows = []
    bootstrap_summary = {}
    pairwise_rows = []
    best_zeta_by_environment = []

    design_lookup = {row["zeta"]: row for row in system_rows}

    for environment in ENVIRONMENTS:
        rng = np.random.default_rng(environment["seed"])
        env_scenarios = []
        per_zeta = {zeta: [] for zeta in ZETAS}

        for trial_index in range(environment["trials"]):
            fast_scale = float(rng.uniform(*environment["fast_scale_range"]))
            slow_scale = float(rng.uniform(*environment["slow_scale_range"]))
            noise = environment["noise_std"] * rng.normal(size=len(TIME))
            scenario = {
                "trial_index": trial_index,
                "fast_scale": fast_scale,
                "slow_scale": slow_scale,
                "mode": environment["mode"],
                "level": environment["level"],
                "environment_name": environment["name"],
                "noise_std": float(environment["noise_std"]),
                "per_zeta": {},
            }

            for zeta in ZETAS:
                design = design_lookup[zeta]
                system, denominator, fast_pole, slow_pole = build_closed_loop_system(
                    design["k_p"],
                    design["k_i"],
                    fast_scale=fast_scale,
                    slow_scale=slow_scale,
                )
                poles = np.roots(denominator)
                stable = bool(np.all(np.real(poles) < 0.0))
                observed_iae = None

                if stable:
                    if environment["mode"] == "command":
                        output = simulate_output(system, MAIN_REFERENCE + noise)
                        true_metrics = tracking_metrics(output, MAIN_REFERENCE)
                    else:
                        output = simulate_output(system, MAIN_REFERENCE - noise)
                        true_metrics = tracking_metrics(output, MAIN_REFERENCE)
                        observed_metrics = tracking_metrics(output + noise, MAIN_REFERENCE)
                        observed_iae = observed_metrics["iae"]

                    shadow = shadow_metrics(system)
                    true_iae = true_metrics["iae"]
                    true_ise = true_metrics["ise"]
                    peak_abs_error = true_metrics["peak_abs_error"]
                    mean_abs_error = true_metrics["mean_abs_error"]
                    shadow_mass_l2_trial = shadow["shadow_mass_l2"]
                    occupancy_proxy_l2 = (environment["noise_std"] ** 2) * shadow_mass_l2_trial
                    excess_true_iae = true_iae - clean_lookup[zeta]["ramp_sine"]["iae"]
                else:
                    true_iae = np.nan
                    true_ise = np.nan
                    peak_abs_error = np.nan
                    mean_abs_error = np.nan
                    shadow_mass_l2_trial = np.nan
                    occupancy_proxy_l2 = np.nan
                    excess_true_iae = np.nan

                row = {
                    "environment_name": environment["name"],
                    "mode": environment["mode"],
                    "level": environment["level"],
                    "trial_index": trial_index,
                    "zeta": float(zeta),
                    "noise_std": float(environment["noise_std"]),
                    "noise_power": float(environment["noise_std"] ** 2),
                    "fast_scale": fast_scale,
                    "slow_scale": slow_scale,
                    "fast_pole": float(fast_pole),
                    "slow_pole": float(slow_pole),
                    "stability_flag": int(stable),
                    "true_iae": None if np.isnan(true_iae) else float(true_iae),
                    "true_ise": None if np.isnan(true_ise) else float(true_ise),
                    "peak_abs_error": None if np.isnan(peak_abs_error) else float(peak_abs_error),
                    "mean_abs_error": None if np.isnan(mean_abs_error) else float(mean_abs_error),
                    "excess_true_iae_over_clean": None if np.isnan(excess_true_iae) else float(excess_true_iae),
                    "shadow_mass_l2_trial": None if np.isnan(shadow_mass_l2_trial) else float(shadow_mass_l2_trial),
                    "occupancy_proxy_l2": None if np.isnan(occupancy_proxy_l2) else float(occupancy_proxy_l2),
                    "observed_iae": None if observed_iae is None else float(observed_iae),
                }
                trial_rows.append(row)
                scenario["per_zeta"][zeta] = row
                per_zeta[zeta].append(row)
            env_scenarios.append(scenario)

        env_bootstrap = build_environment_bootstrap(environment, env_scenarios)
        bootstrap_summary[environment["name"]] = env_bootstrap

        for zeta in ZETAS:
            rows = per_zeta[zeta]
            stable_rows = [row for row in rows if row["stability_flag"] == 1 and row["true_iae"] is not None]
            stability_rate = float(np.mean([row["stability_flag"] for row in rows]))

            true_iae_values = [row["true_iae"] for row in stable_rows]
            true_ise_values = [row["true_ise"] for row in stable_rows]
            peak_values = [row["peak_abs_error"] for row in stable_rows]
            mean_values = [row["mean_abs_error"] for row in stable_rows]
            excess_values = [row["excess_true_iae_over_clean"] for row in stable_rows]
            shadow_values = [row["shadow_mass_l2_trial"] for row in stable_rows]
            occupancy_values = [row["occupancy_proxy_l2"] for row in stable_rows]
            observed_values = [row["observed_iae"] for row in stable_rows if row["observed_iae"] is not None]

            true_iae_stats = summarize(true_iae_values)
            true_ise_stats = summarize(true_ise_values)
            peak_stats = summarize(peak_values)
            mean_stats = summarize(mean_values)
            excess_stats = summarize(excess_values)

            ci = env_bootstrap["mean_true_iae_ci"][decimal_key(zeta)]
            best_frequency = env_bootstrap["best_zeta_frequency"][decimal_key(zeta)]
            grid_rows.append({
                "environment_name": environment["name"],
                "mode": environment["mode"],
                "level": environment["level"],
                "zeta": float(zeta),
                "noise_std": float(environment["noise_std"]),
                "noise_power": float(environment["noise_std"] ** 2),
                "mean_true_iae": true_iae_stats["mean"],
                "std_true_iae": true_iae_stats["std"],
                "p10_true_iae": true_iae_stats["p10"],
                "median_true_iae": true_iae_stats["median"],
                "p90_true_iae": true_iae_stats["p90"],
                "ci_true_iae_low": ci["low"],
                "ci_true_iae_high": ci["high"],
                "mean_true_ise": true_ise_stats["mean"],
                "mean_peak_abs_error": peak_stats["mean"],
                "mean_abs_error": mean_stats["mean"],
                "mean_excess_true_iae_over_clean": excess_stats["mean"],
                "mean_shadow_mass_l2_trial": float(np.mean(shadow_values)),
                "mean_occupancy_proxy_l2": float(np.mean(occupancy_values)),
                "mean_observed_iae": None if len(observed_values) == 0 else float(np.mean(observed_values)),
                "stability_rate": stability_rate,
                "valid_trial_count": len(stable_rows),
                "bootstrap_best_frequency": best_frequency,
            })

        best_entry = {
            "environment_name": environment["name"],
            "mode": environment["mode"],
            "level": environment["level"],
            "noise_std": float(environment["noise_std"]),
            "best_zeta": env_bootstrap["best_zeta"]["mean"],
            "best_zeta_ci_low": env_bootstrap["best_zeta"]["low"],
            "best_zeta_ci_high": env_bootstrap["best_zeta"]["high"],
            "best_zeta_probability_table": env_bootstrap["best_zeta_frequency"],
        }
        best_zeta_by_environment.append(best_entry)

        if environment["mode"] == "measurement":
            pairwise_rows.extend(pairwise_reliability_rows(environment, env_scenarios))

    return trial_rows, grid_rows, bootstrap_summary, pairwise_rows, best_zeta_by_environment


def build_environment_bootstrap(environment, scenarios):
    valid_scenarios = [
        scenario for scenario in scenarios
        if all(
            scenario["per_zeta"][zeta]["stability_flag"] == 1 and scenario["per_zeta"][zeta]["true_iae"] is not None
            for zeta in ZETAS
        )
    ]
    if len(valid_scenarios) == 0:
        null_ci = {decimal_key(zeta): {"low": None, "high": None} for zeta in ZETAS}
        null_freq = {decimal_key(zeta): 0.0 for zeta in ZETAS}
        return {
            "mean_true_iae_ci": null_ci,
            "best_zeta": {"mean": None, "low": None, "high": None},
            "best_zeta_frequency": null_freq,
        }

    matrix = np.array(
        [[scenario["per_zeta"][zeta]["true_iae"] for zeta in ZETAS] for scenario in valid_scenarios],
        dtype=float,
    )
    if len(valid_scenarios) == 1:
        mean_values = np.mean(matrix, axis=0)
        ci = {
            decimal_key(zeta): {"low": float(mean_values[index]), "high": float(mean_values[index])}
            for index, zeta in enumerate(ZETAS)
        }
        best_index = int(np.argmin(mean_values))
        best_zeta = ZETAS[best_index]
        frequency = {
            decimal_key(zeta): 1.0 if zeta == best_zeta else 0.0
            for zeta in ZETAS
        }
        return {
            "mean_true_iae_ci": ci,
            "best_zeta": {"mean": float(best_zeta), "low": float(best_zeta), "high": float(best_zeta)},
            "best_zeta_frequency": frequency,
        }

    rng = np.random.default_rng(environment["seed"] + 9000)
    bootstrap_indices = rng.integers(0, len(valid_scenarios), size=(BOOTSTRAP_SAMPLES, len(valid_scenarios)))
    sampled_means = np.mean(matrix[bootstrap_indices], axis=1)
    ci = {
        decimal_key(zeta): {
            "low": float(np.percentile(sampled_means[:, index], 2.5)),
            "high": float(np.percentile(sampled_means[:, index], 97.5)),
        }
        for index, zeta in enumerate(ZETAS)
    }
    best_indices = np.argmin(sampled_means, axis=1)
    best_zetas = np.array([ZETAS[index] for index in best_indices], dtype=float)
    frequency = {
        decimal_key(zeta): float(np.mean(best_zetas == zeta))
        for zeta in ZETAS
    }
    return {
        "mean_true_iae_ci": ci,
        "best_zeta": {
            "mean": float(np.mean(best_zetas)),
            "low": float(np.percentile(best_zetas, 2.5)),
            "high": float(np.percentile(best_zetas, 97.5)),
        },
        "best_zeta_frequency": frequency,
    }


def pairwise_reliability_rows(environment, scenarios):
    rows = []
    for pair_index, (left_zeta, right_zeta) in enumerate(PAIRWISE_COMPARISONS):
        valid_scenarios = [
            scenario for scenario in scenarios
            if scenario["per_zeta"][left_zeta]["stability_flag"] == 1
            and scenario["per_zeta"][right_zeta]["stability_flag"] == 1
            and scenario["per_zeta"][left_zeta]["true_iae"] is not None
            and scenario["per_zeta"][right_zeta]["true_iae"] is not None
        ]

        true_wins = np.array([
            scenario["per_zeta"][left_zeta]["true_iae"] < scenario["per_zeta"][right_zeta]["true_iae"]
            for scenario in valid_scenarios
        ], dtype=float)
        observed_wins = np.array([
            scenario["per_zeta"][left_zeta]["observed_iae"] < scenario["per_zeta"][right_zeta]["observed_iae"]
            for scenario in valid_scenarios
        ], dtype=float)

        true_ci = bootstrap_probability_ci(true_wins, environment["seed"] + 12000 + pair_index)
        observed_ci = bootstrap_probability_ci(observed_wins, environment["seed"] + 13000 + pair_index)
        rows.append({
            "environment_name": environment["name"],
            "mode": environment["mode"],
            "level": environment["level"],
            "noise_std": float(environment["noise_std"]),
            "left_zeta": float(left_zeta),
            "right_zeta": float(right_zeta),
            "valid_pair_trial_count": len(valid_scenarios),
            "true_winner_probability_left": float(np.mean(true_wins)),
            "true_winner_ci_low": true_ci["low"],
            "true_winner_ci_high": true_ci["high"],
            "observed_winner_probability_left": float(np.mean(observed_wins)),
            "observed_winner_ci_low": observed_ci["low"],
            "observed_winner_ci_high": observed_ci["high"],
        })
    return rows


def matched_pair_rows(system_rows, clean_lookup):
    rows = []
    for left_index, left in enumerate(system_rows):
        for right in system_rows[left_index + 1:]:
            settling_left = left["step_settling_time_2pct"]
            settling_right = right["step_settling_time_2pct"]
            mean_settling = 0.5 * (settling_left + settling_right)
            settling_diff_pct = 0.0 if mean_settling == 0.0 else abs(settling_left - settling_right) / mean_settling * 100.0
            iae_left = clean_lookup[left["zeta"]]["ramp_sine"]["iae"]
            iae_right = clean_lookup[right["zeta"]]["ramp_sine"]["iae"]
            slower, faster = (left, right) if iae_left >= iae_right else (right, left)
            worse_iae = max(iae_left, iae_right)
            better_iae = min(iae_left, iae_right)
            ratio = worse_iae / max(better_iae, 1e-12)
            rows.append({
                "left_zeta": float(left["zeta"]),
                "right_zeta": float(right["zeta"]),
                "settling_diff_pct": float(settling_diff_pct),
                "left_settling_time_2pct": settling_left,
                "right_settling_time_2pct": settling_right,
                "left_ramp_sine_iae": iae_left,
                "right_ramp_sine_iae": iae_right,
                "iae_ratio": float(ratio),
                "better_zeta": float(faster["zeta"]),
                "worse_zeta": float(slower["zeta"]),
            })
    rows.sort(key=lambda row: row["iae_ratio"], reverse=True)
    return rows


def summary_payload(system_rows, clean_rows, clean_lookup, grid_rows, trial_rows, bootstrap_summary, pairwise_rows):
    ramp_sine_rows = [row for row in clean_rows if row["test_name"] == "ramp_sine"]
    ramp_sine_rows.sort(key=lambda row: row["zeta"])
    clean_iae_by_zeta = {row["zeta"]: row["iae"] for row in ramp_sine_rows}

    rank_fidelity = {
        "step_settling_time_2pct": spearman_corr(
            [row["step_settling_time_2pct"] for row in system_rows],
            [clean_iae_by_zeta[row["zeta"]] for row in system_rows],
        ),
        "bandwidth_3db": spearman_corr(
            [row["bandwidth_3db"] for row in system_rows],
            [clean_iae_by_zeta[row["zeta"]] for row in system_rows],
        ),
        "slow_band_deficit_0_05": spearman_corr(
            [row["slow_band_deficit_0_05"] for row in system_rows],
            [clean_iae_by_zeta[row["zeta"]] for row in system_rows],
        ),
        "shadow_mass_l1": spearman_corr(
            [row["shadow_mass_l1"] for row in system_rows],
            [clean_iae_by_zeta[row["zeta"]] for row in system_rows],
        ),
        "shadow_mass_l2": spearman_corr(
            [row["shadow_mass_l2"] for row in system_rows],
            [clean_iae_by_zeta[row["zeta"]] for row in system_rows],
        ),
    }

    matched_pairs = matched_pair_rows(system_rows, clean_lookup)
    supportive_pairs = [
        row for row in matched_pairs
        if row["settling_diff_pct"] <= 15.0 and row["iae_ratio"] >= 3.0
    ]
    top_supportive_pair = supportive_pairs[0] if supportive_pairs else None

    best_by_environment = {}
    for environment in ENVIRONMENTS:
        env_rows = [row for row in grid_rows if row["environment_name"] == environment["name"]]
        best_row = min(env_rows, key=lambda row: row["mean_true_iae"])
        long_shadow_row = next(row for row in env_rows if abs(row["zeta"] - LONG_SHADOW_ZETA) < 1e-12)
        best_by_environment[environment["name"]] = {
            "mode": environment["mode"],
            "level": environment["level"],
            "noise_std": environment["noise_std"],
            "best_zeta": float(best_row["zeta"]),
            "best_mean_true_iae": best_row["mean_true_iae"],
            "best_zeta_ci_low": bootstrap_summary[environment["name"]]["best_zeta"]["low"],
            "best_zeta_ci_high": bootstrap_summary[environment["name"]]["best_zeta"]["high"],
            "best_zeta_frequency": bootstrap_summary[environment["name"]]["best_zeta_frequency"],
            "long_shadow_gap_vs_best": float(long_shadow_row["mean_true_iae"] - best_row["mean_true_iae"]),
            "stability_rate_min": float(min(row["stability_rate"] for row in env_rows)),
        }

    noisy_grid = [row for row in grid_rows if row["level"] != "clean"]
    occupancy_corr = spearman_corr(
        [row["mean_occupancy_proxy_l2"] for row in noisy_grid],
        [row["mean_excess_true_iae_over_clean"] for row in noisy_grid],
    )
    raw_noise_corr = spearman_corr(
        [row["noise_power"] for row in noisy_grid],
        [row["mean_excess_true_iae_over_clean"] for row in noisy_grid],
    )
    per_mode_corr = {}
    for mode in ("command", "measurement"):
        mode_rows = [row for row in noisy_grid if row["mode"] == mode]
        per_mode_corr[mode] = {
            "occupancy_proxy_l2_vs_excess_true_iae": spearman_corr(
                [row["mean_occupancy_proxy_l2"] for row in mode_rows],
                [row["mean_excess_true_iae_over_clean"] for row in mode_rows],
            ),
            "raw_noise_power_vs_excess_true_iae": spearman_corr(
                [row["noise_power"] for row in mode_rows],
                [row["mean_excess_true_iae_over_clean"] for row in mode_rows],
            ),
        }

    pairwise_highlights = {}
    for left_zeta, right_zeta in PAIRWISE_COMPARISONS:
        pair_rows = [
            row for row in pairwise_rows
            if abs(row["left_zeta"] - left_zeta) < 1e-12 and abs(row["right_zeta"] - right_zeta) < 1e-12
        ]
        pairwise_highlights[f"{left_zeta}_vs_{right_zeta}"] = pair_rows

    claim_support = {
        "clean_slow_tracking_separation_exists": bool(
            min(clean_iae_by_zeta, key=clean_iae_by_zeta.get) == LONG_SHADOW_ZETA
        ),
        "matched_pair_support_exists": top_supportive_pair is not None,
        "nuisance_driven_inward_movement_exists": any(
            best_by_environment[environment["name"]]["best_zeta"] > LONG_SHADOW_ZETA
            for environment in ENVIRONMENTS
            if environment["level"] != "clean"
        ),
        "occupancy_proxy_beats_raw_noise_by_0_10": bool(
            occupancy_corr is not None and raw_noise_corr is not None and occupancy_corr - raw_noise_corr >= 0.10
        ) or any(
            (
                per_mode_corr[mode]["occupancy_proxy_l2_vs_excess_true_iae"] is not None
                and per_mode_corr[mode]["raw_noise_power_vs_excess_true_iae"] is not None
                and per_mode_corr[mode]["occupancy_proxy_l2_vs_excess_true_iae"]
                - per_mode_corr[mode]["raw_noise_power_vs_excess_true_iae"] >= 0.10
            )
            for mode in per_mode_corr
        ),
    }

    return {
        "study": "out-of-family-plant-pi-validation",
        "objective": "Validate the pole-shadow diagnostic framework in an explicit plant-plus-PI-controller family.",
        "nominal_plant": "1 / ((s + 1.0)(s + 0.2))",
        "controller_family": "C(s) = Kp + Ki / s",
        "matched_decay_construction": {
            "sigma_target": SIGMA_TARGET,
            "p3_target": P3_TARGET,
            "k_p_formula": "wn^2 + 2*zeta*wn*p3 - 0.2",
            "k_i_formula": "wn^2 * p3",
            "wn_formula": "sigma_target / zeta",
        },
        "damping_grid": ZETAS,
        "primary_clean_task": "ramp_sine",
        "clean_rank_fidelity": rank_fidelity,
        "matched_pairs": {
            "top_supportive_pair": top_supportive_pair,
            "pair_count_meeting_threshold": len(supportive_pairs),
            "null_report": None if top_supportive_pair is not None else "No pair met both settling-difference <= 15% and clean IAE ratio >= 3x.",
            "top_pairs_by_iae_ratio": matched_pairs[:6],
        },
        "best_design_by_environment": best_by_environment,
        "occupancy_proxy_summary": {
            "global_occupancy_proxy_vs_excess_true_iae_spearman": occupancy_corr,
            "global_raw_noise_power_vs_excess_true_iae_spearman": raw_noise_corr,
            "per_mode": per_mode_corr,
        },
        "pairwise_reliability": pairwise_highlights,
        "claim_support": claim_support,
    }


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def plot_family_overview(system_rows, clean_lookup):
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 9.5))
    representative_zetas = [0.15, 0.25, 0.35, 0.707, 1.0]
    color_map = {
        0.15: LIGHT_SHADOW_COLOR,
        0.25: "#f1a340",
        0.35: MEMORY_COLOR,
        0.707: FAST_COLOR,
        1.0: NOISE_COLOR,
    }

    ax = axes[0, 0]
    for row in system_rows:
        if row["zeta"] in representative_zetas:
            ax.plot(TIME, row["step_response"], linewidth=2.2, color=color_map[row["zeta"]], label=f"zeta = {row['zeta']:.3g}")
    style_panel(ax, "Nominal Step Responses", "Time t (seconds)", "Output")
    ax.legend(frameon=False, loc="lower right")
    add_takeaway(ax, "Matched-decay PI designs still span visibly different transient shapes.", "lower right")

    ax = axes[0, 1]
    for row in system_rows:
        poles = row["poles"]
        ax.scatter(np.real(poles), np.imag(poles), s=58, color=color_map.get(row["zeta"], MEMORY_COLOR), label=f"zeta = {row['zeta']:.3g}")
    style_panel(ax, "Closed-Loop Pole Map", "Real Axis", "Imaginary Axis")
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys(), frameon=False, fontsize=9, loc="lower left")
    add_takeaway(ax, "This family is generated through an explicit plant + PI architecture, not a prescribed second-order template.", "upper left")

    ax = axes[1, 0]
    ax.plot(
        [row["zeta"] for row in system_rows],
        [row["step_settling_time_2pct"] for row in system_rows],
        color=SETTLING_COLOR,
        marker="o",
        linewidth=2.2,
    )
    style_panel(ax, "Step Settling Across the PI Family", "Damping Ratio zeta", "2% Settling Time (s)")
    add_takeaway(ax, "Settling behavior changes less than slow-tracking cost.", "upper left")

    ax = axes[1, 1]
    zetas = [row["zeta"] for row in system_rows]
    iaes = [clean_lookup[row["zeta"]]["ramp_sine"]["iae"] for row in system_rows]
    ax.plot(zetas, iaes, color=LIGHT_SHADOW_COLOR, marker="o", linewidth=2.2)
    style_panel(ax, "Clean Ramp+Sine Tracking Cost", "Damping Ratio zeta", "IAE")
    add_takeaway(ax, "The slow-tracking advantage survives outside the hand-specified second-order family.", "upper right")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "plant_pi_family_overview.png")
    plt.close(figure)


def plot_settling_blind_spot(system_rows, clean_lookup, matched_pairs):
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 9.8))
    zetas = [row["zeta"] for row in system_rows]
    clean_iae = [clean_lookup[row["zeta"]]["ramp_sine"]["iae"] for row in system_rows]
    point_colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(zetas)))

    ax = axes[0, 0]
    settling = [row["step_settling_time_2pct"] for row in system_rows]
    ax.scatter(settling, clean_iae, s=90, c=point_colors)
    for row in system_rows:
        ax.annotate(f"{row['zeta']:.3g}", (row["step_settling_time_2pct"], clean_lookup[row["zeta"]]["ramp_sine"]["iae"]), xytext=(4, 4), textcoords="offset points", fontsize=9)
    style_panel(ax, "Settling Time vs Clean Slow-Tracking Cost", "2% Settling Time (s)", "Ramp+Sine IAE")

    ax = axes[0, 1]
    deficits = [row["slow_band_deficit_0_05"] for row in system_rows]
    ax.scatter(deficits, clean_iae, s=90, c=point_colors)
    for row in system_rows:
        ax.annotate(f"{row['zeta']:.3g}", (row["slow_band_deficit_0_05"], clean_lookup[row["zeta"]]["ramp_sine"]["iae"]), xytext=(4, 4), textcoords="offset points", fontsize=9)
    style_panel(ax, "Slow-Band Deficit vs Clean Slow-Tracking Cost", "Slow-Band Deficit [0, 0.05]", "Ramp+Sine IAE")

    ax = axes[1, 0]
    shadow_l2 = [row["shadow_mass_l2"] for row in system_rows]
    ax.scatter(shadow_l2, clean_iae, s=90, c=point_colors)
    for row in system_rows:
        ax.annotate(f"{row['zeta']:.3g}", (row["shadow_mass_l2"], clean_lookup[row["zeta"]]["ramp_sine"]["iae"]), xytext=(4, 4), textcoords="offset points", fontsize=9)
    style_panel(ax, "Shadow Mass vs Clean Slow-Tracking Cost", "Shadow Mass L2", "Ramp+Sine IAE")

    ax = axes[1, 1]
    supportive_pairs = [row for row in matched_pairs if row["settling_diff_pct"] <= 15.0][:5]
    if len(supportive_pairs) > 0:
        labels = [f"{row['better_zeta']:.3g} vs {row['worse_zeta']:.3g}" for row in supportive_pairs]
        ratios = [row["iae_ratio"] for row in supportive_pairs]
        bars = ax.barh(labels, ratios, color=MATCHED_PAIR_COLOR)
        ax.invert_yaxis()
        for bar, row in zip(bars, supportive_pairs):
            ax.text(
                bar.get_width() + 0.05,
                bar.get_y() + bar.get_height() / 2.0,
                f"{row['settling_diff_pct']:.1f}% settling gap",
                va="center",
                fontsize=9,
            )
        style_panel(ax, "Best Matched-Settling Separations", "Ramp+Sine IAE Ratio", "")
        add_takeaway(ax, "Near-matched settling can still conceal large slow-tracking gaps.", "lower right")
    else:
        style_panel(ax, "Best Matched-Settling Separations", "Ramp+Sine IAE Ratio", "")
        ax.text(0.5, 0.5, "No pair met the\n<=15% settling gap filter.", ha="center", va="center", transform=ax.transAxes, fontsize=12)
        add_takeaway(ax, "This family still shows the blind-spot idea, but not through a qualifying matched pair.", "lower right")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "plant_pi_settling_blind_spot.png")
    plt.close(figure)


def plot_noise_conditioned_optimum(grid_rows, bootstrap_summary):
    figure, axes = plt.subplots(2, 2, figsize=(14.0, 9.8))
    command_rows = [row for row in grid_rows if row["mode"] == "command"]
    measurement_rows = [row for row in grid_rows if row["mode"] == "measurement"]

    def plot_mode_curves(ax, rows, mode_name):
        mode_env_names = [env["name"] for env in ENVIRONMENTS if env["mode"] == mode_name]
        for env_name in mode_env_names:
            env_rows = sorted([row for row in rows if row["environment_name"] == env_name], key=lambda row: row["zeta"])
            level = env_rows[0]["level"]
            zetas = [row["zeta"] for row in env_rows]
            means = [row["mean_true_iae"] for row in env_rows]
            lows = [row["ci_true_iae_low"] for row in env_rows]
            highs = [row["ci_true_iae_high"] for row in env_rows]
            color = LEVEL_COLORS[level]
            ax.plot(zetas, means, color=color, linewidth=2.2, marker="o", label=LEVEL_LABELS[level])
            ax.fill_between(zetas, lows, highs, color=color, alpha=0.18)
        style_panel(ax, f"{mode_name.capitalize()}-Side Nuisance", "Damping Ratio zeta", "Mean True IAE")
        ax.legend(frameon=False, ncol=2, fontsize=9)

    plot_mode_curves(axes[0, 0], command_rows, "command")
    add_takeaway(axes[0, 0], "The preferred design moves inward as command-side nuisance intensifies.", "upper left")
    plot_mode_curves(axes[0, 1], measurement_rows, "measurement")
    add_takeaway(axes[0, 1], "Sensor-side nuisance shifts the optimum even more clearly.", "upper left")

    def best_path(ax, mode_name):
        mode_envs = [env for env in ENVIRONMENTS if env["mode"] == mode_name]
        x_values = np.arange(len(mode_envs))
        best_means = [bootstrap_summary[env["name"]]["best_zeta"]["mean"] for env in mode_envs]
        best_lows = [bootstrap_summary[env["name"]]["best_zeta"]["low"] for env in mode_envs]
        best_highs = [bootstrap_summary[env["name"]]["best_zeta"]["high"] for env in mode_envs]
        color = MODE_COLORS[mode_name]
        ax.plot(x_values, best_means, color=color, marker="o", linewidth=2.4)
        ax.fill_between(x_values, best_lows, best_highs, color=color, alpha=0.20)
        ax.set_xticks(x_values)
        ax.set_xticklabels([LEVEL_LABELS[env["level"]] for env in mode_envs])
        style_panel(ax, f"Best-zeta Path: {mode_name.capitalize()} Side", "Environment Severity", "Bootstrap Best zeta")

    best_path(axes[1, 0], "command")
    add_takeaway(axes[1, 0], "The longest shadow wins cleanly, but not uniformly once nuisance grows.", "upper left")
    best_path(axes[1, 1], "measurement")
    add_takeaway(axes[1, 1], "Measurement-side nuisance produces a stronger interior optimum.", "upper left")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "plant_pi_noise_conditioned_optimum.png")
    plt.close(figure)


def plot_shadow_mass_occupancy(grid_rows):
    figure, axes = plt.subplots(1, 2, figsize=(14.0, 5.5))
    noisy_rows = [row for row in grid_rows if row["level"] != "clean"]

    ax = axes[0]
    for mode in ("command", "measurement"):
        mode_rows = [row for row in noisy_rows if row["mode"] == mode]
        ax.scatter(
            [row["mean_occupancy_proxy_l2"] for row in mode_rows],
            [row["mean_excess_true_iae_over_clean"] for row in mode_rows],
            s=80,
            alpha=0.85,
            color=MODE_COLORS[mode],
            label=mode.capitalize(),
        )
    style_panel(ax, "Occupancy Proxy vs Excess Slow-Tracking Penalty", "Noise Power x Shadow Mass L2", "Mean Excess True IAE")
    ax.legend(frameon=False)
    occupancy_corr = spearman_corr(
        [row["mean_occupancy_proxy_l2"] for row in noisy_rows],
        [row["mean_excess_true_iae_over_clean"] for row in noisy_rows],
    )
    raw_noise_corr = spearman_corr(
        [row["noise_power"] for row in noisy_rows],
        [row["mean_excess_true_iae_over_clean"] for row in noisy_rows],
    )
    add_takeaway(
        ax,
        f"Global Spearman: occupancy = {occupancy_corr:.2f}, raw noise = {raw_noise_corr:.2f}",
        "lower right",
    )

    ax = axes[1]
    for mode in ("command", "measurement"):
        mode_envs = [env for env in ENVIRONMENTS if env["mode"] == mode]
        x_values = []
        occupancies = []
        gaps = []
        labels = []
        for index, env in enumerate(mode_envs):
            env_rows = [row for row in grid_rows if row["environment_name"] == env["name"]]
            best_row = min(env_rows, key=lambda row: row["mean_true_iae"])
            long_shadow_row = next(row for row in env_rows if abs(row["zeta"] - LONG_SHADOW_ZETA) < 1e-12)
            x_values.append(index if mode == "command" else index + 0.1)
            occupancies.append(long_shadow_row["mean_occupancy_proxy_l2"])
            gaps.append(long_shadow_row["mean_true_iae"] - best_row["mean_true_iae"])
            labels.append(LEVEL_LABELS[env["level"]])
        ax.plot(occupancies, gaps, marker="o", linewidth=2.2, color=MODE_COLORS[mode], label=mode.capitalize())
        for occupancy, gap, label in zip(occupancies, gaps, labels):
            ax.annotate(label, (occupancy, gap), xytext=(4, 4), textcoords="offset points", fontsize=9)
    style_panel(ax, "Long-Shadow Gap vs Long-Shadow Occupancy", "Long-Shadow Occupancy Proxy", "Long-Shadow Gap to Best IAE")
    ax.legend(frameon=False)
    add_takeaway(ax, "As occupancy rises, the longest shadow stops being the best design.", "upper left")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "plant_pi_shadow_mass_occupancy.png")
    plt.close(figure)


def plot_pairwise_reliability(pairwise_rows, bootstrap_summary):
    figure, axes = plt.subplots(2, 2, figsize=(14.0, 9.8))
    measurement_envs = [env for env in ENVIRONMENTS if env["mode"] == "measurement"]
    noise_values = [env["noise_std"] for env in measurement_envs]

    for axis, (left_zeta, right_zeta) in zip(axes.flat[:3], PAIRWISE_COMPARISONS):
        rows = [
            row for row in pairwise_rows
            if abs(row["left_zeta"] - left_zeta) < 1e-12 and abs(row["right_zeta"] - right_zeta) < 1e-12
        ]
        rows.sort(key=lambda row: row["noise_std"])
        axis.plot(
            [row["noise_std"] for row in rows],
            [row["true_winner_probability_left"] for row in rows],
            color=LIGHT_SHADOW_COLOR,
            linewidth=2.2,
            marker="o",
            label="True winner probability",
        )
        axis.fill_between(
            [row["noise_std"] for row in rows],
            [row["true_winner_ci_low"] for row in rows],
            [row["true_winner_ci_high"] for row in rows],
            color=LIGHT_SHADOW_COLOR,
            alpha=0.18,
        )
        axis.plot(
            [row["noise_std"] for row in rows],
            [row["observed_winner_probability_left"] for row in rows],
            color=MEMORY_COLOR,
            linewidth=2.2,
            marker="s",
            label="Observed winner probability",
        )
        axis.fill_between(
            [row["noise_std"] for row in rows],
            [row["observed_winner_ci_low"] for row in rows],
            [row["observed_winner_ci_high"] for row in rows],
            color=MEMORY_COLOR,
            alpha=0.18,
        )
        axis.axhline(0.5, color=REFERENCE_COLOR, linewidth=1.0, linestyle="--", alpha=0.45)
        style_panel(axis, f"zeta = {left_zeta:.3g} vs zeta = {right_zeta:.3g}", "Measurement Noise Std", "Probability Left Design Wins")
        axis.legend(frameon=False, fontsize=8, loc="lower left")

    heatmap = axes[1, 1]
    matrix = np.array([
        [bootstrap_summary[env["name"]]["best_zeta_frequency"][decimal_key(zeta)] for zeta in ZETAS]
        for env in measurement_envs
    ], dtype=float)
    image = heatmap.imshow(matrix, aspect="auto", cmap="Blues", vmin=0.0, vmax=1.0)
    heatmap.set_xticks(np.arange(len(ZETAS)))
    heatmap.set_xticklabels([f"{zeta:.3g}" for zeta in ZETAS], rotation=45, ha="right")
    heatmap.set_yticks(np.arange(len(measurement_envs)))
    heatmap.set_yticklabels([LEVEL_LABELS[env["level"]] for env in measurement_envs])
    heatmap.set_title("Bootstrap Best-zeta Frequency\nMeasurement-Side Nuisance")
    heatmap.set_xlabel("Damping Ratio zeta")
    heatmap.set_ylabel("Environment Severity")
    figure.colorbar(image, ax=heatmap, fraction=0.046, pad=0.04)
    add_takeaway(heatmap, "The sensor-side optimum migrates away from the longest shadow as noise rises.", "lower right")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "plant_pi_pairwise_reliability.png")
    plt.close(figure)


def write_outputs(system_rows, clean_rows, grid_rows, trial_rows, pairwise_rows, bootstrap_summary, summary):
    system_metrics_path = DATA_DIR / "plant_pi_system_metrics.csv"
    clean_tracking_path = DATA_DIR / "plant_pi_clean_tracking_metrics.csv"
    environment_grid_path = DATA_DIR / "plant_pi_environment_grid.csv"
    trial_samples_path = DATA_DIR / "plant_pi_trial_samples.csv"
    pairwise_path = DATA_DIR / "plant_pi_pairwise_reliability.csv"
    bootstrap_path = DATA_DIR / "plant_pi_bootstrap_summary.json"
    summary_path = DATA_DIR / "plant_pi_summary.json"
    manifest_path = DATA_DIR / "manifest.json"

    system_metric_rows = []
    for row in system_rows:
        system_metric_rows.append({
            "zeta": row["zeta"],
            "wn": row["wn"],
            "k_p": row["k_p"],
            "k_i": row["k_i"],
            "pole_real_parts": ";".join(f"{np.real(pole):.6f}" for pole in row["poles"]),
            "pole_imag_parts": ";".join(f"{np.imag(pole):.6f}" for pole in row["poles"]),
            "dominant_real_part": row["dominant_real_part"],
            "stability_margin_d": row["stability_margin_d"],
            "step_settling_time_2pct": row["step_settling_time_2pct"],
            "step_overshoot_pct": row["step_overshoot_pct"],
            "step_rise_time_10_90": row["step_rise_time_10_90"],
            "bandwidth_3db": row["bandwidth_3db"],
            "slow_band_deficit_0_05": row["slow_band_deficit_0_05"],
            "shadow_horizon_eps_0_02": row["shadow_horizon_eps_0_02"],
            "shadow_mass_l1": row["shadow_mass_l1"],
            "shadow_mass_l2": row["shadow_mass_l2"],
            "impulse_peak": row["impulse_peak"],
        })

    write_csv(
        system_metrics_path,
        system_metric_rows,
        [
            "zeta",
            "wn",
            "k_p",
            "k_i",
            "pole_real_parts",
            "pole_imag_parts",
            "dominant_real_part",
            "stability_margin_d",
            "step_settling_time_2pct",
            "step_overshoot_pct",
            "step_rise_time_10_90",
            "bandwidth_3db",
            "slow_band_deficit_0_05",
            "shadow_horizon_eps_0_02",
            "shadow_mass_l1",
            "shadow_mass_l2",
            "impulse_peak",
        ],
    )
    write_csv(
        clean_tracking_path,
        clean_rows,
        ["test_name", "test_title", "zeta", "iae", "ise", "peak_abs_error", "mean_abs_error"],
    )
    write_csv(
        environment_grid_path,
        grid_rows,
        [
            "environment_name",
            "mode",
            "level",
            "zeta",
            "noise_std",
            "noise_power",
            "mean_true_iae",
            "std_true_iae",
            "p10_true_iae",
            "median_true_iae",
            "p90_true_iae",
            "ci_true_iae_low",
            "ci_true_iae_high",
            "mean_true_ise",
            "mean_peak_abs_error",
            "mean_abs_error",
            "mean_excess_true_iae_over_clean",
            "mean_shadow_mass_l2_trial",
            "mean_occupancy_proxy_l2",
            "mean_observed_iae",
            "stability_rate",
            "valid_trial_count",
            "bootstrap_best_frequency",
        ],
    )
    write_csv(
        trial_samples_path,
        trial_rows,
        [
            "environment_name",
            "mode",
            "level",
            "trial_index",
            "zeta",
            "noise_std",
            "noise_power",
            "fast_scale",
            "slow_scale",
            "fast_pole",
            "slow_pole",
            "stability_flag",
            "true_iae",
            "true_ise",
            "peak_abs_error",
            "mean_abs_error",
            "excess_true_iae_over_clean",
            "shadow_mass_l2_trial",
            "occupancy_proxy_l2",
            "observed_iae",
        ],
    )
    write_csv(
        pairwise_path,
        pairwise_rows,
        [
            "environment_name",
            "mode",
            "level",
            "noise_std",
            "left_zeta",
            "right_zeta",
            "valid_pair_trial_count",
            "true_winner_probability_left",
            "true_winner_ci_low",
            "true_winner_ci_high",
            "observed_winner_probability_left",
            "observed_winner_ci_low",
            "observed_winner_ci_high",
        ],
    )
    write_json(bootstrap_path, bootstrap_summary)
    write_json(summary_path, summary)
    write_json(
        manifest_path,
        {
            "study": "out-of-family-plant-pi-validation",
            "generated_files": {
                "csv": [
                    str(system_metrics_path.relative_to(ROOT_DIR)),
                    str(clean_tracking_path.relative_to(ROOT_DIR)),
                    str(environment_grid_path.relative_to(ROOT_DIR)),
                    str(trial_samples_path.relative_to(ROOT_DIR)),
                    str(pairwise_path.relative_to(ROOT_DIR)),
                ],
                "json": [
                    str(bootstrap_path.relative_to(ROOT_DIR)),
                    str(summary_path.relative_to(ROOT_DIR)),
                    str(manifest_path.relative_to(ROOT_DIR)),
                ],
                "plots": [
                    str((PLOT_DIR / "plant_pi_family_overview.png").relative_to(ROOT_DIR)),
                    str((PLOT_DIR / "plant_pi_settling_blind_spot.png").relative_to(ROOT_DIR)),
                    str((PLOT_DIR / "plant_pi_noise_conditioned_optimum.png").relative_to(ROOT_DIR)),
                    str((PLOT_DIR / "plant_pi_shadow_mass_occupancy.png").relative_to(ROOT_DIR)),
                    str((PLOT_DIR / "plant_pi_pairwise_reliability.png").relative_to(ROOT_DIR)),
                ],
            },
        },
    )


def main():
    apply_plot_style()
    ensure_dirs()

    system_rows = nominal_system_rows()
    clean_rows, clean_lookup = clean_tracking_rows(system_rows)
    trial_rows, grid_rows, bootstrap_summary, pairwise_rows, _ = run_environment_sweep(system_rows, clean_lookup)
    summary = summary_payload(system_rows, clean_rows, clean_lookup, grid_rows, trial_rows, bootstrap_summary, pairwise_rows)
    matched_pairs = matched_pair_rows(system_rows, clean_lookup)

    plot_family_overview(system_rows, clean_lookup)
    plot_settling_blind_spot(system_rows, clean_lookup, matched_pairs)
    plot_noise_conditioned_optimum(grid_rows, bootstrap_summary)
    plot_shadow_mass_occupancy(grid_rows)
    plot_pairwise_reliability(pairwise_rows, bootstrap_summary)
    write_outputs(system_rows, clean_rows, grid_rows, trial_rows, pairwise_rows, bootstrap_summary, summary)

    print("Study complete.")
    top_pair = summary["matched_pairs"]["top_supportive_pair"]
    if top_pair is None:
        print("No matched pair met the study threshold.")
    else:
        print(
            "Top matched pair:",
            f"zeta = {top_pair['better_zeta']:.3g} vs zeta = {top_pair['worse_zeta']:.3g}",
            f"| settling diff = {top_pair['settling_diff_pct']:.2f}% | IAE ratio = {top_pair['iae_ratio']:.2f}x",
        )


if __name__ == "__main__":
    main()
