from pathlib import Path
import shutil
import sys
import tempfile

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

# Figure 2: paired run-level battery and CPU outcomes.
# Usage:
#   python make_figure2_run_level_outcomes_updated.py "C:\Users\Dell\OneDrive\Desktop\FMCL_Pilot2"
#
# Required input:
#   manuscript_tables_v3\Table5_run_level_outcomes.csv
#
# Required Table 5 columns:
#   device_label, run_id, battery_level_delta_percentage_points,
#   mean_cpu_busy_percent

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
TABLE_PATH = ROOT / "manuscript_tables_v3" / "Table5_run_level_outcomes.csv"

PROJECT_OUTDIR = ROOT / "figures"
PROJECT_OUTDIR.mkdir(parents=True, exist_ok=True)

# Render outside OneDrive first, then copy completed files into the project folder.
TEMP_OUTDIR = Path(tempfile.gettempdir()) / "FMCL_Figure_Exports"
TEMP_OUTDIR.mkdir(parents=True, exist_ok=True)
TEMP_PNG = TEMP_OUTDIR / "Figure2_run_level_outcomes.png"
TEMP_PDF = TEMP_OUTDIR / "Figure2_run_level_outcomes.pdf"
FINAL_PNG = PROJECT_OUTDIR / "Figure2_run_level_outcomes.png"
FINAL_PDF = PROJECT_OUTDIR / "Figure2_run_level_outcomes.pdf"

DEVICE_ORDER = ["oppo_a78_5g", "lenovo_tablet", "motorola_device"]
DEVICE_TITLES = {
    "oppo_a78_5g": "Oppo A78 5G",
    "lenovo_tablet": "Lenovo tablet",
    "motorola_device": "Motorola device",
}

# Common bright condition-based palette, identical to Figure 1.
COLORS = {
    "idle": "#555555",       # Neutral dark gray
    "compact": "#0072B2",    # Bright blue
    "high": "#D55E00",       # Bright vermilion/orange-red
}

RUN_META = {
    "C0":   {"kind": "idle",    "label": "C0: Unplugged idle"},
    "C1":   {"kind": "idle",    "label": "C1: AC-connected idle"},
    "C2-L": {"kind": "compact", "label": "C2-L: Compact, continuous"},
    "C2-H": {"kind": "high",    "label": "C2-H: High, continuous"},
    "C3-L": {"kind": "compact", "label": "C3-L: Compact, continuous"},
    "C3-H": {"kind": "high",    "label": "C3-H: High, continuous"},
    "C4-L": {"kind": "compact", "label": "C4-L: Compact, duty cycle"},
    "C4-H": {"kind": "high",    "label": "C4-H: High, duty cycle"},
    "C5-L": {"kind": "compact", "label": "C5-L: Compact, duty cycle"},
    "C5-H": {"kind": "high",    "label": "C5-H: High, duty cycle"},
}

# Each tuple defines a legitimate within-device pair.
# A solid connector is drawn only within each pair; it does not imply a time series
# or connect unrelated comparison groups.
COMPARISONS = [
    ("C0", "C1", "Idle\nUnplugged → AC"),
    ("C2-L", "C4-L", "Compact\nAC: cont. → duty"),
    ("C2-H", "C4-H", "High\nAC: cont. → duty"),
    ("C3-L", "C5-L", "Compact\nUnplugged: cont. → duty"),
    ("C3-H", "C5-H", "High\nUnplugged: cont. → duty"),
]

REQUIRED_COLUMNS = {
    "device_label",
    "run_id",
    "battery_level_delta_percentage_points",
    "mean_cpu_busy_percent",
}

if not TABLE_PATH.exists():
    raise SystemExit(
        f"Table 5 not found:\n{TABLE_PATH}\n\n"
        "Confirm that Table5_run_level_outcomes.csv is located in manuscript_tables_v3."
    )

df = pd.read_csv(TABLE_PATH)
missing_columns = REQUIRED_COLUMNS.difference(df.columns)
if missing_columns:
    raise SystemExit("Table 5 is missing required columns:\n- " + "\n- ".join(sorted(missing_columns)))

df["device_label"] = df["device_label"].astype(str).str.strip().str.lower()
df["run_id"] = df["run_id"].astype(str).str.strip().str.upper()
for column in ["battery_level_delta_percentage_points", "mean_cpu_busy_percent"]:
    df[column] = pd.to_numeric(df[column], errors="coerce")

validation_errors = []
for device in DEVICE_ORDER:
    for left_run, right_run, _ in COMPARISONS:
        for run_id in (left_run, right_run):
            selected = df[(df["device_label"] == device) & (df["run_id"] == run_id)]
            if len(selected) != 1:
                validation_errors.append(f"{DEVICE_TITLES[device]} {run_id}: found {len(selected)} rows")
            else:
                missing_metrics = [
                    metric
                    for metric in ["battery_level_delta_percentage_points", "mean_cpu_busy_percent"]
                    if pd.isna(selected.iloc[0][metric])
                ]
                if missing_metrics:
                    validation_errors.append(
                        f"{DEVICE_TITLES[device]} {run_id}: missing " + ", ".join(missing_metrics)
                    )

