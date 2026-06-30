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
      python -m qubo.builder --toy     # brute-force sanity check (removed)
"""
import sys, os, itertools, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.instance import instance


def _bits_for(upper_bound, B,lower_bound=0):
    """Number of bits needed to represent lower_bound(0)    ..upper_bound in steps of B."""
    n_blocks = int(upper_bound // B)
    return max(1, int(math.ceil(math.log2(n_blocks-lower_bound + 1))))


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

    def add_inequality_unbalanced(self, names, bound, l1, l2):
        """Add a SLACK-FREE penalty for the inequality  sum(values) <= bound.

        Unbalanced penalization (Montanez-Barrera et al. 2022): instead of a
        slack variable, add  l1*(S - bound) + l2*(S - bound)^2  with S = sum of
        the named values. Expanding (b_k^2 = b_k for binaries) gives diagonal and
        pairwise terms only. The minimum sits at S* = bound - l1/(2*l2), i.e. just
        below capacity, and overuse (S > bound) is penalised quadratically. Costs
        ZERO extra qubits versus the slack-variable equality form.
        """
        terms = self._terms(names)
        self.offset += -l1 * bound + l2 * bound ** 2
        for (i, wi) in terms:
            self._add(i, i, l1 * wi - 2 * l2 * bound * wi + l2 * wi * wi)
            for (j, wj) in terms:
                if j > i:
                    self._add(i, j, 2 * l2 * wi * wj)

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


def build_qubo(scenario, B=10, lam=0.0, penalty=None, urban_only=False,
               cap_mode="slack", l1=None, l2=None):
    """Build the QUBO for one drought scenario.

    B          : block size in hm^3 (smaller = more accurate, more qubits)
    lam        : weight on allocation cost (benchmark uses 0)
    penalty    : constraint penalty P. If None, a heuristic value is chosen.
    urban_only : if True, drop the agri demand type entirely. Removes all
                 x_agri_* and u_agri_* variables and the agri balance penalties,
                 leaving an urban-only objective and constraints (fewer qubits).
    cap_mode   : "slack"      -> source capacity as an equality with a slack
                                 variable cap_i (default, original behaviour).
                 "unbalanced" -> source capacity as a slack-FREE inequality via
                                 unbalanced penalization. Saves the cap_i qubits.
    l1, l2     : coefficients for the unbalanced capacity term. Defaults
                 l2 = penalty, l1 = penalty * B  (penalty minimum ~B/2 below cap).
    """
    inst = instance(scenario)
    I, J = inst["source_names"], inst["municipalities"]
    Du, Da = inst["urban_demand"], inst["agri_demand"]
    A, c = inst["sources"], inst["cost"]
    wU, wA = inst["w_urban"], inst["w_agri"]
    # Snap every hm^3 quantity to the nearest block of B BEFORE building the
    # QUBO, so demand/capacity land exactly on the encoding grid (zero balance
    # residual). Anything rounding to 0 is bumped to one block (B) so no
    # demand/source disappears and the NWWD denominator is never zero.
    def _snap(v):
        s = int(math.floor(v / B + 0.5)) * B   # nearest multiple, ties round up
        return s if s > 0 else B               # 0 -> one block
    Du = {j: _snap(v) for j, v in Du.items()}
    Da = {j: _snap(v) for j, v in Da.items()}
    A  = {i: _snap(v) for i, v in A.items()}

    demand = {"urban": Du, "agri": Da}
    weight = {"urban": wU, "agri": wA}
    dtypes = ("urban",) if urban_only else ("urban", "agri")

    if penalty is None:
        # Penalty per one-block (B hm^3) constraint violation should be a fixed
        # multiple of the largest objective gain that block could buy, for ANY B.
        # Worst objective gain per hm^3 is max_{d,j} (w_d / D_j^d); times B is the
        # gain per block. Setting P * B^2 = C_FEAS * (gain per block) keeps the
        # feasible region as the ground state with margin C_FEAS, independent of B:
        #     P = C_FEAS * max(w_d / D_j^d) / B
        # This is ~B^2 smaller than the old flat P=500, which dwarfed the NWWD
        # term and blinded QAOA (penalty coeffs were ~200,000x the objective).
        C_FEAS = 10.0
        g_max = max(weight[d] / demand[d][j]
                    for d in dtypes for j in J)
        penalty = C_FEAS * g_max / B
    if l2 is None:
        l2 = penalty
    if l1 is None:
        l1 = penalty * B

    qubo = QUBO()

    for d in dtypes:
        for i in I:
            for j in J:
                ub = min(demand[d][j], A[i])
                qubo.add_variable(f"x_{d}_{i}_{j}", ub, B)
    for d in dtypes:
        for j in J:
            qubo.add_variable(f"u_{d}_{j}", demand[d][j], B)
    if cap_mode == "slack":
        for i in I:
            qubo.add_variable(f"cap_{i}", A[i], B)

    # objective: NWWD = sum_d w_d * sum_j u_j^d / D_j^d
    for d in dtypes:
        for j in J:
            qubo.add_linear([f"u_{d}_{j}"], weight[d] / demand[d][j])

    # optional allocation-cost term
    if lam: # if lam neq 0
        for d in dtypes:
            for i in I:
                for j in J:
                    qubo.add_linear([f"x_{d}_{i}_{j}"], lam * c[(i, j)])

    # demand balance: sum_i x_{i,j}^d + u_j^d = D_j^d
    for d in dtypes:
        for j in J:
            names = [f"x_{d}_{i}_{j}" for i in I] + [f"u_{d}_{j}"]
            qubo.add_penalty(names, demand[d][j], penalty)

    # source capacity: sum_{j,d} x_{i,j}^d <= A_eff_i
    for i in I:
        names = [f"x_{d}_{i}_{j}" for d in dtypes for j in J]
        if cap_mode == "slack":
            # equality with slack:  sum x + cap_i = A_eff_i
            qubo.add_penalty(names + [f"cap_{i}"], A[i], penalty)
        elif cap_mode == "unbalanced":
            # slack-free inequality:  sum x <= A_eff_i
            qubo.add_inequality_unbalanced(names, A[i], l1, l2)
        else:
            raise ValueError(f"unknown cap_mode {cap_mode!r}")

    qubo.meta = {"scenario": scenario, "B": B, "lam": lam, "penalty": penalty,
                 "urban_only": urban_only, "cap_mode": cap_mode,
                 "dtypes": dtypes, "l1": l1, "l2": l2}
    return qubo


def decode(qubo, bitvec, scenario, tol=None):
    """Turn a bitstring into allocations, unmet demand, NWWD and feasibility.

    Because every variable is a multiple of the block size B, each equality
    constraint (which sums multiples of B) can only land on a multiple of B and
    therefore meets a non-multiple demand to within at most one block. `tol` is
    that discretization slack, applied to BOTH the demand-balance equalities and
    the source-capacity inequalities. It defaults to B (read from qubo.meta).

    tol = B guarantees a feasible solution always exists for any B: the all-unmet
    allocation (x = 0, every slack u = floor(D/B)*B) leaves each balance residual
    D mod B < B and zero capacity overuse. Pass tol explicitly to tighten it
    (e.g. tol = B/2 for nearest-block rounding) or loosen it.
    """
    inst = instance(scenario)
    I, J = inst["source_names"], inst["municipalities"]
    Du, Da = inst["urban_demand"], inst["agri_demand"]
    A = inst["sources"]

    # Snap to the same block grid the QUBO was built on (see build_qubo), so the
    # residual/NWWD targets match the encoding exactly.
    B = float(getattr(qubo, "meta", {}).get("B", 0.0))
    if B > 0:
        def _snap(v):
            s = int(math.floor(v / B + 0.5)) * B
            return s if s > 0 else B
        Du = {j: _snap(v) for j, v in Du.items()}
        Da = {j: _snap(v) for j, v in Da.items()}
        A  = {i: _snap(v) for i, v in A.items()}

    demand = {"urban": Du, "agri": Da}
    weight = {"urban": inst["w_urban"], "agri": inst["w_agri"]}

    if tol is None:                       # default slack = one block
        tol = B or 1e-6

    # demand types actually present in this QUBO (urban-only drops "agri")
    dtypes = tuple(getattr(qubo, "meta", {}).get("dtypes", ("urban", "agri")))

    unmet = {(d, j): qubo.value(f"u_{d}_{j}", bitvec)
             for d in dtypes for j in J}
    nwwd = sum(weight[d] * unmet[(d, j)] / demand[d][j]
               for d in dtypes for j in J)

    # demand balance (equality):  served + unmet == demand
    balance_resid = []
    for d in dtypes:
        for j in J:
            served = sum(qubo.value(f"x_{d}_{i}_{j}", bitvec) for i in I)
            balance_resid.append(abs(served + unmet[(d, j)] - demand[d][j]))
    # source capacity (inequality):  used <= A_eff  (only overuse is a violation)
    capacity_resid = []
    for i in I:
        used = sum(qubo.value(f"x_{d}_{i}_{j}", bitvec)
                   for d in dtypes for j in J)
        capacity_resid.append(max(0.0, used - A[i]))

    max_residual = max(balance_resid + capacity_resid)
    return {
        "NWWD": nwwd,
        "unmet": {f"{d}_{j}": v for (d, j), v in unmet.items() if v > 1e-9},
        "max_balance_residual": max(balance_resid),
        "max_capacity_residual": max(capacity_resid),
        "max_residual": max_residual,
        "tol": tol,
        "feasible": max_residual <= tol + 1e-9,
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

if __name__ == "__main__":
    for B in (20, 10, 5):
        for s in ("Normal", "Moderate", "Severe"):
            q = build_qubo(s, B=B)
            print(f"B={B:2d}  {s:9s}  qubits={q.num_qubits}  penalty={q.meta['penalty']}")
