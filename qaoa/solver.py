"""
QAOA solver starter (PennyLane).

Pipeline:  QUBO  ->  Ising (h, J)  ->  cost Hamiltonian  ->  QAOA(p layers)
           ->  classical optimization of (gamma, beta)  ->  sample bitstrings
           ->  decode best feasible allocation.

This is a STARTER. The structure runs; the parts marked TODO are where the
team tunes (p, optimizer, penalty, block size) to push the result toward the
MILP optimum. Keep the framework choice in backend.py.

Run:  python -m qaoa.solver        (needs: pip install pennylane)
"""
import sys, os, gc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qubo.builder import build_qubo, decode
from backend import get_backend


def qubo_to_ising(qubo):
    """Convert QUBO (binary 0/1) to Ising (spin +-1).

    x_i = (1 - z_i) / 2,  z_i in {+1,-1}.  Returns (h, J, offset) where
    energy(z) = offset + sum_i h_i z_i + sum_{i<j} J_ij z_i z_j.
    """
    n = qubo.num_qubits
    h = {i: 0.0 for i in range(n)}
    J = {}
    offset = qubo.offset
    for (p, q), v in qubo.Q.items():
        if p == q:                      # linear (diagonal) term: v * x_p
            offset += v / 2.0
            h[p] -= v / 2.0
        else:                             # quadratic term: v * x_p x_q
            offset += v / 4.0
            h[p] -= v / 4.0
            h[q] -= v / 4.0
            J[(p, q)] = J.get((p, q), 0.0) + v / 4.0
    return h, J, offset # we include the offset to not mess up NWWD calculation. 


