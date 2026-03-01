import pandas as pd
from tkinter import filedialog, Tk
import os

def seleccionar_y_convertir():
    # 1. Crear una ventana oculta para que no moleste
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True) # Pone la ventana al frente

    print("📂 Selecciona tu archivo de Libro Mayor...")
    
    # 2. Abrir el explorador de archivos de Mac
    ruta_archivo = filedialog.askopenfilename(
        title="Selecciona el Libro Mayor (Excel)",
        filetypes=[("Archivos de Excel", "*.xlsx *.xls")]
    )

    if not ruta_archivo:
        print("❌ No seleccionaste ningún archivo.")
        return

    try:
        # 3. Leer el archivo seleccionado
        df = pd.read_excel(ruta_archivo)
        print(f"✅ Archivo '{os.path.basename(ruta_archivo)}' cargado.")

        # --- AQUÍ LA MAGIA DEL DIARIO ---
        # Reordenamos por Fecha y luego por Asiento (asumiendo que esos nombres existen)
        # Si tus columnas se llaman distinto, cámbialas aquí abajo:
        columnas_orden = ['Fecha', 'Asiento'] 
        
        # Verificamos si las columnas existen antes de ordenar
        columnas_reales = [c for c in columnas_orden if c in df.columns]
        df_diario = df.sort_values(by=columnas_reales)

        # 4. Guardar el resultado en la misma carpeta
        carpeta = os.path.dirname(ruta_archivo)
        nombre_salida = os.path.join(carpeta, "Libro_Diario_Generado.xlsx")
        
        df_diario.to_excel(nombre_salida, index=False)
        
        print(f"🚀 ¡Éxito! El Libro Diario se guardó en:\n{nombre_salida}")

    except Exception as e:
        print(f"⚠️ Error al procesar: {e}")

if __name__ == "__main__":
    seleccionar_y_convertir()
