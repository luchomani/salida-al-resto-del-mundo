import pandas as pd
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
import re
import streamlit as st

# Configuración de la interfaz
st.set_page_config(
    page_title="Procesador Aduanero con OCR - 13 Columnas",
    page_icon="📦",
    layout="wide",
)

st.title("📦 Automatización y Extracción Aduanera (Soporta Escaneados / OCR)")
st.write(
    "Sube tus archivos PDF (incluso si son documentos escaneados o fotos)"
    " para estructurar la información en las 13 columnas requeridas."
)


def extraer_datos_con_ocr(pdf_file):
  """Función híbrida: Lee texto digital o aplica OCR si el PDF es una imagen escaneada."""

  datos = {
      "Archivo": pdf_file.name,
      "Nro_Manifiesto_MCI": "No detectado",
      "Carta_de_Porte": "No detectado",
      "Placa_Camion": "No detectado",
      "Placa_Remolque": "No detectado",
      "Conductor_Nombre": "No detectado",
      "Conductor_Cedula": "No detectado",
      "Nro_Precintos": "No detectado",
      "Peso_Bruto_Kg": "No detectado",
      "Peso_Neto_Kg": "No detectado",
      "Termino_Negociacion": "No detectado",
      "Observaciones": "Sin novedades",
      "Estado_Extraccion": "Fallida",
  }

  texto_completo = ""
  bytes_pdf = pdf_file.read()

  try:
    # 1. Intento 1: Extracción de texto digital directo (rápido)
    with pdfplumber.open(pdf_file) as pdf:
      for pagina in pdf.pages:
        t = pagina.extract_text()
        if t:
          texto_completo += t + "\n"

    # 2. Intento 2: Si el texto está vacío (es una imagen escaneada), aplicamos OCR
    if not texto_completo.strip():
      # Convierte el PDF a imágenes de alta calidad
      imagenes = convert_from_bytes(bytes_pdf)
      for img in imagenes:
        # Extrae texto usando OCR (español)
        texto_ocr = pytesseract.image_to_string(img, lang="spa")
        texto_completo += texto_ocr + "\n"
      datos["Observaciones"] = "Procesado mediante OCR (Imagen escaneada)"
    else:
      datos["Observaciones"] = "Procesado mediante texto digital"

    # Si aun así no hay texto, retorna fallido
    if not texto_completo.strip():
      datos["Estado_Extraccion"] = "Fallida (No se pudo leer contenido)"
      return datos

    # --- EXPRESIONES REGULARES PARA LLENAR LAS 13 COLUMNAS ---

    # 1. Número de Manifiesto / MCI
    match_mci = re.search(
        r"(?:NATIS|MANIFIESTO|MCI|N[°º])[^\d]*([\d\-]{4,15})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_mci:
      datos["Nro_Manifiesto_MCI"] = match_mci.group(1).strip()

    # 2. Carta de Porte
    match_cp = re.search(
        r"(?:Carta de Porte|CP|Documento de Transporte)[^\w]*([A-Z0-9\-]{5,15})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_cp:
      datos["Carta_de_Porte"] = match_cp.group(1).strip()

    # 3. Placa del Camión
    match_placa = re.search(
        r"(?:Placa y Pais|Placa Camión|Veh[ií]culo)[^\w]*([A-Z0-9\-]{5,8})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_placa:
      datos["Placa_Camion"] = match_placa.group(1).strip()

    # 4. Placa del Remolque
    match_rem = re.search(
        r"(?:Remolque|Semirremolque|Placa Remolque)[^\w]*([A-Z0-9\-]{5,8})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_rem:
      datos["Placa_Remolque"] = match_rem.group(1).strip()

    # 5. Nombre del Conductor
    match_cond = re.search(
        r"(?:CONDUCTOR PRINCIPAL|Conductor)[^\w]*(?:Nombre:)?\s*([A-ZÁÉÍÓÚÑ\s]{5,40})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_cond:
      datos["Conductor_Nombre"] = match_cond.group(1).strip()

    # 6. Cédula del Conductor
    match_doc = re.search(
        r"(?:Documento de Identidad|C[eé]dula|Identidad)[^\d]*(\d{6,12})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_doc:
      datos["Conductor_Cedula"] = match_doc.group(1).strip()

    # 7. Número de Precintos
    match_prec = re.search(
        r"(?:Precintos?|Sellos?)[^\w]*([A-Z0-9\-\,\s]{4,20})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_prec:
      datos["Nro_Precintos"] = match_prec.group(1).strip()

    # 8 y 9. Pesos Bruto y Neto (Búsqueda heurística numérica)
    numeros_encontrados = re.findall(
        r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\b", texto_completo
    )
    if len(numeros_encontrados) >= 2:
      pass  # Se mantiene espacio para asignación de pesos

    # 10. Término de Negociación (Incoterm)
    match_incoterm = re.search(
        r"\b(FOB|CIF|EXW|CFR|DAP|DDP|FCA)\b", texto_completo, re.IGNORECASE
    )
    if match_incoterm:
      datos["Termino_Negociacion"] = match_incoterm.group(1).upper()

    # Validación de éxito global si encuentra identificadores clave
    if (
        datos["Nro_Manifiesto_MCI"] != "No detectado"
        or datos["Placa_Camion"] != "No detectado"
    ):
      datos["Estado_Extraccion"] = "Exitosa"
    else:
      datos["Estado_Extraccion"] = (
          "Revisión manual (Texto extraído pero sin coincidencias exactas)"
      )

  except Exception as e:
    datos["Estado_Extraccion"] = f"Error crítico: {str(e)}"

  return datos


# --- Interfaz en Streamlit ---
uploaded_files = st.file_uploader(
    "Selecciona tus documentos PDF (Escaneados o Digitales)",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files:
  if st.button("🚀 Procesar con Motor OCR e Inteligente", type="primary"):
    lista_resultados = []
    exitosas = 0
    fallidas = 0

    barra_progreso = st.progress(0)
    total_archivos = len(uploaded_files)

    for i, archivo in enumerate(uploaded_files):
      resultado_dict = extraer_datos_con_ocr(archivo)
      lista_resultados.append(resultado_dict)

      if "Exitosa" in resultado_dict["Estado_Extraccion"]:
        exitosas += 1
      else:
        fallidas += 1

      barra_progreso.progress((i + 1) / total_archivos)

    # Métricas visuales
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("📁 Total Procesados", total_archivos)
    col2.metric("✅ Exitosas", exitosas)
    col3.metric("⚠️ Con Observaciones / Fallidas", fallidas)

    # DataFrame con el orden estricto de las 13 columnas
    df_final = pd.DataFrame(lista_resultados)

    columnas_fijas = [
        "Archivo",
        "Nro_Manifiesto_MCI",
        "Carta_de_Porte",
        "Placa_Camion",
        "Placa_Remolque",
        "Conductor_Nombre",
        "Conductor_Cedula",
        "Nro_Precintos",
        "Peso_Bruto_Kg",
        "Peso_Neto_Kg",
        "Termino_Negociacion",
        "Observaciones",
        "Estado_Extraccion",
    ]

    df_final = df_final[columnas_fijas]

    st.subheader("📊 Tabla Consolidada (13 Columnas)")
    st.dataframe(df_final, use_container_width=True)

    # Botón de descarga CSV
    csv_data = df_final.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Reporte en CSV",
        data=csv_data,
        file_name="reporte_aduanas_ocr.csv",
        mime="text/csv",
    )
else:
  st.info("Sube tus documentos PDF para iniciar la extracción asistida por OCR.")
