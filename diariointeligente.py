import streamlit as st
import pandas as pd
import io

# Configuración de página
st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato Oficial Definitivo")

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
        if st.button("🚀 Generar Libro Diario", disabled=not (empresa and periodo)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        progreso_container = st.empty()
        bar = progreso_container.progress(0)
        
        try:
            df = pd.read_excel(archivo).dropna(how='all')
            
            # Mapeo de columnas
            c_fecha, c_cta, c_desc_cta, c_comp, c_conc, c_debe_orig, c_haber_orig = \
                "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
            df = df.dropna(subset=[c_fecha])
            
            # CONCATENADO CON SALTO DE LÍNEA (Si el texto es largo, Excel hará el resto)
            df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc])} \n{str(r[c_comp])}".strip(), axis=1)
            
            for col, new in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                df[new] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            # Agrupación por asientos
            df['Bloque'] = (df[c_fecha].dt.strftime('%d%m%Y') + df['Leyenda_Full']).ne((df[c_fecha].dt.strftime('%d%m%Y') + df['Leyenda_Full']).shift()).cumsum()
            
            lista_final = []
            bloques = df['Bloque'].unique()
            total_b = len(bloques)
            texto_lateral = f"DIARIO GENERAL - {empresa.upper()} - {periodo.upper()}"

            for i, b in enumerate(bloques, 1):
                bar.progress(i / total_b)
                sub_df = df[df['Bloque'] == b].copy()
                n = len(sub_df)
                
                df_bloque = pd.DataFrame({
                    ' ': [""] * n, # Espacio reservado para el lomo lateral
                    'FECHA': [sub_df.iloc[0][c_fecha].strftime('%d/%m/%y')] + [""] * (n - 1),
                    'AS': [f"{i}"] + [""] * (n - 1),
                    'DETALLE / COMPROBANTE': [sub_df.iloc[0]['Leyenda_Full']] + [""] * (n - 1),
                    'CTA': sub_df[c_cta].astype(str).values,
                    'DESCRIPCIÓN': sub_df[c_desc_cta].str.slice(0, 45).values,
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
                f_num = workbook.add_format({
                    'font_name': 'Arial Narrow', 'font_size': 8.5, 
                    'num_format': '#,##0.00;;""', 'valign': 'top'
                })
                # Detalle con Wrap Text para que se vea en dos renglones si es necesario
                f_wrap = workbook.add_format({
                    'font_name': 'Arial Narrow', 'font_size': 8.5, 
                    'valign': 'top', 'text_wrap': True
                })
                f_head = workbook.add_format({
                    'bold': True, 'font_size': 9, 'border': 1, 
                    'align': 'center', 'bg_color': '#FFFFFF'
                })
                f_sep = workbook.add_format({'top': 1, 'top_color': '#000000'})

                # --- CONFIGURACIÓN DE IMPRESIÓN ---
                worksheet.set_portrait()
                worksheet.set_paper(9) # A4
                worksheet.set_margins(left=0.5, right=0.3, top=0.6, bottom=0.5)
                
                # Encabezado con Número de Página en todas las hojas
                worksheet.set_header(f'&L&10&B{empresa}&R&10Página &P de &N')
                worksheet.repeat_rows(0) # Repetir títulos de columna
                worksheet.fit_to_pages(1, 0)

                # Anchos
                worksheet.set_column(0, 0, 4)           # Espacio para Lomo (Textbox)
                worksheet.set_column(1, 1, 8.5, f_wrap) # Fecha
                worksheet.set_column(2, 2, 4.5, f_wrap) # Asiento
                worksheet.set_column(3, 3, 28, f_wrap)  # Detalle (Dos renglones)
                worksheet.set_column(4, 4, 8, f_wrap)   # Cuenta
                worksheet.set_column(5, 5, 28, f_wrap)  # Descripción
                worksheet.set_column(6, 7, 13, f_num)   # Importes

                # --- EL TRUCO INTELIGENTE: CUADRO DE TEXTO ROTADO ---
                # Esto no se corta entre páginas porque Excel lo trata como objeto de dibujo
                worksheet.insert_textbox(1, 0, texto_lateral, {
                    'width': 35,
                    'height': 1200, # Altura grande para cubrir varias páginas o ajustarse
                    'font': {'name': 'Arial Narrow', 'size': 9, 'bold': True},
                    'align': {'vertical': 'middle', 'horizontal': 'center'},
                    'gradient': {'fill': False},
                    'line': {'none': True},
                    'text_rotation': 90
                })

                # Ajuste de filas dinámico
                for row_num, row_data in enumerate(df_to_excel.values, 1):
                    if "SEP" in row_data:
                        worksheet.set_row(row_num, 1.5, f_sep)
                    else:
                        # Altura automática para permitir el wrap del texto (2do renglón)
                        worksheet.set_row(row_num, None) 

                for col_num, value in enumerate(df_to_excel.columns.values):
                    worksheet.write(0, col_num, value, f_head)

            st.session_state.excel_final = buf.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.paso = 'configuracion'

    if st.session_state.paso == 'listo':
        st.success("✅ Generado: Texto en dos renglones, sin ceros y numeración de página corregida.")
        st.download_button("📥 Descargar Libro Diario", st.session_state.excel_final, f"Diario_Final.xlsx")
        if st.button("🏁 Nuevo"):
            st.session_state.clear()
            st.rerun()
