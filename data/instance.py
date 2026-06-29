"""
Benchmark instance for the SDG 6.4 Guided Challenge:
Sustainable Water Allocation in the Alto Atoyac Basin Under Drought Scenarios.

All values are taken directly from Annex A of the challenge document.
This is the SINGLE SOURCE OF TRUTH for the instance. The MILP, QUBO, and QAOA
modules must all import from here so the comparison stays valid.

Units: hm^3 / year (cubic hectometers per year).
"""

# --- A.2 Municipalities: demand (hm^3/year) -------------------------------
URBAN_DEMAND = {
    "Puebla": 95,
    "SAC": 14,        # San Andres Cholula
    "Atlixco": 9,
}
AGRI_DEMAND = {
    "Puebla": 8,
    "SAC": 5,
    "Atlixco": 18,
}

# --- A.3 Water sources: base availability (hm^3/year) ---------------------
SOURCES = {
    "VdP": 80,        # Valle de Puebla Aquifer (groundwater)
    "AI": 45,         # Atlixco-Izucar Aquifer (groundwater)
}

# --- A.4 Drought scenarios: availability factor (alpha) -------------------
# Effective availability A_eff_i = alpha * A_i
DROUGHT = {
    "Normal": 1.00,
    "Moderate": 0.80,
    "Severe": 0.60,
    # "Extreme": 0.40,  # mentioned on the data-inputs slide; optional
}

# --- A.5 Source -> municipality allocation cost ---------------------------
# Relative delivery difficulty (NOT real infrastructure cost). Used only if lambda > 0.
COST = {
    ("VdP", "Puebla"): 1.0,
    ("VdP", "SAC"): 1.2,
    ("VdP", "Atlixco"): 2.5,
    ("AI", "Puebla"): 2.8,
    ("AI", "SAC"): 2.0,
    ("AI", "Atlixco"): 1.0,
}

# --- A.6 Priority weights -------------------------------------------------
W_URBAN = 10
W_AGRI = 3

# --- A.7 Optional crop-water requirements (m^3/ha/year) -------------------
# Only needed if you expand the agricultural demand model (Annex A.7).
CROP_WATER = {
    "Maize": 7000, "Alfalfa": 12000, "Beans": 4500, "Wheat": 5500,
    "Barley": 4500, "Sorghum": 6000, "Oats": 5000, "Vegetables": 8000,
    "Potato": 6500, "Onion": 7500, "ChiliPepper": 6500, "FruitTrees": 9000,
}

MUNICIPALITIES = list(URBAN_DEMAND.keys())
SOURCE_NAMES = list(SOURCES.keys())


def effective_availability(scenario):
    """Return {source: alpha * base_availability} for a named drought scenario."""
    alpha = DROUGHT[scenario]
    return {i: alpha * cap for i, cap in SOURCES.items()}


def instance(scenario):
    """Bundle the full instance for one drought scenario into a dict."""
    return {
        "scenario": scenario,
        "alpha": DROUGHT[scenario],
        "urban_demand": dict(URBAN_DEMAND),
        "agri_demand": dict(AGRI_DEMAND),
        "sources": effective_availability(scenario),
        "cost": dict(COST),
        "w_urban": W_URBAN,
        "w_agri": W_AGRI,
        "municipalities": list(MUNICIPALITIES),
        "source_names": list(SOURCE_NAMES),
    }


if __name__ == "__main__":
    tot_d = sum(URBAN_DEMAND.values()) + sum(AGRI_DEMAND.values())
    print(f"Total demand: {tot_d} hm3/year "
          f"(urban {sum(URBAN_DEMAND.values())}, agri {sum(AGRI_DEMAND.values())})")
    for s in DROUGHT:
        avail = sum(effective_availability(s).values())
        print(f"  {s:9s} alpha={DROUGHT[s]:.2f}  available={avail:6.1f}  "
              f"forced deficit >= {tot_d - avail:6.1f} hm3")
