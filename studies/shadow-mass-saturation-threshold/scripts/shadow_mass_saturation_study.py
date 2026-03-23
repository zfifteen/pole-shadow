import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import TransferFunction, lsim


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
ZETAS = [0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.55, 0.707, 1.0]
LONG_SHADOW_ZETA = min(ZETAS)
LEVEL_ORDER = ["clean", "light", "moderate", "heavy", "extreme"]
ENVIRONMENTS = [
    {
        "name": "command_clean",
        "mode": "command",
        "level": "clean",
        "noise_std": 0.0,
        "wn_scale_range": (1.0, 1.0),
        "trials": 1,
        "seed": 4101,
    },
    {
        "name": "command_light",
        "mode": "command",
        "level": "light",
        "noise_std": 0.03,
        "wn_scale_range": (0.95, 1.05),
        "trials": 40,
        "seed": 4102,
    },
    {
        "name": "command_moderate",
        "mode": "command",
        "level": "moderate",
        "noise_std": 0.06,
        "wn_scale_range": (0.9, 1.1),
        "trials": 40,
        "seed": 4103,
    },
    {
        "name": "command_heavy",
        "mode": "command",
        "level": "heavy",
        "noise_std": 0.10,
        "wn_scale_range": (0.8, 1.2),
        "trials": 40,
        "seed": 4104,
    },
    {
        "name": "measurement_clean",
        "mode": "measurement",
        "level": "clean",
        "noise_std": 0.0,
        "wn_scale_range": (1.0, 1.0),
        "trials": 1,
        "seed": 4201,
    },
    {
        "name": "measurement_light",
        "mode": "measurement",
        "level": "light",
        "noise_std": 0.02,
        "wn_scale_range": (0.95, 1.05),
        "trials": 40,
        "seed": 4202,
    },
    {
        "name": "measurement_moderate",
        "mode": "measurement",
        "level": "moderate",
        "noise_std": 0.04,
        "wn_scale_range": (0.9, 1.1),
        "trials": 40,
        "seed": 4203,
    },
    {
        "name": "measurement_heavy",
        "mode": "measurement",
        "level": "heavy",
        "noise_std": 0.08,
        "wn_scale_range": (0.8, 1.2),
        "trials": 40,
        "seed": 4204,
    },
    {
        "name": "measurement_extreme",
        "mode": "measurement",
        "level": "extreme",
        "noise_std": 0.12,
        "wn_scale_range": (0.8, 1.2),
        "trials": 40,
        "seed": 4205,
    },
]
MODE_COLOR = {
    "command": LIGHT_SHADOW_COLOR,
    "measurement": MEMORY_COLOR,
}
LEVEL_COLOR = {
    "clean": LIGHT_SHADOW_COLOR,
    "light": "#f1a340",
    "moderate": MEMORY_COLOR,
    "heavy": FAST_COLOR,
    "extreme": NOISE_COLOR,
}


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


def summarize(values):
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(array)),
        "std": float(np.std(array)),
        "p10": float(np.percentile(array, 10)),
        "median": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)),
    }


def create_system(zeta, wn=1.0):
    return TransferFunction([wn**2], [1.0, 2.0 * zeta * wn, wn**2])


def shadow_mass_l2(zeta, wn):
    # For G(s) = wn^2 / (s^2 + 2 zeta wn s + wn^2), the H2 norm squared is wn / (4 zeta).
    return float(wn / (4.0 * zeta))


def simulate_true_iae(system, mode, noise):
    excitation = BASE_REFERENCE + noise if mode == "command" else BASE_REFERENCE - noise
    _, output, _ = lsim(system, U=excitation, T=TIME)
    output = np.asarray(output, dtype=float)
    return float(trapz(np.abs(output - BASE_REFERENCE), TIME))


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def build_clean_baseline():
    baseline = {}
    for zeta in ZETAS:
        system = create_system(zeta, 1.0)
        baseline[zeta] = simulate_true_iae(system, "command", np.zeros_like(TIME))
    return baseline