if validation_errors:
    raise SystemExit("Table 5 validation failed:\n- " + "\n- ".join(validation_errors))

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11.5,
    "text.color": "black",
    "axes.labelcolor": "black",
    "axes.edgecolor": "black",
    "axes.titlecolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "axes.labelsize": 12.5,
    "axes.titlesize": 13.5,
    "xtick.labelsize": 10.8,
    "ytick.labelsize": 11.0,
    "legend.fontsize": 10.5,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

fig, axes = plt.subplots(2, 1, figsize=(11.6, 8.6), sharex=True)

# The two panels are labelled only A and B. Metric definitions belong in the caption.
METRICS = [
    (
        "battery_level_delta_percentage_points",
        "Battery-level change\n(percentage points)",
        "A",
    ),
    (
        "mean_cpu_busy_percent",
        "Mean CPU busy (%)",
        "B",
    ),
]

x_base = np.arange(len(COMPARISONS), dtype=float) * 2.35
x_offsets = {
    "oppo_a78_5g": -0.30,
    "lenovo_tablet": 0.00,
    "motorola_device": 0.30,
}
marker_map = {
    "oppo_a78_5g": "o",
    "lenovo_tablet": "s",
    "motorola_device": "^",
}

for ax, (metric, ylabel, panel_letter) in zip(axes, METRICS):
    for device in DEVICE_ORDER:
        device_values = df[df["device_label"] == device].set_index("run_id")

        for comparison_index, (left_run, right_run, _) in enumerate(COMPARISONS):
            left_meta = RUN_META[left_run]
            right_meta = RUN_META[right_run]

            x_left = x_base[comparison_index] - 0.37 + x_offsets[device]
            x_right = x_base[comparison_index] + 0.37 + x_offsets[device]
            y_left = float(device_values.loc[left_run, metric])
            y_right = float(device_values.loc[right_run, metric])

            # The continuous solid segment shows a matched, within-device contrast.
            ax.plot(
                [x_left, x_right],
                [y_left, y_right],
                color="#333333",
                linewidth=1.55,
                alpha=0.92,
                zorder=1,
            )

            ax.scatter(
                x_left,
                y_left,
                s=74,
                marker=marker_map[device],
                facecolor=COLORS[left_meta["kind"]],
                edgecolor="black",
                linewidth=0.9,
                zorder=3,
            )
            ax.scatter(
                x_right,
                y_right,
                s=74,
                marker=marker_map[device],
                facecolor=COLORS[right_meta["kind"]],
                edgecolor="black",
                linewidth=0.9,
                zorder=3,
            )

    ax.axhline(0, color="black", linewidth=1.05, zorder=0)
    ax.set_ylabel(ylabel, fontsize=12.5, color="black")
    ax.set_title(panel_letter, loc="left", fontweight="bold", fontsize=13.5, color="black")
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.70, alpha=0.92)
    ax.set_axisbelow(True)

axes[-1].set_xticks(x_base)
axes[-1].set_xticklabels([label for _, _, label in COMPARISONS], color="black")
axes[-1].set_xlabel(
    "Matched within-device condition comparison",
    fontsize=12.5,
    color="black",
)

# Shared legend: colors encode condition; marker shapes encode device.
legend_handles = [
    Line2D(
        [0], [0],
        marker="o",
        color="none",
        markerfacecolor=COLORS["idle"],
        markeredgecolor="black",
        markersize=8.5,
        label="Idle",
    ),
    Line2D(
        [0], [0],
        marker="o",
        color="none",
        markerfacecolor=COLORS["compact"],
        markeredgecolor="black",
        markersize=8.5,
        label="Compact workload",
    ),
    Line2D(
        [0], [0],
        marker="o",
        color="none",
        markerfacecolor=COLORS["high"],
        markeredgecolor="black",
        markersize=8.5,
        label="High workload",
    ),
    Line2D(
        [0], [0],
        marker="o",
        color="none",
        markerfacecolor="white",
        markeredgecolor="black",
        markersize=8.5,
        label="Oppo A78 5G",
    ),
    Line2D(
        [0], [0],
        marker="s",
        color="none",
        markerfacecolor="white",
        markeredgecolor="black",
        markersize=8.5,
        label="Lenovo tablet",
    ),
    Line2D(
        [0], [0],
        marker="^",
        color="none",
        markerfacecolor="white",
        markeredgecolor="black",
        markersize=8.5,
        label="Motorola device",
    ),
]

fig.legend(
    handles=legend_handles,
    loc="lower center",
    ncol=3,
    frameon=True,
    framealpha=1.0,
    edgecolor="black",
    labelcolor="black",
    bbox_to_anchor=(0.5, 0.006),
)

# No overall title: panel letters and caption provide the required description.
fig.tight_layout(rect=(0, 0.115, 1, 0.995))

fig.savefig(TEMP_PNG, dpi=600, bbox_inches="tight")
fig.savefig(TEMP_PDF, bbox_inches="tight")
plt.close(fig)

try:
    shutil.copy2(TEMP_PNG, FINAL_PNG)
    shutil.copy2(TEMP_PDF, FINAL_PDF)
    print(f"Created PNG: {FINAL_PNG}")
    print(f"Created PDF: {FINAL_PDF}")
except OSError as exc:
    print(f"Rendered PNG: {TEMP_PNG}")
    print(f"Rendered PDF: {TEMP_PDF}")
    print(f"Could not copy files to the OneDrive project directory: {exc}")
    print("Close any application previewing the output files, then rerun or manually copy the rendered files.")
