import csv
import importlib.util
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize


ROOT_DIR = Path(__file__).resolve().parents[3]
RUN_DIR = Path(__file__).resolve().parents[1] / "runs" / "latest"
BASE_SCRIPT = Path(__file__).resolve().parents[0] / "aircraft_longitudinal_autopilot_study.py"
BASE_DATA_DIR = Path(__file__).resolve().parents[1] / "runs" / "latest" / "data"

spec = importlib.util.spec_from_file_location("aircraft_baseline", BASE_SCRIPT)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
style_panel = base.style_panel
add_takeaway = base.add_takeaway
save_figure = base.save_figure


DATA_DIR = RUN_DIR / "data"
PLOT_DIR = base.get_plot_dir(RUN_DIR / "plots")
VARIANT_GUST_TAU = 8.0
VARIANT_REFERENCE = -1.5 * base.TIME + 60.0 * np.sin(0.006 * base.TIME)
PAIRWISE_COMPARISONS = [(0.15, 0.707), (0.25, 0.707), (0.35, 0.707)]
BOOTSTRAP_SAMPLES = 400


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


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


def load_baseline_family():
    rows = load_csv(BASE_DATA_DIR / "aircraft_autopilot_system_metrics.csv")
    family = []
    for row in rows:
        family.append({
            "zeta": float(row["zeta"]),
            "k_theta": float(row["k_theta"]),
            "k_i_theta": float(row["k_i_theta"]),
            "k_q": float(row["k_q"]),
            "k_h": float(row["k_h"]),
            "k_i_h": float(row["k_i_h"]),
            "pitch_step_settling_time_2pct": float(row["pitch_step_settling_time_2pct"]),
            "pitch_step_overshoot": float(row["pitch_step_overshoot"]),
            "pitch_bandwidth_3db": float(row["pitch_bandwidth_3db"]),
        })
    family.sort(key=lambda row: row["zeta"])
    return family


def variant_inner_objective(log_scales, baseline_row, a_matrix, b_matrix, target_settling, target_overshoot):
    scales = np.exp(log_scales)
    k_theta = baseline_row["k_theta"] * scales[0]
    k_i_theta = baseline_row["k_i_theta"] * scales[1]
    k_q = baseline_row["k_q"] * scales[2]
    a_inner, b_inner, c_inner, d_inner = base.build_inner_loop_state_space(k_theta, k_i_theta, k_q, a_matrix, b_matrix)
    eigenvalues = np.linalg.eigvals(a_inner)
    if np.any(np.real(eigenvalues) >= 0.0):
        return 1e9

    metrics = base.step_response_metrics(a_inner, b_inner, c_inner, d_inner, amplitude=1.0, time=np.linspace(0.0, 40.0, 1500))
    settling_penalty = (metrics["settling_time_2pct"] - target_settling) ** 2 * 24.0
    overshoot_penalty = (metrics["overshoot"] - target_overshoot) ** 2 * 60.0
    final_penalty = (metrics["final_value"] - 1.0) ** 2 * 120.0
    scale_penalty = 0.35 * np.sum(np.square(log_scales))
    stability_penalty = sum(max(np.real(pole) + 0.03, 0.0) ** 2 * 400.0 for pole in eigenvalues)
    return settling_penalty + overshoot_penalty + final_penalty + scale_penalty + stability_penalty