def run_environment_sweep(clean_baseline):
    trial_rows = []
    grid_rows = []
    environment_rows = []

    for env in ENVIRONMENTS:
        rng = np.random.default_rng(env["seed"])
        per_zeta = {zeta: [] for zeta in ZETAS}

        for zeta in ZETAS:
            for trial_index in range(env["trials"]):
                low, high = env["wn_scale_range"]
                wn_scale = low if low == high else float(rng.uniform(low, high))
                wn = wn_scale
                system = create_system(zeta, wn)
                noise = env["noise_std"] * rng.normal(size=len(TIME))
                true_iae = simulate_true_iae(system, env["mode"], noise)
                mass_l2 = shadow_mass_l2(zeta, wn)
                occupancy_proxy_l2 = (env["noise_std"] ** 2) * mass_l2

                row = {
                    "environment_name": env["name"],
                    "mode": env["mode"],
                    "level": env["level"],
                    "trial_index": trial_index,
                    "zeta": float(zeta),
                    "noise_std": float(env["noise_std"]),
                    "wn_scale": float(wn_scale),
                    "wn": float(wn),
                    "shadow_mass_l2": float(mass_l2),
                    "occupancy_proxy_l2": float(occupancy_proxy_l2),
                    "true_iae": float(true_iae),
                    "excess_true_iae_over_clean": float(true_iae - clean_baseline[zeta]),
                }
                trial_rows.append(row)
                per_zeta[zeta].append(row)

        summary_by_zeta = []
        for zeta in ZETAS:
            rows = per_zeta[zeta]
            iae_stats = summarize([row["true_iae"] for row in rows])
            excess_stats = summarize([row["excess_true_iae_over_clean"] for row in rows])
            mean_shadow_mass_l2 = float(np.mean([row["shadow_mass_l2"] for row in rows]))
            occupancy_proxy_l2 = (env["noise_std"] ** 2) * mean_shadow_mass_l2
            summary = {
                "environment_name": env["name"],
                "mode": env["mode"],
                "level": env["level"],
                "zeta": float(zeta),
                "noise_std": float(env["noise_std"]),
                "mean_true_iae": iae_stats["mean"],
                "std_true_iae": iae_stats["std"],
                "p10_true_iae": iae_stats["p10"],
                "median_true_iae": iae_stats["median"],
                "p90_true_iae": iae_stats["p90"],
                "mean_excess_true_iae_over_clean": excess_stats["mean"],
                "mean_shadow_mass_l2": mean_shadow_mass_l2,
                "occupancy_proxy_l2": occupancy_proxy_l2,
            }
            summary_by_zeta.append(summary)
            grid_rows.append(summary)

        best_row = min(summary_by_zeta, key=lambda row: row["mean_true_iae"])
        long_shadow_row = next(row for row in summary_by_zeta if abs(row["zeta"] - LONG_SHADOW_ZETA) < 1e-12)
        environment_rows.append({
            "environment_name": env["name"],
            "mode": env["mode"],
            "level": env["level"],
            "noise_std": float(env["noise_std"]),
            "best_zeta_by_mean_true_iae": float(best_row["zeta"]),
            "best_mean_true_iae": float(best_row["mean_true_iae"]),
            "best_shadow_mass_l2": float(best_row["mean_shadow_mass_l2"]),
            "long_shadow_zeta": float(LONG_SHADOW_ZETA),
            "long_shadow_mean_true_iae": float(long_shadow_row["mean_true_iae"]),
            "long_shadow_shadow_mass_l2": float(long_shadow_row["mean_shadow_mass_l2"]),
            "long_shadow_occupancy_proxy_l2": float(long_shadow_row["occupancy_proxy_l2"]),
            "long_shadow_gap_vs_best": float(long_shadow_row["mean_true_iae"] - best_row["mean_true_iae"]),
        })

    return trial_rows, grid_rows, environment_rows


