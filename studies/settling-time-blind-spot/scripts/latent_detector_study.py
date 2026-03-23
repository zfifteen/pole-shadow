import csv
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
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

SIGMA_TARGET = 0.5
MATCHED_ZETAS = [0.15, 0.25, 0.4, 0.55, 0.707, 1.0]
NOISE_LEVELS = [0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12]
TRIALS_PER_LEVEL = 60
TIME = np.linspace(0.0, 150.0, 3000)
BASE_INPUT = 0.025 * TIME + 0.7 * np.sin(0.012 * TIME)
SLOW_BAND_LIMIT = 0.05
BANDWIDTH_GRID = np.logspace(-4, 2, 40000)
SLOW_BAND_GRID = np.linspace(0.0, 0.25, 1500)
PAIR_A = (0.15, 0.707)
PAIR_B = (0.25, 0.707)
SHOWCASE_NOISE = 0.12


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)


def decimal_key(value):
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "_")


def create_matched_system(zeta):
    wn = SIGMA_TARGET / zeta
    return TransferFunction([wn**2], [1.0, 2.0 * zeta * wn, wn**2]), wn


def spearman_corr(x_values, y_values):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    x_ranks = np.argsort(np.argsort(x))
    y_ranks = np.argsort(np.argsort(y))
    if np.std(x_ranks) == 0.0 or np.std(y_ranks) == 0.0:
        return None
    return float(np.corrcoef(x_ranks, y_ranks)[0, 1])


def percentile_summary(values):
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(array)),
        "p10": float(np.percentile(array, 10)),
        "median": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)),
    }


def step_settling_time(system, time):
    unit_step = np.ones_like(time)
    _, y, _ = lsim(system, U=unit_step, T=time)
    y = np.asarray(y, dtype=float)
    final_value = float(y[-1])
    band = 0.02 * max(abs(final_value), 1e-12)
    violating = np.flatnonzero(np.abs(y - final_value) > band)
    return 0.0 if len(violating) == 0 else float(time[violating[-1]])


def slow_band_deficit(system):
    _, response = freqresp(system, w=SLOW_BAND_GRID)
    gap = np.abs(1.0 - response) ** 2
    mask = SLOW_BAND_GRID <= SLOW_BAND_LIMIT
    return float(trapz(gap[mask], SLOW_BAND_GRID[mask]))


def bandwidth(system):
    _, response = freqresp(system, w=BANDWIDTH_GRID)
    magnitude = np.abs(response)
    crossing = np.where(magnitude <= 1.0 / np.sqrt(2.0))[0]
    return float(BANDWIDTH_GRID[crossing[0]]) if len(crossing) else float(BANDWIDTH_GRID[-1])


def iae_from_output(output, reference):
    return float(trapz(np.abs(output - reference), TIME))


def clean_system_rows():
    rows = []
    for zeta in MATCHED_ZETAS:
        system, wn = create_matched_system(zeta)
        _, y_clean, _ = lsim(system, U=BASE_INPUT, T=TIME)
        clean_iae = iae_from_output(y_clean, BASE_INPUT)
        clean_ise = float(trapz((y_clean - BASE_INPUT) ** 2, TIME))
        rows.append({
            "zeta": float(zeta),
            "wn": float(wn),
            "system": system,
            "y_clean": np.asarray(y_clean, dtype=float),
            "clean_iae": clean_iae,
            "clean_ise": clean_ise,
            "step_settling_time_2pct": step_settling_time(system, TIME),
            "slow_band_deficit_0_05": slow_band_deficit(system),
            "bandwidth_3db": bandwidth(system),
        })
    return rows


def pairwise_winner_probability(trial_rows, left_zeta, right_zeta):
    wins = [
        row[f"iae_zeta_{decimal_key(left_zeta)}"] < row[f"iae_zeta_{decimal_key(right_zeta)}"]
        for row in trial_rows
    ]
    return float(np.mean(wins))


