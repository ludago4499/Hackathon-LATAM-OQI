import streamlit as st

st.markdown('<div class="page-num">01</div>', unsafe_allow_html=True)

# Hero image placeholder — reemplazar con imagen real de la cuenca
st.markdown("""
<div style='width:100%; height:220px; background:linear-gradient(135deg,#0B1E3D,#1A9B8C22);
            border-radius:8px; display:flex; align-items:center; justify-content:center;
            margin-bottom:28px; position:relative; overflow:hidden;'>
  <svg width="100%" height="100%" viewBox="0 0 900 220" preserveAspectRatio="xMidYMid slice"
       xmlns="http://www.w3.org/2000/svg">
    <defs>
      <radialGradient id="g1" cx="30%" cy="50%">
        <stop offset="0%" stop-color="#1A9B8C" stop-opacity="0.3"/>
        <stop offset="100%" stop-color="#0B1E3D" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <rect width="900" height="220" fill="#0B1E3D"/>
    <ellipse cx="270" cy="110" rx="260" ry="140" fill="url(#g1)"/>
    <!-- wave decorativas -->
    <path d="M0,140 C150,100 300,160 450,130 C600,100 750,150 900,120 L900,220 L0,220 Z"
          fill="rgba(26,155,140,0.15)"/>
    <path d="M0,160 C200,130 400,170 600,145 C750,125 850,160 900,150 L900,220 L0,220 Z"
          fill="rgba(79,195,192,0.08)"/>
    <!-- texto hero -->
    <text x="450" y="95" text-anchor="middle" font-family="Space Grotesk,sans-serif"
          font-weight="700" font-size="42" fill="white" font-style="italic" opacity="0.9">
      AEGIS WATER
    </text>
    <text x="450" y="130" text-anchor="middle" font-family="Space Grotesk,sans-serif"
          font-size="16" fill="#4FC3C0" letter-spacing="3">
      ADAPTIVE ENVIRONMENTAL GROUNDWATER INTELLIGENCE SYSTEM
    </text>
    <line x1="350" y1="145" x2="550" y2="145" stroke="#1A9B8C" stroke-width="2"/>
  </svg>
</div>
""", unsafe_allow_html=True)

# Título
st.markdown("### 🛡️ *AEGIS — ANÁLISIS HÍDRICO ALTO ATOYAC*")
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown("**Optimización cuántica-clásica de la asignación de agua bajo escenarios de sequía · SDG 6.4**")
st.markdown("*Cuenca Alto Atoyac, Puebla, México · QWorld OQI Hackathon-LATAM 2026*")

st.markdown("---")

# Sección 1 — Vista rápida
with st.expander("💧 Sección 1 — Vista rápida del sistema hídrico", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fuentes de agua", "2", "acuíferos")
    col2.metric("Municipios", "3", "en modelo")
    col3.metric("Disponibilidad base", "125 hm³", "Valle + Atlixco-Izúcar")
    col4.metric("Demanda total", "149 hm³", "urbana + agrícola")

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div style='background:white;border:1px solid #E0DDD6;border-radius:6px;padding:16px 20px;'>
          <div style='font-family:Space Mono,monospace;font-size:10px;text-transform:uppercase;
                      letter-spacing:0.12em;color:#888;margin-bottom:8px;'>Acuíferos</div>
          <div style='display:flex;justify-content:space-between;margin-bottom:8px;font-size:14px;'>
            <span>Valle de Puebla</span>
            <strong style='color:#1A9B8C;'>80 hm³</strong>
          </div>
          <div style='display:flex;justify-content:space-between;font-size:14px;'>
            <span>Atlixco-Izúcar</span>
            <strong style='color:#1A9B8C;'>45 hm³</strong>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div style='background:white;border:1px solid #E0DDD6;border-radius:6px;padding:16px 20px;'>
          <div style='font-family:Space Mono,monospace;font-size:10px;text-transform:uppercase;
                      letter-spacing:0.12em;color:#888;margin-bottom:8px;'>Municipios</div>
          <div style='display:flex;justify-content:space-between;margin-bottom:6px;font-size:14px;'>
            <span>Puebla</span><span><strong>95</strong> urb · <strong>8</strong> agr hm³</span>
          </div>
          <div style='display:flex;justify-content:space-between;margin-bottom:6px;font-size:14px;'>
            <span>S.A. Cholula</span><span><strong>14</strong> urb · <strong>5</strong> agr hm³</span>
          </div>
          <div style='display:flex;justify-content:space-between;font-size:14px;'>
            <span>Atlixco</span><span><strong>9</strong> urb · <strong>18</strong> agr hm³</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# Sección 2 — Escenarios
st.markdown("### 📋 *SECCIÓN 2 — ESCENARIOS DE SEQUÍA*")
st.markdown('<hr>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div style='background:white;border-left:4px solid #1A9B8C;
                border-radius:4px;padding:16px 20px;'>
      <span class='badge-normal'>NORMAL</span>
      <div style='font-size:28px;font-weight:700;color:#1A9B8C;margin:8px 0;'>α = 1.00</div>
      <div style='font-size:13px;color:#666;'>125 hm³ disponibles<br>Sin restricción adicional</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div style='background:white;border-left:4px solid #F5C542;
                border-radius:4px;padding:16px 20px;'>
      <span class='badge-mod'>SEQUÍA MODERADA</span>
      <div style='font-size:28px;font-weight:700;color:#B8860B;margin:8px 0;'>α = 0.80</div>
      <div style='font-size:13px;color:#666;'>100 hm³ disponibles<br>-20% por sequía</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div style='background:white;border-left:4px solid #E05C5C;
                border-radius:4px;padding:16px 20px;'>
      <span class='badge-sev'>SEQUÍA SEVERA</span>
      <div style='font-size:28px;font-weight:700;color:#C0392B;margin:8px 0;'>α = 0.60</div>
      <div style='font-size:13px;color:#666;'>75 hm³ disponibles<br>-40% por sequía</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Ruta recomendada
with st.sidebar:
    st.markdown("""
    <div style='margin-top:16px;'>
      <div style='font-size:11px;font-weight:700;color:#F5C542;letter-spacing:0.1em;
                  text-transform:uppercase;margin-bottom:8px;'>⚡ RUTA RECOMENDADA</div>
      <div style='font-size:12px;color:#AAA;line-height:1.8;'>
        1. <b style='color:#F4F1EA;'>MAIN</b> — resumen<br>
        2. <b style='color:#F4F1EA;'>MODELO</b> — formulación<br>
        3. <b style='color:#F4F1EA;'>SIMULACIÓN</b> — corre el MILP<br>
        4. <b style='color:#F4F1EA;'>RESULTADOS</b> — gráficas<br>
        5. <b style='color:#F4F1EA;'>VALIDACIÓN</b> — métricas<br>
        6. <b style='color:#F4F1EA;'>ECONOMICS</b> — viabilidad<br>
        7. <b style='color:#F4F1EA;'>SLIDES</b> — presentación
      </div>
    </div>
    """, unsafe_allow_html=True)
