"""
Two-stage hierarchical QAOA with bound tightening (coarse-QAOA bracket).

Stage 1 (coarse):  run QAOA at block size B0 (default 20). Decode the best
                   sampled bitstring -> per-variable block value v_coarse[name].
Bracket:           [v_coarse - margin*B0,  v_coarse + margin*B0]  per variable
                   (margin coarse blocks each side), clamped to the variable's
                   native [0, ub] and snapped to the fine grid.
Stage 2 (fine):    rebuild the QUBO at block size B1 (<= B0) with bounds=bracket
                   so each variable is OFFSET-encoded over its narrow window:
                       x = lower + B1 * sum_k 2^k b_k
                   -> fewer qubits and/or finer resolution. Run QAOA again.

We separate two questions the method must pass:
  (A) METHOD CEILING  - does the bracketed search space still CONTAIN a near
      optimal solution? Measured by brute-forcing the reduced QUBO (small) and
      comparing its true minimum NWWD to the MILP optimum and to the full
      (untightened) fine-grid optimum. This is independent of QAOA quality.
  (B) SOLVER QUALITY  - does QAOA actually FIND it? Measured by the sampled
      NWWD vs that ceiling.

Run:  python -m qaoa.hierarchical --scenario Severe --B0 20 --B1 10 --margin 1
"""
import os, sys, math, json, argparse, itertools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qubo.builder import build_qubo, decode
from qaoa.solver import run_qaoa
from milp.baseline import solve_milp
from data.instance import instance


def true_nwwd(q, bits, scenario):
    """Physically meaningful score from the ALLOCATION itself (ignore u-slack).

    unmet_j = max(0, D_j - served_j) against the real (unsnapped) demand D_j;
    NWWD = sum_d w_d * sum_j unmet_j / D_j. Feasible iff every source's used
    water respects its real availability A_i. This removes the degenerate
    'set u=0 and under-serve within tol' solutions the loose decode admits.
    """
    inst = instance(scenario)
    I, J = inst["source_names"], inst["municipalities"]
    dem = {"urban": inst["urban_demand"], "agri": inst["agri_demand"]}
    w = {"urban": inst["w_urban"], "agri": inst["w_agri"]}
    A = inst["sources"]
    dtypes = tuple(q.meta.get("dtypes", ("urban", "agri")))
    served = {(d, j): sum(q.value(f"x_{d}_{i}_{j}", bits) for i in I)
              for d in dtypes for j in J}
    nwwd = sum(w[d] * max(0.0, dem[d][j] - served[(d, j)]) / dem[d][j]
               for d in dtypes for j in J)
    used = {i: sum(q.value(f"x_{d}_{i}_{j}", bits) for d in dtypes for j in J)
            for i in I}
    cap_ok = all(used[i] <= A[i] + 1e-6 for i in I)
    return nwwd, cap_ok


def best_of(scenario, B, p, steps, seeds, urban_only, cap_mode, bounds=None):
    """Run QAOA over several seeds; keep the lowest-energy result."""
    best = None
    for sd in seeds:
        r = run_qaoa(scenario, B=B, p=p, steps=steps, seed=sd,
                     urban_only=urban_only, cap_mode=cap_mode, bounds=bounds)
        if best is None or r["energy"] < best["energy"]:
            best = r
    return best


def brute_min(scenario, B, urban_only, cap_mode, bounds=None, cap_qubits=16):
    """Exact min TRUE-NWWD over capacity-feasible allocations in the search space.
    Returns (nwwd, n_qubits) or (None, n) if too big to enumerate."""
    q = build_qubo(scenario, B=B, urban_only=urban_only, cap_mode=cap_mode,
                   bounds=bounds)
    n = q.num_qubits
    if n > cap_qubits:
        return None, n
    best = float("inf")
    for bits in itertools.product((0, 1), repeat=n):
        nw, ok = true_nwwd(q, bits, scenario)
        if ok and nw < best:
            best = nw
    return best, n


def bracket(values, B0, margin):
    return {nm: (max(0.0, v - margin * B0), v + margin * B0)
            for nm, v in values.items()}


