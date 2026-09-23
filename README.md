# FMCL Paper 3 — Reproduction Code

This repository contains the code used to produce every result reported in
the paper: the lifecycle carbon accounting engine, the federated-learning
training harness, and the analysis scripts that verify each coefficient the
accounting model depends on against its primary source.

## Requirements

```
pip install -r requirements.txt
```

Python 3.10+ is assumed. `h5py` and `SALib` are only needed for FEMNIST
loading and the sensitivity analysis respectively.

## Reproducing the main results (Tables IV, V, VI)

Each domain has its own entry point. All seven confirmed configurations:

```bash
# PTB-XL
python run_ptbxl_study.py --data_dir <path> --rounds 300 --K 50 --lr 0.01 \
  --epochs 2 --mu 0.01 --policy energy_aware --n_seeds 3 --study A

# FEMNIST, compact model
python run_femnist_study.py --data_dir <path> --model compact --rounds 300 \
  --K 50 --lr 0.01 --epochs 2 --mu 0.01 --policy energy_aware --n_seeds 3 --study A

# FEMNIST, ResNet
python run_femnist_study.py --data_dir <path> --model resnet --rounds 600 \
  --K 50 --lr 0.001 --epochs 2 --mu 0.01 --policy energy_aware --n_seeds 3 --study A

# MIT-BIH, TinyCNN
python run_mitbih_study.py --data_dir <path> --model tiny --rounds 100 \
  --K 6 --lr 0.001 --epochs 2 --mu 0.01 --policy energy_aware --n_seeds 14 --study A

# MIT-BIH, ResNet
python run_mitbih_study.py --data_dir <path> --model resnet --rounds 100 \
  --K 6 --lr 0.001 --epochs 2 --mu 0.01 --policy energy_aware --n_seeds 8 --study A

# Icentia11k, TinyCNN
python run_icentia11k_study.py --data_dir <path> --model tiny --rounds 100 \
  --K 30 --bs 256 --lr 0.001 --epochs 2 --mu 0.01 --policy energy_aware --n_seeds 5 --study A

# Icentia11k, ResNet
python run_icentia11k_study.py --data_dir <path> --model resnet --rounds 100 \
  --K 30 --bs 256 --lr 0.01 --epochs 2 --mu 0.01 --policy energy_aware --n_seeds 8 --study A
```

Each run saves per-seed results (accuracy, measured FLOPs, measured
transmitted bytes, and the resulting lifecycle carbon by architecture) to a
JSON file.

## Reproducing the matched-target comparison (§IV-F, §V-C)

Table 5/6 price every configuration at a fixed round budget. A separate
script instead runs the compact and large model on MIT-BIH and Icentia11k
until both reach the same balanced-accuracy target, so the energy cost of
reaching a given quality level can be compared directly rather than
inferred from accuracy after a fixed budget.

```bash
# MIT-BIH
python run_matched_target_study.py --data_dir <path> --domain mitbih \
  --target 0.25 --max_rounds 400 --n_seeds 5

# Icentia11k
python run_matched_target_study.py --data_dir <path> --domain icentia11k \
  --target 0.35 --max_rounds 400 --n_seeds 5 --batch_size 256
```

Each command runs the compact model (TinyCNN) and the large model
(ResNet1D_PTB) sequentially and saves one JSON file per seed to
`results_matched_target/`. Use `--model tiny` and `--model resnet` in
separate processes, each with its own `CUDA_VISIBLE_DEVICES`, to run them
in parallel on separate GPUs instead.

Run with `--probe_only` first to see what balanced accuracy each model
reaches within `--max_rounds`, with no early stopping, before trusting a
"did not reach target" result; see the script's module docstring for the
full rationale, including why balanced accuracy rather than raw accuracy
is the stopping metric on these two majority-class-dominated domains.

## Dataset availability

All datasets are publicly available. None require contacting the authors.

