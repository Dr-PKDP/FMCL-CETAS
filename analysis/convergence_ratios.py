"""
Convergence ratios relative to random selection (Tables 9, S21, and the
multi-partition checks of Section 8.9). For each policy: geometric-mean ratio
of the final squared gradient norm to that of random selection in the same
seed, 95% t-interval on the log ratios, number of seeds in which the policy is
slower than random, uncorrected Wilcoxon p, and Holm-adjusted p across the
policies. For CETAS against each other policy: geometric-mean ratio, seeds in
which CETAS is lower, and uncorrected Wilcoxon p.

Inputs are the pickles written by
  convergence/table9_and_s21_confirmatory_seeds.py   (conv30.pkl; keys alpha, policy, seed)
  realdata/section8_9_digits_mnist_partitions.py     (real_digits.pkl, real_mnist.pkl; keys 'multi', policy, seed)
CIFAR-10 is analysed by realdata/analyze_cifar_partitions.py.

Usage: python analysis/convergence_ratios.py conv30.pkl 0.3
       python analysis/convergence_ratios.py real_digits.pkl
"""
import pickle
import sys

import numpy as np
from scipy import stats

D = pickle.load(open(sys.argv[1], "rb"))
if sys.argv[1].startswith("real_"):
    res = {(k[1], k[2]): v for k, v in D.items() if k[0] == "multi"}
else:
    alpha = float(sys.argv[2])
    res = {(k[1], k[2]): v for k, v in D.items() if k[0] == alpha}
policies = sorted({k[0] for k in res})
seeds = sorted(s for s in {k[1] for k in res} if all((p, s) in res for p in policies))
n = len(seeds)
print(f"{n} complete paired seeds; policies: {policies}\n")
vec = {p: np.array([res[(p, s)] for s in seeds], float) for p in policies}
rnd = vec["random"]
t = stats.t.ppf(0.975, n - 1)
others = [p for p in policies if p != "random"]
raw = {p: stats.wilcoxon(np.log(vec[p] / rnd)).pvalue for p in others}
order = sorted(others, key=raw.get)
holm, running = {}, 0.0
for i, p in enumerate(order):
    running = max(running, min(1.0, (len(order) - i) * raw[p]))
    holm[p] = running
print(f"{'policy':16}{'ratio':>8}{'95% CI':>18}{'slower':>9}{'Holm p':>10}   CETAS/policy (CETAS lower; p)")
for p in others:
    lr = np.log(vec[p] / rnd)
    m, se = lr.mean(), lr.std(ddof=1) / np.sqrt(n)
    line = (f"{p:16}{np.exp(m):8.2f}{np.exp(m - t*se):9.2f} to {np.exp(m + t*se):<5.2f}"
            f"{int((vec[p] > rnd).sum()):6d}/{n}{holm[p]:10.3f}")
    if "charger_aware" in vec and p != "charger_aware":
        c = vec["charger_aware"]
        line += f"   {np.exp(np.log(c / vec[p]).mean()):.2f} ({int((c < vec[p]).sum())}/{n}; p = {stats.wilcoxon(np.log(c / vec[p])).pvalue:.3f})"
    print(line)
