# Presentation — Quantum Water Allocation (Beamer)

7-minute deck for Hackathon LATAM 2026. Slides in English.

## Build
```
pdflatex main.tex
pdflatex main.tex      # run twice so slide numbers resolve
```
Works locally or on Overleaf (engine: pdfLaTeX). Only standard packages
(tikz, xcolor, booktabs, amsmath).

## Before you present — two things to fill
1. **Logo.** Drop the Logarithm logo at `figs/logo.png`. The title slide loads
   it automatically; without it a text placeholder is shown.
2. **Results table (slide "Benchmarking II").** Cells `QAOA NWWD`, `feasible`,
   `runtime` are blank (`__`) — fill them from tonight's simulator runs. Qubit
   counts are already exact. The runtime plot on "Benchmarking I" is the
   expected `p·2ⁿ` cost model; overlay measured `(B,p)` points when ready.

## Figures (regenerated from the repo, not hand-drawn)
| file | what it shows | source |
|------|---------------|--------|
| `lambda_justification.png` | NWWD & delivery cost vs λ (3 scenarios); dominance bound 10/95 | MILP sweep, `milp/baseline.py` |
| `nwwd_heatmap.png` | NWWD decomposed by user — all deficit on Puebla urban | MILP optimum |
| `qubits_vs_B.png` | real QUBO qubit counts vs block size B | `qubo/builder.py` |
| `runtime_model.png` | expected statevector cost p·2ⁿ vs B | qubit counts |

## λ = 0.1 justification (slide 7)
Human priority is preserved iff λ < (w_d/D_j)/c_ij on every served edge. The
binding edge is Puebla-urban via Valle de Puebla: λ_max = w_u/D_Pue = 10/95 ≈
0.105. MILP sweep confirms Severe keeps the exact optimum up to λ* = 0.106.
λ = 0.1 is the largest round value below the ceiling: keeps human demand first
in the worst-case drought, maximizes cost-regularization, and lifts the λ=0
degeneracy (unique min-cost allocation → better-conditioned QAOA).

## Slide order (12 frames)
title · problem/SDG · MILP baseline · NWWD color map · QUBO · Ising+QAOA ansatz ·
λ=0.1 · scaling · results · critiques+AI · takeaway · **backup** (hierarchical QAOA).

Rubric coverage: Problem (2,4) · Baseline (3) · Quantum impl. (5,6) ·
Benchmarking (8,9) · Presentation quality (10,11) · AI use (10).
