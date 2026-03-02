import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Motor Contable V3 - PDF Pro", layout="wide")

st.title("⚖️ Libro Diario: Generación Dual (Excel + PDF Oficial)")

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
        if st.button("🚀 Lanzar Generación (Excel + PDF)", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        st.button("⏳ Procesando a máxima velocidad...", disabled=True)
        
        try:
            # 1. Lectura robusta
            df = pd.read_excel(archivo).astype(object) 
            c_fec, c_cta, c_des, c_com, c_con, c_deb, c_cre = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"
            
            # 2. Limpieza
            df[c_fec] = pd.to_datetime(df[c_fec], errors='coerce').ffill()
            df = df.dropna(subset=[c_fec])
            df[c_con] = df[c_con].fillna("").astype(str)
            df[c_com] = df[c_com].fillna("").astype(str)
            df['Ley_F'] = df[c_con] + " " + df[c_com]
            for c in [c_deb, c_cre]:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            # 3. Identificar Asientos
            df['ID'] = (df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).ne((df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).shift()).cumsum()
            
            # 4. Estructura de Reporte
            mask = df.duplicated(subset=['ID'])
            asiento_nums = {id_as: f"{i+1:03d}" for i, id_as in enumerate(df['ID'].unique())}
            
            # Creamos el HTML con estilo de impresión
            html_rows = ""
            for i, row in df.iterrows():
                es_inicio = not mask[i]
                # Estilo para línea divisoria entre asientos
                row_style = "border-top: 1.5pt solid black;" if es_inicio and i > 0 else ""
                
                f_val = row[c_fec].strftime('%d/%m/%y') if es_inicio else ""
                n_val = asiento_nums[row['ID']] if es_inicio else ""
                l_val = row['Ley_F'] if es_inicio else ""
                d_val = f"{row[c_deb]:,.2f}" if row[c_deb] > 0 else ""
                h_val = f"{row[c_cre]:,.2f}" if row[c_cre] > 0 else ""
                
                html_rows += f"""
                <tr style="{row_style}">
                    <td style="font-weight:{'bold' if es_inicio else 'normal'}">{f_val}</td>
                    <td>{n_val}</td>
                    <td class="text-wrap">{l_val}</td>
                    <td>{row[c_cta]}</td>
                    <td class="text-wrap">{row[c_des]}</td>
                    <td class="num">{d_val}</td>
                    <td class="num">{h_val}</td>
                </tr>"""

            # --- CSS DE IMPRESIÓN PROFESIONAL ---
            full_html = f"""
            <html><head><style>
                @media print {{
                    @page {{ size: A4 portrait; margin: 1cm; }}
                    thead {{ display: table-header-group; }} /* Repite cabecera en cada hoja */
                    tfoot {{ display: table-footer-group; }}
                }}
                body {{ font-family: Arial, sans-serif; font-size: 7.5pt; line-height: 1.2; }}
                table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
                th {{ border: 1pt solid black; background: #f0f0f0; padding: 4px; font-size: 8pt; }}
                td {{ border: 0.1pt solid #ddd; padding: 2px 4px; vertical-align: top; word-wrap: break-word; }}
                .num {{ text-align: right; white-space: nowrap; }}
                .text-wrap {{ overflow: hidden; text-overflow: ellipsis; }}
                .header-table {{ width: 100%; margin-bottom: 10px; border: none; }}
                .header-table td {{ border: none; font-size: 10pt; font-weight: bold; }}
            </style></head><body>
                <table class="header-table">
                    <tr><td>{empresa} - {periodo}</td><td style="text-align:right">DIARIO GENERAL</td></tr>
                </table>
                <table>
                    <thead>
                        <tr>
                            <th style="width:10%">Fecha</th>
                            <th style="width:6%">Nro</th>
                            <th style="width:25%">Leyenda</th>
                            <th style="width:9%">Cuenta</th>
                            <th style="width:26%">Descripción</th>
                            <th style="width:12%">Debe</th>
                            <th style="width:12%">Haber</th>
                        </tr>
                    </thead>
                    <tbody>
                        {html_rows}
                    </tbody>
                </table>
            </body></html>"""

            # --- EXCEL (Mismo formato rápido) ---
            buf_ex = io.BytesIO()
            with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as writer:
                # Limpieza rápida para Excel
                df_ex = df.copy()
                df_ex.loc[mask, [c_fec, 'Ley_F']] = ""
                df_ex['NRO'] = df_ex['ID'].map(asiento_nums)
                df_ex.loc[mask, 'NRO'] = ""
                df_ex = df_ex[[c_fec, 'NRO', 'Ley_F', c_cta, c_des, c_deb, c_cre]]
                df_ex.columns = ['Fecha', 'NRO.', 'Leyenda', 'Cuenta', 'Descripción', 'Debe', 'Haber']
                
                df_ex.to_excel(writer, index=False, sheet_name="Diario")
                wb, ws = writer.book, writer.sheets['Diario']
                f_base = wb.add_format({'font_name': 'Arial', 'font_size': 7.5})
                f_num = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'num_format': '#,##0.00;;'})
                ws.set_column(0,1,8,f_base); ws.set_column(2,2,30,f_base)
                ws.set_column(3,3,8,f_base); ws.set_column(4,4,30,f_base); ws.set_column(5,6,12,f_num)

            st.session_state.excel_ready = buf_ex.getvalue()
            st.session_state.html_ready = full_html
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}"); st.session_state.paso = 'configuracion'

if st.session_state.paso == 'listo':
    st.success("✅ Generación finalizada.")
    c1, c2 = st.columns(2)
    with c1: st.download_button("📥 Excel Contable", st.session_state.excel_ready, "Libro_Diario.xlsx")
    with c2: 
        st.download_button("📥 Reporte PDF (Oficial)", st.session_state.html_ready.encode('utf-8'), "Reporte_Diario.html", "text/html")
    
    st.warning("⚠️ **INSTRUCCIÓN IMPORTANTE PARA EL PDF:**")
    st.write("1. Descarga el archivo **Reporte_Diario.html** y ábrelo en Chrome o Edge.")
    st.write("2. Presiona **Ctrl + P** (Imprimir).")
    st.write("3. En 'Destino', selecciona **Guardar como PDF**.")
    st.write("4. En 'Más opciones', asegúrate que **Gráficos de fondo** esté activado si quieres ver las líneas.")

    if st.button("🏁 Nuevo Reporte"):
        st.session_state.clear(); st.rerun()
