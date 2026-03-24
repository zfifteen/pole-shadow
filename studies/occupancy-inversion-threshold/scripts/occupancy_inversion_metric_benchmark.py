import csv
import importlib.util
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import TransferFunction, impulse


ROOT_DIR = Path(__file__).resolve().parents[3]
SHARED_PYTHON_DIR = ROOT_DIR / "shared" / "python"
OCCUPANCY_DIR = ROOT_DIR / "studies" / "occupancy-inversion-threshold"
PLANT_PI_SCRIPT = ROOT_DIR / "studies" / "out-of-family-plant-pi-validation" / "scripts" / "plant_pi_out_of_family_study.py"

if str(SHARED_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_PYTHON_DIR))

from plot_theme import (
    REFERENCE_COLOR,
    MEMORY_COLOR,
    FAST_COLOR,
    LIGHT_SHADOW_COLOR,
    NOISE_COLOR,
    apply_plot_style,
    get_plot_dir,
    save_figure,
    style_panel,
    add_takeaway,
)

from occupancy_inversion_pid_common import (
    phase_gain_margins,
    sensitivity_tf,
)


RUN_DIR = OCCUPANCY_DIR / "runs" / "latest"
DATA_DIR = RUN_DIR / "data"
PLOT_DIR = get_plot_dir(RUN_DIR / "plots")

spec = importlib.util.spec_from_file_location("plant_pi_base", PLANT_PI_SCRIPT)
plant_pi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plant_pi)


FAMILY_COLORS = {
    "plant_pi": MEMORY_COLOR,
    "pid_generic": FAST_COLOR,
    "powerplant_load_following": LIGHT_SHADOW_COLOR,
}


