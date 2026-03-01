import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Suite Contable: Libro Diario Profesional")
st.markdown("Diagnóstico: **Buscando columnas automáticamente...**")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        # Cargamos el Excel
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
        
        # --- DICCIONARIO DE SINÓNIMOS (Ampliado) ---
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA', 'F. Contable', 'F.Contable', 'Fecha Contable'],
            'asiento': ['Asiento', 'Num_Asiento', 'Poliza', 'Nro', 'ASIENTO', 'Asiento Nro', 'Número', 'No. Asiento'],
            'cuenta': ['Cuenta', 'Código', 'Cod_Cuenta', 'Cta', 'CUENTA', 'Cod. Cuenta', 'Codigo'],
            'desc_cuenta': ['Nombre Cuenta', 'Descripción Cuenta', 'Nombre_Cuenta', 'DESCRIPCION CUENTA', 'Cuenta Nombre', 'Nombre de la Cuenta'],
            'comprobante': ['Comprobante', 'Nro Comprobante', 'Comp.', 'Voucher', 'Nro. Comp.'],
            'concepto': ['Concepto de pase', 'Descripcion', 'Detalle', 'Concepto', 'DESCRIPCION', 'Glosa', 'Concepto Pase'],
            'debe': ['Débitos', 'Debe', 'Débito', 'Cargo', 'DEBE', 'Debito'],
            'haber': ['Créditos', 'Haber', 'Crédito', 'Abono', 'HABER', 'Credito']
        }
        
        def detectar(lista_opciones, reales):
            for opcion in lista_opciones:
                if opcion in reales: return opcion
            return None

        # Identificamos qué columna es cada una
        c_fecha = detectar(mapeo['fecha'], cols)
        c_asiento = detectar(mapeo['asiento'], cols)
        c_cta = detectar(mapeo['cuenta'], cols)
        c_desc_cta = detectar(mapeo['desc_cuenta'], cols)
        c_comp = detectar(mapeo['comprobante'], cols)
        c_conc = detectar(mapeo['concepto'], cols)
        c_debe = detectar(mapeo['debe'], cols)
        c_haber = detectar(mapeo['haber'], cols)

        # SI DETECTA LAS COLUMNAS VITALES, PROCESA:
        if c_fecha and c_asiento:
            # 1. Preparación
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])

            # 2. Fusión Leyenda (Concepto + Comprobante)
            def armar_leyenda(row):
                base = str(row[c_conc]) if c_conc and pd.notna(row[c_conc]) else ""
                extra = str(row[c_comp]) if c_comp and pd.notna(row[c_comp]) else ""
                return f"{base} {extra}".strip()

            df_ordenado['Leyenda'] = df_ordenado.apply(armar_leyenda, axis=1)

            # 3. Números (Puntos para miles)
            for col_orig, nombre_final in zip([c_debe, c_haber], ['Debe', 'Haber']):
                if col_orig:
                    df_ordenado[nombre_final] = df_ordenado[col_orig].astype(str).str.replace(',', '.')
                    df_ordenado[nombre_final] = pd.to_numeric(df_ordenado[nombre_final], errors='coerce').fillna(0)
                else:
                    df_ordenado[nombre_final] = 0.0

            # 4. Columnas Finales
            f_cta = c_cta if c_cta else "Cuenta"
            f_desc = c_desc_cta if c_desc_cta else "Descripción Cuenta"
            if not c_cta: df_ordenado[f_cta] = ""
            if not c_desc_cta: df_ordenado[f_desc] = ""

            columnas_finales = [c_fecha, f_cta, f_desc, 'Leyenda', 'Debe', 'Haber']
            df_final = df_ordenado[columnas_finales].copy()

            # 5. Estética (Fecha y Leyenda solo arriba)
            df_final[c_fecha] = df_final[c_fecha].dt.strftime('%d/%m/%Y')
            duplicados = df_ordenado[c_asiento].duplicated()
            df_final.loc[duplicados, [c_fecha, 'Leyenda']] = ""

            # 6. Construcción con separadores
            lista_final = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            fila_separadora = pd.DataFrame([["MARK_BLACK"] * len(df_final.columns)], columns=df_final.columns)

            for asiento in asientos_unicos:
                filas = df_final[df_ordenado[c_asiento] == asiento]
                lista_final.append(filas)
                lista_final.append(fila_separadora.copy())

            df_exportar = pd.concat(lista_final, ignore_index=True)

            # 7. Excel
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
                    max_len = max([len(str(val)) for val in df_exportar[col].values] + [len(col)]) + 2
                    if col in ['Debe', 'Haber']:
                        worksheet.set_column(i, i, max_len, f_miles)
                    else:
                        worksheet.set_column(i, i, min(max_len, 50))

                for row_num in range(len(df_exportar)):
                    if df_exportar.iloc[row_num, 0] == "MARK_BLACK":
                        worksheet.set_row(row_num + 1, 2, f_negro)
                        for c_idx in range(len(df_exportar.columns)):
                            worksheet.write(row_num + 1, c_idx, "", f_negro)

            st.success("✅ ¡Columnas detectadas y Diario generado!")
            st.download_button(label="📥 Descargar Libro Diario", data=buf.getvalue(), file_name="Libro_Diario_Final.xlsx")
            
        else:
            # --- DIAGNÓSTICO EN CASO DE ERROR ---
            st.error("❌ No pude encontrar las columnas necesarias.")
            st.subheader("Tu Excel tiene estas columnas:")
            st.write(cols)
            st.info("💡 Por favor, dime cómo se llaman las columnas de Fecha y Asiento en tu lista para agregarlas.")

    except Exception as e:
        st.error(f"Error: {e}")
