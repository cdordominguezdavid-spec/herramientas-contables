import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚙️ Procesador Avanzado: Mayor a Diario")
st.markdown("Ajuste Final: **Líneas negras ultra finas** (separadores de 4px).")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
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
            # Formato de fecha
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            df[c_fecha] = df[c_fecha].dt.strftime('%d/%m/%Y')
            
            # Limpieza de números
            if c_debe: df[c_debe] = pd.to_numeric(df[c_debe], errors='coerce').fillna(0)
            if c_haber: df[c_haber] = pd.to_numeric(df[c_haber], errors='coerce').fillna(0)
            
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])

            # Construcción de la lista con filas marcadoras
            lista_final = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            fila_separadora = pd.DataFrame([[None] * len(cols)], columns=cols)

            for asiento in asientos_unicos:
                filas_asiento = df_ordenado[df_ordenado[c_asiento] == asiento]
                lista_final.append(filas_asiento)
                lista_final.append(fila_separadora)

            df_exportar = pd.concat(lista_final, ignore_index=True)

            # --- GENERACIÓN DEL EXCEL CON LÍNEA ULTRA FINA ---
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                # Formato negro sólido
                formato_negro = workbook.add_format({'bg_color': '#000000'})
                
                for row_num in range(len(df_exportar)):
                    # Buscamos nuestra fila marcadora (donde el asiento es nulo)
                    if pd.isna(df_exportar.iloc[row_num][c_asiento]):
                        # worksheet.set_row(fila, altura, formato)
                        # Usamos altura 4 para que sea la mitad de fina que antes
                        worksheet.set_row(row_num + 1, 4, formato_negro)

            st.success("✅ ¡Hecho! Las líneas ahora son ultra finas.")
            st.download_button(
                label="📥 Descargar con Líneas Ultra Finas",
                data=buf.getvalue(),
                file_name="Diario_Final_Elegante.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Columnas clave no encontradas.")

    except Exception as e:
        st.error(f"Error: {e}")
