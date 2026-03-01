import streamlit as st
import pandas as pd
import io

# Configuración visual
st.set_page_config(page_title="Suite Contable", page_icon="📊")

st.title("📊 Convertidor: Libro Mayor a Diario")
st.markdown("Sube tu archivo Excel del Libro Mayor para reordenarlo.")

# Botón de subida de archivos (Versión Web)
archivo_subido = st.file_uploader("Arrastra aquí tu Excel del Mayor", type=["xlsx", "xls"])

if archivo_subido is not None:
    try:
        # Leer el Excel
        df = pd.read_excel(archivo_subido)
        st.success("✅ Archivo cargado.")
        
        # Mostrar columnas para que el usuario verifique
        st.write("Columnas encontradas:", df.columns.tolist())
        
        # Intentar ordenar (ajusta estos nombres si en tu Excel son distintos)
        columnas_disponibles = df.columns.tolist()
        criterio_orden = [c for c in ['Fecha', 'Asiento', 'Comprobante'] if c in columnas_disponibles]
        
        if criterio_orden:
            df_resultado = df.sort_values(by=criterio_orden)
            st.info(f"Ordenado por: {', '.join(criterio_orden)}")
        else:
            df_resultado = df
            st.warning("⚠️ No se encontraron columnas 'Fecha' o 'Asiento' para ordenar automáticamente.")

        # Botón para descargar el resultado
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_resultado.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Descargar Libro Diario",
            data=buffer.getvalue(),
            file_name="Libro_Diario_Convertido.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
