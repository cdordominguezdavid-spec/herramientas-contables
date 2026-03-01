import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Motor Contable Pro", layout="wide")

st.title("⚖️ Libro Diario: Formato Profesional")
st.markdown("Estado: **Forzando visibilidad de Descripción de Cuenta.**")

archivo = st.file_uploader("Sube tu Libro Mayor (Excel)", type=["xlsx", "xls"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = df.dropna(how='all')
        
        cols = df.columns.tolist()
        
        # Mapeo ultra-flexible para encontrar los nombres de las cuentas
        mapeo = {
            'fecha': ['Fecha', 'Fec.', 'Fecha_Asiento', 'Date', 'FECHA', 'F. Contable', 'Fecha Contable'],
            'asiento': ['Asiento', 'Num_Asiento', 'Poliza', 'Nro', 'ASIENTO', 'Asiento Nro', 'Número', 'Comprobante'],
            'cuenta': ['Cuenta', 'Código', 'Cod_Cuenta', 'Cta', 'CUENTA', 'Cod. Cuenta', 'Codigo'],
            'desc_cuenta': ['Nombre Cuenta', 'Descripción Cuenta', 'Nombre_Cuenta', 'DESCRIPCION CUENTA', 'Cuenta Nombre', 'Nombre de la Cuenta', 'Descripcion Cuenta', 'DESCRIPCION'],
            'comprobante': ['Comprobante', 'Nro Comprobante', 'Comp.', 'Voucher', 'Nro. Comp.'],
            'concepto': ['Concepto de pase', 'Descripcion', 'Detalle', 'Concepto', 'Glosa', 'Concepto Pase'],
            'debe': ['Débitos', 'Debe', 'Débito', 'Cargo', 'DEBE', 'Debito'],
            'haber': ['Créditos', 'Haber', 'Crédito', 'Abono', 'HABER', 'Credito']
        }
        
        def detectar(lista, reales):
            for s in lista:
                if s in reales: return s
            return None

        # Identificación de columnas reales
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

            # 2. Leyenda Fusionada (Concepto + Comprobante)
            def armar_leyenda(row):
                base = str(row[c_conc]) if c_conc and pd.notna(row[c_conc]) else ""
                extra = str(row[c_comp]) if c_comp and pd.notna(row[c_comp]) else ""
                return f"{base} {extra}".strip()

            df_ordenado['Leyenda'] = df_ordenado.apply(armar_leyenda, axis=1)

            # 3. Formato Numérico
            for col_orig, nombre_final in zip([c_debe, c_haber], ['Debe', 'Haber']):
                if col_orig:
                    df_ordenado[nombre_final] = df_ordenado[col_orig].astype(str).str.replace(',', '.')
                    df_ordenado[nombre_final] = pd.to_numeric(df_ordenado[nombre_final], errors='coerce').fillna(0)
                else:
                    df_ordenado[nombre_final] = 0.0

            # 4. Asegurar Nombres de Cuenta (Si no se detectó, usamos un Plan B)
            nombre_col_desc = c_desc_cta if c_desc_cta else "Descripción Cuenta"
            if not c_desc_cta:
                # Si no encontramos la columna, intentamos buscar alguna que tenga texto y no sea de las ya usadas
                posibles = [c for c in cols if c not in [c_fecha, c_asiento, c_debe, c_haber, c_cta, c_comp, c_conc]]
                if posibles:
                    nombre_col_desc = posibles[0] # Tomamos la primera columna de texto disponible
            
            # 5. Seleccionamos columnas finales
            final_cta_code = c_cta if c_cta else "Código"
            if not c_cta: df_ordenado[final_cta_code] = ""

            columnas_finales = [c_fecha, final_cta_code, nombre_col_desc, 'Leyenda', 'Debe', 'Haber']
            df_final = df_ordenado[columnas_finales].copy()
            
            # Renombramos para que el Excel salga con el nombre correcto
            df_final = df_final.rename(columns={nombre_col_desc: 'Descripción Cuenta'})

            # 6. Limpieza Estética (SOLO Fecha y Leyenda)
            df_final[c_fecha] = df_final[c_fecha].dt.strftime('%d/%m/%Y')
            duplicados = df_ordenado[c_asiento].duplicated()
            
            # IMPORTANTE: Aquí NO incluimos 'Descripción Cuenta' para que no salga en blanco
            df_final.loc[duplicados, [c_fecha, 'Leyenda']] = ""

            # 7. Construcción de filas con separador negro
            lista_export = []
            asientos_unicos = df_ordenado[c_asiento].unique()
            fila_separadora = pd.DataFrame([["MARK_BLACK"] * len(df_final.columns)], columns=df_final.columns)

            for asiento in asientos_unicos:
