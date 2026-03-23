import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import TransferFunction, lsim
from matplotlib.backends.backend_pdf import PdfPages

ROOT_DIR = Path(__file__).resolve().parents[3]
SHARED_PYTHON_DIR = ROOT_DIR / "shared" / "python"
RUN_DIR = Path(__file__).resolve().parents[1] / "runs" / "latest"

if str(SHARED_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_PYTHON_DIR))

from plot_theme import (
    FAST_COLOR,
    LIGHT_SHADOW_COLOR,
    REFERENCE_COLOR,
    NOISE_COLOR,
    MEMORY_COLOR,
    apply_plot_style,
    get_plot_dir,
    save_figure,
    style_panel,
    add_takeaway,
    highlight_window,
    cumulative_integral,
    moving_average,
)

# Create output directory
apply_plot_style()
plot_dir = get_plot_dir(RUN_DIR / "plots")

# NumPy compatibility
trapz = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz

# System parameters
wn = 1.0
t = np.linspace(0, 150, 8000)

def create_system(zeta):
    return TransferFunction([wn**2], [1, 2*zeta*wn, wn**2])

sys_robust = create_system(0.707)
sys_light = create_system(0.25)

def focus_window_for(name):
    return {
        "ramp": 18,
        "ramp_sine": 25,
        "slow_sine": 40,
        "noisy": 20,
    }.get(name, 25)

def run_test(name, u, title, save_name, display_reference=None, noisy_reference=None):
    _, y_robust, _ = lsim(sys_robust, u, t)
    _, y_light, _ = lsim(sys_light, u, t)

    reference_to_show = u if display_reference is None else display_reference
    err_signed_r = y_robust - u
    err_signed_l = y_light - u
    err_r = np.abs(err_signed_r)
    err_l = np.abs(err_signed_l)
    iae_r = trapz(err_r, t)
    iae_l = trapz(err_l, t)
    cumulative_r = cumulative_integral(err_r, t)
    cumulative_l = cumulative_integral(err_l, t)
    focus_end = focus_window_for(name)
    focus_mask = t <= focus_end
    focus_series = [
        reference_to_show[focus_mask],
        y_robust[focus_mask],
        y_light[focus_mask],
    ]
    if noisy_reference is not None:
        focus_series.append(noisy_reference[focus_mask])
    focus_min = min(series.min() for series in focus_series)
    focus_max = max(series.max() for series in focus_series)
    focus_pad = max(0.05, 0.08 * (focus_max - focus_min))
    winner = "Light Shadow" if iae_l < iae_r else "Robust"
    improvement = iae_r / iae_l if iae_l else np.inf

    fig, axs = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)
    ax_main, ax_zoom = axs[0]
    ax_err, ax_cum = axs[1]

    if noisy_reference is not None:
        ax_main.plot(t, noisy_reference, color=NOISE_COLOR, lw=0.9, alpha=0.4, label='Noisy commanded input')
    ax_main.plot(t, reference_to_show, color=REFERENCE_COLOR, ls='--', lw=2, label='Reference trend')
    ax_main.plot(t, y_robust, color=FAST_COLOR, lw=2.4, label=f'Robust (ζ=0.707) | IAE={iae_r:.3f}')
    ax_main.plot(t, y_light, color=LIGHT_SHADOW_COLOR, lw=2.4, label=f'Light Shadow (ζ=0.25) | IAE={iae_l:.3f}')
    highlight_window(ax_main, 0, focus_end)
    style_panel(ax_main, f'Falsification Test: {title}', 'Time (s)', 'Output')
    ax_main.legend(loc='upper left')
    add_takeaway(ax_main, f'{winner} wins\nFinal IAE ratio: {improvement:.2f}x', location='lower right')

    if noisy_reference is not None:
        ax_zoom.plot(t[focus_mask], noisy_reference[focus_mask], color=NOISE_COLOR, lw=0.8, alpha=0.35, label='Noisy input')
    ax_zoom.plot(t[focus_mask], reference_to_show[focus_mask], color=REFERENCE_COLOR, ls='--', lw=2)
    ax_zoom.plot(t[focus_mask], y_robust[focus_mask], color=FAST_COLOR, lw=2.4)
    ax_zoom.plot(t[focus_mask], y_light[focus_mask], color=LIGHT_SHADOW_COLOR, lw=2.4)
    ax_zoom.set_xlim(0, focus_end)
    ax_zoom.set_ylim(focus_min - focus_pad, focus_max + focus_pad)
    style_panel(ax_zoom, f'Zoomed view (0 to {focus_end:.0f} s)', 'Time (s)', 'Output')

    if noisy_reference is not None:
        smooth_window = 201
        ax_err.plot(t, moving_average(err_r, smooth_window), color=FAST_COLOR, lw=2.1,
                    label='Robust rolling mean |error|')
        ax_err.plot(t, moving_average(err_l, smooth_window), color=LIGHT_SHADOW_COLOR, lw=2.1,
                    label='Light Shadow rolling mean |error|')
        style_panel(ax_err, 'Rolling mean absolute error', 'Time (s)', 'Mean |output - input|')
    else:
        ax_err.plot(t, err_signed_r, color=FAST_COLOR, lw=2.0, label='Robust error')
        ax_err.plot(t, err_signed_l, color=LIGHT_SHADOW_COLOR, lw=2.0, label='Light Shadow error')
        ax_err.axhline(0.0, color=REFERENCE_COLOR, lw=1.0, alpha=0.7)
        style_panel(ax_err, 'Signed tracking error', 'Time (s)', 'Output - input')
    ax_err.legend(loc='upper right')

    ax_cum.plot(t, cumulative_r, color=FAST_COLOR, lw=2.2, label='Robust cumulative IAE')
    ax_cum.plot(t, cumulative_l, color=LIGHT_SHADOW_COLOR, lw=2.2, label='Light Shadow cumulative IAE')
    ax_cum.fill_between(t, cumulative_l, cumulative_r, where=cumulative_r >= cumulative_l, color=MEMORY_COLOR, alpha=0.12)
    style_panel(ax_cum, 'Cumulative absolute error', 'Time (s)', 'Accumulated error')
    ax_cum.legend(loc='upper left')

    save_figure(fig, plot_dir, save_name, dpi=280)
    plt.close()
    print(f"✓ {title} | Robust: {iae_r:.3f} | Light: {iae_l:.3f} | Winner: {winner}")
    return {
        "name": name,
        "title": title,
        "u": u,
        "display_reference": reference_to_show,
        "noisy_reference": noisy_reference,
        "y_robust": y_robust,
        "y_light": y_light,
        "err_signed_r": err_signed_r,
        "err_signed_l": err_signed_l,
        "cumulative_r": cumulative_r,
        "cumulative_l": cumulative_l,
        "iae_r": iae_r,
        "iae_l": iae_l,
        "focus_end": focus_end,
    }

