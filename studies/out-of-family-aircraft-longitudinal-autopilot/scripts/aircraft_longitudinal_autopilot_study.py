import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import solve_continuous_lyapunov
from scipy.optimize import minimize
from scipy.signal import StateSpace, freqresp, impulse, lsim


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

ALTITUDE_TRIM_FT = 20000.0
V_TRIM = 916.6
TAU_E = 0.05
TAU_H = 0.35
TAU_G = 2.0
TIME = np.linspace(0.0, 180.0, 2600)
STEP_TIME = np.linspace(0.0, 180.0, 2600)
IMPULSE_TIME = np.linspace(0.0, 180.0, 3200)
SLOW_BAND_LIMIT = 0.03
SLOW_BAND_GRID = np.linspace(0.0, 0.15, 1200)
BANDWIDTH_GRID = np.logspace(-5, 1, 2600)
BOOTSTRAP_SAMPLES = 1000
PAIRWISE_COMPARISONS = [(0.15, 0.707), (0.25, 0.707), (0.35, 0.707)]
ZETAS = [0.15, 0.20, 0.25, 0.35, 0.50, 0.707, 1.00]
LONG_SHADOW_ZETA = min(ZETAS)

A_BASE = np.array([
    [-0.8, -0.0006, -12.0, 0.0],
    [0.0, -0.014, -16.64, -32.2],
    [1.0, -0.0001, -1.5, 0.0],
    [1.0, 0.0, 0.0, 0.0],
], dtype=float)
B_BASE = np.array([[-19.0], [-0.66], [-0.16], [0.0]], dtype=float)

MODE_COLORS = {
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
SETTLING_COLOR = "#4d7c59"
MATCHED_PAIR_COLOR = "#4c8eda"

CLEAN_TESTS = [
    {
        "name": "altitude_ramp",
        "title": "Altitude Ramp",
        "reference": 3.0 * TIME,
    },
    {
        "name": "glide_profile",
        "title": "Glide Profile + Slow Correction",
        "reference": -3.0 * TIME + 40.0 * np.sin(0.012 * TIME),
    },
    {
        "name": "altitude_slow_sine",
        "title": "Altitude Slow Sine",
        "reference": 60.0 * np.sin(0.008 * TIME),
    },
]
PRIMARY_REFERENCE = next(test["reference"] for test in CLEAN_TESTS if test["name"] == "glide_profile")
ENVIRONMENTS = [
    {
        "name": "command_clean",
        "mode": "command",
        "level": "clean",
        "command_noise_std": 0.0,
        "measurement_noise_std": 0.0,
        "gust_std": 0.0,
        "jitter_pct": 0.0,
        "trials": 1,
        "seed": 9101,
    },
    {
        "name": "command_light",
        "mode": "command",
        "level": "light",
        "command_noise_std": 5.0,
        "measurement_noise_std": 0.0,
        "gust_std": 0.25,
        "jitter_pct": 0.05,
        "trials": 200,
        "seed": 9102,
    },
    {
        "name": "command_moderate",
        "mode": "command",
        "level": "moderate",
        "command_noise_std": 10.0,
        "measurement_noise_std": 0.0,
        "gust_std": 0.5,
        "jitter_pct": 0.10,
        "trials": 200,
        "seed": 9103,
    },
    {
        "name": "command_heavy",
        "mode": "command",
        "level": "heavy",
        "command_noise_std": 20.0,
        "measurement_noise_std": 0.0,
        "gust_std": 1.0,
        "jitter_pct": 0.15,
        "trials": 200,
        "seed": 9104,
    },
    {
        "name": "measurement_clean",
        "mode": "measurement",
        "level": "clean",
        "command_noise_std": 0.0,
        "measurement_noise_std": 0.0,
        "gust_std": 0.0,
        "jitter_pct": 0.0,
        "trials": 1,
        "seed": 9201,
    },
    {
        "name": "measurement_light",
        "mode": "measurement",
        "level": "light",
        "command_noise_std": 0.0,
        "measurement_noise_std": 3.0,
        "gust_std": 0.25,
        "jitter_pct": 0.05,
        "trials": 200,
        "seed": 9202,
    },
    {
        "name": "measurement_moderate",
        "mode": "measurement",
        "level": "moderate",
        "command_noise_std": 0.0,
        "measurement_noise_std": 6.0,
        "gust_std": 0.5,
        "jitter_pct": 0.10,
        "trials": 200,
        "seed": 9203,
    },
    {
        "name": "measurement_heavy",
        "mode": "measurement",
        "level": "heavy",
        "command_noise_std": 0.0,
        "measurement_noise_std": 12.0,
        "gust_std": 1.0,
        "jitter_pct": 0.15,
        "trials": 200,
        "seed": 9204,
    },
    {
        "name": "measurement_extreme",
        "mode": "measurement",
        "level": "extreme",
        "command_noise_std": 0.0,
        "measurement_noise_std": 18.0,
        "gust_std": 1.5,
        "jitter_pct": 0.15,
        "trials": 200,
        "seed": 9205,
    },
]


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def decimal_key(value):
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "_")


def summarize(values):
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(array)),
        "std": float(np.std(array)),
        "p10": float(np.percentile(array, 10)),
        "median": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)),
    }


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


def percentile_ci(values):
    array = np.asarray(values, dtype=float)
    return {
        "low": float(np.percentile(array, 2.5)),
        "high": float(np.percentile(array, 97.5)),
    }


def bootstrap_probability_ci(boolean_values, seed):
    array = np.asarray(boolean_values, dtype=float)
    if len(array) == 0:
        return {"low": None, "high": None}
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(BOOTSTRAP_SAMPLES, len(array)))
    probabilities = np.mean(array[indices], axis=1)
    return percentile_ci(probabilities)


def build_jittered_matrices(short_scale=1.0, phugoid_scale=1.0, control_scale=1.0):
    a_matrix = np.array(A_BASE, copy=True)
    b_matrix = np.array(B_BASE, copy=True)

    a_matrix[0, [0, 1, 2]] *= short_scale
    a_matrix[2, [0, 1, 2]] *= short_scale
    a_matrix[1, [1, 2, 3]] *= phugoid_scale
    b_matrix[:, 0] *= control_scale
    return a_matrix, b_matrix


def generate_filtered_noise(std, tau, rng):
    if std <= 0.0:
        return np.zeros_like(TIME)
    dt = float(TIME[1] - TIME[0])
    a = float(np.exp(-dt / tau))
    b = float(std * np.sqrt(max(1.0 - a * a, 0.0)))
    signal = np.zeros_like(TIME)
    white = rng.normal(size=len(TIME))
    for index in range(1, len(TIME)):
        signal[index] = a * signal[index - 1] + b * white[index]
    return signal


def build_inner_loop_state_space(k_theta, k_i_theta, k_q, a_matrix, b_matrix):
    a_cl = np.zeros((6, 6), dtype=float)
    a_cl[:4, :4] = a_matrix
    a_cl[:4, 4] = b_matrix[:, 0]
    a_cl[4, 0] = k_q / TAU_E
    a_cl[4, 3] = k_theta / TAU_E
    a_cl[4, 4] = -1.0 / TAU_E
    a_cl[4, 5] = -k_i_theta / TAU_E
    a_cl[5, 3] = -1.0

    b_cl = np.zeros((6, 1), dtype=float)
    b_cl[4, 0] = -k_theta / TAU_E
    b_cl[5, 0] = 1.0
    c_cl = np.array([[0.0, 0.0, 0.0, 1.0, 0.0, 0.0]], dtype=float)
    d_cl = np.array([[0.0]], dtype=float)
    return a_cl, b_cl, c_cl, d_cl


def build_full_closed_loop(k_theta, k_i_theta, k_q, k_h, k_i_h, a_matrix, b_matrix):
    a_cl = np.zeros((9, 9), dtype=float)
    a_cl[:4, :4] = a_matrix
    a_cl[:4, 5] = b_matrix[:, 0]
    a_cl[4, 2] = -V_TRIM
    a_cl[4, 3] = V_TRIM
    a_cl[5, 0] = k_q / TAU_E
    a_cl[5, 3] = k_theta / TAU_E
    a_cl[5, 5] = -1.0 / TAU_E
    a_cl[5, 6] = (k_theta * k_h) / TAU_E
    a_cl[5, 7] = -k_i_theta / TAU_E
    a_cl[5, 8] = -(k_theta * k_i_h) / TAU_E
    a_cl[6, 4] = 1.0 / TAU_H
    a_cl[6, 6] = -1.0 / TAU_H
    a_cl[7, 3] = -1.0
    a_cl[7, 6] = -k_h
    a_cl[7, 8] = k_i_h
    a_cl[8, 6] = -1.0

    b_cl = np.zeros((9, 4), dtype=float)
    # Inputs: h_ref, measurement_noise, command_noise, vertical_gust
    b_cl[4, 3] = 1.0
    b_cl[5, 0] = -(k_theta * k_h) / TAU_E
    b_cl[5, 2] = -(k_theta * k_h) / TAU_E
    b_cl[6, 1] = 1.0 / TAU_H
    b_cl[7, 0] = k_h
    b_cl[7, 2] = k_h
    b_cl[8, 0] = 1.0
    b_cl[8, 2] = 1.0

    c_all = np.eye(9, dtype=float)
    d_all = np.zeros((9, 4), dtype=float)
    return a_cl, b_cl, c_all, d_all


