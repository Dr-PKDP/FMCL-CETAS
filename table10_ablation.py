"""
Table 10: one-factor-at-a-time ablation of CETAS. Each row removes exactly one
term of the Eq. 18 scoring function (charger term, wear queue, or thermal
state) while holding every other setting -- V, W, gamma, the data-utility
weight, K, the fleet, and the six seeds -- identical to the full policy.

Requires: fleet_charging.py
"""
import pickle
import numpy as np
import fleet_charging as FC

SEEDS = range(6)
K = 30
W_BUDGET = 0.05
T_ROUND = 65.0
T_GAP = 15.0
HOURS = 6.0
V_TUNED = 5.0
NU_TUNED = 0.5


def p_ablate_charger(f, pool, K, st, rng):
    """Eq. 18 with the charger-headroom term (nu*h) removed. Energy and
    wear terms, and the weights on them, are exactly as in the full
    policy."""
    w = f.marginal_wear()[pool]
    e = f.round_energy()[pool]
    drift = FC._norm(st["Q"][pool] * w)
    return FC._topk(-(st["V"] * FC._norm(e) + drift)
                     + st["mu"] * f.utility[pool], pool, K)


def p_ablate_wear(f, pool, K, st, rng):
    """Eq. 18 with the virtual-wear-queue term (Q_hat * w_hat) removed
    from the SCORE. The queue itself keeps updating in run()'s outer
    loop exactly as for every other policy (Eq. 17 sits outside the
    policy function), so per-device fatigue is still measured; the
    policy just stops conditioning selection on it."""
    e = f.round_energy()[pool]
    h = FC._norm(f.charge_headroom()[pool])
    return FC._topk(-(st["V"] * FC._norm(e))
                     + st["mu"] * f.utility[pool] + st["nu"] * h, pool, K)


def p_ablate_thermal(f, pool, K, st, rng):
    """Eq. 18 with round_energy() (throttling-aware, temperature-dependent)
    replaced by the same nominal, thermally-blind power model the linear
    score baseline (p_static) uses for its own energy term: P_comp *
    t_round, with no eta/throttling factor at all."""
    w = f.marginal_wear()[pool]
    e_nominal = f.P_comp[pool] * f.t_round
    drift = FC._norm(st["Q"][pool] * w)
    h = FC._norm(f.charge_headroom()[pool])
    return FC._topk(-(st["V"] * FC._norm(e_nominal) + drift)
                     + st["mu"] * f.utility[pool] + st["nu"] * h, pool, K)


FC.POLICIES["ablate_charger"] = p_ablate_charger
FC.POLICIES["ablate_wear"] = p_ablate_wear
FC.POLICIES["ablate_thermal"] = p_ablate_thermal

RUNS = {
    "CETAS full":           ("charger_aware", V_TUNED, NU_TUNED),
    "Without charger term": ("ablate_charger", V_TUNED, NU_TUNED),
    "Without wear queue":   ("ablate_wear",    V_TUNED, NU_TUNED),
    "Without thermal state":("ablate_thermal", V_TUNED, NU_TUNED),
}


def run_all():
    results = {}
    for label, (policy, V, nu) in RUNS.items():
        results[label] = [
            FC.run(policy, n=100, hours=HOURS, K=K, seed=s, V=V, nu=nu,
                   W_budget=W_BUDGET, t_round=T_ROUND, t_gap=T_GAP)
            for s in SEEDS
        ]
    return results


def summarize(runs):
    return dict(
        energy_MJ=np.mean([r["energy_J"] for r in runs]) / 1e6,
        chg_pen_pct=np.mean([r["chg_penalty_mean"] for r in runs]) * 100,
        fatigue=np.mean([r["cycling_max"] for r in runs]),
        work_ks=np.mean([r["work_s"] for r in runs]) / 1000,
    )


if __name__ == "__main__":
    results = run_all()
    print(f"{'configuration':<24}{'energy(MJ)':>11}{'delay':>9}{'fatigue':>9}{'compute(ks)':>13}")
    print("-" * 66)
    for label in RUNS:
        s = summarize(results[label])
        print(f"{label:<24}{s['energy_MJ']:>11.2f}{s['chg_pen_pct']:>8.1f}%"
              f"{s['fatigue']:>9.0f}{s['work_ks']:>13.1f}")
    pickle.dump(results, open("true_ablation.pkl", "wb"))
