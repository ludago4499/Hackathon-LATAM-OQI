# Two-stage hierarchical QAOA with bound tightening — results

**Idea (yours).** Run a coarse QAOA at block size `B0=20`, take a round-down /
round-up window around its solution per variable, conclude the optimum lies in
that smaller range, then re-encode each variable over the narrowed range with
`bits = max(1, ceil(log2(n_blocks - lower_bound + 1)))` (offset / warm-start
encoding `x = lower + B*sum_k 2^k b_k`) to cut qubits and tighten the QAOA
landscape.

**Status of the code first.** The repo did not run: `qubo/builder.py`,
`milp/baseline.py` and `qaoa/solver.py` were all truncated mid-function (the
Windows-mounted folder was serving inconsistent reads and a stale `.pyc` was
masking it). Repaired all three, completed `decode()`, `run_qaoa()`'s return,
and `baseline.py` (MILP optima re-verified: Normal 2.526 / Moderate 5.158 /
Severe 7.789). Added offset encoding to the QUBO (`add_variable(..., lower_bound)`
+ `build_qubo(..., bounds=...)`); verified energy-invariant (a fixed physical
allocation has identical QUBO energy under full vs tightened encoding, dE=0).

**Metric.** The stock `decode()` uses a loose tolerance (`tol = B = 20`) and
scores unmet only from the slack variable, so a solution can score NWWD=0 by
simply under-serving within a block. Results below use a physical score:
`unmet_j = max(0, demand_j - served_j)` vs real demand, feasible iff source
capacity is respected. `fullCeil`/`redCeil` are the *exact* best achievable
(brute force) over the full vs bracketed search space — the method's ceiling,
independent of QAOA quality. `valid` = the bracket did not raise that ceiling
(i.e. it still contains the optimum).

Model: urban-only, unbalanced capacity. `opt` = continuous LP optimum.

| scen | B1 | margin | fullQ | redQ | saved | opt | coarseQAOA | refQAOA | fullCeil | redCeil | bracket valid |
|------|----|--------|-------|------|-------|-----|-----------|---------|----------|---------|---------------|
| Severe   | 20 | 0 | 12 | 9  | 3  | 4.53 | 7.89 | 7.89 | 7.89 | 7.89 | True |
| Severe   | 20 | 1 | 12 | 11 | 1  | 4.53 | 7.89 | 7.89 | 7.89 | 7.89 | True |
| Severe   | 10 | 0 | 15 | 9  | 6  | 4.53 | 7.89 | 7.89 | 6.84 | 7.89 | **False** |
| Severe   | 10 | 1 | 15 | 14 | 1  | 4.53 | 7.89 | 7.59 | 6.84 | 6.84 | True |
| Severe   | 5  | 0 | 24 | 9  | 15 | 4.53 | 7.89 | 7.89 | n/a  | 6.84 | n/a |
| Moderate | 10 | 0 | 16 | 9  | 7  | 1.89 | 5.79 | 4.74 | 3.68 | inf  | **False** |
| Moderate | 10 | 1 | 16 | 15 | 1  | 1.89 | 5.79 | 5.49 | 3.68 | 3.68 | True |
| Normal   | 10 | 0 | 17 | 9  | 8  | 0.00 | 10.0 | 10.0 | n/a  | 10.0 | n/a |
| Normal   | 10 | 1 | 17 | 13 | 4  | 0.00 | 10.0 | 2.86 | n/a  | 0.53 | n/a |

## Conclusions

1. **The idea is correct, conditionally.** With a one-coarse-block margin
   (`margin=1`) the bracket is *valid in every case we could check*
   (`redCeil == fullCeil`): the optimum really does sit inside the round-down /
   round-up range. So the premise "the optimum is within that range" holds — at
   margin 1.

2. **Qubit saving and validity are in direct tension.** Big savings need
   aggressive pinning (`margin=0`: 15→9, 24→9 qubits), but margin=0 repeatedly
   makes the bracket **invalid** (Severe B1=10: best-in-bracket 7.89 vs true
   6.84; Moderate B1=10: *no feasible point in the bracket at all*). At the safe
   `margin=1`, the saving is usually just 1 qubit, because ±1 coarse block is a
   wide window at a finer grid.

3. **The coarse QAOA's own error is the dominant failure mode**, not the
   encoding or discretization. The bracket is anchored on the coarse solution;
   when that is bad (Normal coarse = 10.0 vs optimum 0.0) the bracket is centred
   in the wrong place. margin=0 then locks you into the bad region; margin=1
   partly rescues it.

4. **Best case is genuinely strong.** Severe at B1=5: the full B=5 problem is 24
   qubits (impractical to simulate exactly here), but the bracketed problem is
   **9 qubits** and reaches the same 6.84 optimum as B=10. Bracketing unlocks a
   resolution you otherwise can't run.

5. **Discretization gap is large at B=20** (exact best 7.89 vs LP 4.53), so
   refining to finer B is worth it; the bracket is what makes finer B affordable.

## Recommendations
- Build the bracket from the **distribution** of low-energy coarse samples
  (per-variable min/max over the top-k bitstrings), not one sample — tighter than
  ±1 block, safer than margin=0.
- **Validate the bracket against the LP relaxation** (we already solve it): check
  the LP optimum falls inside before committing. This catches the margin=0
  failures for free and is a clean hybrid (LP says where, QAOA refines).
- Spend budget on the **coarse stage** (higher p / more restarts, or seed it from
  the LP), since everything downstream inherits its error.

Run: `python -m qaoa.hierarchical --scenario Severe --B0 20 --B1 10 --margin 1`
