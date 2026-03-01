import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato Final")
st.markdown("Columnas: **Fecha | Cuenta | Descripción Cuenta | Leyenda | Debe | Haber**")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        # Nombres exactos de tu archivo original
        c_fecha = "Fecha"
        c_cta = "Cuenta"
        c_desc_cta = "Descripción cuenta"
        c_comp = "Comprobante"
        c_conc = "Concepto pase"
        c_debe_orig = "Débitos"
        c_haber_orig = "Créditos"

        if c_fecha in df.columns:
            # 1. Limpieza y Formato inicial
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
            df = df.dropna(subset=[c_fecha])
            
            # 2. Crear Leyenda (Concepto + Comprobante)
            df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc]) if pd.notna(r[c_conc]) else ''} {str(r[c_comp]) if pd.notna(r[c_comp]) else ''}".strip(), axis=1)

            # 3. Formato Debe y Haber (Miles)
            for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                df[nombre_nuevo] = df[col_orig].astype(str).str.replace(',', '.')
                df[nombre_nuevo] = pd.to_numeric(df[nombre_nuevo], errors='coerce').fillna(0)

            # 4. Preparar visualización (Fecha y Leyenda solo en la primera fila)
            df['Fecha_Aux'] = df[c_fecha].dt.strftime('%d/%m/%Y')
            # Identificamos bloques por cambio de Fecha + Leyenda
            df['Bloque'] = (df['Fecha_Aux'] + df['Leyenda_Full']).ne((df['Fecha_Aux'] + df['Leyenda_Full']).shift()).cumsum()
            
            df_final = df[[c_fecha, c_cta, c_desc_cta, 'Leyenda_Full', 'Debe', 'Haber', 'Bloque']].copy()
            df_final['Fecha_Disp'] = df[c_fecha].dt.strftime('%d/%m/%Y')
            
            # Solo dejamos datos en la primera fila de cada bloque
            duplicados = df_final.duplicated(subset=['Bloque'])
            df_final.loc[duplicados, ['Fecha_Disp', 'Leyenda_Full']] = ""

            # 5. Construcción de lista para exportar con SEPARADORES
            lista_export = []
            bloques_unicos = df_final['Bloque'].unique()
            # Fila marcadora para la línea negra
            fila_negra = pd.DataFrame([["LINEA_NEGRA"] * 6], columns=['Fecha', 'Cuenta', 'Descripción Cuenta', 'Leyenda', 'Debe', 'Haber'])

            for b in bloques_unicos:
                sub_df = df_final[df_final['Bloque'] == b][['Fecha_Disp', c_cta, c_desc_cta, 'Leyenda_Full', 'Debe', 'Haber']]
                sub_df.columns = ['Fecha', 'Cuenta', 'Descripción Cuenta', 'Leyenda', 'Debe', 'Haber']
                lista_export.append(sub_df)
                lista_export.append(fila_negra)

            df_to_excel = pd.concat(lista_export, ignore_index=True)

            # 6. Generación de Excel con XlsxWriter (Líneas de 2pts)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                # Estilos
                f_miles = workbook.add_format({'num_format': '#,##0.00', 'font_name': 'Arial', 'font_size': 10})
                f_negro = workbook.add_format({'bg_color': '#000000'})
                f_head  = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})

                # Formatear encabezados
                for col_num, value in enumerate(df_to_excel.columns.values):
                    worksheet.write(0, col_num, value, f_head)

                # Autoajuste y miles
                for i, col in enumerate(df_to_excel.columns):
                    worksheet.set_column(i, i, 18 if col in ['Debe', 'Haber'] else 25, f_miles if col in ['Debe', 'Haber'] else None)

                # Aplicar las LÍNEAS NEGRAS de 2pts
                for row_num in range(len(df_to_excel)):
                    if df_to_excel.iloc[row_num, 0] == "LINEA_NEGRA":
                        # Establecer altura de fila a 2 puntos y color negro
                        worksheet.set_row(row_num + 1, 2, f_negro)
                        # Limpiar el texto marcador
                        for c_idx in range(6):
                            worksheet.write(row_num + 1, c_idx, "", f_negro)

            st.success("✅ ¡Libro Diario con líneas divisorias de 2pts generado!")
            st.download_button(label="📥 Descargar Libro Diario", data=buf.getvalue(), file_name="Libro_Diario_Lineas.xlsx")
            
        else:
            st.error("No se encontró la columna 'Fecha'.")

    except Exception as e:
        st.error(f"Error: {e}")