def retune_inner_family(baseline_family):
    a_nominal, b_nominal = base.build_jittered_matrices()
    target_settling = float(np.median([row["pitch_step_settling_time_2pct"] for row in baseline_family]))
    target_overshoot = float(np.median([row["pitch_step_overshoot"] for row in baseline_family]))

    tuned_family = []
    for row in baseline_family:
        result = minimize(
            lambda log_scales: variant_inner_objective(log_scales, row, a_nominal, b_nominal, target_settling, target_overshoot),
            np.zeros(3, dtype=float),
            method="Nelder-Mead",
            options={"maxiter": 220, "xatol": 1e-4, "fatol": 1e-4},
        )
        scales = np.exp(result.x)
        k_theta = row["k_theta"] * scales[0]
        k_i_theta = row["k_i_theta"] * scales[1]
        k_q = row["k_q"] * scales[2]
        a_inner, b_inner, c_inner, d_inner = base.build_inner_loop_state_space(k_theta, k_i_theta, k_q, a_nominal, b_nominal)
        pitch_step = base.step_response_metrics(a_inner, b_inner, c_inner, d_inner, amplitude=1.0, time=np.linspace(0.0, 40.0, 1500))
        pitch_bandwidth = base.bandwidth_3db(a_inner, b_inner, c_inner, d_inner)
        outer = base.tune_outer_loop(
            {
                "k_theta": k_theta,
                "k_i_theta": k_i_theta,
                "k_q": k_q,
                "pitch_bandwidth_3db": pitch_bandwidth,
            },
            a_nominal,
            b_nominal,
        )
        tuned_family.append({
            "zeta": row["zeta"],
            "k_theta": float(k_theta),
            "k_i_theta": float(k_i_theta),
            "k_q": float(k_q),
            "k_h": float(outer["k_h"]),
            "k_i_h": float(outer["k_i_h"]),
            "pitch_step_settling_time_2pct": float(pitch_step["settling_time_2pct"]),
            "pitch_step_overshoot": float(pitch_step["overshoot"]),
            "retune_residual": float(result.fun),
        })
    return tuned_family


def simulate_variant(gains, reference_signal, environment, trial_rng, a_matrix, b_matrix):
    measurement_noise = np.zeros_like(base.TIME)
    command_noise = np.zeros_like(base.TIME)
    if environment["measurement_noise_std"] > 0.0:
        measurement_noise = environment["measurement_noise_std"] * trial_rng.normal(size=len(base.TIME))
    if environment["command_noise_std"] > 0.0:
        command_noise = environment["command_noise_std"] * trial_rng.normal(size=len(base.TIME))
    gust_signal = base.generate_filtered_noise(environment["gust_std"], VARIANT_GUST_TAU, trial_rng)
    return base.simulate_closed_loop(
        gains,
        reference_signal,
        measurement_noise=measurement_noise,
        command_noise=command_noise,
        gust_signal=gust_signal,
        a_matrix=a_matrix,
        b_matrix=b_matrix,
    )


