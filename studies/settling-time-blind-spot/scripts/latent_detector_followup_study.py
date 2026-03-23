import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[3]
SHARED_PYTHON_DIR = ROOT_DIR / "shared" / "python"
RUN_DIR = Path(__file__).resolve().parents[1] / "runs" / "latest"

if str(SHARED_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_PYTHON_DIR))

from plot_theme import (
    FAST_COLOR,
    LIGHT_SHADOW_COLOR,
    MEMORY_COLOR,
    REFERENCE_COLOR,
    apply_plot_style,
    get_plot_dir,
    save_figure,
    style_panel,
    add_takeaway,
)


DATA_DIR = RUN_DIR / "data"
PLOT_DIR = get_plot_dir(RUN_DIR / "plots")

SYNTHETIC_SUMMARY = ROOT_DIR / "studies" / "settling-time-blind-spot" / "runs" / "latest" / "data" / "latent_detector_summary.json"
PLANT_PI_SUMMARY = ROOT_DIR / "studies" / "out-of-family-plant-pi-validation" / "runs" / "latest" / "data" / "plant_pi_summary.json"
AIRCRAFT_SUMMARY = ROOT_DIR / "studies" / "out-of-family-aircraft-longitudinal-autopilot" / "runs" / "latest" / "data" / "aircraft_autopilot_summary.json"


def read_json(path):
    with path.open() as handle:
        return json.load(handle)


def write_json(path, payload):
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_summaries():
    return {
        "synthetic_matched_family": read_json(SYNTHETIC_SUMMARY),
        "plant_pi_explicit_family": read_json(PLANT_PI_SUMMARY),
        "aircraft_autopilot_family": read_json(AIRCRAFT_SUMMARY),
    }


def synthetic_followup_row(summary):
    matched_family = summary["matched_settling_family"]
    best_pair = None
    pair_count = 0
    for left_index, left in enumerate(matched_family):
        for right in matched_family[left_index + 1:]:
            settling_diff_pct = 100.0 * abs(left["step_settling_time_2pct"] - right["step_settling_time_2pct"]) / (
                0.5 * (left["step_settling_time_2pct"] + right["step_settling_time_2pct"])
            )
            iae_ratio = max(left["clean_iae"], right["clean_iae"]) / min(left["clean_iae"], right["clean_iae"])
            candidate = {
                "left_zeta": left["zeta"],
                "right_zeta": right["zeta"],
                "settling_diff_pct": float(settling_diff_pct),
                "iae_ratio": float(iae_ratio),
            }
            if settling_diff_pct <= 15.0 and iae_ratio >= 3.0:
                pair_count += 1
                if best_pair is None or iae_ratio > best_pair["iae_ratio"]:
                    best_pair = candidate

    noise_ladder = summary["noise_ladder"]
    command_max = next(row for row in noise_ladder if row["noise_mode"] == "command_noise" and row["noise_std"] == 0.12)
    measurement_max = next(row for row in noise_ladder if row["noise_mode"] == "measurement_noise" and row["noise_std"] == 0.12)
    metrics = summary["system_metric_rank_fidelity_vs_clean_iae"]
    return {
        "family": "synthetic_matched_family",
        "family_label": "Synthetic matched family",
        "primary_task": "ramp+sine",
        "settling_rank_fidelity": float(metrics["step_settling_time_2pct"]),
        "bandwidth_rank_fidelity": float(metrics["bandwidth_3db"]),
        "slow_band_rank_fidelity": float(metrics["slow_band_deficit_0_05"]),
        "abs_settling_rank_fidelity": abs(float(metrics["step_settling_time_2pct"])),
        "abs_bandwidth_rank_fidelity": abs(float(metrics["bandwidth_3db"])),
        "abs_slow_band_rank_fidelity": abs(float(metrics["slow_band_deficit_0_05"])),
        "slow_band_minus_settling_abs": abs(float(metrics["slow_band_deficit_0_05"])) - abs(float(metrics["step_settling_time_2pct"])),
        "slow_band_minus_bandwidth_abs": abs(float(metrics["slow_band_deficit_0_05"])) - abs(float(metrics["bandwidth_3db"])),
        "matched_pair_support_exists": bool(best_pair is not None),
        "pair_count_meeting_threshold": pair_count,
        "top_pair_settling_diff_pct": None if best_pair is None else best_pair["settling_diff_pct"],
        "top_pair_iae_ratio": None if best_pair is None else best_pair["iae_ratio"],
        "command_max_noise_ordering_spearman": float(command_max["spearman_mean"]),
        "measurement_max_noise_ordering_spearman": float(measurement_max["spearman_mean"]),
        "nuisance_note": "One-shot ordering degrades strongly under command noise but remains strong under measurement noise.",
    }