| Dataset | Source | Notes |
|---|---|---|
| PTB-XL | https://physionet.org/content/ptb-xl/1.0.3/ (ODC-BY 1.0) | 12-lead clinical ECG |
| MIT-BIH | https://physionet.org/content/mitdb/1.0.0/ | Single/dual-lead ambulatory ECG |
| Icentia11k | https://physionet.org/content/icentia11k-continuous-ecg/1.0/ (CC BY-NC-SA 4.0, DOI 10.13026/kk0v-r952) | Continuous wearable ECG |
| FEMNIST | https://www.tensorflow.org/federated/api_docs/python/tff/simulation/datasets/emnist | TensorFlow Federated's hosted distribution, re-processing the LEAF writer partition (https://github.com/TalwalkarLab/leaf) |
| Device availability trace | https://github.com/PKU-Chengxu/FLASH | Used for the participation-correlation analysis (`analyze_rho.py`, `flash_parser.py`) |
| Grid carbon intensity | https://api.carbonintensity.org.uk | National Grid ESO Carbon Intensity API, used by `analyze_grid.py` |

`download_icentia11k.py` fetches the Icentia11k subset directly from
PhysioNet. PTB-XL, MIT-BIH, and FEMNIST are standard downloads from the
sources above; point `--data_dir` at wherever they are extracted.

`analyze_grid.py` expects a locally downloaded grid-intensity file
(`testdata/grid_uk_jan2025.json`) fetched separately from the API above, and
`flash_parser.py`'s trace parsing expects the corresponding FLASH device-state
data — neither raw data file is redistributed here.

## Repository structure

| File | Role |
|---|---|
| `engine.py` | Lifecycle carbon accounting engine (FMCL / dedicated-edge / cloud). |
| `fl_harness.py` | Federated-learning mechanics: client state, local training, FedProx, selection policies, differential privacy. |
| `study_runner.py` | Orchestrates one domain's training run: calls `fl_harness` for training, `engine` for lifecycle costing. |
| `data_ptbxl.py`, `data_mitbih.py`, `data_icentia11k.py`, `data_femnist.py` | Dataset loaders and model architectures. |
| `run_ptbxl_study.py`, `run_mitbih_study.py`, `run_icentia11k_study.py`, `run_femnist_study.py` | CLI entry points, one per domain. |
| `run_matched_target_study.py` | Matched-target (balanced-accuracy) comparison on MIT-BIH and Icentia11k: energy cost of reaching a fixed quality bar, rather than a fixed round budget. |
| `download_icentia11k.py` | Fetches the Icentia11k subset from PhysioNet. |
| `wear.py` | Device wear sub-model: derives the marginal embodied-carbon term from measured battery cycle life and campaign energy. |
| `uncertainty.py` | Monte Carlo and Sobol sensitivity analysis over the full accounting model (Sobol sampling is seeded, so reported indices reproduce exactly across runs). |
| `flash_parser.py`, `analyze_rho.py` | Device-availability trace parsing and pairwise-correlation estimation. |
| `analyse_www24.py`, `analyse_qiu.py`, `analyse_comms.py`, `analyse_lca.py`, `analyse_server_lca.py`, `fit_energy_model.py`, `measurement_design.py`, `analyze_grid.py` | Primary-source verification of every coefficient the accounting engine depends on (device energy, communication energy, embodied carbon, grid intensity), each traced to a cited, published source. |

## Coefficient provenance

Every numerical coefficient the lifecycle accounting model depends on is
calibrated from a primary source rather than a secondary citation:

- Device energy coefficients: Yuan et al. (WWW'24) and Qiu et al. (JMLR
  2023), reconciled in `analyse_www24.py`, `analyse_qiu.py`, and
  `fit_energy_model.py`.
- Communication energy: measured radio parameters, reconciled in
  `analyse_comms.py`.
- Device embodied carbon: Fraunhofer IZM's Fairphone 5 life-cycle
  assessment, in `analyse_lca.py`.
- Server embodied carbon and idle power: a Dell R740 life-cycle assessment,
  in `analyse_server_lca.py`.
- Grid carbon intensity: the UK National Grid ESO Carbon Intensity API, in
  `analyze_grid.py`.

Each script prints its derivation with the source figures it starts from, so
the calibration can be checked independently rather than taken on trust.
