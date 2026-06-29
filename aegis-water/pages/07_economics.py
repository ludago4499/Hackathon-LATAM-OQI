import streamlit as st
import plotly.graph_objects as go
import numpy as np

st.markdown('<div class="page-num">07</div>', unsafe_allow_html=True)
st.markdown("### 💹 *ECONOMICS — VIABILIDAD FINANCIERA*")
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown("AEGIS como producto SaaS de optimización hídrica para organismos operadores y autoridades de cuencas.")
st.markdown("---")

# ── Métricas principales (de la foto) ────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("TIR", "21%", "TIR > TREMA (15%) ✅")
c2.metric("VPN", "$1,665,401 MXN", "Valor presente neto")
c3.metric("Período de recuperación", "4.8 años", "Retorno de inversión")

st.markdown("---")

# ── Modelo de negocio ─────────────────────────────────────────────────────
st.markdown("#### Modelo de negocio — SaaS")
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div style='background:white;border:1px solid #E0DDD6;border-radius:6px;padding:20px;'>
      <div style='font-family:Space Mono,monospace;font-size:10px;text-transform:uppercase;
                  letter-spacing:0.12em;color:#888;margin-bottom:12px;'>Segmentos de mercado</div>
      <div style='margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #eee;'>
        <b>Organismos operadores pequeños</b>
        <div style='color:#888;font-size:13px;'>Municipios &lt;100k hab · licencia anual</div>
        <div style='color:#1A9B8C;font-family:Space Mono,monospace;font-size:13px;margin-top:4px;'>
          [ precio por definir ]
        </div>
      </div>
      <div style='margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #eee;'>
        <b>Autoridades de cuenca / estado</b>
        <div style='color:#888;font-size:13px;'>Multi-municipio · datos históricos integrados</div>
        <div style='color:#1A9B8C;font-family:Space Mono,monospace;font-size:13px;margin-top:4px;'>
          [ precio por definir ]
        </div>
      </div>
      <div>
        <b>Consultoría de implementación</b>
        <div style='color:#888;font-size:13px;'>Setup, capacitación, integración CONAGUA</div>
        <div style='color:#1A9B8C;font-family:Space Mono,monospace;font-size:13px;margin-top:4px;'>
          [ precio por definir ]
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    # Flujo de caja simulado (placeholder — editar con datos reales)
    years = [0, 1, 2, 3, 4, 5]
    # ── Edita estos valores con tu análisis financiero real ──────────────
    inversion = -500_000
    flujos = [inversion, 80_000, 200_000, 380_000, 520_000, 660_000]
    flujo_acumulado = np.cumsum(flujos)
    # ────────────────────────────────────────────────────────────────────

    fig = go.Figure()
    fig.add_bar(x=years, y=flujos,
                marker_color=["#E05C5C" if f < 0 else "#1A9B8C" for f in flujos],
                name="Flujo anual")
    fig.add_scatter(x=years, y=flujo_acumulado, name="Acumulado",
                    line=dict(color="#0B1E3D", width=2), mode="lines+markers")
    fig.add_hline(y=0, line_color="#888", line_dash="dash")
    fig.update_layout(
        template="plotly_white", paper_bgcolor="#F4F1EA", plot_bgcolor="#F4F1EA",
        font=dict(family="Space Grotesk"), xaxis_title="Año",
        yaxis_title="MXN", margin=dict(t=10, b=10),
        legend=dict(orientation="h", y=1.1),
        title="Flujo de caja proyectado (placeholder)",
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Cálculo TIR/VPN interactivo ───────────────────────────────────────────
st.markdown("#### Calculadora TIR / VPN")
with st.expander("Ajustar supuestos financieros"):
    c1, c2 = st.columns(2)
    with c1:
        inv_inicial = st.number_input("Inversión inicial (MXN)", value=500_000, step=10_000)
        trema = st.slider("TREMA (%)", 5, 30, 15) / 100
    with c2:
        st.markdown("**Flujos anuales (MXN)**")
        f1 = st.number_input("Año 1", value=80_000,  step=10_000)
        f2 = st.number_input("Año 2", value=200_000, step=10_000)
        f3 = st.number_input("Año 3", value=380_000, step=10_000)
        f4 = st.number_input("Año 4", value=520_000, step=10_000)
        f5 = st.number_input("Año 5", value=660_000, step=10_000)

    cash_flows = [-inv_inicial, f1, f2, f3, f4, f5]

    # VPN
    vpn = sum(cf / (1 + trema) ** t for t, cf in enumerate(cash_flows))

    # TIR (bisección simple)
    def npv(rate, flows):
        return sum(cf / (1 + rate) ** t for t, cf in enumerate(flows))

    lo, hi = -0.99, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(mid, cash_flows) > 0:
            lo = mid
        else:
            hi = mid
    tir = mid

    c1, c2, c3 = st.columns(3)
    c1.metric("VPN calculado", f"${vpn:,.0f} MXN",
              "✅ viable" if vpn > 0 else "❌ no viable")
    c2.metric("TIR calculada", f"{tir*100:.1f}%",
              f"{'✅' if tir > trema else '❌'} vs TREMA {trema*100:.0f}%")
    c3.metric("TREMA", f"{trema*100:.0f}%")
