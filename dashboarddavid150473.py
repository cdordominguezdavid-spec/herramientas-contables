import streamlit as st

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Dashboard del Contador", layout="wide")

# --- ESTILOS PERSONALIZADOS (CSS) PARA BOTONES ---
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        color: #1E3A8A;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    /* Estilo para los botones/enlaces */
    .stButton > button, .btn-link {
        width: 100%;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 18px;
        border-radius: 10px;
        border: 2px solid #1E3A8A;
        background-color: white;
        color: #1E3A8A !important;
        text-decoration: none;
        transition: 0.3s;
        margin-bottom: 10px;
    }
    .stButton > button:hover, .btn-link:hover {
        background-color: #1E3A8A;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">DASHBOARD DEL CONTADOR</div>', unsafe_allow_html=True)

# --- CUADRÍCULA DE 15 BOTONES ---
cols = st.columns(3)

# Definición de los botones
# El primero es un link, los demás por ahora son placeholders
botones = [
    {"nombre": "⚖️ Libro Diario Pro", "url": "https://herramientas-contables-diariodavid150473.streamlit.app/"},
    {"nombre": "📊 Balance de Sumas y Saldos", "url": None},
    {"nombre": "🏦 Conciliación Bancaria", "url": None},
    {"nombre": "📑 Registro de Ventas", "url": None},
    {"nombre": "📝 Registro de Compras", "url": None},
    {"nombre": "🔍 Auditoría de Facturas", "url": None},
    {"nombre": "📈 Análisis de Gastos", "url": None},
    {"nombre": "📅 Agenda de Vencimientos", "url": None},
    {"nombre": "💵 Cálculo de Impuestos", "url": None},
    {"nombre": "📋 Gestión de Clientes", "url": None},
    {"nombre": "📂 Archivo Digital", "url": None},
    {"nombre": "💡 Proyecciones", "url": None},
    {"nombre": "⚙️ Configuración", "url": None},
    {"nombre": "❓ Ayuda / Soporte", "url": None},
    {"nombre": "🚪 Salir", "url": None},
]

for i, btn in enumerate(botones):
    with cols[i % 3]:
        if btn["url"]:
            # Botón 1: Link externo
            st.markdown(f'<a href="{btn["url"]}" target="_blank" class="btn-link">{btn["nombre"]}</a>', unsafe_allow_html=True)
        else:
            # Otros botones: Función normal de Streamlit por ahora
            if st.button(btn["nombre"], key=f"btn_{i}"):
                st.toast(f"Módulo '{btn['nombre']}' en desarrollo...")
