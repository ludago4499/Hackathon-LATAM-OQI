# Team 11 — Sustainable Water Allocation in the Alto Atoyac Basin (SDG 6.4)

Quantum Hackathon LATAM. We minimize the **Normalized Weighted Water Deficit
(NWWD)** for water allocation across the Puebla portion of the Alto Atoyac
Basin under drought, and compare a classical **MILP** baseline against a
**QUBO / QAOA** quantum formulation.

The goal of the challenge is **not** to beat MILP — current hardware won't — but
to assess whether this problem's structure suits quantum optimization.

## The objective in one line

**NWWD = 10 × (total % urban demand unmet) + 3 × (total % agricultural demand unmet).**
Lower is better. The weights (10 vs 3) encode that unmet human consumption is
penalized more than unmet agriculture.

## Key fact about the instance

Total demand is 149 hm³/yr but max supply is 125 (Normal), 100 (Moderate),
75 (Severe). **Supply never meets demand** — the optimizer decides *who is cut*.
Because the deficit is normalized per category and Puebla's urban demand (95) is
huge, Puebla urban has the lowest marginal value per hm³, so the optimum
concentrates the entire shortfall there.

## Validated baseline (MILP, λ = 0) — our target numbers

| Scenario | Availability | NWWD (optimal) | Unmet |
|----------|-------------:|---------------:|-------|
| Normal   | 125 | **2.526** | Puebla urban 24 |
| Moderate | 100 | **5.158** | Puebla urban 49 |
| Severe   |  75 | **7.789** | Puebla urban 74 |

If QAOA lands near these, it works.

## Repo layout

```
team11-atoyac-water-qaoa/
├── data/instance.py     # Annex A benchmark — SINGLE SOURCE OF TRUTH
├── milp/baseline.py     # classical LP/MILP baseline (ground truth)
├── qubo/builder.py      # discretization + QUBO + brute-force validator
├── qaoa/solver.py       # QAOA starter (PennyLane)
├── backend.py           # the ONLY place that picks simulator/hardware
├── run.py               # entrypoint: MILP + QUBO check (+ --qaoa)
├── results/             # output tables / plots
└── requirements.txt
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py            # MILP baseline + QUBO sanity check
python run.py --qaoa     # also run the QAOA starter (needs pennylane)
```

Individual modules:
```bash
python -m data.instance        # demand vs supply per scenario
python -m milp.baseline        # the three validated NWWD values
python -m qubo.builder         # full-instance qubit counts
python -m qubo.builder --toy   # brute-force sanity check (reproduces NWWD 6.667)
```

## How the QUBO works (the one trick)

Each continuous allocation `x[i,j,d]` (source i → municipality j, demand type d)
is **discretized into blocks of B hm³**, encoded in binary. The **unmet demand
is a slack variable**, so demand balance `Σ_i x + u = D` becomes a quadratic
penalty — and the QUBO objective is then literally the NWWD. Source capacity
uses a capacity-slack the same way.

Block size **B** is the key knob: smaller B = more accurate, more qubits.

| Block size B | Qubits (per scenario) |
|-------------:|----------------------:|
| 20 hm³ | ~28 |
| 10 hm³ | ~33 |
|  5 hm³ | ~44 |

Start at B=20 on a simulator; shrink B as resources allow.

## QCentroid

Local repo = what runs on QCentroid. `git clone` into the **Launchpad** Jupyter
environment, `pip install -r requirements.txt`, run. Backend choice lives only in
`backend.py` — switch local simulator → GPU sim → real QPU by changing the
device name (or env vars `QAOA_FRAMEWORK` / `QAOA_DEVICE`), no logic changes.

## Deliverables checklist (Annex B)

For each of Normal / Moderate / Severe, report: NWWD, allocation decisions,
unmet urban + agri (raw and normalized), feasibility, runtime, and number of
binary variables in the QUBO. Compare MILP vs QUBO(brute) vs QAOA.

## Workflow / ownership

- **data/** — commit first; everyone builds against the same instance.
- **milp/** — owner A (ground truth + plots).
- **qubo/ + qaoa/** — owners B/C (formulation, penalty tuning, QAOA).
- **report** — owner D (assemble the Annex B table + slides).

Short-lived branches + quick PRs, or commit to `main` for speed.
