import csv
import json
from pathlib import Path

import numpy as np
from scipy.signal import TransferFunction, freqresp, impulse, lsim


try:
    trapz = np.trapezoid
except AttributeError:
    trapz = np.trapz


ROOT_DIR = Path(__file__).resolve().parents[3]
RUN_DIR = Path(__file__).resolve().parents[1] / "runs" / "latest"
DATA_DIR = RUN_DIR / "data"
TIME_SERIES_DIR = DATA_DIR / "time_series"

WN_NOMINAL = 1.0
T = np.linspace(0, 150, 8000)
W = np.linspace(0.0, 0.25, 1200)
ZETAS = sorted(set(np.round(np.linspace(0.1, 1.0, 19), 3).tolist() + [0.25, 0.707]))
EPSILONS = (0.1, 0.05, 0.02)
SLOW_BAND_LIMITS = (0.03, 0.05, 0.1)
ROBUST_ZETA = 0.707
LIGHT_ZETA = 0.25
MATCHED_SETTLING_ZETAS = [0.15, 0.25, 0.4, 0.55, 0.707, 1.0]
SIGMA_TARGET = 0.5
BATCH_CONFIGS = [
    {
        "name": "nominal_clean",
        "description": "No noise, nominal natural frequency.",
        "samples": 1,
        "wn_scale_range": (1.0, 1.0),
        "noise_std": 0.0,
        "seed": 101,
    },
    {
        "name": "wn_jitter_clean",
        "description": "No noise, natural frequency jitter in [0.9, 1.1].",
        "samples": 30,
        "wn_scale_range": (0.9, 1.1),
        "noise_std": 0.0,
        "seed": 201,
    },
    {
        "name": "wn_jitter_noisy",
        "description": "Moderate noise with natural frequency jitter in [0.9, 1.1].",
        "samples": 30,
        "wn_scale_range": (0.9, 1.1),
        "noise_std": 0.04,
        "seed": 301,
    },
    {
        "name": "wide_jitter_noisy",
        "description": "Higher noise with wider natural frequency jitter in [0.8, 1.2].",
        "samples": 30,
        "wn_scale_range": (0.8, 1.2),
        "noise_std": 0.08,
        "seed": 401,
    },
]


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    TIME_SERIES_DIR.mkdir(exist_ok=True)


def create_system(zeta, wn):
    return TransferFunction([wn**2], [1, 2 * zeta * wn, wn**2])


def cumulative_integral(values, time):
    cumulative = np.zeros_like(values)
    cumulative[1:] = np.cumsum(0.5 * (values[1:] + values[:-1]) * np.diff(time))
    return cumulative


def decimal_key(value):
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text.replace(".", "_")


def shadow_horizon(time, signal_values, epsilon):
    magnitude = np.abs(signal_values)
    peak = float(np.max(magnitude))
    if peak <= 0:
        return 0.0
    threshold = epsilon * peak
    above = magnitude > threshold
    if not np.any(above):
        return 0.0
    return float(time[np.max(np.flatnonzero(above))])


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


def correlation(x_values, y_values, kind):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    if kind == "spearman":
        x = rankdata(x)
        y = rankdata(y)
    x_std = float(np.std(x))
    y_std = float(np.std(y))
    if x_std == 0.0 or y_std == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def summarize(values):
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(array)),
        "std": float(np.std(array)),
        "min": float(np.min(array)),
        "p10": float(np.percentile(array, 10)),
        "median": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)),
        "max": float(np.max(array)),
    }


def build_base_inputs(time):
    rng = np.random.default_rng(42)
    noisy_base = 0.025 * time + 0.6 * np.sin(0.011 * time)
    noisy_signal = noisy_base + 0.08 * rng.normal(size=len(time))
    return {
        "ramp": {
            "title": "Pure Slow Ramp",
            "u": 0.025 * time,
            "reference": 0.025 * time,
        },
        "ramp_sine": {
            "title": "Ramp + Low-Freq Sine",
            "u": 0.025 * time + 0.7 * np.sin(0.012 * time),
            "reference": 0.025 * time + 0.7 * np.sin(0.012 * time),
        },
        "slow_sine": {
            "title": "Ultra-Slow Sine",
            "u": 1.2 * np.sin(0.008 * time),
            "reference": 1.2 * np.sin(0.008 * time),
        },
        "noisy": {
            "title": "Slow Input + Noise",
            "u": noisy_signal,
            "reference": noisy_base,
        },
    }


