# Analysis and Figure Scripts

This directory contains the scripts used to inspect pilot-study telemetry and generate the repository figures. The processed CSV tables in `../data/processed/` and the rendered outputs in `../results/` are retained alongside the scripts for transparent checking.

## Contents

Expected scripts include:

- `run_final_telemetry.ps1` — workflow used to execute or collect the final telemetry runs, where included.
- `make_figure1_all_devices_temperature.py` — generates the all-device battery-temperature trajectory figure.
- `make_figure2_run_level_outcomes.py` — generates the run-level outcomes figure.
- `make_figure3_duty_cycle_phase_effects.py` — generates the duty-cycle active/pause phase-effects figure.
- `make_figure4_data_coverage.py` — generates the telemetry-coverage figure.
- `analyze_pilot_study.py` — optional analysis script, if included.
- `requirements.txt` — Python dependencies for the analysis/plotting scripts.

## Environment setup

Use a dedicated Python environment when possible. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Running scripts

Run scripts from the repository root or from this directory according to the path assumptions in each script. Example from the repository root:

```powershell
python .\scripts\make_figure1_all_devices_temperature.py
python .\scripts\make_figure2_run_level_outcomes.py
python .\scripts\make_figure3_duty_cycle_phase_effects.py
python .\scripts\make_figure4_data_coverage.py
```

Inspect each script before execution for input paths, expected column names, output settings, and any condition filters. Scripts should use the anonymized release files only; do not replace them with unredacted source telemetry.

## Inputs and outputs

- Raw CSV input: `../data/raw/`
- Processed-table input/output: `../data/processed/`
- Rendered tables and figures: `../results/tables/` and `../results/figures/`

## Interpretation note

Battery-side current and power fields depend on device drivers. Analysis should preserve device-level interpretation and avoid treating signed battery-side power as a single pooled cross-device energy measure.
