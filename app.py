import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato Profesional")
st.markdown("Diagnóstico activo: Si falta una columna, el sistema te dirá cuál es.")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
        
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA', 'F. Contable', 'Fecha Contable'],
            'asiento': ['Asiento', 'Num_Asiento', 'Poliza', 'Nro', 'ASIENTO', 'Asiento Nro', 'Número', 'Comprobante'],
            'cuenta': ['Cuenta', 'Código', 'Cod_Cuenta', 'Cta', 'CUENTA', 'Cod. Cuenta', 'Codigo'],
            'desc_cuenta': ['Nombre Cuenta', 'Descripción Cuenta', 'Nombre_Cuenta', 'DESCRIPCION CUENTA', 'Cuenta Nombre'],
            'comprobante': ['Comprobante', 'Nro Comprobante', 'Comp.', 'Voucher', 'Nro. Comp.'],
            'concepto': ['Concepto de pase', 'Descripcion', 'Detalle', 'Concepto', 'DESCRIPCION', 'Glosa'],
            'debe': ['Débitos', 'Debe', 'Débito', 'Cargo', 'DEBE', 'Debito'],
            'haber': ['Créditos', 'Haber', 'Crédito', 'Abono', 'HABER', 'Credito']
        }
        
        def detectar(lista, reales):
            for s in lista:
                if s in reales: return s
            return None

        # Buscamos cada columna
        c_fecha = detectar(mapeo['fecha'], cols)
        c_asiento = detectar(mapeo['asiento'], cols)
        c_cta = detectar(mapeo['cuenta'], cols)
        c_desc_cta = detectar(mapeo['desc_cuenta'], cols)
        c_comp = detectar(mapeo['comprobante'], cols)
        c_conc = detectar(mapeo['concepto'], cols)
        c_debe = detectar(mapeo['debe'], cols)
        c_haber = detectar(mapeo['haber'], cols)

        # VALIDACIÓN DETALLADA
        if c_fecha and c_asiento:
            # --- PROCESAMIENTO (Igual al anterior pero optimizado) ---
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])

            def armar_leyenda(row):
                base = str(row[c_conc]) if c_conc and pd.notna(row[c_conc]) else ""
                extra = str(row[c_comp]) if c_comp and pd.notna(row[c_comp]) else ""
                return f"{base} {extra}".strip()

            df_ordenado['Leyenda'] = df_ordenado.apply(armar_leyenda, axis=1)

            for col_orig, nombre_final in zip([c_debe, c_haber], ['Debe', 'Haber']):
                if col_orig:
                    df_ordenado[nombre_final] = df_ordenado[col_orig].astype(str).str.replace(',', '.')
                    df_ordenado[nombre_final] = pd.to_numeric(df_ordenado[nombre_final], errors='coerce').fillna(0)
                else:
                    df_ordenado[nombre_final] = 0.0

            final_cta = c_cta if c_cta else "Cuenta"
            final_desc = c_desc_cta if c_desc_cta else "Descripción Cuenta"
            if not c_cta: df_ordenado[final_cta] = ""
            if not c_desc_cta: df_ordenado[final_desc] = ""

            columnas_finales = [c_fecha, final_cta, final_desc, 'Leyenda', 'Debe', 'Haber']
            df_final = df_ordenado[columnas_finales].copy()
            df_final[c_fecha] = df_final[c_fecha].dt.strftime('%d/%m/%Y')
            
            duplicados = df_ordenado[c_asiento].duplicated()
            df_final.loc[duplicados, [c_fecha, 'Leyenda']] = ""

            lista_final = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            fila_separadora = pd.DataFrame([["MARK_BLACK"] * len(df_final.columns)], columns=df_final.columns)

            for asiento in asientos_unicos:
                filas_asiento = df_final[df_ordenado[c_asiento] == asiento]
                lista_final.append(filas_asiento)
                lista_final.append(fila_separadora)

            df_exportar = pd.concat(lista_final, ignore_index=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_exportar.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook  = writer.book
                worksheet = writer.sheets['Libro Diario']
                
                f_miles = workbook.add_format({'num_format': '#,##0.00'})
                f_negro = workbook.add_format({'bg_color': '#000000'})
                f_head  = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})

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
                        for col_idx in range(len(df_exportar.columns)):
                            worksheet.write(row_num + 1, col_idx, "", f_negro)

            st.success("✅ ¡Diario procesado con éxito!")
            st.download_button(label="📥 Descargar Libro Diario", data=buf.getvalue(), file_name="Diario_Final.xlsx")
            
        else:
            # --- SECCIÓN DE DIAGNÓSTICO ---
            st.error("❌ No se pudieron identificar las columnas necesarias.")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Buscaba:")
                st.write(f"- Fecha: {'✅' if c_fecha else '❌ (No encontrada)'}")
                st.write(f"- Asiento/Número: {'✅' if c_asiento else '❌ (No encontrada)'}")
                st.write(f"- Debe: {'✅' if c_debe else '⚠️ (Usando 0)'}")
                st.write(f"- Haber: {'✅' if c_haber else '⚠️ (Usando 0)'}")
            
            with col2:
                st.subheader("Encontró en tu Excel:")
                st.write(cols)
            
            st.info("💡 Tip: Asegúrate de que los nombres de las columnas estén en la primera fila de tu Excel.")

    except Exception as e:
        st.error(f"Error: {e}")
