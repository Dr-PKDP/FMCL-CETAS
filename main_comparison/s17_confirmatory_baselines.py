"""
Table S17 (simulation runs): CETAS and the baselines on 30 further seeds
(12 to 41). The statistical analysis, with Holm correction, is in
analysis/s17_holm_analysis.py.

The baselines are the seven policies of Table 4 plus the tuned variants of
Oort, EAFL, and the WILF-Q-analog from Table 11. The tuned parameters are the
grid values selected by baseline_tuning.py (Table S15): Oort alpha = 4.5759,
EAFL safety floor = 0.1445, WILF-Q-analog utility weight = 0.0. They are fixed
inputs here; this script does not repeat the search.

The code-informed Oort variant of Table 11 is not included: its
implementation is not part of this repository.

Usage: python main_comparison/s17_confirmatory_baselines.py <row,row,...>
Rows: cetas, random, static_score, energy_only, oort, eafl, fedcs, wilfq,
oort_t, eafl_t, wilfq_t. Results accumulate in conf30.pkl.

Requires: fleet_charging.py, baseline_tuning.py
"""

import os
import pickle
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import fleet_charging as FC
from baseline_tuning import make_p_oort, make_p_eafl, make_p_wilfq

BEST = {'oort': 4.5759, 'eafl': 0.1445, 'wilfq': 0.0}
idx = FC._build_wilfq_index(65.0, 15.0)
FC.POLICIES['oort_t'] = make_p_oort(BEST['oort'])
FC.POLICIES['eafl_t'] = make_p_eafl(BEST['eafl'])
FC.POLICIES['wilfq_t'] = make_p_wilfq(BEST['wilfq'], idx)

ROWS = {
    'cetas': ('charger_aware', 5.0, 0.5),
    'random': ('random', 1, 1), 'static_score': ('static_score', 1, 1),
    'energy_only': ('energy_only', 1, 1), 'oort': ('oort', 1, 1),
    'eafl': ('eafl', 1, 1), 'fedcs': ('fedcs', 1, 1), 'wilfq': ('wilfq', 1, 1),
    'oort_t': ('oort_t', 1, 1), 'eafl_t': ('eafl_t', 1, 1), 'wilfq_t': ('wilfq_t', 1, 1),
}
SEEDS = range(12, 42)

names = sys.argv[1].split(',') if len(sys.argv) > 1 else list(ROWS)
try:
    out = pickle.load(open('conf30.pkl', 'rb'))
except Exception:
    out = {}
t = time.time()
for n in names:
    pol, V, nu = ROWS[n]
    out[n] = [FC.run(pol, n=100, hours=6.0, K=30, seed=s, V=V, nu=nu, W_budget=0.05,
                     t_round=65.0, t_gap=15.0) for s in SEEDS]
    print(n, round(time.time() - t), 's', flush=True)
    pickle.dump(out, open('conf30.pkl', 'wb'))
