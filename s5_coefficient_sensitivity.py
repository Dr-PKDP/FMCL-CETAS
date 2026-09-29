"""
Table S5: ordinal robustness of the Section 8 claims across the coefficient
library's plausible ranges. Draws 70 coefficient sets from the provenance
ranges in coefficients.py and reports the fraction of draws under which each
stated ordering between policies holds.

Usage: python s5_coefficient_sensitivity.py <seed_start> <seed_end>

Requires: fleet_charging.py, uq_charging.py, charging.py
"""
import numpy as np, pickle, sys, time
import uq_charging as UQ, charging as CH, fleet_charging as FC
s0,s1=int(sys.argv[1]),int(sys.argv[2])
# pre-generate the same 70 draws as the original script (same seed, same order)
UQ.RNG=np.random.default_rng(20260803)
draws=[UQ.sample_params() for _ in range(70)]
try: D=pickle.load(open('mc70.pkl','rb'))
except Exception: D={}
keep={k:getattr(CH,k) for k in UQ.NAMES}
POL=[('random','random',1,1),('static','static_score',1,1),('energy','energy_only',1,1),('oort','oort',1,1),('eafl','eafl',1,1),('wilfq','wilfq',1,1),('fedcs','fedcs',1,1),('aware','charger_aware',5.0,0.5),('blind','charger_aware',5.0,0.0)]
t=time.time()
for i in range(s0,s1):
    if i in D: continue
    UQ.apply(draws[i]); out={}
    try:
        for name,pol,V,nu in POL:
            r=FC.run(pol,n=100,hours=6.0,K=30,seed=0,V=V,nu=nu,W_budget=0.05,t_round=65.0,t_gap=15.0)
            out[name]={k:r[k] for k in ('work_s','energy_J','chg_penalty_mean','cycling_max','suspended_s','fast_share')}
        D[i]=out
    except Exception as ex:
        D[i]=None
    for k,v in keep.items(): setattr(CH,k,v)
    pickle.dump(D,open('mc70.pkl','wb'))
print('draws',s0,s1,'done',round(time.time()-t),'s; stored',len(D),flush=True)
