import io
import re
import pandas as pd
import pdfplumber
from PIL import Image
import pytesseract
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Extractor Logístico - Manifiestos y Cartas de Porte",
    page_icon="🚛",
    layout="wide",
)

st.title("🚛 Extractor Automatizado de Documentos de Transporte")
st.markdown(
    "Sube tus **Manifiestos de Carga** o **Cartas de Porte** (en formato PDF"
    " o imágenes JPG/PNG). El sistema extraerá los datos clave de forma"
    " unificada."
)

# Componente para carga múltiple de archivos
uploaded_files = st.file_uploader(
    "Selecciona o arrastra tus archivos aquí",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
)


def extraer_texto_inteligente(uploaded_file):
  """Extrae texto de un PDF (nativo o escaneado) o de una imagen usando OCR."""
  texto = ""
  nombre_archivo = uploaded_file.name
  extension = nombre_archivo.split(".")[-1].lower()

  try:
    if extension == "pdf":
      # Intento 1: Extraer texto digital directo con pdfplumber
      with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
          t_pagina = page.extract_text()
          if t_pagina:
            texto += t_pagina + "\n"

      # Intento 2: Si el PDF es un escaneo (texto muy corto), aplicar OCR convirtiendo a imágenes
      if len(texto.strip()) < 40:
        uploaded_file.seek(0)
        from pdf2image import convert_from_bytes

        imagenes = convert_from_bytes(uploaded_file.read())
        for img in imagenes:
          texto += pytesseract.image_to_string(img, lang="spa") + "\n"

    elif extension in ["png", "jpg", "jpeg"]:
      # Procesamiento directo para imágenes
      imagen = Image.open(uploaded_file)
      texto = pytesseract.image_to_string(imagen, lang="spa")

  except Exception as e:
    st.error(f"Error procesando {nombre_archivo}: {e}")

  return texto


def parsear_datos_manifiesto(texto, nombre_archivo):
  """Aplica expresiones regulares para capturar los campos logísticos clave

  independientemente del diseño del documento.
  """
  datos = {"Archivo": nombre_archivo}

  # Patrón para Número de Manifiesto / MCI / Carta de Porte
  m_manifiesto = re.search(
      r"(?:Manifiesto|MCI|Carta\s*de\s*Porte|CPIC|N[°º]\s*Manifesto)[:\s]*([A-Z0-9\-]+)",
      texto,
      re.IGNORECASE,
  )
  datos["Nro_Documento"] = (
      m_manifiesto.group(1).strip() if m_manifiesto else "No detectado"
  )

  # Patrón para Placa del Vehículo (Chuto)
  m_placa = re.search(
      r"(?:Placa|Veh[ií]culo|Chuto|Placa\s*Camion)[:\s]*([A-Z0-9\-]{5,8})",
      texto,
      re.IGNORECASE,
  )
  datos["Placa_Vehiculo"] = (
      m_placa.group(1).strip() if m_placa else "No detectada"
  )

  # Patrón para Remolque / Unidad de Carga
  m_remolque = re.search(
      r"(?:Remolque|Semirremolque|Batea|Unidad)[:\s]*([A-Z0-9\-]{5,8})",
      texto,
      re.IGNORECASE,
  )
  datos["Placa_Remolque"] = (
      m_remolque.group(1).strip() if m_remolque else "No detectado"
  )

  # Patrón para Conductor
  m_conductor = re.search(
      r"(?:Conductor|Chofer|Nombre\s*Conductor)[:\s]*([A-ZÁÉÍÓÚÑ\s]+)",
      texto,
      re.IGNORECASE,
  )
  datos["Conductor"] = (
      m_conductor.group(1).strip() if m_conductor else "No detectado"
  )

  # Patrón para Destinatario / Importador
  m_destinatario = re.search(
      r"(?:Destinatario|Consignatario)[:\s]*([A-ZÁÉÍÓÚÑ0-9\.\,\s]+)",
      texto,
      re.IGNORECASE,
  )
  datos["Destinatario"] = (
      m_destinatario.group(1).strip() if m_destinatario else "No detectado"
  )

  # Almacenar un fragmento del texto bruto para auditoría rápida
  datos["Texto_Extraido_Snippet"] = (
      texto.replace("\n", " ")[:150] + "..." if texto else "Vacío"
  )

  return datos


# Procesamiento cuando el usuario carga archivos
if uploaded_files:
  resultados = []

  with st.spinner(
      "Procesando documentos y aplicando IA/OCR de extracción..."
  ):
    for archivo in uploaded_files:
      texto_crudo = extraer_texto_inteligente(archivo)
      info_extraida = parsear_datos_manifiesto(texto_crudo, archivo.name)
      resultados.append(info_extraida)

  # Crear DataFrame consolidado
  df_resultado = pd.DataFrame(resultados)

  st.success(
      f"¡Proceso finalizado! Se analizaron {len(uploaded_files)} archivo(s)"
      " exitosamente."
  )

  # Mostrar tabla interactiva en Streamlit
  st.subheader("📋 Datos Consolidados Extraídos")
  st.dataframe(df_resultado, use_container_width=True)

  # Botón de descarga en Excel
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_resultado.to_excel(writer, index=False, sheet_name="Manifiestos_Extraidos")
  excel_data = output.getvalue()

  st.download_button(
      label="📥 Descargar Consolidado en Excel",
      data=excel_data,
      file_name="consolidado_manifiestos.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )
else:
  st.info(
      "👆 Sube tus documentos arriba para comenzar la extracción automática."
  )