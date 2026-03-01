import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato Premium")
st.markdown("Mejora: **Celdas de Leyenda combinadas** y ajuste de texto automático.")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
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

            # Agrupación por bloques
            df['Fecha_Aux'] = df[c_fecha].dt.strftime('%d/%m/%Y')
            df['Bloque'] = (df['Fecha_Aux'] + df['Leyenda_Full']).ne((df['Fecha_Aux'] + df['Leyenda_Full']).shift()).cumsum()
            
            # 2. Construcción de la lista con lógica de filas
            lista_final = []
            asientos_indices = [] # Para saber dónde empiezan y terminan los asientos en el Excel final
            
            bloques = df['Bloque'].unique()
            current_row = 1 # Empezamos después del encabezado

            for b in bloques:
                sub_df = df[df['Bloque'] == b].copy()
                num_filas = len(sub_df)
                
                # Preparar datos de visualización
                sub_df_export = pd.DataFrame({
                    'Fecha': [sub_df.iloc[0][c_fecha].strftime('%d/%m/%Y')] + [""] * (num_filas - 1),
                    'Leyenda': [sub_df.iloc[0]['Leyenda_Full']] + [""] * (num_filas - 1),
                    'Cuenta': sub_df[c_cta].values,
                    'Descripción Cuenta': sub_df[c_desc_cta].values,
                    'Debe': sub_df['Debe'].values,
                    'Haber': sub_df['Haber'].values
                })
                
                start_row = current_row
                end_row = current_row + num_filas - 1
                asientos_indices.append({'start': start_row, 'end': end_row, 'len': num_filas})
                
                lista_final.append(sub_df_export)
                # Fila negra marcadora
                lista_final.append(pd.DataFrame([["MARK"] * 6], columns=sub_df_export.columns))
                current_row += num_filas + 1

            df_to_excel = pd.concat(lista_final, ignore_index=True)

            # 3. Escritura en Excel
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                # FORMATOS
                f_miles = workbook.add_format({'num_format': '#,##0.00', 'font_name': 'Arial', 'font_size': 10, 'valign': 'top'})
                f_text  = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'valign': 'top', 'text_wrap': True})
                f_merge = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'valign': 'top', 'align': 'left', 'text_wrap': True})
                f_negro = workbook.add_format({'bg_color': '#000000'})
                f_head  = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})

                # Anchos de columna
                worksheet.set_column(0, 0, 10, f_text)  # Fecha
                worksheet.set_column(1, 1, 40, f_text)  # Leyenda (Ajuste de texto activo)
                worksheet.set_column(2, 2, 7, f_text)   # Cuenta
                worksheet.set_column(3, 3, 40, f_text)  # Descripción
                worksheet.set_column(4, 5, 14, f_miles) # Debe y Haber

                # Aplicar Merges y Líneas Negras
                for idx in asientos_indices:
                    # Lógica de Combinado de Leyenda
                    # Si el asiento tiene 2 o más filas, unimos la fila 1 y 2 de la columna Leyenda (col index 1)
                    if idx['len'] >= 2:
                        # merge_range(fila_inicio, col_inicio, fila_fin, col_fin, dato, formato)
                        texto_leyenda = df_to_excel.iloc[idx['start']-1]['Leyenda']
                        worksheet.merge_range(idx['start'], 1, idx['start'] + 1, 1, texto_leyenda, f_merge)
                    
                    # Línea negra al final del bloque
                    row_negra = idx['end'] + 1
                    worksheet.set_row(row_negra, 2, f_negro)
                    for c in range(6): worksheet.write(row_negra, c, "", f_negro)

                # Encabezados
                for col_num, value in enumerate(df_to_excel.columns.values):
                    worksheet.write(0, col_num, value, f_head)

            st.success("✅ ¡Libro Diario optimizado con celdas combinadas!")
            st.download_button(label="📥 Descargar Diario Premium", data=buf.getvalue(), file_name="Diario_Combinado.xlsx")

    except Exception as e:
        st.error(f"Error: {e}")
