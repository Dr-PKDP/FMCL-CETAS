# CETAS: Charger-, Energy-, and Thermal-Aware Scheduling for Federated Learning on Reused Consumer Devices

Simulation code, datasets, and the empirical pilot study supporting the paper of the same title.

A federated round is usually scheduled while a device charges, but a charging device is also warm, and charging losses and local training draw from one thermal budget. This repository reproduces the coupled thermal/wear device model, the CETAS scheduler and seven baseline policies, the main policy comparison, baseline tuning, ablation, sensitivity analysis, real-trace and real-dataset checks, and the released Android telemetry pilot study.

## Requirements

Python 3.10+ and:

```
pip install -r requirements.txt
```

The simulation, trace-analysis, and figure-generation workflows need no GPU, cluster, or specialised hardware and run on a single CPU core. `run_cifar_partitions.py` uses a small convolutional model and benefits from a GPU but will run on CPU. The separate `pilot-study/` package includes Android source and telemetry materials; collecting new pilot telemetry requires a compatible Android device and Android/ADB tooling, while inspecting the released data and reproducing the included tables and figures does not.

## Repository structure

**Core model** (no external data required):

| File | Contents |
| --- | --- |
| `thermal.py` | Lumped-node thermal, throttling-derating, energy, and wear equations |
| `charging.py` | Two-node charging-coupled thermal network |
| `coefficients.py` | Provenance-tagged coefficient library (Section 9.1), every value tiered and sourced |
| `scheduler.py` | Device-class definitions and shared utilities used by `fleet_charging.py` |
| `fleet_charging.py` | The charging-coupled fleet simulator and all eight policies (CETAS plus seven baselines) |
| `simulation.py` | Standard FedProx local-training engine |
| `converge_charging.py` | Couples `simulation.py` to `fleet_charging.py` for the optimisation-progress comparisons (Tables 7–9) |
| `verify.py` | Independent verification suite for the thermal/wear model; run it first |

**Main policy comparison and baseline fidelity:**

| File | Contents |
| --- | --- |
| `reproduce_table4.py` | Main policy comparison (Table 4) and the classical scheduling metrics that accompany it (Table 6); writes `cats_tuned_full.pkl`, which later scripts read |
| `baseline_tuning.py` | Hyperparameter search for the three tunable baselines (Section 8.10) |
| `run_sweeps.py` | Additional coefficient and parameter sweeps referenced in Sections 8.3–8.5 |
| `pols.py`, `oort_v2.py`, `eafl_v2.py` | Code-informed reimplementations of Oort and EAFL, checked against their published source |
| `s17_confirmatory_baselines.py` | Table S17: CETAS against eleven baselines on 30 further seeds, Holm-corrected |
| `s20_availability_check.py`, `fleet_charging_independent_availability.py` | Table S20: robustness to an independent availability random stream |

**Convergence:**

| File | Contents |
| --- | --- |
| `table7_8_convergence.py` | Tables 7 and 8: optimisation progress at a fixed budget, single partition, six seeds |
| `table9_and_s21_confirmatory_seeds.py` | Table 9 and Table S21: 30 paired seeds, each with its own fleet and data partition |
| `noniid_sweep.py` | Section 8.8: convergence at Dirichlet alpha = 0.3, 0.1, and 0.05, single partition, six seeds |
| `table10_ablation.py` | Table 10: one-factor-at-a-time ablation of the CETAS scoring function |
| `churn_experiment.py` | Correlated availability shock robustness check (Section 7.8) |

**Wear model and coefficient sensitivity:**

| File | Contents |
| --- | --- |
| `s18_raw_dpp_form.py` | Table S18: CETAS with the raw drift-plus-penalty form and fixed scaling constants |
| `s19_drain_rate_sweep.py` | Table S19: effect of the wear-queue drain rate W, including constraint feasibility |
| `uncertainty.py`, `uq_charging.py` | Monte Carlo / Sobol sensitivity analysis over the coefficient library |
| `s5_coefficient_sensitivity.py` | Table S5: ordinal robustness of the Section 8 claims across the coefficient library's plausible ranges |

**Real-data validation (Section 8.9):**

| File | Contents |
| --- | --- |
| `realdata/real_data.py` | Federated partitioner for UCI digits and MNIST |
| `realdata/prepare_mnist.py` | One-time conversion of raw MNIST files into the array format `real_data.py` expects |
| `realdata/full_run.py` | Single-partition digits/MNIST comparison |
| `section8_9_digits_mnist_partitions.py` | Multi-partition digits/MNIST comparison (30 and 10 paired seeds respectively) |
| `run_cifar_partitions.py` | CIFAR-10 with a small CNN, 20 paired seeds, each with its own fleet and data partition |
| `analyze_cifar_partitions.py` | Paired analysis of the CIFAR-10 run: geometric-mean ratios, confidence intervals, Wilcoxon tests |
| `realdata/train-images-idx3-ubyte.gz`, `train-labels-idx1-ubyte.gz` | Unmodified MNIST training-set files |

