import streamlit as st
import pandas as pd
import io
import re

# Configuración de página
st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Generación de Reportes A4")

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'
if 'excel_data' not in st.session_state:
    st.session_state.excel_data = None
if 'html_data' not in st.session_state:
    st.session_state.html_data = None

# --- FUNCIÓN VALIDACIÓN ---
def validar_periodo(texto):
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    match = re.match(patron, texto)
    if not match: return False, "Formato requerido: dd/mm/aaaa - dd/mm/aaaa"
    v = match.groups()
    try:
        if not (1 <= int(v[0]) <= 31) or not (1 <= int(v[3]) <= 31): return False, "Día inválido (1-31)"
        if not (1 <= int(v[1]) <= 12) or not (1 <= int(v[4]) <= 12): return False, "Mes inválido (1-12)"
        if not (1900 <= int(v[2]) <= 2050) or not (1900 <= int(v[5]) <= 2050): return False, "Año fuera de rango"
        return True, ""
    except: return False, "Error en formato numérico"

archivo = st.file_uploader("1. Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Nombre de la Empresa:", disabled=(st.session_state.paso != 'configuracion'))
    with col2:
        periodo = st.text_input("Período (dd/mm/aaaa - dd/mm/aaaa):", placeholder="01/01/2026 - 31/01/2026", disabled=(st.session_state.paso != 'configuracion'))
    
    periodo_ok = False
    if periodo:
        es_valido, msg = validar_periodo(periodo)
        if not es_valido: st.error(msg)
        else: periodo_ok = True

    # --- LÓGICA DE BOTONES ---
    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Generar Libros (Excel y PDF)", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()
    else:
        st.button("⏳ Procesando con ahorro de papel...", disabled=True)
        
        try:
            # Procesamiento de datos (Columnas según tu imagen)
            df = pd.read_excel(archivo)
            c_fec, c_cta, c_des, c_com, c_con, c_deb, c_cre = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"
            
            df[c_fec] = pd.to_datetime(df[c_fec], errors='coerce').ffill()
            df = df.dropna(subset=[c_fec])
            df['Ley_F'] = df.apply(lambda r: f"{str(r[c_con]) if pd.notna(r[c_con]) else ''} {str(r[c_com]) if pd.notna(r[c_com]) else ''}".strip(), axis=1)
            for col in [c_deb, c_cre]:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            # Identificador de Asiento
            df['ID'] = (df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).ne((df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).shift()).cumsum()
            
            lista_final = []
            asientos_info = []
            curr_row = 1
            bloques = df['ID'].unique()
            prog = st.progress(0)

            for i, b in enumerate(bloques, 1):
                prog.progress(i/len(bloques))
                sub = df[df['ID'] == b].copy()
                n = len(sub)
                
                df_b = pd.DataFrame({
                    'Fecha': [sub.iloc[0][c_fec].strftime('%d/%m/%y')] + [""]*(n-1),
                    'NRO.': [f"{i:03d}"] + [""]*(n-1),
                    'Leyenda': [sub.iloc[0]['Ley_F']] + [""]*(n-1),
                    'Cuenta': sub[c_cta].values,
                    'Descripción': sub[c_des].values,
                    'Debe': sub[c_deb].values,
                    'Haber': sub[c_cre].values
                })
                asientos_info.append({'start': curr_row, 'end': curr_row + n - 1, 'len': n})
                lista_final.append(df_b)
                lista_final.append(pd.DataFrame([["SEP"]*7], columns=df_b.columns))
                curr_row += n + 1

            df_total = pd.concat(lista_final, ignore_index=True)

            # --- 1. GENERAR EXCEL CON MERGE ---
            buf_ex = io.BytesIO()
            with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as writer:
                df_total.to_excel(writer, index=False, sheet_name="Diario")
                wb, ws = writer.book, writer.sheets['Diario']
                
                f_base = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top'})
                f_num  = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'num_format': '#,##0.00;;', 'valign': 'top'})
                f_mrg  = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top', 'align': 'left', 'text_wrap': True})
                f_sep  = wb.add_format({'bg_color': '#000000'})
                f_hdr  = wb.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'font_size': 8})

                ws.set_paper(9); ws.set_margins(0.3, 0.3, 0.4, 0.4); ws.fit_to_pages(1, 0)
                ws.set_header(f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL")
                ws.set_column(0,0,8,f_base); ws.set_column(1,1,4,f_base); ws.set_column(2,2,30,f_base)
                ws.set_column(3,3,7,f_base); ws.set_column(4,4,30,f_base); ws.set_column(5,6,11,f_num)

                for item in asientos_info:
                    if item['len'] >= 2:
                        s = item['start']
                        ws.merge_range(s, 0, s+1, 0, df_total.iloc[s-1]['Fecha'], f_mrg)
                        ws.merge_range(s, 1, s+1, 1, df_total.iloc[s-1]['NRO.'], f_mrg)
                        ws.merge_range(s, 2, s+1, 2, df_total.iloc[s-1]['Leyenda'], f_mrg)
                    ws.set_row(item['end']+1, 1.2, f_sep)
                for c_idx, val in enumerate(df_total.columns): ws.write(0, c_idx, val, f_hdr)

            st.session_state.excel_data = buf_ex.getvalue()

            # --- 2. GENERAR HTML (PARA PDF) ---
            html = f"""
            <html><head><style>
                @page {{ size: A4; margin: 1cm; }}
                body {{ font-family: Arial, sans-serif; font-size: 7.5pt; color: #333; }}
                .header {{ display: flex; justify-content: space-between; font-weight: bold; border-bottom: 1px solid black; margin-bottom: 5px; font-size: 9pt; }}
                table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
                th {{ background: #eee; border: 0.5pt solid black; padding: 2px; font-size: 8pt; }}
                td {{ border: 0.1pt solid #ddd; padding: 2px; vertical-align: top; overflow: hidden; }}
                .sep {{ background: black; height: 2px; padding: 0; border: none; }}
                .num {{ text-align: right; font-family: 'Courier New', monospace; }}
                .merge {{ font-weight: bold; color: #000; }}
            </style></head><body>
                <div class="header"><div>{empresa} - {periodo}</div><div>DIARIO GENERAL</div></div>
                <table><thead><tr><th style="width:10%">Fecha</th><th style="width:5%">Nro</th><th style="width:25%">Leyenda</th><th style="width:8%">Cta</th><th style="width:28%">Descripción</th><th style="width:12%">Debe</th><th style="width:12%">Haber</th></tr></thead><tbody>
            """
            for _, r in df_total.iterrows():
                if r['Fecha'] == "SEP":
                    html += '<tr><td colspan="7" class="sep"></td></tr>'
                else:
                    d = f"{r['Debe']:,.2f}" if r['Debe'] > 0 else ""
                    h = f"{r['Haber']:,.2f}" if r['Haber'] > 0 else ""
                    html += f"<tr><td>{r['Fecha']}</td><td>{r['NRO.']}</td><td>{r['Leyenda']}</td><td>{r['Cuenta']}</td><td>{r['Descripción']}</td><td class='num'>{d}</td><td class='num'>{h}</td></tr>"
            html += "</tbody></table></body></html>"
            
            st.session_state.html_data = html
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error técnico: {e}")
            st.session_state.paso = 'configuracion'

# --- INTERFAZ DE DESCARGA ---
if st.session_state.paso == 'listo':
    st.success("✅ ¡Libro Diario generado exitosamente!")
    
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button("📥 Descargar Excel (Con Merge)", st.session_state.excel_data, f"Diario_{empresa}.xlsx")
    with col_dl2:
        st.download_button("📥 Descargar Reporte PDF (HTML)", st.session_state.html_data.encode('utf-8'), f"Diario_{empresa}.html", "text/html")
        st.info("💡 **Instrucción para PDF:** Abre el archivo .html y presiona **Ctrl + P**. Elige 'Guardar como PDF'. Saldrá perfecto en A4.")

    if st.button("🏁 Finalizar y Reiniciar"):
        st.session_state.clear()
        st.rerun()