def run(scenario="Severe", B0=20, B1=10, margin=1, urban_only=True,
        cap_mode="unbalanced", p1=2, s1=60, p2=3, s2=80, nseed=3, brute=True):
    out = {"scenario": scenario, "B0": B0, "B1": B1, "margin": margin,
           "urban_only": urban_only, "cap_mode": cap_mode}
    opt = solve_milp(scenario, urban_only=urban_only)["NWWD"]
    out["milp_opt"] = round(opt, 4)

    # ---- full-grid qubit accounting + ceilings -------------------------------
    qc = build_qubo(scenario, B=B0, urban_only=urban_only, cap_mode=cap_mode)
    out["coarse_qubits"] = qc.num_qubits
    qf = build_qubo(scenario, B=B1, urban_only=urban_only, cap_mode=cap_mode)
    out["fine_full_qubits"] = qf.num_qubits

    # ---- STAGE 1: coarse QAOA ------------------------------------------------
    c = best_of(scenario, B0, p1, s1, range(1, nseed + 1), urban_only, cap_mode)
    cq = build_qubo(scenario, B=B0, urban_only=urban_only, cap_mode=cap_mode)
    cnw, cok = true_nwwd(cq, c["bitvec"], scenario)
    out["coarse_qaoa_nwwd"] = round(cnw, 4)
    out["coarse_feasible"] = cok
    bnd = bracket(c["values"], B0, margin)

    # ---- STAGE 2: tightened fine QAOA ----------------------------------------
    qr = build_qubo(scenario, B=B1, urban_only=urban_only, cap_mode=cap_mode,
                    bounds=bnd)
    out["fine_reduced_qubits"] = qr.num_qubits
    out["qubit_saving"] = out["fine_full_qubits"] - out["fine_reduced_qubits"]
    r = best_of(scenario, B1, p2, s2, range(1, nseed + 1), urban_only, cap_mode,
                bounds=bnd)
    rnw, rok = true_nwwd(qr, r["bitvec"], scenario)
    out["refined_qaoa_nwwd"] = round(rnw, 4)
    out["refined_feasible"] = rok

    # ---- ceilings (method correctness, independent of QAOA) ------------------
    if brute:
        bf_full, _ = brute_min(scenario, B1, urban_only, cap_mode)
        bf_red, _ = brute_min(scenario, B1, urban_only, cap_mode, bounds=bnd)
        out["fine_full_best"] = None if bf_full is None else round(bf_full, 4)
        out["fine_reduced_best"] = None if bf_red is None else round(bf_red, 4)
        # bracket is VALID if tightening did not raise the achievable optimum
        if bf_full is not None and bf_red is not None:
            out["bracket_valid"] = abs(bf_red - bf_full) < 1e-6
            out["bracket_cost"] = round(bf_red - bf_full, 4)
    return out


def fmt(o):
    L = []
    L.append(f"  scenario={o['scenario']}  model={'urban' if o['urban_only'] else 'full'}/{o['cap_mode']}")
    L.append(f"  MILP optimum (continuous)      : {o['milp_opt']}")
    L.append(f"  qubits  coarse B={o['B0']:<3}          : {o['coarse_qubits']}")
    L.append(f"  qubits  fine   B={o['B1']:<3} full     : {o['fine_full_qubits']}")
    L.append(f"  qubits  fine   B={o['B1']:<3} reduced  : {o['fine_reduced_qubits']}   (saved {o['qubit_saving']})")
    L.append(f"  coarse QAOA NWWD               : {o['coarse_qaoa_nwwd']}  feasible={o['coarse_feasible']}")
    L.append(f"  refined QAOA NWWD (tightened)  : {o['refined_qaoa_nwwd']}  feasible={o['refined_feasible']}")
    if "fine_full_best" in o:
        L.append(f"  ceiling: best @B{o['B1']} full        : {o['fine_full_best']}")
        L.append(f"  ceiling: best @B{o['B1']} in-bracket   : {o['fine_reduced_best']}")
        if "bracket_valid" in o:
            L.append(f"  BRACKET VALID (contains optimum): {o['bracket_valid']}  (cost {o['bracket_cost']})")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="Severe")
    ap.add_argument("--B0", type=int, default=20)
    ap.add_argument("--B1", type=int, default=10)
    ap.add_argument("--margin", type=int, default=1)
    ap.add_argument("--full", action="store_true", help="full model (urban+agri)")
    ap.add_argument("--cap", default="unbalanced")
    ap.add_argument("--no-brute", action="store_true")
    ap.add_argument("--nseed", type=int, default=3)
    a = ap.parse_args()
    o = run(a.scenario, a.B0, a.B1, a.margin, urban_only=not a.full,
            cap_mode=a.cap, nseed=a.nseed, brute=not a.no_brute)
    print(fmt(o))
    print(json.dumps(o))
