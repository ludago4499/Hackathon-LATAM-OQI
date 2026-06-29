import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.solver import solve_all_scenarios, MUNS_LIST, MUNICIPALITIES, SOURCES_LIST, SOURCES
import numpy as np
import plotly.graph_objects as go

st.markdown('<div class="page-num">06</div>', unsafe_allow_html=True)
st.markdown("### ✅ *VALIDACIÓN — ¿CÓMO SABEMOS QUE EL MODELO ES CORRECTO?*")
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown("Verificación de factibilidad, restricciones activas y correctitud del solver.")
st.markdown("---")

if st.button("▶  VALIDAR LOS 3 ESCENARIOS", type="primary", use_container_width=True):
    with st.spinner("Resolviendo y verificando..."):
        results = solve_all_scenarios()
    st.session_state["val_results"] = results

if "val_results" not in st.session_state:
    # Reutilizar si ya se resolvió en otra página
    if "all_results" in st.session_state:
        st.session_state["val_results"] = st.session_state["all_results"]
    else:
        st.info("Pulsa el botón para validar el modelo.")
        st.stop()

results = st.session_state["val_results"]

# ── Checklist de factibilidad por escenario ───────────────────────────────
st.markdown("#### Checklist de restricciones — verificación automática")

alphas = {"Normal": 1.0, "Sequía moderada": 0.8, "Sequía severa": 0.6}
tol = 1e-4  # tolerancia numérica

for name, r in results.items():
    alpha = alphas[name]
    st.markdown(f"**{name}** (α = {alpha})")

    checks = {}

    # 1. Capacidad fuente
    for i, src in enumerate(SOURCES_LIST):
        used = float(np.sum(r.x_urban[i,:]) + np.sum(r.x_agri[i,:]))
        avail = SOURCES[src]["base_avail"] * alpha
        ok = used <= avail + tol
        checks[f"Capacidad {src}"] = (ok, f"{used:.3f} ≤ {avail:.1f} hm³")

    # 2. Balance urbano
    for j, mun in enumerate(MUNS_LIST):
        lhs = float(np.sum(r.x_urban[:,j])) + float(r.u_urban[j])
        rhs = MUNICIPALITIES[mun]["urban"]
        ok = abs(lhs - rhs) < tol
        checks[f"Balance urbano {mun}"] = (ok, f"|{lhs:.3f} - {rhs}| = {abs(lhs-rhs):.2e}")

    # 3. Balance agrícola
    for j, mun in enumerate(MUNS_LIST):
        lhs = float(np.sum(r.x_agri[:,j])) + float(r.u_agri[j])
        rhs = MUNICIPALITIES[mun]["agri"]
        ok = abs(lhs - rhs) < tol
        checks[f"Balance agrícola {mun}"] = (ok, f"|{lhs:.3f} - {rhs}| = {abs(lhs-rhs):.2e}")

    # 4. No-negatividad
    all_vars = np.concatenate([r.x_urban.flatten(), r.x_agri.flatten(),
                                r.u_urban, r.u_agri])
    nn_ok = bool(np.all(all_vars >= -tol))
    checks["No-negatividad (todas las variables)"] = (nn_ok, f"min={all_vars.min():.2e}")

    passed = sum(v[0] for v in checks.values())
    total  = len(checks)

    cols = st.columns(len(checks))
    for col, (check_name, (ok, detail)) in zip(cols, checks.items()):
        icon = "✅" if ok else "❌"
        col.markdown(f"""
        <div style='background:{"#F0FFF8" if ok else "#FFF0F0"};
                    border:1px solid {"#1A9B8C" if ok else "#E05C5C"};
                    border-radius:4px;padding:10px;text-align:center;font-size:11px;'>
          <div style='font-size:20px;'>{icon}</div>
          <div style='font-weight:600;font-size:11px;margin:4px 0;'>{check_name.split(" ", 1)[0]}<br>{check_name.split(" ", 1)[1] if " " in check_name else ""}</div>
          <div style='color:#888;font-family:Space Mono,monospace;font-size:10px;'>{detail}</div>
        </div>
        """, unsafe_allow_html=True)

    st.caption(f"✔ {passed}/{total} restricciones satisfechas · Status solver: **{r.status}** · Runtime: {r.runtime_ms} ms")
    st.markdown("")

st.markdown("---")

# ── Sensitivity: NWWD vs alpha ────────────────────────────────────────────
st.markdown("#### Análisis de sensibilidad — NWWD vs factor de sequía α")

from utils.solver import solve_milp
alphas_range = np.arange(0.40, 1.01, 0.05)
nwwds, u_urb_norms, u_agr_norms = [], [], []

with st.spinner("Calculando curva de sensibilidad..."):
    for a in alphas_range:
        res = solve_milp(a)
        nwwds.append(res.nwwd)
        u_urb_norms.append(res.unmet_urban_norm * 100)
        u_agr_norms.append(res.unmet_agri_norm * 100)

fig = go.Figure()
fig.add_scatter(x=alphas_range, y=nwwds, name="NWWD",
                line=dict(color="#1A9B8C", width=2.5), mode="lines+markers")
fig.add_scatter(x=alphas_range, y=u_urb_norms, name="Déficit Urbano (%)",
                line=dict(color="#E05C5C", width=1.5, dash="dot"))
fig.add_scatter(x=alphas_range, y=u_agr_norms, name="Déficit Agrícola (%)",
                line=dict(color="#F5C542", width=1.5, dash="dot"))

# Líneas verticales de los escenarios benchmark
for a_val, label in [(1.0,"Normal"),(0.8,"Mod."),(0.6,"Severa")]:
    fig.add_vline(x=a_val, line_dash="dash", line_color="#888",
                  annotation_text=label, annotation_position="top right")

fig.update_layout(
    template="plotly_white", paper_bgcolor="#F4F1EA", plot_bgcolor="#F4F1EA",
    font=dict(family="Space Grotesk"), xaxis_title="α (factor de disponibilidad)",
    yaxis_title="NWWD / Déficit (%)", legend=dict(orientation="h", y=1.1),
    margin=dict(t=30, b=10),
)
st.plotly_chart(fig, use_container_width=True)
st.caption("La curva muestra dónde el sistema pasa de cero déficit a déficit creciente — punto de quiebre estructural.")