def step_response_metrics(a_matrix, b_matrix, c_matrix, d_matrix, amplitude=1.0, time=STEP_TIME):
    system = StateSpace(a_matrix, b_matrix, c_matrix, d_matrix)
    _, response, _ = lsim(system, U=amplitude * np.ones_like(time), T=time)
    response = response[:, 0] if response.ndim > 1 else response
    response = np.asarray(response, dtype=float)
    final_value = float(response[-1])
    settle_band = 0.02 * max(abs(final_value), 1e-12)
    violating = np.flatnonzero(np.abs(response - final_value) > settle_band)
    settling_time = 0.0 if len(violating) == 0 else float(time[violating[-1]])
    peak_value = float(np.max(response))
    overshoot = max(0.0, (peak_value - final_value) / max(abs(final_value), 1e-12))
    lower = 0.1 * final_value
    upper = 0.9 * final_value
    rise_start = None
    rise_end = None
    for index, value in enumerate(response):
        if rise_start is None and value >= lower:
            rise_start = float(time[index])
        if rise_end is None and value >= upper:
            rise_end = float(time[index])
            break
    rise_time = None if rise_start is None or rise_end is None else float(rise_end - rise_start)
    return {
        "response": response,
        "final_value": final_value,
        "settling_time_2pct": settling_time,
        "overshoot": overshoot,
        "rise_time_10_90": rise_time,
    }


def bandwidth_3db(a_matrix, b_matrix, c_matrix, d_matrix):
    _, response = freqresp(StateSpace(a_matrix, b_matrix, c_matrix, d_matrix), w=BANDWIDTH_GRID)
    magnitude = np.abs(response)
    crossing = np.where(magnitude <= 1.0 / np.sqrt(2.0))[0]
    return float(BANDWIDTH_GRID[crossing[0]]) if len(crossing) else float(BANDWIDTH_GRID[-1])


def shadow_horizon(time_values, signal_values, epsilon):
    magnitude = np.abs(signal_values)
    peak = float(np.max(magnitude))
    if peak <= 0.0:
        return 0.0
    threshold = epsilon * peak
    above = magnitude > threshold
    if not np.any(above):
        return 0.0
    return float(time_values[np.max(np.flatnonzero(above))])


def shadow_mass_l2(a_matrix, b_matrix, c_matrix):
    gramian = solve_continuous_lyapunov(a_matrix, -(b_matrix @ b_matrix.T))
    return float((c_matrix @ gramian @ c_matrix.T).item())


def slow_band_deficit(a_matrix, b_matrix, c_matrix, d_matrix):
    _, response = freqresp(StateSpace(a_matrix, b_matrix, c_matrix, d_matrix), w=SLOW_BAND_GRID)
    gap = np.abs(1.0 - response) ** 2
    mask = SLOW_BAND_GRID <= SLOW_BAND_LIMIT
    return float(trapz(gap[mask], SLOW_BAND_GRID[mask]))


def altitude_channel_metrics(a_matrix, b_matrix):
    c_altitude = np.array([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]], dtype=float)
    d_altitude = np.array([[0.0]], dtype=float)
    input_ref = b_matrix[:, [0]]

    _, impulse_response = impulse(StateSpace(a_matrix, input_ref, c_altitude, d_altitude), T=IMPULSE_TIME)
    impulse_response = np.squeeze(np.asarray(impulse_response, dtype=float))
    abs_impulse = np.abs(impulse_response)
    return {
        "altitude_bandwidth_3db": bandwidth_3db(a_matrix, input_ref, c_altitude, d_altitude),
        "slow_band_deficit_0_03": slow_band_deficit(a_matrix, input_ref, c_altitude, d_altitude),
        "shadow_horizon_eps_0_02": shadow_horizon(IMPULSE_TIME, impulse_response, 0.02),
        "shadow_mass_l1": float(trapz(abs_impulse, IMPULSE_TIME)),
        "shadow_mass_l2": shadow_mass_l2(a_matrix, input_ref, c_altitude),
    }


def tracking_metrics(altitude_true, altitude_measured, altitude_reference):
    altitude_true = np.asarray(altitude_true, dtype=float)
    altitude_measured = np.asarray(altitude_measured, dtype=float)
    altitude_reference = np.asarray(altitude_reference, dtype=float)
    signed_error = altitude_true - altitude_reference
    observed_error = altitude_measured - altitude_reference
    abs_error = np.abs(signed_error)
    return {
        "true_iae": float(trapz(abs_error, TIME)),
        "true_ise": float(trapz(signed_error**2, TIME)),
        "peak_abs_error": float(np.max(abs_error)),
        "mean_abs_error": float(np.mean(abs_error)),
        "observed_iae": float(trapz(np.abs(observed_error), TIME)),
    }


def identify_short_period_pair(eigenvalues):
    complex_modes = [pole for pole in eigenvalues if abs(np.imag(pole)) > 1e-5]
    if len(complex_modes) >= 2:
        return sorted(complex_modes, key=lambda pole: abs(np.imag(pole)), reverse=True)[:2]
    return sorted(eigenvalues, key=lambda pole: np.real(pole), reverse=True)[:2]


def inner_design_objective(k_vector, zeta_target, a_matrix, b_matrix):
    a_inner, b_inner, c_inner, d_inner = build_inner_loop_state_space(*k_vector, a_matrix, b_matrix)
    eigenvalues = np.linalg.eigvals(a_inner)
    if np.any(np.real(eigenvalues) >= 0.0):
        return 1e9

    pitch_step = step_response_metrics(a_inner, b_inner, c_inner, d_inner, amplitude=1.0, time=np.linspace(0.0, 40.0, 1500))
    short_period_pair = identify_short_period_pair(eigenvalues)
    target_overshoot = np.exp(-np.pi * zeta_target / np.sqrt(max(1.0 - zeta_target**2, 1e-9))) if zeta_target < 1.0 else 0.02

    real_part_penalty = sum((np.real(pole) + 0.8) ** 2 for pole in short_period_pair)
    damping_penalty = 0.0
    for pole in short_period_pair:
        wn = abs(pole)
        if wn > 1e-8:
            damping_penalty += ((-np.real(pole) / wn) - min(zeta_target, 0.98)) ** 2

    stability_penalty = sum(max(np.real(pole) + 0.02, 0.0) ** 2 * 200.0 for pole in eigenvalues)
    overshoot_penalty = (pitch_step["overshoot"] - target_overshoot) ** 2 * 25.0
    final_penalty = (pitch_step["final_value"] - 1.0) ** 2 * 100.0
    gain_penalty = 0.01 * np.sum(np.square(np.log10(np.maximum(k_vector, 1e-6))))
    return real_part_penalty * 100.0 + damping_penalty * 80.0 + stability_penalty + overshoot_penalty + final_penalty + gain_penalty


def tune_inner_loop(zeta_target, a_matrix, b_matrix):
    k_theta_grid = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
    k_i_grid = [1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2, 0.1, 0.5, 1.0, 2.0]
    k_q_grid = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]

    best_seed = None
    for k_theta in k_theta_grid:
        for k_i_theta in k_i_grid:
            for k_q in k_q_grid:
                candidate = np.array([k_theta, k_i_theta, k_q], dtype=float)
                score = inner_design_objective(candidate, zeta_target, a_matrix, b_matrix)
                if best_seed is None or score < best_seed[1]:
                    best_seed = (candidate, score)

    result = minimize(
        lambda log_k: inner_design_objective(np.exp(log_k), zeta_target, a_matrix, b_matrix),
        np.log(best_seed[0]),
        method="Nelder-Mead",
        options={"maxiter": 350, "xatol": 1e-4, "fatol": 1e-4},
    )
    gains = np.exp(result.x)
    a_inner, b_inner, c_inner, d_inner = build_inner_loop_state_space(*gains, a_matrix, b_matrix)
    metrics = step_response_metrics(a_inner, b_inner, c_inner, d_inner, amplitude=1.0, time=np.linspace(0.0, 40.0, 1500))
    short_period_pair = identify_short_period_pair(np.linalg.eigvals(a_inner))
    bandwidth = bandwidth_3db(a_inner, b_inner, c_inner, d_inner)
    return {
        "k_theta": float(gains[0]),
        "k_i_theta": float(gains[1]),
        "k_q": float(gains[2]),
        "pitch_step_settling_time_2pct": metrics["settling_time_2pct"],
        "pitch_step_overshoot": metrics["overshoot"],
        "pitch_step_rise_time_10_90": metrics["rise_time_10_90"],
        "pitch_step_response": metrics["response"],
        "pitch_bandwidth_3db": float(bandwidth),
        "short_period_pair_real": [float(np.real(pole)) for pole in short_period_pair],
        "short_period_pair_imag": [float(np.imag(pole)) for pole in short_period_pair],
        "inner_tuning_residual": float(result.fun),
    }