print("=== POLE SHADOW COMPREHENSIVE ANALYSIS ===\n")

# Test 1-3 (original)
u1 = 0.025 * t
result_ramp = run_test("ramp", u1, "Pure Slow Ramp", "falsification_ramp.png")

u2 = 0.025 * t + 0.7 * np.sin(0.012 * t)
result_ramp_sine = run_test("ramp_sine", u2, "Ramp + Low-Freq Sine", "falsification_ramp_sine.png")

u3 = 1.2 * np.sin(0.008 * t)
result_slow_sine = run_test("slow_sine", u3, "Ultra-Slow Sine", "falsification_slow_sine.png")

# === NEW: Test 4 — Real-world style with noise ===
print("\nRunning Fourth Test (Realistic Noise)...")
np.random.seed(42)
u4 = 0.025 * t + 0.6 * np.sin(0.011 * t)
noise = 0.08 * np.random.randn(len(t))   # realistic high-frequency sensor noise
u4_noisy = u4 + noise
result_noisy = run_test(
    "noisy",
    u4_noisy,
    "Slow Input + Noise",
    "falsification_noisy.png",
    display_reference=u4,
    noisy_reference=u4_noisy,
)

# === NEW: ζ Sweep Plot ===
print("\nRunning ζ sweep (0.1 → 1.0)...")
zetas = np.linspace(0.1, 1.0, 18)
iaes = []
u_sweep = 0.025 * t + 0.7 * np.sin(0.012 * t)   # representative slow signal

for zeta in zetas:
    sys = create_system(zeta)
    _, y, _ = lsim(sys, u_sweep, t)
    iae = trapz(np.abs(y - u_sweep), t)
    iaes.append(iae)

best_iae = min(iaes)
robust_iae = np.interp(0.707, zetas, iaes)
light_iae = np.interp(0.25, zetas, iaes)
penalty = np.array(iaes) / best_iae

fig, axs = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
ax_main, ax_zoom = axs[0]
ax_penalty, ax_compare = axs[1]

ax_main.plot(zetas, iaes, 'o-', color=MEMORY_COLOR, lw=2.5, markersize=5)
ax_main.scatter([0.25, 0.707], [light_iae, robust_iae], color=[LIGHT_SHADOW_COLOR, FAST_COLOR], s=90, zorder=3)
highlight_window(ax_main, 0.1, 0.75)
style_panel(ax_main, "Performance sweep", 'Damping ratio ζ', 'Integrated Absolute Error (IAE)')
add_takeaway(ax_main, f"Robust / Light IAE\n{robust_iae / light_iae:.2f}x", location='upper left')

zoom_mask = (zetas >= 0.1) & (zetas <= 0.8)
ax_zoom.plot(zetas[zoom_mask], np.array(iaes)[zoom_mask], 'o-', color=MEMORY_COLOR, lw=2.5, markersize=5)
ax_zoom.scatter([0.25, 0.707], [light_iae, robust_iae], color=[LIGHT_SHADOW_COLOR, FAST_COLOR], s=90, zorder=3)
style_panel(ax_zoom, 'Zoom on modeled tunings', 'Damping ratio ζ', 'Integrated Absolute Error (IAE)')
ax_zoom.annotate('Light Shadow', xy=(0.25, light_iae), xytext=(0.18, light_iae + 0.7),
                 arrowprops=dict(arrowstyle='->', color=LIGHT_SHADOW_COLOR), color=LIGHT_SHADOW_COLOR)
