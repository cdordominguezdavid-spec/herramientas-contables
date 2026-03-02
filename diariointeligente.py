import streamlit as st
import pandas as pd
import io

# Configuración de página
st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato Multipágina Optimizado")

if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'

archivo = st.file_uploader("1. Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Empresa:", placeholder="Nombre de la firma")
    with col2:
        periodo = st.text_input("Período:", placeholder="Ej: ENERO 2026")

    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Generar Diario Multipágina", disabled=not (empresa and periodo)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        progreso_container = st.empty()
        status_text = st.empty()
        bar = progreso_container.progress(0)
        
        try:
            df = pd.read_excel(archivo).dropna(how='all')
            
            # Mapeo de columnas origen
            c_fecha, c_cta, c_desc_cta, c_comp, c_conc, c_debe_orig, c_haber_orig = \
                "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
            df = df.dropna(subset=[c_fecha])
            df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc])} {str(r[c_comp])}".strip(), axis=1)
            
            for col, new in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                df[new] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            df['Bloque'] = (df[c_fecha].dt.strftime('%d%m%Y') + df['Leyenda_Full']).ne((df[c_fecha].dt.strftime('%d%m%Y') + df['Leyenda_Full']).shift()).cumsum()
            
            lista_final = []
            bloques = df['Bloque'].unique()
            total_b = len(bloques)
            
            # Texto para el lomo lateral
            texto_lomo = f"DIARIO GENERAL - {empresa.upper()} - {periodo.upper()}"

            for i, b in enumerate(bloques, 1):
                bar.progress(i / total_b)
                status_text.text(f"Estructurando asiento {i}...")
                
                sub_df = df[df['Bloque'] == b].copy()
                n = len(sub_df)
                
                df_bloque = pd.DataFrame({
                    'LOMO': [texto_lomo] * n, # Se repite en cada fila para que Excel lo imprima al repetir columna
                    'FECHA': [sub_df.iloc[0][c_fecha].strftime('%d/%m/%y')] + [""] * (n - 1),
                    'AS': [f"{i}"] + [""] * (n - 1),
                    'DETALLE': [sub_df.iloc[0]['Leyenda_Full']] + [""] * (n - 1),
                    'CTA': sub_df[c_cta].astype(str).values,
                    'DESCRIPCIÓN': sub_df[c_desc_cta].str.slice(0, 35).values,
                    'DEBE': sub_df['Debe'].values,
                    'HABER': sub_df['Haber'].values
                })
                lista_final.append(df_bloque)
                lista_final.append(pd.DataFrame([["SEP"] * 8], columns=df_bloque.columns))

            df_to_excel = pd.concat(lista_final, ignore_index=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Diario")
                workbook, worksheet = writer.book, writer.sheets['Diario']
                
                # --- FORMATOS ---
                f_lomo = workbook.add_format({
                    'rotation': 90, 
                    'align': 'center', 
                    'valign': 'vcenter', 
                    'font_name': 'Arial Narrow', 
                    'font_size': 7, # Un poco más pequeña para asegurar que entre
                    'bold': True
                })
                f_base = {'font_name': 'Arial Narrow', 'font_size': 8, 'valign': 'top'}
                f_num = workbook.add_format({**f_base, 'num_format': '#,##0.00'})
                f_txt = workbook.add_format({**f_base, 'text_wrap': True})
                f_head = workbook.add_format({'bold': True, 'font_size': 8, 'border': 1, 'align': 'center'})
                f_sep = workbook.add_format({'top': 1, 'top_color': '#CCCCCC'})

                # --- CONFIGURACIÓN DE IMPRESIÓN ---
                worksheet.set_portrait()
                worksheet.set_paper(9) # A4
                worksheet.set_margins(0.3, 0.2, 0.4, 0.4)
                
                # REPETIR COLUMNA A EN TODAS LAS HOJAS (Esto es la clave)
                worksheet.repeat_columns(0, 0)
                # REPETIR ENCABEZADO SUPERIOR EN TODAS LAS HOJAS
                worksheet.repeat_rows(0)
                
                # NÚMERO DE PÁGINA (Arriba a la derecha)
                worksheet.set_header('&R&8Página &P de &N')
                
                worksheet.fit_to_pages(1, 0)

                # Anchos
                worksheet.set_column(0, 0, 3, f_lomo)   # Lomo Lateral
                worksheet.set_column(1, 1, 8, f_txt)    # Fecha
                worksheet.set_column(2, 2, 4, f_txt)    # AS
                worksheet.set_column(3, 3, 24, f_txt)   # Detalle
                worksheet.set_column(4, 4, 8, f_txt)    # CTA
                worksheet.set_column(5, 5, 24, f_txt)   # Descripción
                worksheet.set_column(6, 7, 11, f_num)   # Importes

                # Ajuste de filas y escritura del lomo
                for row_num, row_data in enumerate(df_to_excel.values, 1):
                    if "SEP" in row_data:
                        worksheet.set_row(row_num, 1, f_sep)
                    else:
                        worksheet.set_row(row_num, 11)
                        # Escribir el texto lateral en cada celda para que al repetir columna siempre haya texto
                        worksheet.write(row_num, 0, texto_lomo, f_lomo)

                for col_num, value in enumerate(df_to_excel.columns.values):
                    worksheet.write(0, col_num, value, f_head)

            st.session_state.excel_final = buf.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.paso = 'configuracion'

    if st.session_state.paso == 'listo':
        st.success("✅ Generado correctamente con paginación y lomo lateral continuo.")
        st.download_button("📥 Descargar Libro Diario", st.session_state.excel_final, f"Diario_Final_{empresa}.xlsx")
        if st.button("🏁 Cargar nuevo"):
            st.session_state.clear()
            st.rerun()
