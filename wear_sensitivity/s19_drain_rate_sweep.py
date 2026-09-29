"""
Table S19: effect of the wear-queue drain rate W on CETAS at the tuned
operating point (V = 5, gamma = 0.5). Reports energy, delay, worst-device
fatigue, and the fraction of participating devices meeting the per-device
average-wear constraint of Eq. 14 at each tested value of W.

Requires: fleet_charging.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# The line above lets this script, now one level below the repo root, still find
# the core model modules (fleet_charging.py, converge_charging.py, etc.) that
# remain at the repo root.
import numpy as np, fleet_charging as FC
def run_ext(policy,seed,V,nu,W):
    rng=np.random.default_rng(seed); n=100
    fleet=FC.ChargingFleet(n,rng,t_round=65.0,t_gap=15.0); fleet.total_rounds=int(6*3600/80)
    base=FC.counterfactual_full_time(fleet)
    st={"Q":np.zeros(n),"V":V,"mu":0.3,"nu":nu,"_round":0}; fn=FC.POLICIES[policy]; Qmax=[]
    for _ in range(fleet.total_rounds):
        pool=np.where(fleet.available())[0]
        if len(pool)==0: fleet.step_round(np.array([],dtype=int)); continue
        chosen=np.asarray(fn(fleet,pool,30,st,rng),dtype=int); w=fleet.marginal_wear(); fleet.step_round(chosen)
        st["Q"]=np.maximum(st["Q"]-W,0.0); st["Q"][chosen]+=w[chosen]; Qmax.append(st["Q"].max())
    fleet.close()
    horizon=fleet.total_rounds*80; ft=np.where(np.isnan(fleet.full_time),horizon,fleet.full_time); bf=np.where(np.isnan(base),horizon,base)
    pen=ft/np.maximum(bf,1.0)-1.0; touched=fleet.selections>0
    return dict(cyc=fleet.cycling.copy(),Q=st["Q"].copy(),Qmax=np.array(Qmax),sel=fleet.selections.copy(),energy=fleet.energy.sum()/1e6,delay=pen[touched].mean()*100,work=fleet.work.sum()/1e3,rounds=fleet.total_rounds)
print('W sweep for CETAS (V=5, nu=0.5), seeds 0-3')
for W in (0.05,1.0,5.0,20.0,50.0):
    R=[run_ext('charger_aware',s,5.0,0.5,W) for s in range(4)]
    avg_rate=np.mean([r['cyc']/r['rounds'] for r in R],axis=0)      # per-device average wear per round
    part=np.concatenate([(r['sel']>0) for r in R])
    rate=np.concatenate([r['cyc']/r['rounds'] for r in R])
    frac_ok=np.mean(rate[part]<=W)
    print(f"W={W:<5} worst fatigue {np.mean([r['cyc'].max() for r in R]):8.0f} | energy {np.mean([r['energy'] for r in R]):.2f} delay {np.mean([r['delay'] for r in R]):.2f}% work {np.mean([r['work'] for r in R]):.1f} | participating devices with average wear <= W: {100*frac_ok:5.1f}% | median avg wear/round {np.median(rate[part]):7.2f} | final max Q {np.mean([r['Q'].max() for r in R]):9.0f}")