def build_summary(clean_baseline, grid_rows, environment_rows):
    noisy_grid_rows = [row for row in grid_rows if row["noise_std"] > 0.0]
    occupancy_proxy = [row["occupancy_proxy_l2"] for row in noisy_grid_rows]
    excess_penalty = [row["mean_excess_true_iae_over_clean"] for row in noisy_grid_rows]
    noise_power = [row["noise_std"] ** 2 for row in noisy_grid_rows]
    zetas = [row["zeta"] for row in noisy_grid_rows]

    global_correlations = {
        "occupancy_proxy_l2_vs_excess_penalty_spearman": rank_spearman(occupancy_proxy, excess_penalty),
        "noise_power_vs_excess_penalty_spearman": rank_spearman(noise_power, excess_penalty),
        "zeta_vs_excess_penalty_spearman": rank_spearman(zetas, excess_penalty),
    }

    per_mode = {}
    for mode in ("command", "measurement"):
        mode_rows = [row for row in noisy_grid_rows if row["mode"] == mode]
        per_mode[mode] = {
            "occupancy_proxy_l2_vs_excess_penalty_spearman": rank_spearman(
                [row["occupancy_proxy_l2"] for row in mode_rows],
                [row["mean_excess_true_iae_over_clean"] for row in mode_rows],
            ),
            "noise_power_vs_excess_penalty_spearman": rank_spearman(
                [row["noise_std"] ** 2 for row in mode_rows],
                [row["mean_excess_true_iae_over_clean"] for row in mode_rows],
            ),
        }

    highlights = []
    for mode in ("command", "measurement"):
        mode_envs = [row for row in environment_rows if row["mode"] == mode]
        mode_envs.sort(key=lambda row: LEVEL_ORDER.index(row["level"]))
        highlights.append({
            "mode": mode,
            "clean_best_zeta": next(row["best_zeta_by_mean_true_iae"] for row in mode_envs if row["level"] == "clean"),
            "heaviest_best_zeta": mode_envs[-1]["best_zeta_by_mean_true_iae"],
            "heaviest_long_shadow_gap_vs_best": mode_envs[-1]["long_shadow_gap_vs_best"],
            "best_path": [
                {
                    "level": row["level"],
                    "noise_std": row["noise_std"],
                    "best_zeta_by_mean_true_iae": row["best_zeta_by_mean_true_iae"],
                    "best_shadow_mass_l2": row["best_shadow_mass_l2"],
                }
                for row in mode_envs
            ],
        })

    return {
        "objective": "Test whether the preferred shadow-mass budget shifts inward as noise and uncertainty increase, rather than remaining fixed at the longest-shadow design.",
        "candidate_proxy": "occupancy_proxy_l2 = noise_power * shadow_mass_l2",
        "clean_baseline_true_iae": clean_baseline,
        "global_correlations": global_correlations,
        "per_mode_correlations": per_mode,
        "environment_highlights": highlights,
    }


