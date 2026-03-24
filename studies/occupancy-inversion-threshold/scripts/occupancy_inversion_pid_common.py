import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import TransferFunction, freqresp, impulse, lsim, step


ROOT_DIR = Path(__file__).resolve().parents[3]
SHARED_PYTHON_DIR = ROOT_DIR / "shared" / "python"

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


BOOTSTRAP_SAMPLES = 500
PAIR_COLORS = {
    "0.15_vs_0.707": MEMORY_COLOR,
    "0.25_vs_0.707": FAST_COLOR,
    "0.35_vs_0.707": LIGHT_SHADOW_COLOR,
}
DEFAULT_ZETAS = [0.15, 0.20, 0.25, 0.35, 0.50, 0.707, 1.00]
DEFAULT_PAIRS = [(0.15, 0.707), (0.25, 0.707), (0.35, 0.707)]


def decimal_key(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


def pair_key(left_zeta, right_zeta):
    return f"{decimal_key(left_zeta)}_vs_{decimal_key(right_zeta)}"


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def bootstrap_mean_ci(values, seed):
    array = np.asarray(values, dtype=float)
    if len(array) == 0:
        return {"low": None, "high": None}
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(BOOTSTRAP_SAMPLES, len(array)))
    samples = np.mean(array[indices], axis=1)
    return {
        "low": float(np.percentile(samples, 2.5)),
        "high": float(np.percentile(samples, 97.5)),
    }


def bootstrap_probability_ci(boolean_values, seed):
    array = np.asarray(boolean_values, dtype=float)
    if len(array) == 0:
        return {"low": None, "high": None}
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(BOOTSTRAP_SAMPLES, len(array)))
    samples = np.mean(array[indices], axis=1)
    return {
        "low": float(np.percentile(samples, 2.5)),
        "high": float(np.percentile(samples, 97.5)),
    }


def interpolate_zero_crossing(noise_values, value_series):
    for left_index in range(len(noise_values) - 1):
        noise_left = float(noise_values[left_index])
        noise_right = float(noise_values[left_index + 1])
        value_left = float(value_series[left_index])
        value_right = float(value_series[left_index + 1])
        if value_left == 0.0:
            return noise_left
        if value_left > 0.0 and value_right < 0.0:
            fraction = value_left / (value_left - value_right)
            return float(noise_left + fraction * (noise_right - noise_left))
    return None


def interpolate_series(noise_values, value_series, target_noise):
    if target_noise is None:
        return None
    for left_index in range(len(noise_values) - 1):
        noise_left = float(noise_values[left_index])
        noise_right = float(noise_values[left_index + 1])
        if noise_left <= target_noise <= noise_right:
            value_left = float(value_series[left_index])
            value_right = float(value_series[left_index + 1])
            if noise_right == noise_left:
                return value_left
            fraction = (target_noise - noise_left) / (noise_right - noise_left)
            return float(value_left + fraction * (value_right - value_left))
    return None


def rankdata(values):
    array = np.asarray(values, dtype=float)
    order = np.argsort(array)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(array), dtype=float)
    unique_values, inverse, counts = np.unique(array, return_inverse=True, return_counts=True)
    for unique_index, count in enumerate(counts):
        if count > 1:
            duplicate_positions = np.flatnonzero(inverse == unique_index)
            ranks[duplicate_positions] = float(np.mean(ranks[duplicate_positions]))
    return ranks


def spearman_corr(x_values, y_values):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    x_ranks = rankdata(x)
    y_ranks = rankdata(y)
    if float(np.std(x_ranks)) == 0.0 or float(np.std(y_ranks)) == 0.0:
        return None
    return float(np.corrcoef(x_ranks, y_ranks)[0, 1])


def design_pid_family(zeta, sigma_target, plant_poles, extra_pole):
    fast_pole, slow_pole = plant_poles
    plant_sum = fast_pole + slow_pole
    plant_product = fast_pole * slow_pole
    natural_frequency = sigma_target / zeta
    desired_denominator = np.convolve(
        [1.0, 2.0 * zeta * natural_frequency, natural_frequency ** 2],
        [1.0, extra_pole],
    )
    s2_coeff = desired_denominator[1]
    s1_coeff = desired_denominator[2]
    s0_coeff = desired_denominator[3]
    k_d = float(s2_coeff - plant_sum)
    k_p = float(s1_coeff - plant_product)
    k_i = float(s0_coeff)
    return {
        "k_d": k_d,
        "k_p": k_p,
        "k_i": k_i,
        "natural_frequency": float(natural_frequency),
    }


