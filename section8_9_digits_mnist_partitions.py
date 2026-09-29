"""
Section 8.9: convergence checks on real image datasets (UCI digits and MNIST),
both single-partition and multi-partition variants.

Usage: python section8_9_digits_mnist_partitions.py <digits|mnist> <n_per> <single|multi> <n_seeds>

Requires: real_data.py, converge_charging.py
"""
import numpy as np, pickle, sys, time
import real_data as R, converge_charging as CC
ds,n_per,mode,nseeds=sys.argv[1],int(sys.argv[2]),sys.argv[3],int(sys.argv[4])
SET={'random':('random',1.0),'charger_aware':('charger_aware',5.0)}
if ds=='digits': SET['energy_only']=('energy_only',1.0)
fn=f'real_{ds}.pkl'
try: D=pickle.load(open(fn,'rb'))
except Exception: D={}
t=time.time()
if mode=='single':
    cl=R.make_real_federated_data(ds,N=100,n_per=n_per,alpha=0.3,seed=0)
    for s in range(nseeds):
        for p,(pol,V) in SET.items():
            k=('single',p,s)
            if k not in D: D[k]=CC.run(pol,*cl,n=100,K=30,hours=6.0,seed=s,V=V,nu=0.5)['final_quality']
else:
    for s in range(nseeds):
        cl=R.make_real_federated_data(ds,N=100,n_per=n_per,alpha=0.3,seed=s)
        for p,(pol,V) in SET.items():
            k=('multi',p,s)
            if k not in D: D[k]=CC.run(pol,*cl,n=100,K=30,hours=6.0,seed=s,V=V,nu=0.5)['final_quality']
        pickle.dump(D,open(fn,'wb'))
pickle.dump(D,open(fn,'wb')); print(ds,mode,nseeds,'done',round(time.time()-t),'s',flush=True)
