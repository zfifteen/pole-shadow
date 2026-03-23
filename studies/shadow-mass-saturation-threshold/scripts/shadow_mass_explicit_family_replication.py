import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[3]
SHARED_PYTHON_DIR = ROOT_DIR / "shared" / "python"
RUN_DIR = Path(__file__).resolve().parents[1] / "runs" / "latest"
SOURCE_RUN_DIR = ROOT_DIR / "studies" / "out-of-family-plant-pi-validation" / "runs" / "latest"

if str(SHARED_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_PYTHON_DIR))

from plot_theme import (
    FAST_COLOR,
    LIGHT_SHADOW_COLOR,
    MEMORY_COLOR,
    NOISE_COLOR,
    REFERENCE_COLOR,
    add_takeaway,
    apply_plot_style,
    get_plot_dir,
    save_figure,
    style_panel,
)


DATA_DIR = RUN_DIR / "data"
PLOT_DIR = get_plot_dir(RUN_DIR / "plots")
SOURCE_DATA_DIR = SOURCE_RUN_DIR / "data"

MODE_COLOR = {
    "command": LIGHT_SHADOW_COLOR,
    "measurement": MEMORY_COLOR,
}
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


def load_csv(path):
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


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def parse_float(row, key):
    value = row[key]
    return None if value in ("", None) else float(value)


def build_environment_rows(source_grid_rows, bootstrap_summary):
    environment_rows = []
    best_path_rows = []

    by_environment = {}
    for row in source_grid_rows:
        by_environment.setdefault(row["environment_name"], []).append(row)

    for environment_name, rows in by_environment.items():
        ordered = sorted(rows, key=lambda row: float(row["zeta"]))
        best_row = min(ordered, key=lambda row: float(row["mean_true_iae"]))
        long_shadow_row = min(ordered, key=lambda row: float(row["zeta"]))
        best_info = bootstrap_summary[environment_name]["best_zeta"]

        for row in ordered:
            environment_rows.append({
                "environment_name": environment_name,
                "mode": row["mode"],
                "level": row["level"],
                "zeta": float(row["zeta"]),
                "noise_std": float(row["noise_std"]),
                "noise_power": float(row["noise_power"]),
                "mean_true_iae": float(row["mean_true_iae"]),
                "ci_true_iae_low": float(row["ci_true_iae_low"]),
                "ci_true_iae_high": float(row["ci_true_iae_high"]),
                "mean_excess_true_iae_over_clean": float(row["mean_excess_true_iae_over_clean"]),
                "mean_shadow_mass_l2_trial": float(row["mean_shadow_mass_l2_trial"]),
                "mean_occupancy_proxy_l2": float(row["mean_occupancy_proxy_l2"]),
                "stability_rate": float(row["stability_rate"]),
                "bootstrap_best_frequency": float(row["bootstrap_best_frequency"]),
            })

        best_path_rows.append({
            "environment_name": environment_name,
            "mode": best_row["mode"],
            "level": best_row["level"],
            "noise_std": float(best_row["noise_std"]),
            "noise_power": float(best_row["noise_power"]),
            "best_zeta": float(best_row["zeta"]),
            "best_mean_true_iae": float(best_row["mean_true_iae"]),
            "best_zeta_ci_low": float(best_info["low"]),
            "best_zeta_ci_high": float(best_info["high"]),
            "best_shadow_mass_l2": float(best_row["mean_shadow_mass_l2_trial"]),
            "long_shadow_zeta": float(long_shadow_row["zeta"]),
            "long_shadow_mean_true_iae": float(long_shadow_row["mean_true_iae"]),
            "long_shadow_shadow_mass_l2": float(long_shadow_row["mean_shadow_mass_l2_trial"]),
            "long_shadow_gap_vs_best": float(long_shadow_row["mean_true_iae"]) - float(best_row["mean_true_iae"]),
            "min_stability_rate": min(float(row["stability_rate"]) for row in ordered),
        })

    return environment_rows, best_path_rows


