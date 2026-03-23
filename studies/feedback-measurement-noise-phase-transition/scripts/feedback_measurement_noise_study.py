import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import TransferFunction, freqresp, lsim

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

TIME = np.linspace(0.0, 150.0, 2500)
BASE_REFERENCE = 0.025 * TIME + 0.7 * np.sin(0.012 * TIME)
MATCHED_ZETAS = [0.15, 0.25, 0.4, 0.55, 0.707, 1.0]
NOISE_LEVELS = [0.0, 0.02, 0.04, 0.08, 0.12, 0.16, 0.20]
TRIALS_PER_LEVEL = 60
SIGMA_TARGET = 0.5
SLOW_BAND_LIMIT = 0.05
SLOW_BAND_GRID = np.linspace(0.0, 0.25, 1200)
BANDWIDTH_GRID = np.logspace(-4, 2, 30000)
PAIRWISE_COMPARISONS = [(0.15, 0.707), (0.25, 0.707), (0.4, 0.707)]
SHOWCASE_NOISE = 0.16
SETTLING_COLOR = "#5b8c5a"


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)


def decimal_key(value):
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "_")


def rank_spearman(x_values, y_values):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    x_ranks = np.argsort(np.argsort(x))
    y_ranks = np.argsort(np.argsort(y))
    if np.std(x_ranks) == 0.0 or np.std(y_ranks) == 0.0:
        return None
    return float(np.corrcoef(x_ranks, y_ranks)[0, 1])


def create_matched_system(zeta):
    wn = SIGMA_TARGET / zeta
    system = TransferFunction([wn**2], [1.0, 2.0 * zeta * wn, wn**2])
    return system, wn


def step_settling_time(system):
    unit_step = np.ones_like(TIME)
    _, response, _ = lsim(system, U=unit_step, T=TIME)
    response = np.asarray(response, dtype=float)
    final_value = float(response[-1])
    settle_band = 0.02 * max(abs(final_value), 1e-12)
    violating = np.flatnonzero(np.abs(response - final_value) > settle_band)
    return 0.0 if len(violating) == 0 else float(TIME[violating[-1]])


def slow_band_deficit(system):
    _, response = freqresp(system, w=SLOW_BAND_GRID)
    response = np.asarray(response)
    mask = SLOW_BAND_GRID <= SLOW_BAND_LIMIT
    return float(trapz(np.abs(1.0 - response[mask]) ** 2, SLOW_BAND_GRID[mask]))


def bandwidth(system):
    _, response = freqresp(system, w=BANDWIDTH_GRID)
    magnitude = np.abs(response)
    crossing = np.where(magnitude <= 1.0 / np.sqrt(2.0))[0]
    return float(BANDWIDTH_GRID[crossing[0]]) if len(crossing) else float(BANDWIDTH_GRID[-1])


def summarize(values):
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(array)),
        "std": float(np.std(array)),
        "p10": float(np.percentile(array, 10)),
        "median": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)),
    }


def build_system_table():
    rows = []
    for zeta in MATCHED_ZETAS:
        system, wn = create_matched_system(zeta)
        _, clean_output, _ = lsim(system, U=BASE_REFERENCE, T=TIME)
        clean_output = np.asarray(clean_output, dtype=float)
        rows.append({
            "zeta": float(zeta),
            "wn": float(wn),
            "system": system,
            "clean_output": clean_output,
            "clean_true_iae": float(trapz(np.abs(clean_output - BASE_REFERENCE), TIME)),
            "step_settling_time_2pct": step_settling_time(system),
            "slow_band_deficit_0_05": slow_band_deficit(system),
            "inverse_bandwidth_3db": float(1.0 / bandwidth(system)),
        })
    return rows


