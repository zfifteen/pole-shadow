import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import lsim, TransferFunction

ROOT_DIR = Path(__file__).resolve().parents[3]
SHARED_PYTHON_DIR = ROOT_DIR / "shared" / "python"
RUN_DIR = Path(__file__).resolve().parents[1] / "runs" / "latest"

if str(SHARED_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_PYTHON_DIR))

from plot_theme import (
    FAST_COLOR,
    LIGHT_SHADOW_COLOR,
    ENVELOPE_COLOR,
    THRESHOLD_COLOR,
    REFERENCE_COLOR,
    MEMORY_COLOR,
    apply_plot_style,
    get_plot_dir,
    save_figure,
    style_panel,
    add_takeaway,
    highlight_window,
    cumulative_integral,
)

# Compatibility for old (np.trapz) and new (np.trapezoid) NumPy
try:
    trapz = np.trapezoid
except AttributeError:
    trapz = np.trapz

apply_plot_style()
PLOTS_DIR = get_plot_dir(RUN_DIR / "plots")


def save_plot(filename):
    save_figure(plt.gcf(), PLOTS_DIR, filename, dpi=250)

def plot_pole_shadow_decay():
    """Plot 1: Pole's Shadow decay comparison"""
    t = np.linspace(0, 30, 2000)
    sigma_f, wd_f = -1.0, 3.0
    y_f = np.exp(sigma_f * t) * np.cos(wd_f * t)
    env_f = np.exp(sigma_f * t)

    sigma_s, wd_s = -0.2, 1.2
    y_s = np.exp(sigma_s * t) * np.cos(wd_s * t)
    env_s = np.exp(sigma_s * t)

    settle_threshold = 0.02
    settle_fast = -np.log(settle_threshold) / abs(sigma_f)
    settle_slow = -np.log(settle_threshold) / abs(sigma_s)
    cum_fast = cumulative_integral(np.abs(y_f), t)
    cum_slow = cumulative_integral(np.abs(y_s), t)
    focus_end = 12
    focus_mask = t <= focus_end

    fig, axs = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    ax_main, ax_zoom = axs[0]
    ax_metric, ax_cum = axs[1]

    ax_main.plot(t, y_f, color=FAST_COLOR, lw=2.2, label='Fast decay (σ = -1.0)')
    ax_main.plot(t, y_s, color=LIGHT_SHADOW_COLOR, lw=2.2, label='Long shadow (σ = -0.2)')
    ax_main.plot(t, env_f, color=FAST_COLOR, lw=1.2, alpha=0.45, linestyle='--')
    ax_main.plot(t, -env_f, color=FAST_COLOR, lw=1.2, alpha=0.45, linestyle='--')
    ax_main.plot(t, env_s, color=LIGHT_SHADOW_COLOR, lw=1.2, alpha=0.45, linestyle='--')
    ax_main.plot(t, -env_s, color=LIGHT_SHADOW_COLOR, lw=1.2, alpha=0.45, linestyle='--')
    ax_main.axhline(settle_threshold, color=THRESHOLD_COLOR, linestyle=':', lw=1.8, label='2% threshold')
    ax_main.axhline(-settle_threshold, color=THRESHOLD_COLOR, linestyle=':', lw=1.2, alpha=0.75)
    highlight_window(ax_main, 0, focus_end)
    style_panel(ax_main, "Transient response context", "Time t (seconds)", "Amplitude")
    ax_main.legend(loc='upper right')
    add_takeaway(
        ax_main,
        f"Settling time\nFast: {settle_fast:.1f}s\nLong shadow: {settle_slow:.1f}s",
        location="lower right",
    )

    ax_zoom.plot(t[focus_mask], y_f[focus_mask], color=FAST_COLOR, lw=2.2)
    ax_zoom.plot(t[focus_mask], y_s[focus_mask], color=LIGHT_SHADOW_COLOR, lw=2.2)
    ax_zoom.plot(t[focus_mask], env_f[focus_mask], color=FAST_COLOR, lw=1.2, alpha=0.45, linestyle='--')
    ax_zoom.plot(t[focus_mask], -env_f[focus_mask], color=FAST_COLOR, lw=1.2, alpha=0.45, linestyle='--')
    ax_zoom.plot(t[focus_mask], env_s[focus_mask], color=LIGHT_SHADOW_COLOR, lw=1.2, alpha=0.45, linestyle='--')
    ax_zoom.plot(t[focus_mask], -env_s[focus_mask], color=LIGHT_SHADOW_COLOR, lw=1.2, alpha=0.45, linestyle='--')
    ax_zoom.axhline(settle_threshold, color=THRESHOLD_COLOR, linestyle=':', lw=1.8)
    ax_zoom.axhline(-settle_threshold, color=THRESHOLD_COLOR, linestyle=':', lw=1.2, alpha=0.75)
    ax_zoom.set_xlim(0, focus_end)
    style_panel(ax_zoom, "Early-time zoom", "Time t (seconds)", "Amplitude")

    ax_metric.semilogy(t, np.maximum(np.abs(y_f), 1e-4), color=FAST_COLOR, lw=2.2, label='|Fast decay response|')
    ax_metric.semilogy(t, np.maximum(np.abs(y_s), 1e-4), color=LIGHT_SHADOW_COLOR, lw=2.2, label='|Long shadow response|')
    ax_metric.axhline(settle_threshold, color=THRESHOLD_COLOR, linestyle=':', lw=1.8)
    style_panel(ax_metric, "Absolute amplitude (log scale)", "Time t (seconds)", "|Amplitude|")
    ax_metric.legend(loc='upper right')

    ax_cum.plot(t, cum_fast, color=FAST_COLOR, lw=2.2, label='Fast decay cumulative |response|')
    ax_cum.plot(t, cum_slow, color=LIGHT_SHADOW_COLOR, lw=2.2, label='Long shadow cumulative |response|')
    ax_cum.fill_between(t, cum_fast, cum_slow, where=cum_slow >= cum_fast, color=MEMORY_COLOR, alpha=0.12)
    style_panel(ax_cum, "Accumulated transient energy", "Time t (seconds)", "Cumulative |response| dt")
    ax_cum.legend(loc='upper left')

    save_plot('pole_shadow_decay.png')
    plt.close()

