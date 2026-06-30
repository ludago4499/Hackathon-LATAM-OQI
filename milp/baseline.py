"""
Classical MILP/LP baseline for the Alto Atoyac water-allocation benchmark.

This is the GROUND TRUTH the quantum results are compared against.
With lambda = 0 the allocation variables are continuous, so this is an LP and
the solver returns the exact optimal NWWD.

Validated optimum (lambda = 0):
    Normal    NWWD = 2.526   (Puebla urban unmet 24)
    Moderate  NWWD = 5.158   (Puebla urban unmet 49)
    Severe    NWWD = 7.789   (Puebla urban unmet 74)

Run:  python -m milp.baseline
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pulp
from data.instance import instance, DROUGHT


def solve_milp(scenario, lam=0.0, urban_only=False):
    """Solve the allocation LP/MILP for one drought scenario.

    lam (lambda): weight on allocation cost. The benchmark uses lam = 0.
    urban_only  : if True, drop agriculture entirely (no agri demand, balance or
                  objective term) so this matches the urban-only QUBO variant.
    Returns a results dict with NWWD, allocations and unmet demand.
    """
    inst = instance(scenario)
    I = inst["source_names"]
    J = inst["municipalities"]
    Du, Da = inst["urban_demand"], inst["agri_demand"]
    A = inst["sources"]
    c = inst["cost"]
    wU, wA = inst["w_urban"], inst["w_agri"]

    m = pulp.LpProblem("atoyac_allocation", pulp.LpMinimize)

    xu = pulp.LpVariable.dicts("xu", (I, J), lowBound=0)   # source->urban
    xa = pulp.LpVariable.dicts("xa", (I, J), lowBound=0)   # source->agri
    uu = pulp.LpVariable.dicts("uu", J, lowBound=0)        # unmet urban
    ua = pulp.LpVariable.dicts("ua", J, lowBound=0)        # unmet agri

    # Objective: NWWD (+ optional cost term). Agri terms vanish if urban_only.
    nwwd = wU * pulp.lpSum(uu[j] / Du[j] for j in J)
    if not urban_only:
        nwwd += wA * pulp.lpSum(ua[j] / Da[j] for j in J)
    if urban_only:
        cost = pulp.lpSum(c[(i, j)] * xu[i][j] for i in I for j in J)
    else:
        cost = pulp.lpSum(c[(i, j)] * (xu[i][j] + xa[i][j]) for i in I for j in J)
    m += nwwd + lam * cost

    # Source capacity (agri usage included only when not urban_only)
    for i in I:
        used = pulp.lpSum(xu[i][j] for j in J)
        if not urban_only:
            used += pulp.lpSum(xa[i][j] for j in J)
        m += used <= A[i], f"cap_{i}"
    # Demand balance
    for j in J:
        m += pulp.lpSum(xu[i][j] for i in I) + uu[j] == Du[j], f"urb_{j}"
        if not urban_only:
            m += pulp.lpSum(xa[i][j] for i in I) + ua[j] == Da[j], f"agr_{j}"

    m.solve(pulp.PULP_CBC_CMD(msg=0))

    alloc = {(i, j, "urban"): xu[i][j].value() for i in I for j in J}
    if not urban_only:
        alloc.update({(i, j, "agri"): xa[i][j].value() for i in I for j in J})
    return {
        "scenario": scenario,
        "urban_only": urban_only,
        "status": pulp.LpStatus[m.status],
        "NWWD": pulp.value(nwwd),
        "objective": pulp.value(m.objective),
        "unmet_urban": {j: round(uu[j].value(), 4) for j in J},
        "unmet_agri": ({} if urban_only
                       else {j: round(ua[j].value(), 4) for j in J}),
        "norm_unmet_urban": {j: round(uu[j].value() / Du[j], 4) for j in J},
        "norm_unmet_agri": ({} if urban_only
                            else {j: round(ua[j].value() / Da[j], 4) for j in J}),
        "allocation": {k: round(v, 4) for k, v in alloc.items() if v and v > 1e-6},
    }


def main(lam=0.0, urban_only=False):
    tag = " [urban-only]" if urban_only else ""
    print(f"MILP baseline (lambda={lam}){tag}\n" + "=" * 48)
    for s in DROUGHT:
        if s not in ("Normal", "Moderate", "Severe"):
            continue
        r = solve_milp(s, lam=lam, urban_only=urban_only)
        print(f"\n{s} [{r['status']}]  NWWD = {r['NWWD']:.4f}")
        uu = {j: v for j, v in r["unmet_urban"].items() if v > 1e-6}
        ua = {j: v for j, v in r["unmet_agri"].items() if v > 1e-6}
        print(f"  unmet urban: {uu or 'none'}")
        if not urban_only:
            print(f"  unmet agri : {ua or 'none'}")


if __name__ == "__main__":
    main()