def run_feedback_measurement_noise_study(system_rows):
    summary_rows = []
    trial_rows = []

    for noise_std in NOISE_LEVELS:
        rng = np.random.default_rng(230323 + int(round(noise_std * 1000)))
        per_zeta_true = {row["zeta"]: [] for row in system_rows}
        per_zeta_observed = {row["zeta"]: [] for row in system_rows}

        for trial_index in range(TRIALS_PER_LEVEL):
            measurement_noise = noise_std * rng.normal(size=len(TIME))
            trial_record = {
                "noise_std": noise_std,
                "trial_index": trial_index,
            }

            for row in system_rows:
                zeta = row["zeta"]
                system = row["system"]
                noise_to_controller = BASE_REFERENCE - measurement_noise
                _, output, _ = lsim(system, U=noise_to_controller, T=TIME)
                output = np.asarray(output, dtype=float)

                true_iae = float(trapz(np.abs(output - BASE_REFERENCE), TIME))
                observed_iae = float(trapz(np.abs((output + measurement_noise) - BASE_REFERENCE), TIME))

                per_zeta_true[zeta].append(true_iae)
                per_zeta_observed[zeta].append(observed_iae)
                trial_record[f"true_iae_zeta_{decimal_key(zeta)}"] = true_iae
                trial_record[f"observed_iae_zeta_{decimal_key(zeta)}"] = observed_iae

            trial_rows.append(trial_record)

        mean_true_by_zeta = {zeta: float(np.mean(values)) for zeta, values in per_zeta_true.items()}
        mean_observed_by_zeta = {zeta: float(np.mean(values)) for zeta, values in per_zeta_observed.items()}

        best_zeta = min(mean_true_by_zeta, key=mean_true_by_zeta.get)
        summary_rows.append({
            "noise_std": noise_std,
            "best_zeta_by_mean_true_iae": float(best_zeta),
            "slow_band_deficit_rank_fidelity": rank_spearman(
                [row["slow_band_deficit_0_05"] for row in system_rows],
                [mean_true_by_zeta[row["zeta"]] for row in system_rows],
            ),
            "inverse_bandwidth_rank_fidelity": rank_spearman(
                [row["inverse_bandwidth_3db"] for row in system_rows],
                [mean_true_by_zeta[row["zeta"]] for row in system_rows],
            ),
            "step_settling_time_rank_fidelity": rank_spearman(
                [row["step_settling_time_2pct"] for row in system_rows],
                [mean_true_by_zeta[row["zeta"]] for row in system_rows],
            ),
        })

        for row in system_rows:
            zeta = row["zeta"]
            true_stats = summarize(per_zeta_true[zeta])
            observed_stats = summarize(per_zeta_observed[zeta])
            summary_rows.append({
                "noise_std": noise_std,
                "zeta": zeta,
                "mean_true_iae": true_stats["mean"],
                "std_true_iae": true_stats["std"],
                "p10_true_iae": true_stats["p10"],
                "median_true_iae": true_stats["median"],
                "p90_true_iae": true_stats["p90"],
                "mean_observed_iae": observed_stats["mean"],
                "std_observed_iae": observed_stats["std"],
                "p10_observed_iae": observed_stats["p10"],
                "median_observed_iae": observed_stats["median"],
                "p90_observed_iae": observed_stats["p90"],
            })

    return summary_rows, trial_rows


def build_grid_rows(summary_rows):
    return [
        row for row in summary_rows
        if "zeta" in row
    ]


def build_metric_rows(summary_rows):
    return [
        row for row in summary_rows
        if "best_zeta_by_mean_true_iae" in row
    ]


