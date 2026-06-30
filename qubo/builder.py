"""
QUBO formulation of the Alto Atoyac water-allocation benchmark.

Idea (this is the whole trick):
  * Each continuous allocation x_{i,j}^d (source i -> municipality j, demand
    type d in {urban, agri}) is DISCRETIZED into integer blocks of size B hm^3,
    encoded in binary:  x = B * sum_k 2^k * b_k.
  * The UNMET demand u_j^d is represented by a slack variable, also in blocks.
    Demand balance  sum_i x_{i,j}^d + u_j^d = D_j^d  is added as a quadratic
    penalty. Because u_j^d IS the slack, the QUBO objective below is literally
    the NWWD:   NWWD = wU * sum (u_urban/D_urban) + wA * sum (u_agri/D_agri).
  * Source capacity  sum_{j,d} x_{i,j}^d <= A_eff_i  becomes an equality with a
    capacity-slack variable, also added as a quadratic penalty.

Output: a QUBO as an upper-triangular (by convention) dict   {(p, q): coeff} over bit indices,
plus a constant offset. Minimizing  x^T Q x + offset  is the optimization

Documented choices the challenge asks for (Section 1.9):
  - discretization strategy : fixed block size B (hm^3)
  - binary encoding         : standard base-2 expansion per variable
  - penalty coefficient     : `penalty` (single P for all constraints; can be tuned if necessary for specific model.)
  - number of binary vars   : build_qubo(...).num_qubits
  - feasibility             : decode() reports constraint residuals

Run:  python -m qubo.builder           # full instance qubit counts
      python -m qubo.builder --toy     # brute-force sanity check
"""
import sys, os, itertools, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.instance import instance