def run_variant_sweep(tuned_family):
    clean_iae = {}
    environment_grid_rows = []
    pairwise_rows = []

    family_lookup = {
        row["zeta"]: {
            "k_theta": row["k_theta"],
            "k_i_theta": row["k_i_theta"],
            "k_q": row["k_q"],
            "k_h": row["k_h"],
            "k_i_h": row["k_i_h"],
        }
        for row in tuned_family
    }

    a_nominal, b_nominal = base.build_jittered_matrices()
    for row in tuned_family:
        sim = base.simulate_closed_loop(family_lookup[row["zeta"]], VARIANT_REFERENCE, a_matrix=a_nominal, b_matrix=b_nominal)
        clean_iae[row["zeta"]] = sim["metrics"]["true_iae"]

    for environment in base.ENVIRONMENTS:
        rng = np.random.default_rng(environment["seed"] + 5000)
        scenarios = []
        per_zeta = {row["zeta"]: [] for row in tuned_family}

        for trial_index in range(environment["trials"]):
            jitter = environment["jitter_pct"]
            short_scale = 1.0 if jitter == 0.0 else float(rng.uniform(1.0 - jitter, 1.0 + jitter))
            phugoid_scale = 1.0 if jitter == 0.0 else float(rng.uniform(1.0 - jitter, 1.0 + jitter))
            control_scale = 1.0 if jitter == 0.0 else float(rng.uniform(1.0 - jitter, 1.0 + jitter))
            a_trial, b_trial = base.build_jittered_matrices(short_scale, phugoid_scale, control_scale)
            scenario = {
                "environment_name": environment["name"],
                "mode": environment["mode"],
                "level": environment["level"],
                "noise_std": environment["measurement_noise_std"] if environment["mode"] == "measurement" else environment["command_noise_std"],
                "per_zeta": {},
            }

            for row in tuned_family:
                zeta = row["zeta"]
                sim = simulate_variant(family_lookup[zeta], VARIANT_REFERENCE, environment, rng, a_trial, b_trial)
                stable = sim is not None
                if stable:
                    metrics = sim["metrics"]
                    c_altitude = np.array([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]], dtype=float)
                    input_ref = sim["input_matrix"][:, [0]]
                    shadow_mass = base.shadow_mass_l2(sim["full_state_matrix"], input_ref, c_altitude)
                    nuisance_power = (
                        environment["command_noise_std"] ** 2 + environment["gust_std"] ** 2
                        if environment["mode"] == "command"
                        else environment["measurement_noise_std"] ** 2 + environment["gust_std"] ** 2
                    )
                    record = {
                        "zeta": zeta,
                        "stability_flag": 1,
                        "true_iae": metrics["true_iae"],
                        "observed_iae": metrics["observed_iae"] if environment["mode"] == "measurement" else None,
                        "excess_true_iae_over_clean": metrics["true_iae"] - clean_iae[zeta],
                        "occupancy_proxy_l2": nuisance_power * shadow_mass,
                        "nuisance_power": nuisance_power,
                    }
                else:
                    record = {
                        "zeta": zeta,
                        "stability_flag": 0,
                        "true_iae": None,
                        "observed_iae": None,
                        "excess_true_iae_over_clean": None,
                        "occupancy_proxy_l2": None,
                        "nuisance_power": (
                            environment["command_noise_std"] ** 2 + environment["gust_std"] ** 2
                            if environment["mode"] == "command"
                            else environment["measurement_noise_std"] ** 2 + environment["gust_std"] ** 2
                        ),
                    }
                per_zeta[zeta].append(record)
                scenario["per_zeta"][zeta] = record
            scenarios.append(scenario)

        for row in tuned_family:
            zeta = row["zeta"]
            valid = [entry for entry in per_zeta[zeta] if entry["stability_flag"] == 1]
            environment_grid_rows.append({
                "environment_name": environment["name"],
                "mode": environment["mode"],
                "level": environment["level"],
                "noise_std": float(environment["measurement_noise_std"] if environment["mode"] == "measurement" else environment["command_noise_std"]),
                "gust_std": float(environment["gust_std"]),
                "zeta": float(zeta),
                "mean_true_iae": float(np.mean([entry["true_iae"] for entry in valid])),
                "mean_excess_true_iae_over_clean": float(np.mean([entry["excess_true_iae_over_clean"] for entry in valid])),
                "mean_occupancy_proxy_l2": float(np.mean([entry["occupancy_proxy_l2"] for entry in valid])),
                "mean_observed_iae": None if environment["mode"] != "measurement" else float(np.mean([entry["observed_iae"] for entry in valid])),
                "stability_rate": float(np.mean([entry["stability_flag"] for entry in per_zeta[zeta]])),
            })

        if environment["mode"] == "measurement":
            for pair_index, (left_zeta, right_zeta) in enumerate(PAIRWISE_COMPARISONS):
                valid = [
                    scenario for scenario in scenarios
                    if scenario["per_zeta"][left_zeta]["stability_flag"] == 1 and scenario["per_zeta"][right_zeta]["stability_flag"] == 1
                ]
                true_wins = np.array([
                    scenario["per_zeta"][left_zeta]["true_iae"] < scenario["per_zeta"][right_zeta]["true_iae"]
                    for scenario in valid
                ], dtype=float)
                observed_wins = np.array([
                    scenario["per_zeta"][left_zeta]["observed_iae"] < scenario["per_zeta"][right_zeta]["observed_iae"]
                    for scenario in valid
                ], dtype=float)
                true_ci = bootstrap_probability_ci(true_wins, environment["seed"] + 21000 + pair_index)
                observed_ci = bootstrap_probability_ci(observed_wins, environment["seed"] + 22000 + pair_index)
                pairwise_rows.append({
                    "environment_name": environment["name"],
                    "level": environment["level"],
                    "noise_std": float(environment["measurement_noise_std"]),
                    "left_zeta": float(left_zeta),
                    "right_zeta": float(right_zeta),
                    "true_winner_probability_left": float(np.mean(true_wins)),
                    "true_winner_ci_low": true_ci["low"],
                    "true_winner_ci_high": true_ci["high"],
                    "observed_winner_probability_left": float(np.mean(observed_wins)),
                    "observed_winner_ci_low": observed_ci["low"],
                    "observed_winner_ci_high": observed_ci["high"],
                })

    return clean_iae, environment_grid_rows, pairwise_rows


