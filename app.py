import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide", page_icon="⚖️")

st.title("⚙️ Procesador Avanzado: Mayor a Diario")
st.markdown("Ahora con **separación automática** entre asientos para una mejor lectura.")

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
            # Limpieza y formato
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            
            if c_debe: df[c_debe] = pd.to_numeric(df[c_debe], errors='coerce').fillna(0)
            if c_haber: df[c_haber] = pd.to_numeric(df[c_haber], errors='coerce').fillna(0)
            
            # Cuadratura
            total_d = df[c_debe].sum() if c_debe else 0
            total_h = df[c_haber].sum() if c_haber else 0
            dif = round(total_d - total_h, 2)

            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total DEBE", f"{total_d:,.2f}")
            m2.metric("Total HABER", f"{total_h:,.2f}")
            m3.metric("DIFERENCIA", f"{dif:,.2f}", delta=dif, delta_color="inverse")

            # --- LÓGICA DE INTERLÍNEA ---
            # Ordenamos primero
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])
            
            # Creamos una lista para almacenar las filas con espacios
            lista_filas = []
            asientos = df_ordenado[c_asiento].unique()
            
            for asiento in asientos:
                # Extraemos las filas de este asiento específico
                filas_asiento = df_ordenado[df_ordenado[c_asiento] == asiento]
                lista_filas.append(filas_asiento)
                
                # Insertamos una fila vacía (Serie de NaNs)
                fila_vacia = pd.DataFrame([[None] * len(cols)], columns=cols)
                lista_filas.append(fila_vacia)
            
            # Concatenamos todo de nuevo
            df_final = pd.concat(lista_filas, ignore_index=True)

            st.subheader("Vista Previa del Diario (con espacios)")
            st.dataframe(df_final, use_container_width=True)

            # Descarga
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name="Libro Diario")
            
            st.download_button(
                label="📥 Descargar Diario con Interlíneas",
                data=buf.getvalue(),
                file_name="Diario_con_Espacios.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error(f"❌ No se identificaron columnas clave. Columnas: {cols}")

    except Exception as e:
        st.error(f"Error: {e}")
