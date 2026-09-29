"""
Table 9 and Table S21: convergence over 30 paired seeds, each with its own
fleet and its own Dirichlet data partition. Table 9 is the alpha = 0.3 row;
Table S21 repeats the comparison at alpha = 0.1 and alpha = 0.05.

Usage: python table9_and_s21_confirmatory_seeds.py <alpha> <policy,policy,...> <seed_start> <seed_end>

Requires: fleet_charging.py, converge_charging.py, simulation.py
"""
import numpy as np, json, sys, time, pickle
import converge_charging as CC
from simulation import make_federated_data
alpha=float(sys.argv[1]); pols=sys.argv[2].split(','); s0,s1=int(sys.argv[3]),int(sys.argv[4])
SET={'random':('random',1.0),'charger_aware':('charger_aware',5.0),'energy_only':('energy_only',1.0),'static_score':('static_score',1.0),'oort':('oort',1.0),'eafl':('eafl',1.0),'wilfq':('wilfq',1.0),'fedcs':('fedcs',1.0)}
fn='conv30.pkl'
try: D=pickle.load(open(fn,'rb'))
except Exception: D={}
t=time.time()
for s in range(s0,s1):
    cl=make_federated_data(N=100,K=4,dim=10,n_per=50,alpha=alpha,seed=s)
    for p in pols:
        key=(alpha,p,s)
        if key in D: continue
        pol,V=SET[p]; D[key]=CC.run(pol,*cl,n=100,K=30,hours=6.0,seed=s,V=V,nu=0.5)['final_quality']
    pickle.dump(D,open(fn,'wb'))
print('alpha',alpha,'seeds',s0,s1,'done',round(time.time()-t),'s',len(D),'stored',flush=True)