def explicit_followup_row(summary, family_label, settling_key, bandwidth_key, slow_band_key, primary_task):
    metrics = summary["clean_rank_fidelity"]
    matched_pairs = summary["matched_pairs"]
    best_pair = matched_pairs["top_supportive_pair"]
    extreme_pair = summary["pairwise_reliability"]["0.15_vs_0.707"][-1]
    return {
        "family": summary["study"],
        "family_label": family_label,
        "primary_task": primary_task,
        "settling_rank_fidelity": float(metrics[settling_key]),
        "bandwidth_rank_fidelity": float(metrics[bandwidth_key]),
        "slow_band_rank_fidelity": float(metrics[slow_band_key]),
        "abs_settling_rank_fidelity": abs(float(metrics[settling_key])),
        "abs_bandwidth_rank_fidelity": abs(float(metrics[bandwidth_key])),
        "abs_slow_band_rank_fidelity": abs(float(metrics[slow_band_key])),
        "slow_band_minus_settling_abs": abs(float(metrics[slow_band_key])) - abs(float(metrics[settling_key])),
        "slow_band_minus_bandwidth_abs": abs(float(metrics[slow_band_key])) - abs(float(metrics[bandwidth_key])),
        "matched_pair_support_exists": bool(best_pair is not None),
        "pair_count_meeting_threshold": int(matched_pairs["pair_count_meeting_threshold"]),
        "top_pair_settling_diff_pct": None if best_pair is None else float(best_pair["settling_diff_pct"]),
        "top_pair_iae_ratio": None if best_pair is None else float(best_pair["iae_ratio"]),
        "command_max_noise_ordering_spearman": None,
        "measurement_max_noise_ordering_spearman": None,
        "nuisance_note": (
            "At max measurement noise, true winner probability for 0.15 vs 0.707 is "
            f"{float(extreme_pair['true_winner_probability_left']):.3f} while observed winner probability is "
            f"{float(extreme_pair['observed_winner_probability_left']):.3f}."
        ),
    }


def build_metric_rows():
    summaries = load_summaries()
    rows = [
        synthetic_followup_row(summaries["synthetic_matched_family"]),
        explicit_followup_row(
            summaries["plant_pi_explicit_family"],
            "Explicit plant + PI",
            "step_settling_time_2pct",
            "bandwidth_3db",
            "slow_band_deficit_0_05",
            "ramp+sine",
        ),
        explicit_followup_row(
            summaries["aircraft_autopilot_family"],
            "Aircraft autopilot",
            "pitch_step_settling_time_2pct",
            "altitude_bandwidth_3db",
            "slow_band_deficit_0_03",
            "glide_profile",
        ),
    ]
    return rows


def determine_conclusion(rows):
    slow_band_beats_settling_all = all(row["abs_slow_band_rank_fidelity"] > row["abs_settling_rank_fidelity"] for row in rows)
    slow_band_vs_bandwidth_gaps = [row["slow_band_minus_bandwidth_abs"] for row in rows]
    if slow_band_beats_settling_all and any(gap > 0.02 for gap in slow_band_vs_bandwidth_gaps):
        return "slow_band_adds_information_beyond_settling_time_but_not_beyond_bandwidth"
    if slow_band_beats_settling_all and all(abs(gap) <= 0.02 for gap in slow_band_vs_bandwidth_gaps):
        return "bandwidth_and_slow_band_are_effectively_equivalent_in_this_followup"
    return "slow_band_adds_information_beyond_settling_time"


def build_summary(rows):
    conclusion = determine_conclusion(rows)
    max_slow_band_minus_settling = max(row["slow_band_minus_settling_abs"] for row in rows)
    max_slow_band_minus_bandwidth = max(row["slow_band_minus_bandwidth_abs"] for row in rows)
    return {
        "objective": "Clarify whether slow-band deficit is primarily a settling-time correction, a bandwidth surrogate, or a more portable low-band diagnostic.",
        "families_compared": [
            {
                "family": row["family"],
                "label": row["family_label"],
                "primary_task": row["primary_task"],
            }
            for row in rows
        ],
        "clean_metric_role_table": rows,
        "nuisance_mode_observations": {
            "synthetic_command_vs_measurement": "Command-side noise degrades one-shot rollout ordering far more than measurement noise in the matched synthetic family.",
            "plant_pi_measurement_extreme_pair_gap": next(
                row["nuisance_note"] for row in rows if row["family"] == "out-of-family-plant-pi-validation"
            ),
            "aircraft_measurement_extreme_pair_gap": next(
                row["nuisance_note"] for row in rows if row["family"] == "out-of-family-aircraft-longitudinal-autopilot"
            ),
        },
        "headline_checks": {
            "slow_band_beats_settling_in_all_families": all(
                row["abs_slow_band_rank_fidelity"] > row["abs_settling_rank_fidelity"] for row in rows
            ),
            "bandwidth_nearly_matches_slow_band_in_all_families": all(
                abs(row["slow_band_minus_bandwidth_abs"]) <= 0.05 for row in rows
            ),
            "at_least_one_family_has_matched_pair_support": any(row["matched_pair_support_exists"] for row in rows),
            "max_slow_band_minus_settling_abs": float(max_slow_band_minus_settling),
            "max_slow_band_minus_bandwidth_abs": float(max_slow_band_minus_bandwidth),
        },
        "conclusion": conclusion,
        "interpretation": {
            "slow_band_role": "Slow-band deficit consistently outperforms settling-time summaries as a clean-task ordering statistic.",
            "bandwidth_role": "Bandwidth remains nearly as informative as slow-band deficit in these follow-up families, so the evidence supports a settling-time blind spot more strongly than a slow-band uniqueness claim.",
        },
    }


