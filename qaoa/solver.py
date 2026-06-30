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
import sys, os
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


def run_qaoa(scenario="Normal", B=20, p=2, steps=60, penalty=None, seed=1):
    """Build the QUBO for a scenario and approximately minimize it with QAOA."""
    import pennylane as qml
    from pennylane import numpy as pnp

    qubo = build_qubo(scenario, B=B, penalty=penalty)
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
    H_cost = qml.Hamiltonian(coeffs, ops)

    dev = get_backend(framework="pennylane", name="default.qubit", wires=n)

    def qaoa_layer(gamma, beta):
        qml.qaoa.cost_layer(gamma, H_cost)
        qml.qaoa.mixer_layer(beta, qml.qaoa.x_mixer(range(n)))

    @qml.qnode(dev)
    def circuit(params):
        for w in range(n):
            qml.Hadamard(w)                         # |+>^n initial state
        for l in range(p):
            qaoa_layer(params[0][l], params[1][l])
        return qml.expval(H_cost)

    pnp.random.seed(seed)
    params = pnp.array([[0.3] * p, [0.3] * p], requires_grad=True)
    opt = qml.AdamOptimizer(stepsize=0.1)           # TODO: try COBYLA / SPSA
    for _ in range(steps):
        params = opt.step(circuit, params)

    # Sample to read out a bitstring.
    @qml.qnode(get_backend(framework="pennylane", name="default.qubit",
                           wires=n, shots=512))
    def sample_circuit(params):
        for w in range(n):
            qml.Hadamard(w)
        for l in range(p):
            qaoa_layer(params[0][l], params[1][l])
        return [qml.sample(qml.PauliZ(w)) for w in range(n)]

    samples = pnp.array(sample_circuit(params)).T   # shape (shots, n), values +-1
    # Pick the lowest-energy sampled bitstring (z=+1 -> bit 0, z=-1 -> bit 1).
    best = None
    for row in samples:
        bitvec = [0 if z == 1 else 1 for z in row]
        e = qubo.energy(bitvec)
        if best is None or e < best[0]:
            best = (e, bitvec)
    result = decode(qubo, best[1], scenario)
    result.update({"scenario": scenario, "B": B, "p": p,
                   "num_qubits": n, "energy": best[0]})
    return result


if __name__ == "__main__":
    r = run_qaoa(scenario="Normal", B=20, p=2)
    print(r)
