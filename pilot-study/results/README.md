# Results

This directory contains rendered tables and figures derived from the FMCL-CETAS pilot-study telemetry data. The matching machine-readable tables are in `../data/processed/`, and the scripts used for figure generation are in `../scripts/`.

## Tables

The `tables/` directory is expected to contain presentation-ready versions of the main analytical outputs, including:

- Table 5 — run-level telemetry outcomes.
- Table 6 — paired power contrasts.
- Table 7 — duty-cycle active/pause outcomes.

The corresponding CSV files are maintained in `../data/processed/`. Tables 3 and 4 are also distributed there as CSV files for telemetry completeness and condition-level summaries.

## Figures

The `figures/` directory is expected to contain PDF and PNG versions of:

- Figure 1 — all-device battery-temperature trajectories.
- Figure 2 — run-level outcomes.
- Figure 3 — duty-cycle phase effects.
- Figure 4 — telemetry coverage.

Use PDF files for print-quality inspection and PNG files for convenient preview. The figure filenames should match those used by the analysis scripts and manuscript references.

## Reproduction

To recreate or validate result files:

1. Review the experimental context in `../protocol/`.
2. Confirm raw-data completeness and redaction through `../data/raw/manifest.csv` and `../data/raw/README.md`.
3. Install packages listed in `../scripts/requirements.txt`.
4. Run the appropriate scripts in `../scripts/` or the repository-level runner in `../reproducibility/reproduce_all.ps1`.

## Interpretation

Results must be interpreted with the limitations specified in the protocol and data documentation. In particular, signed battery current and battery-side power are device-driver-dependent; comparisons should be made within device unless the analysis explicitly justifies a harmonized cross-device measure.
