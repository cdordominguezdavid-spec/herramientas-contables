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
        # Mapeo para identificar qué es qué en el archivo original
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA'],
            'asiento': ['Asiento', 'Num_Asiento', 'Poliza', 'Nro', 'ASIENTO'],
            'cuenta': ['Cuenta', 'Código', 'Cod_Cuenta', 'Cta', 'CUENTA', 'Account'],
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
            # 1. Limpieza y Orden
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce')
            df = df.dropna(subset=[c_fecha])
            df_ordenado = df.sort_values(by=[c_fecha, c_asiento])

            # 2. Crear la "Leyenda" (Fusión de Concepto + Comprobante)
            def armar_leyenda(row):
                base = str(row[c_conc]) if c_conc and pd.notna(row[c_conc]) else ""
                extra = str(row[c_comp]) if c_comp and pd.notna(row[c_comp]) else ""
                return f"{base} {extra}".strip()

            df_ordenado['Leyenda'] = df_ordenado.apply(armar_leyenda, axis=1)

            # 3. Limpieza de Números y Renombramiento
            for c, nombre_nuevo in zip([c_debe, c_haber], ['Debe', 'Haber']):
                if c:
                    df_ordenado[nombre_nuevo] = df_ordenado[c].astype(str).str.replace(',', '.')
                    df_ordenado[nombre_nuevo] = pd.to_numeric(df_ordenado[nombre_nuevo], errors='coerce').fillna(0)

            # 4. Seleccionar solo las columnas deseadas
            # Buscamos nombres para Cuenta y Descripción Cuenta si se detectaron
            col_cta = c_cta if c_cta else (cols[2] if len(cols)>2 else "")
            col_desc_cta = c_desc_cta if c_desc_cta else (cols[3] if len(cols)>3 else "")
            
            # Reordenamos al formato final pedido
            columnas_finales = [c_fecha, col_cta, col_desc_cta, 'Leyenda', 'Debe', 'Haber']
            # Filtramos solo las que existen
            columnas_finales = [c for c in columnas_finales if c in df_ordenado.columns]
            df_final = df_ordenado[columnas_finales].copy()

            # 5. Formateo de visibilidad (Primera fila del asiento)
            df_final[c_fecha] = df_final[c_fecha].dt.strftime('%d/%m/%Y')
            duplicados = df_ordenado[c_asiento].duplicated()
            df_final.loc[duplicados, [c_fecha, 'Leyenda']] = ""

            # 6. Estructura con separadores negros
            lista_export = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            fila_separadora = pd.DataFrame([[" "] * len(df_final.columns)], columns=df_final.columns)

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
                
                # Formatos
                f_miles = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
                f_negro = workbook.add_format({'bg_color': '#000000'})
                f_bold  = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})

                # Encabezados con color gris suave para que resalten
                for col_num, value in enumerate(df_exportar.columns.values):
                    worksheet.write(0, col_num, value, f_bold)

                # Ajuste de columnas y formato de miles
                for i, col in enumerate(df_exportar.columns):
                    max_len = max([len(str(v)) for v in df_exportar[col].values] + [len(col)]) + 2
                    if col in ['Debe', 'Haber']:
                        worksheet.set_column(i, i, max_len, f_miles)
                    else:
                        worksheet.set_column(i, i, min(max_len, 50))

                # Pintar separadores de 2pt
                for row_num in range(len(df_exportar)):
                    # Usamos el espacio en blanco como guía para el separador
                    if df_exportar.iloc[row_num].astype(str).str.contains(" ").all():
                        worksheet.set_row(row_num + 1, 2, f_negro)

            st.success("✅ ¡Libro Diario generado con éxito!")
            st.download_button(
                label="📥 Descargar Libro Diario",
                data=buf.getvalue(),
                file_name="Libro_Diario_Final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No se pudo procesar: Faltan columnas de Fecha o Asiento.")

    except Exception as e:
        st.error(f"Error técnico: {e}")
