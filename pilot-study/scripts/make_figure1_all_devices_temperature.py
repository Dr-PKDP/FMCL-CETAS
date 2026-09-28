from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd

# Usage:
#   python make_figure1_all_devices_temperature.py "C:\Users\Dell\OneDrive\Desktop\FMCL_Pilot2"
#
# The folder may contain arbitrary CSV filenames. This script identifies final files
# from the device_label and run_id columns, discards incomplete/older duplicates by
# retaining the file with greatest elapsed-time coverage, and requires one final CSV
# for each device-by-run combination used in the figure.

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
OUTDIR = ROOT / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PNG = OUTDIR / "Figure1_all_devices_battery_temperature_trajectories.png"
OUTPUT_PDF = OUTDIR / "Figure1_all_devices_battery_temperature_trajectories.pdf"

DEVICES = ["oppo_a78_5g", "lenovo_tablet", "motorola_device"]
DEVICE_TITLES = {
    "oppo_a78_5g": "Oppo A78 5G",
    "lenovo_tablet": "Lenovo tablet",
    "motorola_device": "Motorola device",
}

# One hue family per device. Within each device, workload and policy are distinguished
# by shade and line style so that device identity remains readable in every panel.
# A single condition-based palette is used for all devices.
# Rows identify devices; colors identify workload type.
CONDITION_COLORS = {
    "idle": "#555555",       # Neutral dark gray
    "compact": "#0072B2",    # Bright blue
    "high": "#D55E00",       # Bright vermilion/orange-red
}

RUN_META = {
    "C1":   {"power": "AC-connected", "kind": "idle",    "label": "C1: Idle",                    "ls": "--", "lw": 2.1},
    "C2-L": {"power": "AC-connected", "kind": "compact", "label": "C2-L: Compact, continuous", "ls": "-",  "lw": 2.4},
    "C2-H": {"power": "AC-connected", "kind": "high",    "label": "C2-H: High, continuous",    "ls": "-",  "lw": 2.4},
    "C3-L": {"power": "Unplugged",    "kind": "compact", "label": "C3-L: Compact, continuous", "ls": "-",  "lw": 2.4},
    "C3-H": {"power": "Unplugged",    "kind": "high",    "label": "C3-H: High, continuous",    "ls": "-",  "lw": 2.4},
    "C4-L": {"power": "AC-connected", "kind": "compact", "label": "C4-L: Compact, duty cycle", "ls": "--", "lw": 2.4},
    "C4-H": {"power": "AC-connected", "kind": "high",    "label": "C4-H: High, duty cycle",    "ls": "--", "lw": 2.4},
    "C5-L": {"power": "Unplugged",    "kind": "compact", "label": "C5-L: Compact, duty cycle", "ls": "--", "lw": 2.4},
    "C5-H": {"power": "Unplugged",    "kind": "high",    "label": "C5-H: High, duty cycle",    "ls": "--", "lw": 2.4},
}

PANEL_RUNS = {
    "AC-connected": ["C1", "C2-L", "C2-H", "C4-L", "C4-H"],
    "Unplugged": ["C3-L", "C3-H", "C5-L", "C5-H"],
}
REQUIRED_RUNS = [run for runs in PANEL_RUNS.values() for run in runs]


def load_final_runs(root: Path):
    chosen = {}
    for csv_path in root.rglob("*.csv"):
        try:
            df = pd.read_csv(csv_path, low_memory=False)
        except Exception:
            continue
        required_columns = {"device_label", "run_id", "elapsed_seconds", "battery_temperature_c"}
        if df.empty or not required_columns.issubset(df.columns):
            continue

        device = str(df["device_label"].iloc[0]).strip().lower()
        run_id = str(df["run_id"].iloc[0]).strip().upper()
        if device not in DEVICES or run_id not in REQUIRED_RUNS:
            continue

        d = df[["elapsed_seconds", "battery_temperature_c"]].copy()
        d["elapsed_seconds"] = pd.to_numeric(d["elapsed_seconds"], errors="coerce")
        d["battery_temperature_c"] = pd.to_numeric(d["battery_temperature_c"], errors="coerce")
        d = d.dropna().sort_values("elapsed_seconds").drop_duplicates("elapsed_seconds")
        if d.empty:
            continue

        key = (device, run_id)
        # A duplicated preliminary export is never selected over a longer final file.
        if key not in chosen or d["elapsed_seconds"].max() > chosen[key][1]["elapsed_seconds"].max():
            chosen[key] = (csv_path, d)
    return chosen


