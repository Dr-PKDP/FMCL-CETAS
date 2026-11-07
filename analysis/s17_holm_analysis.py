"""
Table S17: paired comparison of CETAS with each baseline over the 30 further
seeds (12 to 41), from conf30.pkl (written by
main_comparison/s17_confirmatory_baselines.py). For each baseline and each of
energy, charging delay, fatigue, and compute it reports the median difference
(CETAS minus baseline), whether CETAS is better in every seed, and the paired
Wilcoxon signed-rank p-value, then applies Holm correction across all tests.

Usage: python analysis/s17_holm_analysis.py [conf30.pkl]
"""
import pickle
import sys

import numpy as np
from scipy import stats

out = pickle.load(open(sys.argv[1] if len(sys.argv) > 1 else "conf30.pkl", "rb"))
METRICS = [("energy_J", 1e6, "energy (MJ)", False), ("chg_penalty_mean", 0.01, "delay (pp)", False),
           ("cycling_max", 1, "fatigue", False), ("work_s", 1e3, "compute (ks)", True)]
cetas = out["cetas"]
rows, pvals = [], []
for name, runs in out.items():
    if name == "cetas":
        continue
    cells, all_better = [], True
    for key, scale, _, higher_better in METRICS:
        c = np.array([r[key] for r in cetas], float)
        b = np.array([r[key] for r in runs], float)
        d = c - b
        all_better &= bool((d > 0).all() if higher_better else (d < 0).all())
        cells.append(np.median(d) / scale)
        pvals.append(stats.wilcoxon(d).pvalue)
    rows.append((name, cells, all_better))

m = len(pvals)
order = np.argsort(pvals)
holm = np.empty(m)
running = 0.0
for rank, i in enumerate(order):
    running = max(running, min(1.0, (m - rank) * pvals[i]))
    holm[i] = running

print(f"{'baseline':14}" + "".join(f"{lab:>16}" for *_, lab, _ in METRICS) + "   better in all seeds")
for name, cells, ok in rows:
    print(f"{name:14}" + "".join(f"{v:16.2f}" for v in cells) + f"   {ok}")
print(f"\n{m} paired Wilcoxon tests; raw p-values: {sorted(set(round(p, 12) for p in pvals))}")
print(f"Holm-adjusted p: min {holm.min():.2e}, max {holm.max():.2e}")
