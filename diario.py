import streamlit as st
import pandas as pd
import io
import re
import time

# Configuración de página
st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato de Impresión Oficial")

# --- FUNCIONES DE APOYO ---
def validar_periodo(texto):
    """Valida el formato dd/mm/aaaa - dd/mm/aaaa y los rangos numéricos"""
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    match = re.match(patron, texto)
    
    if not match:
        return False, "Formato incorrecto. Debe ser: dd/mm/aaaa - dd/mm/aaaa"
    
    vals = match.groups()
    # Validar rangos: Día (1-31), Mes (1-12), Año (1900-2050)
    try:
        d1, m1, a1 = int(vals[0]), int(vals[1]), int(vals[2])
        d2, m2, a2 = int(vals[3]), int(vals[4]), int(vals[5])
        
        for d in [d1, d2]:
            if not (1 <= d <= 31): return False, f"Día {d} fuera de rango (1-31)"
        for m in [m1, m2]:
            if not (1 <= m <= 12): return False, f"Mes {m} fuera de rango (1-12)"
        for a in [a1, a2]:
            if not (1900 <= a <= 2050): return False, f"Año {a} fuera de rango (1900-2050)"
            
        return True, ""
    except ValueError:
        return False, "Los valores ingresados no son números válidos."

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion' # configuracion | procesando | listo
if 'excel_final' not in st.session_state:
    st.session_state.excel_final = None