runs = load_final_runs(ROOT)
missing = [f"{DEVICE_TITLES[d]} {r}" for d in DEVICES for r in REQUIRED_RUNS if (d, r) not in runs]
if missing:
    raise SystemExit(
        "The complete three-device Figure 1 requires final CSV files for every listed run.\n"
        "Missing:\n- " + "\n- ".join(missing) +
        "\n\nAdd the missing final CSV files under the project folder, then rerun the script."
    )

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10.5,
    "text.color": "black",
    "axes.labelcolor": "black",
    "axes.edgecolor": "black",
    "axes.titlecolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "axes.labelsize": 11.0,
    "axes.titlesize": 12.0,
    "xtick.labelsize": 10.0,
    "ytick.labelsize": 10.0,
    "legend.fontsize": 9.5,
    "figure.dpi": 120,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

all_temperatures = pd.concat([df["battery_temperature_c"] for _, df in runs.values()])
ymin = max(0, float(all_temperatures.min()) - 0.7)
ymax = float(all_temperatures.max()) + 0.7

fig, axes = plt.subplots(3, 2, figsize=(11.2, 9.0), sharex=True, sharey=True)
for row, device in enumerate(DEVICES):
    for col, (power, run_ids) in enumerate(PANEL_RUNS.items()):
        ax = axes[row, col]
        for run_id in run_ids:
            _, df = runs[(device, run_id)]
            meta = RUN_META[run_id]
            ax.plot(
                df["elapsed_seconds"],
                df["battery_temperature_c"],
                color=CONDITION_COLORS[meta["kind"]],
                linestyle=meta["ls"],
                linewidth=meta["lw"],
            )
        ax.axvline(60, color="#202020", linestyle=":", linewidth=0.9, alpha=0.85)
        ax.set_xlim(0, 900)
        ax.set_ylim(ymin, ymax)
        ax.set_xticks([0, 180, 360, 540, 720, 900])
        ax.grid(True, color="#dddddd", linewidth=0.55, alpha=0.9)
        if row == 0:
            ax.set_title(power, fontweight="bold", fontsize=12, color="black")
        if col == 0:
            ax.set_ylabel(
    f"{DEVICE_TITLES[device]}\nBattery temperature (°C)",
    fontsize=11,
    color="black",
)
        if row == len(DEVICES) - 1:
            ax.set_xlabel("Elapsed time (s)")

condition_legend = [
    Line2D(
        [0], [0],
        color=CONDITION_COLORS["idle"],
        linewidth=2.1,
        linestyle="--",
        label="C1: AC-connected idle",
    ),
    Line2D(
        [0], [0],
        color=CONDITION_COLORS["compact"],
        linewidth=2.4,
        linestyle="-",
        label="Compact, continuous (C2/C3)",
    ),
    Line2D(
        [0], [0],
        color=CONDITION_COLORS["high"],
        linewidth=2.4,
        linestyle="-",
        label="High, continuous (C2/C3)",
    ),
    Line2D(
        [0], [0],
        color=CONDITION_COLORS["compact"],
        linewidth=2.4,
        linestyle="--",
        label="Compact, duty cycle (C4/C5)",
    ),
    Line2D(
        [0], [0],
        color=CONDITION_COLORS["high"],
        linewidth=2.4,
        linestyle="--",
        label="High, duty cycle (C4/C5)",
    ),
    Line2D(
        [0], [0],
        color="black",
        linewidth=1.1,
        linestyle=":",
        label="Steady-state window begins (60 s)",
    ),
]

fig.legend(
    handles=condition_legend,
    loc="lower center",
    ncol=3,
    fontsize=10,
    frameon=True,
    framealpha=1.0,
    edgecolor="black",
    labelcolor="black",
    bbox_to_anchor=(0.5, -0.012),
)
fig.suptitle("Battery-temperature trajectories across devices and experimental conditions", y=0.995, fontsize=12.5, fontweight="bold", color="black",)
fig.tight_layout(rect=(0, 0.075, 1, 0.975))
fig.savefig(OUTPUT_PNG, dpi=600, bbox_inches="tight")
fig.savefig(OUTPUT_PDF, bbox_inches="tight")
plt.close(fig)

print(f"Created PNG: {OUTPUT_PNG}")
print(f"Created PDF: {OUTPUT_PDF}")
print("Selected source files:")
for device in DEVICES:
    for run_id in REQUIRED_RUNS:
        print(f"  {DEVICE_TITLES[device]} | {run_id}: {runs[(device, run_id)][0]}")