def read_csv(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def roc_auc_score(features, labels):
    positives = [feature for feature, label in zip(features, labels) if label == 1]
    negatives = [feature for feature, label in zip(features, labels) if label == 0]
    if len(positives) == 0 or len(negatives) == 0:
        return None
    wins = 0.0
    total = len(positives) * len(negatives)
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return float(wins / total)


def coeff_var(values):
    array = np.asarray(values, dtype=float)
    mean = float(np.mean(array))
    if abs(mean) < 1e-12:
        return None
    return float(np.std(array) / abs(mean))


def build_plant_pi_metrics():
    metrics = {}
    plant_denominator, _, _ = plant_pi.plant_denominator()
    for zeta in [0.15, 0.25, 0.35, 0.707]:
        design = plant_pi.design_pi_family(zeta)
        closed_loop, _, _, _ = plant_pi.build_closed_loop_system(design["k_p"], design["k_i"])
        open_loop = TransferFunction(
            [design["k_p"], design["k_i"]],
            np.convolve([1.0, 0.0], plant_denominator),
        )
        sensitivity = TransferFunction(
            np.convolve([1.0, 0.0], plant_denominator),
            closed_loop.den,
        )
        margins = phase_gain_margins(open_loop, np.logspace(-4, 3, 45000))
        time_values, signal_values = impulse(sensitivity, T=plant_pi.IMPULSE_TIME)
        sensor_noise_sensitivity_l2 = float(np.trapezoid(signal_values ** 2, time_values))
        step_metrics = plant_pi.step_response_metrics(closed_loop)
        metrics[zeta] = {
            "bandwidth_3db": plant_pi.bandwidth_3db(closed_loop),
            "step_settling_time_2pct": step_metrics["step_settling_time_2pct"],
            "phase_margin_deg": margins["phase_margin_deg"],
            "gain_margin_db": margins["gain_margin_db"],
            "sensor_noise_sensitivity_l2": sensor_noise_sensitivity_l2,
        }
    return metrics


def build_pid_metrics(path):
    rows = read_csv(path)
    metrics = {}
    for row in rows:
        zeta = float(row["zeta"])
        metrics[zeta] = {
            "bandwidth_3db": float(row["bandwidth_3db"]),
            "step_settling_time_2pct": float(row["step_settling_time_2pct"]),
            "phase_margin_deg": float(row["phase_margin_deg"]) if row["phase_margin_deg"] not in {"", "None"} else None,
            "gain_margin_db": float(row["gain_margin_db"]) if row["gain_margin_db"] not in {"", "None"} else None,
            "sensor_noise_sensitivity_l2": float(row["sensor_noise_sensitivity_l2"]),
        }
    return metrics


def normalize_metric(value):
    return None if value in {"", "None", None} else float(value)


def collect_family_rows():
    family_configs = [
        {
            "family_slug": "plant_pi",
            "summary_path": DATA_DIR / "occupancy_inversion_summary.json",
            "grid_path": DATA_DIR / "occupancy_inversion_grid.csv",
            "metrics": build_plant_pi_metrics(),
        },
        {
            "family_slug": "pid_generic",
            "summary_path": DATA_DIR / "occupancy_inversion_pid_generic_summary.json",
            "grid_path": DATA_DIR / "occupancy_inversion_pid_generic_grid.csv",
            "metrics": build_pid_metrics(DATA_DIR / "occupancy_inversion_pid_generic_system_metrics.csv"),
        },
        {
            "family_slug": "powerplant_load_following",
            "summary_path": DATA_DIR / "occupancy_inversion_load_following_summary.json",
            "grid_path": DATA_DIR / "occupancy_inversion_load_following_grid.csv",
            "metrics": build_pid_metrics(DATA_DIR / "occupancy_inversion_load_following_system_metrics.csv"),
        },
        {
            "family_slug": "missile_guidance",
            "summary_path": DATA_DIR / "occupancy_inversion_guidance_summary.json",
            "grid_path": DATA_DIR / "occupancy_inversion_guidance_grid.csv",
            "metrics": build_pid_metrics(DATA_DIR / "occupancy_inversion_guidance_system_metrics.csv"),
        },
    ]

    pair_rows = []
    point_rows = []

    for family in family_configs:
        summary = json.load(family["summary_path"].open())
        grid_rows = read_csv(family["grid_path"])
        metrics = family["metrics"]

        for pair_name, payload in summary["pairwise_findings"].items():
            left = payload["left_zeta"]
            right = payload["right_zeta"]
            left_metrics = metrics[left]
            right_metrics = metrics[right]
            pair_rows.append({
                "family_slug": family["family_slug"],
                "pair_name": pair_name,
                "left_zeta": left,
                "right_zeta": right,
                "observed_zero_crossing_noise": payload["observed_zero_crossing_noise"],
                "true_zero_crossing_noise": payload["true_zero_crossing_noise"],
                "observed_crossing_precedes_true_crossing": payload["observed_crossing_precedes_true_crossing"],
                "parity_ratio_at_observed_crossing": payload["parity_ratio_at_observed_crossing"],
                "clean_advantage_iae": payload["clean_advantage_iae"],
                "noise_power_at_observed_crossing": None
                if payload["observed_zero_crossing_noise"] is None
                else float(payload["observed_zero_crossing_noise"] ** 2),
                "normalized_noise_power_at_observed_crossing": None
                if payload["observed_zero_crossing_noise"] is None
                else float((payload["observed_zero_crossing_noise"] ** 2) / payload["clean_advantage_iae"]),
                "sensor_noise_burden_at_observed_crossing": None
                if payload["observed_zero_crossing_noise"] is None
                else float(
                    (payload["observed_zero_crossing_noise"] ** 2) * left_metrics["sensor_noise_sensitivity_l2"] / payload["clean_advantage_iae"]
                ),
                "bandwidth_ratio_left_over_right": float(left_metrics["bandwidth_3db"] / right_metrics["bandwidth_3db"]),
                "settling_diff_pct": float(
                    abs(left_metrics["step_settling_time_2pct"] - right_metrics["step_settling_time_2pct"])
                    / ((left_metrics["step_settling_time_2pct"] + right_metrics["step_settling_time_2pct"]) / 2.0)
                    * 100.0
                ),
                "phase_margin_diff_deg": None
                if left_metrics["phase_margin_deg"] is None or right_metrics["phase_margin_deg"] is None
                else float(left_metrics["phase_margin_deg"] - right_metrics["phase_margin_deg"]),
                "gain_margin_diff_db": None
                if left_metrics["gain_margin_db"] is None or right_metrics["gain_margin_db"] is None
                else float(left_metrics["gain_margin_db"] - right_metrics["gain_margin_db"]),
            })

        for row in grid_rows:
            left = float(row["left_zeta"])
            right = float(row["right_zeta"])
            left_metrics = metrics[left]
            right_metrics = metrics[right]
            true_gap = float(row["mean_true_gap_iae"])
            observed_gap = float(row["mean_observed_gap_iae"])
            point_rows.append({
                "family_slug": family["family_slug"],
                "pair_name": row["pair_name"],
                "noise_std": float(row["noise_std"]),
                "noise_power": float(row["noise_power"]),
                "clean_advantage_iae": float(row["clean_advantage_iae"]),
                "parity_ratio_iae": float(row["mean_parity_ratio_iae"]),
                "normalized_noise_power": float(row["noise_power"]) / float(row["clean_advantage_iae"]),
                "sensor_noise_burden": float(row["noise_power"]) * left_metrics["sensor_noise_sensitivity_l2"] / float(row["clean_advantage_iae"]),
                "bandwidth_ratio_left_over_right": float(left_metrics["bandwidth_3db"] / right_metrics["bandwidth_3db"]),
                "settling_diff_pct": float(
                    abs(left_metrics["step_settling_time_2pct"] - right_metrics["step_settling_time_2pct"])
                    / ((left_metrics["step_settling_time_2pct"] + right_metrics["step_settling_time_2pct"]) / 2.0)
                    * 100.0
                ),
                "phase_margin_diff_deg": None
                if left_metrics["phase_margin_deg"] is None or right_metrics["phase_margin_deg"] is None
                else float(left_metrics["phase_margin_deg"] - right_metrics["phase_margin_deg"]),
                "gain_margin_diff_db": None
                if left_metrics["gain_margin_db"] is None or right_metrics["gain_margin_db"] is None
                else float(left_metrics["gain_margin_db"] - right_metrics["gain_margin_db"]),
                "true_gap_iae": true_gap,
                "observed_gap_iae": observed_gap,
                "inversion_regime": int(true_gap > 0.0 and observed_gap < 0.0),
                "pre_crossover": int(true_gap > 0.0),
            })

    return pair_rows, point_rows


def build_summary(pair_rows, point_rows):
    positive_pairs = [row for row in pair_rows if row["observed_crossing_precedes_true_crossing"]]
    pre_crossover_rows = [row for row in point_rows if row["pre_crossover"] == 1]
    labels = [row["inversion_regime"] for row in pre_crossover_rows]

    aucs = {}
    for feature in [
        "parity_ratio_iae",
        "normalized_noise_power",
        "sensor_noise_burden",
        "bandwidth_ratio_left_over_right",
        "settling_diff_pct",
        "phase_margin_diff_deg",
        "gain_margin_diff_db",
    ]:
        feature_values = []
        feature_labels = []
        for row in pre_crossover_rows:
            value = row[feature]
            if value is None:
                continue
            feature_values.append(float(value))
            feature_labels.append(row["inversion_regime"])
        aucs[feature] = roc_auc_score(feature_values, feature_labels)

    crossing_concentration = {
        "parity_ratio_at_observed_crossing_cv": coeff_var(
            [row["parity_ratio_at_observed_crossing"] for row in positive_pairs if row["parity_ratio_at_observed_crossing"] is not None]
        ),
        "normalized_noise_power_at_observed_crossing_cv": coeff_var(
            [row["normalized_noise_power_at_observed_crossing"] for row in positive_pairs if row["normalized_noise_power_at_observed_crossing"] is not None]
        ),
        "sensor_noise_burden_at_observed_crossing_cv": coeff_var(
            [row["sensor_noise_burden_at_observed_crossing"] for row in positive_pairs if row["sensor_noise_burden_at_observed_crossing"] is not None]
        ),
    }

    return {
        "objective": "Compare the inversion-threshold candidate against standard noise-sensitivity and robustness summaries across the current positive families.",
        "positive_pair_count": len(positive_pairs),
        "positive_pairs": positive_pairs,
        "pre_crossover_point_count": len(pre_crossover_rows),
        "inversion_regime_auc": aucs,
        "crossing_concentration": crossing_concentration,
        "main_readout": "Parity ratio should outperform raw noise-power summaries on inversion-regime detection and should cluster more tightly at observed crossing than standard summaries.",
    }


def plot_auc_benchmark(summary, plot_dir):
    apply_plot_style()
    aucs = summary["inversion_regime_auc"]
    labels = [
        "parity_ratio_iae",
        "sensor_noise_burden",
        "normalized_noise_power",
        "bandwidth_ratio_left_over_right",
        "settling_diff_pct",
        "phase_margin_diff_deg",
        "gain_margin_diff_db",
    ]
    display = [
        "Parity ratio",
        "Sensor-noise burden",
        "Noise power",
        "Bandwidth ratio",
        "Settling diff",
        "Phase margin diff",
        "Gain margin diff",
    ]
    values = [0.5 if aucs[label] is None else aucs[label] for label in labels]
    colors = [MEMORY_COLOR, FAST_COLOR, LIGHT_SHADOW_COLOR, NOISE_COLOR, NOISE_COLOR, NOISE_COLOR, NOISE_COLOR]

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.bar(display, values, color=colors, alpha=0.88)
    ax.axhline(0.5, color=REFERENCE_COLOR, linewidth=1.0, linestyle=":")
    ax.set_ylim(0.45, 1.0)
    style_panel(ax, "Inversion-Regime Detection AUC", "Candidate metric", "AUC on pre-crossover points")
    add_takeaway(ax, "Higher AUC means the metric separates honest from adversarial sensor regimes more cleanly.", location="upper left")
    plt.xticks(rotation=22, ha="right")
    save_figure(fig, plot_dir, "occupancy_inversion_metric_benchmark_auc.png")
    plt.close(fig)


def plot_crossing_concentration(summary, plot_dir):
    apply_plot_style()
    concentration = summary["crossing_concentration"]
    labels = [
        "parity_ratio_at_observed_crossing_cv",
        "sensor_noise_burden_at_observed_crossing_cv",
        "normalized_noise_power_at_observed_crossing_cv",
    ]
    display = ["Parity ratio", "Sensor-noise burden", "Noise power"]
    values = [concentration[label] for label in labels]
    colors = [MEMORY_COLOR, FAST_COLOR, LIGHT_SHADOW_COLOR]

    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    ax.bar(display, values, color=colors, alpha=0.9)
    style_panel(ax, "Observed-Crossing Concentration", "Candidate threshold", "Coefficient of variation across positive pairs")
    add_takeaway(ax, "Lower spread means the threshold travels more consistently across families.", location="upper right")
    save_figure(fig, plot_dir, "occupancy_inversion_metric_benchmark_crossing_cv.png")
    plt.close(fig)


def main():
    pair_rows, point_rows = collect_family_rows()
    summary = build_summary(pair_rows, point_rows)

    pair_csv = DATA_DIR / "occupancy_inversion_metric_benchmark_pairs.csv"
    point_csv = DATA_DIR / "occupancy_inversion_metric_benchmark_points.csv"
    summary_json = DATA_DIR / "occupancy_inversion_metric_benchmark_summary.json"

    write_csv(pair_csv, pair_rows, list(pair_rows[0].keys()))
    write_csv(point_csv, point_rows, list(point_rows[0].keys()))
    write_json(summary_json, summary)

    plot_auc_benchmark(summary, PLOT_DIR)
    plot_crossing_concentration(summary, PLOT_DIR)


if __name__ == "__main__":
    main()
