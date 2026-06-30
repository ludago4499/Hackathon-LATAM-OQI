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
        self.var_offset = {}     # var name -> constant hm3 offset (lower bound)
        self._n = 0

    def add_variable(self, name, upper_bound, B, lower_bound=0):
        # Offset (warm-start) encoding: value = lower_bound + B*sum_k 2^k b_k.
        # lower_bound is in hm^3 and should be a multiple of B. Bit count is
        # _bits_for over the TIGHTENED block range [lower_bound/B .. upper_bound/B],
        # so a narrow [lower, upper] window costs far fewer qubits.
        self.var_offset[name] = lower_bound
        bits = []
        for k in range(_bits_for(upper_bound, B, int(lower_bound // B))):
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

    def _offset_sum(self, names):
        return sum(self.var_offset.get(nm, 0.0) for nm in names)

    def add_linear(self, names, scale):
        """Add  scale * sum(values)  to the objective (diagonal terms)."""
        self.offset += scale * self._offset_sum(names)
        for (idx, w) in self._terms(names):
            self._add(idx, idx, scale * w)

    def add_penalty(self, names, constant, P):
        """Add  P * (sum(values) - constant)^2  to the objective."""
        constant = constant - self._offset_sum(names)   # fold in variable offsets
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
        bound = bound - self._offset_sum(names)          # fold in variable offsets
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
        return self.var_offset.get(name, 0.0) + sum(
            w for (idx, w) in self.registry[name] if bitvec[idx])

    def energy(self, bitvec):
        e = self.offset
        for (p, q), v in self.Q.items():
            if bitvec[p] and bitvec[q]:
                e += v
        return e


def build_qubo(scenario, B=10, lam=0.0, penalty=None, urban_only=False,
               cap_mode="slack", l1=None, l2=None, bounds=None):
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
        #
        # C_FEAS: the visible objective/penalty ratio QAOA sees scales as
        # 1/C_FEAS, so a large value re-buries the NWWD signal and shallow QAOA
        # parks on the trivial all-unmet feasible state. The theoretical
        # feasibility floor is C_FEAS = 1 (worst case); empirically, brute-forcing
        # every <=24-qubit scenario/B (urban-only and with agri) the ground state
        # stays feasible down to ~0.1, and the decode tol=B slack lets the optimum
        # sit at residual<B without exact-equality over-constraining. C_FEAS = 0.3
        # is the chosen operating point: it restores the signal (p=2 QAOA finds
        # NWWD=0 on Normal/B=20/urban-only) while keeping a feasibility margin on
        # all brute-checked instances. Going below ~0.1 makes the ground state
        # infeasible (e.g. Severe/B=10/urban-only), so do not lower it further
        # without re-verifying feasibility for the instance at hand.
        C_FEAS = 0.3
        g_max = max(weight[d] / demand[d][j]
                    for d in dtypes for j in J)
        penalty = C_FEAS * g_max / B
    if l2 is None:
        l2 = penalty
    if l1 is None:
        l1 = penalty * B

    qubo = QUBO()

    def _bnd(nm, default_ub):
        # tightened (lower, upper) for a variable, snapped to the B-grid;
        # defaults to the full [0, default_ub] when no bound is supplied.
        if bounds and nm in bounds:
            lo, hi = bounds[nm]
            lo = max(0, int(math.floor(lo / B)) * B)
            hi = min(default_ub, int(math.ceil(hi / B)) * B)
            if hi < lo:
                hi = lo
            return lo, hi
        return 0, default_ub

    for d in dtypes:
        for i in I:
            for j in J:
                ub = min(demand[d][j], A[i])
                nm = f"x_{d}_{i}_{j}"; lo, hi = _bnd(nm, ub)
                qubo.add_variable(nm, hi, B, lower_bound=lo)
    for d in dtypes:
        for j in J:
            nm = f"u_{d}_{j}"; lo, hi = _bnd(nm, demand[d][j])
            qubo.add_variable(nm, hi, B, lower_bound=lo)
    if cap_mode == "slack":
        for i in I:
            nm = f"cap_{i}"; lo, hi = _bnd(nm, A[i])
            qubo.add_variable(nm, hi, B, lower_bound=lo)

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
    inst = instance(scenario)
    I, J = inst["source_names"], inst["municipalities"]
    Du, Da = inst["urban_demand"], inst["agri_demand"]
    demand = {"urban": Du, "agri": Da}
    weight = {"urban": inst["w_urban"], "agri": inst["w_agri"]}
    A = inst["sources"]
    if tol is None:
        tol = float(getattr(qubo, "meta", {}).get("B", 0.0)) or 1e-6
    dtypes = tuple(getattr(qubo, "meta", {}).get("dtypes", ("urban", "agri")))
    unmet = {(d, j): qubo.value(f"u_{d}_{j}", bitvec) for d in dtypes for j in J}
    nwwd = sum(weight[d] * unmet[(d, j)] / demand[d][j] for d in dtypes for j in J)
    balance_resid = []
    for d in dtypes:
        for j in J:
            served = sum(qubo.value(f"x_{d}_{i}_{j}", bitvec) for i in I)
            balance_resid.append(abs(served + unmet[(d, j)] - demand[d][j]))
    capacity_resid = []
    for i in I:
        used = sum(qubo.value(f"x_{d}_{i}_{j}", bitvec) for d in dtypes for j in J)
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
