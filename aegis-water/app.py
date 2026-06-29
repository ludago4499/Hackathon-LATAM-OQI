import streamlit as st

st.set_page_config(
    page_title="AEGIS Water — SDG 6.4",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS (estilo Streger: fondo crema, tipografía bold italic) ──────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono&display=swap');

html, body, [class*="css"] {
    background-color: #F4F1EA !important;
    color: #1A1A1A !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #1A1A1A !important;
    min-width: 220px !important;
}
section[data-testid="stSidebar"] * { color: #F4F1EA !important; }
section[data-testid="stSidebar"] .stRadio label { font-size: 13px !important; }

/* Botones de nav en sidebar */
div[data-testid="stSidebarNav"] a {
    color: #F4F1EA !important;
}

/* Titles */
h1 { font-style: italic !important; font-weight: 700 !important; font-size: 2.4rem !important; letter-spacing: -0.02em !important; }
h2 { font-weight: 700 !important; }
h3 { font-weight: 600 !important; }

/* Metric cards */
div[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E0DDD6;
    border-radius: 4px;
    padding: 16px 20px !important;
}
div[data-testid="metric-container"] label { font-family: 'Space Mono', monospace !important; font-size: 11px !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; color: #888 !important; }
div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700 !important; color: #1A9B8C !important; }

/* Expander */
details { border: 1px solid #E0DDD6 !important; border-radius: 4px !important; background: #FAFAF7 !important; }

/* Divider accent */
hr { border: none; border-top: 3px solid #1A9B8C; width: 60px; margin: 0 0 24px 0; }

/* Tag pills */
.tag { display:inline-block; background:#1A9B8C22; color:#1A9B8C; border:1px solid #1A9B8C44;
       font-family:'Space Mono',monospace; font-size:11px; padding:2px 10px; border-radius:3px;
       text-transform:uppercase; letter-spacing:0.08em; margin:2px; }
.tag-yellow { background:#F5C54222; color:#B8860B; border-color:#F5C54244; }
.tag-red { background:#E05C5C22; color:#C0392B; border-color:#E05C5C44; }

/* Page number deco */
.page-num { position:fixed; top:60px; right:40px; font-size:120px; font-weight:900;
            font-style:italic; color:rgba(26,155,140,0.08); line-height:1;
            pointer-events:none; z-index:0; font-family:'Space Grotesk',sans-serif; }

/* Formula box */
.formula-box { background:#1A1A1A; color:#4FC3C0; font-family:'Space Mono',monospace;
               font-size:13px; padding:16px 20px; border-radius:6px; line-height:2; }

/* Scenario badge */
.badge-normal  { background:#1A9B8C; color:white; padding:3px 12px; border-radius:3px; font-size:12px; font-weight:700; }
.badge-mod     { background:#F5C542; color:#1A1A1A; padding:3px 12px; border-radius:3px; font-size:12px; font-weight:700; }
.badge-sev     { background:#E05C5C; color:white; padding:3px 12px; border-radius:3px; font-size:12px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar brand ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:24px 0 8px 0; text-align:center;'>
      <svg width='48' height='48' viewBox='0 0 64 64' fill='none'>
        <path d='M32 4 L56 16 L56 36 C56 49 44 58 32 62 C20 58 8 49 8 36 L8 16 Z'
              fill='none' stroke='#1A9B8C' stroke-width='2'/>
        <circle cx='32' cy='35' r='6' fill='none' stroke='#4FC3C0' stroke-width='1.5'/>
        <path d='M26 35 Q29 28 32 35 Q35 28 38 35' stroke='#4FC3C0' stroke-width='1.2' fill='none'/>
      </svg>
      <div style='font-family:Space Grotesk,sans-serif; font-weight:700; font-size:18px;
                  letter-spacing:0.12em; color:#4FC3C0; margin-top:6px;'>AEGIS</div>
      <div style='font-size:10px; color:#888; margin-top:2px; font-family:Space Mono,monospace;
                  letter-spacing:0.08em;'>SDG 6.4 · HACKATHON 2026</div>
    </div>
    <hr style='border-color:#333; margin:12px 0 20px 0;'>
    """, unsafe_allow_html=True)

# Redirect to main page if needed
pg = st.navigation([
    st.Page("pages/01_main.py",       title="MAIN",        icon="🏠"),
    st.Page("pages/02_team.py",       title="TEAM",        icon="👥"),
    st.Page("pages/03_modelo.py",     title="MODELO",      icon="📐"),
    st.Page("pages/04_simulacion.py", title="SIMULACIÓN",  icon="⚙️"),
    st.Page("pages/05_resultados.py", title="RESULTADOS",  icon="📊"),
    st.Page("pages/06_validacion.py", title="VALIDACIÓN",  icon="✅"),
    st.Page("pages/07_economics.py",  title="ECONOMICS",   icon="💹"),
    st.Page("pages/08_presentacion.py", title="SLIDES",    icon="🎞️"),
])
pg.run()