ax_zoom.annotate('Robust', xy=(0.707, robust_iae), xytext=(0.62, robust_iae + 0.8),
                 arrowprops=dict(arrowstyle='->', color=FAST_COLOR), color=FAST_COLOR)

ax_penalty.plot(zetas, penalty, 'o-', color=MEMORY_COLOR, lw=2.5, markersize=5)
ax_penalty.axhline(1.0, color=REFERENCE_COLOR, lw=1.0, alpha=0.7, linestyle='--')
style_panel(ax_penalty, 'Penalty relative to best sweep result', 'Damping ratio ζ', 'IAE / best IAE')

comparison_labels = ['Best ζ=0.10', 'Light ζ=0.25', 'Robust ζ=0.707']
comparison_values = [best_iae, light_iae, robust_iae]
comparison_colors = [MEMORY_COLOR, LIGHT_SHADOW_COLOR, FAST_COLOR]
ax_compare.bar(comparison_labels, comparison_values, color=comparison_colors)
style_panel(ax_compare, 'Representative comparison', 'Tuning', 'Integrated Absolute Error (IAE)')
add_takeaway(ax_compare, f"Lowest tested damping\nwins this sweep", location='upper right')

save_figure(fig, plot_dir, 'iae_vs_damping_ratio.png', dpi=280)
plt.close(fig)

# === NEW: One-Page Visual Proof PDF ===
print("\nGenerating one-page Visual Proof PDF...")
with PdfPages(plot_dir / 'visual_proof_pole_shadow.pdf') as pdf:
    fig, axs = plt.subplots(2, 2, figsize=(11, 8.5), constrained_layout=True)
    fig.suptitle("Visual Proof: The Pole's Shadow Hypothesis\nRobustness vs Temporal Integration Capacity",
                 fontsize=16, fontweight='bold')
    ax1, ax2 = axs[0]
    ax3, ax4 = axs[1]

    ax1.plot(t, result_ramp_sine["display_reference"], color=REFERENCE_COLOR, ls='--', lw=1.6, label='Reference')
    ax1.plot(t, result_ramp_sine["y_robust"], color=FAST_COLOR, lw=2.0, label='Robust')
    ax1.plot(t, result_ramp_sine["y_light"], color=LIGHT_SHADOW_COLOR, lw=2.0, label='Light Shadow')
    highlight_window(ax1, 0, result_ramp_sine["focus_end"])
    style_panel(ax1, 'Ramp + low-frequency sine', 'Time (s)', 'Output')
    ax1.legend(loc='upper left')

    focus_mask = t <= result_ramp_sine["focus_end"]
    ax2.plot(t[focus_mask], result_ramp_sine["display_reference"][focus_mask], color=REFERENCE_COLOR, ls='--', lw=1.6)
    ax2.plot(t[focus_mask], result_ramp_sine["y_robust"][focus_mask], color=FAST_COLOR, lw=2.0)
    ax2.plot(t[focus_mask], result_ramp_sine["y_light"][focus_mask], color=LIGHT_SHADOW_COLOR, lw=2.0)
    style_panel(ax2, 'Zoom on separation', 'Time (s)', 'Output')

    ax3.plot(zetas, iaes, 'o-', color=MEMORY_COLOR, lw=2.6, markersize=5)
    ax3.scatter([0.25, 0.707], [light_iae, robust_iae], color=[LIGHT_SHADOW_COLOR, FAST_COLOR], s=80, zorder=3)
    style_panel(ax3, 'Performance sweep', 'Damping ratio ζ', 'Integrated Absolute Error (IAE)')
    add_takeaway(ax3, f'Robust / Light\n{robust_iae / light_iae:.2f}x', location='upper left')

    ax4.plot(t, result_ramp_sine["cumulative_r"], color=FAST_COLOR, lw=2.0, label='Robust cumulative IAE')
    ax4.plot(t, result_ramp_sine["cumulative_l"], color=LIGHT_SHADOW_COLOR, lw=2.0, label='Light cumulative IAE')
    ax4.fill_between(t, result_ramp_sine["cumulative_l"], result_ramp_sine["cumulative_r"],
                     where=result_ramp_sine["cumulative_r"] >= result_ramp_sine["cumulative_l"],
                     color=MEMORY_COLOR, alpha=0.12)
    style_panel(ax4, 'Accumulated evidence', 'Time (s)', 'Cumulative absolute error')
    ax4.legend(loc='upper left')

    pdf.savefig(fig, dpi=300)
    plt.close()

print(f"✅ All done! Visual proof saved to: {plot_dir}/visual_proof_pole_shadow.pdf")
print("Files created:")
print("   • 4 falsification response plots")
print("   • iae_vs_damping_ratio.png")
print("   • visual_proof_pole_shadow.pdf")