def matched_pairs(tuned_family, clean_iae):
    pairs = []
    for index, left in enumerate(tuned_family):
        for right in tuned_family[index + 1:]:
            settling_left = left["pitch_step_settling_time_2pct"]
            settling_right = right["pitch_step_settling_time_2pct"]
            settling_mean = 0.5 * (settling_left + settling_right)
            settling_diff_pct = 0.0 if settling_mean == 0.0 else abs(settling_left - settling_right) / settling_mean * 100.0
            iae_left = clean_iae[left["zeta"]]
            iae_right = clean_iae[right["zeta"]]
            pairs.append({
                "left_zeta": left["zeta"],
                "right_zeta": right["zeta"],
                "settling_diff_pct": settling_diff_pct,
                "left_variant_iae": iae_left,
                "right_variant_iae": iae_right,
                "iae_ratio": max(iae_left, iae_right) / max(min(iae_left, iae_right), 1e-12),
            })
    pairs.sort(key=lambda row: row["iae_ratio"], reverse=True)
    return pairs


def build_summary(baseline_summary, tuned_family, clean_iae, environment_grid_rows, pairwise_rows):
    by_environment = {}
    for row in environment_grid_rows:
        by_environment.setdefault(row["environment_name"], []).append(row)
    best_by_environment = {}
    for environment_name, rows in by_environment.items():
        best_row = min(rows, key=lambda row: row["mean_true_iae"])
        best_by_environment[environment_name] = {
            "mode": best_row["mode"],
            "level": best_row["level"],
            "noise_std": best_row["noise_std"],
            "baseline_best_zeta": baseline_summary["best_design_by_environment"][environment_name]["best_zeta"],
            "variant_best_zeta": best_row["zeta"],
            "variant_best_mean_true_iae": best_row["mean_true_iae"],
        }

    clean_best_zeta = best_by_environment["command_clean"]["variant_best_zeta"]
    matched = matched_pairs(tuned_family, clean_iae)
    supportive = [row for row in matched if row["settling_diff_pct"] <= 15.0 and row["iae_ratio"] >= 3.0]
    noisy_rows = [row for row in environment_grid_rows if row["level"] != "clean"]
    occupancy_corr = spearman_corr(
        [row["mean_occupancy_proxy_l2"] for row in noisy_rows],
        [row["mean_excess_true_iae_over_clean"] for row in noisy_rows],
    )
    nuisance_corr = spearman_corr(
        [row["noise_std"] ** 2 + row["gust_std"] ** 2 for row in noisy_rows],
        [row["mean_excess_true_iae_over_clean"] for row in noisy_rows],
    )
    movement_exists = any(
        abs(row["variant_best_zeta"] - clean_best_zeta) > 1e-12
        for name, row in best_by_environment.items()
        if name not in ("command_clean", "measurement_clean")
    )
    inward_movement_exists = any(
        row["variant_best_zeta"] > clean_best_zeta + 1e-12
        for name, row in best_by_environment.items()
        if name not in ("command_clean", "measurement_clean")
    )
    outward_movement_exists = any(
        row["variant_best_zeta"] < clean_best_zeta - 1e-12
        for name, row in best_by_environment.items()
        if name not in ("command_clean", "measurement_clean")
    )
    recommendation = "promote_to_stronger_validation" if supportive or inward_movement_exists else "keep_as_boundary_case"
    return {
        "objective": "Second-pass aircraft variant study for matched-transient strengthening and boundary-case confirmation.",
        "variant_definition": {
            "inner_loop_retune": "Retune baseline inner-loop gains toward a common pitch-step target.",
            "primary_mission": "slow_glide_profile_variant",
            "reference_formula": "h_ref(t) = -1.5 t + 60 sin(0.006 t)",
            "gust_tau_seconds": VARIANT_GUST_TAU,
        },
        "baseline_reference_summary": "studies/out-of-family-aircraft-longitudinal-autopilot/runs/latest/data/aircraft_autopilot_summary.json",
        "best_design_by_environment": best_by_environment,
        "matched_pairs": {
            "top_supportive_pair": supportive[0] if supportive else None,
            "pair_count_meeting_threshold": len(supportive),
            "top_pairs_by_iae_ratio": matched[:6],
        },
        "movement_summary": {
            "clean_best_zeta": clean_best_zeta,
            "any_movement_exists": movement_exists,
            "inward_movement_exists": inward_movement_exists,
            "outward_movement_exists": outward_movement_exists,
        },
        "occupancy_proxy_summary": {
            "global_occupancy_proxy_vs_excess_true_iae_spearman": occupancy_corr,
            "global_raw_nuisance_vs_excess_true_iae_spearman": nuisance_corr,
        },
        "pairwise_reliability": {
            f"{left}_vs_{right}": [
                row for row in pairwise_rows
                if abs(row["left_zeta"] - left) < 1e-12 and abs(row["right_zeta"] - right) < 1e-12
            ]
            for left, right in PAIRWISE_COMPARISONS
        },
        "final_recommendation": recommendation,
    }


