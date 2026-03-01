import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Suite Contable: Libro Diario")
st.markdown("Acabado: Línea divisoria de **2pt** y **autoajuste de ancho** de columnas.")

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
            # Formato de fecha y limpieza
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            
            # Ordenar y convertir fecha a texto para el Excel
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])
            df_ordenado[c_fecha] = df_ordenado[c_fecha].dt.strftime('%d/%m/%Y')
            
            if c_debe: df[c_debe] = pd.to_numeric(df[c_debe], errors='coerce').fillna(0)
            if c_haber: df[c_haber] = pd.to_numeric(df[c_haber], errors='coerce').fillna(0)

            # Construcción del DataFrame con filas vacías
            lista_final = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            fila_separadora = pd.DataFrame([[None] * len(cols)], columns=cols)

            for asiento in asientos_unicos:
                filas_asiento = df_ordenado[df_ordenado[c_asiento] == asiento]
                lista_final.append(filas_asiento)
                lista_final.append(fila_separadora)

            df_exportar = pd.concat(lista_final, ignore_index=True)

            # --- GENERACIÓN DE EXCEL CON DISEÑO ---
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                # 1. Formato de línea negra
                formato_negro = workbook.add_format({'bg_color': '#000000'})
                
                # 2. AUTOAJUSTE DE COLUMNAS
                # Recorremos cada columna para medir el contenido
                for i, col in enumerate(df_exportar.columns):
                    # Medimos el largo del nombre de la columna o del dato más largo
                    max_len = max(
                        df_exportar[col].astype(str).map(len).max(), 
                        len(str(col))
                    ) + 2  # Añadimos un pequeño margen
                    worksheet.set_column(i, i, max_len)

                # 3. APLICAR LÍNEA ULTRA FINA (2pt)
                for row_num in range(len(df_exportar)):
                    if pd.isna(df_exportar.iloc[row_num][c_asiento]):
                        worksheet.set_row(row_num + 1, 2, formato_negro)

            st.success("✅ ¡Perfeccionado! Columnas ajustadas y líneas de 2pt.")
            st.download_button(
                label="📥 Descargar Libro Diario Final",
                data=buf.getvalue(),
                file_name="Libro_Diario_Perfecto.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No se encontraron las columnas clave de Fecha o Asiento.")

    except Exception as e:
        st.error(f"Error: {e}")