def pairwise_rows(trial_rows):
    rows = []
    for noise_std in NOISE_LEVELS:
        matching_trials = [row for row in trial_rows if abs(row["noise_std"] - noise_std) < 1e-12]
        for left_zeta, right_zeta in PAIRWISE_COMPARISONS:
            left_true_key = f"true_iae_zeta_{decimal_key(left_zeta)}"
            right_true_key = f"true_iae_zeta_{decimal_key(right_zeta)}"
            left_observed_key = f"observed_iae_zeta_{decimal_key(left_zeta)}"
            right_observed_key = f"observed_iae_zeta_{decimal_key(right_zeta)}"
            rows.append({
                "noise_std": noise_std,
                "left_zeta": left_zeta,
                "right_zeta": right_zeta,
                "true_winner_probability_left": float(np.mean([
                    row[left_true_key] < row[right_true_key]
                    for row in matching_trials
                ])),
                "observed_winner_probability_left": float(np.mean([
                    row[left_observed_key] < row[right_observed_key]
                    for row in matching_trials
                ])),
            })
    return rows


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def plot_phase_transition(system_rows, grid_rows, metric_rows):
    grid_lookup = {(row["noise_std"], row["zeta"]): row for row in grid_rows}
    noise_levels = NOISE_LEVELS
    show_zetas = [0.15, 0.25, 0.4, 0.707, 1.0]
    zeta_palette = {
        0.15: LIGHT_SHADOW_COLOR,
        0.25: "#f1a340",
        0.4: MEMORY_COLOR,
        0.707: FAST_COLOR,
        1.0: NOISE_COLOR,
    }

    fig, axs = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)
    ax_lines, ax_heat, ax_metrics, ax_slices = axs[0, 0], axs[0, 1], axs[1, 0], axs[1, 1]

    for zeta in show_zetas:
        values = [grid_lookup[(noise_std, zeta)]["mean_true_iae"] for noise_std in noise_levels]
        ax_lines.plot(noise_levels, values, marker="o", lw=2.2, color=zeta_palette[zeta], label=f"ζ={zeta:g}")
    style_panel(ax_lines, "True slow-tracking cost under feedback measurement noise", "Measurement-noise standard deviation", "Mean true IAE")
    ax_lines.legend(loc="upper left")
    add_takeaway(ax_lines, "The best design moves upward in damping\nonce sensor noise enters the loop.", location="upper left")

    heat_data = np.array([
        [grid_lookup[(noise_std, zeta)]["mean_true_iae"] for noise_std in noise_levels]
        for zeta in MATCHED_ZETAS
    ])
    image = ax_heat.imshow(heat_data, aspect="auto", cmap="cividis", origin="lower")
    ax_heat.set_xticks(range(len(noise_levels)), [f"{noise_std:.2f}" for noise_std in noise_levels])
    ax_heat.set_yticks(range(len(MATCHED_ZETAS)), [f"{zeta:g}" for zeta in MATCHED_ZETAS])
    ax_heat.set_xlabel("Measurement-noise standard deviation")
    ax_heat.set_ylabel("Matched-settling damping ratio ζ")
    ax_heat.set_title("Mean true IAE heatmap")
    best_indices = []
    for noise_index, noise_std in enumerate(noise_levels):
        column = heat_data[:, noise_index]
        best_row = int(np.argmin(column))
        best_indices.append(best_row)
        ax_heat.scatter(noise_index, best_row, marker="*", s=140, color="white", edgecolor="#222222", linewidth=0.7)
    fig.colorbar(image, ax=ax_heat, fraction=0.046, pad=0.04, label="Mean true IAE")

    ax_metrics.plot(
        noise_levels,
        [row["slow_band_deficit_rank_fidelity"] for row in metric_rows],
        marker="o",
        lw=2.2,
        color=MEMORY_COLOR,
        label="Slow-band deficit",
    )
    ax_metrics.plot(
        noise_levels,
        [row["inverse_bandwidth_rank_fidelity"] for row in metric_rows],
        marker="o",
        lw=2.2,
        color=FAST_COLOR,
        label="Inverse bandwidth",
    )
    ax_metrics.plot(
        noise_levels,
        [row["step_settling_time_rank_fidelity"] for row in metric_rows],
        marker="o",
        lw=2.2,
        color=SETTLING_COLOR,
        label="Step settling time",
    )
    ax_metrics.set_ylim(-0.05, 1.05)
    style_panel(ax_metrics, "How well do fixed system metrics predict the new objective?", "Measurement-noise standard deviation", "Spearman vs mean true IAE")
    ax_metrics.legend(loc="lower right")
    add_takeaway(ax_metrics, "Slow-band deficit is best in the clean regime.\nIt stops being sufficient when the objective itself changes.", location="upper left")

    representative_levels = [0.0, 0.08, 0.16]
    representative_colors = [LIGHT_SHADOW_COLOR, MEMORY_COLOR, FAST_COLOR]
    for noise_std, color in zip(representative_levels, representative_colors):
        values = [grid_lookup[(noise_std, zeta)]["mean_true_iae"] for zeta in MATCHED_ZETAS]
        ax_slices.plot(MATCHED_ZETAS, values, marker="o", lw=2.2, color=color, label=f"noise={noise_std:.2f}")
    style_panel(ax_slices, "Cross-sections of the noise-conditioned design curve", "Damping ratio ζ", "Mean true IAE")
    ax_slices.legend(loc="upper left")
    add_takeaway(ax_slices, "The optimum drifts from ζ=0.15 toward ζ=0.4.\nThis is a real objective shift, not just metric contamination.", location="upper right")

    save_figure(fig, PLOT_DIR, "feedback_measurement_noise_phase_transition.png", dpi=280)
    plt.close(fig)


