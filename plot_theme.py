from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


FAST_COLOR = "#1f77b4"
LIGHT_SHADOW_COLOR = "#d95f02"
ENVELOPE_COLOR = "#6c757d"
THRESHOLD_COLOR = "#a6761d"
REFERENCE_COLOR = "#111111"
MEMORY_COLOR = "#7b3294"
NOISE_COLOR = "#9aa0a6"
FOCUS_SHADE = "#e8eef7"
TEXT_BOX = {
    "boxstyle": "round,pad=0.35",
    "facecolor": "white",
    "edgecolor": "#c8d1dc",
    "alpha": 0.94,
}


def apply_plot_style():
    style_name = "seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default"
    plt.style.use(style_name)


def get_plot_dir():
    plot_dir = Path("plots")
    plot_dir.mkdir(exist_ok=True)
    return plot_dir


def save_figure(fig, plot_dir, filename, dpi=280):
    output_path = plot_dir / filename
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    print(f"✓ Saved: {output_path}")


def style_panel(ax, title, xlabel, ylabel):
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.28)


def add_takeaway(ax, text, location="lower right"):
    anchors = {
        "lower right": (0.98, 0.03, "right", "bottom"),
        "upper left": (0.02, 0.97, "left", "top"),
        "upper right": (0.98, 0.97, "right", "top"),
        "lower left": (0.02, 0.03, "left", "bottom"),
    }
    x, y, ha, va = anchors[location]
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va, bbox=TEXT_BOX)


def highlight_window(ax, start, end):
    ax.axvspan(start, end, color=FOCUS_SHADE, alpha=0.35, zorder=0)


def cumulative_integral(values, time):
    cumulative = np.zeros_like(values)
    cumulative[1:] = np.cumsum(0.5 * (values[1:] + values[:-1]) * np.diff(time))
    return cumulative


def moving_average(values, window):
    kernel = np.ones(window) / window
    return np.convolve(values, kernel, mode="same")
