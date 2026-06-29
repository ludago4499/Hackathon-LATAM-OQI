"""
Single entrypoint. On QCentroid Launchpad, run this from a notebook cell:
    %run run.py
or from a terminal:
    python run.py            # MILP baseline + QUBO sanity check
    python run.py --qaoa     # also run the QAOA starter (needs pennylane)
"""
import sys

from milp.baseline import main as run_milp
from qubo.builder import build_reduced_qubo, brute_force, build_qubo


def qubo_section():
    print("\nQUBO sanity check (reduced problem)\n" + "=" * 48)
    q, D, wU = build_reduced_qubo(B=5)
    e, combo = brute_force(q)
    nwwd = sum(wU * q.value(f"u_{j}", combo) / D[j] for j in D)
    print(f"  {q.num_qubits} qubits  ->  NWWD = {nwwd:.4f} (expected 6.6667)")

    print("\nFull-instance QUBO size (qubits)\n" + "=" * 48)
    for B in (20, 10, 5):
        sizes = {s: build_qubo(s, B=B).num_qubits
                 for s in ("Normal", "Moderate", "Severe")}
        print(f"  B={B:2d} hm3:  " + "  ".join(f"{s}={n}" for s, n in sizes.items()))


if __name__ == "__main__":
    run_milp()
    qubo_section()
    if "--qaoa" in sys.argv:
        print("\nQAOA starter\n" + "=" * 48)
        from qaoa.solver import run_qaoa
        print(run_qaoa(scenario="Normal", B=20, p=2))
