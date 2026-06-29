import streamlit as st

st.markdown('<div class="page-num">03</div>', unsafe_allow_html=True)
st.markdown("### 📐 *MODELO MILP — FORMULACIÓN*")
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown("Mixed Integer Linear Programming · baseline clásico que el enfoque cuántico debe replicar.")
st.markdown("---")

with st.expander("📖 Fórmula implementada", expanded=True):
    st.markdown("""
    <div class='formula-box'>
      <b style='color:#F4F1EA;'>min</b>  <span style='color:#4FC3C0;'>wU</span> · Σⱼ (u<sup>urb</sup>ⱼ / D<sup>urb</sup>ⱼ)
           + <span style='color:#F5C542;'>wA</span> · Σⱼ (u<sup>agri</sup>ⱼ / D<sup>agri</sup>ⱼ)
           + λ · Σᵢⱼ cᵢⱼ (x<sup>urb</sup>ᵢⱼ + x<sup>agri</sup>ᵢⱼ)<br><br>
      <span style='color:#888;font-size:11px;'>// NWWD: Normalized Weighted Water Deficit</span><br>
      <span style='color:#888;font-size:11px;'>// wU=10 (urbano tiene mayor prioridad) · wA=3 (agrícola)</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### Restricciones del modelo")
    st.markdown("""
    <div style='background:white;border:1px solid #E0DDD6;border-radius:6px;padding:20px;'>
      <div style='margin-bottom:14px;'>
        <span class='tag'>Capacidad fuente</span><br>
        <code style='font-size:13px;'>Σⱼ (x<sup>urb</sup>ᵢⱼ + x<sup>agri</sup>ᵢⱼ) ≤ A<sup>eff</sup>ᵢ   ∀i</code>
      </div>
      <div style='margin-bottom:14px;'>
        <span class='tag'>Balance urbano</span><br>
        <code style='font-size:13px;'>Σᵢ x<sup>urb</sup>ᵢⱼ + u<sup>urb</sup>ⱼ = D<sup>urb</sup>ⱼ   ∀j</code>
      </div>
      <div style='margin-bottom:14px;'>
        <span class='tag tag-yellow'>Balance agrícola</span><br>
        <code style='font-size:13px;'>Σᵢ x<sup>agri</sup>ᵢⱼ + u<sup>agri</sup>ⱼ = D<sup>agri</sup>ⱼ   ∀j</code>
      </div>
      <div>
        <span class='tag'>No-negatividad</span><br>
        <code style='font-size:13px;'>x<sup>urb</sup>ᵢⱼ, x<sup>agri</sup>ᵢⱼ, u<sup>urb</sup>ⱼ, u<sup>agri</sup>ⱼ ≥ 0</code>
      </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("#### Variables del modelo")
    st.markdown("""
    <div style='background:white;border:1px solid #E0DDD6;border-radius:6px;padding:20px;'>
      <table style='width:100%;font-size:13px;border-collapse:collapse;'>
        <tr style='border-bottom:1px solid #eee;'>
          <td style='padding:8px 0;'><code>x<sup>urb</sup>ᵢⱼ</code></td>
          <td style='color:#666;padding:8px;'>Vol. asignado fuente i → urbano municipio j</td>
        </tr>
        <tr style='border-bottom:1px solid #eee;'>
          <td style='padding:8px 0;'><code>x<sup>agri</sup>ᵢⱼ</code></td>
          <td style='color:#666;padding:8px;'>Vol. asignado fuente i → agrícola municipio j</td>
        </tr>
        <tr style='border-bottom:1px solid #eee;'>
          <td style='padding:8px 0;'><code>A<sup>eff</sup>ᵢ = αAᵢ</code></td>
          <td style='color:#666;padding:8px;'>Disponibilidad ajustada por sequía</td>
        </tr>
        <tr style='border-bottom:1px solid #eee;'>
          <td style='padding:8px 0;'><code>u<sup>urb</sup>ⱼ</code></td>
          <td style='color:#666;padding:8px;'>Déficit urbano municipio j</td>
        </tr>
        <tr>
          <td style='padding:8px 0;'><code>u<sup>agri</sup>ⱼ</code></td>
          <td style='color:#666;padding:8px;'>Déficit agrícola municipio j</td>
        </tr>
      </table>
      <div style='margin-top:14px;padding:10px;background:#F4F1EA;border-radius:4px;
                  font-family:Space Mono,monospace;font-size:12px;color:#555;'>
        Instancia benchmark: 2 fuentes × 3 municipios × 2 categorías<br>
        → <b>18 variables continuas</b> · solver HiGHS (scipy)
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("#### Red fuente–municipio con costos")

# Visualización de la red como tabla de costos
import pandas as pd
costs_df = pd.DataFrame({
    "Fuente \\ Municipio": ["Valle de Puebla", "Atlixco-Izúcar"],
    "Puebla":        [1.0, 2.8],
    "S.A. Cholula":  [1.2, 2.0],
    "Atlixco":       [2.5, 1.0],
}).set_index("Fuente \\ Municipio")

st.dataframe(
    costs_df.style
        .background_gradient(cmap="YlGn", axis=None)
        .format("{:.1f}"),
    use_container_width=True
)
st.caption("Costos cᵢⱼ — representan distancia/dificultad relativa de distribución (no costo real de infraestructura).")
