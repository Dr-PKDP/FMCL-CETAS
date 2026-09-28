#!/usr/bin/env python3
"""Read-only consistency audit for the FMCL-CETAS pilot-study repository.

Derives canonical coverage and temperature values from anonymized sample-level
raw telemetry and compares them with manifest.csv, Table 3, the S10 temperature
audit, and Figure 4 coverage values when those derivative files are present.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RAW_DIRECTORY = REPOSITORY_ROOT / "data" / "raw"
PROCESSED_DIRECTORY = REPOSITORY_ROOT / "data" / "processed"
FIGURE_DIRECTORY = REPOSITORY_ROOT / "results" / "figures"

RUN_ORDER = ["C0", "C1", "C2-L", "C2-H", "C3-L", "C3-H", "C4-L", "C4-H", "C5-L", "C5-H"]
DEVICE_ORDER = ["oppo_a78_5g", "lenovo_tablet", "motorola_device"]
RESTRICTED_COLUMNS = {
    "adb_serial",
    "adb_tcp_port",
    "timestamp_local",
    "build_fingerprint",
    "charger_id",
    "dataset_id",
    "dataset_partition_id",
}


class AuditError(RuntimeError):
    pass


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


def find_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {normalize_column_name(column): column for column in frame.columns}
    for candidate in candidates:
        found = normalized.get(normalize_column_name(candidate))
        if found is not None:
            return found
    return None


def valid_mask(frame: pd.DataFrame, require_temperature: bool = False) -> pd.Series:
    mask = frame["elapsed_seconds"].notna()
    if require_temperature:
        mask &= frame["battery_temperature_c"].notna()
    if "sample_ok" in frame.columns:
        mask &= frame["sample_ok"].astype(str).str.strip().str.upper().eq("TRUE")
    return mask


def load_raw_telemetry() -> tuple[pd.DataFrame, list[str]]:
    if not RAW_DIRECTORY.is_dir():
        raise AuditError(f"Raw-data directory missing: {RAW_DIRECTORY}")

    messages: list[str] = []
    frames: list[pd.DataFrame] = []
    files = [
        path
        for path in sorted(RAW_DIRECTORY.rglob("*.csv"))
        if path.name.lower() != "manifest.csv" and "telemetry" in path.name.lower()
    ]

    if not files:
        raise AuditError("No *_telemetry.csv files found below data/raw.")

    for path in files:
        try:
            frame = pd.read_csv(path, low_memory=False)
        except Exception as error:
            messages.append(f"FAIL unreadable raw CSV: {path.relative_to(REPOSITORY_ROOT)} ({error})")
            continue

        retained_restricted = sorted(set(frame.columns).intersection(RESTRICTED_COLUMNS))
        if retained_restricted:
            messages.append(
                f"FAIL redaction: {path.relative_to(REPOSITORY_ROOT)} retains "
                + ", ".join(retained_restricted)
            )

        frame = rename_known_columns(frame)
        needed = {"device_label", "run_id", "elapsed_seconds", "battery_temperature_c"}
        missing = sorted(needed.difference(frame.columns))
        if missing:
            messages.append(
                f"FAIL raw schema: {path.relative_to(REPOSITORY_ROOT)} lacks "
                + ", ".join(missing)
            )
            continue

        frame = frame.copy()
        frame["device_label"] = frame["device_label"].map(canonical_device)
        frame["run_id"] = frame["run_id"].map(canonical_run)
        frame["elapsed_seconds"] = pd.to_numeric(frame["elapsed_seconds"], errors="coerce")
        frame["battery_temperature_c"] = pd.to_numeric(
            frame["battery_temperature_c"], errors="coerce"
        )
        frame["source_file"] = str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/")
        frames.append(frame)

    if not frames:
        raise AuditError("No usable sample-level raw telemetry could be loaded.")

    telemetry = pd.concat(frames, ignore_index=True, sort=False)
    telemetry = telemetry.loc[
        telemetry["device_label"].isin(DEVICE_ORDER)
        & telemetry["run_id"].isin(RUN_ORDER)
    ].copy()

    if telemetry.empty:
        raise AuditError("No rows match the expected device labels and run IDs.")

    candidates = (
        telemetry.groupby(["source_file", "device_label", "run_id"], as_index=False)
        .agg(source_rows=("elapsed_seconds", "size"), source_max_elapsed=("elapsed_seconds", "max"))
        .sort_values(
            ["device_label", "run_id", "source_max_elapsed", "source_rows", "source_file"],
            ascending=[True, True, False, False, True],
        )
    )
    selected = (
        candidates.groupby(["device_label", "run_id"], as_index=False)
        .head(1)[["source_file", "device_label", "run_id"]]
    )

    telemetry = telemetry.merge(
        selected,
        on=["source_file", "device_label", "run_id"],
        how="inner",
    )
    return telemetry, messages


def canonical_summaries(telemetry: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    valid_coverage = telemetry.loc[valid_mask(telemetry, False)].copy()
    valid_temperature = telemetry.loc[valid_mask(telemetry, True)].copy()

    coverage = (
        valid_coverage.groupby(["device_label", "run_id", "source_file"], as_index=False)
        .agg(
            valid_telemetry_records=("elapsed_seconds", "size"),
            observed_elapsed_seconds=("elapsed_seconds", "max"),
        )
    )
    device_run = (
        valid_temperature.groupby(["device_label", "run_id", "source_file"], as_index=False)
        .agg(
            valid_temperature_records=("battery_temperature_c", "size"),
            min_battery_temperature_c=("battery_temperature_c", "min"),
            mean_battery_temperature_c=("battery_temperature_c", "mean"),
            max_battery_temperature_c=("battery_temperature_c", "max"),
        )
        .merge(coverage, on=["device_label", "run_id", "source_file"], how="outer", validate="one_to_one")
    )

    device_run["device_label"] = pd.Categorical(
        device_run["device_label"], categories=DEVICE_ORDER, ordered=True
    )
    device_run["run_id"] = pd.Categorical(
        device_run["run_id"], categories=RUN_ORDER, ordered=True
    )
    device_run = device_run.sort_values(["run_id", "device_label"]).reset_index(drop=True)

    condition = (
        device_run.groupby("run_id", observed=False, as_index=False)
        .agg(
            median_device_level_max_battery_temperature_c=("max_battery_temperature_c", "median"),
            observed_battery_temperature_min_c=("min_battery_temperature_c", "min"),
            observed_battery_temperature_max_c=("max_battery_temperature_c", "max"),
        )
    )
    condition["run_id"] = pd.Categorical(condition["run_id"], categories=RUN_ORDER, ordered=True)
    condition = condition.sort_values("run_id").reset_index(drop=True)
    return device_run, condition


def compare_numeric(
    label: str,
    expected: pd.DataFrame,
    actual: pd.DataFrame,
    keys: list[str],
    expected_column: str,
    actual_column: str,
    tolerance: float,
) -> list[str]:
    merged = expected[keys + [expected_column]].merge(
        actual[keys + [actual_column]], on=keys, how="outer", indicator=True
    )
    messages: list[str] = []

    for _, row in merged.loc[merged["_merge"] != "both"].iterrows():
        values = ", ".join(f"{key}={row[key]}" for key in keys)
        messages.append(f"FAIL {label}: unmatched row ({values}); status={row['_merge']}")

    both = merged.loc[merged["_merge"] == "both"].copy()
    both[expected_column] = pd.to_numeric(both[expected_column], errors="coerce")
    both[actual_column] = pd.to_numeric(both[actual_column], errors="coerce")
    mismatch = both.loc[
        both[expected_column].isna()
        | both[actual_column].isna()
        | ((both[expected_column] - both[actual_column]).abs() > tolerance)
    ]

    for _, row in mismatch.iterrows():
        values = ", ".join(f"{key}={row[key]}" for key in keys)
        messages.append(
            f"FAIL {label}: {values}; raw={row[expected_column]}, table={row[actual_column]}"
        )
    return messages


def audit_manifest(device_run: pd.DataFrame) -> list[str]:
    path = RAW_DIRECTORY / "manifest.csv"
    if not path.is_file():
        return ["FAIL manifest: data/raw/manifest.csv is missing"]

    table = rename_known_columns(pd.read_csv(path))
    if len(table) != 30:
        return [f"FAIL manifest: expected 30 rows; found {len(table)}"]

    device_column = find_column(table, ["device_label"])
    run_column = find_column(table, ["run_id"])
    record_column = find_column(table, ["valid_telemetry_records", "records", "total_records"])
    elapsed_column = find_column(table, ["final_elapsed_seconds", "observed_elapsed_seconds"])
    hash_column = find_column(table, ["published_sha256"])

    if not device_column or not run_column:
        return ["FAIL manifest: missing device_label or run_id column"]

    table = table.copy()
    table["device_label"] = table[device_column].map(canonical_device)
    table["run_id"] = table[run_column].map(canonical_run)
    messages: list[str] = []

    if table.duplicated(["device_label", "run_id"]).any():
        messages.append("FAIL manifest: duplicate device/run rows")

    if record_column:
        table["manifest_records"] = pd.to_numeric(table[record_column], errors="coerce")
        messages.extend(compare_numeric(
            "manifest valid-record count", device_run, table,
            ["device_label", "run_id"], "valid_telemetry_records", "manifest_records", 0.0
        ))
    else:
        messages.append("WARN manifest: no valid-record count column")

    if elapsed_column:
        table["manifest_elapsed"] = pd.to_numeric(table[elapsed_column], errors="coerce")
        messages.extend(compare_numeric(
            "manifest elapsed duration", device_run, table,
            ["device_label", "run_id"], "observed_elapsed_seconds", "manifest_elapsed", 0.11
        ))
    else:
        messages.append("WARN manifest: no elapsed-duration column")

    if hash_column:
        for _, row in table.iterrows():
            match = device_run.loc[
                (device_run["device_label"].astype(str) == row["device_label"])
                & (device_run["run_id"].astype(str) == row["run_id"])
            ]
            if len(match) != 1:
                continue
            source_path = REPOSITORY_ROOT / str(match["source_file"].iloc[0])
            expected_hash = str(row[hash_column]).strip()
            if expected_hash and source_path.is_file():
                import hashlib
                actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
                if actual_hash != expected_hash.upper():
                    messages.append(
                        f"FAIL manifest SHA-256: {row['device_label']}/{row['run_id']}"
                    )
    return messages


def audit_table3(condition: pd.DataFrame) -> list[str]:
    path = PROCESSED_DIRECTORY / "Table3_condition_level_summary.csv"
    if not path.is_file():
        return ["FAIL Table 3: data/processed/Table3_condition_level_summary.csv is missing"]

    table = rename_known_columns(pd.read_csv(path))
    run_column = find_column(table, ["run_id"])
    median_column = find_column(table, [
        "median_device_level_max_battery_temperature_c",
        "median_max_battery_temperature_c",
    ])
    min_column = find_column(table, ["observed_battery_temperature_min_c"])
    max_column = find_column(table, ["observed_battery_temperature_max_c"])

    if not run_column or not median_column:
        return ["FAIL Table 3: missing run_id or median maximum-temperature column"]

    table = table.copy()
    table["run_id"] = table[run_column].map(canonical_run)
    table["table3_median"] = pd.to_numeric(table[median_column], errors="coerce")
    messages = compare_numeric(
        "Table 3 median maximum temperature", condition, table,
        ["run_id"], "median_device_level_max_battery_temperature_c", "table3_median", 0.051
    )

    if min_column and max_column:
        table["table3_min"] = pd.to_numeric(table[min_column], errors="coerce")
        table["table3_max"] = pd.to_numeric(table[max_column], errors="coerce")
        messages.extend(compare_numeric(
            "Table 3 observed minimum temperature", condition, table,
            ["run_id"], "observed_battery_temperature_min_c", "table3_min", 0.051
        ))
        messages.extend(compare_numeric(
            "Table 3 observed maximum temperature", condition, table,
            ["run_id"], "observed_battery_temperature_max_c", "table3_max", 0.051
        ))
    else:
        messages.append("WARN Table 3: numeric observed minimum/maximum columns are absent")
    return messages


def audit_s10(device_run: pd.DataFrame) -> list[str]:
    candidates = [
        PROCESSED_DIRECTORY / "TableS10_device_run_temperature_audit.csv",
        PROCESSED_DIRECTORY / "TableS10_device_run_outcomes.csv",
        PROCESSED_DIRECTORY / "TableS10_device_level_outcomes.csv",
    ]
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        return ["WARN Table S10: no machine-readable device/run audit CSV found"]

    table = rename_known_columns(pd.read_csv(path))
    device_column = find_column(table, ["device_label"])
    run_column = find_column(table, ["run_id"])
    max_column = find_column(table, ["max_battery_temperature_c", "maximum_battery_temperature_c"])
    mean_column = find_column(table, ["mean_battery_temperature_c"])

    if not device_column or not run_column or not max_column:
        return [f"WARN Table S10: {path.name} lacks device/run/maximum-temperature columns"]

    table = table.copy()
    table["device_label"] = table[device_column].map(canonical_device)
    table["run_id"] = table[run_column].map(canonical_run)
    table["s10_max"] = pd.to_numeric(table[max_column], errors="coerce")
    messages = compare_numeric(
        "Table S10 maximum temperature", device_run, table,
        ["device_label", "run_id"], "max_battery_temperature_c", "s10_max", 0.051
    )

    if mean_column:
        table["s10_mean"] = pd.to_numeric(table[mean_column], errors="coerce")
        messages.extend(compare_numeric(
            "Table S10 mean temperature", device_run, table,
            ["device_label", "run_id"], "mean_battery_temperature_c", "s10_mean", 0.051
        ))
    return messages


def audit_figure4(device_run: pd.DataFrame) -> list[str]:
    path = FIGURE_DIRECTORY / "Figure4_telemetry_coverage_values.csv"
    if not path.is_file():
        return ["WARN Figure 4: values CSV missing; rerun make_figure4_data_coverage.py"]

    table = rename_known_columns(pd.read_csv(path))
    device_column = find_column(table, ["device_label"])
    run_column = find_column(table, ["run_id"])
    record_column = find_column(table, ["valid_telemetry_records", "telemetry_samples"])
    elapsed_column = find_column(table, ["observed_elapsed_seconds"])

    if not device_column or not run_column or not record_column or not elapsed_column:
        return ["FAIL Figure 4 values: missing device/run/record/elapsed column"]

    table = table.copy()
    table["device_label"] = table[device_column].map(canonical_device)
    table["run_id"] = table[run_column].map(canonical_run)
    table["figure4_records"] = pd.to_numeric(table[record_column], errors="coerce")
    table["figure4_elapsed"] = pd.to_numeric(table[elapsed_column], errors="coerce")

    messages = compare_numeric(
        "Figure 4 valid-record count", device_run, table,
        ["device_label", "run_id"], "valid_telemetry_records", "figure4_records", 0.0
    )
    messages.extend(compare_numeric(
        "Figure 4 elapsed duration", device_run, table,
        ["device_label", "run_id"], "observed_elapsed_seconds", "figure4_elapsed", 0.11
    ))
    return messages


def main() -> None:
    try:
        telemetry, messages = load_raw_telemetry()
        device_run, condition = canonical_summaries(telemetry)
    except AuditError as error:
        print(f"FAIL audit cannot continue: {error}")
        sys.exit(1)

    expected = pd.MultiIndex.from_product(
        [DEVICE_ORDER, RUN_ORDER], names=["device_label", "run_id"]
    )
    observed = pd.MultiIndex.from_frame(device_run[["device_label", "run_id"]].astype(str))
    missing = expected.difference(observed)
    if len(missing):
        messages.append(
            "FAIL raw archive missing expected pairs: "
            + ", ".join(f"{device}/{run}" for device, run in missing)
        )
    if len(device_run) != 30:
        messages.append(f"FAIL raw archive: expected 30 device/run files; found {len(device_run)}")

    c0 = device_run.loc[
        (device_run["device_label"].astype(str) == "lenovo_tablet")
        & (device_run["run_id"].astype(str) == "C0")
    ]
    c2h = device_run.loc[
        (device_run["device_label"].astype(str) == "lenovo_tablet")
        & (device_run["run_id"].astype(str) == "C2-H")
    ]
    if len(c0) != 1 or int(c0["valid_telemetry_records"].iloc[0]) != 90:
        messages.append("FAIL raw archive: Lenovo C0 must contain exactly 90 valid telemetry records")
    if len(c2h) != 1 or int(c2h["valid_telemetry_records"].iloc[0]) != 78:
        messages.append("FAIL raw archive: Lenovo C2-H must contain exactly 78 valid telemetry records")

    messages.extend(audit_manifest(device_run))
    messages.extend(audit_table3(condition))
    messages.extend(audit_s10(device_run))
    messages.extend(audit_figure4(device_run))

    print("FMCL-CETAS PILOT-STUDY CONSISTENCY AUDIT")
    print(f"Repository: {REPOSITORY_ROOT}")
    print()
    print("Canonical device/run values derived from anonymized raw telemetry:")
    display = device_run.copy()
    display["device_label"] = display["device_label"].astype(str)
    display["run_id"] = display["run_id"].astype(str)
    print(display[[
        "device_label",
        "run_id",
        "valid_telemetry_records",
        "observed_elapsed_seconds",
        "min_battery_temperature_c",
        "mean_battery_temperature_c",
        "max_battery_temperature_c",
    ]].to_string(index=False))
    print()

    failures = [message for message in messages if message.startswith("FAIL")]
    warnings = [message for message in messages if message.startswith("WARN")]

    if failures:
        print("FAILURES")
        for message in failures:
            print(message)
        print()
    if warnings:
        print("WARNINGS")
        for message in warnings:
            print(message)
        print()

    if failures:
        print(f"STATUS: FAIL — {len(failures)} consistency issue(s) require correction.")
        sys.exit(1)

    print("STATUS: PASS — checked raw archive, manifest, Table 3, available S10 audit, and Figure 4 values.")


if __name__ == "__main__":
    main()