def step_response_metrics(system, time):
    unit_step = np.ones_like(time)
    _, y, _ = lsim(system, U=unit_step, T=time)
    y = np.asarray(y, dtype=float)
    y_final = float(y[-1])
    peak_index = int(np.argmax(y))
    peak_value = float(y[peak_index])
    overshoot = 0.0
    if abs(y_final) > 1e-12:
        overshoot = max(0.0, (peak_value - y_final) / abs(y_final))

    lower = 0.1 * y_final
    upper = 0.9 * y_final
    rise_start = None
    rise_end = None
    for index, value in enumerate(y):
        if rise_start is None and value >= lower:
            rise_start = float(time[index])
        if rise_end is None and value >= upper:
            rise_end = float(time[index])
            break
    rise_time = None if rise_start is None or rise_end is None else rise_end - rise_start

    settle_band = 0.02 * max(abs(y_final), 1e-12)
    violating = np.flatnonzero(np.abs(y - y_final) > settle_band)
    settling_time = 0.0 if len(violating) == 0 else float(time[violating[-1]])

    return {
        "step_final_value": y_final,
        "step_peak_value": peak_value,
        "step_peak_time": float(time[peak_index]),
        "step_overshoot": overshoot,
        "step_rise_time_10_90": rise_time,
        "step_settling_time_2pct": settling_time,
    }


def intrinsic_metrics(system, zeta, wn, time, w_grid, epsilons, slow_band_limits):
    t_impulse, y_impulse = impulse(system, T=time)
    y_impulse = np.squeeze(np.asarray(y_impulse, dtype=float))
    abs_impulse = np.abs(y_impulse)
    _, frequency_response = freqresp(system, w=w_grid)
    tracking_gap = np.abs(1.0 - frequency_response) ** 2

    slow_band_metrics = {}
    for limit in slow_band_limits:
        mask = w_grid <= limit
        key = f"slow_band_deficit_{decimal_key(limit)}"
        slow_band_metrics[key] = float(trapz(tracking_gap[mask], w_grid[mask])) if np.any(mask) else 0.0

    horizon_metrics = {
        f"shadow_horizon_eps_{decimal_key(epsilon)}": shadow_horizon(t_impulse, y_impulse, epsilon)
        for epsilon in epsilons
    }

    sigma = zeta * wn
    classical = step_response_metrics(system, time)
    metrics = {
        "zeta": float(zeta),
        "wn": float(wn),
        "sigma": float(sigma),
        "dominant_real_part": float(np.max(np.real(system.poles))),
        "stability_margin_d": float(-np.max(np.real(system.poles))),
        "settling_time_approx_2pct": float(4.0 / sigma),
        "impulse_peak": float(np.max(abs_impulse)),
        "shadow_mass_l1": float(trapz(abs_impulse, t_impulse)),
        "shadow_mass_l2": float(trapz(abs_impulse**2, t_impulse)),
        **horizon_metrics,
        **slow_band_metrics,
        **classical,
    }
    return metrics


def simulate_test(system, u, time):
    _, y, _ = lsim(system, U=u, T=time)
    y = np.asarray(y, dtype=float)
    err_signed = y - u
    err_abs = np.abs(err_signed)
    return {
        "y": y,
        "err_signed": err_signed,
        "err_abs": err_abs,
        "iae": float(trapz(err_abs, time)),
        "ise": float(trapz(err_signed**2, time)),
        "peak_abs_error": float(np.max(err_abs)),
        "mean_abs_error": float(np.mean(err_abs)),
        "cumulative_iae": cumulative_integral(err_abs, time),
    }