def run_noise_study(clean_rows):
    clean_iae_by_zeta = {row["zeta"]: row["clean_iae"] for row in clean_rows}
    clean_ranking = [clean_iae_by_zeta[zeta] for zeta in MATCHED_ZETAS]
    summary_rows = []
    trial_rows = []

    for noise_mode in ("measurement_noise", "command_noise"):
        for noise_std in NOISE_LEVELS:
            rng = np.random.default_rng(20260323 + int(round(noise_std * 1000)) + (0 if noise_mode == "measurement_noise" else 10000))
            trial_spearmans = []
            mode_trial_rows = []

            for trial_index in range(TRIALS_PER_LEVEL):
                trial_record = {
                    "noise_mode": noise_mode,
                    "noise_std": noise_std,
                    "trial_index": trial_index,
                }
                observed_iaes = []

                if noise_mode == "command_noise":
                    noisy_input = BASE_INPUT + noise_std * rng.normal(size=len(TIME))

                for row in clean_rows:
                    zeta = row["zeta"]
                    key = f"iae_zeta_{decimal_key(zeta)}"

                    if noise_mode == "measurement_noise":
                        observed_output = row["y_clean"] + noise_std * rng.normal(size=len(TIME))
                        observed_iae = iae_from_output(observed_output, BASE_INPUT)
                    else:
                        _, y_noisy, _ = lsim(row["system"], U=noisy_input, T=TIME)
                        observed_iae = iae_from_output(y_noisy, noisy_input)

                    trial_record[key] = observed_iae
                    observed_iaes.append(observed_iae)

                trial_record["spearman_vs_clean_iae"] = spearman_corr(observed_iaes, clean_ranking)
                trial_spearmans.append(trial_record["spearman_vs_clean_iae"])
                mode_trial_rows.append(trial_record)

            summary = percentile_summary(trial_spearmans)
            summary_rows.append({
                "noise_mode": noise_mode,
                "noise_std": noise_std,
                "spearman_mean": summary["mean"],
                "spearman_p10": summary["p10"],
                "spearman_median": summary["median"],
                "spearman_p90": summary["p90"],
                "winner_prob_pair_a": pairwise_winner_probability(mode_trial_rows, *PAIR_A),
                "winner_prob_pair_b": pairwise_winner_probability(mode_trial_rows, *PAIR_B),
            })
            trial_rows.extend(mode_trial_rows)

    return summary_rows, trial_rows


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def plot_metric_comparison(clean_rows):
    point_colors = plt.cm.cividis(np.linspace(0.15, 0.85, len(clean_rows)))
    zetas = [row["zeta"] for row in clean_rows]
    clean_ise = [row["clean_ise"] for row in clean_rows]
    settling_times = [row["step_settling_time_2pct"] for row in clean_rows]
    slow_deficits = [row["slow_band_deficit_0_05"] for row in clean_rows]
    bandwidths = [row["bandwidth_3db"] for row in clean_rows]

    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)
    ax_settling, ax_sbd, ax_bw = axs

    ax_settling.scatter(settling_times, clean_ise, s=80, c=point_colors, edgecolor="white", linewidth=0.8)
    ax_settling.set_yscale("log")
    style_panel(ax_settling, "Matched settling vs clean slow-tracking cost", "Step settling time (s)", "Clean ramp+sine ISE")
    for zeta, x_value, y_value in zip(zetas, settling_times, clean_ise):
        ax_settling.annotate(f"ζ={zeta:g}", (x_value, y_value), xytext=(4, 4), textcoords="offset points", fontsize=8)
    add_takeaway(ax_settling, "Settling time stays clustered\nwhile clean cost spreads widely", location="upper left")

    ax_sbd.scatter(slow_deficits, clean_ise, s=80, c=point_colors, edgecolor="white", linewidth=0.8)
    ax_sbd.plot(slow_deficits, clean_ise, color=MEMORY_COLOR, lw=1.6, alpha=0.55)
    ax_sbd.set_xscale("log")
    ax_sbd.set_yscale("log")
    style_panel(ax_sbd, "Slow-band deficit vs clean slow-tracking cost", "Slow-band deficit over [0, 0.05]", "Clean ramp+sine ISE")
    for zeta, x_value, y_value in zip(zetas, slow_deficits, clean_ise):
        ax_sbd.annotate(f"ζ={zeta:g}", (x_value, y_value), xytext=(4, 4), textcoords="offset points", fontsize=8)
    add_takeaway(ax_sbd, "Low-band unity shortfall\ntracks hidden liability directly", location="upper left")

    ax_bw.scatter(bandwidths, clean_ise, s=80, c=point_colors, edgecolor="white", linewidth=0.8)
    ax_bw.plot(bandwidths, clean_ise, color=FAST_COLOR, lw=1.6, alpha=0.55)
    ax_bw.set_xscale("log")
    ax_bw.set_yscale("log")
    style_panel(ax_bw, "Bandwidth vs clean slow-tracking cost", "3 dB bandwidth (rad/s)", "Clean ramp+sine ISE")
    for zeta, x_value, y_value in zip(zetas, bandwidths, clean_ise):
        ax_bw.annotate(f"ζ={zeta:g}", (x_value, y_value), xytext=(4, 4), textcoords="offset points", fontsize=8)
    add_takeaway(ax_bw, "Bandwidth also sees this family\nso the gap is not invisible in all frequency metrics", location="upper right")

    save_figure(fig, PLOT_DIR, "latent_detector_metric_comparison.png", dpi=280)
    plt.close(fig)