def plot_variant_matched_transient(baseline_summary, variant_summary):
    figure, axes = plt.subplots(1, 2, figsize=(14.0, 5.6))

    for ax, summary, title, color in [
        (axes[0], baseline_summary["matched_pairs"], "Baseline Aircraft Study", base.MEMORY_COLOR),
        (axes[1], variant_summary["matched_pairs"], "Variant Aircraft Study", base.LIGHT_SHADOW_COLOR),
    ]:
        rows = summary["top_pairs_by_iae_ratio"][:5]
        labels = [f"{row['left_zeta']:.3g} vs {row['right_zeta']:.3g}" for row in rows]
        ratios = [row["iae_ratio"] for row in rows]
        bars = ax.barh(labels, ratios, color=color, alpha=0.9)
        ax.invert_yaxis()
        for bar, row in zip(bars, rows):
            ax.text(bar.get_width() + 0.03, bar.get_y() + bar.get_height() / 2.0, f"{row['settling_diff_pct']:.1f}% pitch gap", va="center", fontsize=9)
        style_panel(ax, title, "Mission IAE Ratio", "")
    add_takeaway(axes[0], "The baseline aircraft family never cleared the strong matched-pair threshold.", "lower right")
    add_takeaway(axes[1], "The variant either reveals a stronger separation or confirms the aircraft boundary case.", "lower right")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "aircraft_autopilot_variant_matched_transient.png")
    plt.close(figure)


