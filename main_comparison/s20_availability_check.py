"""
Table S20: effect of an independent availability random stream.

The main tables draw device availability from the same random generator
used for selection in Random and in the code-informed baselines, so their
availability sequences differ slightly from the other policies at the same
seed. This script reruns all eight policies with availability drawn from an
independent stream (fleet_charging_independent_availability.py) and compares
against the original harness.

Requires: fleet_charging.py, fleet_charging_independent_availability.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# The line above lets this script, now one level below the repo root, still find
# the core model modules (fleet_charging.py, converge_charging.py, etc.) that
# remain at the repo root.
import numpy as np, json, sys, importlib, time
import fleet_charging as FC, fleet_charging_independent_availability as FCf
ROWS=[('Random','random',1,1),('Linear score','static_score',1,1),('Energy-only','energy_only',1,1),('Oort','oort',1,1),('EAFL','eafl',1,1),('WILF-Q-analog','wilfq',1,1),('FedCS-Greedy','fedcs',1,1),('CETAS','charger_aware',5.0,0.5)]
def row(runs):
    g=lambda k:np.array([r[k] for r in runs],float)
    return dict(comp=g('work_s').mean()/1e3,en=g('energy_J').mean()/1e6,dl=g('chg_penalty_mean').mean()*100,dsd=g('chg_penalty_mean').std(ddof=1)*100,harm=g('n_harmed').mean(),Ts=g('T_s_peak').mean(),cap=g('above_cap_s').mean()/1e3,susp=g('suspended_s').mean()/1e3,fat=g('cycling_max').mean(),fsd=g('cycling_max').std(ddof=1),used=g('n_touched').mean(),util=g('utilisation').mean(),jain=g('jain').mean(),gini=g('gini').mean())
out={}
t=time.time()
for tag,mod in (('orig',FC),('fixed',FCf)):
    out[tag]={}
    for name,pol,V,nu in ROWS:
        runs=[mod.run(pol,n=100,hours=6.0,K=30,seed=s,V=V,nu=nu,W_budget=0.05,t_round=65.0,t_gap=15.0) for s in range(6)]
        out[tag][name]=row(runs)
    print(tag,'done',round(time.time()-t),'s',flush=True)
json.dump(out,open('s20_availability_check.json','w'))