def plot_pairwise_reliability(pair_rows, trial_rows):
    fig, axs = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    pair_axes = {
        (0.15, 0.707): axs[0, 0],
        (0.25, 0.707): axs[0, 1],
        (0.4, 0.707): axs[1, 0],
    }

    for pair, axis in pair_axes.items():
        rows = [row for row in pair_rows if row["left_zeta"] == pair[0] and row["right_zeta"] == pair[1]]
        axis.plot(
            NOISE_LEVELS,
            [row["true_winner_probability_left"] for row in rows],
            marker="o",
            lw=2.3,
            color=MEMORY_COLOR,
            label="True IAE winner probability",
        )
        axis.plot(
            NOISE_LEVELS,
            [row["observed_winner_probability_left"] for row in rows],
            marker="o",
            lw=2.3,
            color=NOISE_COLOR,
            label="Observed IAE winner probability",
        )
        axis.axhline(0.5, color=REFERENCE_COLOR, linestyle=":", lw=1.2, alpha=0.7)
        style_panel(
            axis,
            f"Pairwise reliability: ζ={pair[0]:g} vs ζ={pair[1]:g}",
            "Measurement-noise standard deviation",
            "P(left design wins)",
        )
        axis.set_ylim(-0.05, 1.05)
        axis.legend(loc="lower left")

    showcase_trials = [row for row in trial_rows if abs(row["noise_std"] - SHOWCASE_NOISE) < 1e-12]
    box_labels = ["ζ=0.15", "ζ=0.25", "ζ=0.4", "ζ=0.707"]
    box_keys = [
        "observed_iae_zeta_0_15",
        "observed_iae_zeta_0_25",
        "observed_iae_zeta_0_4",
        "observed_iae_zeta_0_707",
    ]
    box_colors = [LIGHT_SHADOW_COLOR, "#f1a340", MEMORY_COLOR, FAST_COLOR]
    box_data = [[row[key] for row in showcase_trials] for key in box_keys]

    ax_box = axs[1, 1]
    boxplot = ax_box.boxplot(box_data, patch_artist=True, tick_labels=box_labels)
    for patch, color in zip(boxplot["boxes"], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.58)
    for median in boxplot["medians"]:
        median.set_color(REFERENCE_COLOR)
        median.set_linewidth(1.5)
    style_panel(ax_box, f"Observed sensor-side IAE at noise = {SHOWCASE_NOISE:.2f}", "Matched-settling design", "Observed IAE")
    add_takeaway(ax_box, "The sensor view can lag the true shift in the best design.\nThat is a different blind spot from the settling-time one.", location="upper left")

    save_figure(fig, PLOT_DIR, "feedback_measurement_noise_pairwise_reliability.png", dpi=280)
    plt.close(fig)


