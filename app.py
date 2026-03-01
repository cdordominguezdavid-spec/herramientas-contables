import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Suite Contable: Libro Diario Profesional")
st.markdown("Configuración: **Fecha y Leyenda únicos por asiento** | **Formato Contable (1.234,56)**")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
        
        # Mapeo de columnas
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA'],
            'asiento': ['Asiento', 'Num_Asiento', 'Poliza', 'Nro', 'ASIENTO'],
            'cuenta': ['Cuenta', 'Código', 'Cod_Cuenta', 'Cta', 'CUENTA'],
            'desc_cuenta': ['Nombre Cuenta', 'Descripción Cuenta', 'Nombre_Cuenta', 'DESCRIPCION CUENTA'],
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
        c_cta = detectar(mapeo['cuenta'], cols)
        c_desc_cta = detectar(mapeo['desc_cuenta'], cols)
        c_comp = detectar(mapeo['comprobante'], cols)
        c_conc = detectar(mapeo['concepto'], cols)
        c_debe = detectar(mapeo['debe'], cols)
        c_haber = detectar(mapeo['haber'], cols)

        if c_fecha and c_asiento:
            # 1. Preparación de datos
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])

            # 2. Lógica de Leyenda (Concepto + Comprobante)
            def armar_leyenda(row):
                base = str(row[c_conc]) if c_conc and pd.notna(row[c_conc]) else ""
                extra = str(row[c_comp]) if c_comp and pd.notna(row[c_comp]) else ""
                return f"{base} {extra}".strip()

            df_ordenado['Leyenda'] = df_ordenado.apply(armar_leyenda, axis=1)

            # 3. Formato Numérico y Renombrado (Debe/Haber)
            for col_orig, nombre_final in zip([c_debe, c_haber], ['Debe', 'Haber']):
                if col_orig:
                    df_ordenado[nombre_final] = df_ordenado[col_orig].astype(str).str.replace(',', '.')
                    df_ordenado[nombre_final] = pd.to_numeric(df_ordenado[nombre_final], errors='coerce').fillna(0)
                else:
                    df_ordenado[nombre_final] = 0.0

            # 4. Organización de Columnas Finales
            col_cta_final = c_cta if c_cta else "Cuenta"
            col_desc_final = c_desc_cta if c_desc_cta else "Descripción Cuenta"
            
            if not c_cta: df_ordenado[col_cta_final] = ""
            if not c_desc_cta: df_ordenado[col_desc_final] = ""

            columnas_finales = [c_fecha, col_cta_final, col_desc_final, 'Leyenda', 'Debe', 'Haber']
            df_final = df_ordenado[columnas_finales].copy()

            # 5. Formateo de Visibilidad (Solo primera fila por asiento)
            df_final[c_fecha] = df_final[c_fecha].dt.strftime('%d/%m/%Y')
            duplicados = df_ordenado[c_asiento].duplicated()
            
            # Limpiamos Fecha y Leyenda en filas repetidas del mismo asiento
            df_final.loc[duplicados, [c_fecha, 'Leyenda']] = ""

            # 6. Construcción con separadores negros
            lista_final = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            fila_separadora = pd.DataFrame([["MARK_BLACK"] * len(df_final.columns)], columns=df_final.columns)

            for asiento in asientos_unicos:
                filas = df_final[df_ordenado[c_asiento] == asiento]
                lista_final.append(filas)
                lista_final.append(fila_separadora.copy())

            df_exportar = pd.concat(lista_final, ignore_index=True)

            # 7. Exportación a Excel con formato de miles
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                # Formato: Punto para miles y 2 decimales
                formato_miles = workbook.add_format({'num_format': '#,##0.00'})
                formato_negro = workbook.add_format({'bg_color': '#000000'})
                formato_head  = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})

                # Encabezados
                for col_num, value in enumerate(df_exportar.columns.values):
                    worksheet.write(0, col_num, value, formato_head)

                # Ajuste de columnas
                for i, col in enumerate(df_exportar.columns):
                    max_len = max([len(str(val)) for val in df_exportar[col].values] + [len(col)]) + 2
                    if col in ['Debe', 'Haber']:
                        worksheet.set_column(i, i, max_len, formato_miles)
                    else:
                        worksheet.set_column(i, i, min(max_len, 50))

                # Pintar separadores
                for row_num in range(len(df_exportar)):
                    if df_exportar.iloc[row_num, 0] == "MARK_BLACK":
                        worksheet.set_row(row_num + 1, 2, formato_negro)
                        for col_idx in range(len(df_exportar.columns)):
                            worksheet.write(row_num + 1, col_idx, "", formato_negro)

            st.success("✅ ¡Libro Diario generado correctamente!")
            st.download_button(
                label="📥 Descargar Libro Diario Final",
                data=buf.getvalue(),
                file_name="Libro_Diario_Profesional.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No se detectaron columnas clave (Fecha o Asiento).")

    except Exception as e:
        st.error(f"Error: {e}")
