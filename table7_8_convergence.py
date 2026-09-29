"""
Tables 7 and 8: optimisation progress at a fixed round budget, single data
partition, six fleet seeds. Table 7 reports the final gradient norm, fitted
convergence rate, and fitted floor per policy; Table 8 reports paired
significance tests of CETAS against each baseline.

Requires: fleet_charging.py, converge_charging.py, simulation.py
"""
import numpy as np, json, time
import fleet_charging as FC
import converge_charging as CC
from simulation import make_federated_data
clients,NC,DIM=make_federated_data(N=100,K=4,dim=10,n_per=50,alpha=0.3,seed=0)
ROWS=[('Random','random',1.0),('Linear score','static_score',1.0),('Energy-only','energy_only',1.0),('Oort','oort',1.0),('EAFL','eafl',1.0),('WILF-Q-analog','wilfq',1.0),('FedCS-Greedy','fedcs',1.0),('CETAS','charger_aware',5.0)]
out={}; t=time.time()
for name,pol,V in ROWS:
    runs=[CC.run(pol,clients,NC,DIM,n=100,K=30,hours=6.0,seed=s,V=V,nu=0.5) for s in range(6)]
    g=np.mean([r['grads'] for r in runs],axis=0)
    rate,floor=CC.rate_and_floor(g)
    out[name]=dict(final=float(np.mean([r['final_quality'] for r in runs])),final_sd=float(np.std([r['final_quality'] for r in runs],ddof=1)),rate=rate,floor=floor,contrib=float(np.mean([r['n_contributors'] for r in runs])),gini=float(np.mean([r['contrib_gini'] for r in runs])),dropout=float(np.mean([r['dropout_rate'] for r in runs])),finals=[r['final_quality'] for r in runs])
    print(name,round(time.time()-t),'s',flush=True)
json.dump(out,open('table7_8_convergence.json','w'))