def main():
    apply_plot_style()
    ensure_dirs()

    system_rows = build_system_table()
    summary_rows, trial_rows = run_feedback_measurement_noise_study(system_rows)
    grid_rows = build_grid_rows(summary_rows)
    metric_rows = build_metric_rows(summary_rows)
    pair_rows = pairwise_rows(trial_rows)

    system_rows.sort(key=lambda row: row["zeta"])
    grid_rows.sort(key=lambda row: (row["noise_std"], row["zeta"]))
    metric_rows.sort(key=lambda row: row["noise_std"])
    pair_rows.sort(key=lambda row: (row["left_zeta"], row["right_zeta"], row["noise_std"]))
    trial_rows.sort(key=lambda row: (row["noise_std"], row["trial_index"]))

    system_fieldnames = [
        "zeta",
        "wn",
        "clean_true_iae",
        "step_settling_time_2pct",
        "slow_band_deficit_0_05",
        "inverse_bandwidth_3db",
    ]
    grid_fieldnames = [
        "noise_std",
        "zeta",
        "mean_true_iae",
        "std_true_iae",
        "p10_true_iae",
        "median_true_iae",
        "p90_true_iae",
        "mean_observed_iae",
        "std_observed_iae",
        "p10_observed_iae",
        "median_observed_iae",
        "p90_observed_iae",
    ]
    metric_fieldnames = [
        "noise_std",
        "best_zeta_by_mean_true_iae",
        "slow_band_deficit_rank_fidelity",
        "inverse_bandwidth_rank_fidelity",
        "step_settling_time_rank_fidelity",
    ]
    pair_fieldnames = [
        "noise_std",
        "left_zeta",
        "right_zeta",
        "true_winner_probability_left",
        "observed_winner_probability_left",
    ]
    trial_fieldnames = ["noise_std", "trial_index"]
    for prefix in ("true_iae", "observed_iae"):
        trial_fieldnames.extend([f"{prefix}_zeta_{decimal_key(zeta)}" for zeta in MATCHED_ZETAS])

    write_csv(
        DATA_DIR / "feedback_measurement_noise_system_metrics.csv",
        [{key: row[key] for key in system_fieldnames} for row in system_rows],
        system_fieldnames,
    )
    write_csv(DATA_DIR / "feedback_measurement_noise_grid.csv", grid_rows, grid_fieldnames)
    write_csv(DATA_DIR / "feedback_measurement_noise_metric_ladder.csv", metric_rows, metric_fieldnames)
    write_csv(DATA_DIR / "feedback_measurement_noise_pairwise.csv", pair_rows, pair_fieldnames)
    write_csv(DATA_DIR / "feedback_measurement_noise_trials.csv", trial_rows, trial_fieldnames)

    summary = {
        "objective": "Follow-up brainstorm experiment with true measurement noise entering the feedback path rather than the commanded input.",
        "assumption": "Closed-loop second-order transfer functions are interpreted as unity-feedback complementary sensitivities T(s), so sensor noise enters through y = T(r - n).",
        "noise_levels": NOISE_LEVELS,
        "matched_settling_family": [{key: row[key] for key in system_fieldnames} for row in system_rows],
        "metric_ladder": metric_rows,
        "pairwise_reliability": pair_rows,
        "headline_findings": {
            "clean_best_zeta": metric_rows[0]["best_zeta_by_mean_true_iae"],
            "highest_noise_best_zeta": metric_rows[-1]["best_zeta_by_mean_true_iae"],
            "highest_noise_slow_band_deficit_rank_fidelity": metric_rows[-1]["slow_band_deficit_rank_fidelity"],
            "highest_noise_step_settling_rank_fidelity": metric_rows[-1]["step_settling_time_rank_fidelity"],
        },
    }
    write_json(DATA_DIR / "feedback_measurement_noise_summary.json", summary)

    plot_phase_transition(system_rows, grid_rows, metric_rows)
    plot_pairwise_reliability(pair_rows, trial_rows)

    print("✅ Feedback measurement-noise brainstorm study complete.")
    print("Files created:")
    print("   • studies/feedback-measurement-noise-phase-transition/runs/latest/data/feedback_measurement_noise_system_metrics.csv")
    print("   • studies/feedback-measurement-noise-phase-transition/runs/latest/data/feedback_measurement_noise_grid.csv")
    print("   • studies/feedback-measurement-noise-phase-transition/runs/latest/data/feedback_measurement_noise_metric_ladder.csv")
    print("   • studies/feedback-measurement-noise-phase-transition/runs/latest/data/feedback_measurement_noise_pairwise.csv")
    print("   • studies/feedback-measurement-noise-phase-transition/runs/latest/data/feedback_measurement_noise_trials.csv")
    print("   • studies/feedback-measurement-noise-phase-transition/runs/latest/data/feedback_measurement_noise_summary.json")
    print("   • studies/feedback-measurement-noise-phase-transition/runs/latest/plots/feedback_measurement_noise_phase_transition.png")
    print("   • studies/feedback-measurement-noise-phase-transition/runs/latest/plots/feedback_measurement_noise_pairwise_reliability.png")


if __name__ == "__main__":
    main()
