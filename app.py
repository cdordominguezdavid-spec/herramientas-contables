import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato Final")
st.markdown("Basado en tus columnas: **Fecha | Cuenta | Descripción cuenta | Comprobante | Concepto pase | Débitos | Créditos**")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        # --- MAPEO EXACTO SEGÚN TU IMAGEN ---
        # Forzamos los nombres que se ven en tu captura
        c_fecha = "Fecha"
        c_cta = "Cuenta"
        c_desc_cta = "Descripción cuenta"
        c_comp = "Comprobante"
        c_conc = "Concepto pase"
        c_debe_orig = "Débitos"
        c_haber_orig = "Créditos"

        # Verificamos si las columnas existen en el archivo subido
        columnas_actuales = df.columns.tolist()
        if c_fecha in columnas_actuales:
            
            # 1. Limpieza de Fecha
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill() # Rellenamos hacia abajo si hay huecos
            df = df.dropna(subset=[c_fecha])
            
            # 2. Fusión de "Leyenda" (Concepto pase + Comprobante)
            def armar_leyenda(row):
                base = str(row[c_conc]) if c_conc in row and pd.notna(row[c_conc]) else ""
                extra = str(row[c_comp]) if c_comp in row and pd.notna(row[c_comp]) else ""
                return f"{base} {extra}".strip()
            
            df['Leyenda'] = df.apply(armar_leyenda, axis=1)

            # 3. Formato de Números (Debe y Haber)
            for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                if col_orig in columnas_actuales:
                    df[nombre_nuevo] = df[col_orig].astype(str).str.replace(',', '.')
                    df[nombre_nuevo] = pd.to_numeric(df[nombre_nuevo], errors='coerce').fillna(0)
                else:
                    df[nombre_nuevo] = 0.0

            # 4. Selección de Columnas Finales
            # Usamos los nombres exactos que quieres
            df_final = df[[c_fecha, c_cta, c_desc_cta, 'Leyenda', 'Debe', 'Haber']].copy()

            # 5. Estética: Fecha y Leyenda solo en la primera fila de cada grupo de fecha
            df_final['Fecha_Str'] = df_final[c_fecha].dt.strftime('%d/%m/%Y')
            
            # Como no hay número de asiento, agrupamos por Fecha y Leyenda
            duplicados = df.duplicated(subset=[c_fecha, 'Leyenda'])
            
            df_final.loc[duplicados, ['Fecha_Str', 'Leyenda']] = ""
            
            # Reorganizamos para el Excel final
            df_final = df_final[['Fecha_Str', c_cta, c_desc_cta, 'Leyenda', 'Debe', 'Haber']]
            df_final.columns = ['Fecha', 'Cuenta', 'Descripción Cuenta', 'Leyenda', 'Debe', 'Haber']

            # 6. Generar Excel
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                f_miles = workbook.add_format({'num_format': '#,##0.00'})
                f_head  = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})

                for col_num, value in enumerate(df_final.columns.values):
                    worksheet.write(0, col_num, value, f_head)

                for i, col in enumerate(df_final.columns):
                    max_len = max([len(str(val)) for val in df_final[col].values] + [len(col)]) + 2
                    if col in ['Debe', 'Haber']:
                        worksheet.set_column(i, i, max_len, f_miles)
                    else:
                        worksheet.set_column(i, i, min(max_len, 50))

            st.success("✅ ¡Libro Diario procesado con éxito!")
            st.download_button(label="📥 Descargar Libro Diario", data=buf.getvalue(), file_name="Libro_Diario_Final.xlsx")
            
        else:
            st.error(f"No encontré la columna '{c_fecha}'. Revisa los encabezados de tu Excel.")

    except Exception as e:
        st.error(f"Error técnico: {e}")
