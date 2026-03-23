import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import lsim, TransferFunction
from pathlib import Path

# Compatibility for old (np.trapz) and new (np.trapezoid) NumPy
try:
    trapz = np.trapezoid
except AttributeError:
    trapz = np.trapz

# Clean style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

BASE_DIR = Path(__file__).resolve().parent
PLOTS_DIR = BASE_DIR / "plots"

FAST_COLOR = "#1f77b4"
LIGHT_SHADOW_COLOR = "#d95f02"
ENVELOPE_COLOR = "#6c757d"
THRESHOLD_COLOR = "#a6761d"
REFERENCE_COLOR = "#111111"
MEMORY_COLOR = "#7b3294"
FOCUS_SHADE = "#e8eef7"


def save_plot(filename):
    PLOTS_DIR.mkdir(exist_ok=True)
    output_path = PLOTS_DIR / filename
    plt.savefig(output_path, dpi=250, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")


def cumulative_integral(values, time):
    cumulative = np.zeros_like(values)
    cumulative[1:] = np.cumsum(0.5 * (values[1:] + values[:-1]) * np.diff(time))
    return cumulative

def plot_pole_shadow_decay():
    """Plot 1: Pole's Shadow decay comparison"""
    t = np.linspace(0, 30, 2000)
    sigma_f, wd_f = -1.0, 3.0
    y_f = np.exp(sigma_f * t) * np.cos(wd_f * t)
    env_f = np.exp(sigma_f * t)

    sigma_s, wd_s = -0.2, 1.2
    y_s = np.exp(sigma_s * t) * np.cos(wd_s * t)
    env_s = np.exp(sigma_s * t)

    fig, axs = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    axs[0].plot(t, y_f, color=FAST_COLOR, lw=2.4, label='Dominant pole σ = -1.0 (fast decay)')
    axs[0].plot(t, env_f, color=ENVELOPE_COLOR, lw=1.6, alpha=0.85, linestyle='--')
    axs[0].plot(t, -env_f, color=ENVELOPE_COLOR, lw=1.6, alpha=0.85, linestyle='--')
    axs[0].axhline(0.02, color=THRESHOLD_COLOR, linestyle=':', lw=1.8, label='≈2% settling threshold')
    axs[0].set_title("Pole's Shadow: Fast vs Slow Transient Decay")
    axs[0].set_ylabel('Transient Amplitude')
    axs[0].grid(True, alpha=0.3)
    axs[0].legend()

    axs[1].plot(t, y_s, color=LIGHT_SHADOW_COLOR, lw=2.4, label='Dominant pole σ = -0.2 (long shadow)')
    axs[1].plot(t, env_s, color=ENVELOPE_COLOR, lw=1.6, alpha=0.85, linestyle='--')
    axs[1].plot(t, -env_s, color=ENVELOPE_COLOR, lw=1.6, alpha=0.85, linestyle='--')
    axs[1].axhline(0.02, color=THRESHOLD_COLOR, linestyle=':', lw=1.8)
    axs[1].set_xlabel('Time t (seconds)')
    axs[1].set_ylabel('Transient Amplitude')
    axs[1].grid(True, alpha=0.3)
    axs[1].legend()

    plt.tight_layout()
    save_plot('pole_shadow_decay.png')
    plt.close()

def plot_tradeoff():
    """Plot 2: Robustness vs Memory tradeoff"""
    d = np.logspace(-1, 1, 300)
    horizon = 4.0 / d
    memory = 1.0 / (1 - np.exp(-2 * d))

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.set_xscale('log')
    ax1.plot(d, horizon, color=FAST_COLOR, lw=3, label='Cognitive Horizon ts ≈ 4/d')
    ax1.set_xlabel('Stability Margin d = -Re(σ_dom) (larger = more robust)')
    ax1.set_ylabel('Cognitive Horizon (seconds)', color=FAST_COLOR)
    ax1.tick_params(axis='y', labelcolor=FAST_COLOR)
    ax1.grid(True, which='both', alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(d, memory, color=MEMORY_COLOR, lw=2.5, linestyle='--', label='Approximate Memory Capacity')
    ax2.set_ylabel('Memory Capacity (scaled)', color=MEMORY_COLOR)
    ax2.tick_params(axis='y', labelcolor=MEMORY_COLOR)

    plt.title("The Explicit Tradeoff: Robustness vs Temporal Integration Capacity\n(Pole's Shadow Length = Cognitive Budget)")
    fig.tight_layout()
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
    ax_main.axvspan(0, focus_end, color=FOCUS_SHADE, alpha=0.35, zorder=0)
    ax_main.set_ylabel('Output')
    ax_main.set_xlabel('Time t (seconds)')
    ax_main.set_title("Tracking Slowly Drifting Input")
    ax_main.legend(loc='upper left')

    ax_zoom.plot(t[focus_mask], u[focus_mask], color=REFERENCE_COLOR, linestyle='--', lw=1.8)
    ax_zoom.plot(t[focus_mask], y_robust[focus_mask], color=FAST_COLOR, lw=2.3)
    ax_zoom.plot(t[focus_mask], y_light[focus_mask], color=LIGHT_SHADOW_COLOR, lw=2.3)
    ax_zoom.set_xlim(0, focus_end)
    ax_zoom.set_ylim(focus_min - focus_pad, focus_max + focus_pad)
    ax_zoom.set_ylabel('Output')
    ax_zoom.set_xlabel('Time t (seconds)')
    ax_zoom.set_title('Zoomed response (first 15 seconds)')

    ax_err.plot(t, err_signed_r, color=FAST_COLOR, lw=2.1, label=f'Robust error | IAE = {iae_r:.3f}')
    ax_err.plot(t, err_signed_l, color=LIGHT_SHADOW_COLOR, lw=2.1, label=f'Light Shadow error | IAE = {iae_l:.3f}')
    ax_err.axhline(0.0, color=REFERENCE_COLOR, lw=1.0, alpha=0.7)
    ax_err.set_ylabel('Output - input')
    ax_err.set_xlabel('Time t (seconds)')
    ax_err.set_title('Signed tracking error')
    ax_err.legend(loc='upper right')

    ax_cum.plot(t, cum_r, color=FAST_COLOR, lw=2.1, label='Robust cumulative IAE')
    ax_cum.plot(t, cum_l, color=LIGHT_SHADOW_COLOR, lw=2.1, label='Light Shadow cumulative IAE')
    ax_cum.fill_between(t, cum_l, cum_r, where=cum_r >= cum_l, color=MEMORY_COLOR, alpha=0.12)
    ax_cum.set_ylabel('Accumulated error')
    ax_cum.set_xlabel('Time t (seconds)')
    ax_cum.set_title('Cumulative absolute error')
    ax_cum.legend(loc='upper left')

    save_plot('pole_shadow_slow_tracking_prediction_test.png')
    plt.close()

if __name__ == "__main__":
    print("🚀 Generating all Pole's Shadow plots...\n")
    plot_pole_shadow_decay()
    plot_tradeoff()
    plot_slow_tracking()
    print("\n✅ All three plots saved perfectly!")