def outer_design_objective(log_outer_gains, inner_gains, inner_bandwidth, a_matrix, b_matrix):
    k_h, k_i_h = np.exp(log_outer_gains)
    a_full, b_full, _, _ = build_full_closed_loop(
        inner_gains["k_theta"],
        inner_gains["k_i_theta"],
        inner_gains["k_q"],
        k_h,
        k_i_h,
        a_matrix,
        b_matrix,
    )
    eigenvalues = np.linalg.eigvals(a_full)
    if np.any(np.real(eigenvalues) >= 0.0):
        return 1e9

    c_altitude = np.array([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]], dtype=float)
    d_altitude = np.array([[0.0]], dtype=float)
    altitude_step = step_response_metrics(a_full, b_full[:, [0]], c_altitude, d_altitude, amplitude=100.0)
    altitude_bandwidth = bandwidth_3db(a_full, b_full[:, [0]], c_altitude, d_altitude)
    target_bandwidth = 0.15 * inner_bandwidth
    target_overshoot = np.exp(-np.pi * 0.9 / np.sqrt(max(1.0 - 0.9**2, 1e-9)))
    stability_penalty = max(np.max(np.real(eigenvalues)) + 0.02, 0.0) ** 2 * 300.0
    bandwidth_penalty = (np.log10(max(altitude_bandwidth, 1e-8)) - np.log10(target_bandwidth)) ** 2 * 100.0
    overshoot_penalty = (altitude_step["overshoot"] - target_overshoot) ** 2 * 60.0
    final_penalty = (altitude_step["final_value"] - 100.0) ** 2 * 0.02
    gain_penalty = 0.01 * np.sum(np.square(np.log10(np.maximum([k_h * 1e4, k_i_h * 1e6], 1e-6))))
    return bandwidth_penalty + overshoot_penalty + final_penalty + stability_penalty + gain_penalty


def tune_outer_loop(inner_gains, a_matrix, b_matrix):
    inner_bandwidth = inner_gains["pitch_bandwidth_3db"]
    k_h_grid = [1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3]
    k_i_h_grid = [1e-7, 3e-7, 1e-6, 3e-6, 1e-5, 3e-5, 1e-4]

    best_seed = None
    for k_h in k_h_grid:
        for k_i_h in k_i_h_grid:
            score = outer_design_objective(np.log([k_h, k_i_h]), inner_gains, inner_bandwidth, a_matrix, b_matrix)
            if best_seed is None or score < best_seed[1]:
                best_seed = ((k_h, k_i_h), score)

    result = minimize(
        lambda log_gains: outer_design_objective(log_gains, inner_gains, inner_bandwidth, a_matrix, b_matrix),
        np.log(np.array(best_seed[0], dtype=float)),
        method="Nelder-Mead",
        options={"maxiter": 300, "xatol": 1e-4, "fatol": 1e-4},
    )
    k_h, k_i_h = np.exp(result.x)
    a_full, b_full, _, _ = build_full_closed_loop(
        inner_gains["k_theta"],
        inner_gains["k_i_theta"],
        inner_gains["k_q"],
        k_h,
        k_i_h,
        a_matrix,
        b_matrix,
    )
    c_altitude = np.array([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]], dtype=float)
    d_altitude = np.array([[0.0]], dtype=float)
    altitude_step = step_response_metrics(a_full, b_full[:, [0]], c_altitude, d_altitude, amplitude=100.0)
    altitude_bandwidth = bandwidth_3db(a_full, b_full[:, [0]], c_altitude, d_altitude)
    return {
        "k_h": float(k_h),
        "k_i_h": float(k_i_h),
        "altitude_step_settling_time_2pct": altitude_step["settling_time_2pct"],
        "altitude_step_overshoot": altitude_step["overshoot"],
        "altitude_step_rise_time_10_90": altitude_step["rise_time_10_90"],
        "altitude_step_response": altitude_step["response"],
        "altitude_bandwidth_3db_step": float(altitude_bandwidth),
        "outer_tuning_residual": float(result.fun),
    }


def simulate_closed_loop(k_gains, reference_signal, measurement_noise=None, command_noise=None, gust_signal=None, a_matrix=None, b_matrix=None):
    if measurement_noise is None:
        measurement_noise = np.zeros_like(TIME)
    if command_noise is None:
        command_noise = np.zeros_like(TIME)
    if gust_signal is None:
        gust_signal = np.zeros_like(TIME)

    a_full, b_full, c_full, d_full = build_full_closed_loop(
        k_gains["k_theta"],
        k_gains["k_i_theta"],
        k_gains["k_q"],
        k_gains["k_h"],
        k_gains["k_i_h"],
        a_matrix,
        b_matrix,
    )
    eigenvalues = np.linalg.eigvals(a_full)
    if np.any(np.real(eigenvalues) >= 0.0):
        return None

    system = StateSpace(a_full, b_full, c_full, d_full)
    inputs = np.column_stack([reference_signal, measurement_noise, command_noise, gust_signal])
    _, output, _ = lsim(system, U=inputs, T=TIME)
    altitude_true = output[:, 4]
    altitude_measured = output[:, 6]
    metrics = tracking_metrics(altitude_true, altitude_measured, reference_signal)
    return {
        "altitude_true": altitude_true,
        "altitude_measured": altitude_measured,
        "metrics": metrics,
        "eigenvalues": eigenvalues,
        "full_state_matrix": a_full,
        "input_matrix": b_full,
    }


def nominal_design_rows():
    rows = []
    a_nominal, b_nominal = build_jittered_matrices()
    for zeta in ZETAS:
        inner_gains = tune_inner_loop(zeta, a_nominal, b_nominal)
        outer_gains = tune_outer_loop(inner_gains, a_nominal, b_nominal)
        gains = {
            **inner_gains,
            **outer_gains,
        }
        simulation = simulate_closed_loop(gains, PRIMARY_REFERENCE, a_matrix=a_nominal, b_matrix=b_nominal)
        altitude_metrics = altitude_channel_metrics(simulation["full_state_matrix"], simulation["input_matrix"])
        rows.append({
            "zeta": float(zeta),
            "system_state_matrix": simulation["full_state_matrix"],
            "system_input_matrix": simulation["input_matrix"],
            "full_eigenvalues": simulation["eigenvalues"],
            **gains,
            **altitude_metrics,
        })
    return rows


def clean_tracking_rows(system_rows):
    rows = []
    lookup = {}
    a_nominal, b_nominal = build_jittered_matrices()
    for system_row in system_rows:
        zeta = system_row["zeta"]
        lookup[zeta] = {}
        gains = {
            key: system_row[key]
            for key in ("k_theta", "k_i_theta", "k_q", "k_h", "k_i_h")
        }
        for test in CLEAN_TESTS:
            simulation = simulate_closed_loop(gains, test["reference"], a_matrix=a_nominal, b_matrix=b_nominal)
            metrics = simulation["metrics"]
            row = {
                "test_name": test["name"],
                "test_title": test["title"],
                "zeta": float(zeta),
                "true_iae": metrics["true_iae"],
                "true_ise": metrics["true_ise"],
                "peak_abs_error": metrics["peak_abs_error"],
                "mean_abs_error": metrics["mean_abs_error"],
            }
            rows.append(row)
            lookup[zeta][test["name"]] = row
    return rows, lookup


