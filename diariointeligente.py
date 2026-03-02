import streamlit as st
import pandas as pd
import io
import time

# Configuración de página
st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Optimización con Título Lateral")

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'
if 'excel_final' not in st.session_state:
    st.session_state.excel_final = None

archivo = st.file_uploader("1. Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Empresa:", placeholder="Ej: Mi Empresa S.A.")
    with col2:
        periodo = st.text_input("Período:", placeholder="01/01/2026 - 31/01/2026")

    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Lanzar Generación", disabled=not (empresa and periodo)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        # --- CONTENEDORES PARA LA BARRA DE PROGRESO ---
        progreso_container = st.empty()
        status_text = st.empty()
        bar = progreso_container.progress(0)
        
        try:
            status_text.text("Leyendo archivo...")
            df = pd.read_excel(archivo).dropna(how='all')
            
            # Columnas origen (Ajustar nombres según tu Excel)
            c_fecha, c_cta, c_desc_cta, c_comp, c_conc, c_debe_orig, c_haber_orig = \
                "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
            df = df.dropna(subset=[c_fecha])
            df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc])} {str(r[c_comp])}".strip(), axis=1)
            
            for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                df[nombre_nuevo] = pd.to_numeric(df[col_orig].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            # Agrupación
            df['Bloque'] = (df[c_fecha].dt.strftime('%d%m%Y') + df['Leyenda_Full']).ne((df[c_fecha].dt.strftime('%d%m%Y') + df['Leyenda_Full']).shift()).cumsum()
            
            lista_final = []
            bloques = df['Bloque'].unique()
            total_b = len(bloques)
            texto_lateral = f"DIARIO GENERAL - {empresa} - {periodo}"

            # --- BUCLE CON BARRA DE PROGRESO ---
            for i, b in enumerate(bloques, 1):
                # Actualizar barra
                porcentaje = i / total_b
                bar.progress(porcentaje)
                status_text.text(f"Estructurando asiento {i} de {total_b}...")
                
                sub_df = df[df['Bloque'] == b].copy()
                n_filas = len(sub_df)
                
                df_bloque = pd.DataFrame({
                    'TITULO LATERAL': [texto_lateral] + [""] * (n_filas - 1),
                    'FECHA': [sub_df.iloc[0][c_fecha].strftime('%d/%m/%y')] + [""] * (n_filas - 1),
                    'Nº': [f"{i}"] + [""] * (n_filas - 1),
                    'DETALLE': [sub_df.iloc[0]['Leyenda_Full']] + [""] * (n_filas - 1),
                    'CTA': sub_df[c_cta].astype(str).values,
                    'DESCRIPCIÓN': sub_df[c_desc_cta].str.slice(0, 30).values,
                    'DEBE': sub_df['Debe'].values,
                    'HABER': sub_df['Haber'].values
                })
                lista_final.append(df_bloque)
                # Separador sutil
                lista_final.append(pd.DataFrame([["SEP"] * 8], columns=df_bloque.columns))

            df_to_excel = pd.concat(lista_final, ignore_index=True)

            status_text.text("Finalizando formato de Excel...")
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Diario")
                workbook, worksheet = writer.book, writer.sheets['Diario']
                
                # Formatos
                f_lomo = workbook.add_format({'rotation': 90, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Arial Narrow', 'font_size': 7, 'bold': True, 'bg_color': '#D9D9D9'})
                f_base = {'font_name': 'Arial Narrow', 'font_size': 7.5, 'valign': 'top'}
                f_num = workbook.add_format({**f_base, 'num_format': '#,##0.00;[Red]-#,##0.00;""'})
                f_txt = workbook.add_format({**f_base, 'text_wrap': True})
                f_head = workbook.add_format({'bold': True, 'font_size': 7.5, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
                f_sep = workbook.add_format({'bottom': 1, 'bottom_color': '#AAAAAA'})

                # Configuración de página
                worksheet.set_portrait()
                worksheet.set_margins(left=0.2, right=0.2, top=0.3, bottom=0.3)
                worksheet.repeat_columns(0, 0) # Repite el título lateral en cada hoja
                worksheet.fit_to_pages(1, 0)

                # Anchos (Columna 0 es el lomo lateral)
                worksheet.set_column(0, 0, 2.5, f_lomo) 
                worksheet.set_column(1, 1, 7, f_txt)
                worksheet.set_column(2, 2, 3, f_txt)
                worksheet.set_column(3, 3, 22, f_txt)
                worksheet.set_column(4, 4, 7, f_txt)
                worksheet.set_column(5, 5, 22, f_txt)
                worksheet.set_column(6, 7, 10, f_num)

                for row_num, row_data in enumerate(df_to_excel.values, 1):
                    if "SEP" in row_data:
                        worksheet.set_row(row_num, 0.5, f_sep)
                    else:
                        worksheet.set_row(row_num, 9.5)

                for col_num, value in enumerate(df_to_excel.columns.values):
                    worksheet.write(0, col_num, value, f_head)

            st.session_state.excel_final = buf.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.paso = 'configuracion'

    if st.session_state.paso == 'listo':
        st.success("✅ ¡Procesado con éxito!")
        st.download_button("📥 Descargar Libro Diario", st.session_state.excel_final, f"Diario_{empresa}.xlsx")
        if st.button("🏁 Reiniciar"):
            st.session_state.clear()
            st.rerun()