def open_loop_tf(k_d, k_p, k_i, plant_poles):
    fast_pole, slow_pole = plant_poles
    denominator = np.poly([-fast_pole, -slow_pole])
    numerator = np.array([k_d, k_p, k_i], dtype=float)
    full_denominator = np.convolve([1.0, 0.0], denominator)
    return TransferFunction(numerator, full_denominator)


def closed_loop_tf(k_d, k_p, k_i, plant_poles):
    fast_pole, slow_pole = plant_poles
    denominator = np.poly([-fast_pole, -slow_pole])
    numerator = np.array([k_d, k_p, k_i], dtype=float)
    closed_loop_den = np.array(
        [1.0, denominator[1] + k_d, denominator[2] + k_p, k_i],
        dtype=float,
    )
    return TransferFunction(numerator, closed_loop_den)


def sensitivity_tf(k_d, k_p, k_i, plant_poles):
    fast_pole, slow_pole = plant_poles
    denominator = np.poly([-fast_pole, -slow_pole])
    numerator = np.convolve([1.0, 0.0], denominator)
    closed_loop_den = np.array(
        [1.0, denominator[1] + k_d, denominator[2] + k_p, k_i],
        dtype=float,
    )
    return TransferFunction(numerator, closed_loop_den)


def tracking_metrics(output, observed_output, reference, time):
    true_error = output - reference
    observed_error = observed_output - reference
    return {
        "true_iae": float(np.trapezoid(np.abs(true_error), time)),
        "true_ise": float(np.trapezoid(true_error ** 2, time)),
        "observed_iae": float(np.trapezoid(np.abs(observed_error), time)),
        "peak_abs_error": float(np.max(np.abs(true_error))),
        "mean_abs_error": float(np.mean(np.abs(true_error))),
    }


def step_response_metrics(system, time):
    _, response = step(system, T=time)
    final_value = float(response[-1])
    if abs(final_value) < 1e-12:
        return {
            "step_settling_time_2pct": None,
            "step_overshoot": None,
            "step_rise_time_10_90": None,
        }
    lower = 0.1 * final_value
    upper = 0.9 * final_value
    rise_time = None
    crossed_lower = False
    lower_time = None
    for time_value, response_value in zip(time, response):
        if not crossed_lower and response_value >= lower:
            crossed_lower = True
            lower_time = time_value
        if crossed_lower and response_value >= upper:
            rise_time = float(time_value - lower_time)
            break
    tolerance = 0.02 * abs(final_value)
    settling_time = None
    for index, time_value in enumerate(time):
        if np.all(np.abs(response[index:] - final_value) <= tolerance):
            settling_time = float(time_value)
            break
    overshoot = float(max(0.0, np.max(response) - final_value) / abs(final_value))
    return {
        "step_settling_time_2pct": settling_time,
        "step_overshoot": overshoot,
        "step_rise_time_10_90": rise_time,
    }


def bandwidth_3db(system, grid):
    _, response = freqresp(system, w=grid)
    magnitudes = np.abs(response)
    threshold = 1.0 / np.sqrt(2.0)
    below = np.flatnonzero(magnitudes <= threshold)
    return None if len(below) == 0 else float(grid[below[0]])


def slow_band_deficit(system, slow_band_grid, slow_band_limit):
    _, response = freqresp(system, w=slow_band_grid)
    magnitudes = np.abs(response)
    mask = slow_band_grid <= slow_band_limit
    deficits = np.maximum(0.0, 1.0 - magnitudes[mask])
    return float(np.trapezoid(deficits, slow_band_grid[mask]))


def shadow_horizon(time_values, signal_values, epsilon):
    normalized = np.abs(signal_values)
    peak = float(np.max(normalized))
    if peak <= 0.0:
        return 0.0
    threshold = epsilon * peak
    indices = np.flatnonzero(normalized >= threshold)
    return 0.0 if len(indices) == 0 else float(time_values[indices[-1]])