def _bits_for(upper_bound, B):
    """Number of bits needed to represent 0..upper_bound in steps of B."""
    n_blocks = int(upper_bound // B)
    return max(1, int(math.ceil(math.log2(n_blocks + 1))))


class QUBO:
    """Sparse QUBO with a constant offset and a named-variable registry."""

    def __init__(self):
        self.Q = {}              # {(p,q): coeff}, p <= q
        self.offset = 0.0
        self.registry = {}       # var name -> list of (bit_index, hm3_weight)
        self._n = 0

    def add_variable(self, name, upper_bound, B):
        bits = []
        for k in range(_bits_for(upper_bound, B)):
            bits.append((self._n, B * (2 ** k)))
            self._n += 1
        self.registry[name] = bits
        return bits

    @property
    def num_qubits(self):
        return self._n

    def _terms(self, names):
        out = []
        for nm in names:
            out.extend(self.registry[nm])
        return out

    def add_linear(self, names, scale):
        """Add  scale * sum(values)  to the objective (diagonal terms)."""
        for (idx, w) in self._terms(names):
            self._add(idx, idx, scale * w)

    def add_penalty(self, names, constant, P):
        """Add  P * (sum(values) - constant)^2  to the objective."""
        terms = self._terms(names)
        self.offset += P * constant ** 2
        for (i, wi) in terms:
            self._add(i, i, P * wi * wi - 2 * P * constant * wi)
            for (j, wj) in terms:
                if j > i:
                    self._add(i, j, 2 * P * wi * wj)

    def _add(self, p, q, v):
        if v == 0:
            return
        key = (p, q) if p <= q else (q, p)
        self.Q[key] = self.Q.get(key, 0.0) + v

    def value(self, name, bitvec):
        return sum(w for (idx, w) in self.registry[name] if bitvec[idx])

    def energy(self, bitvec):
        e = self.offset
        for (p, q), v in self.Q.items():
            if bitvec[p] and bitvec[q]:
                e += v
        return e


def build_qubo(scenario, B=10, lam=0.0, penalty=None):
    """Build the QUBO for one drought scenario.

    B       : block size in hm^3 (smaller = more accurate, more qubits)
    lam     : weight on allocation cost (benchmark uses 0)
    penalty : constraint penalty P. If None, a heuristic value is chosen.
    """
    inst = instance(scenario)
    I, J = inst["source_names"], inst["municipalities"]
    Du, Da = inst["urban_demand"], inst["agri_demand"]
    A, c = inst["sources"], inst["cost"]
    wU, wA = inst["w_urban"], inst["w_agri"]
    demand = {"urban": Du, "agri": Da}
    weight = {"urban": wU, "agri": wA}

    if penalty is None:
        penalty = 50.0 * max(wU, wA) # 50 is big number

    qubo = QUBO()

    for d in ("urban", "agri"):
        for i in I:
            for j in J:
                ub = min(demand[d][j], A[i])
                qubo.add_variable(f"x_{d}_{i}_{j}", ub, B)
    for d in ("urban", "agri"):
        for j in J:
            qubo.add_variable(f"u_{d}_{j}", demand[d][j], B)
    for i in I:
        qubo.add_variable(f"cap_{i}", A[i], B)

    # objective: NWWD = sum_d w_d * sum_j u_j^d / D_j^d
    for d in ("urban", "agri"):
        for j in J:
            qubo.add_linear([f"u_{d}_{j}"], weight[d] / demand[d][j])

    # optional allocation-cost term
    if lam: # if lam neq 0
        for d in ("urban", "agri"):
            for i in I:
                for j in J:
                    qubo.add_linear([f"x_{d}_{i}_{j}"], lam * c[(i, j)])

    # demand balance: sum_i x_{i,j}^d + u_j^d = D_j^d
    for d in ("urban", "agri"):
        for j in J:
            names = [f"x_{d}_{i}_{j}" for i in I] + [f"u_{d}_{j}"]
            qubo.add_penalty(names, demand[d][j], penalty)

    # source capacity: sum_{j,d} x_{i,j}^d + cap_i = A_eff_i
    for i in I:
        names = [f"x_{d}_{i}_{j}" for d in ("urban", "agri") for j in J] + [f"cap_{i}"]
        qubo.add_penalty(names, A[i], penalty)

    qubo.meta = {"scenario": scenario, "B": B, "lam": lam, "penalty": penalty}
    return qubo


def decode(qubo, bitvec, scenario):
    """Turn a bitstring into allocations, unmet demand, NWWD and feasibility."""
    inst = instance(scenario)
    I, J = inst["source_names"], inst["municipalities"]
    Du, Da = inst["urban_demand"], inst["agri_demand"]
    demand = {"urban": Du, "agri": Da}
    weight = {"urban": inst["w_urban"], "agri": inst["w_agri"]}
    A = inst["sources"]

    unmet = {(d, j): qubo.value(f"u_{d}_{j}", bitvec)
             for d in ("urban", "agri") for j in J}
    nwwd = sum(weight[d] * unmet[(d, j)] / demand[d][j]
               for d in ("urban", "agri") for j in J)

    resid = []
    for d in ("urban", "agri"):
        for j in J:
            served = sum(qubo.value(f"x_{d}_{i}_{j}", bitvec) for i in I)
            resid.append(abs(served + unmet[(d, j)] - demand[d][j]))
    for i in I:
        used = sum(qubo.value(f"x_{d}_{i}_{j}", bitvec)
                   for d in ("urban", "agri") for j in J)
        resid.append(max(0, used - A[i]))
    return {
        "NWWD": nwwd,
        "unmet": {f"{d}_{j}": v for (d, j), v in unmet.items() if v > 1e-9},
        "max_residual": max(resid),
        "feasible": max(resid) < 1e-6,
    }


def brute_force(qubo):
    """Exhaustively minimize energy. Only for <= ~40 qubits. (USING QPU SIMULATOR)""" 
    n = qubo.num_qubits
    if n > 40:
        raise ValueError(f"{n} qubits is too many to brute force")
    best = None
    for combo in itertools.product((0, 1), repeat=n):
        e = qubo.energy(combo)
        if best is None or e < best[0]:
            best = (e, combo)
    return best


def build_reduced_qubo(B=5, penalty=200.0):
    """A tiny, brute-forceable problem that exercises the same QUBO machinery.

    1 source (cap 15), 2 urban municipalities (demand 10 and 15), urban only.
    Optimal: serve the high-priority small one fully -> NWWD = 10*(10/15) = 6.667.
    """
    wU = 10
    D = {"A": 10, "B": 15}
    cap = 15
    q = QUBO()
    for j in D:
        q.add_variable(f"x_S_{j}", min(D[j], cap), B)
        q.add_variable(f"u_{j}", D[j], B)
    q.add_variable("cap_S", cap, B)
    for j in D:
        q.add_linear([f"u_{j}"], wU / D[j])
    for j in D:
        q.add_penalty([f"x_S_{j}", f"u_{j}"], D[j], penalty)
    q.add_penalty([f"x_S_{j}" for j in D] + ["cap_S"], cap, penalty)
    return q, D, wU


if __name__ == "__main__":
    if "--toy" in sys.argv:
        q, D, wU = build_reduced_qubo(B=5)
        print(f"Reduced check: {q.num_qubits} qubits, brute-forcing...")
        e, combo = brute_force(q)
        served = {j: q.value(f"x_S_{j}", combo) for j in D}
        unmet = {j: q.value(f"u_{j}", combo) for j in D}
        nwwd = sum(wU * unmet[j] / D[j] for j in D)
        print(f"  min energy : {e:.4f}")
        print(f"  served     : {served}")
        print(f"  unmet      : {unmet}")
        print(f"  NWWD       : {nwwd:.4f}   (expected 6.6667)")
        assert abs(nwwd - 6.6667) < 1e-3, "QUBO machinery FAILED sanity check"
        print("  OK: QUBO machinery reproduces the priority-optimal allocation.")
    else:
        for B in (20, 10, 5):
            for s in ("Normal", "Moderate", "Severe"):
                q = build_qubo(s, B=B)
                print(f"B={B:2d}  {s:9s}  qubits={q.num_qubits}  penalty={q.meta['penalty']}")
