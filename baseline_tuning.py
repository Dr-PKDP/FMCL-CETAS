"""
Baseline tuning (Section 8.10, Tables 11, S15, and S16).

Oort, EAFL, and the WILF-Q-analog each expose one free parameter; FedCS-Greedy
has none. Each parameter is swept over 30 evenly spaced values on the six
evaluation seeds (0 to 5):

    Oort speed-discount exponent alpha      0.1 to 6.0
    EAFL safety floor (state of charge)     0.01 to 0.40
    WILF-Q-analog utility-blend weight      0.0 to 2.0

For each baseline the selected value minimises the rank-sum of mean energy,
mean charging delay, and mean worst-device fatigue over the 30 values (ties
broken by lower delay). The selected settings are then re-evaluated on six
unseen seeds (6 to 11), which gives Table S16.

The decision rules below are parameterised copies of p_oort, p_eafl, and
p_wilfq in fleet_charging.py. Run with default parameters they reproduce the
corresponding Table 4 rows (checked by the sanity block at the start of main).

Usage: python baseline_tuning.py
Writes baseline_tuning_results.pkl. Requires cats_tuned_full.pkl from
reproduce_table4.py for the sanity check.
"""
import pickle

import numpy as np

import fleet_charging as FC
import thermal as TH


def _topk(score, pool, K):
    return pool if len(pool) <= K else pool[np.argsort(-score)[:K]]


# ---- Parameterised copies of the tunable baselines ----

def make_p_oort(alpha):
    def p_oort_tuned(f, pool, K, st, rng):
        T_i = f.t_round / np.maximum(TH.eta(f.T_s[pool], f.T_cap[pool],
                                            f.eta_min[pool]), 1e-6)
        T_target = np.percentile(T_i, 50)
        sys_util = np.where(T_i > T_target, (T_target / T_i) ** alpha, 1.0)
        util = f.utility[pool] * sys_util
        round_idx = st.get("_round", 0)
        last_seen = st.setdefault("_last_seen", np.zeros(f.n))
        staleness = round_idx - last_seen[pool]
        ucb = np.sqrt(2.0 * np.log(round_idx + 2.0) / np.maximum(staleness, 1.0))
        chosen = _topk(util + 0.1 * ucb, pool, K)
        last_seen[chosen] = round_idx
        st["_round"] = round_idx + 1
        return chosen
    return p_oort_tuned

def make_p_eafl(soc_min):
    def p_eafl_tuned(f, pool, K, st, rng):
        headroom = np.maximum(f.soc[pool] - soc_min, 0.0)
        T_i = f.t_round / np.maximum(TH.eta(f.T_s[pool], f.T_cap[pool],
                                            f.eta_min[pool]), 1e-6)
        return _topk(headroom / T_i, pool, K)
    return p_eafl_tuned

def make_p_wilfq(util_weight, wilfq_idx):
    def p_wilfq_tuned(f, pool, K, st, rng):
        scores = np.array([wilfq_idx[f.cls[i]].at(f.T_s[i]) for i in pool])
        return _topk(scores + util_weight * f.utility[pool], pool, K)
    return p_wilfq_tuned


def run_custom(policy_fn, n=100, hours=6.0, K=30, seed=0,
                W_budget=0.05, t_round=65.0, t_gap=15.0):
    """Exact mirror of fleet_charging.run(), taking a policy FUNCTION
    directly instead of a string looked up in FC.POLICIES."""
    rng = np.random.default_rng(seed)
    fleet = FC.ChargingFleet(n, rng, t_round=t_round, t_gap=t_gap)
    fleet.total_rounds = int(hours * 3600 / (t_round + t_gap))
    base_full = FC.counterfactual_full_time(fleet)

    st = {"Q": np.zeros(n), "V": 1.0, "mu": 0.3, "nu": 1.0, "_round": 0}
    for _ in range(fleet.total_rounds):
        pool = np.where(fleet.available())[0]
        if len(pool) == 0:
            fleet.step_round(np.array([], dtype=int))
            continue
        chosen = np.asarray(policy_fn(fleet, pool, K, st, rng), dtype=int)
        w = fleet.marginal_wear()
        fleet.step_round(chosen)
        st["Q"] = np.maximum(st["Q"] - W_budget, 0.0)
        st["Q"][chosen] += w[chosen]
    fleet.close()

    horizon = fleet.total_rounds * (t_round + t_gap)
    ft = np.where(np.isnan(fleet.full_time), horizon, fleet.full_time)
    bf = np.where(np.isnan(base_full), horizon, base_full)
    pen = ft / np.maximum(bf, 1.0) - 1.0
    touched = fleet.selections > 0

    return {
        "work_s": float(fleet.work.sum()),
        "energy_J": float(fleet.energy.sum()),
        "cycling_max": float(fleet.cycling.max()),
        "chg_penalty_mean_frac": float(pen[touched].mean()) if touched.any() else 0.0,
        "chg_penalty_max_frac": float(pen.max()),
    }


