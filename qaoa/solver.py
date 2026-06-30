"""
QAOA solver starter (PennyLane).

Pipeline:  QUBO  ->  Ising (h, J)  ->  cost Hamiltonian  ->  QAOA(p layers)
           ->  classical optimization of (gamma, beta)  ->  sample bitstrings
           ->  decode best feasible allocation. (lowest energy) 

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
             device=None, shots=512, urban_only=False, cap_mode="slack"):
    """Build the QUBO for a scenario and approximately minimize it with QAOA.

    Optimization is gradient-FREE (scipy COBYLA) over the 2*p angles (gamma, beta)
    on a forward-only qnode (diff_method=None). This avoids autograd backprop,
    which stores every intermediate statevector and blows up RAM past ~22 qubits.
    Only the angle search differs from a gradient-based run; the QUBO, circuit,
    sampling and NWWD decoding are unchanged, so the reported score is exact.

    device : PennyLane device name. Defaults to env QAOA_DEVICE, else
             "lightning.qubit" (fast C++ statevector, low memory). 
             
             On the GPU box we can set QAOA_DEVICE=lightning.gpu. Memory is 2**n * 16 bytes regardless
             of optimizer, so exact simulation still caps around ~30 to 35 qubits.
    """
    import numpy as np
    import pennylane as qml
    from scipy.optimize import minimize

    device = device or os.environ.get("QAOA_DEVICE", "lightning.qubit")

    qubo = build_qubo(scenario, B=B, penalty=penalty,
                      urban_only=urban_only, cap_mode=cap_mode)
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

    np.random.seed(seed)
    x0 = np.full(2 * p, 0.3)
    # Live progress so the run isn't silent during the optimizer loop.
    # Set QAOA_VERBOSE=0 to mute (e.g. inside the sweep).
    verbose = os.environ.get("QAOA_VERBOSE", "1") != "0"
    state = {"i": 0, "best": float("inf")}

    def objective(x):
        e = float(cost(x))
        state["i"] += 1
        state["best"] = min(state["best"], e)
        if verbose and state["i"] % 5 == 0:
            print(f"    [qaoa {scenario} n={n}] eval {state['i']:3d}  "
                  f"E={e:.4f}  best={state['best']:.4f}", flush=True)
        return e

    res = minimize(objective, x0, method="COBYLA",
                   options={"maxiter": steps})      # TODO: try SPSA for noisy backends
    params = res.x

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
    result.update({"scenario": scenario, "B": B, "p": p,
                   "num_qubits": n, "energy": best[0],
                   "urban_only": urban_only, "cap_mode": cap_mode})

    # Release the sampler statevector so the next instance starts from a clean
    # slate (this is the "free memory before the next slot" step).
    del sample_circuit, sdev, samples
    gc.collect()
    return result


if __name__ == "__main__":
    r = run_qaoa(scenario="Normal", B=20, p=2)
    print(r)
