import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato Profesional")
st.markdown("Columnas: **Fecha | Cuenta | Descripción Cuenta | Leyenda | Debe | Haber**")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
        
        # Mapeo ultra-reforzado
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA', 'F. Contable', 'Fecha Contable'],
            'asiento': ['Asiento', 'Num_Asiento', 'Poliza', 'Nro', 'ASIENTO', 'Asiento Nro', 'Número', 'Comprobante'],
            'cuenta': ['Cuenta', 'Código', 'Cod_Cuenta', 'Cta', 'CUENTA', 'Cod. Cuenta', 'Codigo'],
            'desc_cuenta': ['Nombre Cuenta', 'Descripción Cuenta', 'Nombre_Cuenta', 'DESCRIPCION CUENTA', 'Cuenta Nombre', 'Nombre de la Cuenta', 'Descripcion Cuenta'],
            'comprobante': ['Comprobante', 'Nro Comprobante', 'Comp.', 'Voucher', 'Nro. Comp.'],
            'concepto': ['Concepto de pase', 'Descripcion', 'Detalle', 'Concepto', 'DESCRIPCION', 'Glosa'],
            'debe': ['Débitos', 'Debe', 'Débito', 'Cargo', 'DEBE', 'Debito'],
            'haber': ['Créditos', 'Haber', 'Crédito', 'Abono', 'HABER', 'Credito']
        }
        
        def detectar(lista, reales):
            for s in lista:
                if s in reales: return s
            return None

        # Identificación de columnas
        c_fecha = detectar(mapeo['fecha'], cols)
        c_asiento = detectar(mapeo['asiento'], cols)
        c_cta = detectar(mapeo['cuenta'], cols)
        c_desc_cta = detectar(mapeo['desc_cuenta'], cols)
        c_comp = detectar(mapeo['comprobante'], cols)
        c_conc = detectar(mapeo['concepto'], cols)
        c_debe = detectar(mapeo['debe'], cols)
        c_haber = detectar(mapeo['haber'], cols)

        if c_fecha and c_asiento:
            # 1. Limpieza y Orden
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])

            # 2. Leyenda Fusionada
            def armar_leyenda(row):
                base = str(row[c_conc]) if c_conc and pd.notna(row[c_conc]) else ""
                extra = str(row[c_comp]) if c_comp and pd.notna(row[c_comp]) else ""
                return f"{base} {extra}".strip()

            df_ordenado['Leyenda'] = df_ordenado.apply(armar_leyenda, axis=1)

            # 3. Formato Numérico (Debe/Haber)
            for col_orig, nombre_final in zip([c_debe, c_haber], ['Debe', 'Haber']):
                if col_orig:
                    df_ordenado[nombre_final] = df_ordenado[col_orig].astype(str).str.replace(',', '.')
                    df_ordenado[nombre_final] = pd.to_numeric(df_ordenado[nombre_final], errors='coerce').fillna(0)
                else:
                    df_ordenado[nombre_final] = 0.0

            # 4. Preparar Columnas Finales (Asegurando la Descripción de Cuenta)
            final_cta = c_cta if c_cta else "Cuenta"
            final_desc_cta = c_desc_cta if c_desc_cta else "Descripción Cuenta"
            
            if not c_cta: df_ordenado[final_cta] = ""
            if not c_desc_cta: df_ordenado[final_desc_cta] = ""

            columnas_finales = [c_fecha, final_cta, final_desc_cta, 'Leyenda', 'Debe', 'Haber']
            df_final = df_ordenado[columnas_finales].copy()
            
            # 5. Estética: Limpiar repetidos por asiento (EXCEPTO la cuenta)
            df_final[c_fecha] = df_final[c_fecha].dt.strftime('%d/%m/%Y')
            duplicados = df_ordenado[c_asiento].duplicated()
            
            # Solo vaciamos Fecha y Leyenda en las filas repetidas
            df_final.loc[duplicados, [c_fecha, 'Leyenda']] = ""

            # 6. Estructura con separadores
            lista_export = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            fila_separadora = pd.DataFrame([["MARK_BLACK"] * len(df_final.columns)], columns=df_final.columns)

            for asiento in asientos_unicos:
                filas = df_final[df_ordenado[c_asiento] == asiento]
                lista_export.append(filas)
                lista_export.append(fila_separadora)

            df_exportar = pd.concat(lista_export, ignore_index=True)

            # 7. Excel con XlsxWriter
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                f_miles = workbook.add_format({'num_format': '#,##0.00'})
                f_negro = workbook.add_format({'bg_color': '#000000'})
                f_head  = workbook.add_format({'bold': True, 'bg_color': '#EFEFEF', 'border': 1})

                for col_num, value in enumerate(df_exportar.columns.values):
                    worksheet.write(0, col_num, value, f_head)

                for i, col in enumerate(df_exportar.columns):
                    longitudes = [len(str(val)) for val in df_exportar[col].values]
                    max_len = max(longitudes + [len(str(col))]) + 2
                    if col in ['Debe', 'Haber']:
                        worksheet.set_column(i, i, max_len, f_miles)
                    else:
                        worksheet.set_column(i, i, min(max_len, 50))

                for row_num in range(len(df_exportar)):
                    if df_exportar.iloc[row_num, 0] == "MARK_BLACK":
                        worksheet.set_row(row_num + 1, 2, f_negro)
                        for c_idx in range(len(df_exportar.columns)):
                            worksheet.write(row_num + 1, c_idx, "", f_negro)

            st.success("✅ ¡Libro Diario completo! La descripción de cuenta está incluida.")
            st.download_button(label="📥 Descargar Libro Diario", data=buf.getvalue(), file_name="Libro_Diario_Completo.xlsx")
            
        else:
            st.error("❌ Faltan columnas vitales.")
            st.write("Detectadas:", cols)

    except Exception as e:
        st.error(f"Error: {e}")