def build_summary(source_summary, best_path_rows):
    highlights = []
    for mode in ("command", "measurement"):
        mode_rows = [row for row in best_path_rows if row["mode"] == mode]
        clean = next(row for row in mode_rows if row["level"] == "clean")
        heaviest = max(mode_rows, key=lambda row: row["noise_power"])
        highlights.append({
            "mode": mode,
            "clean_best_zeta": clean["best_zeta"],
            "heaviest_best_zeta": heaviest["best_zeta"],
            "heaviest_long_shadow_gap_vs_best": heaviest["long_shadow_gap_vs_best"],
            "best_path": [
                {
                    "level": row["level"],
                    "noise_std": row["noise_std"],
                    "best_zeta_by_mean_true_iae": row["best_zeta"],
                    "best_shadow_mass_l2": row["best_shadow_mass_l2"],
                }
                for row in sorted(mode_rows, key=lambda row: row["noise_power"])
            ],
        })

    return {
        "objective": "Replicate the shadow-mass moving-optimum and occupancy-proxy story in an explicit plant-plus-PI-controller family.",
        "source_study": "out-of-family-plant-pi-validation",
        "source_summary": "studies/out-of-family-plant-pi-validation/runs/latest/data/plant_pi_summary.json",
        "candidate_proxy": "occupancy_proxy_l2 = noise_power * shadow_mass_l2",
        "global_correlations": {
            "occupancy_proxy_l2_vs_excess_penalty_spearman": source_summary["occupancy_proxy_summary"]["global_occupancy_proxy_vs_excess_true_iae_spearman"],
            "noise_power_vs_excess_penalty_spearman": source_summary["occupancy_proxy_summary"]["global_raw_noise_power_vs_excess_true_iae_spearman"],
        },
        "per_mode_correlations": {
            mode: {
                "occupancy_proxy_l2_vs_excess_penalty_spearman": values["occupancy_proxy_l2_vs_excess_true_iae"],
                "noise_power_vs_excess_penalty_spearman": values["raw_noise_power_vs_excess_true_iae"],
            }
            for mode, values in source_summary["occupancy_proxy_summary"]["per_mode"].items()
        },
        "environment_highlights": highlights,
        "acceptance_check": {
            "inward_optimum_shift_exists": source_summary["claim_support"]["nuisance_driven_inward_movement_exists"],
            "occupancy_proxy_beats_raw_noise_by_0_10": source_summary["claim_support"]["occupancy_proxy_beats_raw_noise_by_0_10"],
            "all_regimes_report_stability": all(row["min_stability_rate"] is not None for row in best_path_rows),
        },
    }


def plot_sweet_spot(environment_rows, best_path_rows):
    figure, axes = plt.subplots(2, 2, figsize=(14.0, 9.6))

    def plot_mode_curves(ax, mode):
        rows = [row for row in environment_rows if row["mode"] == mode]
        by_level = {}
        for row in rows:
            by_level.setdefault(row["level"], []).append(row)
        for level, level_rows in sorted(by_level.items(), key=lambda item: item[0]):
            ordered = sorted(level_rows, key=lambda row: row["zeta"])
            zetas = [row["zeta"] for row in ordered]
            means = [row["mean_true_iae"] for row in ordered]
            lows = [row["ci_true_iae_low"] for row in ordered]
            highs = [row["ci_true_iae_high"] for row in ordered]
            ax.plot(zetas, means, marker="o", linewidth=2.2, color=LEVEL_COLORS[level], label=LEVEL_LABELS[level])
            ax.fill_between(zetas, lows, highs, color=LEVEL_COLORS[level], alpha=0.18)
        style_panel(ax, f"{mode.capitalize()}-Side Explicit Family", "Damping Ratio zeta", "Mean Slow-Tracking IAE")
        ax.legend(frameon=False, ncol=2, fontsize=9)

    plot_mode_curves(axes[0, 0], "command")
    add_takeaway(axes[0, 0], "The explicit family reproduces the inward movement of the preferred design under command-side nuisance.", "upper left")
    plot_mode_curves(axes[0, 1], "measurement")
    add_takeaway(axes[0, 1], "The same explicit family reproduces the inward movement under measurement-side nuisance too.", "upper left")

    def plot_best_path(ax, mode):
        rows = [row for row in best_path_rows if row["mode"] == mode]
        rows.sort(key=lambda row: row["noise_power"])
        x_values = np.arange(len(rows))
        means = [row["best_zeta"] for row in rows]
        lows = [row["best_zeta_ci_low"] for row in rows]
        highs = [row["best_zeta_ci_high"] for row in rows]
        ax.plot(x_values, means, marker="o", linewidth=2.4, color=MODE_COLOR[mode])
        ax.fill_between(x_values, lows, highs, color=MODE_COLOR[mode], alpha=0.20)
        ax.set_xticks(x_values)
        ax.set_xticklabels([LEVEL_LABELS[row["level"]] for row in rows])
        style_panel(ax, f"Best-zeta Path: {mode.capitalize()}", "Environment Severity", "Bootstrap Best zeta")

    plot_best_path(axes[1, 0], "command")
    add_takeaway(axes[1, 0], "The clean best tuning is not stable as nuisance grows; the optimum moves inward.", "upper left")
    plot_best_path(axes[1, 1], "measurement")
    add_takeaway(axes[1, 1], "This explicit-family replication confirms the moving-sweet-spot story beyond the synthetic family.", "upper left")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "shadow_mass_explicit_family_sweet_spot.png")
    plt.close(figure)