def representative_input(time):
    return 0.025 * time + 0.7 * np.sin(0.012 * time)


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def export_time_series(test_name, time, reference, input_used, simulations):
    path = TIME_SERIES_DIR / f"{test_name}.csv"
    ordered_zetas = sorted(simulations)
    fieldnames = ["t", "reference", "input_used"]
    for zeta in ordered_zetas:
        suffix = f"zeta_{decimal_key(zeta)}"
        fieldnames.extend([
            f"y_{suffix}",
            f"err_signed_{suffix}",
            f"err_abs_{suffix}",
            f"cum_iae_{suffix}",
        ])

    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, t_value in enumerate(time):
            row = {
                "t": float(t_value),
                "reference": float(reference[index]),
                "input_used": float(input_used[index]),
            }
            for zeta in ordered_zetas:
                suffix = f"zeta_{decimal_key(zeta)}"
                simulation = simulations[zeta]
                row[f"y_{suffix}"] = float(simulation["y"][index])
                row[f"err_signed_{suffix}"] = float(simulation["err_signed"][index])
                row[f"err_abs_{suffix}"] = float(simulation["err_abs"][index])
                row[f"cum_iae_{suffix}"] = float(simulation["cumulative_iae"][index])
            writer.writerow(row)


def build_nominal_exports():
    inputs = build_base_inputs(T)
    systems = {float(zeta): create_system(float(zeta), WN_NOMINAL) for zeta in ZETAS}
    system_metrics_rows = []
    system_metrics_by_zeta = {}
    tracking_rows = []
    time_series_exports = {name: {} for name in inputs}

    for zeta in sorted(systems):
        metrics = intrinsic_metrics(systems[zeta], zeta, WN_NOMINAL, T, W, EPSILONS, SLOW_BAND_LIMITS)
        system_metrics_rows.append(metrics)
        system_metrics_by_zeta[zeta] = metrics

        for test_name, config in inputs.items():
            simulation = simulate_test(systems[zeta], config["u"], T)
            tracking_rows.append({
                "test_name": test_name,
                "test_title": config["title"],
                "zeta": zeta,
                "iae": simulation["iae"],
                "ise": simulation["ise"],
                "peak_abs_error": simulation["peak_abs_error"],
                "mean_abs_error": simulation["mean_abs_error"],
            })
            if zeta in (LIGHT_ZETA, ROBUST_ZETA):
                time_series_exports[test_name][zeta] = simulation

    for test_name, config in inputs.items():
        export_time_series(
            test_name,
            T,
            config["reference"],
            config["u"],
            time_series_exports[test_name],
        )

    robust_vs_light = []
    for test_name, config in inputs.items():
        light_sim = time_series_exports[test_name][LIGHT_ZETA]
        robust_sim = time_series_exports[test_name][ROBUST_ZETA]
        winner = "light_shadow" if light_sim["iae"] < robust_sim["iae"] else "robust"
        robust_vs_light.append({
            "test_name": test_name,
            "test_title": config["title"],
            "robust_zeta": ROBUST_ZETA,
            "light_shadow_zeta": LIGHT_ZETA,
            "robust_iae": robust_sim["iae"],
            "light_shadow_iae": light_sim["iae"],
            "iae_ratio_robust_over_light": robust_sim["iae"] / light_sim["iae"],
            "winner": winner,
        })

    return inputs, system_metrics_rows, system_metrics_by_zeta, tracking_rows, robust_vs_light


def build_metric_correlations(system_metrics_by_zeta, tracking_rows):
    metric_names = [
        "stability_margin_d",
        "settling_time_approx_2pct",
        "step_settling_time_2pct",
        "step_overshoot",
        "shadow_horizon_eps_0_02",
        "shadow_mass_l1",
        "shadow_mass_l2",
        "slow_band_deficit_0_05",
    ]
    grouped_tracking = {}
    for row in tracking_rows:
        grouped_tracking.setdefault(row["test_name"], []).append(row)

    correlation_rows = []
    for test_name, rows in grouped_tracking.items():
        rows = sorted(rows, key=lambda row: row["zeta"])
        zeta_order = [row["zeta"] for row in rows]
        y = [row["iae"] for row in rows]
        for metric in metric_names:
            x = [system_metrics_by_zeta[zeta][metric] for zeta in zeta_order]
            correlation_rows.append({
                "test_name": test_name,
                "metric_name": metric,
                "pearson_with_iae": correlation(x, y, "pearson"),
                "spearman_with_iae": correlation(x, y, "spearman"),
            })
    return correlation_rows


