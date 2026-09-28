# Data Documentation

This directory contains the anonymized raw telemetry released for the FMCL-CETAS pilot study and the processed tabular outputs used to report the study results.

## Directory structure

```text
data/
├── raw/        Anonymized per-run telemetry CSV files and manifest
├── processed/  Processed tables used for reported analyses
└── metadata/   Optional redacted device metadata and data dictionary, if supplied
```

## Raw data

The `raw/` directory contains one anonymized telemetry CSV per released device/run pair. Each file is accompanied by `raw/manifest.csv`, which records the published relative path, device label, run identifier, record count, observed final elapsed time, source filename, SHA-256 checksums, export time, and the redacted columns.

Read `raw/README.md` before using raw data. It describes the redaction process and the interpretation limitations of device-specific battery-side current and power.

### Redacted fields

The following fields are removed before public release:

- `adb_serial`
- `adb_tcp_port`
- `timestamp_local`
- `build_fingerprint`
- `charger_id`
- `dataset_id`
- `dataset_partition_id`

## Processed data

The `processed/` directory contains the study tables in CSV form:

- `Table3_telemetry_file_completeness.csv` — retained telemetry files and coverage/completeness information.
- `Table4_condition_level_summary.csv` — condition-level thermal and telemetry summary.
- `Table5_run_level_outcomes.csv` — run-level outcome data.
- `Table6_paired_contrasts.csv` — paired contrasts for the reported comparisons.
- `Table7_duty_cycle_phases.csv` — active/pause duty-cycle phase outcomes.

Use the tables and associated scripts as the authoritative source for reported summaries. Do not infer that every device provides equivalent battery-driver semantics merely because telemetry fields share a name.

## Data interpretation

- `device_label` and `run_id` identify the released experimental device/run pairing.
- `elapsed_seconds` is the elapsed time within a run and supports within-run trajectories and coverage checks.
- Battery current and battery-side power are driver-dependent and should be interpreted within device.
- Cross-device comparisons should focus on consistently interpretable measures and should preserve the study's stated analytical limitations.
- `sample_ok` and related error fields should be considered during quality-control checks.

## Integrity checks

Use `raw/manifest.csv` to compare output filenames, record counts, and SHA-256 checksums. The repository-level reproduction script may additionally verify the presence of required raw and processed files.
