# Expected Outputs and Verification Targets

A successful pilot-study reproducibility run validates the released raw archive and regenerates the following derived outputs.

## Required generated outputs

```text
../data/processed/Table3_condition_level_summary.csv
../data/processed/TableS10_device_run_temperature_audit.csv
../results/tables/Table3_condition_level_temperature_summary.md
../results/figures/Figure4_telemetry_coverage.pdf
../results/figures/Figure4_telemetry_coverage.png
../results/figures/Figure4_telemetry_coverage_values.csv
file_manifest_sha256.csv
```

## Archive checks

| Check | Expected result |
|---|---|
| Released telemetry files | 30 device/run CSV files |
| Expected device/run design | 3 devices × 10 conditions |
| Raw-data manifest entries | 30 |
| Restricted identifier columns in released raw headers | None |
| Lenovo C0 valid records | 90 |
| Lenovo C0 observed elapsed time | 890 s |
| Lenovo C2-H valid records | 78 |
| Lenovo C2-H observed elapsed time | Approximately 892 s |
| Lenovo C3-L observed elapsed time | Approximately 898 s |
| Lenovo C4-L observed elapsed time | Approximately 899 s |

## Table 3 checks

Table 3 is temperature-only. It must report:

- the median of the three device-level maximum battery temperatures for each condition; and
- the observed minimum-to-maximum battery-temperature envelope across valid samples from the three retained device/run files.

The Table 3 median values must reproduce from `TableS10_device_run_temperature_audit.csv`.

## Figure 4 checks

Figure 4 Panel A must match the per-device/run observed elapsed-time values in the raw archive. Panel B must match valid telemetry-record counts. It must show 30 device/run points and identify Lenovo C2-H as the 78-record run.

## Expected terminal status

The consistency audit should finish with:

```text
STATUS: PASS — checked raw archive, manifest, Table 3, available S10 audit, and Figure 4 values.
```

A `FAIL` line indicates a numerical or archive inconsistency that should be resolved before the repository is released.
