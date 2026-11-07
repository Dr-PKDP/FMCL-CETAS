"""
Section 5.4 / Table S5 companion: relation between the observed fatigue-worst
session length m* and the prediction tau_heat / t_round (Eq. 13), and Sobol
total-order indices of m* over the coefficient library.

Reports, over 2000 Monte Carlo draws per seed, the Spearman correlation
between observed m* and the prediction, the share of draws in which the
observed and predicted values fall on the same or an adjacent grid point of
the tested session lengths, and the largest Sobol total-order indices. The
Sobol indices depend on the sampling seed of the scrambled sequence; the seeds
printed make that dependence visible.

Usage: python analysis/f9_sobol_check.py        (run from the repository root)
Requires: SALib
"""
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import uncertainty as U

names = U.NAMES
it, ir = names.index("tau_heat"), names.index("t_round")
grid = np.array(U.PATTERNS)


def run(seed, n=2000):
    U.RNG = np.random.default_rng(seed)
    X, res = U.monte_carlo(n)
    wm = np.array([r["worst_m"] for r in res])
    pred = X[:, it] / X[:, ir]
    gi = np.searchsorted(grid, wm)
    pi = np.abs(np.log(grid[None, :] / pred[:, None])).argmin(1)
    return (stats.spearmanr(wm, pred)[0], np.mean(gi == pi), np.mean(np.abs(gi - pi) <= 1),
            np.median(wm), np.median(pred))


for s in (20260802, 1, 2, 3):
    print(s, "rho %.3f  same grid point %.3f  within one %.3f  median m* %.1f  median prediction %.2f" % run(s))

from SALib.analyze import sobol as sa
from SALib.sample import sobol as ss

problem = {"num_vars": len(names), "names": names, "bounds": U.BOUNDS}
for seed in (20260809, 1, 2):
    X = ss.sample(problem, 256, calc_second_order=False, seed=seed)
    y = np.array([U.evaluate(x)["worst_m"] for x in X])
    Si = sa.analyze(problem, y, calc_second_order=False, print_to_console=False)
    top = np.argsort(-np.array(Si["ST"]))[:4]
    print("Sobol seed", seed, [(names[i], round(float(Si["ST"][i]), 3)) for i in top])
