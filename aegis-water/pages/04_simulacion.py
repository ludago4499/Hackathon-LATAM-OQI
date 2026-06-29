import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.solver import solve_milp, SOURCES, MUNICIPALITIES, SOURCES_LIST, MUNS_LIST
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

st.markdown('<div class="page-num">04</div>', unsafe_allow_html=True)
st.markdown("### ⚙️ *SIMULACIÓN — MODELO MILP INTERACTIVO*")
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown("Ajusta los parámetros y corre el solver en tiempo real.")
st.markdown("---")

# ── Controles ────────────────────────────────────────────────────────────────
with st.expander("🎛️ Parámetros del modelo", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Factor de sequía α**")
        alpha = st.slider("α (disponibilidad)", 0.40, 1.00, 1.00, 0.05,
                          help="α=1.0 = normal · α=0.8 = moderada · α=0.6 = severa")
        # Badge automático
        if alpha >= 0.90:
            badge = "<span class='badge-normal'>NORMAL</span>"
        elif alpha >= 0.70:
            badge = "<span class='badge-mod'>SEQUÍA MODERADA</span>"
        else:
            badge = "<span class='badge-sev'>SEQUÍA SEVERA</span>"
        st.markdown(f"Escenario: {badge}", unsafe_allow_html=True)

    with col2:
        st.markdown("**Pesos de prioridad**")
        wU = st.slider("wU — peso urbano",     1, 20, 10,
                       help="Penalización por déficit urbano (benchmark: 10)")
        wA = st.slider("wA — peso agrícola",   1, 10,  3,
                       help="Penalización por déficit agrícola (benchmark: 3)")

    with col3:
        st.markdown("**Costo de distribución**")
        lam = st.slider("λ — peso del costo",  0.0, 2.0, 0.0, 0.1,
                        help="λ=0 ignora costos · λ>0 penaliza rutas caras")
        st.markdown("""
        <div style='background:#FFF8E7;border:1px solid #F5C542;border-radius:4px;
                    padding:10px 12px;font-size:12px;color:#B8860B;margin-top:8px;'>
          Benchmark oficial: λ = 0<br>
          Puedes ajustar para explorar trade-offs
        </div>
        """, unsafe_allow_html=True)

# ── Disponibilidad resultante ─────────────────────────────────────────────────
A_eff = {src: SOURCES[src]["base_avail"] * alpha for src in SOURCES_LIST}
total_avail = sum(A_eff.values())
total_demand = sum(v["urban"] + v["agri"] for v in MUNICIPALITIES.values())
deficit_total = max(0, total_demand - total_avail)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Valle de Puebla (A_eff)", f"{A_eff['Valle de Puebla']:.1f} hm³",
          f"{(alpha-1)*100:.0f}% base")
m2.metric("Atlixco-Izúcar (A_eff)", f"{A_eff['Atlixco-Izúcar']:.1f} hm³",
          f"{(alpha-1)*100:.0f}% base")
m3.metric("Disponibilidad total", f"{total_avail:.1f} hm³")
m4.metric("Déficit estructural", f"{deficit_total:.1f} hm³",
          delta_color="inverse")

st.markdown("---")

# ── Resolver ─────────────────────────────────────────────────────────────────
if st.button("▶  RESOLVER MILP", type="primary", use_container_width=True):
    with st.spinner("Corriendo solver HiGHS..."):
        result = solve_milp(alpha, wU, wA, lam)
    st.session_state["last_result"] = result
    st.session_state["last_params"] = {"alpha": alpha, "wU": wU, "wA": wA, "lam": lam}

