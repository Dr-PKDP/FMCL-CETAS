from pathlib import Path
import shutil
import sys
import tempfile

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

# Figure 3: duty-cycle active-versus-pause phase effects.
#
# Usage:
#   python make_figure3_duty_cycle_phase_effects_final.py "C:\Users\Dell\OneDrive\Desktop\FMCL_Pilot2"
#
# Fixed final input:
#   manuscript_tables_v3\Table7_duty_cycle_phases.csv
#
# Required columns in the final Table 7 file:
#   device_label
#   run_id
#   active_minus_pause_temperature_c
#   active_minus_pause_cpu_busy_percentage_points

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
TABLE_PATH = ROOT / "manuscript_tables_v3" / "Table7_duty_cycle_phases.csv"

PROJECT_OUTDIR = ROOT / "figures"
PROJECT_OUTDIR.mkdir(parents=True, exist_ok=True)

# Render outside OneDrive first, then copy the completed figure files into the project folder.
TEMP_OUTDIR = Path(tempfile.gettempdir()) / "FMCL_Figure_Exports"
TEMP_OUTDIR.mkdir(parents=True, exist_ok=True)
TEMP_PNG = TEMP_OUTDIR / "Figure3_duty_cycle_phase_effects.png"
TEMP_PDF = TEMP_OUTDIR / "Figure3_duty_cycle_phase_effects.pdf"
FINAL_PNG = PROJECT_OUTDIR / "Figure3_duty_cycle_phase_effects.png"
FINAL_PDF = PROJECT_OUTDIR / "Figure3_duty_cycle_phase_effects.pdf"

DEVICE_ORDER = ["oppo_a78_5g", "lenovo_tablet", "motorola_device"]
DEVICE_TITLES = {
    "oppo_a78_5g": "Oppo A78 5G",
    "lenovo_tablet": "Lenovo tablet",
    "motorola_device": "Motorola device",
}

# Same common bright condition palette used in Figures 1 and 2.
COLORS = {
    "compact": "#0072B2",  # Bright blue
    "high": "#D55E00",     # Bright vermilion/orange-red
}

RUN_META = {
    "C4-L": {"kind": "compact", "label": "C4-L\nAC, Compact"},
    "C4-H": {"kind": "high",    "label": "C4-H\nAC, High"},
    "C5-L": {"kind": "compact", "label": "C5-L\nUnplugged, Compact"},
    "C5-H": {"kind": "high",    "label": "C5-H\nUnplugged, High"},
}
RUN_ORDER = list(RUN_META)

TEMPERATURE_COLUMN = "active_minus_pause_temperature_c"
CPU_COLUMN = "active_minus_pause_cpu_busy_percentage_points"
REQUIRED_COLUMNS = {"device_label", "run_id", TEMPERATURE_COLUMN, CPU_COLUMN}

if not TABLE_PATH.exists():
    raise SystemExit(
        "Final Table 7 file was not found:\n"
        f"{TABLE_PATH}\n\n"
        "Confirm that Table7_duty_cycle_phases.csv is stored in manuscript_tables_v3."
    )

df = pd.read_csv(TABLE_PATH)
missing_columns = REQUIRED_COLUMNS.difference(df.columns)
if missing_columns:
    raise SystemExit(
        "The final Table 7 file is missing required columns:\n- " +
        "\n- ".join(sorted(missing_columns)) +
        "\n\nAvailable columns:\n- " + "\n- ".join(str(column) for column in df.columns)
    )

df["device_label"] = df["device_label"].astype(str).str.strip().str.lower()
df["run_id"] = df["run_id"].astype(str).str.strip().str.upper()
df[TEMPERATURE_COLUMN] = pd.to_numeric(df[TEMPERATURE_COLUMN], errors="coerce")
df[CPU_COLUMN] = pd.to_numeric(df[CPU_COLUMN], errors="coerce")

validation_errors = []
for device in DEVICE_ORDER:
    for run_id in RUN_ORDER:
        selected = df[(df["device_label"] == device) & (df["run_id"] == run_id)]
        if len(selected) != 1:
            validation_errors.append(f"{DEVICE_TITLES[device]} {run_id}: found {len(selected)} rows")
            continue
        if pd.isna(selected.iloc[0][TEMPERATURE_COLUMN]):
            validation_errors.append(f"{DEVICE_TITLES[device]} {run_id}: missing temperature phase contrast")
        if pd.isna(selected.iloc[0][CPU_COLUMN]):
            validation_errors.append(f"{DEVICE_TITLES[device]} {run_id}: missing CPU-busy phase contrast")

if validation_errors:
    raise SystemExit("Final Table 7 validation failed:\n- " + "\n- ".join(validation_errors))

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

fig, axes = plt.subplots(2, 1, figsize=(10.8, 8.4), sharex=True)
METRICS = [
    (
        TEMPERATURE_COLUMN,
        "Active minus pause\nbattery temperature (°C)",
        "A",
    ),
    (
        CPU_COLUMN,
        "Active minus pause\nCPU busy (percentage points)",
        "B",
    ),
]

x_base = np.arange(len(RUN_ORDER), dtype=float)
x_offsets = {
    "oppo_a78_5g": -0.20,
    "lenovo_tablet": 0.00,
    "motorola_device": 0.20,
}
marker_map = {
    "oppo_a78_5g": "o",
    "lenovo_tablet": "s",
    "motorola_device": "^",
}

for ax, (metric, ylabel, panel_letter) in zip(axes, METRICS):
    for device in DEVICE_ORDER:
        device_values = df[df["device_label"] == device].set_index("run_id")
        for index, run_id in enumerate(RUN_ORDER):
            value = float(device_values.loc[run_id, metric])
            ax.scatter(
                x_base[index] + x_offsets[device],
                value,
                s=78,
                marker=marker_map[device],
                facecolor=COLORS[RUN_META[run_id]["kind"]],
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
axes[-1].set_xticklabels([RUN_META[run_id]["label"] for run_id in RUN_ORDER], color="black")
axes[-1].set_xlabel("Duty-cycle condition", fontsize=12.5, color="black")

legend_handles = [
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
    bbox_to_anchor=(0.5, 0.008),
)

# No overall title: captions define panels A and B.
fig.tight_layout(rect=(0, 0.115, 1, 0.995))
fig.savefig(TEMP_PNG, dpi=600, bbox_inches="tight")
fig.savefig(TEMP_PDF, bbox_inches="tight")
plt.close(fig)

try:
    shutil.copy2(TEMP_PNG, FINAL_PNG)
    shutil.copy2(TEMP_PDF, FINAL_PDF)
    print(f"Using final Table 7: {TABLE_PATH}")
    print(f"Temperature contrast field: {TEMPERATURE_COLUMN}")
    print(f"CPU-busy contrast field: {CPU_COLUMN}")
    print(f"Created PNG: {FINAL_PNG}")
    print(f"Created PDF: {FINAL_PDF}")
except OSError as exc:
    print(f"Rendered PNG: {TEMP_PNG}")
    print(f"Rendered PDF: {TEMP_PDF}")
    print(f"Could not copy files to the OneDrive project directory: {exc}")
    print("Close any program previewing the output files, then rerun or copy the rendered files manually.")
