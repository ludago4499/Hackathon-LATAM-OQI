import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.solver import solve_all_scenarios, MUNS_LIST, SOURCES_LIST, MUNICIPALITIES
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.markdown('<div class="page-num">05</div>', unsafe_allow_html=True)
st.markdown("### 📊 *RESULTADOS — COMPARACIÓN POR ESCENARIO*")
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown("Resolución automática de los 3 escenarios benchmark del Guided Challenge.")
st.markdown("---")

if st.button("▶  RESOLVER LOS 3 ESCENARIOS", type="primary", use_container_width=True):
    with st.spinner("Resolviendo Normal, Moderada y Severa..."):
        results = solve_all_scenarios()
    st.session_state["all_results"] = results

if "all_results" not in st.session_state:
    st.info("Pulsa el botón para resolver los tres escenarios benchmark simultáneamente.")
    st.stop()

results = st.session_state["all_results"]
scenario_names = list(results.keys())
colors_sc = {"Normal": "#1A9B8C", "Sequía moderada": "#F5C542", "Sequía severa": "#E05C5C"}

# ── Tabla maestra ──────────────────────────────────────────────────────────
st.markdown("#### Tabla de resultados requeridos (Annex B)")
rows = []
for name, r in results.items():
    rows.append({
        "Escenario": name,
        "α": {"Normal": 1.0, "Sequía moderada": 0.8, "Sequía severa": 0.6}[name],
        "NWWD": r.nwwd,
        "Déficit urb. norm.": f"{r.unmet_urban_norm*100:.2f}%",
        "Déficit agri. norm.": f"{r.unmet_agri_norm*100:.2f}%",
        "Déficit urb. total (hm³)": round(float(sum(r.u_urban)), 3),
        "Déficit agri. total (hm³)": round(float(sum(r.u_agri)), 3),
        "Factible": "✅" if r.status == "OPTIMAL" else "❌",
        "Runtime (ms)": r.runtime_ms,
    })
df_master = pd.DataFrame(rows)
st.dataframe(df_master, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Métricas por escenario ────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
for col, (name, r) in zip([c1, c2, c3], results.items()):
    col.metric(f"NWWD — {name}", f"{r.nwwd:.4f}")

st.markdown("---")

# ── Gráfica NWWD comparativo ──────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("#### NWWD por escenario")
    fig_nwwd = go.Figure(go.Bar(
        x=scenario_names,
        y=[results[n].nwwd for n in scenario_names],
        marker_color=[colors_sc[n] for n in scenario_names],
        text=[f"{results[n].nwwd:.4f}" for n in scenario_names],
        textposition="outside",
    ))
    fig_nwwd.update_layout(
        template="plotly_white", paper_bgcolor="#F4F1EA", plot_bgcolor="#F4F1EA",
        font=dict(family="Space Grotesk"), margin=dict(t=30, b=10),
        yaxis_title="NWWD", showlegend=False,
    )
    st.plotly_chart(fig_nwwd, use_container_width=True)

with col_b:
    st.markdown("#### Déficit normalizado urbano vs agrícola")
    fig_def = go.Figure()
    fig_def.add_bar(
        name="Déficit Urbano norm.",
        x=scenario_names,
        y=[results[n].unmet_urban_norm * 100 for n in scenario_names],
        marker_color="#E05C5C",
    )
    fig_def.add_bar(
        name="Déficit Agrícola norm.",
        x=scenario_names,
        y=[results[n].unmet_agri_norm * 100 for n in scenario_names],
        marker_color="#F5C542",
    )
    fig_def.update_layout(
        barmode="group", template="plotly_white",
        paper_bgcolor="#F4F1EA", plot_bgcolor="#F4F1EA",
        font=dict(family="Space Grotesk"), margin=dict(t=30, b=10),
        yaxis_title="%", legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig_def, use_container_width=True)

st.markdown("---")

# ── Asignación por municipio en cada escenario ────────────────────────────
st.markdown("#### Asignación total por municipio y escenario")

scenario_sel = st.selectbox("Ver escenario:", scenario_names)
r = results[scenario_sel]

mun_rows = []
for j, mun in enumerate(MUNS_LIST):
    asig_u = float(np.sum(r.x_urban[:, j]))
    asig_a = float(np.sum(r.x_agri[:, j]))
    mun_rows.append({
        "Municipio": mun,
        "Dem. Urbana": MUNICIPALITIES[mun]["urban"],
        "Asig. Urbana": round(asig_u, 3),
        "Déficit Urbano": round(float(r.u_urban[j]), 3),
        "Dem. Agrícola": MUNICIPALITIES[mun]["agri"],
        "Asig. Agrícola": round(asig_a, 3),
        "Déficit Agrícola": round(float(r.u_agri[j]), 3),
    })
df_mun = pd.DataFrame(mun_rows)
st.dataframe(df_mun, use_container_width=True, hide_index=True)

# radar chart por municipio
fig_radar = go.Figure()
categories = ["Asig. Urbana", "Asig. Agrícola", "Déficit Urbano", "Déficit Agrícola"]
mun_colors = ["#1A9B8C", "#4FC3C0", "#0B5E57"]
for idx, row in df_mun.iterrows():
    vals = [row["Asig. Urbana"], row["Asig. Agrícola"],
            row["Déficit Urbano"], row["Déficit Agrícola"]]
    vals += [vals[0]]
    fig_radar.add_trace(go.Scatterpolar(
        r=vals, theta=categories + [categories[0]],
        fill='toself', name=row["Municipio"],
        line_color=mun_colors[idx], opacity=0.7,
    ))
fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, color="#888")),
    template="plotly_white", paper_bgcolor="#F4F1EA",
    font=dict(family="Space Grotesk"), margin=dict(t=30, b=10),
    legend=dict(orientation="h", y=-0.1),
)
st.plotly_chart(fig_radar, use_container_width=True)