def run_qaoa(scenario="Normal", B=20, p=2, steps=60, penalty=None, seed=1,
             device=None, shots=512, urban_only=False, cap_mode="slack",
             bounds=None, lam=0.0, restarts=None, max_iter=0):
    """Build the QUBO for a scenario and approximately minimize it with QAOA.

    Optimization is gradient-FREE (scipy COBYLA) over the 2*p angles (gamma, beta)
    on a forward-only qnode (diff_method=None). This avoids autograd backprop,
    which stores every intermediate statevector and blows up RAM past ~22 qubits.
    Only the angle search differs from a gradient-based run; the QUBO, circuit,
    sampling and NWWD decoding are unchanged, so the reported score is exact.

    lam      : weight on the allocation-cost term (forwarded to build_qubo). The
               benchmark uses 0; set e.g. 0.1 to add lam * sum c_ij * x_ij to the
               NWWD objective and pull solutions toward cheaper sources.

    device   : PennyLane device name. Defaults to env QAOA_DEVICE, else
               "lightning.qubit" (fast C++ statevector, low memory). On a GPU box
               set QAOA_DEVICE=lightning.gpu. Memory is 2**n * 16 bytes regardless
               of optimizer, so exact simulation still caps around ~30 qubits.
    restarts : number of independent angle starts (best-of-N). None reads env
               QAOA_RESTARTS (default 1). restart 0 keeps the flat 0.3 warm start
               so best-of-N can never beat the single-start baseline; restarts 1..
               use random angles. The start with the lowest optimized expectation
               value (res.fun) wins.
    max_iter : COBYLA eval budget per restart. Precedence: explicit max_iter (>0)
               overrides `steps`, which overrides the p-scaled default (30*p).
    """
    import numpy as np
    import pennylane as qml
    from scipy.optimize import minimize

    device = device or os.environ.get("QAOA_DEVICE", "lightning.qubit")

    qubo = build_qubo(scenario, B=B, lam=lam, penalty=penalty,
                      urban_only=urban_only, cap_mode=cap_mode, bounds=bounds)
    n = qubo.num_qubits
    h, J, offset = qubo_to_ising(qubo)

    # Cost Hamiltonian as a PennyLane observable.
    coeffs, ops = [], []
    for i, hi in h.items():
        if hi:
            coeffs.append(hi); ops.append(qml.PauliZ(i))
    for (i, j), Jij in J.items():
        if Jij:
            coeffs.append(Jij); ops.append(qml.PauliZ(i) @ qml.PauliZ(j))

    # Normalize so max|coeff| = 1. QAOA applies a single angle gamma to the whole
    # cost layer; unscaled, the large penalty terms saturate (rotate past 2*pi)
    # while the tiny NWWD terms are invisible, so the optimizer can't see the
    # objective. Scaling H by a constant doesn't change its argmin, and the best
    # bitstring + NWWD are read from the RAW QUBO below, so this only helps the
    # angle search; the reported score is unchanged.
    scale = max((abs(c) for c in coeffs), default=1.0) or 1.0
    coeffs = [c / scale for c in coeffs]
    H_cost = qml.Hamiltonian(coeffs, ops)

    # params is a flat vector: gammas = params[:p], betas = params[p:].
    def ansatz(params):
        for w in range(n):
            qml.Hadamard(w)                         # |+>^n initial state
        for l in range(p):
            qml.qaoa.cost_layer(params[l], H_cost)
            qml.qaoa.mixer_layer(params[p + l], qml.qaoa.x_mixer(range(n)))

    dev = get_backend(framework="pennylane", name=device, wires=n)

    @qml.qnode(dev, diff_method=None)               # forward-only, no autograd graph
    def cost(params):
        ansatz(params)
        return qml.expval(H_cost)

    np.random.seed(seed)            # keep the readout sampling reproducible
    rng = np.random.default_rng(seed)   # independent stream for restart angles

    # Optimizer budget. Precedence: explicit max_iter (>0) > steps > p-scaled
    # default (30 COBYLA evals per layer). max_iter=0 means "not given".
    if max_iter:
        maxiter = max_iter
    elif steps is not None:
        maxiter = steps
    else:
        maxiter = 30 * p
    # Number of independent starts (best-of-N). Env override: QAOA_RESTARTS.
    if restarts is None:
        restarts = int(os.environ.get("QAOA_RESTARTS", "1"))
    restarts = max(1, restarts)

    # Live progress so the run isn't silent during the optimizer loop.
    # Set QAOA_VERBOSE=0 to mute (e.g. inside the sweep).
    verbose = os.environ.get("QAOA_VERBOSE", "1") != "0"

    def make_x0(r):
        # restart 0 keeps the old flat warm start, so best-of-N can never do
        # worse than the single-start baseline; restarts 1.. are random angles
        # (gammas in [0, 2pi), betas in [0, pi)).
        if r == 0:
            return np.full(2 * p, 0.3)
        return np.concatenate([rng.uniform(0.0, 2 * np.pi, p),
                               rng.uniform(0.0, np.pi, p)])

    # Track the best start by optimized expectation value (res.fun). All starts
    # share the same scaled Hamiltonian, so res.fun is directly comparable.
    opt = {"fun": float("inf"), "params": None, "restart": -1, "evals": 0}
    for r in range(restarts):
        state = {"i": 0, "best": float("inf")}

        def objective(x):
            e = float(cost(x))
            state["i"] += 1
            state["best"] = min(state["best"], e)
            if verbose and state["i"] % 5 == 0:
                print(f"    [qaoa {scenario} n={n} p={p} r={r}] "
                      f"eval {state['i']:3d}  E={e:.4f}  best={state['best']:.4f}",
                      flush=True)
            return e

        res = minimize(objective, make_x0(r), method="COBYLA",
                       options={"maxiter": maxiter})   # TODO: try SPSA for noisy backends
        if verbose:
            stop = "hit cap" if state["i"] >= maxiter else "converged early"
            print(f"    [qaoa {scenario} p={p}] restart {r}/{restarts - 1}: "
                  f"final={res.fun:.4f}  evals={state['i']}/{maxiter} ({stop})  "
                  f"incumbent={min(opt['fun'], res.fun):.4f}", flush=True)
        if res.fun < opt["fun"]:
            opt.update(fun=float(res.fun), params=res.x,
                       restart=r, evals=state["i"])

    params = opt["params"]

    # Free the optimizer's statevector BEFORE allocating the sampler's, so peak
    # RAM stays at one 2**n statevector instead of two (8GB -> 4GB at 28 qubits).
    del cost, dev
    gc.collect()

    # Sample to read out a bitstring.
    sdev = get_backend(framework="pennylane", name=device, wires=n, shots=shots)

    @qml.qnode(sdev, diff_method=None)
    def sample_circuit(params):
        ansatz(params)
        return [qml.sample(qml.PauliZ(w)) for w in range(n)]

    samples = np.array(sample_circuit(params)).T    # shape (shots, n), values +-1
    # Pick the lowest-energy sampled bitstring (z=+1 -> bit 0, z=-1 -> bit 1).
    best = None
    for row in samples:
        bitvec = [0 if z == 1 else 1 for z in row]
        e = qubo.energy(bitvec)
        if best is None or e < best[0]:
            best = (e, bitvec)
    result = decode(qubo, best[1], scenario)
    result.update({"scenario": scenario, "B": B, "p": p, "lam": lam,
                   "num_qubits": n, "energy": best[0],
                   "urban_only": urban_only, "cap_mode": cap_mode,
                   "restarts": restarts, "maxiter": maxiter,
                   "best_restart": opt["restart"], "opt_evals": opt["evals"],
                   "best_expval": opt["fun"],
                   "bitvec": best[1],
                   "values": {nm: qubo.value(nm, best[1]) for nm in qubo.registry}})

    # Release the sampler statevector so the next instance starts from a clean
    # slate (free memory before the next slot in a sweep).
    del sdev, sample_circuit
    gc.collect()
    return result