def run_environment_sweep(system_rows, clean_lookup):
    trial_rows = []
    grid_rows = []
    pairwise_rows = []
    bootstrap_summary = {}

    gains_lookup = {
        row["zeta"]: {
            key: row[key]
            for key in ("k_theta", "k_i_theta", "k_q", "k_h", "k_i_h")
        }
        for row in system_rows
    }

    for environment in ENVIRONMENTS:
        rng = np.random.default_rng(environment["seed"])
        per_zeta = {zeta: [] for zeta in ZETAS}
        scenarios = []

        for trial_index in range(environment["trials"]):
            jitter = environment["jitter_pct"]
            short_scale = 1.0 if jitter == 0.0 else float(rng.uniform(1.0 - jitter, 1.0 + jitter))
            phugoid_scale = 1.0 if jitter == 0.0 else float(rng.uniform(1.0 - jitter, 1.0 + jitter))
            control_scale = 1.0 if jitter == 0.0 else float(rng.uniform(1.0 - jitter, 1.0 + jitter))
            a_trial, b_trial = build_jittered_matrices(short_scale, phugoid_scale, control_scale)

            measurement_noise = np.zeros_like(TIME)
            command_noise = np.zeros_like(TIME)
            if environment["measurement_noise_std"] > 0.0:
                measurement_noise = environment["measurement_noise_std"] * rng.normal(size=len(TIME))
            if environment["command_noise_std"] > 0.0:
                command_noise = environment["command_noise_std"] * rng.normal(size=len(TIME))
            gust_signal = generate_filtered_noise(environment["gust_std"], TAU_G, rng)

            scenario = {
                "environment_name": environment["name"],
                "mode": environment["mode"],
                "level": environment["level"],
                "noise_std": environment["measurement_noise_std"] if environment["mode"] == "measurement" else environment["command_noise_std"],
                "short_scale": short_scale,
                "phugoid_scale": phugoid_scale,
                "control_scale": control_scale,
                "per_zeta": {},
            }

            for zeta in ZETAS:
                gains = gains_lookup[zeta]
                simulation = simulate_closed_loop(
                    gains,
                    PRIMARY_REFERENCE,
                    measurement_noise=measurement_noise,
                    command_noise=command_noise,
                    gust_signal=gust_signal,
                    a_matrix=a_trial,
                    b_matrix=b_trial,
                )

                stable = simulation is not None
                if stable:
                    metrics = simulation["metrics"]
                    c_altitude = np.array([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]], dtype=float)
                    input_ref = simulation["input_matrix"][:, [0]]
                    shadow_mass_trial = shadow_mass_l2(simulation["full_state_matrix"], input_ref, c_altitude)
                    nuisance_power_scalar = (
                        environment["command_noise_std"] ** 2 + environment["gust_std"] ** 2
                        if environment["mode"] == "command"
                        else environment["measurement_noise_std"] ** 2 + environment["gust_std"] ** 2
                    )
                    row = {
                        "environment_name": environment["name"],
                        "mode": environment["mode"],
                        "level": environment["level"],
                        "trial_index": trial_index,
                        "zeta": float(zeta),
                        "noise_std": float(environment["measurement_noise_std"] if environment["mode"] == "measurement" else environment["command_noise_std"]),
                        "gust_std": float(environment["gust_std"]),
                        "short_period_scale": short_scale,
                        "phugoid_scale": phugoid_scale,
                        "control_scale": control_scale,
                        "stability_flag": 1,
                        "true_iae": metrics["true_iae"],
                        "true_ise": metrics["true_ise"],
                        "peak_abs_error": metrics["peak_abs_error"],
                        "mean_abs_error": metrics["mean_abs_error"],
                        "observed_iae": metrics["observed_iae"] if environment["mode"] == "measurement" else None,
                        "excess_true_iae_over_clean": metrics["true_iae"] - clean_lookup[zeta]["glide_profile"]["true_iae"],
                        "shadow_mass_l2_trial": shadow_mass_trial,
                        "occupancy_proxy_l2": nuisance_power_scalar * shadow_mass_trial,
                        "nuisance_power_scalar": nuisance_power_scalar,
                    }
                else:
                    row = {
                        "environment_name": environment["name"],
                        "mode": environment["mode"],
                        "level": environment["level"],
                        "trial_index": trial_index,
                        "zeta": float(zeta),
                        "noise_std": float(environment["measurement_noise_std"] if environment["mode"] == "measurement" else environment["command_noise_std"]),
                        "gust_std": float(environment["gust_std"]),
                        "short_period_scale": short_scale,
                        "phugoid_scale": phugoid_scale,
                        "control_scale": control_scale,
                        "stability_flag": 0,
                        "true_iae": None,
                        "true_ise": None,
                        "peak_abs_error": None,
                        "mean_abs_error": None,
                        "observed_iae": None,
                        "excess_true_iae_over_clean": None,
                        "shadow_mass_l2_trial": None,
                        "occupancy_proxy_l2": None,
                        "nuisance_power_scalar": float(
                            environment["command_noise_std"] ** 2 + environment["gust_std"] ** 2
                            if environment["mode"] == "command"
                            else environment["measurement_noise_std"] ** 2 + environment["gust_std"] ** 2
                        ),
                    }

                trial_rows.append(row)
                per_zeta[zeta].append(row)
                scenario["per_zeta"][zeta] = row
            scenarios.append(scenario)

        env_bootstrap = environment_bootstrap(environment, scenarios)
        bootstrap_summary[environment["name"]] = env_bootstrap

        for zeta in ZETAS:
            rows = per_zeta[zeta]
            stable_rows = [row for row in rows if row["stability_flag"] == 1]
            stability_rate = float(np.mean([row["stability_flag"] for row in rows]))
            true_iae_values = [row["true_iae"] for row in stable_rows]
            true_ise_values = [row["true_ise"] for row in stable_rows]
            peak_values = [row["peak_abs_error"] for row in stable_rows]
            mean_values = [row["mean_abs_error"] for row in stable_rows]
            excess_values = [row["excess_true_iae_over_clean"] for row in stable_rows]
            shadow_values = [row["shadow_mass_l2_trial"] for row in stable_rows]
            occupancy_values = [row["occupancy_proxy_l2"] for row in stable_rows]
            observed_values = [row["observed_iae"] for row in stable_rows if row["observed_iae"] is not None]
            true_stats = summarize(true_iae_values)
            ci = env_bootstrap["mean_true_iae_ci"][decimal_key(zeta)]

            grid_rows.append({
                "environment_name": environment["name"],
                "mode": environment["mode"],
                "level": environment["level"],
                "zeta": float(zeta),
                "noise_std": float(environment["measurement_noise_std"] if environment["mode"] == "measurement" else environment["command_noise_std"]),
                "gust_std": float(environment["gust_std"]),
                "mean_true_iae": true_stats["mean"],
                "std_true_iae": true_stats["std"],
                "p10_true_iae": true_stats["p10"],
                "median_true_iae": true_stats["median"],
                "p90_true_iae": true_stats["p90"],
                "ci_true_iae_low": ci["low"],
                "ci_true_iae_high": ci["high"],
                "mean_true_ise": float(np.mean(true_ise_values)),
                "mean_peak_abs_error": float(np.mean(peak_values)),
                "mean_abs_error": float(np.mean(mean_values)),
                "mean_excess_true_iae_over_clean": float(np.mean(excess_values)),
                "mean_shadow_mass_l2_trial": float(np.mean(shadow_values)),
                "mean_occupancy_proxy_l2": float(np.mean(occupancy_values)),
                "mean_observed_iae": None if len(observed_values) == 0 else float(np.mean(observed_values)),
                "stability_rate": stability_rate,
                "valid_trial_count": len(stable_rows),
                "bootstrap_best_frequency": env_bootstrap["best_zeta_frequency"][decimal_key(zeta)],
            })

        if environment["mode"] == "measurement":
            pairwise_rows.extend(environment_pairwise_rows(environment, scenarios))

    return trial_rows, grid_rows, pairwise_rows, bootstrap_summary


