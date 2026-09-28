# Charging and Computation Compete: Simulation Code

Simulation code and datasets supporting:

> "Charging and Computation Compete: Energy- and Thermal-Aware Scheduling
> for Federated Learning on Reused Consumer Devices"

This repository contains the simulation, trace-validation, real-dataset
validation, and empirical pilot-study materials supporting the paper. It
reproduces the coupled thermal/wear device model, the CATS scheduler and
seven baseline policies, the main policy comparison, tuning sweeps, ablation,
sensitivity analysis, real-trace and real-dataset checks, and the released
Android telemetry pilot-study outputs (a real 107,749-device availability trace, a 500,000-entry
compute/communication capacity trace, and two real image datasets in place
of the synthetic learning task).

## Requirements

Python 3.10+ and:

```
pip install -r requirements.txt
```

The simulation, trace-analysis, and figure-generation workflows require no
GPU, cluster, or specialised hardware and run on a single CPU core. The
separate `pilot-study/` package includes Android source and telemetry
materials; collecting new pilot telemetry requires a compatible Android
device and Android/ADB tooling, while inspecting the released data and
reproducing the included tables and figures does not.

## Repository structure

**Core model** (no external data required):

| File | Contents |
|---|---|
| `thermal.py` | Lumped-node thermal, throughput-derating, energy, and wear equations (Eq. 1-13) |
| `charging.py` | Two-node charging-coupled thermal network (Eq. 3-4, 8-9) |
| `coefficients.py` | Provenance-tagged coefficient library (Section 9.1), every value tiered and sourced |
| `scheduler.py` | Device-class definitions and shared utilities used by `fleet_charging.py` |
| `fleet_charging.py` | The charging-coupled fleet simulator and all eight policies (CATS plus seven baselines) |
| `simulation.py` | Standard FedProx local-training engine, included so the repository is self-contained (see header comment for details) |
| `converge_charging.py` | Couples `simulation.py` to `fleet_charging.py` for the model-quality comparisons (Tables 9-11) |
| `verify.py` | Independent verification suite for the thermal/wear model; run it first |
| `COEFFICIENTS_FINDINGS.md` | Write-up of the six findings (F1–F6) `verify.py` and `uncertainty.py` produce, plus their Monte Carlo / Sobol robustness results |
| `table13_upper.py` | Coefficient-uncertainty sweep across all eight policies (Table 13's dominance-robustness claims); N=70, see header docstring for a full account of what reproduces and what doesn't |
| `table11_reproduction_attempt.py` | Documented reproduction attempt for Table 11 (propensity truncation sweep); does **not** reproduce Table 11 — see `TABLE11_REPRODUCTION_NOTES.md` |
| `TABLE11_REPRODUCTION_NOTES.md` | What was tried for Table 11, why it doesn't match, and why the paper's values were left unchanged rather than replaced with an unreliable reconstruction |
| `uncertainty.py`, `uq_charging.py` | Monte Carlo / sensitivity analysis over the coefficient library (Table 13, Section 9) |
| `baseline_tuning.py` | Minimal hyperparameter search for the three tunable baselines (Section 8.10) |
| `churn_experiment.py` | Correlated availability shock robustness check (Section 7.8) |
| `noniid_sweep.py` | Statistical heterogeneity sensitivity sweep (Section 8.8) |
| `reproduce_table4.py` | Generates the main policy comparison and the `cats_tuned_full.pkl` reference file several other scripts read |

**Real-data validation:**

| Path | Contents |
|---|---|
| `realdata/real_data.py` | Federated partitioner for two real image datasets (Section 8.9) |
| `realdata/prepare_mnist.py` | One-time conversion of raw MNIST files into the array format `real_data.py` expects |
| `realdata/full_run.py` | Runs the Table 9 quality comparison on real data in place of the synthetic task |
| `realdata/train-images-idx3-ubyte.gz`, `train-labels-idx1-ubyte.gz` | Unmodified MNIST training-set files (60,000 images) |

**Real-trace validation** (Sections 7.7 and 7.9):

| Path | Contents |
|---|---|
| `tracesim/setup_data.sh` | Downloads and checksum-verifies both real FedScale data files this section needs. Run this first. |
| `tracesim/trace_summary_stats.py` | Reproduces all three Section 7.7 checks: session-length distribution, concurrent-availability sampling, and compute-heterogeneity spread |
| `tracesim/trace_availability.py` | Converts FedScale's real per-device session data into a round-by-round availability matrix |
| `tracesim/trace_run.py` | Reruns the main policy comparison (Section 7.9) with real trace-derived availability in place of the i.i.d. draw |

**Supplementary:**

| File | Contents |
|---|---|
| `MEASUREMENT_PROTOCOL.md` | A one-afternoon, no-lab-equipment protocol for directly measuring the model's four least-certain coefficients (Section 9.6) |

## Empirical pilot study: Android telemetry

The `pilot-study/` directory contains the empirical companion package for the
FMCL-CETAS pilot study. It documents and releases the controlled Android
telemetry workload used to examine thermal trajectories, telemetry coverage,
run-level outcomes, paired contrasts, and duty-cycle active/pause effects on
reused consumer devices.

This package is intentionally separate from the fleet-scale simulator. It is
a small, device-level empirical study intended to provide transparent
measurement context and checks for the paper's charging/thermal assumptions;
it is not a claim of population-representative smartphone performance.

| Path | Contents |
|---|---|
| `pilot-study/README.md` | Pilot-study overview, directory map, scope, and reproduction entry point |
| `pilot-study/app/` | Android application source and Gradle project files for the telemetry workload |
| `pilot-study/protocol/` | Experimental procedure, condition matrix, workload specification, and telemetry schema |
| `pilot-study/data/raw/` | Anonymized per-run telemetry CSV files, release manifest, and raw-data documentation |
| `pilot-study/data/processed/` | Machine-readable Tables 3–7: coverage/completeness, condition summaries, run-level outcomes, paired contrasts, and duty-cycle phases |
| `pilot-study/scripts/` | Telemetry workflow and Python scripts that generate the pilot-study figures |
| `pilot-study/results/tables/` | Presentation-ready Tables 5–7 |
| `pilot-study/results/figures/` | PDF and PNG versions of Figures 1–4 |
| `pilot-study/reproducibility/reproduce_all.ps1` | PowerShell-based repository validation/reproduction workflow |

### Pilot-study data and privacy

The public release contains anonymized run-level telemetry rather than
unredacted device exports. Before release, the raw-data workflow removes
`adb_serial`, `adb_tcp_port`, `timestamp_local`, `build_fingerprint`,
`charger_id`, `dataset_id`, and `dataset_partition_id`. The corresponding
`pilot-study/data/raw/manifest.csv` records released file paths, run
identifiers, record counts, observed duration, and SHA-256 checksums.

Battery-side current and power are device-driver-dependent quantities. They
should therefore be interpreted within device and are not treated as a
single pooled cross-device energy endpoint. See
`pilot-study/data/README.md`, `pilot-study/data/raw/README.md`, and
`pilot-study/protocol/telemetry_schema.md` before reusing the telemetry.

### Pilot-study quick start

From the repository root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\pilot-study\reproducibility\reproduce_all.ps1
```

For a complete description of inputs, data redaction, outputs, and expected
repository layout, start with `pilot-study/README.md`.

## Quick start

```bash
# 1. Verify the thermal/wear model independently of the scheduler.
#    Expect "PASSED: 33  FAILED: 0".
python verify.py

# 2. Reproduce the main policy comparison (Table 4) and the classical
#    scheduling metrics that accompany it (Table 7). This also writes
#    cats_tuned_full.pkl, which step 3 and the baseline tuning sweep read.
python reproduce_table4.py

# 3. Sanity-check the baseline reimplementations against that reference,
#    then run the hyperparameter search (Section 8.10).
python baseline_tuning.py
python run_sweeps.py

# 4. Sensitivity analysis over the full coefficient library (Table 13,
#    Section 9). uncertainty.py covers the thermal/wear coefficients;
#    uq_charging.py covers the charging-specific ones.
python uncertainty.py
python uq_charging.py

# 5. The two robustness checks reported in Section 7 and Section 8.
python churn_experiment.py     # correlated availability shock, Section 7.8
python noniid_sweep.py         # heterogeneity sweep, Section 8.8
```

Each script prints a results table to stdout in the same shape as the
corresponding table in the paper, and saves the raw per-seed results to a
`.pkl` file for further inspection.

### Real-dataset validation (Section 8.9)

```bash
cd realdata
python prepare_mnist.py    # one-time: builds mnist_full.npz from the raw files
python full_run.py
```

### Real-trace validation (Sections 7.7 and 7.9)

This requires **two** files from FedScale, neither part of this
repository (both belong to FedScale, not to this paper, and are too
large to bundle sensibly): the client behaviour/availability trace
(Sections 7.7 and 7.9), and the client compute/communication capacity
trace (Section 7.7's third check only). Both are downloaded and
checksum-verified by one script:

```bash
bash tracesim/setup_data.sh
```

This prints `[OK]` for each file once its size and SHA-256 checksum have
been confirmed against the values recorded when this repository's own
results were last verified against them (2026-08-12), and fails loudly,
rather than silently, if anything about the download doesn't match --
including if FedScale has reorganised its repository since this was
written, in which case the script will say so explicitly rather than
proceed with an unverified file. If you need to place the files manually
instead, they belong at `tracesim/data/client_behave_trace` and
`tracesim/data/client_device_capacity`, or can be pointed at via the
`FMCL_FEDSCALE_TRACE` and `FMCL_FEDSCALE_CAPACITY` environment variables.

Then, from the repository root:

```bash
cd tracesim
python trace_summary_stats.py   # Section 7.7's three checks
python trace_run.py             # Section 7.9's full policy rerun
```

**Expected checksums**, for anyone verifying independently rather than
trusting this script:

| File | Size (bytes) | SHA-256 |
|---|---|---|
| `client_behave_trace` | 25,640,150 | `d0b6f81a01f0ea5f7ec432583f5afe93b1e72424db4c1affa88c484f15901662` |
| `client_device_capacity` | 39,369,071 | `477f61049443987318fc5667cafa059b3b420eb0e03ccb5ceb3262d20e059e53` |

## Notes on reproducibility

- All randomness is seeded through NumPy's `Generator` interface; every
  script here uses the same six seeds (or three, for the slower
  trace-reconstruction runs) reported in the paper.
- Every value in `coefficients.py` carries a provenance tier (T1-T4) and a
  plausible range, not just a point estimate; `uncertainty.py` and
  `uq_charging.py` are what test whether the paper's ordinal claims survive
  that uncertainty (Table 13).
- `fleet_charging.py`'s policies accept `V` (energy-vs-wear weight) and
  `nu` (charger-headroom weight) as arguments. The paper's tuned operating
  point, used throughout Sections 7-9 unless a script is explicitly
  sweeping one of these two weights, is `V=5.0, nu=0.5`. Scripts in this
  repository pass these explicitly rather than relying on any function's
  own defaults, several of which are deliberately left at the
  **pre-tuning** values (`V=1.0`) to preserve the untuned comparison
  reported once in Section 8.2/8.3.

## Citation

If you use this code, please cite the paper. Citation details will be
added once the paper is published; in the meantime, please cite the
repository directly.

## License

MIT License. See `LICENSE`.
