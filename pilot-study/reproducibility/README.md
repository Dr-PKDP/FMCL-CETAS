# Reproducibility Guide

This directory contains the repository-level instructions and validation workflow for the FMCL-CETAS pilot-study release.

## Scope

The workflow verifies the released anonymized telemetry archive and reproduces the repository's derived pilot-study outputs from those released files. It does not recreate the historical device acquisitions, establish the exact APK/build identity used for each historical run, or convert operator-entered event timestamps into application-instrumented phase boundaries.

## Prerequisites

- Windows PowerShell 5.1 or PowerShell 7.
- Python 3.10 or later.
- Python packages listed in `../scripts/requirements.txt`.

Install the Python dependencies from the repository root:

```powershell
python -m pip install -r .\scripts\requirements.txt
```

## Reproduction workflow

Run the following command from the `pilot-study` directory:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\reproducibility\reproduce_all.ps1
```

The workflow performs the following steps:

1. Confirms expected raw telemetry, scripts, and output directories are present.
2. Verifies the raw archive contains 30 expected device/run files.
3. Checks that restricted identifier fields are absent from released raw-CSV headers.
4. Rebuilds the temperature-only condition summary for Table 3.
5. Rebuilds the device/run temperature audit used to reconcile Supplementary Table S10.
6. Rebuilds Figure 4 telemetry-coverage outputs.
7. Runs the cross-file consistency audit.
8. Writes or refreshes `file_manifest_sha256.csv`.

## Expected outputs

After a successful run, these files should exist and be non-empty:

```text
../data/processed/Table3_condition_level_summary.csv
../data/processed/TableS10_device_run_temperature_audit.csv
../results/tables/Table3_condition_level_temperature_summary.md
../results/figures/Figure4_telemetry_coverage.pdf
../results/figures/Figure4_telemetry_coverage.png
../results/figures/Figure4_telemetry_coverage_values.csv
file_manifest_sha256.csv
```

Key expected checks are:

- 30 released device/run telemetry files.
- 30 `manifest.csv` entries.
- Lenovo C2-H contains 78 valid telemetry records.
- Lenovo C0 contains 90 valid telemetry records after removal of the blank source placeholder row.
- Table 3 median maximum temperatures reproduce from the device/run maximum-temperature audit.
- Figure 4 record counts and elapsed durations reproduce from the raw archive.

## Interpretation boundaries

- Temperature summaries use valid records with numeric elapsed time and battery temperature and, where present, `sample_ok = TRUE`.
- Table 3 reports the median of three device-level maximum battery temperatures and the minimum-to-maximum observed temperature envelope across valid samples.
- Battery-side current and power are not pooled across devices because Android/vendor driver reporting can differ in scale, sign convention, availability, and unit semantics.
- Event CSVs, if released under `../data/events/`, are operator-entered operational records. Their PC wall-clock timestamps are ancillary documentation and are not treated as application-instrumented duty-cycle phase boundaries.

## Provenance limitation

The released `../app/src/main/java/com/example/fmclpilot/MainActivity.kt` implements the local-training workload selector and continuous/duty-cycle policies, including the programmed 60-second active and 30-second pause schedule. The retained historical telemetry archive does not include a per-run APK hash, package version code, Git commit identifier, or cryptographic build identifier. The exact build provenance of each historical run therefore cannot be independently verified from the released records alone.