def environment_bootstrap(environment, scenarios):
    valid_scenarios = [
        scenario for scenario in scenarios
        if all(
            scenario["per_zeta"][zeta]["stability_flag"] == 1 and scenario["per_zeta"][zeta]["true_iae"] is not None
            for zeta in ZETAS
        )
    ]
    if len(valid_scenarios) == 0:
        null_ci = {decimal_key(zeta): {"low": None, "high": None} for zeta in ZETAS}
        null_frequency = {decimal_key(zeta): 0.0 for zeta in ZETAS}
        return {
            "mean_true_iae_ci": null_ci,
            "best_zeta": {"mean": None, "low": None, "high": None},
            "best_zeta_frequency": null_frequency,
        }

    matrix = np.array(
        [[scenario["per_zeta"][zeta]["true_iae"] for zeta in ZETAS] for scenario in valid_scenarios],
        dtype=float,
    )
    if len(valid_scenarios) == 1:
        means = np.mean(matrix, axis=0)
        best_index = int(np.argmin(means))
        best_zeta = ZETAS[best_index]
        return {
            "mean_true_iae_ci": {
                decimal_key(zeta): {"low": float(means[index]), "high": float(means[index])}
                for index, zeta in enumerate(ZETAS)
            },
            "best_zeta": {"mean": float(best_zeta), "low": float(best_zeta), "high": float(best_zeta)},
            "best_zeta_frequency": {decimal_key(zeta): 1.0 if zeta == best_zeta else 0.0 for zeta in ZETAS},
        }

    rng = np.random.default_rng(environment["seed"] + 15000)
    indices = rng.integers(0, len(valid_scenarios), size=(BOOTSTRAP_SAMPLES, len(valid_scenarios)))
    sampled_means = np.mean(matrix[indices], axis=1)
    best_indices = np.argmin(sampled_means, axis=1)
    best_zetas = np.array([ZETAS[index] for index in best_indices], dtype=float)
    return {
        "mean_true_iae_ci": {
            decimal_key(zeta): {
                "low": float(np.percentile(sampled_means[:, index], 2.5)),
                "high": float(np.percentile(sampled_means[:, index], 97.5)),
            }
            for index, zeta in enumerate(ZETAS)
        },
        "best_zeta": {
            "mean": float(np.mean(best_zetas)),
            "low": float(np.percentile(best_zetas, 2.5)),
            "high": float(np.percentile(best_zetas, 97.5)),
        },
        "best_zeta_frequency": {
            decimal_key(zeta): float(np.mean(best_zetas == zeta))
            for zeta in ZETAS
        },
    }


def environment_pairwise_rows(environment, scenarios):
    rows = []
    for pair_index, (left_zeta, right_zeta) in enumerate(PAIRWISE_COMPARISONS):
        valid_scenarios = [
            scenario for scenario in scenarios
            if scenario["per_zeta"][left_zeta]["stability_flag"] == 1
            and scenario["per_zeta"][right_zeta]["stability_flag"] == 1
        ]
        true_wins = np.array([
            scenario["per_zeta"][left_zeta]["true_iae"] < scenario["per_zeta"][right_zeta]["true_iae"]
            for scenario in valid_scenarios
        ], dtype=float)
        observed_wins = np.array([
            scenario["per_zeta"][left_zeta]["observed_iae"] < scenario["per_zeta"][right_zeta]["observed_iae"]
            for scenario in valid_scenarios
        ], dtype=float)
        true_ci = bootstrap_probability_ci(true_wins, environment["seed"] + 17000 + pair_index)
        observed_ci = bootstrap_probability_ci(observed_wins, environment["seed"] + 18000 + pair_index)
        rows.append({
            "environment_name": environment["name"],
            "mode": environment["mode"],
            "level": environment["level"],
            "noise_std": float(environment["measurement_noise_std"]),
            "left_zeta": float(left_zeta),
            "right_zeta": float(right_zeta),
            "valid_pair_trial_count": len(valid_scenarios),
            "true_winner_probability_left": float(np.mean(true_wins)),
            "true_winner_ci_low": true_ci["low"],
            "true_winner_ci_high": true_ci["high"],
            "observed_winner_probability_left": float(np.mean(observed_wins)),
            "observed_winner_ci_low": observed_ci["low"],
            "observed_winner_ci_high": observed_ci["high"],
        })
    return rows


def matched_pair_rows(system_rows, clean_lookup):
    rows = []
    for left_index, left in enumerate(system_rows):
        for right in system_rows[left_index + 1:]:
            settling_left = left["pitch_step_settling_time_2pct"]
            settling_right = right["pitch_step_settling_time_2pct"]
            settling_mean = 0.5 * (settling_left + settling_right)
            settling_diff_pct = 0.0 if settling_mean == 0.0 else abs(settling_left - settling_right) / settling_mean * 100.0
            iae_left = clean_lookup[left["zeta"]]["glide_profile"]["true_iae"]
            iae_right = clean_lookup[right["zeta"]]["glide_profile"]["true_iae"]
            better_row, worse_row = (left, right) if iae_left <= iae_right else (right, left)
            rows.append({
                "left_zeta": float(left["zeta"]),
                "right_zeta": float(right["zeta"]),
                "settling_diff_pct": float(settling_diff_pct),
                "left_pitch_settling": settling_left,
                "right_pitch_settling": settling_right,
                "left_glide_iae": iae_left,
                "right_glide_iae": iae_right,
                "iae_ratio": float(max(iae_left, iae_right) / max(min(iae_left, iae_right), 1e-12)),
                "better_zeta": float(better_row["zeta"]),
                "worse_zeta": float(worse_row["zeta"]),
            })
    rows.sort(key=lambda row: row["iae_ratio"], reverse=True)
    return rows