def impulse_shadow_metrics(system, impulse_time):
    time_values, signal_values = impulse(system, T=impulse_time)
    absolute = np.abs(signal_values)
    return {
        "shadow_horizon_eps_0_02": shadow_horizon(time_values, signal_values, 0.02),
        "shadow_mass_l1": float(np.trapezoid(absolute, time_values)),
        "shadow_mass_l2": float(np.trapezoid(signal_values ** 2, time_values)),
    }


def sensor_noise_sensitivity_l2(sensitivity_system, impulse_time):
    time_values, signal_values = impulse(sensitivity_system, T=impulse_time)
    return float(np.trapezoid(signal_values ** 2, time_values))


def phase_gain_margins(open_loop_system, margin_grid):
    _, response = freqresp(open_loop_system, w=margin_grid)
    magnitudes = np.abs(response)
    phases = np.unwrap(np.angle(response)) * 180.0 / np.pi
    gain_db = 20.0 * np.log10(np.maximum(magnitudes, 1e-12))

    phase_margin = None
    gain_crossover = None
    for index in range(len(margin_grid) - 1):
        left_gain = gain_db[index]
        right_gain = gain_db[index + 1]
        if left_gain == 0.0:
            gain_crossover = float(margin_grid[index])
            phase_margin = float(180.0 + phases[index])
            break
        if left_gain > 0.0 and right_gain < 0.0:
            fraction = left_gain / (left_gain - right_gain)
            gain_crossover = float(margin_grid[index] + fraction * (margin_grid[index + 1] - margin_grid[index]))
            phase_at_cross = float(phases[index] + fraction * (phases[index + 1] - phases[index]))
            phase_margin = float(180.0 + phase_at_cross)
            break

    gain_margin_db = None
    for index in range(len(margin_grid) - 1):
        left_phase = phases[index] + 180.0
        right_phase = phases[index + 1] + 180.0
        if left_phase == 0.0:
            gain_margin_db = float(-gain_db[index])
            break
        if left_phase > 0.0 and right_phase < 0.0:
            fraction = left_phase / (left_phase - right_phase)
            gain_at_cross = float(gain_db[index] + fraction * (gain_db[index + 1] - gain_db[index]))
            gain_margin_db = float(-gain_at_cross)
            break

    return {
        "phase_margin_deg": phase_margin,
        "gain_margin_db": gain_margin_db,
        "gain_crossover_rad_s": gain_crossover,
    }


def build_system_rows(config):
    rows = []
    for zeta in config["zetas"]:
        design = design_pid_family(zeta, config["sigma_target"], config["plant_poles"], config["extra_pole"])
        closed_loop = closed_loop_tf(design["k_d"], design["k_p"], design["k_i"], config["plant_poles"])
        sensitivity = sensitivity_tf(design["k_d"], design["k_p"], design["k_i"], config["plant_poles"])
        open_loop = open_loop_tf(design["k_d"], design["k_p"], design["k_i"], config["plant_poles"])
        step_metrics = step_response_metrics(closed_loop, config["time"])
        shadow = impulse_shadow_metrics(closed_loop, config["impulse_time"])
        margins = phase_gain_margins(open_loop, config["margin_grid"])
        _, output, _ = lsim(closed_loop, U=config["reference"], T=config["time"])
        clean_metrics = tracking_metrics(output, output, config["reference"], config["time"])
        rows.append({
            "zeta": float(zeta),
            "k_d": float(design["k_d"]),
            "k_p": float(design["k_p"]),
            "k_i": float(design["k_i"]),
            "step_settling_time_2pct": step_metrics["step_settling_time_2pct"],
            "step_overshoot": step_metrics["step_overshoot"],
            "step_rise_time_10_90": step_metrics["step_rise_time_10_90"],
            "bandwidth_3db": bandwidth_3db(closed_loop, config["bandwidth_grid"]),
            "slow_band_deficit": slow_band_deficit(closed_loop, config["slow_band_grid"], config["slow_band_limit"]),
            "sensor_noise_sensitivity_l2": sensor_noise_sensitivity_l2(sensitivity, config["impulse_time"]),
            "phase_margin_deg": margins["phase_margin_deg"],
            "gain_margin_db": margins["gain_margin_db"],
            "gain_crossover_rad_s": margins["gain_crossover_rad_s"],
            "clean_true_iae": clean_metrics["true_iae"],
            "clean_true_ise": clean_metrics["true_ise"],
            **shadow,
        })
    return rows


