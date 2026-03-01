import streamlit as st
import pandas as pd
import io
import time

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato de Impresión A4")

# Inicializar estado para controlar el flujo
if 'procesado' not in st.session_state:
    st.session_state.procesado = False
if 'excel_data' not in st.session_state:
    st.session_state.excel_data = None

archivo = st.file_uploader("1. Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    st.subheader("2. Datos de Cabecera")
    
    col_inp1, col_inp2 = st.columns(2)
    with col_inp1:
        # Si ya se procesó, deshabilitamos los inputs para evitar cambios sin regenerar
        empresa = st.text_input("Nombre de la Empresa:", placeholder="Ej: Mi Empresa S.A.", disabled=st.session_state.procesado)
    with col_inp2:
        periodo = st.text_input("Período del Reporte:", placeholder="Ej: Marzo 2026", disabled=st.session_state.procesado)

    # Lógica del botón generador
    if not st.session_state.procesado:
        if st.button("🚀 Generar Excel con Área de Impresión"):
            if empresa and periodo:
                try:
                    # Lectura inicial
                    df = pd.read_excel(archivo)
                    df = df.dropna(how='all')
                    
                    c_fecha, c_cta, c_desc_cta, c_comp, c_conc, c_debe_orig, c_haber_orig = \
                        "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

                    if c_fecha in df.columns:
                        # 1. Procesamiento de Datos
                        df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
                        df = df.dropna(subset=[c_fecha])
                        
                        df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc]) if pd.notna(r[c_conc]) else ''} {str(r[c_comp]) if pd.notna(r[c_comp]) else ''}".strip(), axis=1)

                        for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                            df[nombre_nuevo] = pd.to_numeric(df[col_orig].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

                        df['Fecha_Aux'] = df[c_fecha].dt.strftime('%d/%m/%Y')
                        df['Bloque'] = (df['Fecha_Aux'] + df['Leyenda_Full']).ne((df['Fecha_Aux'] + df['Leyenda_Full']).shift()).cumsum()
                        
                        # 2. Construcción con BARRA DE PROGRESO
                        lista_final = []
                        asientos_indices = []
                        bloques = df['Bloque'].unique()
                        total_bloques = len(bloques)
                        current_row = 1 

                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        for i, b in enumerate(bloques, 1):
                            porcentaje = int((i / total_bloques) * 100)
                            progress_bar.progress(porcentaje)
                            status_text.text(f"Procesando asiento {i} de {total_bloques}...")

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

                        # 3. Generación del Excel con XlsxWriter
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                            df_to_excel.to_excel(writer, index=False, sheet_name="Libro Diario")
                            workbook  = writer.book
                            worksheet = writer.sheets['Libro Diario']
                            
                            f_miles = workbook.add_format({'num_format': '#,##0.00;;', 'font_name': 'Arial', 'font_size': 9, 'valign': 'top'})
                            f_text  = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'text_wrap': True})
                            f_merge = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'left', 'text_wrap': True})
                            f_negro = workbook.add_format({'bg_color': '#000000'})
                            f_head  = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'font_size': 9})

                            # --- CONFIGURACIÓN DE IMPRESIÓN MEJORADA ---
                            worksheet.set_paper(9) # A4
                            
                            # AJUSTE DE MÁRGENES A 1 CM (0.4 pulgadas)
                            m_seguridad = 0.4
                            worksheet.set_margins(left=0.2, right=0.2, top=m_seguridad, bottom=m_seguridad)
                            
                            worksheet.center_horizontally()
                            worksheet.fit_to_pages(1, 0) # 1 de ancho, automático de alto
                            
                            last_row = len(df_to_excel)
                            worksheet.print_area(0, 0, last_row, 6)
                            worksheet.repeat_rows(0)

                            # Encabezado Concatenado
                            header_string = f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL"
                            worksheet.set_header(header_string, {'margin': 0.2}) # Espacio para el header
                            worksheet.set_footer("&RPágina &P de &N", {'margin': 0.2})

                            # Anchos de columna
                            worksheet.set_column(0, 0, 10, f_text)
                            worksheet.set_column(1, 1, 5, f_text)
                            worksheet.set_column(2, 2, 35, f_text)
                            worksheet.set_column(3, 3, 7, f_text)
                            worksheet.set_column(4, 4, 35, f_text)
                            worksheet.set_column(5, 6, 13, f_miles)

                            # Aplicar Merges y Líneas
                            for idx in asientos_indices:
                                if idx['len'] >= 2:
                                    t_leyenda = df_to_excel.iloc[idx['start']-1]['Leyenda']
                                    worksheet.merge_range(idx['start'], 2, idx['start'] + 1, 2, t_leyenda, f_merge)
                                
                                row_negra = idx['end'] + 1
                                worksheet.set_row(row_negra, 1.5, f_negro)
                                for c in range(7): worksheet.write(row_negra, c, "", f_negro)

                            for col_num, value in enumerate(df_to_excel.columns.values):
                                worksheet.write(0, col_num, value, f_head)

                        st.session_state.excel_data = buf.getvalue()
                        st.session_state.procesado = True
                        st.rerun()

                except Exception as e:
                    st.error(f"Error técnico: {e}")
            else:
                st.warning("⚠️ Completa los datos de cabecera.")
    else:
        # Si ya se procesó, mostramos estado gris y opciones finales
        st.button("⌛ Archivo Generado", disabled=True)
        
        st.success("✅ ¡Libro Diario procesado con márgenes de 1 cm!")
        st.download_button(
            label="📥 Descargar Libro Diario Final",
            data=st.session_state.excel_data,
            file_name=f"Diario_{empresa.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.markdown("---")
        if st.button("🏁 Finalizar y Cargar Otro Archivo"):
            st.session_state.procesado = False
            st.session_state.excel_data = None
            st.rerun()
