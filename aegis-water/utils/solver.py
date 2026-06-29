"""
utils/solver.py
Núcleo del modelo MILP para AEGIS Water — SDG 6.4
Resuelve el problema de asignación hídrica con scipy.optimize.linprog
"""
import numpy as np
from scipy.optimize import linprog
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd

# ── Datos del benchmark (Annex A del Guided Challenge) ────────────────────────

SOURCES = {
    "Valle de Puebla":    {"base_avail": 80.0, "type": "Groundwater"},
    "Atlixco-Izúcar":     {"base_avail": 45.0, "type": "Groundwater"},
}

MUNICIPALITIES = {
    "Puebla":         {"urban": 95.0, "agri": 8.0},
    "S.A. Cholula":   {"urban": 14.0, "agri": 5.0},
    "Atlixco":        {"urban":  9.0, "agri": 18.0},
}

# Costos cij [fuente][municipio]
COSTS = {
    "Valle de Puebla": {"Puebla": 1.0, "S.A. Cholula": 1.2, "Atlixco": 2.5},
    "Atlixco-Izúcar":  {"Puebla": 2.8, "S.A. Cholula": 2.0, "Atlixco": 1.0},
}

SCENARIOS = {
    "Normal":           1.00,
    "Sequía moderada":  0.80,
    "Sequía severa":    0.60,
}

WEIGHTS = {"wU": 10.0, "wA": 3.0}

SOURCES_LIST = list(SOURCES.keys())
MUNS_LIST    = list(MUNICIPALITIES.keys())
nI = len(SOURCES_LIST)   # 2 fuentes
nJ = len(MUNS_LIST)      # 3 municipios

@dataclass
class SolverResult:
    status: str
    nwwd: float
    x_urban: np.ndarray    # (nI, nJ)
    x_agri:  np.ndarray    # (nI, nJ)
    u_urban: np.ndarray    # (nJ,)
    u_agri:  np.ndarray    # (nJ,)
    unmet_urban_norm: float
    unmet_agri_norm:  float
    runtime_ms: float
    alpha: float


