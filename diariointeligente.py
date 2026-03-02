import streamlit as st
import pandas as pd
import io
import re

# Configuración de página Streamlit
st.set_page_config(page_title="Motor Contable Pro - Apaisado", layout="wide")

st.title("⚖️ Libro Diario: Formato Apaisado de Alta Densidad")

def validar_periodo(texto):
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    match = re.match(patron, texto)
    return (True, "") if match else (False, "Formato: dd/mm/aaaa - dd/mm/aaaa")

if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'

archivo = st.file_uploader("1. Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Empresa:", placeholder="Ej: Mi Empresa S.A.")
    with col2:
        periodo = st.text_input("Período:", placeholder="01/01/2026 - 31/01/2026")
    
    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Generar Diario Apaisado", disabled=not (empresa and periodo)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        try:
            df = pd.read_excel(archivo)
            df = df.dropna(how='all')
            
            # Mapeo de columnas (Asegúrate de que coincidan con tu Excel)
            c_fecha, c_cta, c_desc_cta, c_comp, c_conc, c_debe_orig, c_haber_orig = \
                "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
            df = df.dropna(subset=[c_fecha])
            
            # Crear leyenda combinada
            df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc]) if pd.notna(r[c_conc]) else ''} {str(r[c_comp]) if pd.notna(r[c_comp]) else ''}".strip(), axis=1)
            
            for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                df[nombre_nuevo] = pd.to_numeric(df[col_orig].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            df['Fecha_Aux'] = df[c_fecha].dt.strftime('%d/%m/%Y')
            df['Bloque'] = (df['Fecha_Aux'] + df['Leyenda_Full']).ne((df['Fecha_Aux'] + df['Leyenda_Full']).shift()).cumsum()
            
            lista_final = []
            bloques = df['Bloque'].unique()
            
            for i, b in enumerate(bloques, 1):
                sub_df = df[df['Bloque'] == b].copy()
                n_filas = len(sub_df)
                
                df_bloque = pd.DataFrame({
                    'Fecha': [sub_df.iloc[0][c_fecha].strftime('%d/%m/%y')] + [""] * (n_filas - 1),
                    'Nº': [f"{i}"] + [""] * (n_filas - 1),
                    'Leyenda': [sub_df.iloc[0]['Leyenda_Full']] + [""] * (n_filas - 1),
                    'Cuenta': sub_df[c_cta].astype(str).values,
                    'Descripción de la Cuenta': sub_df[c_desc_cta].values,
                    'Debe': sub_df['Debe'].values,
                    'Haber': sub_df['Haber'].values
                })
                lista_final.append(df_bloque)
                # Separador sutil
                lista_final.append(pd.DataFrame([["SEP"] * 7], columns=df_bloque.columns))

            df_to_excel = pd.concat(lista_final, ignore_index=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Diario")
                workbook, worksheet = writer.book, writer.sheets['Diario']
                
                # Formatos
                f_base = {'font_name': 'Arial Narrow', 'font_size': 8.5}
                f_num = workbook.add_format({**f_base, 'num_format': '#,##0.00;[Red]-#,##0.00;""', 'valign': 'top'})
                f_txt = workbook.add_format({**f_base, 'text_wrap': True, 'valign': 'top'})
                f_head = workbook.add_format({'bold': True, 'font_size': 9, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})
                f_sep = workbook.add_format({'bottom': 1, 'bottom_color': '#CCCCCC'})

                # --- CONFIGURACIÓN DE IMPRESIÓN INTELIGENTE ---
                worksheet.set_landscape() # ORIENTACIÓN APAISADA
                worksheet.set_paper(9)    # A4
                # Margen izquierdo de 1.5cm (0.6 pulg) para encuadernar, otros de 0.5cm
                worksheet.set_margins(left=0.6, right=0.2, top=0.5, bottom=0.4)
                worksheet.fit_to_pages(1, 0) 

                # Encabezado en una sola línea para evitar superposición
                # Formato: Empresa | Período | Página X de Y
                header_text = f"&L&8{empresa}  |  Período: {periodo}&R&8Página &P de &N"
                worksheet.set_header(header_text)

                # Anchos de columna optimizados para Paisaje (Total aprox 100-110)
                worksheet.set_column(0, 0, 8, f_txt)   # Fecha
                worksheet.set_column(1, 1, 4, f_txt)   # Nº
                worksheet.set_column(2, 2, 35, f_txt)  # Leyenda (más espacio)
                worksheet.set_column(3, 3, 10, f_txt)  # Cuenta
                worksheet.set_column(4, 4, 35, f_txt)  # Descripción Cuenta
                worksheet.set_column(5, 6, 14, f_num)  # Importes

                # Estilo de filas
                for row_num, row_data in enumerate(df_to_excel.values, 1):
                    if "SEP" in row_data:
                        worksheet.set_row(row_num, 2, f_sep) 
                        for c in range(7): worksheet.write(row_num, c, "", f_sep)
                    else:
                        worksheet.set_row(row_num, 12) # Altura compacta

                # Encabezados
                for col_num, value in enumerate(df_to_excel.columns.values):
                    worksheet.write(0, col_num, value, f_head)

            st.session_state.excel_final = buf.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.paso = 'configuracion'

    if st.session_state.paso == 'listo':
        st.success("✅ Libro Diario generado en formato horizontal (Max-Space).")
        st.download_button(
            label="📥 Descargar Diario Apaisado",
            data=st.session_state.excel_final,
            file_name=f"Diario_Paisaje_{empresa.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        if st.button("🏁 Cargar nuevo"):
            st.session_state.clear()
            st.rerun()
