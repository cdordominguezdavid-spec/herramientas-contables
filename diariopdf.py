import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Sistema Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Ahorro de Papel (Excel + PDF)")

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'
if 'excel_final' not in st.session_state:
    st.session_state.excel_final = None

# --- FUNCIÓN DE VALIDACIÓN ---
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
        if st.button("🚀 Generar Libro Optimizado", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        st.button("⏳ Procesando...", disabled=True)
        
        try:
            df = pd.read_excel(archivo)
            
            # Mapeo exacto de tus columnas según la imagen:
            c_fec, c_cta, c_des, c_com, c_con, c_deb, c_cre = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            # Procesamiento
            df[c_fec] = pd.to_datetime(df[c_fec], errors='coerce').ffill()
            df = df.dropna(subset=[c_fec])
            
            # Leyenda combinada
            df['Leyenda_Final'] = df.apply(lambda r: f"{str(r[c_con]) if pd.notna(r[c_con]) else ''} {str(r[c_com]) if pd.notna(r[c_com]) else ''}".strip(), axis=1)
            
            # Limpieza de valores
            for col in [c_deb, c_cre]:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            # Identificación de asientos (Bloques)
            df['ID_Asiento'] = (df[c_fec].dt.strftime('%d%m%Y') + df['Leyenda_Final']).ne((df[c_fec].dt.strftime('%d%m%Y') + df['Leyenda_Final']).shift()).cumsum()
            
            lista_final = []
            bloques = df['ID_Asiento'].unique()
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
                lista_final.append(bloque_export)
                # Separador de asiento
                lista_final.append(pd.DataFrame([["SEP_LINE"]*7], columns=bloque_export.columns))

            df_to_excel = pd.concat(lista_final, ignore_index=True)

            # --- EXCEL CON CONFIGURACIÓN DE IMPRESIÓN PRO ---
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Libro Diario")
                wb, ws = writer.book, writer.sheets['Libro Diario']
                
                # Fuente 7.5 para máximo ahorro
                f_base = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top', 'text_wrap': True})
                f_num = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'num_format': '#,##0.00;;', 'valign': 'top'})
                f_sep = wb.add_format({'bg_color': '#000000'})
                f_hdr = wb.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'font_size': 8, 'align': 'center'})

                # Configuración A4 y márgenes de 1cm
                ws.set_paper(9)
                ws.set_margins(0.3, 0.3, 0.4, 0.4)
                ws.fit_to_pages(1, 0)
                ws.set_header(f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL")
                ws.set_footer("&RPágina &P de &N")

                # Columnas ajustadas
                ws.set_column(0, 0, 8, f_base)   # Fecha
                ws.set_column(1, 1, 4, f_base)   # Nro
                ws.set_column(2, 2, 30, f_base)  # Leyenda
                ws.set_column(3, 3, 6, f_base)   # Cta
                ws.set_column(4, 4, 30, f_base)  # Desc
                ws.set_column(5, 6, 11, f_num)   # Debe/Haber

                for r_idx, row in df_to_excel.iterrows():
                    if row['Fecha'] == "SEP_LINE":
                        ws.set_row(r_idx + 1, 1.2, f_sep)
                        for c in range(7): ws.write(r_idx+1, c, "", f_sep)
                
                for c_idx, val in enumerate(df_to_excel.columns):
                    ws.write(0, c_idx, val, f_hdr)

            st.session_state.excel_final = buf.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error al procesar: {e}")
            st.session_state.paso = 'configuracion'

    if st.session_state.paso == 'listo':
        st.success("✅ ¡Libro generado con éxito!")
        st.info("💡 Para obtener el PDF: Abre el Excel descargado, pulsa F12 (Guardar como) y elige tipo PDF. ¡Ya está configurado para que salga perfecto en A4!")
        st.download_button("📥 Descargar Libro Diario Final", st.session_state.excel_final, f"Libro_Diario_{empresa}.xlsx")
        
        if st.button("🏁 Finalizar y Reiniciar"):
            st.session_state.clear()
            st.rerun()