def plot_tradeoff():
    """Plot 2: Robustness vs Memory tradeoff"""
    d = np.logspace(-1, 1, 300)
    horizon = 4.0 / d
    memory = 1.0 / (1 - np.exp(-2 * d))
    normalized_horizon = horizon / horizon.max()
    normalized_memory = memory / memory.max()
    representative_d = np.array([0.15, 0.5, 1.5])
    representative_labels = ['Near edge', 'Mid margin', 'Deep stable']
    rep_horizon = 4.0 / representative_d
    rep_memory = 1.0 / (1 - np.exp(-2 * representative_d))

    fig, axs = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    ax_horizon, ax_memory = axs[0]
    ax_norm, ax_bars = axs[1]

    ax_horizon.set_xscale('log')
    ax_horizon.plot(d, horizon, color=FAST_COLOR, lw=2.6)
    highlight_window(ax_horizon, 0.1, 0.6)
    style_panel(ax_horizon, "Cognitive horizon vs stability margin", "Margin d = -Re(σ_dom)", "Horizon (seconds)")
    add_takeaway(ax_horizon, "Moving left on this axis\nbuys persistence quickly", location="upper right")

    ax_memory.set_xscale('log')
    ax_memory.plot(d, memory, color=MEMORY_COLOR, lw=2.6)
    highlight_window(ax_memory, 0.1, 0.6)
    style_panel(ax_memory, "Memory capacity proxy", "Margin d = -Re(σ_dom)", "Scaled memory capacity")
    add_takeaway(ax_memory, "Higher damping margin\ncompresses state budget", location="upper right")

    ax_norm.set_xscale('log')
    ax_norm.plot(d, normalized_horizon, color=FAST_COLOR, lw=2.4, label='Normalized horizon')
    ax_norm.plot(d, normalized_memory, color=MEMORY_COLOR, lw=2.4, linestyle='--', label='Normalized memory')
    highlight_window(ax_norm, 0.1, 0.6)
    style_panel(ax_norm, "Normalized tradeoff curves", "Margin d = -Re(σ_dom)", "Fraction of near-edge value")
    ax_norm.legend(loc='upper right')

    x = np.arange(len(representative_labels))
    width = 0.35
    ax_bars.bar(x - width / 2, rep_horizon / rep_horizon.max(), width=width, color=FAST_COLOR, label='Horizon')
    ax_bars.bar(x + width / 2, rep_memory / rep_memory.max(), width=width, color=MEMORY_COLOR, label='Memory')
    ax_bars.set_xticks(x, representative_labels)
    style_panel(ax_bars, "Representative tuning regimes", "Region", "Normalized budget")
    ax_bars.legend(loc='upper right')

    save_plot('tradeoff_pole_shadow_memory_vs_robustness.png')
    plt.close()

