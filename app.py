import streamlit as st
import pandas as pd
import io

# Configuración
st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚙️ Procesador Avanzado: Mayor a Diario")
st.markdown("Ajuste: Forzando **Líneas Negras** sólidas entre asientos.")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
        # Mapeo de columnas (mismo que antes)
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA', 'F. Contable'],
            'asiento': ['Asiento', 'Num_Asiento', 'Comprobante', 'Nro', 'ID', 'ASIENTO', 'Poliza', 'Referencia'],
            'debe': ['Debe', 'Débito', 'Cargo', 'DEBE', 'Debit', 'Ingresos'],
            'haber': ['Haber', 'Crédito', 'Abono', 'HABER', 'Credit', 'Egresos']
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
            # Formato de fecha español
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            df[c_fecha] = df[c_fecha].dt.strftime('%d/%m/%Y')
            
            # Limpieza de números
            if c_debe: df[c_debe] = pd.to_numeric(df[c_debe], errors='coerce').fillna(0)
            if c_haber: df[c_haber] = pd.to_numeric(df[c_haber], errors='coerce').fillna(0)
            
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])

            # --- CONSTRUCCIÓN DEL DIARIO CON SEPARADORES ---
            lista_final = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            
            # Fila "separadora" (la usaremos como marcador)
            fila_separadora = pd.DataFrame([[None] * len(cols)], columns=cols)

            for asiento in asientos_unicos:
                filas_asiento = df_ordenado[df_ordenado[c_asiento] == asiento]
                lista_final.append(filas_asiento)
                lista_final.append(fila_separadora)

            df_exportar = pd.concat(lista_final, ignore_index=True)

            # --- GENERACIÓN DEL EXCEL CON FORMATO FORZADO ---
            buf = io.BytesIO()
            # IMPORTANTE: Usamos engine='xlsxwriter'
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                # Definimos el formato negro sólido
                formato_negro = workbook.add_format({'bg_color': '#000000', 'bottom': 1, 'top': 1})
                
                # Recorremos el DataFrame para encontrar dónde pusimos los "None" y pintarlos
                for row_num in range(len(df_exportar)):
                    # Si el valor en la columna de Asiento es nulo, es nuestra fila separadora
                    if pd.isna(df_exportar.iloc[row_num][c_asiento]):
                        # Pintamos toda la fila (desde columna 0 hasta la última)
                        # row_num + 1 porque la fila 0 es el encabezado en Excel
                        worksheet.set_row(row_num + 1, 8, formato_negro) # 8 es la altura (más delgada)

            st.success("✅ Procesado. Revisa el archivo descargado.")
            st.download_button(
                label="📥 Descargar con Separadores Negros",
                data=buf.getvalue(),
                file_name="Diario_Con_Lineas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No se detectaron columnas clave.")

    except Exception as e:
        st.error(f"Error técnico: {e}")
