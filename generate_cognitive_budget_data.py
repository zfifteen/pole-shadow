import csv
import json
from pathlib import Path

import numpy as np
from scipy.signal import TransferFunction, freqresp, impulse, lsim


try:
    trapz = np.trapezoid
except AttributeError:
    trapz = np.trapz


ROOT_DIR = Path(".")
DATA_DIR = ROOT_DIR / "data"
TIME_SERIES_DIR = DATA_DIR / "time_series"

WN = 1.0
T = np.linspace(0, 150, 8000)
W = np.linspace(0.0, 0.25, 1200)
ZETAS = sorted(set(np.round(np.linspace(0.1, 1.0, 19), 3).tolist() + [0.25, 0.707]))
EPSILONS = (0.1, 0.05, 0.02)
SLOW_BAND_LIMITS = (0.03, 0.05, 0.1)


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    TIME_SERIES_DIR.mkdir(exist_ok=True)


def create_system(zeta, wn=WN):
    return TransferFunction([wn**2], [1, 2 * zeta * wn, wn**2])


def cumulative_integral(values, time):
    cumulative = np.zeros_like(values)
    cumulative[1:] = np.cumsum(0.5 * (values[1:] + values[:-1]) * np.diff(time))
    return cumulative


def shadow_horizon(time, signal_values, epsilon):
    magnitude = np.abs(signal_values)
    peak = np.max(magnitude)
    if peak <= 0:
        return 0.0
    threshold = epsilon * peak
    above = magnitude > threshold
    if not np.any(above):
        return 0.0
    last_index = np.max(np.flatnonzero(above))
    return float(time[last_index])


def transient_metrics(system, time, w_grid, epsilons, slow_band_limits):
    t_impulse, y_impulse = impulse(system, T=time)
    if y_impulse.ndim > 1:
        y_impulse = np.squeeze(y_impulse)
    abs_impulse = np.abs(y_impulse)
    horizons = {
        f"shadow_horizon_eps_{str(epsilon).replace('.', '_')}": shadow_horizon(t_impulse, y_impulse, epsilon)
        for epsilon in epsilons
    }
    shadow_mass_l1 = float(trapz(abs_impulse, t_impulse))
    shadow_mass_l2 = float(trapz(abs_impulse**2, t_impulse))
    _, freq_response = freqresp(system, w=w_grid)
    tracking_gap = np.abs(1.0 - freq_response) ** 2
    slow_band_deficits = {}
    for omega_limit in slow_band_limits:
        mask = w_grid <= omega_limit
        deficit = trapz(tracking_gap[mask], w_grid[mask]) if np.any(mask) else 0.0
        key = f"slow_band_deficit_0_{str(omega_limit).split('.')[-1]}"
        slow_band_deficits[key] = float(deficit)
    dominant_real_part = float(np.max(np.real(system.poles)))
    return {
        "dominant_real_part": dominant_real_part,
        "stability_margin_d": float(-dominant_real_part),
        "impulse_peak": float(np.max(abs_impulse)),
        "shadow_mass_l1": shadow_mass_l1,
        "shadow_mass_l2": shadow_mass_l2,
        **horizons,
        **slow_band_deficits,
        "impulse_response": y_impulse,
    }


def build_inputs(time):
    rng = np.random.default_rng(42)
    clean_noisy_base = 0.025 * time + 0.6 * np.sin(0.011 * time)
    noisy = clean_noisy_base + 0.08 * rng.normal(size=len(time))
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
            "u": noisy,
            "reference": clean_noisy_base,
        },
    }


def simulate_test(system, u, time):
    _, y, _ = lsim(system, U=u, T=time)
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


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def export_time_series(test_name, time, reference, noisy_input, series_by_zeta):
    path = TIME_SERIES_DIR / f"{test_name}.csv"
    fieldnames = ["t", "reference", "input_used"]
    ordered_zetas = sorted(series_by_zeta)
    for zeta in ordered_zetas:
        suffix = f"zeta_{str(zeta).replace('.', '_')}"
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
                "input_used": float(noisy_input[index]),
            }
            for zeta in ordered_zetas:
                suffix = f"zeta_{str(zeta).replace('.', '_')}"
                simulation = series_by_zeta[zeta]
                row[f"y_{suffix}"] = float(simulation["y"][index])
                row[f"err_signed_{suffix}"] = float(simulation["err_signed"][index])
                row[f"err_abs_{suffix}"] = float(simulation["err_abs"][index])
                row[f"cum_iae_{suffix}"] = float(simulation["cumulative_iae"][index])
            writer.writerow(row)