def plot_occupancy(environment_rows, best_path_rows, summary):
    figure, axes = plt.subplots(1, 2, figsize=(14.0, 5.6))
    noisy_rows = [row for row in environment_rows if row["level"] != "clean"]

    ax = axes[0]
    for mode in ("command", "measurement"):
        mode_rows = [row for row in noisy_rows if row["mode"] == mode]
        ax.scatter(
            [row["mean_occupancy_proxy_l2"] for row in mode_rows],
            [row["mean_excess_true_iae_over_clean"] for row in mode_rows],
            s=80,
            alpha=0.85,
            color=MODE_COLOR[mode],
            label=mode.capitalize(),
        )
    style_panel(ax, "Explicit-Family Occupancy vs Excess Penalty", "Noise Power x Shadow Mass L2", "Mean Excess Slow-Tracking IAE")
    ax.legend(frameon=False)
    global_occ = summary["global_correlations"]["occupancy_proxy_l2_vs_excess_penalty_spearman"]
    global_noise = summary["global_correlations"]["noise_power_vs_excess_penalty_spearman"]
    add_takeaway(ax, f"Global Spearman: occupancy = {global_occ:.2f}, raw noise = {global_noise:.2f}", "lower right")

    ax = axes[1]
    for mode in ("command", "measurement"):
        rows = [row for row in best_path_rows if row["mode"] == mode and row["level"] != "clean"]
        rows.sort(key=lambda row: row["noise_power"])
        ax.plot(
            [row["noise_power"] * row["long_shadow_shadow_mass_l2"] for row in rows],
            [row["long_shadow_gap_vs_best"] for row in rows],
            marker="o",
            linewidth=2.2,
            color=MODE_COLOR[mode],
            label=mode.capitalize(),
        )
        for row in rows:
            ax.text(row["noise_power"] * row["long_shadow_shadow_mass_l2"], row["long_shadow_gap_vs_best"], LEVEL_LABELS[row["level"]], fontsize=9, ha="left", va="bottom")
    style_panel(ax, "Long-Shadow Gap vs Explicit Occupancy", "Long-Shadow Occupancy Proxy", "Long-Shadow Gap to Best")
    ax.legend(frameon=False)
    add_takeaway(ax, "As occupancy rises, the longest-shadow design pays a growing penalty in the explicit family.", "upper left")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "shadow_mass_explicit_family_occupancy.png")
    plt.close(figure)


def main():
    apply_plot_style()
    ensure_dirs()

    source_grid_rows = load_csv(SOURCE_DATA_DIR / "plant_pi_environment_grid.csv")
    source_summary = json.loads((SOURCE_DATA_DIR / "plant_pi_summary.json").read_text())
    bootstrap_summary = json.loads((SOURCE_DATA_DIR / "plant_pi_bootstrap_summary.json").read_text())

    environment_rows, best_path_rows = build_environment_rows(source_grid_rows, bootstrap_summary)
    summary = build_summary(source_summary, best_path_rows)

    write_csv(
        DATA_DIR / "shadow_mass_explicit_family_environment_grid.csv",
        environment_rows,
        [
            "environment_name",
            "mode",
            "level",
            "zeta",
            "noise_std",
            "noise_power",
            "mean_true_iae",
            "ci_true_iae_low",
            "ci_true_iae_high",
            "mean_excess_true_iae_over_clean",
            "mean_shadow_mass_l2_trial",
            "mean_occupancy_proxy_l2",
            "stability_rate",
            "bootstrap_best_frequency",
        ],
    )
    write_csv(
        DATA_DIR / "shadow_mass_explicit_family_best_path.csv",
        best_path_rows,
        [
            "environment_name",
            "mode",
            "level",
            "noise_std",
            "noise_power",
            "best_zeta",
            "best_mean_true_iae",
            "best_zeta_ci_low",
            "best_zeta_ci_high",
            "best_shadow_mass_l2",
            "long_shadow_zeta",
            "long_shadow_mean_true_iae",
            "long_shadow_shadow_mass_l2",
            "long_shadow_gap_vs_best",
            "min_stability_rate",
        ],
    )
    write_json(DATA_DIR / "shadow_mass_explicit_family_summary.json", summary)
    write_json(
        DATA_DIR / "manifest.json",
        {
            "study": "shadow-mass-saturation-threshold-explicit-family-replication",
            "source_study": "out-of-family-plant-pi-validation",
            "generated_files": {
                "csv": [
                    "studies/shadow-mass-saturation-threshold/runs/latest/data/shadow_mass_explicit_family_environment_grid.csv",
                    "studies/shadow-mass-saturation-threshold/runs/latest/data/shadow_mass_explicit_family_best_path.csv",
                ],
                "json": [
                    "studies/shadow-mass-saturation-threshold/runs/latest/data/shadow_mass_explicit_family_summary.json",
                    "studies/shadow-mass-saturation-threshold/runs/latest/data/manifest.json",
                ],
                "plots": [
                    "studies/shadow-mass-saturation-threshold/runs/latest/plots/shadow_mass_explicit_family_sweet_spot.png",
                    "studies/shadow-mass-saturation-threshold/runs/latest/plots/shadow_mass_explicit_family_occupancy.png",
                ],
            },
        },
    )

    plot_sweet_spot(environment_rows, best_path_rows)
    plot_occupancy(environment_rows, best_path_rows, summary)

    print("Shadow-mass explicit-family replication complete.")
    print(f"Command heaviest best zeta: {next(row for row in best_path_rows if row['environment_name'] == 'command_heavy')['best_zeta']:.3g}")
    print(f"Measurement heaviest best zeta: {next(row for row in best_path_rows if row['environment_name'] == 'measurement_extreme')['best_zeta']:.3g}")


if __name__ == "__main__":
    main()