def summary_payload(system_rows, clean_rows, clean_lookup, grid_rows, pairwise_rows, bootstrap_summary):
    primary_rows = [row for row in clean_rows if row["test_name"] == "glide_profile"]
    clean_iae_lookup = {row["zeta"]: row["true_iae"] for row in primary_rows}
    clean_best_zeta = min(clean_iae_lookup, key=clean_iae_lookup.get)
    rank_fidelity = {
        "pitch_step_settling_time_2pct": spearman_corr(
            [row["pitch_step_settling_time_2pct"] for row in system_rows],
            [clean_iae_lookup[row["zeta"]] for row in system_rows],
        ),
        "altitude_bandwidth_3db": spearman_corr(
            [row["altitude_bandwidth_3db"] for row in system_rows],
            [clean_iae_lookup[row["zeta"]] for row in system_rows],
        ),
        "slow_band_deficit_0_03": spearman_corr(
            [row["slow_band_deficit_0_03"] for row in system_rows],
            [clean_iae_lookup[row["zeta"]] for row in system_rows],
        ),
        "shadow_mass_l1": spearman_corr(
            [row["shadow_mass_l1"] for row in system_rows],
            [clean_iae_lookup[row["zeta"]] for row in system_rows],
        ),
        "shadow_mass_l2": spearman_corr(
            [row["shadow_mass_l2"] for row in system_rows],
            [clean_iae_lookup[row["zeta"]] for row in system_rows],
        ),
    }

    matched_pairs = matched_pair_rows(system_rows, clean_lookup)
    supportive_pairs = [
        row for row in matched_pairs
        if row["settling_diff_pct"] <= 15.0 and row["iae_ratio"] >= 3.0
    ]

    best_by_environment = {}
    for environment in ENVIRONMENTS:
        env_rows = [row for row in grid_rows if row["environment_name"] == environment["name"]]
        best_row = min(env_rows, key=lambda row: row["mean_true_iae"])
        long_shadow_row = next(row for row in env_rows if abs(row["zeta"] - LONG_SHADOW_ZETA) < 1e-12)
        best_by_environment[environment["name"]] = {
            "mode": environment["mode"],
            "level": environment["level"],
            "noise_std": float(environment["measurement_noise_std"] if environment["mode"] == "measurement" else environment["command_noise_std"]),
            "best_zeta": float(best_row["zeta"]),
            "best_mean_true_iae": best_row["mean_true_iae"],
            "best_zeta_ci_low": bootstrap_summary[environment["name"]]["best_zeta"]["low"],
            "best_zeta_ci_high": bootstrap_summary[environment["name"]]["best_zeta"]["high"],
            "best_zeta_frequency": bootstrap_summary[environment["name"]]["best_zeta_frequency"],
            "long_shadow_gap_vs_best": float(long_shadow_row["mean_true_iae"] - best_row["mean_true_iae"]),
            "min_stability_rate": float(min(row["stability_rate"] for row in env_rows)),
        }

    noisy_rows = [row for row in grid_rows if row["level"] != "clean"]
    occupancy_corr = spearman_corr(
        [row["mean_occupancy_proxy_l2"] for row in noisy_rows],
        [row["mean_excess_true_iae_over_clean"] for row in noisy_rows],
    )
    nuisance_corr = spearman_corr(
        [row["noise_std"] ** 2 + row["gust_std"] ** 2 for row in noisy_rows],
        [row["mean_excess_true_iae_over_clean"] for row in noisy_rows],
    )
    per_mode_corr = {}
    for mode in ("command", "measurement"):
        mode_rows = [row for row in noisy_rows if row["mode"] == mode]
        per_mode_corr[mode] = {
            "occupancy_proxy_l2_vs_excess_true_iae": spearman_corr(
                [row["mean_occupancy_proxy_l2"] for row in mode_rows],
                [row["mean_excess_true_iae_over_clean"] for row in mode_rows],
            ),
            "raw_nuisance_power_vs_excess_true_iae": spearman_corr(
                [row["noise_std"] ** 2 + row["gust_std"] ** 2 for row in mode_rows],
                [row["mean_excess_true_iae_over_clean"] for row in mode_rows],
            ),
        }

    return {
        "study": "out-of-family-aircraft-longitudinal-autopilot",
        "model": {
            "base_aircraft": "Modified F-8 longitudinal linearization",
            "trim_altitude_ft": ALTITUDE_TRIM_FT,
            "trim_speed_ft_per_s": V_TRIM,
            "state_order": ["q", "u", "alpha", "theta"],
            "flight_path_relation": "gamma = theta - alpha",
        },
        "primary_mission": "glide_profile",
        "clean_rank_fidelity": rank_fidelity,
        "matched_pairs": {
            "top_supportive_pair": supportive_pairs[0] if supportive_pairs else None,
            "pair_count_meeting_threshold": len(supportive_pairs),
            "null_report": None if supportive_pairs else "No pair met both pitch-step settling <= 15% and glide-profile IAE ratio >= 3x.",
            "top_pairs_by_iae_ratio": matched_pairs[:6],
        },
        "best_design_by_environment": best_by_environment,
        "occupancy_proxy_summary": {
            "global_occupancy_proxy_vs_excess_true_iae_spearman": occupancy_corr,
            "global_raw_nuisance_power_vs_excess_true_iae_spearman": nuisance_corr,
            "per_mode": per_mode_corr,
        },
        "pairwise_reliability": {
            f"{left_zeta}_vs_{right_zeta}": [
                row for row in pairwise_rows
                if abs(row["left_zeta"] - left_zeta) < 1e-12 and abs(row["right_zeta"] - right_zeta) < 1e-12
            ]
            for left_zeta, right_zeta in PAIRWISE_COMPARISONS
        },
        "claim_support": {
            "clean_slow_tracking_separation_exists": bool(
                clean_iae_lookup[0.707] / max(clean_iae_lookup[clean_best_zeta], 1e-12) >= 1.10
            ),
            "matched_pair_support_exists": len(supportive_pairs) > 0,
            "nuisance_driven_inward_movement_exists": any(
                abs(best_by_environment[environment["name"]]["best_zeta"] - clean_best_zeta) > 1e-12
                for environment in ENVIRONMENTS
                if environment["level"] != "clean"
            ),
            "occupancy_proxy_beats_raw_nuisance_by_0_10": bool(
                occupancy_corr is not None and nuisance_corr is not None and occupancy_corr - nuisance_corr >= 0.10
            ) or any(
                (
                    per_mode_corr[mode]["occupancy_proxy_l2_vs_excess_true_iae"] is not None
                    and per_mode_corr[mode]["raw_nuisance_power_vs_excess_true_iae"] is not None
                    and per_mode_corr[mode]["occupancy_proxy_l2_vs_excess_true_iae"]
                    - per_mode_corr[mode]["raw_nuisance_power_vs_excess_true_iae"] >= 0.10
                )
                for mode in per_mode_corr
            ),
        },
    }


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def plot_family_overview(system_rows, clean_lookup):
    figure, axes = plt.subplots(2, 2, figsize=(14.0, 9.8))
    representative = [0.15, 0.25, 0.35, 0.707, 1.0]
    color_map = {
        0.15: LIGHT_SHADOW_COLOR,
        0.25: "#f1a340",
        0.35: MEMORY_COLOR,
        0.707: FAST_COLOR,
        1.0: NOISE_COLOR,
    }

    ax = axes[0, 0]
    for row in system_rows:
        if row["zeta"] in representative:
            ax.plot(np.linspace(0.0, 40.0, len(row["pitch_step_response"])), row["pitch_step_response"], linewidth=2.0, color=color_map[row["zeta"]], label=f"zeta = {row['zeta']:.3g}")
    style_panel(ax, "Pitch Step Responses", "Time t (seconds)", "Pitch Angle theta")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    add_takeaway(ax, "The aircraft family supports a usable matched-transient sweep rather than a single tuning.", "lower right")

    ax = axes[0, 1]
    for row in system_rows:
        poles = row["full_eigenvalues"]
        ax.scatter(np.real(poles), np.imag(poles), s=50, color=color_map.get(row["zeta"], MEMORY_COLOR), label=f"zeta = {row['zeta']:.3g}")
    style_panel(ax, "Full Closed-Loop Pole Map", "Real Axis", "Imaginary Axis")
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys(), frameon=False, fontsize=9, loc="lower left")
    add_takeaway(ax, "This is a domain-specific aircraft autopilot family, not a synthetic transfer-function sweep.", "upper left")

    ax = axes[1, 0]
    ax.plot([row["zeta"] for row in system_rows], [row["pitch_step_settling_time_2pct"] for row in system_rows], color=SETTLING_COLOR, marker="o", linewidth=2.2)
    style_panel(ax, "Pitch-Step Settling Across the Family", "Damping Ratio zeta", "2% Settling Time (s)")
    add_takeaway(ax, "The nominal pitch benchmark moves far less than the mission-tracking cost.", "upper left")

    ax = axes[1, 1]
    ax.plot([row["zeta"] for row in system_rows], [clean_lookup[row["zeta"]]["glide_profile"]["true_iae"] for row in system_rows], color=LIGHT_SHADOW_COLOR, marker="o", linewidth=2.2)
    style_panel(ax, "Clean Glide-Profile Tracking Cost", "Damping Ratio zeta", "IAE")
    add_takeaway(ax, "The mission-level tracking ordering is not the same as the transient-summary ordering.", "upper right")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "aircraft_autopilot_family_overview.png")
    plt.close(figure)


def plot_settling_blind_spot(system_rows, clean_lookup, matched_pairs):
    figure, axes = plt.subplots(2, 2, figsize=(14.0, 9.8))
    clean_iae = [clean_lookup[row["zeta"]]["glide_profile"]["true_iae"] for row in system_rows]
    point_colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(system_rows)))

    ax = axes[0, 0]
    ax.scatter([row["pitch_step_settling_time_2pct"] for row in system_rows], clean_iae, s=90, c=point_colors)
    for row in system_rows:
        ax.annotate(f"{row['zeta']:.3g}", (row["pitch_step_settling_time_2pct"], clean_lookup[row["zeta"]]["glide_profile"]["true_iae"]), xytext=(4, 4), textcoords="offset points", fontsize=9)
    style_panel(ax, "Pitch-Step Settling vs Glide-Profile Cost", "Pitch 2% Settling Time (s)", "Glide-Profile IAE")

    ax = axes[0, 1]
    ax.scatter([row["slow_band_deficit_0_03"] for row in system_rows], clean_iae, s=90, c=point_colors)
    for row in system_rows:
        ax.annotate(f"{row['zeta']:.3g}", (row["slow_band_deficit_0_03"], clean_lookup[row["zeta"]]["glide_profile"]["true_iae"]), xytext=(4, 4), textcoords="offset points", fontsize=9)
    style_panel(ax, "Slow-Band Deficit vs Glide-Profile Cost", "Slow-Band Deficit [0, 0.03]", "Glide-Profile IAE")

    ax = axes[1, 0]
    ax.scatter([row["shadow_mass_l2"] for row in system_rows], clean_iae, s=90, c=point_colors)
    for row in system_rows:
        ax.annotate(f"{row['zeta']:.3g}", (row["shadow_mass_l2"], clean_lookup[row["zeta"]]["glide_profile"]["true_iae"]), xytext=(4, 4), textcoords="offset points", fontsize=9)
    style_panel(ax, "Shadow Mass vs Glide-Profile Cost", "Shadow Mass L2", "Glide-Profile IAE")

    ax = axes[1, 1]
    supportive_pairs = [row for row in matched_pairs if row["settling_diff_pct"] <= 15.0][:5]
    if len(supportive_pairs) > 0:
        labels = [f"{row['better_zeta']:.3g} vs {row['worse_zeta']:.3g}" for row in supportive_pairs]
        ratios = [row["iae_ratio"] for row in supportive_pairs]
        bars = ax.barh(labels, ratios, color=MATCHED_PAIR_COLOR)
        ax.invert_yaxis()
        for bar, row in zip(bars, supportive_pairs):
            ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2.0, f"{row['settling_diff_pct']:.1f}% pitch-step gap", va="center", fontsize=9)
        style_panel(ax, "Best Matched-Transient Separations", "Glide-Profile IAE Ratio", "")
        add_takeaway(ax, "Near-matched pitch transients can still conceal large mission-tracking gaps.", "lower right")
    else:
        style_panel(ax, "Best Matched-Transient Separations", "Glide-Profile IAE Ratio", "")
        ax.text(0.5, 0.5, "No pair met the\n<=15% pitch-step gap filter.", ha="center", va="center", transform=ax.transAxes, fontsize=12)
        add_takeaway(ax, "The aircraft family still matters, but the matched-pair threshold was not met.", "lower right")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "aircraft_autopilot_settling_blind_spot.png")
    plt.close(figure)


