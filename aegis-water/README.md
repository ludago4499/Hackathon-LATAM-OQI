# 🛡️ AEGIS Water — SDG 6.4 Hackathon

**Adaptive Environmental Groundwater Intelligence System**  
Optimización cuántica-clásica de la asignación hídrica en la cuenca Alto Atoyac bajo escenarios de sequía.

> QWorld OQI Hackathon-LATAM 2026 · SDG 6.4 Guided Challenge

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://TU_APP.streamlit.app)

---

## Estructura del repositorio

```
aegis-water/
├── app.py                  # Entrada principal Streamlit
├── index.html              # Presentación HTML (GitHub Pages)
├── requirements.txt
├── utils/
│   └── solver.py           # Motor MILP (scipy HiGHS)
└── pages/
    ├── 01_main.py          # Portada y resumen
    ├── 02_team.py          # Equipo
    ├── 03_modelo.py        # Formulación MILP
    ├── 04_simulacion.py    # Simulación interactiva
    ├── 05_resultados.py    # Resultados 3 escenarios
    ├── 06_validacion.py    # Validación y métricas
    ├── 07_economics.py     # Viabilidad financiera
    └── 08_presentacion.py  # Slides embebidas
```

## Correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Modelo

**Objetivo:** minimizar el NWWD (Normalized Weighted Water Deficit)

```
min  wU · Σⱼ(u_urb_j / D_urb_j)  +  wA · Σⱼ(u_agri_j / D_agri_j)
```

Con `wU = 10`, `wA = 3` (benchmark oficial).

**Escenarios benchmark:**
| Escenario | α | Disponibilidad |
|-----------|---|----------------|
| Normal | 1.00 | 125 hm³ |
| Sequía moderada | 0.80 | 100 hm³ |
| Sequía severa | 0.60 | 75 hm³ |

## Presentación

La presentación vive en `index.html` y se sirve via GitHub Pages:  
`https://TU_USUARIO.github.io/aegis-water/`

## Licencia

MIT
