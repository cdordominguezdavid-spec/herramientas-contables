import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Suite Contable: Libro Diario")
st.markdown("Estado: **Fecha en Columna A**, **Miles con punto** y **Fecha única por asiento**.")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA'],
            'asiento': ['Asiento', 'Comprobante', 'Num_Asiento', 'Poliza', 'Referencia', 'ASIENTO'],
            'debe': ['Débitos', 'Debe', 'Débito', 'Cargo', 'DEBE'],
            'haber': ['Créditos', 'Haber', 'Crédito', 'Abono', 'HABER']
        }
        
        def detectar(lista, reales):
            for s in lista:
                if s in reales: return s
            return None

        c_fecha = detectar(mapeo['fecha'], cols)
        c_asiento = detectar(mapeo['asiento'], cols)
        c_debe = detectar(mapeo['debe'], cols)
        c_haber = detectar(mapeo['haber'], cols)

        if c_fecha and c_asiento:
            # 1. Limpieza de Fechas
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])
            
            # 2. Reordenar: Fecha siempre primero
            cols_reordenadas = [c_fecha] + [c for c in df_ordenado.columns if c != c_fecha]
            df_ordenado = df_ordenado[cols_reordenadas]

            # 3. Limpieza de Números (Forzar conversión para que Excel los reconozca como cifra)
            for col_num in [c_debe, c_haber]:
                if col_num:
                    # Reemplazamos coma por punto si viene como texto y convertimos a número
                    df_ordenado[col_num] = df_ordenado[col_num].astype(str).str.replace(',', '.')
                    df_ordenado[col_num] = pd.to_numeric(df_ordenado[col_num], errors='coerce').fillna(0)

            # 4. Fecha única por asiento (estética)
            df_final_procesado = df_ordenado.copy()
            df_final_procesado[c_fecha] = df_final_procesado[c_fecha].dt.strftime('%d/%m/%Y')
            df_final_procesado.loc[df_final_procesado[c_asiento].duplicated(), c_fecha] = ""

            # 5. Construcción de filas con separadores
            lista_final = []
            asientos_unicos = df_final_procesado[c_asiento].unique()
            fila_separadora = pd.DataFrame([[" "] * len(df_final_procesado.columns)], columns=df_final_procesado.columns)

            for asiento in asientos_unicos:
                filas = df_final_procesado[df_final_procesado[c_asiento] == asiento]
                lista_final.append(filas)
                lista_final.append(fila_separadora)

            df_exportar = pd.concat(lista_final, ignore_index=True)

            # 6. Generación del Excel con formato de miles forzado
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                # FORMATO CONTABLE: #.##0,00
                formato_miles = workbook.add_format({'num_format': '#,##0.00'})
                formato_negro = workbook.add_format({'bg_color': '#000000'})

                for i, col in enumerate(df_exportar.columns):
                    # Autoajuste de columnas
                    longitudes = [len(str(val)) for val in df_exportar[col].values]
                    max_len = max(longitudes + [len(str(col))]) + 2
                    
                    if col in [c_debe, c_haber]:
                        # Aplicamos el formato de miles específicamente a estas columnas
                        worksheet.set_column(i, i, max_len, formato_miles)
                    else:
                        worksheet.set_column(i, i, min(max_len, 50))

                # Línea negra de 2pt
                for row_num in range(len(df_exportar)):
                    if df_exportar.iloc[row_num][c_asiento] == " ":
                        worksheet.set_row(row_num + 1, 2, formato_negro)

            st.success("✅ ¡Listo! Descarga el archivo y verifica los puntos de milésima.")
            st.download_button(
                label="📥 Descargar Diario Profesional",
                data=buf.getvalue(),
                file_name="Diario_Profesional_Miles.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No detecté las columnas. Asegúrate que se llamen Fecha, Comprobante/Asiento y Débitos/Créditos.")

    except Exception as e:
        st.error(f"Error: {e}")