def plot_noise_conditioned_optimum(grid_rows, bootstrap_summary):
    figure, axes = plt.subplots(2, 2, figsize=(14.0, 9.8))

    def plot_mode_curves(ax, mode):
        for environment in [env for env in ENVIRONMENTS if env["mode"] == mode]:
            env_rows = sorted([row for row in grid_rows if row["environment_name"] == environment["name"]], key=lambda row: row["zeta"])
            level = env_rows[0]["level"]
            zetas = [row["zeta"] for row in env_rows]
            means = [row["mean_true_iae"] for row in env_rows]
            lows = [row["ci_true_iae_low"] for row in env_rows]
            highs = [row["ci_true_iae_high"] for row in env_rows]
            color = LEVEL_COLORS[level]
            ax.plot(zetas, means, marker="o", linewidth=2.2, color=color, label=LEVEL_LABELS[level])
            ax.fill_between(zetas, lows, highs, color=color, alpha=0.18)
        style_panel(ax, f"{mode.capitalize()}-Side Nuisance", "Damping Ratio zeta", "Mean Glide-Profile IAE")
        ax.legend(frameon=False, ncol=2, fontsize=9)

    plot_mode_curves(axes[0, 0], "command")
    add_takeaway(axes[0, 0], "Command-side nuisance shifts the preferred autopilot inward from the clean low-damping edge.", "upper left")
    plot_mode_curves(axes[0, 1], "measurement")
    add_takeaway(axes[0, 1], "Measurement-side nuisance reshapes the optimum again through the sensor channel.", "upper left")

    def plot_best_path(ax, mode):
        environments = [env for env in ENVIRONMENTS if env["mode"] == mode]
        x_values = np.arange(len(environments))
        means = [bootstrap_summary[env["name"]]["best_zeta"]["mean"] for env in environments]
        lows = [bootstrap_summary[env["name"]]["best_zeta"]["low"] for env in environments]
        highs = [bootstrap_summary[env["name"]]["best_zeta"]["high"] for env in environments]
        color = MODE_COLORS[mode]
        ax.plot(x_values, means, color=color, marker="o", linewidth=2.4)
        ax.fill_between(x_values, lows, highs, color=color, alpha=0.20)
        ax.set_xticks(x_values)
        ax.set_xticklabels([LEVEL_LABELS[env["level"]] for env in environments])
        style_panel(ax, f"Best-zeta Path: {mode.capitalize()} Side", "Environment Severity", "Bootstrap Best zeta")

    plot_best_path(axes[1, 0], "command")
    add_takeaway(axes[1, 0], "The clean optimum need not stay optimal once slow nuisance starts accumulating.", "upper left")
    plot_best_path(axes[1, 1], "measurement")
    add_takeaway(axes[1, 1], "The sensor side can move the preferred design through a different channel than command noise.", "upper left")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "aircraft_autopilot_noise_conditioned_optimum.png")
    plt.close(figure)


def plot_shadow_mass_occupancy(grid_rows):
    figure, axes = plt.subplots(1, 2, figsize=(14.0, 5.6))
    noisy_rows = [row for row in grid_rows if row["level"] != "clean"]

    ax = axes[0]
    for mode in ("command", "measurement"):
        mode_rows = [row for row in noisy_rows if row["mode"] == mode]
        ax.scatter(
            [row["mean_occupancy_proxy_l2"] for row in mode_rows],
            [row["mean_excess_true_iae_over_clean"] for row in mode_rows],
            s=85,
            alpha=0.85,
            color=MODE_COLORS[mode],
            label=mode.capitalize(),
        )
    style_panel(ax, "Occupancy Proxy vs Excess Mission Penalty", "Nuisance Power x Shadow Mass L2", "Mean Excess Glide-Profile IAE")
    ax.legend(frameon=False)
    occupancy_corr = spearman_corr(
        [row["mean_occupancy_proxy_l2"] for row in noisy_rows],
        [row["mean_excess_true_iae_over_clean"] for row in noisy_rows],
    )
    nuisance_corr = spearman_corr(
        [row["noise_std"] ** 2 + row["gust_std"] ** 2 for row in noisy_rows],
        [row["mean_excess_true_iae_over_clean"] for row in noisy_rows],
    )
    add_takeaway(ax, f"Global Spearman: occupancy = {occupancy_corr:.2f}, raw nuisance = {nuisance_corr:.2f}", "lower right")

    ax = axes[1]
    for mode in ("command", "measurement"):
        mode_points = []
        for environment in [env for env in ENVIRONMENTS if env["mode"] == mode]:
            env_rows = [row for row in grid_rows if row["environment_name"] == environment["name"]]
            best_row = min(env_rows, key=lambda row: row["mean_true_iae"])
            long_shadow_row = next(row for row in env_rows if abs(row["zeta"] - LONG_SHADOW_ZETA) < 1e-12)
            mode_points.append((
                long_shadow_row["mean_occupancy_proxy_l2"],
                long_shadow_row["mean_true_iae"] - best_row["mean_true_iae"],
                LEVEL_LABELS[environment["level"]],
            ))
        ax.plot([point[0] for point in mode_points], [point[1] for point in mode_points], marker="o", linewidth=2.2, color=MODE_COLORS[mode], label=mode.capitalize())
        for x_value, y_value, label in mode_points:
            ax.annotate(label, (x_value, y_value), xytext=(4, 4), textcoords="offset points", fontsize=9)
    style_panel(ax, "Long-Shadow Gap vs Long-Shadow Occupancy", "Long-Shadow Occupancy Proxy", "Long-Shadow Gap to Best IAE")
    ax.legend(frameon=False)
    add_takeaway(ax, "As occupancy rises, the longest-shadow design stops being the best aircraft tuning.", "upper left")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "aircraft_autopilot_shadow_mass_occupancy.png")
    plt.close(figure)


def plot_pairwise_reliability(pairwise_rows, bootstrap_summary):
    figure, axes = plt.subplots(2, 2, figsize=(14.0, 9.8))
    measurement_envs = [env for env in ENVIRONMENTS if env["mode"] == "measurement"]

    for axis, (left_zeta, right_zeta) in zip(axes.flat[:3], PAIRWISE_COMPARISONS):
        rows = [
            row for row in pairwise_rows
            if abs(row["left_zeta"] - left_zeta) < 1e-12 and abs(row["right_zeta"] - right_zeta) < 1e-12
        ]
        rows.sort(key=lambda row: row["noise_std"])
        axis.plot([row["noise_std"] for row in rows], [row["true_winner_probability_left"] for row in rows], color=LIGHT_SHADOW_COLOR, marker="o", linewidth=2.2, label="True winner probability")
        axis.fill_between([row["noise_std"] for row in rows], [row["true_winner_ci_low"] for row in rows], [row["true_winner_ci_high"] for row in rows], color=LIGHT_SHADOW_COLOR, alpha=0.18)
        axis.plot([row["noise_std"] for row in rows], [row["observed_winner_probability_left"] for row in rows], color=MEMORY_COLOR, marker="s", linewidth=2.2, label="Observed winner probability")
        axis.fill_between([row["noise_std"] for row in rows], [row["observed_winner_ci_low"] for row in rows], [row["observed_winner_ci_high"] for row in rows], color=MEMORY_COLOR, alpha=0.18)
        axis.axhline(0.5, color=REFERENCE_COLOR, linestyle="--", alpha=0.45, linewidth=1.0)
        style_panel(axis, f"zeta = {left_zeta:.3g} vs zeta = {right_zeta:.3g}", "Altitude Sensor Noise Std (ft)", "Probability Left Design Wins")
        axis.legend(frameon=False, fontsize=8, loc="lower left")

    heatmap = axes[1, 1]
    matrix = np.array([
        [bootstrap_summary[env["name"]]["best_zeta_frequency"][decimal_key(zeta)] for zeta in ZETAS]
        for env in measurement_envs
    ], dtype=float)
    image = heatmap.imshow(matrix, aspect="auto", cmap="Blues", vmin=0.0, vmax=1.0)
    heatmap.set_xticks(np.arange(len(ZETAS)))
    heatmap.set_xticklabels([f"{zeta:.3g}" for zeta in ZETAS], rotation=45, ha="right")
    heatmap.set_yticks(np.arange(len(measurement_envs)))
    heatmap.set_yticklabels([LEVEL_LABELS[env["level"]] for env in measurement_envs])
    heatmap.set_title("Bootstrap Best-zeta Frequency\nMeasurement-Side Nuisance")
    heatmap.set_xlabel("Damping Ratio zeta")
    heatmap.set_ylabel("Environment Severity")
    figure.colorbar(image, ax=heatmap, fraction=0.046, pad=0.04)
    add_takeaway(heatmap, "The preferred aircraft tuning migrates across the sensor-noise ladder.", "lower right")

    figure.tight_layout()
    save_figure(figure, PLOT_DIR, "aircraft_autopilot_pairwise_reliability.png")
    plt.close(figure)