def run_pairwise_noise_probe(config, system_rows):
    system_map = {row["zeta"]: row for row in system_rows}
    closed_loops = {
        row["zeta"]: closed_loop_tf(row["k_d"], row["k_p"], row["k_i"], config["plant_poles"])
        for row in system_rows
    }

    trial_rows = []
    grid_rows = []

    for noise_index, noise_std in enumerate(config["noise_levels"]):
        rng = np.random.default_rng(config["seed"] + noise_index)
        pair_trial_rows = {pair_key(left, right): [] for left, right in config["pairwise_comparisons"]}

        for trial_index in range(config["trials_per_level"]):
            noise = float(noise_std) * rng.normal(size=len(config["time"]))

            per_zeta = {}
            for zeta in config["unique_zetas"]:
                system = closed_loops[zeta]
                _, output, _ = lsim(system, U=config["reference"] - noise, T=config["time"])
                metrics = tracking_metrics(output, output + noise, config["reference"], config["time"])
                per_zeta[zeta] = {
                    **metrics,
                    "excess_true_iae": float(metrics["true_iae"] - system_map[zeta]["clean_true_iae"]),
                    "occupancy_proxy_l2": float((noise_std ** 2) * system_map[zeta]["shadow_mass_l2"]),
                }

            for left_zeta, right_zeta in config["pairwise_comparisons"]:
                left = per_zeta[left_zeta]
                right = per_zeta[right_zeta]
                clean_advantage_iae = float(system_map[right_zeta]["clean_true_iae"] - system_map[left_zeta]["clean_true_iae"])
                clean_advantage_ise = float(system_map[right_zeta]["clean_true_ise"] - system_map[left_zeta]["clean_true_ise"])
                true_gap_iae = float(right["true_iae"] - left["true_iae"])
                observed_gap_iae = float(right["observed_iae"] - left["observed_iae"])
                true_gap_ise = float(right["true_ise"] - left["true_ise"])
                pairwise_excess_gap_iae = float(left["excess_true_iae"] - right["excess_true_iae"])
                parity_ratio_iae = None if clean_advantage_iae == 0.0 else float(pairwise_excess_gap_iae / clean_advantage_iae)
                inversion_event = bool(true_gap_iae > 0.0 and observed_gap_iae < 0.0)
                row = {
                    "pair_name": pair_key(left_zeta, right_zeta),
                    "family_slug": config["family_slug"],
                    "left_zeta": float(left_zeta),
                    "right_zeta": float(right_zeta),
                    "noise_std": float(noise_std),
                    "noise_power": float(noise_std ** 2),
                    "trial_index": trial_index,
                    "clean_advantage_iae": clean_advantage_iae,
                    "clean_advantage_ise": clean_advantage_ise,
                    "true_gap_iae": true_gap_iae,
                    "observed_gap_iae": observed_gap_iae,
                    "true_gap_ise": true_gap_ise,
                    "pairwise_excess_gap_iae": pairwise_excess_gap_iae,
                    "parity_ratio_iae": parity_ratio_iae,
                    "left_occupancy_proxy_l2": float(left["occupancy_proxy_l2"]),
                    "right_occupancy_proxy_l2": float(right["occupancy_proxy_l2"]),
                    "true_winner_left": int(true_gap_iae > 0.0),
                    "observed_winner_left": int(observed_gap_iae > 0.0),
                    "inversion_event": int(inversion_event),
                }
                trial_rows.append(row)
                pair_trial_rows[pair_key(left_zeta, right_zeta)].append(row)

        for left_zeta, right_zeta in config["pairwise_comparisons"]:
            key = pair_key(left_zeta, right_zeta)
            rows = pair_trial_rows[key]
            true_gap_series = [row["true_gap_iae"] for row in rows]
            observed_gap_series = [row["observed_gap_iae"] for row in rows]
            parity_series = [row["parity_ratio_iae"] for row in rows]
            inversion_series = [row["inversion_event"] for row in rows]
            true_winner_series = [row["true_winner_left"] for row in rows]
            observed_winner_series = [row["observed_winner_left"] for row in rows]

            true_gap_ci = bootstrap_mean_ci(true_gap_series, 1100 + noise_index * 13 + int(left_zeta * 1000))
            observed_gap_ci = bootstrap_mean_ci(observed_gap_series, 1200 + noise_index * 13 + int(right_zeta * 1000))
            parity_ci = bootstrap_mean_ci(parity_series, 1300 + noise_index * 13 + int(left_zeta * 1000))
            inversion_ci = bootstrap_probability_ci(inversion_series, 1400 + noise_index * 13 + int(right_zeta * 1000))

            grid_rows.append({
                "family_slug": config["family_slug"],
                "pair_name": key,
                "left_zeta": float(left_zeta),
                "right_zeta": float(right_zeta),
                "noise_std": float(noise_std),
                "noise_power": float(noise_std ** 2),
                "clean_advantage_iae": float(np.mean([row["clean_advantage_iae"] for row in rows])),
                "mean_true_gap_iae": float(np.mean(true_gap_series)),
                "ci_true_gap_iae_low": true_gap_ci["low"],
                "ci_true_gap_iae_high": true_gap_ci["high"],
                "mean_observed_gap_iae": float(np.mean(observed_gap_series)),
                "ci_observed_gap_iae_low": observed_gap_ci["low"],
                "ci_observed_gap_iae_high": observed_gap_ci["high"],
                "mean_parity_ratio_iae": float(np.mean(parity_series)),
                "ci_parity_ratio_iae_low": parity_ci["low"],
                "ci_parity_ratio_iae_high": parity_ci["high"],
                "true_winner_probability_left": float(np.mean(true_winner_series)),
                "observed_winner_probability_left": float(np.mean(observed_winner_series)),
                "inversion_probability": float(np.mean(inversion_series)),
                "ci_inversion_probability_low": inversion_ci["low"],
                "ci_inversion_probability_high": inversion_ci["high"],
            })

    return trial_rows, grid_rows


