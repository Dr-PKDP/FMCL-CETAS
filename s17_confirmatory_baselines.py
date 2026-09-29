"""
Table S17: confirmatory comparison of CETAS against eleven baselines (the
seven policies of Table 4 plus the four tuned or code-informed variants of
Table 11) on 30 further seeds, with Holm correction across all pairwise
tests.

The four tuned/code-informed baseline parameters below are the values
reported in Table 11 and Table S15 (Oort tuned: alpha=4.6; Oort
code-informed: alpha=4.0; EAFL tuned: floor=0.14; WILF-Q-analog tuned:
weight=0.0). To reproduce the search that selected them, see
baseline_tuning.py; this script takes the selected values as fixed inputs
rather than re-running that search.

Requires: fleet_charging.py, pols.py, oort_v2.py
"""
import numpy as np, pickle, sys, time
import fleet_charging as FC
from pols import make_p_oort, make_p_eafl, make_p_wilfq
from oort_v2 import make_p_oort_v2
# Selected values from Table 11 / Table S15, not re-searched here.
best={'oort':(4.6,), 'eafl':(0.14,), 'wilfq':(0.0,), 'oort_v2':(4.0,)}
idx=FC._build_wilfq_index(65.0,15.0)
FC.POLICIES['oort_t']=make_p_oort(best['oort'][0]); FC.POLICIES['eafl_t']=make_p_eafl(best['eafl'][0])
FC.POLICIES['wilfq_t']=make_p_wilfq(best['wilfq'][0],idx); FC.POLICIES['oort_v2_t']=make_p_oort_v2(alpha=best['oort_v2'][0])
ROWS={'cetas':('charger_aware',5.0,0.5),'random':('random',1,1),'static_score':('static_score',1,1),'energy_only':('energy_only',1,1),'oort':('oort',1,1),'eafl':('eafl',1,1),'fedcs':('fedcs',1,1),'oort_t':('oort_t',1,1),'eafl_t':('eafl_t',1,1),'oort_v2_t':('oort_v2_t',1,1),'wilfq':('wilfq',1,1),'wilfq_t':('wilfq_t',1,1)}
names=sys.argv[1].split(','); out={}
try: out=pickle.load(open('conf30.pkl','rb'))
except Exception: pass
t=time.time()
for n in names:
    pol,V,nu=ROWS[n]
    out[n]=[FC.run(pol,n=100,hours=6.0,K=30,seed=s,V=V,nu=nu,W_budget=0.05,t_round=65.0,t_gap=15.0) for s in range(12,42)]
    print(n,round(time.time()-t),'s',flush=True)
    pickle.dump(out,open('conf30.pkl','wb'))
