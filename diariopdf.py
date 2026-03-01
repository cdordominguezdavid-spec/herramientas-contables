import streamlit as st
import pandas as pd
import io
import re
import base64

st.set_page_config(page_title="Sistema Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Generación Dual (Excel + PDF)")

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'
if 'excel_final' not in st.session_state:
    st.session_state.excel_final = None

# --- VALIDACIÓN DE PERÍODO ---
def validar_periodo(texto):
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    match = re.match(patron, texto)
    if not match: return False, "Formato: dd/mm/aaaa - dd/mm/aaaa"
    v = match.groups()
    try:
        if not (1 <= int(v[0]) <= 31) or not (1 <= int(v[3]) <= 31): return False, "Día inválido"
        if not (1 <= int(v[1]) <= 12) or not (1 <= int(v[4]) <= 12): return False, "Mes inválido"
        if not (1900 <= int(v[2]) <= 2050) or not (1900 <= int(v[5]) <= 2050): return False, "Año fuera de rango"
        return True, ""
    except: return False, "Error numérico"

archivo = st.file_uploader("Sube tu Libro Mayor", type=["xlsx", "xls"])

if archivo:
    # Identificación automática de columnas por tu imagen
    c_fec, c_cta, c_des, c_com, c_con, c_deb, c_cre = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"
    
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

    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Lanzar Generación (Excel + PDF)", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        st.button("⏳ Procesando con ahorro de papel...", disabled=True)
        
        try:
            df = pd.read_excel(archivo)
            df[c_fec] = pd.to_datetime(df[c_fec], errors='coerce').ffill()
            df = df.dropna(subset=[c_fec])
            df['Ley_F'] = df.apply(lambda r: f"{str(r[c_con]) if pd.notna(r[c_con]) else ''} {str(r[c_com]) if pd.notna(r[c_com]) else ''}".strip(), axis=1)
            for c in [c_deb, c_cre]: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            
            # Identificador de Asiento
            df['ID'] = (df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).ne((df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).shift()).cumsum()
            
            lista_ex = []
            idx_asientos = []
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
                idx_asientos.append({'start': curr_row, 'end': curr_row + n - 1, 'len': n})
                lista_ex.append(df_b)
                lista_ex.append(pd.DataFrame([["SEP"]*7], columns=df_b.columns))
                curr_row += n + 1

            df_total = pd.concat(lista_ex, ignore_index=True)

            # --- GENERAR EXCEL ---
            buf_ex = io.BytesIO()
            with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as writer:
                df_total.to_excel(writer, index=False, sheet_name="Diario")
                wb, ws = writer.book, writer.sheets['Diario']
                
                f_base = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top'})
                f_num = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'num_format': '#,##0.00;;', 'valign': 'top'})
                f_mrg = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top', 'align': 'left', 'text_wrap': True})
                f_sep = wb.add_format({'bg_color': '#000000'})
                f_hdr = wb.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'font_size': 8})

                ws.set_paper(9); ws.set_margins(0.3, 0.3, 0.4, 0.4); ws.fit_to_pages(1, 0)
                ws.set_header(f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL")
                ws.set_column(0,0,8,f_base); ws.set_column(1,1,4,f_base); ws.set_column(2,2,30,f_base)
                ws.set_column(3,3,7,f_base); ws.set_column(4,4,30,f_base); ws.set_column(5,6,11,f_num)

                for item in idx_asientos:
                    if item['len'] >= 2:
                        s = item['start']
                        ws.merge_range(s, 0, s+1, 0, df_total.iloc[s-1]['Fecha'], f_mrg)
                        ws.merge_range(s, 1, s+1, 1, df_total.iloc[s-1]['NRO.'], f_mrg)
                        ws.merge_range(s, 2, s+1, 2, df_total.iloc[s-1]['Leyenda'], f_mrg)
                    ws.set_row(item['end']+1, 1.2, f_sep)
                for c_idx, val in enumerate(df_total.columns): ws.write(0, c_idx, val, f_hdr)

            st.session_state.excel_final = buf_ex.getvalue()
            
            # --- GENERAR "PDF" (HTML Imprimible) ---
            # Para evitar errores de librerías, generamos un HTML optimizado para imprimir
            html = f"""
            <html><head><style>
                body {{ font-family: Arial; font-size: 8pt; margin: 1cm; }}
                table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
                th {{ background: #eee; border: 1px solid black; padding: 2px; font-size: 9pt; }}
                td {{ border: 0.1pt solid #ccc; padding: 2px; vertical-align: top; overflow: hidden; }}
                .sep {{ background: black; height: 2px; }}
                .num {{ text-align: right; }}
                .header {{ display: flex; justify-content: space-between; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid black; }}
            </style></head><body>
                <div class="header"><div>{empresa} - {periodo}</div><div>DIARIO GENERAL</div></div>
                <table><thead><tr><th>Fecha</th><th>Nro</th><th>Leyenda</th><th>Cta</th><th>Descripción</th><th>Debe</th><th>Haber</th></tr></thead><tbody>
            """
            for _, r in df_total.iterrows():
                if r['Fecha'] == "SEP":
                    html += '<tr><td colspan="7" class="sep"></td></tr>'
                else:
                    d = f"{r['Debe']:,.2f}" if r['Debe'] > 0 else ""
                    h = f"{r['Haber']:,.2f}" if r['Haber'] > 0 else ""
                    html += f"<tr><td>{r['Fecha']}</td><td>{r['NRO.']}</td><td>{r['Leyenda']}</td><td>{r['Cuenta']}</td><td>{r['Descripción']}</td><td class="num">{d}</td><td class="num">{h}</td></tr>"
            html += "</tbody></table></body></html>"
            
            st.session_state.pdf_html = html
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}"); st.session_state.paso = 'configuracion'

    if st.session_state.paso == 'listo':
        st.success("✅ ¡Archivos listos!")
        col_ex, col_pdf = st.columns(2)
        with col_ex:
            st.download_button("📥 Descargar Excel", st.session_state.excel_final, f"Diario_{empresa}.xlsx")
        with col_pdf:
            # Truco: El PDF se descarga como HTML que al abrirse en Chrome y darle a Imprimir -> Guardar como PDF queda perfecto.
            st.download_button("📥 Descargar PDF (Formato Web)", st.session_state.pdf_html.encode('utf-8'), f"Diario_{empresa}.html", "text/html")
            st.info("👆 Abre el archivo descargado y presiona Ctrl+P para guardarlo como PDF oficial.")
        
        if st.button("🏁 Finalizar"):
            st.session_state.clear(); st.rerun()