def solve_milp(alpha: float, wU: float = 10.0, wA: float = 3.0,
               lam: float = 0.0) -> SolverResult:
    """
    Resuelve el MILP de asignación hídrica.

    Variables (todas continuas, no-negativas):
        x_urban[i,j] : vol. asignado fuente i → demanda urbana municipio j
        x_agri[i,j]  : vol. asignado fuente i → demanda agrícola municipio j
        u_urban[j]   : déficit urbano municipio j
        u_agri[j]    : déficit agrícola municipio j

    Total variables: 2*nI*nJ + 2*nJ = 2*6 + 6 = 18
    """
    import time
    t0 = time.time()

    D_urb = np.array([MUNICIPALITIES[j]["urban"] for j in MUNS_LIST])
    D_agr = np.array([MUNICIPALITIES[j]["agri"]  for j in MUNS_LIST])
    A_eff = np.array([SOURCES[i]["base_avail"] * alpha for i in SOURCES_LIST])

    # Variable layout:
    # [x_urb(0,0), x_urb(0,1), x_urb(0,2),   <- fuente 0, urbano
    #  x_urb(1,0), x_urb(1,1), x_urb(1,2),   <- fuente 1, urbano
    #  x_agr(0,0), x_agr(0,1), x_agr(0,2),
    #  x_agr(1,0), x_agr(1,1), x_agr(1,2),
    #  u_urb(0), u_urb(1), u_urb(2),
    #  u_agr(0), u_agr(1), u_agr(2)]
    # Total: nI*nJ*2 + nJ*2 = 12 + 6 = 18

    n_xu = nI * nJ   # 6
    n_xa = nI * nJ   # 6
    n_uu = nJ        # 3
    n_ua = nJ        # 3
    n_vars = n_xu + n_xa + n_uu + n_ua  # 18

    idx_xu = lambda i,j: i*nJ + j
    idx_xa = lambda i,j: n_xu + i*nJ + j
    idx_uu = lambda j:   n_xu + n_xa + j
    idx_ua = lambda j:   n_xu + n_xa + n_uu + j

    # ── Objective ─────────────────────────────────────────────────────────────
    c = np.zeros(n_vars)
    for j in range(nJ):
        c[idx_uu(j)] = wU / D_urb[j]   # penaliza déficit urbano normalizado
        c[idx_ua(j)] = wA / D_agr[j]   # penaliza déficit agrícola normalizado
    # costo de distribución (opcional, λ)
    if lam > 0:
        for i, src in enumerate(SOURCES_LIST):
            for j, mun in enumerate(MUNS_LIST):
                cij = COSTS[src][mun]
                c[idx_xu(i,j)] += lam * cij
                c[idx_xa(i,j)] += lam * cij

    # ── Inequality constraints (A_ub @ x <= b_ub) ────────────────────────────
    # Restricción de capacidad: sum_j (x_urb[i,j] + x_agr[i,j]) <= A_eff[i]
    A_ub = np.zeros((nI, n_vars))
    b_ub = np.zeros(nI)
    for i in range(nI):
        for j in range(nJ):
            A_ub[i, idx_xu(i,j)] = 1.0
            A_ub[i, idx_xa(i,j)] = 1.0
        b_ub[i] = A_eff[i]

    # ── Equality constraints (A_eq @ x == b_eq) ──────────────────────────────
    # Balance urbano: sum_i x_urb[i,j] + u_urb[j] = D_urb[j]
    # Balance agrícola: sum_i x_agr[i,j] + u_agr[j] = D_agr[j]
    n_eq = 2 * nJ
    A_eq = np.zeros((n_eq, n_vars))
    b_eq = np.zeros(n_eq)

    for j in range(nJ):
        # Urbano
        for i in range(nI):
            A_eq[j, idx_xu(i,j)] = 1.0
        A_eq[j, idx_uu(j)] = 1.0
        b_eq[j] = D_urb[j]
        # Agrícola
        for i in range(nI):
            A_eq[nJ + j, idx_xa(i,j)] = 1.0
        A_eq[nJ + j, idx_ua(j)] = 1.0
        b_eq[nJ + j] = D_agr[j]

    bounds = [(0, None)] * n_vars

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method='highs')

    rt = (time.time() - t0) * 1000

    if res.status != 0:
        return SolverResult("INFEASIBLE", float('inf'),
                            np.zeros((nI,nJ)), np.zeros((nI,nJ)),
                            np.zeros(nJ), np.zeros(nJ), 1.0, 1.0, rt, alpha)

    x = res.x
    xu = x[:n_xu].reshape(nI, nJ)
    xa = x[n_xu:n_xu+n_xa].reshape(nI, nJ)
    uu = x[n_xu+n_xa:n_xu+n_xa+n_uu]
    ua = x[n_xu+n_xa+n_uu:]

    nwwd = (wU * np.sum(uu / D_urb) + wA * np.sum(ua / D_agr))
    uu_norm = float(np.sum(uu / D_urb) / nJ)
    ua_norm = float(np.sum(ua / D_agr) / nJ)

    return SolverResult(
        status="OPTIMAL", nwwd=round(nwwd, 6),
        x_urban=xu, x_agri=xa, u_urban=uu, u_agri=ua,
        unmet_urban_norm=round(uu_norm, 4),
        unmet_agri_norm=round(ua_norm, 4),
        runtime_ms=round(rt, 2), alpha=alpha
    )


def solve_all_scenarios(wU=10.0, wA=3.0, lam=0.0) -> Dict[str, SolverResult]:
    return {name: solve_milp(alpha, wU, wA, lam)
            for name, alpha in SCENARIOS.items()}


def result_to_dataframe(r: SolverResult) -> pd.DataFrame:
    """Tabla de asignación fuente x municipio."""
    rows = []
    for i, src in enumerate(SOURCES_LIST):
        for j, mun in enumerate(MUNS_LIST):
            rows.append({
                "Fuente": src,
                "Municipio": mun,
                "Asig. Urbana (hm³)": round(r.x_urban[i,j], 3),
                "Asig. Agrícola (hm³)": round(r.x_agri[i,j], 3),
                "Costo c_ij": COSTS[src][mun],
            })
    return pd.DataFrame(rows)
