import streamlit as st

st.markdown('<div class="page-num">08</div>', unsafe_allow_html=True)
st.markdown("### 🎞️ *SLIDES — PRESENTACIÓN AEGIS*")
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown("Presentación interactiva servida desde GitHub Pages — siempre actualizada con el repo.")
st.markdown("---")

# ── URL del GitHub Pages — edita cuando tengas el repo publicado ──────────
GITHUB_USER = "TU_USUARIO"       # ← cambia esto
REPO_NAME   = "aegis-water"       # ← cambia si usas otro nombre
PAGES_URL   = f"https://{GITHUB_USER}.github.io/{REPO_NAME}/"
# ─────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style='background:white;border:1px solid #E0DDD6;border-radius:6px;padding:16px 20px;
            margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;'>
  <div>
    <div style='font-family:Space Mono,monospace;font-size:10px;text-transform:uppercase;
                letter-spacing:0.12em;color:#888;margin-bottom:4px;'>GitHub Pages URL</div>
    <code style='font-size:14px;color:#1A9B8C;'>{PAGES_URL}</code>
  </div>
  <a href='{PAGES_URL}' target='_blank'
     style='background:#1A9B8C;color:white;padding:8px 18px;border-radius:4px;
            text-decoration:none;font-weight:700;font-size:13px;'>
    Abrir en nueva pestaña ↗
  </a>
</div>
""", unsafe_allow_html=True)

# Iframe de la presentación
st.markdown(f"""
<iframe src="{PAGES_URL}"
        width="100%"
        height="620"
        style="border:1px solid #E0DDD6; border-radius:8px; background:#0B1E3D;"
        frameborder="0"
        allow="fullscreen">
</iframe>
""", unsafe_allow_html=True)

st.caption("💡 La presentación se actualiza automáticamente cuando haces push al repo. Navega con ← → dentro del iframe.")

st.markdown("---")
st.markdown("#### Acceso rápido al repositorio")
c1, c2 = st.columns(2)
with c1:
    st.markdown(f"""
    <a href='https://github.com/{GITHUB_USER}/{REPO_NAME}' target='_blank'
       style='display:block;background:#1A1A1A;color:white;padding:12px 20px;border-radius:6px;
              text-decoration:none;font-weight:700;font-size:14px;text-align:center;'>
      🐙 Ver repositorio en GitHub
    </a>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <a href='https://github.com/{GITHUB_USER}/{REPO_NAME}/edit/main/index.html' target='_blank'
       style='display:block;background:#1A9B8C;color:white;padding:12px 20px;border-radius:6px;
              text-decoration:none;font-weight:700;font-size:14px;text-align:center;'>
      ✏️ Editar presentación en GitHub
    </a>
    """, unsafe_allow_html=True)