def build_batch_exports():
    base_input = representative_input(T)
    sample_rows = []
    summary_rows = []

    for batch in BATCH_CONFIGS:
        rng = np.random.default_rng(batch["seed"])
        per_zeta_samples = {zeta: [] for zeta in ZETAS}
        for zeta in ZETAS:
            for sample_index in range(batch["samples"]):
                low, high = batch["wn_scale_range"]
                wn_scale = low if low == high else float(rng.uniform(low, high))
                wn = WN_NOMINAL * wn_scale
                system = create_system(zeta, wn)
                metrics = intrinsic_metrics(system, zeta, wn, T, W, EPSILONS, SLOW_BAND_LIMITS)
                noise = batch["noise_std"] * rng.normal(size=len(T))
                input_used = base_input + noise
                simulation = simulate_test(system, input_used, T)
                sample = {
                    "batch_name": batch["name"],
                    "sample_index": sample_index,
                    "zeta": zeta,
                    "wn_scale": wn_scale,
                    "wn": wn,
                    "noise_std": batch["noise_std"],
                    "iae": simulation["iae"],
                    "ise": simulation["ise"],
                    "peak_abs_error": simulation["peak_abs_error"],
                    "mean_abs_error": simulation["mean_abs_error"],
                    "shadow_horizon_eps_0_02": metrics["shadow_horizon_eps_0_02"],
                    "shadow_mass_l1": metrics["shadow_mass_l1"],
                    "slow_band_deficit_0_05": metrics["slow_band_deficit_0_05"],
                    "step_settling_time_2pct": metrics["step_settling_time_2pct"],
                }
                sample_rows.append(sample)
                per_zeta_samples[zeta].append(sample)

        for zeta, samples in per_zeta_samples.items():
            iae_stats = summarize([sample["iae"] for sample in samples])
            shadow_mass_stats = summarize([sample["shadow_mass_l1"] for sample in samples])
            summary_rows.append({
                "batch_name": batch["name"],
                "zeta": zeta,
                "sample_count": len(samples),
                "iae_mean": iae_stats["mean"],
                "iae_std": iae_stats["std"],
                "iae_p10": iae_stats["p10"],
                "iae_median": iae_stats["median"],
                "iae_p90": iae_stats["p90"],
                "shadow_mass_l1_mean": shadow_mass_stats["mean"],
                "shadow_mass_l1_std": shadow_mass_stats["std"],
            })

    summary_rows.sort(key=lambda row: (row["batch_name"], row["zeta"]))
    return sample_rows, summary_rows


def build_matched_settling_study():
    rows = []
    ramp_sine = representative_input(T)
    for zeta in MATCHED_SETTLING_ZETAS:
        wn = SIGMA_TARGET / zeta
        system = create_system(zeta, wn)
        metrics = intrinsic_metrics(system, zeta, wn, T, W, EPSILONS, SLOW_BAND_LIMITS)
        simulation = simulate_test(system, ramp_sine, T)
        rows.append({
            "zeta": zeta,
            "wn": wn,
            "sigma": metrics["sigma"],
            "settling_time_approx_2pct": metrics["settling_time_approx_2pct"],
            "step_settling_time_2pct": metrics["step_settling_time_2pct"],
            "step_overshoot": metrics["step_overshoot"],
            "shadow_horizon_eps_0_02": metrics["shadow_horizon_eps_0_02"],
            "shadow_mass_l1": metrics["shadow_mass_l1"],
            "slow_band_deficit_0_05": metrics["slow_band_deficit_0_05"],
            "ramp_sine_iae": simulation["iae"],
            "ramp_sine_ise": simulation["ise"],
        })
    return rows


