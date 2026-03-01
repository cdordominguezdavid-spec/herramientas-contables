import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Suite Contable: Libro Diario")
st.markdown("Ajustes: **Fecha en Columna A**, **Sin repetición** y **Formato de Miles**.")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA', 'F. Contable'],
            'asiento': ['Asiento', 'Num_Asiento', 'Comprobante', 'Nro', 'ID', 'ASIENTO', 'Poliza', 'Referencia'],
            'debe': ['Debe', 'Débito', 'Cargo', 'DEBE', 'Debit'],
            'haber': ['Haber', 'Crédito', 'Abono', 'HABER', 'Credit']
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
            # Procesamiento de fechas
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            
            # Ordenar
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])
            
            # --- AJUSTE: MOVER FECHA A LA PRIMERA COLUMNA ---
            columnas_reordenadas = [c_fecha] + [c for c in df_ordenado.columns if c != c_fecha]
            df_ordenado = df_ordenado[columnas_reordenadas]
            
            # --- AJUSTE: FECHA ÚNICA POR ASIENTO ---
            # Guardamos la fecha original en texto
            df_ordenado[c_fecha] = df_ordenado[c_fecha].dt.strftime('%d/%m/%Y')
            # Si el número de asiento se repite, vaciamos la celda de la fecha
            df_ordenado.loc[df_ordenado[c_asiento].duplicated(), c_fecha] = ""

            # Asegurar que debe y haber sean números
            if c_debe: df_ordenado[c_debe] = pd.to_numeric(df_ordenado[c_debe], errors='coerce').fillna(0)
            if c_haber: df_ordenado[c_haber] = pd.to_numeric(df_ordenado[c_haber], errors='coerce').fillna(0)

            # Construcción con fila separadora
            lista_final = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            fila_separadora = pd.DataFrame([[" "] * len(df_ordenado.columns)], columns=df_ordenado.columns)

            for asiento in asientos_unicos:
                filas_asiento = df_ordenado[df_ordenado[c_asiento] == asiento]
                lista_final.append(filas_asiento)
                lista_final.append(fila_separadora)

            df_exportar = pd.concat(lista_final, ignore_index=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                # --- AJUSTE: FORMATO DE MILES Y DECIMALES ---
                # Este formato obliga a Excel a poner separador de miles y 2 decimales
                formato_contable = workbook.add_format({'num_format': '#,##0.00'})
                formato_negro = workbook.add_format({'bg_color': '#000000', 'border': 1, 'border_color': '#000000'})
                
                # Autoajuste de columnas y aplicación de formato
                for i, col in enumerate(df_exportar.columns):
                    longitudes = [len(str(val)) for val in df_exportar[col].values]
                    max_len = max(longitudes + [len(str(col))]) + 2
                    
                    # Aplicar formato contable a las columnas de dinero
                    if col in [c_debe, c_haber]:
                        worksheet.set_column(i, i, max_len, formato_contable)
                    else:
                        worksheet.set_column(i, i, min(max_len, 50))

                # Línea divisoria de 2pt
                for row_num in range(len(df_exportar)):
                    if df_exportar.iloc[row_num][c_asiento] == " ":
                        worksheet.set_row(row_num + 1, 2, formato_negro)

            st.success("✅ ¡Hecho! Columna A es Fecha, miles configurados y sin repeticiones.")
            st.download_button(
                label="📥 Descargar Libro Diario Final",
                data=buf.getvalue(),
                file_name="Libro_Diario_Profesional.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No se detectaron columnas clave.")

    except Exception as e:
        st.error(f"Error: {e}")