def plot_noise_robustness(clean_rows, summary_rows, trial_rows):
    fig, axs = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    ax_rank, ax_pair_a = axs[0]
    ax_pair_b, ax_box = axs[1]

    modes = {
        "measurement_noise": {"label": "One-shot IAE under measurement noise", "color": LIGHT_SHADOW_COLOR},
        "command_noise": {"label": "One-shot IAE under noisy command", "color": FAST_COLOR},
    }

    for noise_mode, meta in modes.items():
        rows = [row for row in summary_rows if row["noise_mode"] == noise_mode]
        xs = [row["noise_std"] for row in rows]
        means = [row["spearman_mean"] for row in rows]
        p10 = [row["spearman_p10"] for row in rows]
        p90 = [row["spearman_p90"] for row in rows]
        ax_rank.plot(xs, means, color=meta["color"], lw=2.3, marker="o", label=meta["label"])
        ax_rank.fill_between(xs, p10, p90, color=meta["color"], alpha=0.16)

        ax_pair_a.plot(xs, [row["winner_prob_pair_a"] for row in rows], color=meta["color"], lw=2.3, marker="o", label=meta["label"])
        ax_pair_b.plot(xs, [row["winner_prob_pair_b"] for row in rows], color=meta["color"], lw=2.3, marker="o", label=meta["label"])

    ax_rank.axhline(1.0, color=MEMORY_COLOR, linestyle="--", lw=1.5, label="Slow-band deficit rank fidelity")
    style_panel(ax_rank, "How well does one noisy rollout recover clean truth?", "Noise standard deviation", "Spearman vs clean IAE ranking")
    ax_rank.set_ylim(-0.05, 1.05)
    ax_rank.legend(loc="lower left")
    add_takeaway(ax_rank, "System-side low-band metrics stay fixed.\nObserved IAE becomes a noisy estimator.", location="upper right")

    ax_pair_a.axhline(1.0, color=MEMORY_COLOR, linestyle="--", lw=1.5, label="Slow-band deficit would keep same ordering")
    ax_pair_a.axhline(0.5, color=REFERENCE_COLOR, linestyle=":", lw=1.2, alpha=0.75)
    style_panel(ax_pair_a, "Pairwise winner reliability: ζ=0.15 vs ζ=0.707", "Noise standard deviation", "P(low-mass design wins by observed IAE)")
    ax_pair_a.set_ylim(-0.05, 1.05)
    ax_pair_a.legend(loc="lower left")

    ax_pair_b.axhline(1.0, color=MEMORY_COLOR, linestyle="--", lw=1.5, label="Slow-band deficit would keep same ordering")
    ax_pair_b.axhline(0.5, color=REFERENCE_COLOR, linestyle=":", lw=1.2, alpha=0.75)
    style_panel(ax_pair_b, "Pairwise winner reliability: ζ=0.25 vs ζ=0.707", "Noise standard deviation", "P(low-mass design wins by observed IAE)")
    ax_pair_b.set_ylim(-0.05, 1.05)
    ax_pair_b.legend(loc="lower left")

    selected_rows = [
        row for row in trial_rows
        if row["noise_mode"] == "command_noise" and abs(row["noise_std"] - SHOWCASE_NOISE) < 1e-12
    ]
    box_data = []
    labels = []
    colors = []
    for zeta in (0.15, 0.25, 0.707):
        key = f"iae_zeta_{decimal_key(zeta)}"
        box_data.append([row[key] for row in selected_rows])
        labels.append(f"ζ={zeta:g}")
        colors.append(LIGHT_SHADOW_COLOR if zeta < 0.5 else FAST_COLOR)

    bp = ax_box.boxplot(box_data, patch_artist=True, tick_labels=labels)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.55)
    for median in bp["medians"]:
        median.set_color(REFERENCE_COLOR)
        median.set_linewidth(1.5)
    style_panel(ax_box, f"Observed IAE under noisy command = {SHOWCASE_NOISE:.2f}", "Matched-settling design", "One-shot observed IAE")
    add_takeaway(ax_box, "At this noise level, ζ=0.15 and ζ=0.707 overlap.\nTheir clean liabilities are not this similar.", location="upper left")

    save_figure(fig, PLOT_DIR, "latent_detector_noise_robustness.png", dpi=280)
    plt.close(fig)


