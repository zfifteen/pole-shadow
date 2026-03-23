import csv
import importlib.util
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[3]
RUN_DIR = Path(__file__).resolve().parents[1] / "runs" / "latest"
BASE_SCRIPT = ROOT_DIR / "studies" / "out-of-family-plant-pi-validation" / "scripts" / "plant_pi_out_of_family_study.py"

spec = importlib.util.spec_from_file_location("plant_pi_base", BASE_SCRIPT)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
style_panel = base.style_panel
add_takeaway = base.add_takeaway
save_figure = base.save_figure


DATA_DIR = RUN_DIR / "data"
PLOT_DIR = base.get_plot_dir(RUN_DIR / "plots")

PAIRWISE_COMPARISONS = [(0.15, 0.707), (0.25, 0.707), (0.35, 0.707)]
UNIQUE_ZETAS = sorted({zeta for pair in PAIRWISE_COMPARISONS for zeta in pair})
NOISE_LEVELS = np.round(
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
)
TRIALS_PER_LEVEL = 180
BOOTSTRAP_SAMPLES = 400
PAIR_COLORS = {
    "0.15_vs_0.707": base.MEMORY_COLOR,
    "0.25_vs_0.707": base.FAST_COLOR,
    "0.35_vs_0.707": base.LIGHT_SHADOW_COLOR,
}


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


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
    probabilities = np.mean(array[indices], axis=1)
    return {
        "low": float(np.percentile(probabilities, 2.5)),
        "high": float(np.percentile(probabilities, 97.5)),
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


def precompute_systems():
    systems = {}
    for zeta in UNIQUE_ZETAS:
        design = base.design_pi_family(zeta)
        system, _, _, _ = base.build_closed_loop_system(design["k_p"], design["k_i"])
        clean_output = base.simulate_output(system, base.MAIN_REFERENCE)
        clean_metrics = base.tracking_metrics(clean_output, base.MAIN_REFERENCE)
        shadow = base.shadow_metrics(system)
        systems[zeta] = {
            "zeta": float(zeta),
            "system": system,
            "k_p": float(design["k_p"]),
            "k_i": float(design["k_i"]),
            "clean_iae": float(clean_metrics["iae"]),
            "clean_ise": float(clean_metrics["ise"]),
            "shadow_mass_l2": float(shadow["shadow_mass_l2"]),
        }
    return systems


def run_dense_sensor_noise_probe(systems):
    trial_rows = []
    grid_rows = []

    for noise_index, noise_std in enumerate(NOISE_LEVELS):
        rng = np.random.default_rng(920000 + noise_index)
        pair_trial_rows = {pair_key(left, right): [] for left, right in PAIRWISE_COMPARISONS}

        for trial_index in range(TRIALS_PER_LEVEL):
            noise = float(noise_std) * rng.normal(size=len(base.TIME))
            per_zeta = {}

            for zeta, system_row in systems.items():
                output = base.simulate_output(system_row["system"], base.MAIN_REFERENCE - noise)
                true_metrics = base.tracking_metrics(output, base.MAIN_REFERENCE)
                observed_metrics = base.tracking_metrics(output + noise, base.MAIN_REFERENCE)
                excess_true_iae = float(true_metrics["iae"] - system_row["clean_iae"])
                occupancy_proxy_l2 = float((noise_std ** 2) * system_row["shadow_mass_l2"])
                per_zeta[zeta] = {
                    "true_iae": float(true_metrics["iae"]),
                    "true_ise": float(true_metrics["ise"]),
                    "observed_iae": float(observed_metrics["iae"]),
                    "observed_ise": float(observed_metrics["ise"]),
                    "excess_true_iae": excess_true_iae,
                    "occupancy_proxy_l2": occupancy_proxy_l2,
                }

            for left_zeta, right_zeta in PAIRWISE_COMPARISONS:
                left = per_zeta[left_zeta]
                right = per_zeta[right_zeta]
                clean_advantage_iae = float(systems[right_zeta]["clean_iae"] - systems[left_zeta]["clean_iae"])
                clean_advantage_ise = float(systems[right_zeta]["clean_ise"] - systems[left_zeta]["clean_ise"])
                true_gap_iae = float(right["true_iae"] - left["true_iae"])
                observed_gap_iae = float(right["observed_iae"] - left["observed_iae"])
                true_gap_ise = float(right["true_ise"] - left["true_ise"])
                observed_gap_ise = float(right["observed_ise"] - left["observed_ise"])
                pairwise_excess_gap_iae = float(left["excess_true_iae"] - right["excess_true_iae"])
                parity_ratio_iae = None if clean_advantage_iae == 0.0 else float(pairwise_excess_gap_iae / clean_advantage_iae)
                occupancy_ratio = float(left["occupancy_proxy_l2"] / right["occupancy_proxy_l2"]) if right["occupancy_proxy_l2"] > 0.0 else None
                occupancy_difference = float(left["occupancy_proxy_l2"] - right["occupancy_proxy_l2"])
                observed_minus_true_gap = float(observed_gap_iae - true_gap_iae)
                inversion_event = bool(true_gap_iae > 0.0 and observed_gap_iae < 0.0)

                row = {
                    "pair_name": pair_key(left_zeta, right_zeta),
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
                    "observed_gap_ise": observed_gap_ise,
                    "pairwise_excess_gap_iae": pairwise_excess_gap_iae,
                    "parity_ratio_iae": parity_ratio_iae,
                    "left_occupancy_proxy_l2": float(left["occupancy_proxy_l2"]),
                    "right_occupancy_proxy_l2": float(right["occupancy_proxy_l2"]),
                    "occupancy_ratio": occupancy_ratio,
                    "occupancy_difference": occupancy_difference,
                    "observed_minus_true_gap": observed_minus_true_gap,
                    "true_winner_left": int(true_gap_iae > 0.0),
                    "observed_winner_left": int(observed_gap_iae > 0.0),
                    "inversion_event": int(inversion_event),
                }
                trial_rows.append(row)
                pair_trial_rows[pair_key(left_zeta, right_zeta)].append(row)

        for left_zeta, right_zeta in PAIRWISE_COMPARISONS:
            key = pair_key(left_zeta, right_zeta)
            rows = pair_trial_rows[key]
            true_gap_series = [row["true_gap_iae"] for row in rows]
            observed_gap_series = [row["observed_gap_iae"] for row in rows]
            parity_series = [row["parity_ratio_iae"] for row in rows]
            inversion_series = [row["inversion_event"] for row in rows]
            true_winner_series = [row["true_winner_left"] for row in rows]
            observed_winner_series = [row["observed_winner_left"] for row in rows]
            observed_minus_true_series = [row["observed_minus_true_gap"] for row in rows]

            true_gap_ci = bootstrap_mean_ci(true_gap_series, 1100 + noise_index * 13 + int(left_zeta * 1000))
            observed_gap_ci = bootstrap_mean_ci(observed_gap_series, 1200 + noise_index * 13 + int(right_zeta * 1000))
            parity_ci = bootstrap_mean_ci(parity_series, 1300 + noise_index * 13 + int(left_zeta * 1000))
            inversion_ci = bootstrap_probability_ci(inversion_series, 1400 + noise_index * 13 + int(right_zeta * 1000))

            grid_rows.append({
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
                "mean_observed_minus_true_gap": float(np.mean(observed_minus_true_series)),
                "true_winner_probability_left": float(np.mean(true_winner_series)),
                "observed_winner_probability_left": float(np.mean(observed_winner_series)),
                "inversion_probability": float(np.mean(inversion_series)),
                "ci_inversion_probability_low": inversion_ci["low"],
                "ci_inversion_probability_high": inversion_ci["high"],
                "mean_occupancy_ratio": None
                if not [row["occupancy_ratio"] for row in rows if row["occupancy_ratio"] is not None]
                else float(np.mean([row["occupancy_ratio"] for row in rows if row["occupancy_ratio"] is not None])),
                "mean_occupancy_difference": float(np.mean([row["occupancy_difference"] for row in rows])),
            })

    return trial_rows, grid_rows


def build_pair_summary(grid_rows):
    summaries = {}
    for left_zeta, right_zeta in PAIRWISE_COMPARISONS:
        key = pair_key(left_zeta, right_zeta)
        rows = [row for row in grid_rows if row["pair_name"] == key]
        rows.sort(key=lambda row: row["noise_std"])
        noise_values = [row["noise_std"] for row in rows]
        true_gaps = [row["mean_true_gap_iae"] for row in rows]
        observed_gaps = [row["mean_observed_gap_iae"] for row in rows]
        parity_values = [row["mean_parity_ratio_iae"] for row in rows]
        inversion_probabilities = [row["inversion_probability"] for row in rows]

        observed_crossing = interpolate_zero_crossing(noise_values, observed_gaps)
        true_crossing = interpolate_zero_crossing(noise_values, true_gaps)
        parity_at_observed_crossing = interpolate_series(noise_values, parity_values, observed_crossing)
        inversion_at_observed_crossing = interpolate_series(noise_values, inversion_probabilities, observed_crossing)

        summaries[key] = {
            "left_zeta": float(left_zeta),
            "right_zeta": float(right_zeta),
            "clean_advantage_iae": float(rows[0]["clean_advantage_iae"]),
            "observed_zero_crossing_noise": observed_crossing,
            "true_zero_crossing_noise": true_crossing,
            "observed_crossing_precedes_true_crossing": (
                observed_crossing is not None
                and true_crossing is not None
                and observed_crossing < true_crossing
            ),
            "parity_ratio_at_observed_crossing": parity_at_observed_crossing,
            "inversion_probability_at_observed_crossing": inversion_at_observed_crossing,
            "max_inversion_probability": float(max(inversion_probabilities)),
            "final_noise_true_gap_iae": float(true_gaps[-1]),
            "final_noise_observed_gap_iae": float(observed_gaps[-1]),
            "evidence_of_observed_inversion": bool(any(value < 0.0 for value in observed_gaps) and any(value > 0.0 for value in true_gaps)),
        }
    return summaries


def build_summary(systems, grid_rows):
    pair_summary = build_pair_summary(grid_rows)
    strongest_pair_name = max(
        pair_summary,
        key=lambda key: pair_summary[key]["max_inversion_probability"],
    )
    strongest_pair = pair_summary[strongest_pair_name]
    return {
        "objective": "Test whether a sensor-side design metric can invert the true ranking between competing feedback designs before the true ranking itself changes sign.",
        "family": "Explicit plant + PI controller",
        "nuisance_model": "Pure measurement noise only, no plant jitter, shared noise realization across designs within each trial.",
        "noise_ladder": {
            "start": float(NOISE_LEVELS[0]),
            "end": float(NOISE_LEVELS[-1]),
            "step": float(NOISE_LEVELS[1] - NOISE_LEVELS[0]),
            "trials_per_level": TRIALS_PER_LEVEL,
        },
        "designs": {
            decimal_key(zeta): {
                "zeta": float(zeta),
                "clean_iae": systems[zeta]["clean_iae"],
                "clean_ise": systems[zeta]["clean_ise"],
                "shadow_mass_l2": systems[zeta]["shadow_mass_l2"],
            }
            for zeta in UNIQUE_ZETAS
        },
        "pairwise_findings": pair_summary,
        "headline": {
            "strongest_inverting_pair": strongest_pair_name,
            "observed_inversion_noise": strongest_pair["observed_zero_crossing_noise"],
            "true_crossover_noise": strongest_pair["true_zero_crossing_noise"],
            "parity_ratio_at_observed_inversion": strongest_pair["parity_ratio_at_observed_crossing"],
            "observed_precedes_true": strongest_pair["observed_crossing_precedes_true_crossing"],
        },
        "interpretation": {
            "main_claim": "In the strongest pair, the sensor-side metric flips direction before the true pairwise advantage disappears.",
            "threshold_candidate": "The best current threshold variable is pairwise excess-penalty parity relative to the clean-regime advantage margin, not raw occupancy ratio alone.",
            "scope_note": "The effect is pair-specific rather than universal even within this family: the 0.15 vs 0.707 pair inverts, while the 0.25 vs 0.707 and 0.35 vs 0.707 control pairs do not within the tested ladder.",
        },
    }


def plot_true_vs_observed(grid_rows):
    figure, axes = plt.subplots(1, 3, figsize=(16.0, 4.9), constrained_layout=True, sharey=True)

    for axis, (left_zeta, right_zeta) in zip(axes, PAIRWISE_COMPARISONS):
        key = pair_key(left_zeta, right_zeta)
        rows = [row for row in grid_rows if row["pair_name"] == key]
        rows.sort(key=lambda row: row["noise_std"])
        x = [row["noise_std"] for row in rows]
        y_true = [row["mean_true_gap_iae"] for row in rows]
        y_observed = [row["mean_observed_gap_iae"] for row in rows]
        true_low = [row["ci_true_gap_iae_low"] for row in rows]
        true_high = [row["ci_true_gap_iae_high"] for row in rows]
        obs_low = [row["ci_observed_gap_iae_low"] for row in rows]
        obs_high = [row["ci_observed_gap_iae_high"] for row in rows]
        color = PAIR_COLORS[key]

        axis.fill_between(x, true_low, true_high, color=base.FAST_COLOR, alpha=0.16)
        axis.fill_between(x, obs_low, obs_high, color=color, alpha=0.16)
        axis.plot(x, y_true, color=base.FAST_COLOR, lw=2.2, label="True gap")
        axis.plot(x, y_observed, color=color, lw=2.2, linestyle="--", label="Observed gap")
        axis.axhline(0.0, color=base.REFERENCE_COLOR, lw=1.0, alpha=0.7)
        style_panel(axis, f"Pair {left_zeta:g} vs {right_zeta:g}", "Sensor noise std", "Gap (right - left) in IAE")
        if key == "0.15_vs_0.707":
            add_takeaway(axis, "The observed gap flips sign first.\nThat is the inversion signal.", "upper right")
        else:
            add_takeaway(axis, "These pairs compress but do not invert\nwithin the tested ladder.", "upper right")
        axis.legend(frameon=False, loc="lower left")

    save_figure(figure, PLOT_DIR, "occupancy_inversion_true_vs_observed.png", dpi=280)
    plt.close(figure)


def plot_parity_ratio(grid_rows, pair_summary):
    figure, axes = plt.subplots(1, 3, figsize=(16.0, 4.9), constrained_layout=True, sharey=True)

    for axis, (left_zeta, right_zeta) in zip(axes, PAIRWISE_COMPARISONS):
        key = pair_key(left_zeta, right_zeta)
        rows = [row for row in grid_rows if row["pair_name"] == key]
        rows.sort(key=lambda row: row["noise_std"])
        x = [row["noise_std"] for row in rows]
        y = [row["mean_parity_ratio_iae"] for row in rows]
        low = [row["ci_parity_ratio_iae_low"] for row in rows]
        high = [row["ci_parity_ratio_iae_high"] for row in rows]
        color = PAIR_COLORS[key]

        axis.fill_between(x, low, high, color=color, alpha=0.16)
        axis.plot(x, y, color=color, lw=2.2)
        axis.axhline(1.0, color=base.REFERENCE_COLOR, lw=1.0, linestyle="--", alpha=0.8)
        crossing = pair_summary[key]["observed_zero_crossing_noise"]
        parity_at_crossing = pair_summary[key]["parity_ratio_at_observed_crossing"]
        if crossing is not None and parity_at_crossing is not None:
            axis.scatter([crossing], [parity_at_crossing], color=base.REFERENCE_COLOR, s=35, zorder=5)
        style_panel(axis, f"Parity ratio: {left_zeta:g} vs {right_zeta:g}", "Sensor noise std", "Pairwise excess penalty / clean advantage")
        if key == "0.15_vs_0.707":
            add_takeaway(axis, "The inversion appears near parity.\nThat gives the threshold a real anchor.", "upper left")
        else:
            add_takeaway(axis, "These control pairs stay below parity,\nwhich is why they do not invert.", "upper left")

    save_figure(figure, PLOT_DIR, "occupancy_inversion_parity_ratio.png", dpi=280)
    plt.close(figure)


def plot_inversion_probability(grid_rows):
    figure, axes = plt.subplots(1, 3, figsize=(16.0, 4.9), constrained_layout=True, sharey=True)

    for axis, (left_zeta, right_zeta) in zip(axes, PAIRWISE_COMPARISONS):
        key = pair_key(left_zeta, right_zeta)
        rows = [row for row in grid_rows if row["pair_name"] == key]
        rows.sort(key=lambda row: row["noise_std"])
        x = [row["noise_std"] for row in rows]
        y_inv = [row["inversion_probability"] for row in rows]
        y_true = [row["true_winner_probability_left"] for row in rows]
        y_obs = [row["observed_winner_probability_left"] for row in rows]
        inv_low = [row["ci_inversion_probability_low"] for row in rows]
        inv_high = [row["ci_inversion_probability_high"] for row in rows]
        color = PAIR_COLORS[key]

        axis.fill_between(x, inv_low, inv_high, color=color, alpha=0.16)
        axis.plot(x, y_true, color=base.FAST_COLOR, lw=2.0, label="True winner prob")
        axis.plot(x, y_obs, color=color, lw=2.0, linestyle="--", label="Observed winner prob")
        axis.plot(x, y_inv, color=base.REFERENCE_COLOR, lw=1.8, linestyle=":", label="Inversion prob")
        axis.axhline(0.5, color=base.REFERENCE_COLOR, lw=1.0, alpha=0.45)
        style_panel(axis, f"Ranking reliability: {left_zeta:g} vs {right_zeta:g}", "Sensor noise std", "Probability")
        if key == "0.15_vs_0.707":
            add_takeaway(axis, "Observed ranking crosses below 0.5\nwhile true ranking still favors the left design.", "lower left")
        else:
            add_takeaway(axis, "Compression grows, but the observed metric\nnever becomes adversarial here.", "lower left")
        axis.legend(frameon=False, loc="upper right")

    save_figure(figure, PLOT_DIR, "occupancy_inversion_winner_probability.png", dpi=280)
    plt.close(figure)


def main():
    ensure_dirs()
    base.apply_plot_style()
    systems = precompute_systems()
    trial_rows, grid_rows = run_dense_sensor_noise_probe(systems)
    summary = build_summary(systems, grid_rows)
    pair_summary = summary["pairwise_findings"]

    write_csv(
        DATA_DIR / "occupancy_inversion_trial_samples.csv",
        trial_rows,
        [
            "pair_name",
            "left_zeta",
            "right_zeta",
            "noise_std",
            "noise_power",
            "trial_index",
            "clean_advantage_iae",
            "clean_advantage_ise",
            "true_gap_iae",
            "observed_gap_iae",
            "true_gap_ise",
            "observed_gap_ise",
            "pairwise_excess_gap_iae",
            "parity_ratio_iae",
            "left_occupancy_proxy_l2",
            "right_occupancy_proxy_l2",
            "occupancy_ratio",
            "occupancy_difference",
            "observed_minus_true_gap",
            "true_winner_left",
            "observed_winner_left",
            "inversion_event",
        ],
    )
    write_csv(
        DATA_DIR / "occupancy_inversion_grid.csv",
        grid_rows,
        [
            "pair_name",
            "left_zeta",
            "right_zeta",
            "noise_std",
            "noise_power",
            "clean_advantage_iae",
            "mean_true_gap_iae",
            "ci_true_gap_iae_low",
            "ci_true_gap_iae_high",
            "mean_observed_gap_iae",
            "ci_observed_gap_iae_low",
            "ci_observed_gap_iae_high",
            "mean_parity_ratio_iae",
            "ci_parity_ratio_iae_low",
            "ci_parity_ratio_iae_high",
            "mean_observed_minus_true_gap",
            "true_winner_probability_left",
            "observed_winner_probability_left",
            "inversion_probability",
            "ci_inversion_probability_low",
            "ci_inversion_probability_high",
            "mean_occupancy_ratio",
            "mean_occupancy_difference",
        ],
    )
    write_json(DATA_DIR / "occupancy_inversion_summary.json", summary)
    write_json(
        DATA_DIR / "manifest.json",
        {
            "study": "occupancy-inversion-threshold",
            "scripts": ["scripts/occupancy_inversion_study.py"],
            "data_files": [
                "data/occupancy_inversion_summary.json",
                "data/occupancy_inversion_grid.csv",
                "data/occupancy_inversion_trial_samples.csv",
            ],
            "plot_files": [
                "plots/occupancy_inversion_true_vs_observed.png",
                "plots/occupancy_inversion_parity_ratio.png",
                "plots/occupancy_inversion_winner_probability.png",
            ],
        },
    )

    plot_true_vs_observed(grid_rows)
    plot_parity_ratio(grid_rows, pair_summary)
    plot_inversion_probability(grid_rows)

    headline = summary["headline"]
    print(f"Strongest pair: {headline['strongest_inverting_pair']}")
    print(f"Observed inversion noise: {headline['observed_inversion_noise']}")
    print(f"True crossover noise: {headline['true_crossover_noise']}")
    print("Occupancy inversion study complete.")


if __name__ == "__main__":
    main()
