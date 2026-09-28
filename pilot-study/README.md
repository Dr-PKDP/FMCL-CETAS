# FMCL-CETAS Pilot Study Repository

This repository contains the materials supporting the FMCL-CETAS pilot study: the Android telemetry workload, experimental protocol, anonymized raw telemetry, processed analysis tables, figure-generation scripts, rendered results, and a reproducibility runner.

## Repository contents

- `app/` — Android application source and build files for the pilot telemetry workload.
- `protocol/` — experimental procedure, condition matrix, workload specification, and telemetry schema.
- `data/` — anonymized raw telemetry and processed tabular outputs.
- `scripts/` — analysis and figure-generation scripts, plus the Python dependency list.
- `results/` — rendered tables and figures reported from the pilot study.
- `reproducibility/` — repository-level checks and reproduction workflow.

## Data organization

- `data/raw/` contains anonymized run-level telemetry CSV files, `manifest.csv`, and documentation of the redaction process.
- `data/processed/` contains the processed CSV tables used for telemetry coverage, condition-level summaries, run-level outcomes, paired contrasts, and duty-cycle phase outcomes.

The raw-data export removes the following fields before release: `adb_serial`, `adb_tcp_port`, `timestamp_local`, `build_fingerprint`, `charger_id`, `dataset_id`, and `dataset_partition_id`.

## Quick start

1. Review `protocol/experimental_protocol.md` and `protocol/workload_specification.md` before interpreting the data.
2. Review `data/README.md` and `data/raw/README.md` for the dataset structure, redaction, and interpretation notes.
3. Install the dependencies listed in `scripts/requirements.txt` if you intend to run the Python plotting scripts.
4. Run the PowerShell reproducibility workflow from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\reproducibility\reproduce_all.ps1
```

## Reproducibility scope

The repository preserves the analysis inputs and outputs needed to inspect the reported pilot-study results. Raw telemetry is retained as per-run CSV data. Processed tables and figure files are provided for transparent checking of reported values and visualizations.

Signed battery current and battery-side power are device-driver-dependent measures. They should be interpreted within a device and should not be pooled as a common cross-device energy endpoint.

## License and citation

Add the intended repository license and the final manuscript citation or DOI here when they are available.
