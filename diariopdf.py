import streamlit as st
import pandas as pd
import io
import re
from fpdf import FPDF

st.set_page_config(page_title="Sistema Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Generación Dual (Excel + PDF)")

# --- ESTADOS DE SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.paso = 'configuracion'
if 'excel_final' not in st.session_state:
    st.session_state.excel_final = None
if 'pdf_final' not in st.session_state:
    st.session_state.pdf_final = None

# --- VALIDACIÓN ---
def validar_periodo(texto):
    patron = r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})$"
    match = re.match(patron, texto)
    if not match: return False, "Formato: dd/mm/aaaa - dd/mm/aaaa"
    v = match.groups()
    try:
        if not (1 <= int(v[0]) <= 31) or not (1 <= int(v[3]) <= 31): return False, "Día inválido"
        if not (1 <= int(v[1]) <= 12) or not (1 <= int(v[4]) <= 12): return False, "Mes inválido"
        if not (1900 <= int(v[2]) <= 2050) or not (1900 <= int(v[5]) <= 2050): return False, "Año fuera de rango"
        return True, ""
    except: return False, "Error numérico"

# --- CLASE PDF PERSONALIZADA ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 8)
        self.cell(0, 5, f"{st.session_state.empresa_pdf} - {st.session_state.periodo_pdf}", 0, 0, 'L')
        self.cell(0, 5, "DIARIO GENERAL", 0, 1, 'R')
        self.ln(2)
        # Encabezados de tabla
        self.set_fill_color(217, 217, 217)
        cols = [("Fecha", 18), ("Nro", 10), ("Leyenda", 55), ("Cta", 15), ("Descripción", 55), ("Debe", 21), ("Haber", 21)]
        for txt, w in cols:
            self.cell(w, 5, txt, 1, 0, 'C', True)
        self.ln()

archivo = st.file_uploader("Sube tu Libro Mayor", type=["xlsx", "xls"])

