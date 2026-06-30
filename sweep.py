"""
QAOA sweep over block size B and drought scenario.

Prints the QAOA NWWD next to the MILP optimum (the ground-truth NWWD) for every
(B, scenario) pair. Anything above the qubit cap is reported as NA, because exact
statevector simulation needs 2**n * 16 bytes of RAM (28q ~ 4GB, 30q ~ 16GB,
33q ~ 137GB, 40q ~ 16TB).

Cap defaults to 22 qubits; override with env QAOA_MAX_QUBITS. An instance that
fits the cap but still runs out of memory at runtime is reported as NA(OOM).
Each row streams as it finishes and its statevector is freed before the next.

Run:  python -u sweep.py                              (cwq env: pulp, pennylane, scipy)
      QAOA_BLOCKS=80,50,30 python -u sweep.py         # nerf: 20-23 qubits, no OOM
      QAOA_MAX_QUBITS=30 QAOA_BLOCKS=20,10,5 python -u sweep.py   # big box tomorrow
      QAOA_DEVICE=lightning.gpu python -u sweep.py    # on the GPU box
"""
import sys, os, gc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qubo.builder import build_qubo
from milp.baseline import solve_milp

# Stream every row as it finishes instead of buffering until the whole sweep is
# done (matters when output is piped to a file or a notebook cell).
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Cap defaults to 22 qubits (~64 MB statevector) so a sweep runs on a small box
# without OOM. Raise it on the big machine: QAOA_MAX_QUBITS=30 python sweep.py
os.environ.setdefault("QAOA_VERBOSE", "0")   # keep the table clean; set =1 to trace
MAX_QUBITS = int(os.environ.get("QAOA_MAX_QUBITS", "22"))
SCENARIOS = ("Normal", "Moderate", "Severe") # the three sequía levels
# Block sizes (hm3). Larger B = fewer qubits. Nerf now with big blocks, e.g.
#   QAOA_BLOCKS=80,50,30 python -u sweep.py     -> 20-23 qubits, no OOM
# Revert to full resolution tomorrow with QAOA_BLOCKS=20,10,5 (the default).
BLOCKS = tuple(int(b) for b in os.environ.get("QAOA_BLOCKS", "20,10,5").split(","))


def main(p=1, steps=50):
    opt = {s: solve_milp(s)["NWWD"] for s in SCENARIOS}   # ground-truth NWWD

    print(f"QAOA sweep  (cap {MAX_QUBITS} qubits, p={p}, steps={steps}, "
          f"device={os.environ.get('QAOA_DEVICE', 'lightning.qubit')})")
    print("MILP optimum:  " + "   ".join(f"{s}={opt[s]:.3f}" for s in SCENARIOS))
    hdr = (f"{'B':>4} {'scenario':>10} {'qubits':>7} {'QAOA NWWD':>10} "
           f"{'optimum':>8} {'gap':>7} {'feasible':>9}")
    print(hdr)
    print("-" * len(hdr))

    from qaoa.solver import run_qaoa
    for B in BLOCKS:
        for s in SCENARIOS:
            n = build_qubo(s, B=B).num_qubits
            if n > MAX_QUBITS:
                print(f"{B:>4} {s:>10} {n:>7} {'NA':>10} {opt[s]:>8.3f} "
                      f"{'NA':>7} {'NA':>9}", flush=True)
                continue
            try:
                r = run_qaoa(scenario=s, B=B, p=p, steps=steps)
                gap = r["NWWD"] - opt[s]
                print(f"{B:>4} {s:>10} {n:>7} {r['NWWD']:>10.3f} "
                      f"{opt[s]:>8.3f} {gap:>7.3f} {str(r['feasible']):>9}", flush=True)
            except MemoryError:
                print(f"{B:>4} {s:>10} {n:>7} {'NA(OOM)':>10} {opt[s]:>8.3f} "
                      f"{'NA':>7} {'NA':>9}", flush=True)
            except Exception as e:                  # keep the sweep going
                print(f"{B:>4} {s:>10} {n:>7} {'ERR':>10} {opt[s]:>8.3f} "
                      f"{'NA':>7} {'NA':>9}   # {type(e).__name__}: {e}", flush=True)
            finally:
                # Drop this instance's statevector before the next slot so RAM
                # doesn't accumulate across the sweep.
                gc.collect()


if __name__ == "__main__":
    main()