def find_separation_examples(matched_rows, settling_tolerance=0.12):
    examples = []
    for left_index, left in enumerate(matched_rows):
        for right in matched_rows[left_index + 1:]:
            ts_left = left["step_settling_time_2pct"]
            ts_right = right["step_settling_time_2pct"]
            rel_diff = abs(ts_left - ts_right) / max(ts_left, ts_right, 1e-12)
            if rel_diff <= settling_tolerance:
                horizon_ratio = max(left["shadow_horizon_eps_0_02"], right["shadow_horizon_eps_0_02"]) / max(
                    min(left["shadow_horizon_eps_0_02"], right["shadow_horizon_eps_0_02"]),
                    1e-12,
                )
                mass_ratio = max(left["shadow_mass_l1"], right["shadow_mass_l1"]) / max(
                    min(left["shadow_mass_l1"], right["shadow_mass_l1"]),
                    1e-12,
                )
                iae_ratio = max(left["ramp_sine_iae"], right["ramp_sine_iae"]) / max(
                    min(left["ramp_sine_iae"], right["ramp_sine_iae"]),
                    1e-12,
                )
                examples.append({
                    "left_zeta": left["zeta"],
                    "right_zeta": right["zeta"],
                    "relative_step_settling_difference": rel_diff,
                    "shadow_horizon_ratio": horizon_ratio,
                    "shadow_mass_ratio": mass_ratio,
                    "ramp_sine_iae_ratio": iae_ratio,
                })
    examples.sort(key=lambda example: (example["ramp_sine_iae_ratio"], example["shadow_mass_ratio"]), reverse=True)
    return examples[:5]


def write_outputs(
    system_metrics_rows,
    tracking_rows,
    correlation_rows,
    batch_sample_rows,
    batch_summary_rows,
    matched_rows,
    summary_payload,
    report_payload,
):
    system_fieldnames = [
        "zeta",
        "wn",
        "sigma",
        "dominant_real_part",
        "stability_margin_d",
        "settling_time_approx_2pct",
        "impulse_peak",
        "shadow_mass_l1",
        "shadow_mass_l2",
        "shadow_horizon_eps_0_1",
        "shadow_horizon_eps_0_05",
        "shadow_horizon_eps_0_02",
        "slow_band_deficit_0_03",
        "slow_band_deficit_0_05",
        "slow_band_deficit_0_1",
        "step_final_value",
        "step_peak_value",
        "step_peak_time",
        "step_overshoot",
        "step_rise_time_10_90",
        "step_settling_time_2pct",
    ]
    tracking_fieldnames = [
        "test_name",
        "test_title",
        "zeta",
        "iae",
        "ise",
        "peak_abs_error",
        "mean_abs_error",
    ]
    correlation_fieldnames = [
        "test_name",
        "metric_name",
        "pearson_with_iae",
        "spearman_with_iae",
    ]
    batch_sample_fieldnames = [
        "batch_name",
        "sample_index",
        "zeta",
        "wn_scale",
        "wn",
        "noise_std",
        "iae",
        "ise",
        "peak_abs_error",
        "mean_abs_error",
        "shadow_horizon_eps_0_02",
        "shadow_mass_l1",
        "slow_band_deficit_0_05",
        "step_settling_time_2pct",
    ]
    batch_summary_fieldnames = [
        "batch_name",
        "zeta",
        "sample_count",
        "iae_mean",
        "iae_std",
        "iae_p10",
        "iae_median",
        "iae_p90",
        "shadow_mass_l1_mean",
        "shadow_mass_l1_std",
    ]
    matched_fieldnames = [
        "zeta",
        "wn",
        "sigma",
        "settling_time_approx_2pct",
        "step_settling_time_2pct",
        "step_overshoot",
        "shadow_horizon_eps_0_02",
        "shadow_mass_l1",
        "slow_band_deficit_0_05",
        "ramp_sine_iae",
        "ramp_sine_ise",
    ]

    write_csv(DATA_DIR / "cognitive_budget_system_metrics.csv", system_metrics_rows, system_fieldnames)
    write_csv(DATA_DIR / "cognitive_budget_tracking_metrics.csv", tracking_rows, tracking_fieldnames)
    write_csv(DATA_DIR / "metric_correlations.csv", correlation_rows, correlation_fieldnames)
    write_csv(DATA_DIR / "batch_tracking_samples.csv", batch_sample_rows, batch_sample_fieldnames)
    write_csv(DATA_DIR / "batch_tracking_summary.csv", batch_summary_rows, batch_summary_fieldnames)
    write_csv(DATA_DIR / "matched_settling_study.csv", matched_rows, matched_fieldnames)

    write_json(DATA_DIR / "cognitive_budget_summary.json", summary_payload)
    write_json(DATA_DIR / "cognitive_budget_report.json", report_payload)
    write_json(
        DATA_DIR / "manifest.json",
        {
            "generated_by": "studies/foundation-pole-shadow/scripts/generate_cognitive_budget_data.py",
            "outputs": [
                "studies/foundation-pole-shadow/runs/latest/data/cognitive_budget_system_metrics.csv",
                "studies/foundation-pole-shadow/runs/latest/data/cognitive_budget_tracking_metrics.csv",
                "studies/foundation-pole-shadow/runs/latest/data/metric_correlations.csv",
                "studies/foundation-pole-shadow/runs/latest/data/batch_tracking_samples.csv",
                "studies/foundation-pole-shadow/runs/latest/data/batch_tracking_summary.csv",
                "studies/foundation-pole-shadow/runs/latest/data/matched_settling_study.csv",
                "studies/foundation-pole-shadow/runs/latest/data/cognitive_budget_summary.json",
                "studies/foundation-pole-shadow/runs/latest/data/cognitive_budget_report.json",
                "studies/foundation-pole-shadow/runs/latest/data/manifest.json",
                "studies/foundation-pole-shadow/runs/latest/data/time_series/ramp.csv",
                "studies/foundation-pole-shadow/runs/latest/data/time_series/ramp_sine.csv",
                "studies/foundation-pole-shadow/runs/latest/data/time_series/slow_sine.csv",
                "studies/foundation-pole-shadow/runs/latest/data/time_series/noisy.csv",
            ],
        },
    )