if archivo:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Nombre de la Empresa:", disabled=(st.session_state.paso != 'configuracion'))
    with col2:
        periodo = st.text_input("Período (dd/mm/aaaa - dd/mm/aaaa):", placeholder="01/01/2026 - 31/01/2026", disabled=(st.session_state.paso != 'configuracion'))
    
    periodo_ok = False
    if periodo:
        es_valido, msg = validar_periodo(periodo)
        if not es_valido: st.error(msg)
        else: periodo_ok = True

    if st.session_state.paso == 'configuracion':
        if st.button("🚀 Lanzar Generación (Excel + PDF)", disabled=not (empresa and periodo_ok)):
            st.session_state.empresa_pdf = empresa
            st.session_state.periodo_pdf = periodo
            st.session_state.paso = 'procesando'
            st.rerun()

    elif st.session_state.paso == 'procesando':
        st.button("⏳ Procesando Archivos...", disabled=True)
        
        try:
            df = pd.read_excel(archivo)
            c_fec, c_cta, c_des, c_com, c_con, c_deb, c_cre = "Fecha", "Cuenta", "Descripción cuenta", "Comprobante", "Concepto pase", "Débitos", "Créditos"
            df[c_fec] = pd.to_datetime(df[c_fec], errors='coerce').ffill()
            df = df.dropna(subset=[c_fec])
            df['Ley_F'] = df.apply(lambda r: f"{str(r[c_con]) if pd.notna(r[c_con]) else ''} {str(r[c_com]) if pd.notna(r[c_com]) else ''}".strip(), axis=1)
            for c in [c_deb, c_cre]: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df['ID'] = (df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).ne((df[c_fec].dt.strftime('%Y%m%d') + df['Ley_F']).shift()).cumsum()
            
            # --- PREPARAR DATOS ---
            bloques = df['ID'].unique()
            lista_ex = []
            idx_ex = []
            curr_r = 1
            prog = st.progress(0)

            # PDF Setup
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.add_page()
            pdf.set_font("Arial", size=7)

            for i, b in enumerate(bloques, 1):
                prog.progress(i/len(bloques))
                sub = df[df['ID'] == b].copy()
                n = len(sub)
                
                # Datos para Excel
                df_b = pd.DataFrame({
                    'Fecha': [sub.iloc[0][c_fec].strftime('%d/%m/%y')] + [""]*(n-1),
                    'NRO.': [f"{i:03d}"] + [""]*(n-1),
                    'Leyenda': [sub.iloc[0]['Ley_F']] + [""]*(n-1),
                    'Cuenta': sub[c_cta].values, 'Descripción': sub[c_des].values,
                    'Debe': sub[c_deb].values, 'Haber': sub[c_cre].values
                })
                idx_ex.append({'start': curr_r, 'end': curr_r + n - 1, 'len': n})
                lista_ex.append(df_b)
                lista_ex.append(pd.DataFrame([["SEP"]*7], columns=df_b.columns))
                curr_r += n + 1

                # Datos para PDF
                for idx_sub, row in sub.iterrows():
                    pdf.set_fill_color(255, 255, 255)
                    f_txt = row[c_fec].strftime('%d/%m/%y') if idx_sub == sub.index[0] else ""
                    n_txt = f"{i:03d}" if idx_sub == sub.index[0] else ""
                    l_txt = row['Ley_F'][:40] if idx_sub == sub.index[0] else ""
                    d_txt = f"{row[c_deb]:,.2f}" if row[c_deb] > 0 else ""
                    h_txt = f"{row[c_cre]:,.2f}" if row[c_cre] > 0 else ""
                    
                    pdf.cell(18, 4, f_txt, 0, 0, 'L')
                    pdf.cell(10, 4, n_txt, 0, 0, 'C')
                    pdf.cell(55, 4, l_txt, 0, 0, 'L')
                    pdf.cell(15, 4, str(row[c_cta]), 0, 0, 'L')
                    pdf.cell(55, 4, str(row[c_des])[:40], 0, 0, 'L')
                    pdf.cell(21, 4, d_txt, 0, 0, 'R')
                    pdf.cell(21, 4, h_txt, 0, 1, 'R')
                
                # Línea separadora en PDF
                pdf.set_fill_color(0, 0, 0)
                pdf.cell(195, 0.2, "", 1, 1, 'C', True)

            # --- GENERAR EXCEL ---
            df_total = pd.concat(lista_ex, ignore_index=True)
            buf_ex = io.BytesIO()
            with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as writer:
                df_total.to_excel(writer, index=False, sheet_name="Diario")
                wb, ws = writer.book, writer.sheets['Diario']
                f_base = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top'})
                f_num = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'num_format': '#,##0.00;;', 'valign': 'top'})
                f_mrg = wb.add_format({'font_name': 'Arial', 'font_size': 7.5, 'valign': 'top', 'align': 'left'})
                f_sep = wb.add_format({'bg_color': '#000000'})
                
                ws.set_paper(9); ws.set_margins(0.3, 0.3, 0.4, 0.4); ws.fit_to_pages(1, 0)
                ws.set_header(f"&L&B{empresa} - {periodo}&R&BDIARIO GENERAL")
                ws.set_column(0,0,8,f_base); ws.set_column(1,1,4,f_base); ws.set_column(2,2,30,f_base)
                ws.set_column(3,3,7,f_base); ws.set_column(4,4,30,f_base); ws.set_column(5,6,11,f_num)

                for item in idx_ex:
                    if item['len'] >= 2:
                        s = item['start']
                        ws.merge_range(s, 0, s+1, 0, df_total.iloc[s-1]['Fecha'], f_mrg)
                        ws.merge_range(s, 1, s+1, 1, df_total.iloc[s-1]['NRO.'], f_mrg)
                        ws.merge_range(s, 2, s+1, 2, df_total.iloc[s-1]['Leyenda'], f_mrg)
                    ws.set_row(item['end']+1, 1.2, f_sep)

            st.session_state.excel_final = buf_ex.getvalue()
            st.session_state.pdf_final = pdf.output(dest='S').encode('latin-1')
            st.session_state.paso = 'listo'
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}"); st.session_state.paso = 'configuracion'

    if st.session_state.paso == 'listo':
        st.success("✅ ¡Archivos generados!")
        c_d1, c_d2 = st.columns(2)
        with c_d1: st.download_button("📥 Descargar Excel", st.session_state.excel_final, f"Diario_{empresa}.xlsx")
        with c_d2: st.download_button("📥 Descargar PDF", st.session_state.pdf_final, f"Diario_{empresa}.pdf")
        
        if st.button("🏁 Finalizar y Reiniciar"):
            st.session_state.clear(); st.rerun()
