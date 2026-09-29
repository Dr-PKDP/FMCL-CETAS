"""
CIFAR-10 + small-CNN quality comparison, structurally identical to
converge_charging.py's run() -- same scheduling call, same dropout
handling, same clip-then-aggregate pattern, same debiasing option, same
Q/wear update -- with only the model representation and local-training
mechanics swapped from the flat-matrix linear solver to the CNN. Any
divergence from converge_charging.py's control flow here is a bug.
"""
import numpy as np
import torch

import fleet_charging as FC
from cifar_cnn import (SmallCIFARCNN, fedprox_local_cnn, apply_delta,
                        global_grad_sq_norm, clip_delta, delta_l2_norm)

LOCAL_STEPS = 5


def device_capability(fleet):
    import thermal as TH
    import charging as CH
    eta = TH.eta(fleet.T_s, fleet.T_cap, fleet.eta_min)
    admit = np.clip((CH.T_COMPUTE_KILL - fleet.T_s) /
                    (CH.T_COMPUTE_KILL - CH.T_COMPUTE_CEILING), 0.0, 1.0)
    return eta, admit


def run_cnn(policy, clients, n_classes, shape, n=100, hours=6.0, K=30, seed=0,
            V=1.0, mu=0.3, nu=0.5, W_budget=0.05, t_round=65.0, t_gap=15.0,
            prox_mu=0.1, clip=5.0, dropout_threshold=0.9, debias=False,
            propensity_floor=0.02, cnn_lr=0.02, device=None):
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)

    fleet = FC.ChargingFleet(n, rng, t_round=t_round, t_gap=t_gap)
    fleet.total_rounds = int(hours * 3600 / (t_round + t_gap))
    st = {"Q": np.zeros(n), "V": V, "mu": mu, "nu": nu, "_round": 0}
    if policy == "wilfq":
        st["_wilfq_idx"] = FC._build_wilfq_index(t_round, t_gap)
    fn = FC.POLICIES[policy]

    global_sd = SmallCIFARCNN(num_classes=n_classes).to(device).state_dict()
    global_sd = {k: v.detach().cpu() for k, v in global_sd.items()}

    grads, energy_curve = [], []
    n_selected = n_dropped = 0
    contributions = np.zeros(n)
    sel_count = np.zeros(n)
    rounds_seen = 0

    for _ in range(fleet.total_rounds):
        pool = np.where(fleet.available())[0]
        if len(pool) == 0:
            fleet.step_round(np.array([], dtype=int))
            grads.append(global_grad_sq_norm(global_sd, clients, device,
                                              num_classes=n_classes))
            energy_curve.append(float(fleet.energy.sum()))
            continue

        chosen = np.asarray(fn(fleet, pool, K, st, rng), dtype=int)
        eta, admit = device_capability(fleet)

        agg = {k: torch.zeros_like(v) for k, v in global_sd.items()}
        wsum = 0.0
        for i in chosen:
            n_selected += 1
            if admit[i] < dropout_threshold:
                n_dropped += 1
                continue
            ls = max(int(np.floor(LOCAL_STEPS * eta[i] * admit[i])), 1)
            X, y = clients[i]
            delta = fedprox_local_cnn(global_sd, X, y, device, mu=prox_mu,
                                       local_steps=ls, lr=cnn_lr,
                                       num_classes=n_classes)
            delta = clip_delta(delta, clip)
            wt = float(len(y))
            if debias:
                p_hat = max(sel_count[i] / max(rounds_seen, 1), propensity_floor)
                wt = wt / p_hat
            for k in agg:
                agg[k] = agg[k] + wt * delta[k]
            wsum += wt
            contributions[i] += 1
        if wsum > 0:
            global_sd = apply_delta(global_sd, {k: v / wsum for k, v in agg.items()})

        rounds_seen += 1
        sel_count[chosen] += 1
        w = fleet.marginal_wear()
        fleet.step_round(chosen)
        st["Q"] = np.maximum(st["Q"] - W_budget, 0.0)
        st["Q"][chosen] += w[chosen]

        grads.append(global_grad_sq_norm(global_sd, clients, device,
                                          num_classes=n_classes))
        energy_curve.append(float(fleet.energy.sum()))

    fleet.close()
    g = np.array(grads)
    e = np.array(energy_curve)
    return {
        "policy": policy, "grads": g, "energy_curve": e,
        "final_quality": float(g[-1]),
        "energy_J": float(fleet.energy.sum()),
        "cycling_max": float(fleet.cycling.max()),
        "n_selected": n_selected, "n_dropped": n_dropped,
        "dropout_rate": n_dropped / max(n_selected, 1),
        "n_contributors": int((contributions > 0).sum()),
    }
