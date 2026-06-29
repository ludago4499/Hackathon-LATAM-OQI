import streamlit as st

st.markdown('<div class="page-num">02</div>', unsafe_allow_html=True)
st.markdown("### 👥 *TEAM — AEGIS WATER*")
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown("Equipo participante · QWorld OQI Hackathon-LATAM 2026 · Alto Atoyac Basin")
st.markdown("---")

# ── Edita los nombres y roles aquí ──────────────────────────────────────────
TEAM = [
    {"initials": "?", "name": "[ Nombre ]",   "role": "[ Rol ]",   "area": "[ Universidad ]"},
    {"initials": "?", "name": "[ Nombre ]",   "role": "[ Rol ]",   "area": "[ Universidad ]"},
    {"initials": "?", "name": "[ Nombre ]",   "role": "[ Rol ]",   "area": "[ Universidad ]"},
    {"initials": "?", "name": "[ Nombre ]",   "role": "[ Rol ]",   "area": "[ Universidad ]"},
]
# ────────────────────────────────────────────────────────────────────────────

cols = st.columns(len(TEAM))
for col, member in zip(cols, TEAM):
    with col:
        st.markdown(f"""
        <div style='background:white;border:1px solid #E0DDD6;border-radius:8px;
                    padding:24px 16px;text-align:center;'>
          <div style='width:64px;height:64px;border-radius:50%;
                      background:linear-gradient(135deg,#1A9B8C,#4FC3C0);
                      display:flex;align-items:center;justify-content:center;
                      font-size:24px;font-weight:700;color:white;
                      margin:0 auto 14px auto;'>{member['initials']}</div>
          <div style='font-weight:700;font-size:15px;margin-bottom:4px;'>{member['name']}</div>
          <div style='font-size:12px;color:#1A9B8C;font-weight:600;margin-bottom:4px;'>{member['role']}</div>
          <div style='font-size:11px;color:#888;'>{member['area']}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 🏆 *CONTEXTO DEL HACKATHON*")
st.markdown('<hr>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("""
    <div style='background:white;border:1px solid #E0DDD6;border-radius:6px;padding:20px;'>
      <div style='font-family:Space Mono,monospace;font-size:10px;text-transform:uppercase;
                  letter-spacing:0.12em;color:#888;margin-bottom:12px;'>Challenge</div>
      <b>SDG 6.4</b> — Sustainable Water Allocation in the Alto Atoyac Basin Under Drought Scenarios<br><br>
      <span class='tag'>MILP Baseline</span>
      <span class='tag'>QUBO</span>
      <span class='tag'>QAOA</span>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div style='background:white;border:1px solid #E0DDD6;border-radius:6px;padding:20px;'>
      <div style='font-family:Space Mono,monospace;font-size:10px;text-transform:uppercase;
                  letter-spacing:0.12em;color:#888;margin-bottom:12px;'>Impacto SDG</div>
      <span class='tag'>SDG 6.4 Agua</span>
      <span class='tag'>SDG 11 Ciudades</span>
      <span class='tag tag-yellow'>SDG 13 Clima</span><br><br>
      <i style='font-size:13px;color:#666;'>Trade-offs: SDG 2 Hambre · SDG 8 Trabajo</i>
    </div>
    """, unsafe_allow_html=True)