def plot_variant_best_path(baseline_summary, variant_summary):
    figure, axes = plt.subplots(1, 2, figsize=(14.0, 5.6))

    def plot_mode(ax, mode):
        baseline_rows = [row for key, row in baseline_summary["best_design_by_environment"].items() if row["mode"] == mode]
        variant_rows = [row for key, row in variant_summary["best_design_by_environment"].items() if row["mode"] == mode]
        level_order = [env["level"] for env in base.ENVIRONMENTS if env["mode"] == mode]
        unique_levels = []
        for level in level_order:
            if level not in unique_levels:
                unique_levels.append(level)
        x_values = np.arange(len(unique_levels))
        baseline_vals = [next(row["best_zeta"] for row in baseline_rows if row["level"] == level) for level in unique_levels]
        variant_vals = [next(row["variant_best_zeta"] for row in variant_rows if row["level"] == level) for level in unique_levels]
        ax.plot(x_values, baseline_vals, marker="o", linewidth=2.0, linestyle="--", color=base.NOISE_COLOR, label="Baseline")
        ax.plot(x_values, variant_vals, marker="o", linewidth=2.4, color=base.FAST_COLOR, label="Variant")
        ax.set_xticks(x_values)
        ax.set_xticklabels([level.capitalize() for level in unique_levels])
        style_panel(ax, f"{mode.capitalize()} Side", "Environment Severity", "Best zeta")
        ax.legend(frameon=False)

    plot_mode(axes[0], "command")
    add_takeaway(axes[0], "If the variant line still stays flat, the aircraft capsule remains a boundary case.", "upper left")
    plot_mode(axes[1], "measurement")
    add_takeaway(axes[1], "This plot is the promote-vs-boundary-case decision view.", "upper left")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "aircraft_autopilot_variant_best_zeta_path.png")
    plt.close(figure)


def main():
    base.apply_plot_style()
    ensure_dirs()

    baseline_summary = json.loads((BASE_DATA_DIR / "aircraft_autopilot_summary.json").read_text())
    baseline_family = load_baseline_family()
    tuned_family = retune_inner_family(baseline_family)
    clean_iae, environment_grid_rows, pairwise_rows = run_variant_sweep(tuned_family)
    variant_summary = build_summary(baseline_summary, tuned_family, clean_iae, environment_grid_rows, pairwise_rows)

    write_csv(
        DATA_DIR / "aircraft_autopilot_variant_environment_grid.csv",
        environment_grid_rows,
        [
            "environment_name",
            "mode",
            "level",
            "noise_std",
            "gust_std",
            "zeta",
            "mean_true_iae",
            "mean_excess_true_iae_over_clean",
            "mean_occupancy_proxy_l2",
            "mean_observed_iae",
            "stability_rate",
        ],
    )
    write_json(DATA_DIR / "aircraft_autopilot_variant_comparison_summary.json", variant_summary)
    write_json(
        DATA_DIR / "manifest_variant.json",
        {
            "study": "out-of-family-aircraft-longitudinal-autopilot-variant",
            "generated_files": {
                "csv": [
                    "studies/out-of-family-aircraft-longitudinal-autopilot/runs/latest/data/aircraft_autopilot_variant_environment_grid.csv",
                ],
                "json": [
                    "studies/out-of-family-aircraft-longitudinal-autopilot/runs/latest/data/aircraft_autopilot_variant_comparison_summary.json",
                    "studies/out-of-family-aircraft-longitudinal-autopilot/runs/latest/data/manifest_variant.json",
                ],
                "plots": [
                    "studies/out-of-family-aircraft-longitudinal-autopilot/runs/latest/plots/aircraft_autopilot_variant_matched_transient.png",
                    "studies/out-of-family-aircraft-longitudinal-autopilot/runs/latest/plots/aircraft_autopilot_variant_best_zeta_path.png",
                ],
            },
        },
    )

    plot_variant_matched_transient(baseline_summary, variant_summary)
    plot_variant_best_path(baseline_summary, variant_summary)

    print("Aircraft autopilot variant study complete.")
    print(f"Recommendation: {variant_summary['final_recommendation']}")
    top_pair = variant_summary["matched_pairs"]["top_supportive_pair"]
    if top_pair is None:
        print("No matched pair met the promotion threshold in the variant study.")
    else:
        print(f"Top supportive pair: {top_pair}")


if __name__ == "__main__":
    main()