def plot_slow_tracking():
    """Plot 3: Slow ramp tracking test"""
    wn = 1.0
    t = np.linspace(0, 60, 3000)
    u = 0.05 * t + 0.8 * np.sin(0.02 * t)

    sys_robust = TransferFunction([wn**2], [1, 2*0.707*wn, wn**2])
    _, y_robust, _ = lsim(sys_robust, u, t)

    sys_light = TransferFunction([wn**2], [1, 2*0.25*wn, wn**2])
    _, y_light, _ = lsim(sys_light, u, t)

    err_signed_r = y_robust - u
    err_signed_l = y_light - u
    err_r = np.abs(err_signed_r)
    err_l = np.abs(err_signed_l)
    iae_r = trapz(err_r, t)
    iae_l = trapz(err_l, t)
    cum_r = cumulative_integral(err_r, t)
    cum_l = cumulative_integral(err_l, t)
    focus_end = 15
    focus_mask = t <= focus_end
    focus_series = [u[focus_mask], y_robust[focus_mask], y_light[focus_mask]]
    focus_min = min(series.min() for series in focus_series)
    focus_max = max(series.max() for series in focus_series)
    focus_pad = max(0.05, 0.08 * (focus_max - focus_min))

    fig, axs = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    ax_main, ax_zoom = axs[0]
    ax_err, ax_cum = axs[1]

    ax_main.plot(t, u, color=REFERENCE_COLOR, linestyle='--', lw=1.8, label='Slow ramp reference + low-freq sine')
    ax_main.plot(t, y_robust, color=FAST_COLOR, lw=2.3, label='Robust (ζ=0.707)')
    ax_main.plot(t, y_light, color=LIGHT_SHADOW_COLOR, lw=2.3, label='Light Shadow (ζ=0.25)')
    highlight_window(ax_main, 0, focus_end)
    style_panel(ax_main, "Tracking context", "Time t (seconds)", "Output")
    ax_main.legend(loc='upper left')
    add_takeaway(ax_main, f"Light Shadow wins\nIAE ratio: {iae_r / iae_l:.2f}x", location="lower right")

    ax_zoom.plot(t[focus_mask], u[focus_mask], color=REFERENCE_COLOR, linestyle='--', lw=1.8)
    ax_zoom.plot(t[focus_mask], y_robust[focus_mask], color=FAST_COLOR, lw=2.3)
    ax_zoom.plot(t[focus_mask], y_light[focus_mask], color=LIGHT_SHADOW_COLOR, lw=2.3)
    ax_zoom.set_xlim(0, focus_end)
    ax_zoom.set_ylim(focus_min - focus_pad, focus_max + focus_pad)
    style_panel(ax_zoom, "Zoomed response", "Time t (seconds)", "Output")

    ax_err.plot(t, err_signed_r, color=FAST_COLOR, lw=2.1, label=f'Robust error | IAE = {iae_r:.3f}')
    ax_err.plot(t, err_signed_l, color=LIGHT_SHADOW_COLOR, lw=2.1, label=f'Light Shadow error | IAE = {iae_l:.3f}')
    ax_err.axhline(0.0, color=REFERENCE_COLOR, lw=1.0, alpha=0.7)
    style_panel(ax_err, "Signed tracking error", "Time t (seconds)", "Output - input")
    ax_err.legend(loc='upper right')

    ax_cum.plot(t, cum_r, color=FAST_COLOR, lw=2.1, label='Robust cumulative IAE')
    ax_cum.plot(t, cum_l, color=LIGHT_SHADOW_COLOR, lw=2.1, label='Light Shadow cumulative IAE')
    ax_cum.fill_between(t, cum_l, cum_r, where=cum_r >= cum_l, color=MEMORY_COLOR, alpha=0.12)
    style_panel(ax_cum, "Cumulative absolute error", "Time t (seconds)", "Accumulated error")
    ax_cum.legend(loc='upper left')

    save_plot('pole_shadow_slow_tracking_prediction_test.png')
    plt.close()

if __name__ == "__main__":
    print("🚀 Generating all Pole's Shadow plots...\n")
    plot_pole_shadow_decay()
    plot_tradeoff()
    plot_slow_tracking()
    print("\n✅ All three plots saved perfectly!")
