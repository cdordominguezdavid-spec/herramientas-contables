import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Motor Contable V3", layout="wide")

st.title("⚖️ Libro Diario: Generación Dual Optimizada")

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'

def validar_periodo(texto):
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    return (True, "") if re.match(patron, texto) else (False, "Formato: dd/mm/aaaa - dd/mm/aaaa")

archivo = st.file_uploader("1. Sube tu Libro Mayor", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Empresa:", disabled=(st.session_state.paso != 'configuracion'))
    with col2:
        periodo = st.text_input("Período:", placeholder="01/01/2026 - 31/12/2026", disabled=(st.session_state.paso != 'configuracion'))
    
    periodo_ok = False
    if periodo:
        es_valido, msg = validar_periodo(periodo)
        if not es_valido: st.error(msg)
        else: periodo_ok = True

    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Lanzar Generación", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        st.button("⏳ Procesando a máxima velocidad...", disabled=True)
        
        try:
            # 1. Lectura forzando tipos básicos para evitar el error de 'dtype str'
            df = pd.read_excel(archivo).astype(object) 
            
            # Nombres de columnas según tu imagen
            c_fec, c_cta, c_des, c_com, c_con, c_deb, c_cre = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"
            
            # 2. Limpieza segura de datos
            df[c_fec] = pd.to_datetime(df[c_fec], errors='coerce').ffill()
            df = df.dropna(subset=[c_fec])
            
            # Convertimos a string de forma segura manejando nulos
            df[c_con] = df[c_con].fillna("").astype(str)
            df[c_com] = df[c_com].fillna("").astype(str)
            df['Ley_F'] = df[c_con] + " " + df[c_com]
            
            # Limpieza de números (Debe/Haber)
            for c in [c_deb, c_cre]:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            # 3. Agrupación por Asiento
            df['ID'] = (df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).ne((df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).shift()).cumsum()
            
            # 4. Estructura de visualización (Dato solo en la 1ra fila del asiento)
            mask = df.duplicated(subset=['ID'])
            df.loc[mask, [c_fec, 'Ley_F']] = ""
            
            # Numeración de asientos
            asiento_nums = {id_as: f"{i+1:03d}" for i, id_as in enumerate(df['ID'].unique())}
            df['NRO'] = df['ID'].map(asiento_nums)
            df.loc[mask, 'NRO'] = ""

            df_final = df[[c_fec, 'NRO', 'Ley_F', c_cta, c_des, c_deb, c_cre]].copy()
            df_final.columns = ['Fecha', 'NRO.', 'Leyenda', 'Cuenta', 'Descripción', 'Debe', 'Haber']

            # --- EXCEL ---
            buf_ex = io.BytesIO()
            with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name="Diario")
                wb, ws = writer.book, writer.sheets['Diario']
                
                f_base = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top'})
                f_num  = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'num_format': '#,##0.00;;', 'valign': 'top'})
                f_hdr  = wb.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'font_size': 8})

                ws.set_paper(9); ws.set_margins(0.3, 0.3, 0.4, 0.4); ws.fit_to_pages(1, 0)
                ws.set_header(f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL")
                ws.set_footer("&RPágina &P de &N")
                
                ws.set_column(0,0,8,f_base); ws.set_column(1,1,4,f_base); ws.set_column(2,2,30,f_base)
                ws.set_column(3,3,7,f_base); ws.set_column(4,4,30,f_base); ws.set_column(5,6,11,f_num)

            st.session_state.excel_ready = buf_ex.getvalue()
            
            # --- PDF (HTML) ---
            html_table = df_final.to_html(index=False, border=0)
            st.session_state.html_ready = f"""
            <html><head><style>
                body {{ font-family: Arial; font-size: 7.5pt; margin: 0.5cm; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background: #eee; border: 1px solid black; padding: 3px; }}
                td {{ border-bottom: 0.1pt solid #ccc; padding: 2px; vertical-align: top; }}
                .header {{ display: flex; justify-content: space-between; font-weight: bold; border-bottom: 2px solid black; padding-bottom: 5px; margin-bottom: 10px; font-size: 9pt; }}
            </style></head><body>
                <div class="header"><div>{empresa} - {periodo}</div><div>DIARIO GENERAL</div></div>
                {html_table}
            </body></html>"""
            
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error al procesar: {e}")
            st.session_state.paso = 'configuracion'

if st.session_state.paso == 'listo':
    st.success("✅ Archivos listos para descargar.")
    c1, c2 = st.columns(2)
    with c1: st.download_button("📥 Descargar Excel", st.session_state.excel_ready, "Libro_Diario.xlsx")
    with c2: 
        st.download_button("📥 Descargar Reporte HTML (PDF)", st.session_state.html_ready.encode('utf-8'), "Reporte_Diario.html", "text/html")
        st.info("💡 Abre el archivo .html y presiona **Ctrl + P** para guardarlo como PDF. ¡Sale perfecto en A4!")
    
    if st.button("🏁 Finalizar y Reiniciar"):
        st.session_state.clear(); st.rerun()
