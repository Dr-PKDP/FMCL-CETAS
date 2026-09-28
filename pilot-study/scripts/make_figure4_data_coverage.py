#!/usr/bin/env python3
"""Generate Figure 4: telemetry coverage of retained device-run files.

Panel A shows observed elapsed duration per device-run file.
Panel B shows valid telemetry-record count per device-run file.

The script counts rows within each device/run file. It does not count unique
devices per condition. It expects the anonymized sample-level raw telemetry
archive created by rebuild_raw_telemetry_from_source.ps1.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RAW_DIRECTORY = REPOSITORY_ROOT / "data" / "raw"
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "results" / "figures"

RUN_ORDER = ["C0", "C1", "C2-L", "C2-H", "C3-L", "C3-H", "C4-L", "C4-H", "C5-L", "C5-H"]
DEVICE_ORDER = ["oppo_a78_5g", "lenovo_tablet", "motorola_device"]

DEVICE_LABELS = {
    "oppo_a78_5g": "OPPO A78 5G",
    "lenovo_tablet": "Lenovo tablet",
    "motorola_device": "Motorola device",
}

COLORS = {
    "oppo_a78_5g": "#1f77b4",
    "lenovo_tablet": "#ff7f0e",
    "motorola_device": "#2ca02c",
}

OFFSETS = {
    "oppo_a78_5g": -0.20,
    "lenovo_tablet": 0.00,
    "motorola_device": 0.20,
}


def normalize_column_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def canonical_device(value: object) -> str:
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    compact = re.sub(r"[^a-z0-9]+", "", text)
    aliases = {
        "oppoa785g": "oppo_a78_5g",
        "oppoa78": "oppo_a78_5g",
        "lenovotablet": "lenovo_tablet",
        "lenovo": "lenovo_tablet",
        "tablet": "lenovo_tablet",
        "motoroladevice": "motorola_device",
        "motorola": "motorola_device",
    }
    return aliases.get(compact, text)


def canonical_run(value: object) -> str:
    text = str(value).strip().upper().replace("_", "-").replace(" ", "")
    match = re.fullmatch(r"(C[0-5])(?:-?([LH]))?", text)
    if not match:
        return text
    base, suffix = match.groups()
    return f"{base}-{suffix}" if suffix else base


def rename_known_columns(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "devicelabel": "device_label",
        "device": "device_label",
        "runid": "run_id",
        "run": "run_id",
        "elapsedseconds": "elapsed_seconds",
        "elapsedsecond": "elapsed_seconds",
        "sampleok": "sample_ok",
        "samplevalid": "sample_ok",
    }
    rename_map = {}
    for column in frame.columns:
        normalized = normalize_column_name(column)
        if normalized in aliases:
            rename_map[column] = aliases[normalized]
    return frame.rename(columns=rename_map)


def read_telemetry_file(path: Path) -> pd.DataFrame | None:
    try:
        frame = pd.read_csv(path, low_memory=False)
    except Exception as error:
        print(f"Skipping unreadable CSV: {path.relative_to(REPOSITORY_ROOT)} ({error})")
        return None

    frame = rename_known_columns(frame)
    required = {"device_label", "run_id", "elapsed_seconds"}
    if not required.issubset(frame.columns):
        return None

    frame = frame.copy()
    frame["device_label"] = frame["device_label"].map(canonical_device)
    frame["run_id"] = frame["run_id"].map(canonical_run)
    frame["elapsed_seconds"] = pd.to_numeric(frame["elapsed_seconds"], errors="coerce")
    frame["source_file"] = str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/")
    return frame


def load_telemetry() -> pd.DataFrame:
    if not RAW_DIRECTORY.is_dir():
        raise FileNotFoundError(f"Raw-data directory not found: {RAW_DIRECTORY}")

    frames = []
    for path in sorted(RAW_DIRECTORY.rglob("*.csv")):
        if path.name.lower() == "manifest.csv" or "telemetry" not in path.name.lower():
            continue
        frame = read_telemetry_file(path)
        if frame is not None:
            frames.append(frame)

    if not frames:
        raise RuntimeError("No readable sample-level telemetry CSV files were found.")

    telemetry = pd.concat(frames, ignore_index=True, sort=False)
    telemetry = telemetry.loc[
        telemetry["device_label"].isin(DEVICE_ORDER)
        & telemetry["run_id"].isin(RUN_ORDER)
    ].copy()

    if telemetry.empty:
        raise RuntimeError("No telemetry rows match the expected devices and run IDs.")

    candidates = (
        telemetry.groupby(["source_file", "device_label", "run_id"], as_index=False)
        .agg(
            source_rows=("elapsed_seconds", "size"),
            source_max_elapsed=("elapsed_seconds", "max"),
        )
        .sort_values(
            ["device_label", "run_id", "source_max_elapsed", "source_rows", "source_file"],
            ascending=[True, True, False, False, True],
        )
    )

    selected = (
        candidates.groupby(["device_label", "run_id"], as_index=False)
        .head(1)[["source_file", "device_label", "run_id"]]
    )

    return telemetry.merge(
        selected,
        how="inner",
        on=["source_file", "device_label", "run_id"],
    )


def valid_sample_mask(frame: pd.DataFrame) -> pd.Series:
    mask = frame["elapsed_seconds"].notna()
    if "sample_ok" in frame.columns:
        mask &= frame["sample_ok"].astype(str).str.strip().str.upper().eq("TRUE")
    return mask


def make_coverage_table(telemetry: pd.DataFrame) -> pd.DataFrame:
    valid = telemetry.loc[valid_sample_mask(telemetry)].copy()
    coverage = (
        valid.groupby(["device_label", "run_id", "source_file"], as_index=False)
        .agg(
            observed_elapsed_seconds=("elapsed_seconds", "max"),
            valid_telemetry_records=("elapsed_seconds", "size"),
        )
    )

    coverage["device_label"] = pd.Categorical(
        coverage["device_label"], categories=DEVICE_ORDER, ordered=True
    )
    coverage["run_id"] = pd.Categorical(
        coverage["run_id"], categories=RUN_ORDER, ordered=True
    )
    return coverage.sort_values(["run_id", "device_label"]).reset_index(drop=True)


def validate_coverage(coverage: pd.DataFrame) -> None:
    expected = pd.MultiIndex.from_product(
        [DEVICE_ORDER, RUN_ORDER], names=["device_label", "run_id"]
    )
    observed = pd.MultiIndex.from_frame(
        coverage[["device_label", "run_id"]].astype(str)
    )
    missing = expected.difference(observed)

    if len(missing):
        names = ", ".join(f"{device}/{run}" for device, run in missing)
        raise ValueError(f"Missing expected device/run coverage rows: {names}")

    if len(coverage) != 30:
        raise ValueError(f"Expected 30 device-run coverage rows; found {len(coverage)}.")

    if coverage.duplicated(["device_label", "run_id"]).any():
        raise ValueError("More than one selected coverage row exists for a device/run pair.")

    if (coverage["valid_telemetry_records"] <= 10).any():
        offenders = coverage.loc[
            coverage["valid_telemetry_records"] <= 10,
            ["device_label", "run_id", "valid_telemetry_records", "source_file"],
        ]
        raise ValueError(
            "Implausibly low telemetry-record count; check whether event logs were "
            "used instead of sample-level telemetry:\n" + offenders.to_string(index=False)
        )

    c2h = coverage.loc[
        (coverage["device_label"].astype(str) == "lenovo_tablet")
        & (coverage["run_id"].astype(str) == "C2-H")
    ]
    if len(c2h) != 1:
        raise ValueError("Expected exactly one Lenovo C2-H coverage record.")
    if int(c2h["valid_telemetry_records"].iloc[0]) != 78:
        raise ValueError("Expected Lenovo C2-H to contain exactly 78 valid telemetry records.")


def save_coverage_values(coverage: pd.DataFrame) -> Path:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIRECTORY / "Figure4_telemetry_coverage_values.csv"
    audit = coverage.copy()
    audit["device_label"] = audit["device_label"].astype(str)
    audit["run_id"] = audit["run_id"].astype(str)
    audit.to_csv(output, index=False)
    return output


def add_panel_label(axis: plt.Axes, label: str) -> None:
    axis.text(
        0.01,
        0.99,
        label,
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize=14,
        fontweight="bold",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 1.5},
        zorder=5,
    )


def plot_figure(coverage: pd.DataFrame) -> tuple[Path, Path]:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # No overall figure title: the manuscript caption provides full context.
    figure, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(13.4, 5.7), constrained_layout=True)
    x_positions = {run: index for index, run in enumerate(RUN_ORDER)}

    for device in DEVICE_ORDER:
        subset = coverage.loc[coverage["device_label"].astype(str) == device].copy()
        subset = subset.sort_values("run_id")
        x = np.array(
            [x_positions[str(run)] + OFFSETS[device] for run in subset["run_id"]],
            dtype=float,
        )

        ax_a.scatter(
            x,
            subset["observed_elapsed_seconds"],
            s=52,
            color=COLORS[device],
            edgecolor="black",
            linewidth=0.5,
            alpha=0.92,
            label=DEVICE_LABELS[device],
            zorder=3,
        )
        ax_b.scatter(
            x,
            subset["valid_telemetry_records"],
            s=52,
            color=COLORS[device],
            edgecolor="black",
            linewidth=0.5,
            alpha=0.92,
            label=DEVICE_LABELS[device],
            zorder=3,
        )

    ax_a.axhline(900, color="0.35", linestyle="--", linewidth=1.0, alpha=0.85, zorder=1)
    ax_a.set_ylabel("Observed elapsed time (s)")
    ax_a.set_xlabel("Condition")
    ax_a.set_xticks(range(len(RUN_ORDER)))
    ax_a.set_xticklabels(RUN_ORDER, rotation=45, ha="right")
    ax_a.set_ylim(870, 910)
    ax_a.set_yticks([870, 880, 890, 900, 910])
    ax_a.grid(axis="y", linestyle=":", alpha=0.6, zorder=0)
    add_panel_label(ax_a, "A")
    ax_a.annotate(
        "Planned 900 s",
        xy=(len(RUN_ORDER) - 0.35, 900),
        xytext=(0, 5),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=8.5,
        color="0.25",
    )

    ax_b.axhline(90, color="0.35", linestyle="--", linewidth=1.0, alpha=0.85, zorder=1)
    ax_b.set_ylabel("Valid telemetry records")
    ax_b.set_xlabel("Condition")
    ax_b.set_xticks(range(len(RUN_ORDER)))
    ax_b.set_xticklabels(RUN_ORDER, rotation=45, ha="right")
    ax_b.set_ylim(70, 96)
    ax_b.set_yticks([70, 75, 80, 85, 90, 95])
    ax_b.grid(axis="y", linestyle=":", alpha=0.6, zorder=0)
    add_panel_label(ax_b, "B")
    ax_b.annotate(
        "Nominal 90 records",
        xy=(len(RUN_ORDER) - 0.35, 90),
        xytext=(0, 5),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=8.5,
        color="0.25",
    )

    lenovo_c2h = coverage.loc[
        (coverage["device_label"].astype(str) == "lenovo_tablet")
        & (coverage["run_id"].astype(str) == "C2-H")
    ].iloc[0]
    c2h_x = x_positions["C2-H"] + OFFSETS["lenovo_tablet"]
    c2h_y = float(lenovo_c2h["valid_telemetry_records"])
    ax_b.annotate(
        "Lenovo C2-H\n78 records",
        xy=(c2h_x, c2h_y),
        xytext=(34, -16),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=8.5,
        color=COLORS["lenovo_tablet"],
        arrowprops={
            "arrowstyle": "-",
            "color": COLORS["lenovo_tablet"],
            "linewidth": 0.9,
        },
    )

    handles, labels = ax_a.get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="lower center",
        ncol=3,
        bbox_to_anchor=(0.5, -0.07),
        frameon=True,
        fontsize=9,
    )

    pdf_output = OUTPUT_DIRECTORY / "Figure4_telemetry_coverage.pdf"
    png_output = OUTPUT_DIRECTORY / "Figure4_telemetry_coverage.png"
    figure.savefig(pdf_output, dpi=300, bbox_inches="tight")
    figure.savefig(png_output, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return pdf_output, png_output


def main() -> None:
    telemetry = load_telemetry()
    coverage = make_coverage_table(telemetry)
    validate_coverage(coverage)

    print("\nFigure 4 coverage values:")
    print(
        coverage[
            [
                "device_label",
                "run_id",
                "observed_elapsed_seconds",
                "valid_telemetry_records",
                "source_file",
            ]
        ].to_string(index=False)
    )

    values_csv = save_coverage_values(coverage)
    pdf_output, png_output = plot_figure(coverage)

    print("\nFigure 4 created successfully.")
    print(f"Coverage values: {values_csv}")
    print(f"PDF: {pdf_output}")
    print(f"PNG: {png_output}")


if __name__ == "__main__":
    main()