def plot_sweet_spot(grid_rows, environment_rows):
    fig, axs = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)
    ax_command, ax_measurement, ax_best, ax_gap = axs[0, 0], axs[0, 1], axs[1, 0], axs[1, 1]

    for mode, axis in (("command", ax_command), ("measurement", ax_measurement)):
        mode_rows = [row for row in environment_rows if row["mode"] == mode]
        mode_rows.sort(key=lambda row: LEVEL_ORDER.index(row["level"]))
        lookup = {
            (row["environment_name"], row["zeta"]): row
            for row in grid_rows
            if row["mode"] == mode
        }
        for env_row in mode_rows:
            env_name = env_row["environment_name"]
            color = LEVEL_COLOR[env_row["level"]]
            values = [lookup[(env_name, zeta)]["mean_true_iae"] for zeta in ZETAS]
            axis.plot(
                ZETAS,
                values,
                marker="o",
                lw=2.2,
                color=color,
                label=f"{env_row['level']} (best ζ={env_row['best_zeta_by_mean_true_iae']:g})",
            )
            axis.scatter(
                env_row["best_zeta_by_mean_true_iae"],
                env_row["best_mean_true_iae"],
                marker="*",
                s=160,
                color="white",
                edgecolor="#222222",
                linewidth=0.7,
                zorder=5,
            )
        style_panel(
            axis,
            f"{mode.capitalize()} nuisance: mean true IAE vs damping ratio",
            "Damping ratio ζ",
            "Mean true IAE",
        )
        axis.legend(loc="upper left")

    command_rows = [row for row in environment_rows if row["mode"] == "command"]
    measurement_rows = [row for row in environment_rows if row["mode"] == "measurement"]
    command_rows.sort(key=lambda row: LEVEL_ORDER.index(row["level"]))
    measurement_rows.sort(key=lambda row: LEVEL_ORDER.index(row["level"]))

    command_x = [LEVEL_ORDER.index(row["level"]) for row in command_rows]
    measurement_x = [LEVEL_ORDER.index(row["level"]) for row in measurement_rows]

    ax_best.plot(
        command_x,
        [row["best_zeta_by_mean_true_iae"] for row in command_rows],
        marker="o",
        lw=2.3,
        color=MODE_COLOR["command"],
        label="Command-side nuisance",
    )
    ax_best.plot(
        measurement_x,
        [row["best_zeta_by_mean_true_iae"] for row in measurement_rows],
        marker="o",
        lw=2.3,
        color=MODE_COLOR["measurement"],
        label="Measurement-side nuisance",
    )
    ax_best.set_xticks(range(len(LEVEL_ORDER)), [level.capitalize() for level in LEVEL_ORDER])
    style_panel(ax_best, "The preferred design moves inward as the environment worsens", "Environment severity ladder", "Best ζ by mean true IAE")
    ax_best.legend(loc="upper left")
    add_takeaway(ax_best, "Both nuisance channels push the optimum away\nfrom the longest-shadow design.", location="upper left")

    ax_gap.plot(
        command_x,
        [row["long_shadow_gap_vs_best"] for row in command_rows],
        marker="o",
        lw=2.3,
        color=MODE_COLOR["command"],
        label="Command-side nuisance",
    )
    ax_gap.plot(
        measurement_x,
        [row["long_shadow_gap_vs_best"] for row in measurement_rows],
        marker="o",
        lw=2.3,
        color=MODE_COLOR["measurement"],
        label="Measurement-side nuisance",
    )
    ax_gap.axhline(0.0, color=REFERENCE_COLOR, linestyle=":", lw=1.2, alpha=0.7)
    ax_gap.set_xticks(range(len(LEVEL_ORDER)), [level.capitalize() for level in LEVEL_ORDER])
    style_panel(ax_gap, "When does the longest shadow stop being best?", "Environment severity ladder", "Long-shadow penalty vs best")
    ax_gap.legend(loc="upper left")
    add_takeaway(ax_gap, "A positive gap means the longest shadow is no longer optimal.\nThe penalty grows with environmental severity.", location="upper left")

    save_figure(fig, PLOT_DIR, "shadow_mass_sweet_spot.png", dpi=280)
    plt.close(fig)


def plot_occupancy_proxy(grid_rows, environment_rows, summary):
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.4), constrained_layout=True)
    ax_scatter, ax_long_shadow = axs

    for mode in ("command", "measurement"):
        rows = [row for row in grid_rows if row["mode"] == mode and row["noise_std"] > 0.0]
        ax_scatter.scatter(
            [row["occupancy_proxy_l2"] for row in rows],
            [row["mean_excess_true_iae_over_clean"] for row in rows],
            s=56,
            alpha=0.72,
            color=MODE_COLOR[mode],
            label=f"{mode.capitalize()} nuisance",
        )
    style_panel(ax_scatter, "Candidate saturation proxy vs noise penalty", "occupancy_proxy_l2 = noise_power * shadow_mass_l2", "Mean excess true IAE over clean")
    ax_scatter.legend(loc="upper left")
    add_takeaway(
        ax_scatter,
        (
            "Global Spearman(occupancy, excess) = "
            f"{summary['global_correlations']['occupancy_proxy_l2_vs_excess_penalty_spearman']:.2f}\n"
            "This outperforms raw noise power alone."
        ),
        location="upper left",
    )

    for mode in ("command", "measurement"):
        rows = [row for row in environment_rows if row["mode"] == mode]
        rows.sort(key=lambda row: LEVEL_ORDER.index(row["level"]))
        ax_long_shadow.plot(
            [row["long_shadow_occupancy_proxy_l2"] for row in rows],
            [row["long_shadow_gap_vs_best"] for row in rows],
            marker="o",
            lw=2.3,
            color=MODE_COLOR[mode],
            label=f"{mode.capitalize()} nuisance",
        )
        for row in rows:
            ax_long_shadow.annotate(
                row["level"],
                (row["long_shadow_occupancy_proxy_l2"], row["long_shadow_gap_vs_best"]),
                textcoords="offset points",
                xytext=(4, 5),
                fontsize=8,
            )
    ax_long_shadow.axhline(0.0, color=REFERENCE_COLOR, linestyle=":", lw=1.2, alpha=0.7)
    style_panel(ax_long_shadow, "Longest-shadow design vs occupancy pressure", "Longest-shadow occupancy proxy", "Long-shadow penalty vs best")
    ax_long_shadow.legend(loc="upper left")
    add_takeaway(ax_long_shadow, "As occupancy pressure rises, the longest shadow\nturns from asset into liability.", location="upper left")

    save_figure(fig, PLOT_DIR, "shadow_mass_occupancy_proxy.png", dpi=280)
    plt.close(fig)