def main():
    apply_plot_style()
    ensure_dirs()

    clean_rows = clean_system_rows()
    summary_rows, trial_rows = run_noise_study(clean_rows)

    clean_rows.sort(key=lambda row: row["zeta"])
    summary_rows.sort(key=lambda row: (row["noise_mode"], row["noise_std"]))
    trial_rows.sort(key=lambda row: (row["noise_mode"], row["noise_std"], row["trial_index"]))

    clean_fieldnames = [
        "zeta",
        "wn",
        "step_settling_time_2pct",
        "slow_band_deficit_0_05",
        "bandwidth_3db",
        "clean_iae",
        "clean_ise",
    ]
    summary_fieldnames = [
        "noise_mode",
        "noise_std",
        "spearman_mean",
        "spearman_p10",
        "spearman_median",
        "spearman_p90",
        "winner_prob_pair_a",
        "winner_prob_pair_b",
    ]
    trial_fieldnames = ["noise_mode", "noise_std", "trial_index", "spearman_vs_clean_iae"]
    trial_fieldnames.extend([f"iae_zeta_{decimal_key(zeta)}" for zeta in MATCHED_ZETAS])

    write_csv(DATA_DIR / "latent_detector_clean_metrics.csv", [{key: row[key] for key in clean_fieldnames} for row in clean_rows], clean_fieldnames)
    write_csv(DATA_DIR / "latent_detector_noise_ladder.csv", summary_rows, summary_fieldnames)
    write_csv(DATA_DIR / "latent_detector_trial_samples.csv", trial_rows, trial_fieldnames)

    system_metric_fidelity = {
        "step_settling_time_2pct": spearman_corr(
            [row["step_settling_time_2pct"] for row in clean_rows],
            [row["clean_iae"] for row in clean_rows],
        ),
        "slow_band_deficit_0_05": spearman_corr(
            [row["slow_band_deficit_0_05"] for row in clean_rows],
            [row["clean_iae"] for row in clean_rows],
        ),
        "bandwidth_3db": spearman_corr(
            [row["bandwidth_3db"] for row in clean_rows],
            [row["clean_iae"] for row in clean_rows],
        ),
    }

    measurement_rows = [row for row in summary_rows if row["noise_mode"] == "measurement_noise"]
    command_rows = [row for row in summary_rows if row["noise_mode"] == "command_noise"]
    report = {
        "objective": "Probe whether slow-band deficit behaves like a latent detector of low-frequency tracking liability when one-shot rollout metrics become noise-contaminated.",
        "matched_settling_family": [
            {key: row[key] for key in clean_fieldnames}
            for row in clean_rows
        ],
        "system_metric_rank_fidelity_vs_clean_iae": system_metric_fidelity,
        "noise_ladder": summary_rows,
        "headline_findings": {
            "measurement_noise_rank_fidelity_at_max_noise": measurement_rows[-1]["spearman_mean"],
            "command_noise_rank_fidelity_at_max_noise": command_rows[-1]["spearman_mean"],
            "pair_a_winner_prob_measurement_noise_max": measurement_rows[-1]["winner_prob_pair_a"],
            "pair_a_winner_prob_command_noise_max": command_rows[-1]["winner_prob_pair_a"],
            "pair_b_winner_prob_measurement_noise_max": measurement_rows[-1]["winner_prob_pair_b"],
            "pair_b_winner_prob_command_noise_max": command_rows[-1]["winner_prob_pair_b"],
        },
    }
    write_json(DATA_DIR / "latent_detector_summary.json", report)

    plot_metric_comparison(clean_rows)
    plot_noise_robustness(clean_rows, summary_rows, trial_rows)

    print("✅ Latent-detector brainstorm study complete.")
    print("Files created:")
    print("   • studies/settling-time-blind-spot/runs/latest/data/latent_detector_clean_metrics.csv")
    print("   • studies/settling-time-blind-spot/runs/latest/data/latent_detector_noise_ladder.csv")
    print("   • studies/settling-time-blind-spot/runs/latest/data/latent_detector_trial_samples.csv")
    print("   • studies/settling-time-blind-spot/runs/latest/data/latent_detector_summary.json")
    print("   • studies/settling-time-blind-spot/runs/latest/plots/latent_detector_metric_comparison.png")
    print("   • studies/settling-time-blind-spot/runs/latest/plots/latent_detector_noise_robustness.png")


if __name__ == "__main__":
    main()