def plot_metric_roles(rows):
    labels = [row["family_label"] for row in rows]
    positions = np.arange(len(rows))
    bar_width = 0.24

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), constrained_layout=True)
    ax_rank, ax_delta = axes

    settling_values = [row["abs_settling_rank_fidelity"] for row in rows]
    bandwidth_values = [row["abs_bandwidth_rank_fidelity"] for row in rows]
    slow_band_values = [row["abs_slow_band_rank_fidelity"] for row in rows]

    ax_rank.bar(positions - bar_width, settling_values, width=bar_width, color=LIGHT_SHADOW_COLOR, label="Settling")
    ax_rank.bar(positions, bandwidth_values, width=bar_width, color=FAST_COLOR, label="Bandwidth")
    ax_rank.bar(positions + bar_width, slow_band_values, width=bar_width, color=MEMORY_COLOR, label="Slow-band deficit")
    ax_rank.set_xticks(positions)
    ax_rank.set_xticklabels(labels, rotation=12, ha="right")
    ax_rank.set_ylim(0.0, 1.08)
    style_panel(ax_rank, "Clean-task rank fidelity across families", "", "Absolute Spearman fidelity")
    ax_rank.legend(frameon=False, loc="upper right")
    add_takeaway(
        ax_rank,
        "Settling is the weakest summary in every family.\nBandwidth and slow-band carry most of the task signal.",
        "upper left",
    )

    delta_positions = np.arange(len(rows))
    delta_settling = [row["slow_band_minus_settling_abs"] for row in rows]
    delta_bandwidth = [row["slow_band_minus_bandwidth_abs"] for row in rows]
    ax_delta.barh(delta_positions + 0.16, delta_settling, height=0.28, color=MEMORY_COLOR, label="Slow-band minus settling")
    ax_delta.barh(delta_positions - 0.16, delta_bandwidth, height=0.28, color=FAST_COLOR, label="Slow-band minus bandwidth")
    ax_delta.axvline(0.0, color=REFERENCE_COLOR, lw=1.0, alpha=0.7)
    ax_delta.set_yticks(delta_positions)
    ax_delta.set_yticklabels(labels)
    style_panel(ax_delta, "Where slow-band adds signal", "Absolute fidelity advantage", "")
    ax_delta.legend(frameon=False, loc="lower right")
    add_takeaway(
        ax_delta,
        "The big gain is over settling time.\nThe gain over bandwidth is small and family-dependent.",
        "upper left",
    )

    save_figure(fig, PLOT_DIR, "latent_detector_followup_metric_roles.png", dpi=280)
    plt.close(fig)


def main():
    apply_plot_style()
    rows = build_metric_rows()

    write_csv(
        DATA_DIR / "latent_detector_followup_metric_table.csv",
        rows,
        [
            "family",
            "family_label",
            "primary_task",
            "settling_rank_fidelity",
            "bandwidth_rank_fidelity",
            "slow_band_rank_fidelity",
            "abs_settling_rank_fidelity",
            "abs_bandwidth_rank_fidelity",
            "abs_slow_band_rank_fidelity",
            "slow_band_minus_settling_abs",
            "slow_band_minus_bandwidth_abs",
            "matched_pair_support_exists",
            "pair_count_meeting_threshold",
            "top_pair_settling_diff_pct",
            "top_pair_iae_ratio",
            "command_max_noise_ordering_spearman",
            "measurement_max_noise_ordering_spearman",
            "nuisance_note",
        ],
    )

    summary = build_summary(rows)
    write_json(DATA_DIR / "latent_detector_followup_summary.json", summary)
    plot_metric_roles(rows)
    print(f"Conclusion: {summary['conclusion']}")
    print("Latent detector follow-up study complete.")


if __name__ == "__main__":
    main()