def build_summary(config, system_rows, grid_rows):
    system_map = {row["zeta"]: row for row in system_rows}
    noise_values = sorted({row["noise_std"] for row in grid_rows})
    pair_summaries = {}

    for left_zeta, right_zeta in config["pairwise_comparisons"]:
        key = pair_key(left_zeta, right_zeta)
        rows = sorted(
            [row for row in grid_rows if row["pair_name"] == key],
            key=lambda row: row["noise_std"],
        )
        true_gaps = [row["mean_true_gap_iae"] for row in rows]
        observed_gaps = [row["mean_observed_gap_iae"] for row in rows]
        parity_ratios = [row["mean_parity_ratio_iae"] for row in rows]
        inversion_probabilities = [row["inversion_probability"] for row in rows]

        observed_crossing = interpolate_zero_crossing(noise_values, observed_gaps)
        true_crossing = interpolate_zero_crossing(noise_values, true_gaps)
        pair_summaries[key] = {
            "left_zeta": float(left_zeta),
            "right_zeta": float(right_zeta),
            "clean_advantage_iae": float(rows[0]["clean_advantage_iae"]),
            "observed_zero_crossing_noise": observed_crossing,
            "true_zero_crossing_noise": true_crossing,
            "observed_crossing_precedes_true_crossing": bool(
                observed_crossing is not None and true_crossing is not None and observed_crossing < true_crossing
            ),
            "parity_ratio_at_observed_crossing": interpolate_series(noise_values, parity_ratios, observed_crossing),
            "inversion_probability_at_observed_crossing": interpolate_series(noise_values, inversion_probabilities, observed_crossing),
            "max_inversion_probability": float(max(inversion_probabilities)),
            "evidence_of_observed_inversion": bool(observed_crossing is not None),
        }

    clean_costs = [system_map[zeta]["clean_true_iae"] for zeta in config["unique_zetas"]]
    settling = [system_map[zeta]["step_settling_time_2pct"] for zeta in config["unique_zetas"]]
    bandwidths = [system_map[zeta]["bandwidth_3db"] for zeta in config["unique_zetas"]]
    deficits = [system_map[zeta]["slow_band_deficit"] for zeta in config["unique_zetas"]]
    shadows = [system_map[zeta]["shadow_mass_l2"] for zeta in config["unique_zetas"]]

    positive_pairs = [
        pair_summaries[key]
        for key in pair_summaries
        if pair_summaries[key]["observed_crossing_precedes_true_crossing"]
    ]
    strongest_pair = None
    if positive_pairs:
        strongest_pair = sorted(
            positive_pairs,
            key=lambda row: row["true_zero_crossing_noise"] - row["observed_zero_crossing_noise"],
            reverse=True,
        )[0]

    return {
        "objective": config["objective"],
        "family_slug": config["family_slug"],
        "family_label": config["family_label"],
        "pairwise_findings": pair_summaries,
        "strongest_inverting_pair": None if strongest_pair is None else pair_key(strongest_pair["left_zeta"], strongest_pair["right_zeta"]),
        "clean_rank_fidelity": {
            "settling_time_vs_clean_iae_spearman": spearman_corr(settling, clean_costs),
            "bandwidth_vs_clean_iae_spearman": spearman_corr(bandwidths, clean_costs),
            "slow_band_deficit_vs_clean_iae_spearman": spearman_corr(deficits, clean_costs),
            "shadow_mass_l2_vs_clean_iae_spearman": spearman_corr(shadows, clean_costs),
        },
        "main_claim": config["main_claim"],
        "threshold_candidate": config["threshold_candidate"],
    }


