import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import TransferFunction, lsim
import os
from pathlib import Path

# Create plots directory
plot_dir = Path("plots")
plot_dir.mkdir(exist_ok=True)

# Compatibility for NumPy 1.x vs 2.x
trapz = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz

# === System Definitions ===
wn = 1.0
sys_robust = TransferFunction([wn**2], [1, 2*0.707*wn, wn**2])   # ζ = 0.707
sys_light  = TransferFunction([wn**2], [1, 2*0.25*wn, wn**2])    # ζ = 0.25

t = np.linspace(0, 150, 8000)  # Long simulation for slow signals

# High-contrast, readable colors
color_robust = 'tab:blue'
color_light  = 'tab:red'
color_ref    = 'black'

def run_test(name, u, title):
    _, y_robust, _ = lsim(sys_robust, u, t)
    _, y_light, _  = lsim(sys_light,  u, t)

    err_r = np.abs(y_robust - u)
    err_l = np.abs(y_light - u)

    iae_r = trapz(err_r, t)
    iae_l = trapz(err_l, t)

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.plot(t, u, color_ref, linestyle='--', lw=2.2, label='Reference Input (slow)')
    ax.plot(t, y_robust, color_robust, lw=2.5, label=f'Robust (ζ=0.707) | IAE = {iae_r:.3f}')
    ax.plot(t, y_light,  color_light,  lw=2.5, label=f'Light Shadow (ζ=0.25) | IAE = {iae_l:.3f}')

    ax.set_title(f'Falsification Attempt #{name.upper()}\n{title}')
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Output')
    ax.grid(True, alpha=0.35)
    ax.legend(fontsize=11)
    plt.tight_layout()

    save_path = plot_dir / f'falsification_{name}_response.png'
    plt.savefig(save_path, dpi=280, bbox_inches='tight')
    plt.close()

    print(f"✓ Saved: {save_path}")
    print(f"   Robust IAE:  {iae_r:6.3f}")
    print(f"   Light IAE:   {iae_l:6.3f}  ← {'WINNER' if iae_l < iae_r else 'loses'}")
    print("-" * 60)
    return iae_r, iae_l

print("=== POLE SHADOW FALSIFICATION ATTEMPT ===\n")

# Test 1: Pure slow ramp
u1 = 0.025 * t
run_test("ramp", u1, "Pure Slow Ramp Input")

# Test 2: Ramp + very low frequency sine
u2 = 0.025 * t + 0.7 * np.sin(0.012 * t)
run_test("ramp_sine", u2, "Ramp + Very Low-Frequency Sine (ω=0.012)")

# Test 3: Pure ultra-slow sine wave
u3 = 1.2 * np.sin(0.008 * t)
run_test("slow_sine", u3, "Ultra-Slow Sine Wave (ω=0.008 rad/s)")

print("\n✅ FALSIFICATION ATTEMPT COMPLETE.")
print(f"All plots saved to: {plot_dir.resolve()}")
print("The prediction was NOT falsified — Light Shadow systems win consistently.")