GRIDS = {
    "oort": np.linspace(0.1, 6.0, 30),
    "eafl": np.linspace(0.01, 0.40, 30),
    "wilfq": np.linspace(0.0, 2.0, 30),
}
DEFAULTS = {"oort": 2.0, "eafl": 0.05, "wilfq": 0.05}
SELECTION_SEEDS = range(6)
UNSEEN_SEEDS = range(6, 12)


def make_policy(name, value, wilfq_idx):
    if name == "oort":
        return make_p_oort(value)
    if name == "eafl":
        return make_p_eafl(value)
    return make_p_wilfq(value, wilfq_idx)


def summarize(runs):
    return {
        "energy_MJ": np.mean([r["energy_J"] for r in runs]) / 1e6,
        "delay_pct": np.mean([r["chg_penalty_mean_frac"] for r in runs]) * 100,
        "fatigue": np.mean([r["cycling_max"] for r in runs]),
        "work_ks": np.mean([r["work_s"] for r in runs]) / 1e3,
    }


def select_by_rank_sum(rows):
    """Index of the value with the lowest rank-sum over energy, delay, and
    fatigue; ties are broken by lower delay."""
    keys = ("energy_MJ", "delay_pct", "fatigue")
    ranks = sum(np.argsort(np.argsort([r[k] for r in rows])) + 1 for k in keys)
    best = np.flatnonzero(ranks == ranks.min())
    return int(min(best, key=lambda i: rows[i]["delay_pct"]))


def main():
    wilfq_idx = FC._build_wilfq_index(65.0, 15.0)

    print("Sanity check: default parameters against cats_tuned_full.pkl")
    published = pickle.load(open("cats_tuned_full.pkl", "rb"))
    for name, value in DEFAULTS.items():
        fn = make_policy(name, value, wilfq_idx)
        runs = [run_custom(fn, seed=s) for s in SELECTION_SEEDS]
        e = np.mean([r["energy_J"] for r in runs])
        pub = np.mean([r["energy_J"] for r in published[name]])
        ok = abs(e - pub) / pub < 0.01
        print(f"  {name:6} energy {e/1e6:.4f} MJ vs published {pub/1e6:.4f} MJ: "
              f"{'match' if ok else 'MISMATCH'}")
        if not ok:
            raise SystemExit("default reimplementation does not match Table 4")

    results = {}
    for name, grid in GRIDS.items():
        rows = []
        print(f"\n{name}: sweep over {len(grid)} values")
        for v in grid:
            fn = make_policy(name, v, wilfq_idx)
            rows.append(summarize([run_custom(fn, seed=s) for s in SELECTION_SEEDS]))
            r = rows[-1]
            print(f"  {v:7.4f}  energy {r['energy_MJ']:.3f} MJ  delay {r['delay_pct']:6.1f}%  "
                  f"fatigue {r['fatigue']:7.0f}  work {r['work_ks']:6.1f} ks")
        k = select_by_rank_sum(rows)
        fn = make_policy(name, grid[k], wilfq_idx)
        unseen = summarize([run_custom(fn, seed=s) for s in UNSEEN_SEEDS])
        results[name] = {"grid": grid, "rows": rows, "selected": float(grid[k]),
                         "selected_row": rows[k], "unseen_row": unseen}
        print(f"  selected {grid[k]:.4f}: delay {rows[k]['delay_pct']:.1f}%, "
              f"fatigue {rows[k]['fatigue']:.0f}, energy {rows[k]['energy_MJ']:.2f} MJ")
        print(f"  unseen seeds 6-11: delay {unseen['delay_pct']:.1f}%, "
              f"fatigue {unseen['fatigue']:.0f}, energy {unseen['energy_MJ']:.2f} MJ")

    pickle.dump(results, open("baseline_tuning_results.pkl", "wb"))
    print("\nSaved: baseline_tuning_results.pkl")


if __name__ == "__main__":
    main()
