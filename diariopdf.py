import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Generador de Libro Diario", layout="wide")

st.title("⚖️ Libro Diario: Formato Excel Oficial")

if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'
if 'excel_final' not in st.session_state:
    st.session_state.excel_final = None

def validar_periodo(texto):
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    return (True, "") if re.match(patron, texto) else (False, "Formato: dd/mm/aaaa - dd/mm/aaaa")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Empresa:", disabled=(st.session_state.paso != 'configuracion'))
    with col2:
        periodo = st.text_input("Período:", placeholder="01/01/2026 - 31/01/2026", disabled=(st.session_state.paso != 'configuracion'))
    
    periodo_ok = False
    if periodo:
        es_valido, msg = validar_periodo(periodo)
        if not es_valido: st.error(msg)
        else: periodo_ok = True

    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Generar Libro Diario", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        st.button("⏳ Procesando...", disabled=True)
        
        try:
            # 1. Lectura
            df = pd.read_excel(archivo).astype(object) 
            c_fec, c_cta, c_des, c_com, c_con, c_deb, c_cre = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"
            
            # 2. Limpieza de datos
            df[c_fec] = pd.to_datetime(df[c_fec], errors='coerce').ffill()
            df = df.dropna(subset=[c_fec])
            df[c_con] = df[c_con].fillna("").astype(str)
            df[c_com] = df[c_com].fillna("").astype(str)
            df['Ley_F'] = (df[c_con] + " " + df[c_com]).str.strip()
            for c in [c_deb, c_cre]:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            # 3. Identificar Bloques (Asientos)
            df['ID'] = (df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).ne((df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).shift()).cumsum()
            
            # Preparar lista para exportar
            lista_final = []
            asientos_indices = []
            curr_row = 1
            bloques = df['ID'].unique()
            
            prog = st.progress(0)
            for i, b in enumerate(bloques, 1):
                prog.progress(i/len(bloques))
                sub = df[df['ID'] == b].copy()
                n = len(sub)
                
                bloque_export = pd.DataFrame({
                    'Fecha': [sub.iloc[0][c_fec].strftime('%d/%m/%y')] + [""]*(n-1),
                    'NRO.': [f"{i:03d}"] + [""]*(n-1),
                    'Leyenda': [sub.iloc[0]['Ley_F']] + [""]*(n-1),
                    'Cuenta': sub[c_cta].values,
                    'Descripción': sub[c_des].values,
                    'Debe': sub[c_deb].values,
                    'Haber': sub[c_cre].values
                })
                
                asientos_indices.append({'start': curr_row, 'end': curr_row + n - 1, 'len': n})
                lista_final.append(bloque_export)
                lista_final.append(pd.DataFrame([["SEP"]*7], columns=bloque_export.columns))
                curr_row += n + 1

            df_total = pd.concat(lista_final, ignore_index=True)

            # --- GENERAR EXCEL ---
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_total.to_excel(writer, index=False, sheet_name="Libro Diario")
                wb, ws = writer.book, writer.sheets['Libro Diario']
                
                # Formatos de ahorro de espacio
                f_base = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top'})
                f_num  = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'num_format': '#,##0.00;;', 'valign': 'top'})
                f_mrg  = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top', 'align': 'left', 'text_wrap': True})
                f_sep  = wb.add_format({'bg_color': '#000000'})
                f_hdr  = wb.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'font_size': 8})

                # Configuración A4 profesional
                ws.set_paper(9) # A4
                ws.set_margins(0.3, 0.3, 0.4, 0.4) # 1cm aprox
                ws.fit_to_pages(1, 0)
                ws.set_header(f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL")
                ws.set_footer("&RPágina &P de &N")
                ws.repeat_rows(0) # Repetir cabecera en cada hoja

                ws.set_column(0,0,8,f_base); ws.set_column(1,1,4,f_base); ws.set_column(2,2,28,f_base)
                ws.set_column(3,3,7,f_base); ws.set_column(4,4,28,f_base); ws.set_column(5,6,11,f_num)

                # Aplicar Merges y Líneas Separadoras
                for item in asientos_info_temp := asientos_indices:
                    if item['len'] >= 2:
                        s = item['start']
                        ws.merge_range(s, 0, s+1, 0, df_total.iloc[s-1]['Fecha'], f_mrg)
                        ws.merge_range(s, 1, s+1, 1, df_total.iloc[s-1]['NRO.'], f_mrg)
                        ws.merge_range(s, 2, s+1, 2, df_total.iloc[s-1]['Leyenda'], f_mrg)
                    
                    row_sep = item['end'] + 1
                    ws.set_row(row_sep, 1.2, f_sep)
                    for c in range(7): ws.write(row_sep, c, "", f_sep)

                for c_idx, val in enumerate(df_total.columns): ws.write(0, c_idx, val, f_hdr)

            st.session_state.excel_final = buf.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.paso = 'configuracion'

if st.session_state.paso == 'listo':
    st.success("✅ ¡Libro Diario generado!")
    st.download_button("📥 Descargar Libro Diario Excel", st.session_state.excel_final, f"Diario_{empresa}.xlsx")
    
    if st.button("🏁 Reiniciar"):
        st.session_state.clear()
        st.rerun()
