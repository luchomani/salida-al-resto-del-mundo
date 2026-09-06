import pandas as pd
import pdfplumber
import re
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Procesador de Documentos Aduaneros", page_icon="📦", layout="wide"
)

st.title("📦 Automatización y Extracción de Documentos Aduaneros")
st.write(
    "Sube tus archivos PDF (Manifiestos de Carga, MCI, declaraciones, etc.)"
    " para extraer los datos clave automáticamente."
)


def extraer_datos_pdf(pdf_file):
  """Función robusta para extraer datos de manifiestos y documentos aduaneros."""
  datos = {
      "Archivo": pdf_file.name,
      "Nro_Manifiesto": "No detectado",
      "Placa_Vehiculo": "No detectado",
      "Conductor": "No detectado",
      "Documento_Identidad": "No detectado",
      "Estado": "Fallida",
  }

  try:
    with pdfplumber.open(pdf_file) as pdf:
      texto_completo = ""
      for pagina in pdf.pages:
        texto_extraido = pagina.extract_text()
        if texto_extraido:
          texto_completo += texto_extraido + "\n"

    # Si el PDF es una imagen escaneada sin texto seleccionable, avisa
    if not texto_completo.strip():
      datos["Estado"] = "Fallida (PDF sin texto digital/escaneado)"
      return datos

    # 1. Extracción del Número de Manifiesto / MCI (Patrones flexibles)
    match_mci = re.search(
        r"(?:NATIS|MANIFIESTO|MCI|N[°º])[^\d]*([\d\-]{4,15})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_mci:
      datos["Nro_Manifiesto"] = match_mci.group(1).strip()

    # 2. Extracción de Placa (Busca patrones alfanuméricos de placas comunes)
    match_placa = re.search(
        r"(?:Placa y Pais|Placa|Veh[ií]culo)[^\w]*([A-Z0-9\-]{5,8})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_placa:
      datos["Placa_Vehiculo"] = match_placa.group(1).strip()

    # 3. Extracción de Conductor
    match_cond = re.search(
        r"(?:CONDUCTOR PRINCIPAL|Conductor)[^\w]*(?:Nombre:)?\s*([A-ZÁÉÍÓÚÑ\s]{5,40})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_cond:
      datos["Conductor"] = match_cond.group(1).strip()

    # 4. Extracción de Documento de Identidad del Conductor
    match_doc = re.search(
        r"(?:Documento de Identidad|C[eé]dula|Identidad)[^\d]*(\d{6,12})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_doc:
      datos["Documento_Identidad"] = match_doc.group(1).strip()

    # Validación de éxito: Se marca como exitosa si detecta al menos el manifiesto o la placa
    if (
        datos["Nro_Manifiesto"] != "No detectado"
        or datos["Placa_Vehiculo"] != "No detectado"
    ):
      datos["Estado"] = "Exitosa"

  except Exception as e:
    datos["Estado"] = f"Error de lectura: {str(e)}"

  return datos


# --- Interfaz Principal de Streamlit ---
uploaded_files = st.file_uploader(
    "Sube tus archivos PDF de transporte o aduanas",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files:
  if st.button("🚀 Procesar Lote de Documentos", type="primary"):
    resultados = []
    exitosas = 0
    fallidas = 0

    barra_progreso = st.progress(0)
    total_archivos = len(uploaded_files)

    for i, archivo in enumerate(uploaded_files):
      resultado = extraer_datos_pdf(archivo)
      resultados.append(resultado)

      if "Exitosa" in resultado["Estado"]:
        exitosas += 1
      else:
        fallidas += 1

      barra_progreso.progress((i + 1) / total_archivos)

    # Mostrar Métricas en pantalla
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("📁 Total Procesados", total_archivos)
    col2.metric("✅ Exitosas", exitosas)
    col3.metric("❌ Fallidas / No detectadas", fallidas)

    # Convertir resultados a DataFrame para visualización
    df_resultados = pd.DataFrame(resultados)

    st.subheader("📊 Detalle de Extracción")
    st.dataframe(df_resultados, use_container_width=True)

    # Botón para descargar los resultados consolidados
    csv = df_resultados.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Reporte en CSV",
        data=csv,
        file_name="reporte_extraccion_aduanas.csv",
        mime="text/csv",
    )
else:
  st.info(
      "Esperando archivos... Por favor, selecciona y carga tus documentos PDF"
      " para iniciar."
  )
