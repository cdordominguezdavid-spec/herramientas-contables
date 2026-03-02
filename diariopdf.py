import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Motor Contable Ultra-Rápido", layout="wide")

st.title("⚖️ Libro Diario: Generación Instantánea")

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'

# --- VALIDACIÓN RÁPIDA ---
def validar_periodo(texto):
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    match = re.match(patron, texto)
    if not match: return False, "Formato: dd/mm/aaaa - dd/mm/aaaa"
    return True, ""

archivo = st.file_uploader("1. Sube tu Libro Mayor", type=["xlsx", "xls"])

if archivo:
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Empresa:", disabled=(st.session_state.paso != 'configuracion'))
    with col2:
        periodo = st.text_input("Período:", placeholder="dd/mm/aaaa - dd/mm/aaaa", disabled=(st.session_state.paso != 'configuracion'))
    
    periodo_ok = False
    if periodo:
        es_valido, msg = validar_periodo(periodo)
        if not es_valido: st.error(msg)
        else: periodo_ok = True

    if st.session_state.paso == 'configuracion':
        # Botón que se desactiva al hacer clic
        if st.button("🚀 Lanzar Generación Rápida", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        # Botón gris de procesamiento
        st.button("⏳ Procesando a máxima velocidad...", disabled=True)
        
        try:
            # 1. Lectura veloz
            df = pd.read_excel(archivo)
            c_fec, c_cta, c_des, c_com, c_con, c_deb, c_cre = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"
            
            # 2. Limpieza masiva (sin bucles)
            df[c_fec] = pd.to_datetime(df[c_fec], errors='coerce').ffill()
            df = df.dropna(subset=[c_fec])
            df['Ley_F'] = df[c_con].astype(str).fillna('') + " " + df[c_com].astype(str).fillna('')
            df[c_deb] = pd.to_numeric(df[c_deb].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df[c_cre] = pd.to_numeric(df[c_cre].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            # 3. Identificar asientos en un solo paso
            df['ID'] = (df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).ne((df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).shift()).cumsum()
            
            # 4. Crear estructura final (Optimizada)
            # Solo dejamos los datos de cabecera en la primera fila de cada grupo
            mask_duplicados = df.duplicated(subset=['ID'])
            df.loc[mask_duplicados, [c_fec, 'Ley_F']] = ""
            df['NRO'] = ""
            df.loc[~mask_duplicados, 'NRO'] = range(1, df['ID'].nunique() + 1)
            df['NRO'] = df['NRO'].apply(lambda x: f"{x:03d}" if x != "" else "")

            # Reordenar columnas para el reporte
            df_final = df[[c_fec, 'NRO', 'Ley_F', c_cta, c_des, c_deb, c_cre]].copy()
            df_final.columns = ['Fecha', 'NRO.', 'Leyenda', 'Cuenta', 'Descripción', 'Debe', 'Haber']

            # --- GENERAR EXCEL (Sin Merges pesados para ganar velocidad) ---
            buf_ex = io.BytesIO()
            with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name="Libro Diario")
                wb, ws = writer.book, writer.sheets['Libro Diario']
                
                # Estilos básicos de alto rendimiento
                fmt = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top'})
                num = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'num_format': '#,##0.00;;', 'valign': 'top'})
                hdr = wb.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'font_size': 8})

                ws.set_paper(9); ws.set_margins(0.3, 0.3, 0.4, 0.4); ws.fit_to_pages(1, 0)
                ws.set_header(f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL")
                
                ws.set_column(0, 0, 8, fmt); ws.set_column(1, 1, 4, fmt)
                ws.set_column(2, 2, 30, fmt); ws.set_column(3, 3, 7, fmt)
                ws.set_column(4, 4, 30, fmt); ws.set_column(5, 6, 11, num)

            st.session_state.excel_ready = buf_ex.getvalue()
            
            # --- GENERAR HTML (Imprimible rápido) ---
            html_table = df_final.to_html(index=False, classes='tab')
            st.session_state.html_ready = f"""
            <html><head><style>
                body {{ font-family: Arial; font-size: 7.5pt; margin: 1cm; }}
                .tab {{ width: 100%; border-collapse: collapse; }}
                th {{ background: #eee; border: 1px solid black; padding: 2px; }}
                td {{ border: 0.1pt solid #ddd; padding: 2px; }}
                .header {{ display: flex; justify-content: space-between; font-weight: bold; border-bottom: 2px solid black; }}
            </style></head><body>
                <div class="header"><div>{empresa} - {periodo}</div><div>DIARIO GENERAL</div></div>
                {html_table}
            </body></html>"""
            
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}"); st.session_state.paso = 'configuracion'

# --- INTERFAZ FINAL ---
if st.session_state.paso == 'listo':
    st.success("✅ Generado en tiempo récord.")
    c1, c2 = st.columns(2)
    with c1: st.download_button("📥 Descargar Excel", st.session_state.excel_ready, "Diario.xlsx")
    with c2: st.download_button("📥 Descargar PDF (HTML)", st.session_state.html_ready.encode('utf-8'), "Diario.html", "text/html")
    
    if st.button("🏁 Reiniciar"):
        st.session_state.clear(); st.rerun()
