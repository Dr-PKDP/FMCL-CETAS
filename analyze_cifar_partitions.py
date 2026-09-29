"""
Paired analysis of the CIFAR-10 multi-partition run (same method as Table 9 and
Table S21): per-seed ratio of a policy's final squared gradient norm to that of
random selection, geometric mean, 95% t-interval on the log ratios, count of seeds
where the policy is slower than random, and Wilcoxon signed-rank p (uncorrected).

Usage: python analyze_cifar_partitions.py [checkpoint.pkl ...]
Several checkpoints (e.g. one per GPU) are merged.
"""
import glob
import pickle
import sys

import numpy as np
from scipy import stats

files = sys.argv[1:] or sorted(glob.glob("cifar_partitions_checkpoint*.pkl"))
res = {}
for f in files:
    with open(f, "rb") as fh:
        res.update(pickle.load(fh))
policies = sorted({k[0] for k in res})
seeds = sorted(s for s in {k[1] for k in res}
               if all((p, s) in res for p in policies))
print(f"files: {files}\ncomplete seeds ({len(seeds)}): {seeds}\n")
if "random" not in policies or len(seeds) < 3:
    sys.exit("need random and at least 3 complete seeds")
rnd = np.array([res[("random", s)]["final_quality"] for s in seeds])
n = len(seeds)
print(f"{'policy':16}{'geo-mean ratio':>16}{'95% CI':>18}{'slower than random':>20}{'Wilcoxon p':>12}")
for p in policies:
    if p == "random":
        continue
    x = np.array([res[(p, s)]["final_quality"] for s in seeds])
    lr = np.log(x / rnd)
    m, se = lr.mean(), lr.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.975, n - 1)
    pw = stats.wilcoxon(lr).pvalue
    print(f"{p:16}{np.exp(m):16.2f}{np.exp(m - t*se):9.2f} to {np.exp(m + t*se):<6.2f}"
          f"{int((x > rnd).sum()):>15}/{n}{pw:12.4f}")
if "charger_aware" in policies and "energy_only" in policies:
    c = np.array([res[("charger_aware", s)]["final_quality"] for s in seeds])
    e = np.array([res[("energy_only", s)]["final_quality"] for s in seeds])
    lr = np.log(c / e)
    print(f"\nCETAS / energy-only: geo-mean {np.exp(lr.mean()):.2f}, "
          f"CETAS lower in {int((c < e).sum())}/{n}, Wilcoxon p = {stats.wilcoxon(lr).pvalue:.4f}")
print("\nper-seed final ||g||^2:")
for s in seeds:
    print(f"  seed {s:2d}  " + "  ".join(f"{p}={res[(p, s)]['final_quality']:.3e}" for p in policies))
