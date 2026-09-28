#!/usr/bin/env python3
"""Rebuild Table 3 from anonymized sample-level raw telemetry CSV files.

Table 3 contains temperature-only condition summaries:
- Median device-level maximum battery temperature (deg C)
- Observed battery-temperature range across valid samples (deg C)

The script intentionally does not pool signed battery-side power across devices.
It also writes a device/run audit table that can be used to reconcile the
maximum-temperature values reported in Supplementary Table S10.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RAW_DIRECTORY = REPOSITORY_ROOT / "data" / "raw"
PROCESSED_DIRECTORY = REPOSITORY_ROOT / "data" / "processed"
RESULTS_TABLE_DIRECTORY = REPOSITORY_ROOT / "results" / "tables"

RUN_ORDER = ["C0", "C1", "C2-L", "C2-H", "C3-L", "C3-H", "C4-L", "C4-H", "C5-L", "C5-H"]
DEVICE_ORDER = ["oppo_a78_5g", "lenovo_tablet", "motorola_device"]


class TableBuildError(RuntimeError):
    """Raised when raw data do not meet the expected pilot-study structure."""


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
        "batterytemperaturec": "battery_temperature_c",
        "batterytemperature": "battery_temperature_c",
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
    required = {"device_label", "run_id", "elapsed_seconds", "battery_temperature_c"}
    if not required.issubset(frame.columns):
        return None

    frame = frame.copy()
    frame["device_label"] = frame["device_label"].map(canonical_device)
    frame["run_id"] = frame["run_id"].map(canonical_run)
    frame["elapsed_seconds"] = pd.to_numeric(frame["elapsed_seconds"], errors="coerce")
    frame["battery_temperature_c"] = pd.to_numeric(
        frame["battery_temperature_c"], errors="coerce"
    )
    frame["source_file"] = str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/")
    return frame


def load_raw_telemetry() -> pd.DataFrame:
    if not RAW_DIRECTORY.is_dir():
        raise TableBuildError(f"Raw-data directory not found: {RAW_DIRECTORY}")

    frames = []
    for path in sorted(RAW_DIRECTORY.rglob("*.csv")):
        if path.name.lower() == "manifest.csv" or "telemetry" not in path.name.lower():
            continue
        frame = read_telemetry_file(path)
        if frame is not None:
            frames.append(frame)

    if not frames:
        raise TableBuildError("No sample-level telemetry CSV files were found under data/raw.")

    telemetry = pd.concat(frames, ignore_index=True, sort=False)
    telemetry = telemetry.loc[
        telemetry["device_label"].isin(DEVICE_ORDER)
        & telemetry["run_id"].isin(RUN_ORDER)
    ].copy()

    if telemetry.empty:
        raise TableBuildError("No raw telemetry rows match the expected devices and conditions.")

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


def valid_temperature_mask(frame: pd.DataFrame) -> pd.Series:
    mask = frame["elapsed_seconds"].notna() & frame["battery_temperature_c"].notna()
    if "sample_ok" in frame.columns:
        mask &= frame["sample_ok"].astype(str).str.strip().str.upper().eq("TRUE")
    return mask


def build_device_run_summary(telemetry: pd.DataFrame) -> pd.DataFrame:
    valid = telemetry.loc[valid_temperature_mask(telemetry)].copy()

    summary = (
        valid.groupby(["device_label", "run_id", "source_file"], as_index=False)
        .agg(
            valid_temperature_records=("battery_temperature_c", "size"),
            observed_elapsed_seconds=("elapsed_seconds", "max"),
            min_battery_temperature_c=("battery_temperature_c", "min"),
            mean_battery_temperature_c=("battery_temperature_c", "mean"),
            max_battery_temperature_c=("battery_temperature_c", "max"),
        )
    )

    summary["device_label"] = pd.Categorical(
        summary["device_label"], categories=DEVICE_ORDER, ordered=True
    )
    summary["run_id"] = pd.Categorical(
        summary["run_id"], categories=RUN_ORDER, ordered=True
    )
    summary = summary.sort_values(["run_id", "device_label"]).reset_index(drop=True)

    expected = pd.MultiIndex.from_product(
        [DEVICE_ORDER, RUN_ORDER], names=["device_label", "run_id"]
    )
    observed = pd.MultiIndex.from_frame(summary[["device_label", "run_id"]].astype(str))
    missing = expected.difference(observed)

    if len(missing):
        missing_text = ", ".join(f"{device}/{run}" for device, run in missing)
        raise TableBuildError(f"Missing device/run temperature summaries: {missing_text}")

    if len(summary) != 30:
        raise TableBuildError(f"Expected 30 device/run summaries; found {len(summary)}.")

    if (summary["valid_temperature_records"] <= 10).any():
        offenders = summary.loc[
            summary["valid_temperature_records"] <= 10,
            ["device_label", "run_id", "valid_temperature_records", "source_file"],
        ]
        raise TableBuildError(
            "Implausibly low temperature-record count:\n" + offenders.to_string(index=False)
        )

    return summary


def build_table3(device_run: pd.DataFrame) -> pd.DataFrame:
    table = (
        device_run.groupby("run_id", observed=False, as_index=False)
        .agg(
            median_device_level_max_battery_temperature_c=(
                "max_battery_temperature_c", "median"
            ),
            observed_battery_temperature_min_c=("min_battery_temperature_c", "min"),
            observed_battery_temperature_max_c=("max_battery_temperature_c", "max"),
        )
    )

    table["run_id"] = pd.Categorical(table["run_id"], categories=RUN_ORDER, ordered=True)
    table = table.sort_values("run_id").reset_index(drop=True)
    table["observed_battery_temperature_range_c"] = table.apply(
        lambda row: (
            f"{row['observed_battery_temperature_min_c']:.1f}"
            f" to {row['observed_battery_temperature_max_c']:.1f}"
        ),
        axis=1,
    )

    table["median_device_level_max_battery_temperature_c"] = (
        table["median_device_level_max_battery_temperature_c"].round(1)
    )
    table["observed_battery_temperature_min_c"] = (
        table["observed_battery_temperature_min_c"].round(1)
    )
    table["observed_battery_temperature_max_c"] = (
        table["observed_battery_temperature_max_c"].round(1)
    )

    return table[
        [
            "run_id",
            "median_device_level_max_battery_temperature_c",
            "observed_battery_temperature_range_c",
            "observed_battery_temperature_min_c",
            "observed_battery_temperature_max_c",
        ]
    ]


def validate_table3_against_device_summary(table3: pd.DataFrame, device_run: pd.DataFrame) -> None:
    for _, row in table3.iterrows():
        run = str(row["run_id"])
        maxima = (
            device_run.loc[
                device_run["run_id"].astype(str) == run,
                "max_battery_temperature_c",
            ]
            .astype(float)
            .to_numpy()
        )
        expected_median = round(float(np.median(maxima)), 1)
        actual_median = float(row["median_device_level_max_battery_temperature_c"])
        if actual_median != expected_median:
            raise TableBuildError(
                f"Median validation failed for {run}: expected {expected_median}, got {actual_median}."
            )


def write_markdown_table(table3: pd.DataFrame, output_path: Path) -> None:
    display = table3[
        [
            "run_id",
            "median_device_level_max_battery_temperature_c",
            "observed_battery_temperature_range_c",
        ]
    ].copy()
    display.columns = [
        "Run",
        "Median device-level maximum battery temperature (°C)",
        "Observed battery-temperature range across valid samples (°C)",
    ]

    lines = [
        "# Table 3. Condition-level battery-temperature summaries",
        "",
        "| " + " | ".join(display.columns) + " |",
        "|---|---:|---:|",
    ]
    for _, row in display.iterrows():
        lines.append(
            "| "
            + str(row["Run"])
            + " | "
            + f"{float(row['Median device-level maximum battery temperature (°C)']):.1f}"
            + " | "
            + str(row["Observed battery-temperature range across valid samples (°C)"])
            + " |"
        )

    lines.extend(
        [
            "",
            "**Note.** For each condition, the median maximum is the median of the three "
            "device-level maximum battery temperatures. The observed temperature range is "
            "the minimum to maximum across all valid battery-temperature samples from the "
            "three retained device/run files. Battery-side power is not summarized across "
            "devices because its sign, scale, availability, and interpretation are device- "
            "and driver-dependent.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    PROCESSED_DIRECTORY.mkdir(parents=True, exist_ok=True)
    RESULTS_TABLE_DIRECTORY.mkdir(parents=True, exist_ok=True)

    telemetry = load_raw_telemetry()
    device_run = build_device_run_summary(telemetry)
    table3 = build_table3(device_run)
    validate_table3_against_device_summary(table3, device_run)

    device_run_csv = PROCESSED_DIRECTORY / "TableS10_device_run_temperature_audit.csv"
    table3_csv = PROCESSED_DIRECTORY / "Table3_condition_level_summary.csv"
    table3_markdown = RESULTS_TABLE_DIRECTORY / "Table3_condition_level_temperature_summary.md"

    audit = device_run.copy()
    audit["device_label"] = audit["device_label"].astype(str)
    audit["run_id"] = audit["run_id"].astype(str)
    audit.to_csv(device_run_csv, index=False)
    table3.to_csv(table3_csv, index=False)
    write_markdown_table(table3, table3_markdown)

    print("\nDevice/run temperature audit (source for Table S10 maxima):")
    print(audit.to_string(index=False))
    print("\nCorrected Table 3:")
    print(table3.to_string(index=False))
    print("\nCreated files:")
    print(device_run_csv)
    print(table3_csv)
    print(table3_markdown)


if __name__ == "__main__":
    main()
