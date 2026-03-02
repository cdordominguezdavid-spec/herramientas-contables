import streamlit as st
import pandas as pd
import io
import re

# Configuración de página
st.set_page_config(page_title="Motor Contable Pro - Vertical Optimizado", layout="wide")

st.title("⚖️ Libro Diario: Formato Vertical de Máxima Densidad")

# --- FUNCIONES DE APOYO ---
def validar_periodo(texto):
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    match = re.match(patron, texto)
    return (True, "") if match else (False, "Formato: dd/mm/aaaa - dd/mm/aaaa")

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'
if 'excel_final' not in st.session_state:
    st.session_state.excel_final = None

# --- INTERFAZ DE USUARIO ---
archivo = st.file_uploader("1. Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Empresa:", placeholder="Ej: Mi Empresa S.A.")
    with col2:
        periodo = st.text_input("Período:", placeholder="01/01/2026 - 31/01/2026")
    
    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Generar Diario Compacto (Vertical)", disabled=not (empresa and periodo)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        try:
            df = pd.read_excel(archivo)
            df = df.dropna(how='all')
            
            # Columnas origen
            c_fecha, c_cta, c_desc_cta, c_comp, c_conc, c_debe_orig, c_haber_orig = \
                "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
            df = df.dropna(subset=[c_fecha])
            
            # Unificar concepto para ahorrar espacio vertical
            df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc]) if pd.notna(r[c_conc]) else ''} {str(r[c_comp]) if pd.notna(r[c_comp]) else ''}".strip(), axis=1)
            
            for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                df[nombre_nuevo] = pd.to_numeric(df[col_orig].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            df['Fecha_Aux'] = df[c_fecha].dt.strftime('%d/%m/%Y')
            df['Bloque'] = (df['Fecha_Aux'] + df['Leyenda_Full']).ne((df['Fecha_Aux'] + df['Leyenda_Full']).shift()).cumsum()
            
            lista_final = []
            bloques = df['Bloque'].unique()
            
            for i, b in enumerate(bloques, 1):
                sub_df = df[df['Bloque'] == b].copy()
                n_filas = len(sub_df)
                
                df_bloque = pd.DataFrame({
                    'Fecha': [sub_df.iloc[0][c_fecha].strftime('%d/%m/%y')] + [""] * (n_filas - 1),
                    'Nº': [f"{i}"] + [""] * (n_filas - 1),
                    'Detalle/Leyenda': [sub_df.iloc[0]['Leyenda_Full']] + [""] * (n_filas - 1),
                    'Cta': sub_df[c_cta].astype(str).values,
                    'Descripción Cuenta': sub_df[c_desc_cta].values,
                    'Debe': sub_df['Debe'].values,
                    'Haber': sub_df['Haber'].values
                })
                lista_final.append(df_bloque)
                # Separador minúsculo (solo una línea inferior)
                lista_final.append(pd.DataFrame([["SEP"] * 7], columns=df_bloque.columns))

            df_to_excel = pd.concat(lista_final, ignore_index=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Diario")
                workbook, worksheet = writer.book, writer.sheets['Diario']
                
                # --- FORMATOS DE MICRO-IMPRESIÓN ---
                f_base = {'font_name': 'Arial Narrow', 'font_size': 8}
                f_num = workbook.add_format({**f_base, 'num_format': '#,##0.00;[Red]-#,##0.00;""', 'valign': 'top'})
                f_txt = workbook.add_format({**f_base, 'text_wrap': True, 'valign': 'top'})
                f_head = workbook.add_format({'bold': True, 'font_size': 8, 'bg_color': '#E0E0E0', 'border': 1, 'align': 'center'})
                f_sep = workbook.add_format({'bottom': 1, 'bottom_color': '#333333'})

                # Configuración Vertical (Portrait) para ahorrar hojas
                worksheet.set_portrait()
                worksheet.set_paper(9) # A4
                worksheet.set_margins(left=0.5, right=0.2, top=0.5, bottom=0.4)
                worksheet.fit_to_pages(1, 0) # Forzar ancho a 1 página

                # --- ENCABEZADO CORREGIDO (Sin superposición) ---
                # Agrupamos todo a la izquierda para que no choque con nada a la derecha
                info_line = f"&L&8EMPRESA: {empresa} | PERÍODO: {periodo}\nDIARIO GENERAL&R&8Página &P de &N"
                worksheet.set_header(info_line)

                # Anchos de columna optimizados para Vertical A4
                worksheet.set_column(0, 0, 7.5, f_txt) # Fecha
                worksheet.set_column(1, 1, 3.5, f_txt) # Nº
                worksheet.set_column(2, 2, 22, f_txt)  # Detalle
                worksheet.set_column(3, 3, 7, f_txt)   # Cta
                worksheet.set_column(4, 4, 22, f_txt)  # Descripción
                worksheet.set_column(5, 6, 11, f_num)  # Importes

                # Dibujar filas y separadores
                for row_num, row_data in enumerate(df_to_excel.values, 1):
                    if "SEP" in row_data:
                        worksheet.set_row(row_num, 1, f_sep) # Fila casi invisible pero con línea
                        for c in range(7): worksheet.write(row_num, c, "", f_sep)
                    else:
                        worksheet.set_row(row_num, 10.5) # Altura reducida para ganar espacio

                # Re-escribir encabezados
                for col_num, value in enumerate(df_to_excel.columns.values):
                    worksheet.write(0, col_num, value, f_head)

            st.session_state.excel_final = buf.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()
            
        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.paso = 'configuracion'

    if st.session_state.paso == 'listo':
        st.success("✅ ¡Hecho! Formato vertical optimizado para ahorro de papel.")
        st.download_button(
            label="📥 Descargar Libro Diario Final",
            data=st.session_state.excel_final,
            file_name=f"Diario_Compacto_{empresa.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        if st.button("🏁 Cargar otro archivo"):
            st.session_state.clear()
            st.rerun()