def plot_true_vs_observed(config, grid_rows, plot_dir):
    apply_plot_style()
    fig, axes = plt.subplots(1, len(config["pairwise_comparisons"]), figsize=(5.1 * len(config["pairwise_comparisons"]), 4.2))
    if len(config["pairwise_comparisons"]) == 1:
        axes = [axes]

    for ax, (left_zeta, right_zeta) in zip(axes, config["pairwise_comparisons"]):
        key = pair_key(left_zeta, right_zeta)
        rows = sorted([row for row in grid_rows if row["pair_name"] == key], key=lambda row: row["noise_std"])
        noise = np.array([row["noise_std"] for row in rows], dtype=float)
        true_gap = np.array([row["mean_true_gap_iae"] for row in rows], dtype=float)
        observed_gap = np.array([row["mean_observed_gap_iae"] for row in rows], dtype=float)
        true_low = np.array([row["ci_true_gap_iae_low"] for row in rows], dtype=float)
        true_high = np.array([row["ci_true_gap_iae_high"] for row in rows], dtype=float)
        obs_low = np.array([row["ci_observed_gap_iae_low"] for row in rows], dtype=float)
        obs_high = np.array([row["ci_observed_gap_iae_high"] for row in rows], dtype=float)

        ax.fill_between(noise, true_low, true_high, color=PAIR_COLORS[key], alpha=0.14)
        ax.fill_between(noise, obs_low, obs_high, color=NOISE_COLOR, alpha=0.18)
        ax.plot(noise, true_gap, color=PAIR_COLORS[key], linewidth=2.3, label="True gap")
        ax.plot(noise, observed_gap, color=NOISE_COLOR, linewidth=2.3, linestyle="--", label="Observed gap")
        ax.axhline(0.0, color=REFERENCE_COLOR, linewidth=1.0)
        style_panel(ax, f"{decimal_key(left_zeta)} vs {decimal_key(right_zeta)}", "Sensor noise std", "Gap (right - left) in IAE")
        add_takeaway(ax, "Dashed crosses first when the sensor metric becomes directionally wrong.", location="upper right")
        ax.legend(frameon=True, fontsize=8)

    save_figure(fig, plot_dir, f"{config['file_prefix']}_true_vs_observed.png")
    plt.close(fig)


def plot_parity_ratio(config, grid_rows, plot_dir):
    apply_plot_style()
    fig, axes = plt.subplots(1, len(config["pairwise_comparisons"]), figsize=(5.1 * len(config["pairwise_comparisons"]), 4.2))
    if len(config["pairwise_comparisons"]) == 1:
        axes = [axes]

    for ax, (left_zeta, right_zeta) in zip(axes, config["pairwise_comparisons"]):
        key = pair_key(left_zeta, right_zeta)
        rows = sorted([row for row in grid_rows if row["pair_name"] == key], key=lambda row: row["noise_std"])
        noise = np.array([row["noise_std"] for row in rows], dtype=float)
        parity = np.array([row["mean_parity_ratio_iae"] for row in rows], dtype=float)
        parity_low = np.array([row["ci_parity_ratio_iae_low"] for row in rows], dtype=float)
        parity_high = np.array([row["ci_parity_ratio_iae_high"] for row in rows], dtype=float)
        inversion_prob = np.array([row["inversion_probability"] for row in rows], dtype=float)

        ax.fill_between(noise, parity_low, parity_high, color=PAIR_COLORS[key], alpha=0.14)
        ax.plot(noise, parity, color=PAIR_COLORS[key], linewidth=2.3, label="Parity ratio")
        ax.axhline(1.0, color=REFERENCE_COLOR, linewidth=1.0, linestyle=":")
        ax2 = ax.twinx()
        ax2.plot(noise, inversion_prob, color=NOISE_COLOR, linewidth=1.6, linestyle="--", label="Inversion probability")
        ax2.set_ylim(-0.02, 1.02)
        ax2.set_ylabel("Inversion probability")
        style_panel(ax, f"{decimal_key(left_zeta)} vs {decimal_key(right_zeta)}", "Sensor noise std", "Parity ratio")
        add_takeaway(ax, "Observed inversion tends to appear before full parity is reached.", location="upper left")

    save_figure(fig, plot_dir, f"{config['file_prefix']}_parity_ratio.png")
    plt.close(fig)


