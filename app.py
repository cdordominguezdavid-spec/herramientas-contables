import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Suite Contable: Libro Diario")
st.markdown("Mejora: **Descripción fusionada** (Concepto + Comprobante) solo en la primera fila.")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA'],
            'asiento': ['Asiento', 'Num_Asiento', 'Poliza', 'Nro', 'ASIENTO'],
            'comprobante': ['Comprobante', 'Nro Comprobante', 'Comp.', 'Voucher'],
            'concepto': ['Concepto de pase', 'Descripcion', 'Detalle', 'Concepto', 'DESCRIPCION'],
            'debe': ['Débitos', 'Debe', 'Débito', 'Cargo', 'DEBE'],
            'haber': ['Créditos', 'Haber', 'Crédito', 'Abono', 'HABER']
        }
        
        def detectar(lista, reales):
            for s in lista:
                if s in reales: return s
            return None

        c_fecha = detectar(mapeo['fecha'], cols)
        c_asiento = detectar(mapeo['asiento'], cols)
        c_comp = detectar(mapeo['comprobante'], cols)
        c_conc = detectar(mapeo['concepto'], cols)
        c_debe = detectar(mapeo['debe'], cols)
        c_haber = detectar(mapeo['haber'], cols)

        if c_fecha and c_asiento:
            # 1. Preparación de datos
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])

            # 2. LÓGICA DE CONCATENACIÓN (Concepto + Comprobante)
            # Si existe Comprobante, lo sumamos al Concepto. Si no, solo Concepto.
            def armar_descripcion(row):
                base = str(row[c_conc]) if c_conc and pd.notna(row[c_conc]) else ""
                extra = str(row[c_comp]) if c_comp and pd.notna(row[c_comp]) else ""
                return f"{base} {extra}".strip()

            df_ordenado['Descripción'] = df_ordenado.apply(armar_descripcion, axis=1)

            # 3. Limpieza de Números
            for col_num in [c_debe, c_haber]:
                if col_num:
                    df_ordenado[col_num] = df_ordenado[col_num].astype(str).str.replace(',', '.')
                    df_ordenado[col_num] = pd.to_numeric(df_ordenado[col_num], errors='coerce').fillna(0)

            # 4. REORDENAR Y FILTRAR COLUMNAS
            # Quitamos 'Comprobante' y el 'Concepto' viejo para dejar solo la nueva 'Descripción'
            cols_finales = [c_fecha, c_asiento, 'Descripción']
            if c_debe: cols_finales.append(c_debe)
            if c_haber: cols_finales.append(c_haber)
            
            # Añadimos cualquier otra columna que no sea Comprobante o Concepto antiguo
            otras = [c for c in df_ordenado.columns if c not in cols_finales and c not in [c_comp, c_conc]]
            df_final = df_ordenado[cols_finales + otras]

            # 5. Formateo de Texto (Solo primera fila por asiento)
            df_vista = df_final.copy()
            df_vista[c_fecha] = df_vista[c_fecha].dt.strftime('%d/%m/%Y')
            
            # Máscara para duplicados (Fecha y Descripción solo en la primera fila del asiento)
            duplicados = df_vista[c_asiento].duplicated()
            df_vista.loc[duplicados, c_fecha] = ""
            df_vista.loc[duplicados, 'Descripción'] = ""

            # 6. Construcción con separadores
            lista_final = []
            asientos_unicos = df_vista[c_asiento].unique()
            fila_separadora = pd.DataFrame([[" "] * len(df_vista.columns)], columns=df_vista.columns)

            for asiento in asientos_unicos:
                filas = df_vista[df_vista[c_asiento] == asiento]
                lista_final.append(filas)
                lista_final.append(fila_separadora)

            df_exportar = pd.concat(lista_final, ignore_index=True)

            # 7. Exportación a Excel
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                formato_miles = workbook.add_format({'num_format': '#,##0.00'})
                formato_negro = workbook.add_format({'bg_color': '#000000'})

                for i, col in enumerate(df_exportar.columns):
                    longitudes = [len(str(val)) for val in df_exportar[col].values]
                    max_len = max(longitudes + [len(str(col))]) + 2
                    
                    if col in [c_debe, c_haber]:
                        worksheet.set_column(i, i, max_len, formato_miles)
                    else:
                        worksheet.set_column(i, i, min(max_len, 60))

                for row_num in range(len(df_exportar)):
                    if df_exportar.iloc[row_num][c_asiento] == " ":
                        worksheet.set_row(row_num + 1, 2, formato_negro)

            st.success("✅ ¡Diario optimizado! Comprobante fusionado en Descripción.")
            st.download_button(
                label="📥 Descargar Diario Final",
                data=buf.getvalue(),
                file_name="Diario_Descripcion_Limpia.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No se detectaron columnas clave (Fecha o Asiento).")

    except Exception as e:
        st.error(f"Error: {e}")
