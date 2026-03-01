import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato de Impresión Oficial")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    # --- INPUTS DE ENCABEZADO ---
    col_inp1, col_inp2 = st.columns(2)
    with col_inp1:
        empresa = st.text_input("Nombre de la Empresa:", placeholder="Ej: Mi Empresa S.A.")
    with col_inp2:
        periodo = st.text_input("Período:", placeholder="Ej: Enero 2024")

    if empresa and periodo:
        try:
            df = pd.read_excel(archivo)
            df = df.dropna(how='all')
            
            c_fecha, c_cta, c_desc_cta, c_comp, c_conc, c_debe_orig, c_haber_orig = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            if c_fecha in df.columns:
                # 1. Procesamiento Base
                df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
                df = df.dropna(subset=[c_fecha])
                
                # Crear Leyenda
                df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc]) if pd.notna(r[c_conc]) else ''} {str(r[c_comp]) if pd.notna(r[c_comp]) else ''}".strip(), axis=1)

                # Formato Debe/Haber
                for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                    df[nombre_nuevo] = pd.to_numeric(df[col_orig].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

                # Agrupación por bloques (Asientos)
                df['Fecha_Aux'] = df[c_fecha].dt.strftime('%d/%m/%Y')
                df['Bloque'] = (df['Fecha_Aux'] + df['Leyenda_Full']).ne((df['Fecha_Aux'] + df['Leyenda_Full']).shift()).cumsum()
                
                # 2. Construcción de la lista para Excel
                lista_final = []
                asientos_indices = []
                bloques = df['Bloque'].unique()
                current_row = 1 

                for i, b in enumerate(bloques, 1):
                    sub_df = df[df['Bloque'] == b].copy()
                    num_filas = len(sub_df)
                    
                    sub_df_export = pd.DataFrame({
                        'Fecha': [sub_df.iloc[0][c_fecha].strftime('%d/%m/%Y')] + [""] * (num_filas - 1),
                        'NRO.': [f"{i:03d}"] + [""] * (num_filas - 1), # Correlativo 3 dígitos
                        'Leyenda': [sub_df.iloc[0]['Leyenda_Full']] + [""] * (num_filas - 1),
                        'Cuenta': sub_df[c_cta].values,
                        'Descripción Cuenta': sub_df[c_desc_cta].values,
                        'Debe': sub_df['Debe'].values,
                        'Haber': sub_df['Haber'].values
                    })
                    
                    asientos_indices.append({'start': current_row, 'end': current_row + num_filas - 1, 'len': num_filas})
                    lista_final.append(sub_df_export)
                    lista_final.append(pd.DataFrame([["MARK"] * 7], columns=sub_df_export.columns))
                    current_row += num_filas + 1

                df_to_excel = pd.concat(lista_final, ignore_index=True)

                # 3. Escritura en Excel con Configuración de Página
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                    df_to_excel.to_excel(writer, index=False, sheet_name="Libro Diario")
                    workbook  = writer.book
                    worksheet = writer.sheets['Libro Diario']
                    
                    # FORMATOS
                    # El num_format '#,##0.00;[Red]-#,##0.00;;' elimina los ceros visualmente
                    f_miles = workbook.add_format({'num_format': '#,##0.00;;', 'font_name': 'Arial', 'font_size': 9, 'valign': 'top'})
                    f_text  = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'text_wrap': True})
                    f_merge = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'left', 'text_wrap': True})
                    f_negro = workbook.add_format({'bg_color': '#000000'})
                    f_head  = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'font_size': 9})

                    # CONFIGURACIÓN DE IMPRESIÓN (A4)
                    worksheet.set_paper(9) # 9 = A4
                    worksheet.set_margins(0.2, 0.2, 0.5, 0.5) # Márgenes muy pequeños
                    worksheet.center_horizontally()
                    worksheet.set_print_scale(95) # Escala ligera para asegurar encuadre
                    
                    # Encabezado dinámico y numeración
                    # &L = Izquierda, &C = Centro, &R = Derecha
                    header_str = f"&L&B{empresa}\nPeríodo: {periodo}&R&BDIARIO GENERAL"
                    footer_str = "&RPágina &P de &N"
                    worksheet.set_header(header_str)
                    worksheet.set_footer(footer_str)

                    # Anchos de columna solicitados
                    worksheet.set_column(0, 0, 10, f_text)  # Fecha
                    worksheet.set_column(1, 1, 5, f_text)   # NRO (3 dígitos)
                    worksheet.set_column(2, 2, 40, f_text)  # Leyenda
                    worksheet.set_column(3, 3, 7, f_text)   # Cuenta
                    worksheet.set_column(4, 4, 40, f_text)  # Descripción
                    worksheet.set_column(5, 6, 14, f_miles) # Debe y Haber

                    # Aplicar Merges y Líneas Negras
                    for idx in asientos_indices:
                        if idx['len'] >= 2:
                            # Merge para Leyenda (Columna 2)
                            t_leyenda = df_to_excel.iloc[idx['start']-1]['Leyenda']
                            worksheet.merge_range(idx['start'], 2, idx['start'] + 1, 2, t_leyenda, f_merge)
                        
                        row_negra = idx['end'] + 1
                        worksheet.set_row(row_negra, 1.5, f_negro) # 2 pts aprox
                        for c in range(7): worksheet.write(row_negra, c, "", f_negro)

                    # Escribir encabezados de columna
                    for col_num, value in enumerate(df_to_excel.columns.values):
                        worksheet.write(0, col_num, value, f_head)

                st.success("✅ ¡Libro Diario listo para impresión oficial!")
                st.download_button(label="📥 Descargar Diario para Imprimir", data=buf.getvalue(), file_name="Libro_Diario_Oficial.xlsx")

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("⚠️ Por favor ingresa el nombre de la empresa y el período para continuar.")