def main():
    ensure_dirs()

    inputs = build_inputs(T)
    robust_zeta = 0.707
    light_zeta = 0.25

    systems = {float(zeta): create_system(float(zeta)) for zeta in ZETAS}
    system_metrics_rows = []
    sweep_tracking_rows = []
    hypothesis_comparisons = []

    time_series_exports = {name: {} for name in inputs}

    for zeta, system in systems.items():
        metrics = transient_metrics(system, T, W, EPSILONS, SLOW_BAND_LIMITS)
        system_metrics_rows.append({
            "zeta": zeta,
            "wn": WN,
            "dominant_real_part": metrics["dominant_real_part"],
            "stability_margin_d": metrics["stability_margin_d"],
            "impulse_peak": metrics["impulse_peak"],
            "shadow_mass_l1": metrics["shadow_mass_l1"],
            "shadow_mass_l2": metrics["shadow_mass_l2"],
            "shadow_horizon_eps_0_1": metrics["shadow_horizon_eps_0_1"],
            "shadow_horizon_eps_0_05": metrics["shadow_horizon_eps_0_05"],
            "shadow_horizon_eps_0_02": metrics["shadow_horizon_eps_0_02"],
            "slow_band_deficit_0_03": metrics["slow_band_deficit_0_03"],
            "slow_band_deficit_0_05": metrics["slow_band_deficit_0_05"],
            "slow_band_deficit_0_1": metrics["slow_band_deficit_0_1"],
        })

        for test_name, test_config in inputs.items():
            simulation = simulate_test(system, test_config["u"], T)
            sweep_tracking_rows.append({
                "test_name": test_name,
                "test_title": test_config["title"],
                "zeta": zeta,
                "iae": simulation["iae"],
                "ise": simulation["ise"],
                "peak_abs_error": simulation["peak_abs_error"],
                "mean_abs_error": simulation["mean_abs_error"],
            })
            if zeta in (robust_zeta, light_zeta):
                time_series_exports[test_name][zeta] = simulation

    for test_name, test_config in inputs.items():
        export_time_series(
            test_name,
            T,
            test_config["reference"],
            test_config["u"],
            time_series_exports[test_name],
        )

        robust_metrics = time_series_exports[test_name][robust_zeta]
        light_metrics = time_series_exports[test_name][light_zeta]
        winner = "light_shadow" if light_metrics["iae"] < robust_metrics["iae"] else "robust"
        hypothesis_comparisons.append({
            "test_name": test_name,
            "test_title": test_config["title"],
            "robust_zeta": robust_zeta,
            "light_shadow_zeta": light_zeta,
            "robust_iae": robust_metrics["iae"],
            "light_shadow_iae": light_metrics["iae"],
            "iae_ratio_robust_over_light": robust_metrics["iae"] / light_metrics["iae"],
            "winner": winner,
        })

    system_metrics_rows.sort(key=lambda row: row["zeta"])
    sweep_tracking_rows.sort(key=lambda row: (row["test_name"], row["zeta"]))

    write_csv(
        DATA_DIR / "cognitive_budget_system_metrics.csv",
        system_metrics_rows,
        [
            "zeta",
            "wn",
            "dominant_real_part",
            "stability_margin_d",
            "impulse_peak",
            "shadow_mass_l1",
            "shadow_mass_l2",
            "shadow_horizon_eps_0_1",
            "shadow_horizon_eps_0_05",
            "shadow_horizon_eps_0_02",
            "slow_band_deficit_0_03",
            "slow_band_deficit_0_05",
            "slow_band_deficit_0_1",
        ],
    )
    write_csv(
        DATA_DIR / "cognitive_budget_tracking_metrics.csv",
        sweep_tracking_rows,
        [
            "test_name",
            "test_title",
            "zeta",
            "iae",
            "ise",
            "peak_abs_error",
            "mean_abs_error",
        ],
    )

    summary_payload = {
        "schema_version": 1,
        "description": "Structured evidence exports for the Pole's Shadow / cognitive-budget hypothesis.",
        "assumptions": {
            "system_family": "Continuous-time second-order closed-loop transfer functions with wn=1.0 and varying damping ratio zeta.",
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
            "candidate_metrics": {
                "shadow_horizon": "Time after which the impulse response remains below epsilon times its peak magnitude.",
                "shadow_mass_l1": "Integral of absolute impulse response.",
                "shadow_mass_l2": "Integral of squared impulse response magnitude.",
                "slow_band_deficit": "Integral of |1 - T(jw)|^2 over a low-frequency band.",
            },
        },
        "files": {
            "system_metrics_csv": "data/cognitive_budget_system_metrics.csv",
            "tracking_metrics_csv": "data/cognitive_budget_tracking_metrics.csv",
            "time_series_dir": "data/time_series",
        },
        "robust_vs_light_summary": hypothesis_comparisons,
    }
    write_json(DATA_DIR / "cognitive_budget_summary.json", summary_payload)

    manifest_payload = {
        "generated_by": "generate_cognitive_budget_data.py",
        "outputs": [
            "data/cognitive_budget_system_metrics.csv",
            "data/cognitive_budget_tracking_metrics.csv",
            "data/cognitive_budget_summary.json",
            "data/time_series/ramp.csv",
            "data/time_series/ramp_sine.csv",
            "data/time_series/slow_sine.csv",
            "data/time_series/noisy.csv",
        ],
    }
    write_json(DATA_DIR / "manifest.json", manifest_payload)

    print("✅ Cognitive-budget data export complete.")
    print("Files created:")
    print("   • data/cognitive_budget_system_metrics.csv")
    print("   • data/cognitive_budget_tracking_metrics.csv")
    print("   • data/cognitive_budget_summary.json")
    print("   • data/manifest.json")
    print("   • data/time_series/*.csv")


if __name__ == "__main__":
    main()
