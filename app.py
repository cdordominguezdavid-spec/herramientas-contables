import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide", page_icon="⚖️")

st.title("⚙️ Procesador Avanzado: Mayor a Diario")
st.markdown("Revisión: Fecha **DD/MM/AAAA** y **Separadores Negros** de asientos.")

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
        
        def detectar(lista_sinonimos, reales):
            for s in lista_sinonimos:
                if s in reales: return s
            return None

        c_fecha = detectar(mapeo['fecha'], cols)
        c_asiento = detectar(mapeo['asiento'], cols)
        c_debe = detectar(mapeo['debe'], cols)
        c_haber = detectar(mapeo['haber'], cols)

        if c_fecha and c_asiento:
            # --- 1. FORMATO DE FECHA ---
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            
            if c_debe: df[c_debe] = pd.to_numeric(df[c_debe], errors='coerce').fillna(0)
            if c_haber: df[c_haber] = pd.to_numeric(df[c_haber], errors='coerce').fillna(0)
            
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])
            # Formateamos la fecha para el Excel final
            df_ordenado[c_fecha] = df_ordenado[c_fecha].dt.strftime('%d/%m/%Y')

            # --- 2. LÓGICA DE SEPARACIÓN ---
            lista_final = []
            indices_separadores = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            
            contador_filas = 0
            for asiento in asientos_unicos:
                filas_asiento = df_ordenado[df_ordenado[c_asiento] == asiento]
                lista_final.append(filas_asiento)
                contador_filas += len(filas_asiento)
                
                # Creamos una fila vacía que luego pintaremos de negro
                fila_vacia = pd.DataFrame([[None] * len(cols)], columns=cols)
                lista_final.append(fila_vacia)
                
                # Guardamos el índice de esta fila para pintarla después
                indices_separadores.append(contador_filas)
                contador_filas += 1 # Sumamos la fila vacía al contador

            df_exportar = pd.concat(lista_final, ignore_index=True)

            # --- 3. GENERAR EXCEL CON FORMATO (Línea Negra) ---
            buf = io.BytesIO()
            # Usamos xlsxwriter como motor para poder dar formato
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                # Definimos el formato negro
                formato_negro = workbook.add_format({'bg_color': '#000000'})
                
                # Pintamos las filas de los separadores
                for fila_idx in indices_separadores:
                    # Pintamos desde la columna A hasta la última columna con datos
                    # fila_idx + 1 porque Excel cuenta desde 1 y tiene encabezados
                    worksheet.set_row(fila_idx + 1, None, formato_negro)

            st.success("✅ ¡Procesado con éxito!")
            st.download_button(
                label="📥 Descargar Diario con Líneas Negras",
                data=buf.getvalue(),
                file_name="Diario_Profesional.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No se detectaron columnas clave.")

    except Exception as e:
        st.error(f"Error: {e}")
