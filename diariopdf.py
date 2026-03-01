import streamlit as st
import pandas as pd
import io
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

# Configuración de página Streamlit
st.set_page_config(page_title="Motor Contable Pro Ultra", layout="wide")

st.title("⚖️ Libro Diario: Impresión Optimizada (Ahorro de Papel)")

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'
if 'excel_final' not in st.session_state:
    st.session_state.excel_final = None
if 'df_impresion' not in st.session_state:
    st.session_state.df_impresion = None

# --- VALIDACIÓN DE PERÍODO ---
def validar_periodo(texto):
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    match = re.match(patron, texto)
    if not match: return False, "Formato: dd/mm/aaaa - dd/mm/aaaa"
    vals = match.groups()
    try:
        for i in [0, 3]: 
            if not (1 <= int(vals[i]) <= 31): return False, f"Día {vals[i]} inválido"
        for i in [1, 4]: 
            if not (1 <= int(vals[i]) <= 12): return False, f"Mes {vals[i]} inválido"
        for i in [2, 5]: 
            if not (1900 <= int(vals[i]) <= 2050): return False, "Año fuera de rango"
        return True, ""
    except: return False, "Error en números"

# --- INTERFAZ ---
archivo = st.file_uploader("1. Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Nombre de la Empresa:", disabled=(st.session_state.paso != 'configuracion'))
    with col2:
        periodo = st.text_input("Período (dd/mm/aaaa - dd/mm/aaaa):", placeholder="01/01/2026 - 31/12/2026", disabled=(st.session_state.paso != 'configuracion'))
    
    periodo_ok = False
    if periodo:
        es_valido, msg = validar_periodo(periodo)
        if not es_valido: st.error(msg)
        else: periodo_ok = True

    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Generar Libros (Excel y PDF)", disabled=not (empresa and periodo_ok)):
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        st.button("⏳ Procesando con ahorro de papel...", disabled=True)
        
        try:
            df = pd.read_excel(archivo)
            df = df.dropna(how='all')
            c_fecha, c_cta, c_desc_cta, c_comp, c_conc, c_debe_orig, c_haber_orig = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"

            df[c_fecha] = pd.to_datetime(df[c_fecha], errors='coerce').ffill()
            df = df.dropna(subset=[c_fecha])
            df['Leyenda_Full'] = df.apply(lambda r: f"{str(r[c_conc]) if pd.notna(r[c_conc]) else ''} {str(r[c_comp]) if pd.notna(r[c_comp]) else ''}".strip(), axis=1)
            
            for col_orig, nombre_nuevo in zip([c_debe_orig, c_haber_orig], ['Debe', 'Haber']):
                df[nombre_nuevo] = pd.to_numeric(df[col_orig].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

            df['Bloque'] = (df[c_fecha].dt.strftime('%d%m%Y') + df['Leyenda_Full']).ne((df[c_fecha].dt.strftime('%d%m%Y') + df['Leyenda_Full']).shift()).cumsum()
            
            lista_final = []
            bloques = df['Bloque'].unique()
            prog = st.progress(0)

            for i, b in enumerate(bloques, 1):
                prog.progress(i/len(bloques))
                sub = df[df['Bloque'] == b].copy()
                n = len(sub)
                df_b = pd.DataFrame({
                    'Fecha': [sub.iloc[0][c_fecha].strftime('%d/%m/%y')] + [""]*(n-1),
                    'NRO.': [f"{i:03d}"] + [""]*(n-1),
                    'Leyenda': [sub.iloc[0]['Leyenda_Full']] + [""]*(n-1),
                    'Cuenta': sub[c_cta].values,
                    'Descripción': sub[c_desc_cta].values,
                    'Debe': sub['Debe'].values,
                    'Haber': sub['Haber'].values
                })
                lista_final.append(df_b)
                lista_final.append(pd.DataFrame([["LINEA_NEGRA"]*7], columns=df_b.columns))

            df_to_excel = pd.concat(lista_final, ignore_index=True)
            st.session_state.df_impresion = df_to_excel

            # --- GENERACIÓN EXCEL ---
            buf_ex = io.BytesIO()
            with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as writer:
                df_to_excel.to_excel(writer, index=False, sheet_name="Diario")
                wb, ws = writer.book, writer.sheets['Diario']
                
                # Formato condensado (Fuente 7.5)
                fmt_base = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top', 'text_wrap': True})
                fmt_num = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'num_format': '#,##0.00;;', 'valign': 'top'})
                fmt_negro = wb.add_format({'bg_color': '#000000'})
                fmt_head = wb.add_format({'bold': True, 'bg_color': '#EFEFEF', 'border': 1, 'font_size': 8, 'align': 'center'})

                ws.set_paper(9) # A4
                ws.set_margins(0.3, 0.3, 0.4, 0.4) # Márgenes 1cm aprox
                ws.fit_to_pages(1, 0)
                ws.print_area(0, 0, len(df_to_excel), 6)
                ws.set_header(f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL")
                ws.set_footer("&RPágina &P de &N")

                # Anchos ultra-ajustados
                ws.set_column(0, 0, 8, fmt_base)   # Fecha
                ws.set_column(1, 1, 4, fmt_base)   # Nro
                ws.set_column(2, 2, 32, fmt_base)  # Leyenda
                ws.set_column(3, 3, 6, fmt_base)   # Cta
                ws.set_column(4, 4, 32, fmt_base)  # Desc
                ws.set_column(5, 6, 11, fmt_num)   # Debe/Haber

                for r_idx, row in df_to_excel.iterrows():
                    if row['Fecha'] == "LINEA_NEGRA":
                        ws.set_row(r_idx + 1, 1.2, fmt_negro)
                        for c in range(7): ws.write(r_idx+1, c, "", fmt_negro)
                
                for c_idx, val in enumerate(df_to_excel.columns):
                    ws.write(0, c_idx, val, fmt_head)

            st.session_state.excel_final = buf_ex.getvalue()
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.paso = 'configuracion'

    # --- RESULTADO FINAL ---
    if st.session_state.paso == 'listo':
        st.success("✅ Documentos generados con fuente 7.5pt (Ahorro máximo).")
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button("📥 Descargar Excel", st.session_state.excel_final, f"Diario_{empresa}.xlsx")
        
        with col_dl2:
            # --- GENERACIÓN PDF ---
            buf_pdf = io.BytesIO()
            doc = SimpleDocTemplate(buf_pdf, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=1.5*cm, bottomMargin=1*cm)
            elements = []
            styles = getSampleStyleSheet()
            
            # Encabezado PDF
            header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=9, leading=10, alignment=0)
            elements.append(Paragraph(f"<b>{empresa} - {periodo}</b>", header_style))
            elements.append(Paragraph("DIARIO GENERAL", ParagraphStyle('Sub', parent=header_style, alignment=2)))
            elements.append(Spacer(1, 0.2*cm))

            # Datos Tabla
            data_pdf = [df_to_excel.columns.tolist()]
            for _, r in st.session_state.df_impresion.iterrows():
                if r['Fecha'] == "LINEA_NEGRA":
                    data_pdf.append([""]*7)
                else:
                    # Formatear números para PDF
                    d = f"{r['Debe']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if r['Debe'] != 0 else ""
                    h = f"{r['Haber']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if r['Haber'] != 0 else ""
                    data_pdf.append([r['Fecha'], r['NRO.'], r['Leyenda'], r['Cuenta'], r['Descripción'], d, h])

            t = Table(data_pdf, colWidths=[1.8*cm, 1*cm, 5.5*cm, 1.4*cm, 5.5*cm, 2*cm, 2*cm], repeatRows=1)
            t.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 6.5), # PDF aún más pequeño para asegurar encuadre
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('ALIGN', (5,1), (6,-1), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('GRID', (0,0), (-1,0), 0.5, colors.black),
                # Líneas negras de separación
            ]))
            
            # Aplicar líneas negras en PDF
            for i, row in enumerate(data_pdf):
                if row[0] == "" and i > 0:
                    t.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.black), ('LINEBELOW', (0,i), (-1,i), 1, colors.black)]))

            elements.append(t)
            doc.build(elements)
            st.download_button("📥 Descargar PDF", buf_pdf.getvalue(), f"Diario_{empresa}.pdf", "application/pdf")

        st.markdown("---")
        if st.button("🏁 Finalizar y Reiniciar"):
            st.session_state.clear()
            st.rerun()