**Real-trace validation (Sections 7.7 and 7.9):**

| Path | Contents |
| --- | --- |
| `tracesim/setup_data.sh` | Downloads and checksum-verifies both real FedScale data files this section needs; run this first |
| `tracesim/trace_summary_stats.py` | Session-length distribution, concurrent-availability sampling, and compute-heterogeneity spread |
| `tracesim/trace_availability.py` | Converts FedScale's per-device session data into a round-by-round availability matrix |
| `tracesim/trace_run.py` | Reruns the main policy comparison with real trace-derived availability |

**Supplementary:**

| File | Contents |
| --- | --- |
| `MEASUREMENT_PROTOCOL.md` | A one-afternoon, no-lab-equipment protocol for directly measuring the model's least-certain coefficients (Section 9.6) |

## Empirical pilot study: Android telemetry

The `pilot-study/` directory contains the empirical companion package for the CETAS pilot study: the controlled Android telemetry workload used to examine thermal trajectories, telemetry coverage, run-level outcomes, and paired contrasts on reused consumer devices (Section 4.4, Table 3).

This package is intentionally separate from the fleet-scale simulator. It is a small, device-level empirical study intended to provide transparent measurement context and a directional check for the paper's charging/thermal assumptions; it is not a claim of population-representative smartphone performance. See `pilot-study/README.md` for its directory map and reproduction entry point.

## Quick start

```
# 1. Verify the thermal/wear model independently of the scheduler.
python verify.py

# 2. Reproduce the main policy comparison (Table 4) and the classical
#    scheduling metrics that accompany it (Table 6). Writes cats_tuned_full.pkl,
#    which later scripts read.
python reproduce_table4.py

# 3. Baseline tuning (Section 8.10) and confirmatory checks.
python baseline_tuning.py
python run_sweeps.py
python s17_confirmatory_baselines.py

# 4. Convergence (Tables 7-9, Section 8.8).
python table7_8_convergence.py
python table9_and_s21_confirmatory_seeds.py 0.3 random,charger_aware,energy_only 0 30
python noniid_sweep.py

# 5. Ablation (Table 10).
python table10_ablation.py

# 6. Sensitivity analysis over the coefficient library (Table S5, Section 9).
python uncertainty.py
python uq_charging.py
python s5_coefficient_sensitivity.py 0 70

# 7. Wear model checks (Tables S18, S19).
python s18_raw_dpp_form.py
python s19_drain_rate_sweep.py

# 8. Robustness checks (Section 7.8, Table S20).
python churn_experiment.py
python s20_availability_check.py
```

Each script prints a results table to stdout in the same shape as the corresponding table in the paper, and saves the raw per-seed results to a `.pkl` file for further inspection.

### Real-dataset validation (Section 8.9)

```
cd realdata
python prepare_mnist.py    # one-time: builds mnist_full.npz from the raw files
python full_run.py

cd ..
python section8_9_digits_mnist_partitions.py digits 17 multi 30
python section8_9_digits_mnist_partitions.py mnist 50 multi 10
python run_cifar_partitions.py
python analyze_cifar_partitions.py
```

### Real-trace validation (Sections 7.7 and 7.9)

This requires two files from FedScale, neither part of this repository (both belong to FedScale, not to this paper, and are too large to bundle sensibly): the client behaviour/availability trace and the client compute/communication capacity trace. Both are downloaded and checksum-verified by one script:

```
bash tracesim/setup_data.sh
```

If you need to place the files manually instead, they belong at `tracesim/data/client_behave_trace` and `tracesim/data/client_device_capacity`, or can be pointed at via the `FMCL_FEDSCALE_TRACE` and `FMCL_FEDSCALE_CAPACITY` environment variables.

Then, from the repository root:

```
cd tracesim
python trace_summary_stats.py   # Section 7.7's checks
python trace_run.py             # Section 7.9's policy rerun
```

## Notes on reproducibility

- All randomness is seeded through NumPy's `Generator` interface.
- Every value in `coefficients.py` carries a provenance tier and a plausible range, not just a point estimate; `uncertainty.py`, `uq_charging.py`, and `s5_coefficient_sensitivity.py` test whether the paper's ordinal claims survive that uncertainty.
- `fleet_charging.py`'s policies accept `V` (energy-vs-wear weight) and `nu` (charger-headroom weight) as arguments. The paper's tuned operating point, used throughout Sections 7–9 unless a script is explicitly sweeping one of these two weights, is `V=5.0, nu=0.5`.

## Citation

If you use this code, please cite the paper. Citation details will be added once the paper is published; in the meantime, please cite the repository directly.

## License

MIT License. See `LICENSE`.
