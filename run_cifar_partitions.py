"""
CIFAR-10 + small-CNN convergence check with a NEW DATA PARTITION FOR EVERY SEED.

The earlier run (run_cifar_comparison.py) used one partition (seed=0) for all
fleet seeds, so its ratios cannot separate a policy effect from a partition
effect. Here seed s uses fleet seed s AND partition seed s, and all policies
share both within a seed, so every comparison is paired.

Seed-major order: after each completed seed, every policy has a result for that
seed, so an interrupted run still leaves complete pairs.

Environment variables (all optional):
  CIFAR_PART_SEEDS     number of seeds to run, default 10
  CIFAR_PART_START     first seed, default 0   (use to split seeds across GPUs)
  CIFAR_PART_POLICIES  comma list, default random,energy_only,charger_aware
  CIFAR_PART_OUT       checkpoint file, default cifar_partitions_checkpoint.pkl
"""
import os
import pickle
import sys
import time

import numpy as np
import torch

import cifar_data
from run_cnn import run_cnn

N, K, HOURS = 100, 30, 6.0
ALPHA = 0.3
START = int(os.environ.get("CIFAR_PART_START", 0))
COUNT = int(os.environ.get("CIFAR_PART_SEEDS", 10))
SEEDS = list(range(START, START + COUNT))
POLICIES = os.environ.get("CIFAR_PART_POLICIES",
                          "random,energy_only,charger_aware").split(",")
OUT = os.environ.get("CIFAR_PART_OUT", "cifar_partitions_checkpoint.pkl")


def load():
    if os.path.exists(OUT):
        with open(OUT, "rb") as f:
            return pickle.load(f)
    return {}


def save(res):
    tmp = OUT + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(res, f)
    os.replace(tmp, OUT)          # atomic: no half-written checkpoint


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}  seeds: {SEEDS}  policies: {POLICIES}", flush=True)
    if device.type == "cpu":
        print("WARNING: no GPU detected; this will be very slow.", flush=True)
    res = load()                  # key: (policy, seed) -> result dict
    total = len(SEEDS) * len(POLICIES)
    print(f"resuming with {sum(1 for k in res if k[1] in SEEDS)}/{total} runs done", flush=True)
    for seed in SEEDS:
        if all((p, seed) in res for p in POLICIES):
            continue
        clients, n_classes, shape = cifar_data.make_cifar_federated_data(
            N=N, n_per=50, alpha=ALPHA, seed=seed)      # new partition per seed
        for policy in POLICIES:
            if (policy, seed) in res:
                continue
            t0 = time.time()
            r = run_cnn(policy, clients, n_classes, shape, n=N, hours=HOURS,
                        K=K, seed=seed, V=5.0, nu=0.5, device=device)
            res[(policy, seed)] = r          # keep the full result dict (small)
            save(res)
            print(f"seed {seed:2d} {policy:14s} final ||g||^2 = {r['final_quality']:.4e}"
                  f"  fatigue = {r['cycling_max']:.0f}  dropout = {r['dropout_rate']:.3f}"
                  f"  ({(time.time()-t0)/60:.1f} min)", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
