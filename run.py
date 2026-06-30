"""
Single entrypoint. On QCentroid Launchpad, run this from a notebook cell:
    %run run.py
or from a terminal:
    python run.py            # MILP baseline + QUBO sanity check
    python run.py --qaoa     # also run the QAOA starter (needs pennylane)

Lean QUBO variant flags (fewer qubits, so small B fits on a simulator):
    python run.py --urban-only        # drop agriculture (urban-only model)
    python run.py --unbalanced-cap    # slack-free capacity (no cap_i qubits)
    python run.py --urban-only --unbalanced-cap --qaoa   # both + run QAOA
The same flags apply to the MILP baseline, the qubit-size table and the QAOA run
so everything stays apples-to-apples.

QAOA block size is read from env QAOA_B (default 50 -> 20 qubits, ~16 MB, no
OOM on a small box). Tomorrow on the big machine drop it for finer resolution:
    QAOA_B=20 python run.py --qaoa     # 28 qubits, ~4 GB
"""
import os, sys

from milp.baseline import main as run_milp
from qubo.builder import build_qubo

# ---- variant flags -------------------------------------------------------
URBAN_ONLY = "--urban-only" in sys.argv
UNBALANCED = "--unbalanced-cap" in sys.argv
CAP_MODE = "unbalanced" if UNBALANCED else "slack"
# kwargs threaded into every build_qubo / run_qaoa call below
VKW = {"urban_only": URBAN_ONLY, "cap_mode": CAP_MODE}


def qubo_section():
    tag = []
    if URBAN_ONLY:
        tag.append("urban-only")
    if UNBALANCED:
        tag.append("unbalanced-cap")
    suffix = f"  [{', '.join(tag)}]" if tag else ""
    print(f"\nFull-instance QUBO size (qubits){suffix}\n" + "=" * 48)
    for B in (20, 15, 10): # Arbitrairly set Blocks of 20, 10 ,5. B -> 1 should tend to classic solution.
        sizes = {s: build_qubo(s, B=B, **VKW).num_qubits
                 for s in ("Normal", "Moderate", "Severe")}
        print(f"  B={B:2d} hm3:  " + "  ".join(f"{s}={n}" for s, n in sizes.items()))


if __name__ == "__main__":
    run_milp(urban_only=URBAN_ONLY)
    qubo_section()
    if "--qaoa" in sys.argv:
        print("\nQAOA starter\n" + "=" * 48, flush=True)
        from qaoa.solver import run_qaoa
        scenario = os.environ.get("QAOA_SCENARIO", "Normal")  # Normal | Moderate | Severe
        B = int(os.environ.get("QAOA_B", "50"))   # nerfed default: 20 qubits
        p = int(os.environ.get("QAOA_P", "2"))    # QAOA depth (layers)
        n = build_qubo(scenario, B=B, **VKW).num_qubits
        print(f"  scenario={scenario}  B={B}  p={p}  qubits={n}  cap_mode={CAP_MODE}  "
              f"urban_only={URBAN_ONLY}  "
              f"(statevector ~{16 * (2 ** n) / 1e6:.0f} MB)", flush=True)
        print(run_qaoa(scenario=scenario, B=B, p=p, **VKW), flush=True)