# Mostrar resultado si existe
if "last_result" in st.session_state:
    r = st.session_state["last_result"]
    p = st.session_state["last_params"]

    st.markdown("---")
    st.markdown("### 📊 *RESULTADO DE LA SIMULACIÓN*")
    st.markdown('<hr>', unsafe_allow_html=True)

    # Métricas principales
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NWWD", f"{r.nwwd:.4f}", help="Normalized Weighted Water Deficit")
    c2.metric("Estado", r.status)
    c3.metric("Déficit urbano norm.", f"{r.unmet_urban_norm*100:.1f}%")
    c4.metric("Déficit agrícola norm.", f"{r.unmet_agri_norm*100:.1f}%")

    # Tabla de asignación
    st.markdown("#### Asignación óptima fuente × municipio")
    rows = []
    for i, src in enumerate(SOURCES_LIST):
        for j, mun in enumerate(MUNS_LIST):
            rows.append({
                "Fuente": src, "Municipio": mun,
                "Urbana asig. (hm³)": round(r.x_urban[i,j], 3),
                "Agrícola asig. (hm³)": round(r.x_agri[i,j], 3),
                "Total asig. (hm³)": round(r.x_urban[i,j] + r.x_agri[i,j], 3),
            })
    df = pd.DataFrame(rows)
    st.dataframe(df.style.background_gradient(subset=["Total asig. (hm³)"], cmap="YlGn"),
                 use_container_width=True)

    # Gráfica de barras — asignación vs demanda por municipio
    st.markdown("#### Balance demanda vs asignación por municipio")
    mun_data = []
    for j, mun in enumerate(MUNS_LIST):
        asig_urb  = float(np.sum(r.x_urban[:, j]))
        asig_agr  = float(np.sum(r.x_agri[:, j]))
        dem_urb   = MUNICIPALITIES[mun]["urban"]
        dem_agr   = MUNICIPALITIES[mun]["agri"]
        mun_data.append({
            "Municipio": mun,
            "Dem. Urbana": dem_urb, "Asig. Urbana": asig_urb,
            "Déficit Urbano": float(r.u_urban[j]),
            "Dem. Agrícola": dem_agr, "Asig. Agrícola": asig_agr,
            "Déficit Agrícola": float(r.u_agri[j]),
        })
    mdf = pd.DataFrame(mun_data)

    fig = go.Figure()
    fig.add_bar(name="Asig. Urbana",    x=mdf["Municipio"], y=mdf["Asig. Urbana"],
                marker_color="#1A9B8C")
    fig.add_bar(name="Déficit Urbano",  x=mdf["Municipio"], y=mdf["Déficit Urbano"],
                marker_color="#E05C5C", opacity=0.7)
    fig.add_bar(name="Asig. Agrícola",  x=mdf["Municipio"], y=mdf["Asig. Agrícola"],
                marker_color="#4FC3C0")
    fig.add_bar(name="Déficit Agrícola",x=mdf["Municipio"], y=mdf["Déficit Agrícola"],
                marker_color="#F5C542", opacity=0.7)
    fig.update_layout(
        barmode="stack", template="plotly_white",
        font=dict(family="Space Grotesk"),
        paper_bgcolor="#F4F1EA", plot_bgcolor="#F4F1EA",
        margin=dict(t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="hm³",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Gráfica Sankey — flujo de agua
    st.markdown("#### Diagrama de flujo (Sankey)")
    labels = SOURCES_LIST + MUNS_LIST
    source_idx, target_idx, values, colors = [], [], [], []
    for i in range(len(SOURCES_LIST)):
        for j in range(len(MUNS_LIST)):
            total = float(r.x_urban[i,j] + r.x_agri[i,j])
            if total > 0.01:
                source_idx.append(i)
                target_idx.append(len(SOURCES_LIST) + j)
                values.append(round(total, 2))
                colors.append("rgba(26,155,140,0.4)")

    fig2 = go.Figure(go.Sankey(
        node=dict(
            label=labels,
            color=["#1A9B8C","#0B5E57"] + ["#4FC3C0","#2A9D8F","#1A7A6E"],
            pad=20, thickness=20,
        ),
        link=dict(source=source_idx, target=target_idx, value=values, color=colors)
    ))
    fig2.update_layout(
        font=dict(family="Space Grotesk", size=12),
        paper_bgcolor="#F4F1EA", margin=dict(t=20,b=20)
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.info(f"⏱️ Runtime: **{r.runtime_ms} ms** · α={p['alpha']} · wU={p['wU']} · wA={p['wA']} · λ={p['lam']}")
else:
    st.info("👆 Ajusta los parámetros y pulsa **RESOLVER MILP** para ver los resultados.")