def main():
    apply_plot_style()
    ensure_dirs()

    clean_baseline = build_clean_baseline()
    trial_rows, grid_rows, environment_rows = run_environment_sweep(clean_baseline)
    summary = build_summary(clean_baseline, grid_rows, environment_rows)

    trial_rows.sort(key=lambda row: (row["environment_name"], row["zeta"], row["trial_index"]))
    grid_rows.sort(key=lambda row: (row["mode"], LEVEL_ORDER.index(row["level"]), row["zeta"]))
    environment_rows.sort(key=lambda row: (row["mode"], LEVEL_ORDER.index(row["level"])))

    trial_fieldnames = [
        "environment_name",
        "mode",
        "level",
        "trial_index",
        "zeta",
        "noise_std",
        "wn_scale",
        "wn",
        "shadow_mass_l2",
        "occupancy_proxy_l2",
        "true_iae",
        "excess_true_iae_over_clean",
    ]
    grid_fieldnames = [
        "environment_name",
        "mode",
        "level",
        "zeta",
        "noise_std",
        "mean_true_iae",
        "std_true_iae",
        "p10_true_iae",
        "median_true_iae",
        "p90_true_iae",
        "mean_excess_true_iae_over_clean",
        "mean_shadow_mass_l2",
        "occupancy_proxy_l2",
    ]
    environment_fieldnames = [
        "environment_name",
        "mode",
        "level",
        "noise_std",
        "best_zeta_by_mean_true_iae",
        "best_mean_true_iae",
        "best_shadow_mass_l2",
        "long_shadow_zeta",
        "long_shadow_mean_true_iae",
        "long_shadow_shadow_mass_l2",
        "long_shadow_occupancy_proxy_l2",
        "long_shadow_gap_vs_best",
    ]

    write_csv(DATA_DIR / "shadow_mass_saturation_trials.csv", trial_rows, trial_fieldnames)
    write_csv(DATA_DIR / "shadow_mass_saturation_grid.csv", grid_rows, grid_fieldnames)
    write_csv(DATA_DIR / "shadow_mass_saturation_environment_summary.csv", environment_rows, environment_fieldnames)
    write_json(DATA_DIR / "shadow_mass_saturation_summary.json", summary)

    plot_sweet_spot(grid_rows, environment_rows)
    plot_occupancy_proxy(grid_rows, environment_rows, summary)

    print("✅ Shadow-mass saturation study complete.")
    print("Files created:")
    print("   • studies/shadow-mass-saturation-threshold/runs/latest/data/shadow_mass_saturation_trials.csv")
    print("   • studies/shadow-mass-saturation-threshold/runs/latest/data/shadow_mass_saturation_grid.csv")
    print("   • studies/shadow-mass-saturation-threshold/runs/latest/data/shadow_mass_saturation_environment_summary.csv")
    print("   • studies/shadow-mass-saturation-threshold/runs/latest/data/shadow_mass_saturation_summary.json")
    print("   • studies/shadow-mass-saturation-threshold/runs/latest/plots/shadow_mass_sweet_spot.png")
    print("   • studies/shadow-mass-saturation-threshold/runs/latest/plots/shadow_mass_occupancy_proxy.png")


if __name__ == "__main__":
    main()
