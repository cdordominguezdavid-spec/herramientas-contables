import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato Final")
st.markdown("Columnas: **Fecha | Cuenta | Descripción Cuenta | Leyenda | Debe | Haber**")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
        
        # --- MAPEO REFORZADO (Aquí es donde estaba el fallo) ---
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA', 'F. Contable'],
            'asiento': ['Asiento', 'Num_Asiento', 'Poliza', 'Nro', 'ASIENTO', 'Asiento Nro', 'Número'],
            'cuenta': ['Cuenta', 'Código', 'Cod_Cuenta', 'Cta', 'CUENTA', 'Cod. Cuenta'],
            'desc_cuenta': ['Nombre Cuenta', 'Descripción Cuenta', 'Nombre_Cuenta', 'DESCRIPCION CUENTA', 'Cuenta Nombre'],
            'comprobante': ['Comprobante', 'Nro Comprobante', 'Comp.', 'Voucher', 'Nro. Comp.'],
            'concepto': ['Concepto de pase', 'Descripcion', 'Detalle', 'Concepto', 'DESCRIPCION', 'Glosa'],
            'debe': ['Débitos', 'Debe', 'Débito', 'Cargo', 'DEBE', 'Debito'],
            'haber': ['Créditos', 'Haber', 'Crédito', 'Abono', 'HABER', 'Credito']
        }
        
        def detectar(lista_opciones, reales):
            for opcion in lista_opciones:
                if opcion in reales: return opcion
            return None

        # Detectamos las columnas reales
        c_fecha = detectar(mapeo['fecha'], cols)
        c_asiento = detectar(mapeo['asiento'], cols)
        c_cta = detectar(mapeo['cuenta'], cols)
        c_desc_cta = detectar(mapeo['desc_cuenta'], cols)
        c_comp = detectar(mapeo['comprobante'], cols)
        c_conc = detectar(mapeo['concepto'], cols)
        c_debe = detectar(mapeo['debe'], cols)
        c_haber = detectar(mapeo['haber'], cols)

        # Si falta alguna vital, intentamos por posición (Plan B)
        if not c_asiento and len(cols) > 1: c_asiento = cols[1] # A veces la 2da col es el asiento

        if c_fecha and c_asiento:
            # 1. Limpieza inicial
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])

            # 2. Crear Leyenda (Fusión)
            def armar_leyenda(row):
                base = str(row[c_conc]) if c_conc and pd.notna(row[c_conc]) else ""
                extra = str(row[c_comp]) if c_comp and pd.notna(row[c_comp]) else ""
                return f"{base} {extra}".strip()

            df_ordenado['Leyenda'] = df_ordenado.apply(armar_leyenda, axis=1)

            # 3. Formatear Debe y Haber (Miles con punto)
            for col_orig, nombre_final in zip([c_debe, c_haber], ['Debe', 'Haber']):
                if col_orig:
                    df_ordenado[nombre_final] = df_ordenado[col_orig].astype(str).str.replace(',', '.')
                    df_ordenado[nombre_final] = pd.to_numeric(df_ordenado[nombre_final], errors='coerce').fillna(0)
                else:
                    df_ordenado[nombre_final] = 0.0

            # 4. Seleccionar y Renombrar Columnas Finales
            col_cta_final = c_cta if c_cta else "Cuenta"
            col_desc_final = c_desc_cta if c_desc_cta else "Descripción Cuenta"
            
            # Si no las detectó, creamos vacías para no romper el código
            if not c_cta: df_ordenado[col_cta_final] = ""
            if not c_desc_cta: df_ordenado[col_desc_final] = ""

            columnas_finales = [c_fecha, col_cta_final, col_desc_final, 'Leyenda', 'Debe', 'Haber']
            df_final = df_ordenado[columnas_finales].copy()

            # 5. Estética: Limpiar repetidos por asiento
            df_final[c_fecha] = df_final[c_fecha].dt.strftime('%d/%m/%Y')
            duplicados = df_ordenado[c_asiento].duplicated()
            df_final.loc[duplicados, [c_fecha, 'Leyenda']] = ""

            # 6. Preparar Exportación con separadores
            lista_export = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            # Fila separadora (marcador)
            fila_separadora = pd.DataFrame([["SEPARAR"] * len(df_final.columns)], columns=df_final.columns)

            for asiento in asientos_unicos:
                filas = df_final[df_ordenado[c_asiento] == asiento]
                lista_export.append(filas)
                lista_export.append(fila_separadora)

            df_exportar = pd.concat(lista_export, ignore_index=True)

            # 7. Crear Excel con formato
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                f_miles = workbook.add_format({'num_format': '#,##0.00'})
                f_negro = workbook.add_format({'bg_color': '#000000'})
                f_head  = workbook.add_format({'bold': True, 'bg_color': '#EFEFEF', 'border': 1})

                # Encabezados
                for col_num, value in enumerate(df_exportar.columns.values):
                    worksheet.write(0, col_num, value, f_head)

                # Formato y Ancho
                for i, col in enumerate(df_exportar.columns):
                    longitudes = [len(str(val)) for val in df_exportar[col].values]
                    max_len = max(longitudes + [len(str(col))]) + 2
                    if col in ['Debe', 'Haber']:
                        worksheet.set_column(i, i, max_len, f_miles)
                    else:
                        worksheet.set_column(i, i, min(max_len, 50))

                # Líneas divisorias (2pt)
                for row_num in range(len(df_exportar)):
                    if df_exportar.iloc[row_num, 0] == "SEPARAR":
                        worksheet.set_row(row_num + 1, 2, f_negro)
                        # Limpiamos el texto "SEPARAR" para que no se vea
                        for col_c in range(len(df_exportar.columns)):
                            worksheet.write(row_num + 1, col_c, "", f_negro)

            st.success("✅ ¡Listo! Reporte procesado correctamente.")
            st.download_button(label="📥 Descargar Libro Diario", data=buf.getvalue(), file_name="Libro_Diario_Pro.xlsx")
            
        else:
            st.error("❌ Aún no detecto las columnas.")
            st.info(f"Columnas detectadas en tu archivo: {cols}")
            st.warning("Asegúrate de que el Excel tenga encabezados claros.")

    except Exception as e:
        st.error(f"Error inesperado: {e}")
