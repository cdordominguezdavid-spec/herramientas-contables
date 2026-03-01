import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Sistema Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato A4 Optimizado")

if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'
if 'excel_final' not in st.session_state:
    st.session_state.excel_final = None

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
        if st.button("🚀 Generar Libro Diario", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        st.button("⏳ Procesando...", disabled=True)
        
        try:
            df = pd.read_excel(archivo)
            c_fec, c_cta, c_des, c_com, c_con, c_deb, c_cre = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            df[c_fec] = pd.to_datetime(df[c_fec], errors='coerce').ffill()
            df = df.dropna(subset=[c_fec])
            df['Leyenda_Final'] = df.apply(lambda r: f"{str(r[c_con]) if pd.notna(r[c_con]) else ''} {str(r[c_com]) if pd.notna(r[c_com]) else ''}".strip(), axis=1)
            
            for col in [c_deb, c_cre]:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            df['ID_Asiento'] = (df[c_fec].dt.strftime('%d%m%Y') + df['Leyenda_Final']).ne((df[c_fec].dt.strftime('%d%m%Y') + df['Leyenda_Final']).shift()).cumsum()
            
            lista_final = []
            asientos_indices = []
            bloques = df['ID_Asiento'].unique()
            current_row = 1 # Excel empieza en 1 (header es 0)
            
            prog = st.progress(0)
            for i, b in enumerate(bloques, 1):
                prog.progress(i/len(bloques))
                sub = df[df['ID_Asiento'] == b].copy()
                n = len(sub)
                
                bloque_export = pd.DataFrame({
                    'Fecha': [sub.iloc[0][c_fec].strftime('%d/%m/%y')] + [""]*(n-1),
                    'NRO.': [f"{i:03d}"] + [""]*(n-1),
                    'Leyenda': [sub.iloc[0]['Leyenda_Final']] + [""]*(n-1),
                    'Cuenta': sub[c_cta].values,
                    'Descripción': sub[c_des].values,
                    'Debe': sub[c_deb].values,
                    'Haber': sub[c_cre].values
                })
                
                # Guardamos dónde empieza y termina para hacer el Merge luego
                asientos_indices.append({'start': current_row, 'end': current_row + n - 1, 'len': n})
                lista_final.append(bloque_export)
                lista_final.append(pd.DataFrame([["SEP_LINE"]*7], columns=bloque_export.columns))
                current_row += n + 1

            df_to_excel = pd.concat(lista_final, ignore_index=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Libro Diario")
                wb, ws = writer.book, writer.sheets['Libro Diario']
                
                # FORMATOS (Fuente 7.5 para ahorro de papel)
                f_base = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top', 'text_wrap': True})
                f_num  = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'num_format': '#,##0.00;;', 'valign': 'top'})
                f_merge = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top', 'align': 'left', 'text_wrap': True})
                f_sep  = wb.add_format({'bg_color': '#000000'})
                f_hdr  = wb.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'font_size': 8, 'align': 'center'})

                # CONFIGURACIÓN DE IMPRESIÓN A4
                ws.set_paper(9)
                ws.set_margins(0.3, 0.3, 0.4, 0.4) # Margen 1cm para evitar pisar header
                ws.fit_to_pages(1, 0)
                ws.set_header(f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL")
                ws.set_footer("&RPágina &P de &N")

                ws.set_column(0, 0, 8, f_base)   # Fecha
                ws.set_column(1, 1, 4, f_base)   # NRO.
                ws.set_column(2, 2, 30, f_base)  # Leyenda
                ws.set_column(3, 3, 6, f_base)   # Cuenta
                ws.set_column(4, 4, 30, f_base)  # Descripción
                ws.set_column(5, 6, 11, f_num)   # Debe/Haber

                # Aplicar Merges de 2 filas y Líneas Negras
                for idx in asientos_indices:
                    # Si el asiento tiene 2 o más filas, unimos las primeras 2 de Fecha, NRO y Leyenda
                    if idx['len'] >= 2:
                        # Rango: (fila_inicio, col, fila_fin, col, dato, formato)
                        # Nota: idx['start'] es la fila en el DF (+1 por el header de Excel)
                        row_s = idx['start']
                        ws.merge_range(row_s, 0, row_s + 1, 0, df_to_excel.iloc[row_s-1]['Fecha'], f_merge)
                        ws.merge_range(row_s, 1, row_s + 1, 1, df_to_excel.iloc[row_s-1]['NRO.'], f_merge)
                        ws.merge_range(row_s, 2, row_s + 1, 2, df_to_excel.iloc[row_s-1]['Leyenda'], f_merge)
                    
                    # Línea negra al final del bloque
                    row_negra = idx['end'] + 1
                    ws.set_row(row_negra, 1.5, f_sep)
                    for c in range(7): ws.write(row_negra, c, "", f_sep)
                
                for c_idx, val in enumerate(df_to_excel.columns):
                    ws.write(0, c_idx, val, f_hdr)

            st.session_state.excel_final = buf.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.paso = 'configuracion'

    if st.session_state.paso == 'listo':
        st.success("✅ ¡Libro Diario generado con éxito!")
        st.download_button("📥 Descargar Libro Diario Final", st.session_state.excel_final, f"Diario_{empresa}.xlsx")
        
        if st.button("🏁 Finalizar y Reiniciar"):
            st.session_state.clear()
            st.rerun()
