"""
Table S5, rows that compare policies: fraction of the 70 coefficient draws in
which each stated ordering holds, computed from mc70.pkl (written by
wear_sensitivity/s5_coefficient_sensitivity.py), plus the ratio of the median
mean charging delay of each baseline to that of tuned CETAS across draws.

Usage: python analysis/s5_baseline_rows.py [mc70.pkl]
"""
import pickle
import sys

import numpy as np

D = pickle.load(open(sys.argv[1] if len(sys.argv) > 1 else "mc70.pkl", "rb"))
draws = [d for d in D.values() if d is not None]
print(f"{len(draws)} valid draws of {len(D)}\n")


def col(policy, key):
    return np.array([d[policy][key] for d in draws], float)


def pct(mask):
    return f"{100 * np.mean(mask):.1f}%"


baselines = ["random", "static", "energy", "oort", "eafl", "wilfq", "fedcs"]
A = "aware"
delay, fat, work, en = "chg_penalty_mean", "cycling_max", "work_s", "energy_J"

print("Charger-aware scheduling versus random, linear score, and charger-blind CETAS")
print("  linear score suspends more than random          ", pct(col("static", "suspended_s") > col("random", "suspended_s")))
print("  charger signal lowers high-rate-charger share   ", pct(col(A, "fast_share") < col("blind", "fast_share")))
print("  charger-aware wear below random                 ", pct(col(A, fat) < col("random", fat)))
print("  charger signal lowers delay vs charger-blind    ", pct(col(A, delay) < col("blind", delay)))
print("  charger signal costs under 5% of compute        ", pct(col(A, work) > 0.95 * col("blind", work)))

print("\nTuned CETAS against all seven other policies, jointly")
print("  delay strictly below every policy               ", pct(np.all([col(A, delay) < col(b, delay) for b in baselines], axis=0)))
print("  fatigue strictly below every policy             ", pct(np.all([col(A, fat) < col(b, fat) for b in baselines], axis=0)))
print("  compute at or above every policy                ", pct(np.all([col(A, work) >= col(b, work) for b in baselines], axis=0)))

print("\nTuned CETAS energy at or below each baseline")
for b in baselines:
    print(f"  {b:8}", pct(col(A, en) <= col(b, en)))

print("\nOrderings among baselines")
print("  Oort delay above random                         ", pct(col("oort", delay) > col("random", delay)))
print("  WILF-Q-analog delay above random                ", pct(col("wilfq", delay) > col("random", delay)))
print("  FedCS-Greedy fatigue above Oort                 ", pct(col("fedcs", fat) > col("oort", fat)))
print("  FedCS-Greedy delay above random                 ", pct(col("fedcs", delay) > col("random", delay)))
print("  FedCS-Greedy delay below WILF-Q-analog          ", pct(col("fedcs", delay) < col("wilfq", delay)))

print("\nRatio of the median mean charging delay of each baseline to that of CETAS")
for b in baselines:
    print(f"  {b:8} {np.median(col(b, delay)) / np.median(col(A, delay)):6.1f}")