def write_outputs(system_rows, clean_rows, grid_rows, trial_rows, pairwise_rows, bootstrap_summary, summary):
    system_metrics_path = DATA_DIR / "aircraft_autopilot_system_metrics.csv"
    clean_tracking_path = DATA_DIR / "aircraft_autopilot_clean_tracking_metrics.csv"
    environment_grid_path = DATA_DIR / "aircraft_autopilot_environment_grid.csv"
    trial_samples_path = DATA_DIR / "aircraft_autopilot_trial_samples.csv"
    pairwise_path = DATA_DIR / "aircraft_autopilot_pairwise_reliability.csv"
    bootstrap_path = DATA_DIR / "aircraft_autopilot_bootstrap_summary.json"
    summary_path = DATA_DIR / "aircraft_autopilot_summary.json"
    manifest_path = DATA_DIR / "manifest.json"

    system_metric_rows = []
    for row in system_rows:
        system_metric_rows.append({
            "zeta": row["zeta"],
            "k_theta": row["k_theta"],
            "k_i_theta": row["k_i_theta"],
            "k_q": row["k_q"],
            "k_h": row["k_h"],
            "k_i_h": row["k_i_h"],
            "pitch_step_settling_time_2pct": row["pitch_step_settling_time_2pct"],
            "pitch_step_overshoot": row["pitch_step_overshoot"],
            "pitch_step_rise_time_10_90": row["pitch_step_rise_time_10_90"],
            "altitude_step_settling_time_2pct": row["altitude_step_settling_time_2pct"],
            "altitude_step_overshoot": row["altitude_step_overshoot"],
            "altitude_step_rise_time_10_90": row["altitude_step_rise_time_10_90"],
            "pitch_bandwidth_3db": row["pitch_bandwidth_3db"],
            "altitude_bandwidth_3db": row["altitude_bandwidth_3db"],
            "slow_band_deficit_0_03": row["slow_band_deficit_0_03"],
            "shadow_horizon_eps_0_02": row["shadow_horizon_eps_0_02"],
            "shadow_mass_l1": row["shadow_mass_l1"],
            "shadow_mass_l2": row["shadow_mass_l2"],
            "inner_tuning_residual": row["inner_tuning_residual"],
            "outer_tuning_residual": row["outer_tuning_residual"],
            "pole_real_parts": ";".join(f"{np.real(pole):.6f}" for pole in row["full_eigenvalues"]),
            "pole_imag_parts": ";".join(f"{np.imag(pole):.6f}" for pole in row["full_eigenvalues"]),
        })

    write_csv(
        system_metrics_path,
        system_metric_rows,
        [
            "zeta",
            "k_theta",
            "k_i_theta",
            "k_q",
            "k_h",
            "k_i_h",
            "pitch_step_settling_time_2pct",
            "pitch_step_overshoot",
            "pitch_step_rise_time_10_90",
            "altitude_step_settling_time_2pct",
            "altitude_step_overshoot",
            "altitude_step_rise_time_10_90",
            "pitch_bandwidth_3db",
            "altitude_bandwidth_3db",
            "slow_band_deficit_0_03",
            "shadow_horizon_eps_0_02",
            "shadow_mass_l1",
            "shadow_mass_l2",
            "inner_tuning_residual",
            "outer_tuning_residual",
            "pole_real_parts",
            "pole_imag_parts",
        ],
    )
    write_csv(
        clean_tracking_path,
        clean_rows,
        ["test_name", "test_title", "zeta", "true_iae", "true_ise", "peak_abs_error", "mean_abs_error"],
    )
    write_csv(
        environment_grid_path,
        grid_rows,
        [
            "environment_name",
            "mode",
            "level",
            "zeta",
            "noise_std",
            "gust_std",
            "mean_true_iae",
            "std_true_iae",
            "p10_true_iae",
            "median_true_iae",
            "p90_true_iae",
            "ci_true_iae_low",
            "ci_true_iae_high",
            "mean_true_ise",
            "mean_peak_abs_error",
            "mean_abs_error",
            "mean_excess_true_iae_over_clean",
            "mean_shadow_mass_l2_trial",
            "mean_occupancy_proxy_l2",
            "mean_observed_iae",
            "stability_rate",
            "valid_trial_count",
            "bootstrap_best_frequency",
        ],
    )
    write_csv(
        trial_samples_path,
        trial_rows,
        [
            "environment_name",
            "mode",
            "level",
            "trial_index",
            "zeta",
            "noise_std",
            "gust_std",
            "short_period_scale",
            "phugoid_scale",
            "control_scale",
            "stability_flag",
            "true_iae",
            "true_ise",
            "peak_abs_error",
            "mean_abs_error",
            "observed_iae",
            "excess_true_iae_over_clean",
            "shadow_mass_l2_trial",
            "occupancy_proxy_l2",
            "nuisance_power_scalar",
        ],
    )
    write_csv(
        pairwise_path,
        pairwise_rows,
        [
            "environment_name",
            "mode",
            "level",
            "noise_std",
            "left_zeta",
            "right_zeta",
            "valid_pair_trial_count",
            "true_winner_probability_left",
            "true_winner_ci_low",
            "true_winner_ci_high",
            "observed_winner_probability_left",
            "observed_winner_ci_low",
            "observed_winner_ci_high",
        ],
    )
    write_json(bootstrap_path, bootstrap_summary)
    write_json(summary_path, summary)
    write_json(
        manifest_path,
        {
            "study": "out-of-family-aircraft-longitudinal-autopilot",
            "generated_files": {
                "csv": [
                    str(system_metrics_path.relative_to(ROOT_DIR)),
                    str(clean_tracking_path.relative_to(ROOT_DIR)),
                    str(environment_grid_path.relative_to(ROOT_DIR)),
                    str(trial_samples_path.relative_to(ROOT_DIR)),
                    str(pairwise_path.relative_to(ROOT_DIR)),
                ],
                "json": [
                    str(bootstrap_path.relative_to(ROOT_DIR)),
                    str(summary_path.relative_to(ROOT_DIR)),
                    str(manifest_path.relative_to(ROOT_DIR)),
                ],
                "plots": [
                    str((PLOT_DIR / "aircraft_autopilot_family_overview.png").relative_to(ROOT_DIR)),
                    str((PLOT_DIR / "aircraft_autopilot_settling_blind_spot.png").relative_to(ROOT_DIR)),
                    str((PLOT_DIR / "aircraft_autopilot_noise_conditioned_optimum.png").relative_to(ROOT_DIR)),
                    str((PLOT_DIR / "aircraft_autopilot_shadow_mass_occupancy.png").relative_to(ROOT_DIR)),
                    str((PLOT_DIR / "aircraft_autopilot_pairwise_reliability.png").relative_to(ROOT_DIR)),
                ],
            },
        },
    )


def main():
    apply_plot_style()
    ensure_dirs()

    system_rows = nominal_design_rows()
    clean_rows, clean_lookup = clean_tracking_rows(system_rows)
    trial_rows, grid_rows, pairwise_rows, bootstrap_summary = run_environment_sweep(system_rows, clean_lookup)
    summary = summary_payload(system_rows, clean_rows, clean_lookup, grid_rows, pairwise_rows, bootstrap_summary)
    matched_pairs = matched_pair_rows(system_rows, clean_lookup)

    plot_family_overview(system_rows, clean_lookup)
    plot_settling_blind_spot(system_rows, clean_lookup, matched_pairs)
    plot_noise_conditioned_optimum(grid_rows, bootstrap_summary)
    plot_shadow_mass_occupancy(grid_rows)
    plot_pairwise_reliability(pairwise_rows, bootstrap_summary)
    write_outputs(system_rows, clean_rows, grid_rows, trial_rows, pairwise_rows, bootstrap_summary, summary)

    print("Aircraft autopilot study complete.")
    top_pair = summary["matched_pairs"]["top_supportive_pair"]
    if top_pair is None:
        print("No matched-transient pair met the study threshold.")
    else:
        print(
            "Top matched pair:",
            f"zeta = {top_pair['better_zeta']:.3g} vs zeta = {top_pair['worse_zeta']:.3g}",
            f"| pitch-step gap = {top_pair['settling_diff_pct']:.2f}% | IAE ratio = {top_pair['iae_ratio']:.2f}x",
        )


if __name__ == "__main__":
    main()
