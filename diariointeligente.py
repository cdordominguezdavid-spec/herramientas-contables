import streamlit as st
import pandas as pd
import io
import re

# Configuración de página
st.set_page_config(page_title="Motor Contable Pro - Ultra Compacto", layout="wide")

st.title("⚖️ Libro Diario: Optimizador de Espacio Inteligente")

# --- FUNCIONES DE APOYO ---
def validar_periodo(texto):
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    match = re.match(patron, texto)
    if not match:
        return False, "Formato incorrecto. Debe ser: dd/mm/aaaa - dd/mm/aaaa"
    return True, ""

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'
if 'excel_final' not in st.session_state:
    st.session_state.excel_final = None

# --- INTERFAZ DE USUARIO ---
archivo = st.file_uploader("1. Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Empresa:", placeholder="Ej: Mi Empresa S.A.")
    with col2:
        periodo = st.text_input("Período (dd/mm/aaaa - dd/mm/aaaa):", placeholder="01/01/2026 - 31/01/2026")
    
    periodo_ok = False
    if periodo:
        es_valido, error_msg = validar_periodo(periodo)
        if es_valido:
            periodo_ok = True
        else:
            st.error(error_msg)

    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Optimizar y Generar", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        try:
            df = pd.read_excel(archivo)
            df = df.dropna(how='all')
            
            # Mapeo de columnas
            c_fecha, c_cta, c_desc_cta, c_comp, c_conc, c_debe_orig, c_haber_orig = \
                "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
            df = df.dropna(subset=[c_fecha])
            
            # Compactar leyenda: eliminamos espacios extra
            df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc]) if pd.notna(r[c_conc]) else ''} {str(r[c_comp]) if pd.notna(r[c_comp]) else ''}".strip()[:60], axis=1)
            
            for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                df[nombre_nuevo] = pd.to_numeric(df[col_orig].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            # Agrupación por asientos
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
                    'Leyenda/Detalle': [sub_df.iloc[0]['Leyenda_Full']] + [""] * (n_filas - 1),
                    'Cta': sub_df[c_cta].astype(str).values,
                    'Descripción': sub_df[c_desc_cta].str.slice(0,30).values, # Truncar descripción para ahorrar ancho
                    'Debe': sub_df['Debe'].values,
                    'Haber': sub_df['Haber'].values
                })
                lista_final.append(df_bloque)
                # Fila separadora ultra-delgada
                lista_final.append(pd.DataFrame([["SEP"] * 7], columns=df_bloque.columns))

            df_to_excel = pd.concat(lista_final, ignore_index=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Diario")
                workbook = writer.book
                worksheet = writer.sheets['Diario']
                
                # --- FORMATOS DE MICRO-IMPRESIÓN ---
                # Fuente 8 es el límite legal/legible ideal para libros copiativos
                f_base = {'font_name': 'Arial Narrow', 'font_size': 8, 'valign': 'vcenter'}
                f_num = workbook.add_format({**f_base, 'num_format': '#,##0.00;[Red]-#,##0.00;""'})
                f_txt = workbook.add_format({**f_base, 'text_wrap': True})
                f_head = workbook.add_format({'bold': True, 'font_size': 8, 'bg_color': '#EEEEEE', 'border': 1, 'align': 'center'})
                f_sep = workbook.add_format({'bg_color': '#000000', 'bottom': 1})

                # Configuración de página agresiva (A4)
                worksheet.set_paper(9) 
                worksheet.set_margins(left=0.15, right=0.15, top=0.3, bottom=0.3)
                worksheet.fit_to_pages(1, 0) # Forzar ancho a 1 página

                # Encabezado compacto
                worksheet.set_header(f"&L&7{empresa} | {periodo}&R&7DIARIO GENERAL - Pág &P")

                # --- LÓGICA INTELIGENTE DE COLUMNAS ---
                # Asignamos anchos mínimos para maximizar el espacio de las descripciones
                worksheet.set_column(0, 0, 7, f_txt)  # Fecha corta
                worksheet.set_column(1, 1, 3, f_txt)  # Nº asiento
                worksheet.set_column(2, 2, 25, f_txt) # Leyenda
                worksheet.set_column(3, 3, 8, f_txt)  # Cuenta
                worksheet.set_column(4, 4, 25, f_txt) # Descripción cuenta
                worksheet.set_column(5, 6, 10, f_num) # Importes

                # Aplicar formatos y separadores
                for row_num, row_data in enumerate(df_to_excel.values, 1):
                    if "SEP" in row_data:
                        worksheet.set_row(row_num, 1, f_sep) # Línea de separación casi invisible
                        for c in range(7): worksheet.write(row_num, c, "", f_sep)
                    else:
                        worksheet.set_row(row_num, 11) # Altura de fila reducida (standard es 15)

                # Forzar encabezados
                for col_num, value in enumerate(df_to_excel.columns.values):
                    worksheet.write(0, col_num, value, f_head)

            st.session_state.excel_final = buf.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.paso = 'configuracion'

    if st.session_state.paso == 'listo':
        st.success("✅ Optimización completada: Formato de alta densidad generado.")
        st.download_button(
            label="📥 Descargar Libro Diario Optimizado",
            data=st.session_state.excel_final,
            file_name=f"Diario_Optimizado_{empresa.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        if st.button("🏁 Volver a empezar"):
            st.session_state.clear()
            st.rerun()