# --- INTERFAZ DE USUARIO ---
archivo = st.file_uploader("1. Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    st.subheader("2. Configuración de Reporte")
    
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Nombre de la Empresa:", 
                               placeholder="Ej: Mi Empresa S.A.", 
                               disabled=(st.session_state.paso != 'configuracion'))
    with col2:
        periodo = st.text_input("Período del Reporte (dd/mm/aaaa - dd/mm/aaaa):", 
                               placeholder="01/01/2026 - 31/01/2026",
                               disabled=(st.session_state.paso != 'configuracion'))
    
    # Validación de datos
    periodo_ok = False
    if periodo:
        es_valido, error_msg = validar_periodo(periodo)
        if not es_valido:
            st.error(f"⚠️ {error_msg}")
        else:
            st.success("✅ Formato de período correcto")
            periodo_ok = True

    # --- LÓGICA DEL BOTÓN LANZAR ---
    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Lanzar Generación", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        st.button("⏳ Procesando... Espere por favor", disabled=True)
        
        try:
            # Lectura del archivo
            df = pd.read_excel(archivo)
            df = df.dropna(how='all')
            
            # Definición de columnas origen (Ajustar si cambian en el Excel)
            c_fecha, c_cta, c_desc_cta, c_comp, c_conc, c_debe_orig, c_haber_orig = \
                "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            # Limpieza y preparación
            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
            df = df.dropna(subset=[c_fecha])
            
            df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc]) if pd.notna(r[c_conc]) else ''} {str(r[c_comp]) if pd.notna(r[c_comp]) else ''}".strip(), axis=1)
            
            for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                df[nombre_nuevo] = pd.to_numeric(df[col_orig].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            # Agrupación por bloques (Asientos)
            df['Fecha_Aux'] = df[c_fecha].dt.strftime('%d/%m/%Y')
            df['Bloque'] = (df['Fecha_Aux'] + df['Leyenda_Full']).ne((df['Fecha_Aux'] + df['Leyenda_Full']).shift()).cumsum()
            
            lista_final = []
            asientos_indices = []
            bloques = df['Bloque'].unique()
            total_b = len(bloques)
            current_row = 1 
            
            # Barra de progreso visual
            progreso_bar = st.progress(0)
            status_text = st.empty()

            for i, b in enumerate(bloques, 1):
                progreso_bar.progress(i/total_b)
                status_text.text(f"Estructurando asiento {i} de {total_b}...")
                
                sub_df = df[df['Bloque'] == b].copy()
                n_filas = len(sub_df)
                
                df_bloque = pd.DataFrame({
                    'Fecha': [sub_df.iloc[0][c_fecha].strftime('%d/%m/%Y')] + [""] * (n_filas - 1),
                    'NRO.': [f"{i:03d}"] + [""] * (n_filas - 1),
                    'Leyenda': [sub_df.iloc[0]['Leyenda_Full']] + [""] * (n_filas - 1),
                    'Cuenta': sub_df[c_cta].values,
                    'Descripción Cuenta': sub_df[c_desc_cta].values,
                    'Debe': sub_df['Debe'].values,
                    'Haber': sub_df['Haber'].values
                })
                
                asientos_indices.append({'start': current_row, 'end': current_row + n_filas - 1, 'len': n_filas})
                lista_final.append(df_bloque)
                lista_final.append(pd.DataFrame([["MARK"] * 7], columns=df_bloque.columns))
                current_row += n_filas + 1

            df_to_excel = pd.concat(lista_final, ignore_index=True)

            # --- GENERACIÓN DEL EXCEL CON XLSXWRITER ---
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Libro Diario")
                workbook, worksheet = writer.book, writer.sheets['Libro Diario']
                
                # Formatos
                f_miles = workbook.add_format({'num_format': '#,##0.00;;', 'font_name': 'Arial', 'font_size': 9, 'valign': 'top'})
                f_text = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'text_wrap': True})
                f_merge = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'left', 'text_wrap': True})
                f_negro = workbook.add_format({'bg_color': '#000000'})
                f_head = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'font_size': 9})

                # Configuración de página A4 con márgenes de 1cm (0.4 pulgadas)
                worksheet.set_paper(9) 
                worksheet.set_margins(left=0.2, right=0.2, top=0.4, bottom=0.4)
                worksheet.fit_to_pages(1, 0) # 1 pág de ancho
                
                # Definir área de impresión y títulos repetidos
                worksheet.print_area(0, 0, len(df_to_excel), 6)
                worksheet.repeat_rows(0)

                # Encabezado Concatenado y Pie de página
                worksheet.set_header(f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL", {'margin': 0.2})
                worksheet.set_footer("&RPágina &P de &N", {'margin': 0.2})

                # Anchos de columna
                worksheet.set_column(0, 0, 10, f_text)  # Fecha
                worksheet.set_column(1, 1, 5, f_text)   # NRO.
                worksheet.set_column(2, 2, 35, f_text)  # Leyenda
                worksheet.set_column(3, 3, 7, f_text)   # Cuenta
                worksheet.set_column(4, 4, 35, f_text)  # Descripción
                worksheet.set_column(5, 6, 13, f_miles) # Debe / Haber

                # Aplicación de combinados y líneas de 2pts
                for idx in asientos_indices:
                    if idx['len'] >= 2:
                        t_leyenda = df_to_excel.iloc[idx['start']-1]['Leyenda']
                        worksheet.merge_range(idx['start'], 2, idx['start'] + 1, 2, t_leyenda, f_merge)
                    
                    row_negra = idx['end'] + 1
                    worksheet.set_row(row_negra, 1.5, f_negro) # Altura mínima para línea
                    for c in range(7): worksheet.write(row_negra, c, "", f_negro)
                
                # Forzar escritura de encabezados con formato
                for col_num, value in enumerate(df_to_excel.columns.values):
                    worksheet.write(0, col_num, value, f_head)

            st.session_state.excel_final = buf.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Ocurrió un error inesperado: {e}")
            st.session_state.paso = 'configuracion'

    # --- RESULTADO FINAL ---
    if st.session_state.paso == 'listo':
        st.success("✅ ¡Libro Diario generado correctamente!")
        st.download_button(
            label="📥 Descargar Libro Diario Final",
            data=st.session_state.excel_final,
            file_name=f"Diario_{empresa.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.markdown("---")
        if st.button("🏁 Finalizar y Cargar Otro"):
            st.session_state.clear()
            st.rerun()
