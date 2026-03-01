import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato Final Personalizado")
st.markdown("Orden: **Fecha | Leyenda | Cuenta | Descripción Cuenta | Debe | Haber**")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        # Nombres exactos de las columnas de origen
        c_fecha = "Fecha"
        c_cta = "Cuenta"
        c_desc_cta = "Descripción cuenta"
        c_comp = "Comprobante"
        c_conc = "Concepto pase"
        c_debe_orig = "Débitos"
        c_haber_orig = "Créditos"

        if c_fecha in df.columns:
            # 1. Limpieza y Formato
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
            df = df.dropna(subset=[c_fecha])
            
            # 2. Crear Leyenda (Concepto + Comprobante)
            df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc]) if pd.notna(r[c_conc]) else ''} {str(r[c_comp]) if pd.notna(r[c_comp]) else ''}".strip(), axis=1)

            # 3. Formato Debe y Haber
            for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                df[nombre_nuevo] = df[col_orig].astype(str).str.replace(',', '.')
                df[nombre_nuevo] = pd.to_numeric(df[nombre_nuevo], errors='coerce').fillna(0)

            # 4. Agrupación y Limpieza de duplicados visuales
            df['Fecha_Aux'] = df[c_fecha].dt.strftime('%d/%m/%Y')
            df['Bloque'] = (df['Fecha_Aux'] + df['Leyenda_Full']).ne((df['Fecha_Aux'] + df['Leyenda_Full']).shift()).cumsum()
            
            df_final = df[[c_fecha, 'Leyenda_Full', c_cta, c_desc_cta, 'Debe', 'Haber', 'Bloque']].copy()
            df_final['Fecha_Disp'] = df[c_fecha].dt.strftime('%d/%m/%Y')
            
            # Solo dejamos Fecha y Leyenda en la primera fila de cada bloque
            duplicados = df_final.duplicated(subset=['Bloque'])
            df_final.loc[duplicados, ['Fecha_Disp', 'Leyenda_Full']] = ""

            # 5. Construcción de lista con SEPARADORES
            lista_export = []
            bloques_unicos = df_final['Bloque'].unique()
            # Fila marcadora para la línea negra (6 columnas)
            fila_negra = pd.DataFrame([["LINEA_NEGRA"] * 6], columns=['Fecha', 'Leyenda', 'Cuenta', 'Descripción Cuenta', 'Debe', 'Haber'])

            for b in bloques_unicos:
                sub_df = df_final[df_final['Bloque'] == b][['Fecha_Disp', 'Leyenda_Full', c_cta, c_desc_cta, 'Debe', 'Haber']]
                sub_df.columns = ['Fecha', 'Leyenda', 'Cuenta', 'Descripción Cuenta', 'Debe', 'Haber']
                lista_export.append(sub_df)
                lista_export.append(fila_negra.copy())

            df_to_excel = pd.concat(lista_export, ignore_index=True)

            # 6. Generación de Excel con XlsxWriter
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                # Estilos
                f_miles = workbook.add_format({'num_format': '#,##0.00', 'font_name': 'Arial', 'font_size': 10})
                f_texto = workbook.add_format({'font_name': 'Arial', 'font_size': 10})
                f_negro = workbook.add_format({'bg_color': '#000000'})
                f_head  = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'font_name': 'Arial'})

                # Encabezados
                for col_num, value in enumerate(df_to_excel.columns.values):
                    worksheet.write(0, col_num, value, f_head)

                # --- AJUSTE DE ANCHOS SOLICITADOS ---
                # 0: Fecha (10), 1: Leyenda (40*), 2: Cuenta (7), 3: Desc (40), 4: Debe (14), 5: Haber (14)
                # Nota: Ajusté el orden de los anchos para que coincidan con tu nuevo orden de columnas
                worksheet.set_column(0, 0, 10, f_texto) # Fecha
                worksheet.set_column(1, 1, 40, f_texto) # Leyenda
                worksheet.set_column(2, 2, 7, f_texto)  # Cuenta
                worksheet.set_column(3, 3, 40, f_texto) # Descripción Cuenta
                worksheet.set_column(4, 4, 14, f_miles) # Debe
                worksheet.set_column(5, 5, 14, f_miles) # Haber

                # Aplicar las LÍNEAS NEGRAS de 2pts
                for row_num in range(len(df_to_excel)):
                    if df_to_excel.iloc[row_num, 0] == "LINEA_NEGRA":
                        worksheet.set_row(row_num + 1, 2, f_negro) # 2 puntos de altura
                        for c_idx in range(6):
                            worksheet.write(row_num + 1, c_idx, "", f_negro)

            st.success("✅ ¡Libro Diario generado con el orden y anchos solicitados!")
            st.download_button(label="📥 Descargar Libro Diario", data=buf.getvalue(), file_name="Libro_Diario_Diseno.xlsx")
            
        else:
            st.error("No se encontró la columna 'Fecha'.")

    except Exception as e:
        st.error(f"Error: {e}")
