"""Estilos Tailwind CSS v4, tokens UPC y limpieza del chrome nativo de Streamlit."""

from __future__ import annotations

import streamlit as st

UPC_GREEN = "#006837"
UPC_GREEN_DARK = "#004D28"
UPC_EMERALD = "#10B981"
UPC_SLATE_DARK = "#0F172A"
UPC_SURFACE = "#F8FAFC"
UPC_MUTED = "#475569"

_TAILWIND_BLOCK = """<script src="https://cdn.tailwindcss.com"></script>
<script>
if (window.tailwind) {
  window.tailwind.config = {
    theme: {
      extend: {
        colors: {
          upc: {
            green: '#006837',
            dark: '#004D28',
            emerald: '#10B981',
            slate: '#0F172A',
            surface: '#F8FAFC'
          }
        }
      }
    }
  };
}
</script>"""


def inject_upc_styles() -> None:
    """Inyecta Tailwind CSS CDN, tokens UPC y oculta por completo el chrome nativo de Streamlit."""
    st.markdown(_TAILWIND_BLOCK, unsafe_allow_html=True)
    st.markdown(
        f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
#MainMenu {{ visibility: hidden !important; display: none !important; }}
header[data-testid="stHeader"] {{ visibility: hidden !important; height: 0 !important; display: none !important; }}
div[data-testid="stToolbar"] {{ visibility: hidden !important; display: none !important; }}
.stDeployButton, [data-testid="stAppDeployButton"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}
footer {{ visibility: hidden !important; display: none !important; }}
html, body, [class*="css"] {{
  font-family: 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: {UPC_SLATE_DARK};
}}
.stApp {{
  background-color: {UPC_SURFACE};
}}
.block-container {{
  padding-top: 1.25rem !important;
  padding-bottom: 2.5rem !important;
  max-width: 1320px;
}}
.stMarkdown p, .stMarkdown li {{
  font-size: 15.5px;
  line-height: 1.6;
}}
.upc-public-nav {{
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(8px);
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 0.85rem 1.35rem;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.25rem;
}}
.upc-nav-links {{
  display: flex;
  gap: 1.4rem;
  align-items: center;
}}
.upc-nav-links a {{
  color: {UPC_SLATE_DARK};
  text-decoration: none;
  font-weight: 600;
  font-size: 0.92rem;
  transition: color 0.15s ease;
}}
.upc-nav-links a:hover {{
  color: {UPC_GREEN};
}}
.casagbi-hero {{
  background: linear-gradient(135deg, {UPC_SLATE_DARK} 0%, {UPC_GREEN_DARK} 48%, {UPC_GREEN} 85%, {UPC_EMERALD} 100%);
  color: #FFFFFF;
  padding: 2.25rem 2.4rem;
  border-radius: 20px;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.14);
  margin-bottom: 1rem;
}}
.casagbi-hero h1 {{
  color: #FFFFFF !important;
  font-size: 2.15rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.18;
  margin: 0.45rem 0 0.75rem 0;
}}
.casagbi-hero p {{
  color: #E2F5EA !important;
  font-size: 1.02rem;
  line-height: 1.6;
  margin: 0;
}}
.upc-hero-tag {{
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(16, 185, 129, 0.45);
  color: #D1FAE5;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}}
.upc-breadcrumb {{
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.84rem;
  color: {UPC_MUTED};
  margin-bottom: 0.65rem;
  font-weight: 500;
}}
.upc-breadcrumb strong {{
  color: {UPC_GREEN};
  font-weight: 700;
}}
.upc-card {{
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 1.2rem 1.35rem;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
  margin-bottom: 0.95rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}}
.upc-card:hover {{
  border-color: #BAE6FD;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}}
.upc-card-accent {{
  background: #FFFFFF;
  border: 1px solid #D1FAE5;
  border-left: 5px solid {UPC_GREEN};
  border-radius: 16px;
  padding: 1.2rem 1.35rem;
  box-shadow: 0 4px 14px rgba(0, 104, 55, 0.06);
  margin-bottom: 1rem;
}}
.upc-kpi-card {{
  background: #FFFFFF;
  border-top: 1px solid #E2E8F0;
  border-right: 1px solid #E2E8F0;
  border-bottom: 1px solid #E2E8F0;
  border-left: 4px solid {UPC_GREEN};
  border-radius: 14px;
  padding: 1rem 1.15rem;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
  margin-bottom: 0.6rem;
}}
.upc-kpi-label {{
  font-size: 0.78rem;
  font-weight: 700;
  color: {UPC_MUTED};
  text-transform: uppercase;
  letter-spacing: 0.04em;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}}
.upc-kpi-value {{
  font-size: 1.75rem;
  font-weight: 800;
  color: {UPC_SLATE_DARK};
  margin-top: 0.25rem;
  letter-spacing: -0.02em;
}}
.upc-kpi-delta-pos {{
  display: inline-block;
  font-size: 0.76rem;
  font-weight: 700;
  color: #166534;
  background: #DCFCE7;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  margin-top: 0.35rem;
}}
.upc-kpi-delta-warn {{
  display: inline-block;
  font-size: 0.76rem;
  font-weight: 700;
  color: #92400E;
  background: #FEF3C7;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  margin-top: 0.35rem;
}}
.badge-pill {{
  display: inline-flex;
  align-items: center;
  gap: 0.32rem;
  padding: 0.22rem 0.65rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 700;
  line-height: 1.25;
}}
.badge-green {{ background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; }}
.badge-yellow {{ background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; }}
.badge-red {{ background: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; }}
.badge-blue {{ background: #DBEAFE; color: #1E40AF; border: 1px solid #93C5FD; }}
.badge-slate {{ background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; }}
.badge-emerald {{ background: #D1FAE5; color: #065F46; border: 1px solid #6EE7B7; }}
div.stButton > button[kind="primary"] {{
  background-color: {UPC_GREEN};
  border-color: {UPC_GREEN};
  color: #FFFFFF;
  font-weight: 600;
  border-radius: 10px;
  transition: all 0.15s ease;
}}
div.stButton > button[kind="primary"]:hover {{
  background-color: {UPC_GREEN_DARK};
  border-color: {UPC_GREEN_DARK};
  box-shadow: 0 4px 12px rgba(0, 104, 55, 0.22);
}}
div.stButton > button[kind="secondary"] {{
  border-radius: 10px;
  font-weight: 600;
  border-color: #CBD5E1;
}}
section[data-testid="stSidebar"] {{
  background-color: #FFFFFF;
  border-right: 1px solid #E2E8F0;
}}
.upc-timeline-item {{
  border-left: 2px solid #CBD5E1;
  padding-left: 0.9rem;
  padding-bottom: 0.75rem;
  margin-left: 0.45rem;
  position: relative;
}}
.upc-timeline-item::before {{
  content: "";
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: {UPC_GREEN};
  border: 2px solid #FFFFFF;
  box-shadow: 0 0 0 2px #A7F3D0;
  position: absolute;
  left: -6px;
  top: 4px;
}}
.chat-bubble-user {{
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
  border-radius: 14px;
  padding: 0.8rem 1rem;
  margin-bottom: 0.55rem;
}}
.chat-bubble-tech {{
  background: #FFFFFF;
  border: 1px solid #CBD5E1;
  border-radius: 14px;
  padding: 0.8rem 1rem;
  margin-bottom: 0.55rem;
}}
.upc-tool-chip {{
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: #F1F5F9;
  color: {UPC_SLATE_DARK};
  border: 1px solid #CBD5E1;
  border-radius: 8px;
  padding: 0.18rem 0.55rem;
  font-size: 0.74rem;
  font-weight: 700;
  margin-bottom: 0.35rem;
}}
</style>""",
        unsafe_allow_html=True,
    )


def hide_sidebar_for_public_landing() -> None:
    """Oculta la barra lateral técnica cuando el visitante no ha iniciado sesión."""
    st.markdown(
        """<style>
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
</style>""",
        unsafe_allow_html=True,
    )