def main():
    ensure_dirs()

    _, system_metrics_rows, system_metrics_by_zeta, tracking_rows, robust_vs_light = build_nominal_exports()
    correlation_rows = build_metric_correlations(system_metrics_by_zeta, tracking_rows)
    batch_sample_rows, batch_summary_rows = build_batch_exports()
    matched_rows = build_matched_settling_study()
    separation_examples = find_separation_examples(matched_rows)

    system_metrics_rows.sort(key=lambda row: row["zeta"])
    tracking_rows.sort(key=lambda row: (row["test_name"], row["zeta"]))
    correlation_rows.sort(key=lambda row: (row["test_name"], row["metric_name"]))
    batch_sample_rows.sort(key=lambda row: (row["batch_name"], row["zeta"], row["sample_index"]))

    batch_highlights = []
    for batch in BATCH_CONFIGS:
        rows = [row for row in batch_summary_rows if row["batch_name"] == batch["name"]]
        best = min(rows, key=lambda row: row["iae_mean"])
        worst = max(rows, key=lambda row: row["iae_mean"])
        batch_highlights.append({
            "batch_name": batch["name"],
            "description": batch["description"],
            "best_zeta_by_mean_iae": best["zeta"],
            "best_mean_iae": best["iae_mean"],
            "worst_zeta_by_mean_iae": worst["zeta"],
            "worst_mean_iae": worst["iae_mean"],
        })

    strongest_correlations = []
    for test_name in sorted(set(row["test_name"] for row in correlation_rows)):
        rows = [row for row in correlation_rows if row["test_name"] == test_name and row["spearman_with_iae"] is not None]
        rows.sort(key=lambda row: abs(row["spearman_with_iae"]), reverse=True)
        strongest_correlations.append({
            "test_name": test_name,
            "top_metrics_by_absolute_spearman": rows[:4],
        })

    summary_payload = {
        "schema_version": 2,
        "description": "Structured evidence exports for the Pole's Shadow / cognitive-budget hypothesis.",
        "assumptions": {
            "system_family": "Continuous-time second-order closed-loop transfer functions parameterized by damping ratio zeta and natural frequency wn.",
            "nominal_wn": WN_NOMINAL,
            "time_grid": {
                "start": float(T[0]),
                "end": float(T[-1]),
                "points": len(T),
            },
            "frequency_grid": {
                "start": float(W[0]),
                "end": float(W[-1]),
                "points": len(W),
            },
            "epsilons": list(EPSILONS),
            "slow_band_limits": list(SLOW_BAND_LIMITS),
            "matched_settling_sigma_target": SIGMA_TARGET,
        },
        "files": {
                "system_metrics_csv": "studies/foundation-pole-shadow/runs/latest/data/cognitive_budget_system_metrics.csv",
                "tracking_metrics_csv": "studies/foundation-pole-shadow/runs/latest/data/cognitive_budget_tracking_metrics.csv",
                "metric_correlations_csv": "studies/foundation-pole-shadow/runs/latest/data/metric_correlations.csv",
                "batch_tracking_samples_csv": "studies/foundation-pole-shadow/runs/latest/data/batch_tracking_samples.csv",
                "batch_tracking_summary_csv": "studies/foundation-pole-shadow/runs/latest/data/batch_tracking_summary.csv",
                "matched_settling_study_csv": "studies/foundation-pole-shadow/runs/latest/data/matched_settling_study.csv",
                "time_series_dir": "studies/foundation-pole-shadow/runs/latest/data/time_series",
        },
        "robust_vs_light_summary": robust_vs_light,
        "batch_highlights": batch_highlights,
    }

    report_payload = {
        "report_version": 1,
        "objective": "Create machine-readable supporting evidence for candidate cognitive-budget diagnostics.",
        "candidate_metrics": {
            "shadow_horizon_eps_0_02": "Time after which the impulse response stays below 2% of its peak magnitude.",
            "shadow_mass_l1": "Integral of the absolute impulse response.",
            "shadow_mass_l2": "Integral of the squared impulse response magnitude.",
            "slow_band_deficit_0_05": "Integral of |1 - T(jw)|^2 over the low-frequency band [0, 0.05].",
        },
        "classical_metrics_tracked": [
            "settling_time_approx_2pct",
            "step_settling_time_2pct",
            "step_overshoot",
            "step_rise_time_10_90",
        ],
        "robust_vs_light_summary": robust_vs_light,
        "strongest_metric_correlations": strongest_correlations,
        "batch_highlights": batch_highlights,
        "matched_settling_study": {
            "rows": matched_rows,
            "separation_examples": separation_examples,
            "interpretation": "These examples are intended to show where similar settling-time behavior still leaves room for substantial separation in cognitive-budget metrics and slow-tracking performance.",
        },
    }

    write_outputs(
        system_metrics_rows,
        tracking_rows,
        correlation_rows,
        batch_sample_rows,
        batch_summary_rows,
        matched_rows,
        summary_payload,
        report_payload,
    )

    print("✅ Cognitive-budget data export complete.")
    print("Files created:")
    print("   • studies/foundation-pole-shadow/runs/latest/data/cognitive_budget_system_metrics.csv")
    print("   • studies/foundation-pole-shadow/runs/latest/data/cognitive_budget_tracking_metrics.csv")
    print("   • studies/foundation-pole-shadow/runs/latest/data/metric_correlations.csv")
    print("   • studies/foundation-pole-shadow/runs/latest/data/batch_tracking_samples.csv")
    print("   • studies/foundation-pole-shadow/runs/latest/data/batch_tracking_summary.csv")
    print("   • studies/foundation-pole-shadow/runs/latest/data/matched_settling_study.csv")
    print("   • studies/foundation-pole-shadow/runs/latest/data/cognitive_budget_summary.json")
    print("   • studies/foundation-pole-shadow/runs/latest/data/cognitive_budget_report.json")
    print("   • studies/foundation-pole-shadow/runs/latest/data/manifest.json")
    print("   • studies/foundation-pole-shadow/runs/latest/data/time_series/*.csv")


if __name__ == "__main__":
    main()