def plot_winner_probability(config, grid_rows, plot_dir):
    apply_plot_style()
    fig, axes = plt.subplots(1, len(config["pairwise_comparisons"]), figsize=(5.1 * len(config["pairwise_comparisons"]), 4.2))
    if len(config["pairwise_comparisons"]) == 1:
        axes = [axes]

    for ax, (left_zeta, right_zeta) in zip(axes, config["pairwise_comparisons"]):
        key = pair_key(left_zeta, right_zeta)
        rows = sorted([row for row in grid_rows if row["pair_name"] == key], key=lambda row: row["noise_std"])
        noise = np.array([row["noise_std"] for row in rows], dtype=float)
        true_prob = np.array([row["true_winner_probability_left"] for row in rows], dtype=float)
        observed_prob = np.array([row["observed_winner_probability_left"] for row in rows], dtype=float)

        ax.plot(noise, true_prob, color=PAIR_COLORS[key], linewidth=2.3, label="True winner probability")
        ax.plot(noise, observed_prob, color=NOISE_COLOR, linewidth=2.3, linestyle="--", label="Observed winner probability")
        ax.axhline(0.5, color=REFERENCE_COLOR, linewidth=1.0, linestyle=":")
        style_panel(ax, f"{decimal_key(left_zeta)} vs {decimal_key(right_zeta)}", "Sensor noise std", "Probability left design wins")
        add_takeaway(ax, "The inversion window is where truth stays above 0.5 but observation falls below it.", location="upper right")
        ax.set_ylim(-0.02, 1.02)
        ax.legend(frameon=True, fontsize=8)

    save_figure(fig, plot_dir, f"{config['file_prefix']}_winner_probability.png")
    plt.close(fig)


def run_pid_inversion_study(config):
    run_dir = ROOT_DIR / "studies" / "occupancy-inversion-threshold" / "runs" / "latest"
    data_dir = run_dir / "data"
    plot_dir = get_plot_dir(run_dir / "plots")
    data_dir.mkdir(parents=True, exist_ok=True)

    config = {
        **config,
        "zetas": config.get("zetas", DEFAULT_ZETAS),
        "pairwise_comparisons": config.get("pairwise_comparisons", DEFAULT_PAIRS),
    }
    config["unique_zetas"] = sorted({zeta for pair in config["pairwise_comparisons"] for zeta in pair} | set(config["zetas"]))

    system_rows = build_system_rows(config)
    trial_rows, grid_rows = run_pairwise_noise_probe(config, system_rows)
    summary = build_summary(config, system_rows, grid_rows)

    system_csv = data_dir / f"{config['file_prefix']}_system_metrics.csv"
    grid_csv = data_dir / f"{config['file_prefix']}_grid.csv"
    trial_csv = data_dir / f"{config['file_prefix']}_trial_samples.csv"
    summary_json = data_dir / f"{config['file_prefix']}_summary.json"

    write_csv(system_csv, system_rows, list(system_rows[0].keys()))
    write_csv(grid_csv, grid_rows, list(grid_rows[0].keys()))
    write_csv(trial_csv, trial_rows, list(trial_rows[0].keys()))
    write_json(summary_json, summary)

    plot_true_vs_observed(config, grid_rows, plot_dir)
    plot_parity_ratio(config, grid_rows, plot_dir)
    plot_winner_probability(config, grid_rows, plot_dir)

    return {
        "system_csv": system_csv,
        "grid_csv": grid_csv,
        "trial_csv": trial_csv,
        "summary_json": summary_json,
        "summary": summary,
    }
