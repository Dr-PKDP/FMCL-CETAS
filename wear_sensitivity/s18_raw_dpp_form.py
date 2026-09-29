"""
Table S18: CETAS scored with the raw drift-plus-penalty form (fixed scaling
constants, no per-round min-max normalisation) in place of Eq. 18, at several
values of V. Fixed constants are calibrated on a held-out seed, never on the
evaluation seeds.

Requires: fleet_charging.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# The line above lets this script, now one level below the repo root, still find
# the core model modules (fleet_charging.py, converge_charging.py, etc.) that
# remain at the repo root.
import numpy as np, fleet_charging as FC, pickle
# 1. calibrate FIXED constants on a separate seed (100), never on evaluation seeds
rec={'er':[],'dr':[]}
orig=FC.p_charger_aware
def wrap(f,pool,K,st,rng):
    w=f.marginal_wear()[pool]; e=f.round_energy()[pool]; d=st['Q'][pool]*w
    rec['er'].append(np.ptp(e)); rec['dr'].append(np.ptp(d)); return orig(f,pool,K,st,rng)
FC.POLICIES['tmp']=wrap
FC.run('tmp',n=100,hours=6.0,K=30,seed=100,V=5.0,nu=0.5,W_budget=0.05,t_round=65.0,t_gap=15.0)
cE=1.0/np.mean(rec['er']); cD=1.0/np.mean(rec['dr']); print('fixed constants: cE=%.5f per J, cD=%.3e'%(cE,cD),flush=True)
# 2. raw drift-plus-penalty score with FIXED constants: S = -(V*cE*E + cD*Q*w) + mu*U + nu*h_hat  (h already in [0,1])
def make(V_scale):
    def p(f,pool,K,st,rng):
        w=f.marginal_wear()[pool]; e=f.round_energy()[pool]
        h=f.charge_headroom()[pool]
        S=-(st['V']*cE*e + cD*st['Q'][pool]*w) + st['mu']*f.utility[pool] + st['nu']*h
        return FC._topk(S,pool,K)
    return p
FC.POLICIES['raw_dpp']=make(1.0)
res={}
for V in (1.0,2.0,3.0,5.0,8.0):
    runs=[FC.run('raw_dpp',n=100,hours=6.0,K=30,seed=s,V=V,nu=0.5,W_budget=0.05,t_round=65.0,t_gap=15.0) for s in range(6)]
    g=lambda k:np.array([r[k] for r in runs],float)
    res[V]=dict(en=g('energy_J').mean()/1e6,dl=g('chg_penalty_mean').mean()*100,fat=g('cycling_max').mean(),comp=g('work_s').mean()/1e3,used=g('n_touched').mean(),util=g('utilisation').mean(),jain=g('jain').mean())
    print('raw V=%.0f'%V,{k:round(float(v),2) for k,v in res[V].items()},flush=True)
pickle.dump(dict(cE=cE,cD=cD,res=res),open('raw_dpp.pkl','wb'))
print('CETAS ref: en 3.48 dl 2.11 fat 4667 comp 525.0 used 92 util 0.997 jain 0.755')
