from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import pandas as pd
import pdfplumber
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import re
import streamlit as st

# Configuración de la interfaz
st.set_page_config(
    page_title="Procesador Aduanero de Alto Rendimiento",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Automatización Aduanera Optimizada (Multihilo + OCR Avanzado)")
st.write(
    "Sube tus documentos PDF. El sistema procesará todo en paralelo de forma"
    " ultrarrápida y filtrará los datos exactos para las 13 columnas."
)


def limpiar_texto(texto):
  """Limpia saltos de línea excesivos y espacios duplicados."""
  if not texto:
    return "No detectado"
  return " ".join(texto.split())


def extraer_datos_aduaneros(pdf_file):
  """Función de extracción optimizada con filtros de precisión."""
  nombre_archivo = pdf_file.name
  datos = {
      "Archivo": nombre_archivo,
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
      "Observaciones": "Procesado correctamente",
      "Estado_Extraccion": "Fallida",
  }

  try:
    bytes_pdf = pdf_file.read()
    texto_completo = ""

    # 1. Intento rápido de texto digital
    try:
      with pdfplumber.open(io.BytesIO(bytes_pdf)) as pdf:
        for pagina in pdf.pages:
          t = pagina.extract_text()
          if t:
            texto_completo += t + "\n"
    except Exception:
      pass

    # 2. Si no hay texto digital, aplicar OCR optimizado (escala de grises)
    if not texto_completo.strip():
      # Carga rápida convirtiendo a escala de grises para acelerar Tesseract
      imagenes = convert_from_bytes(bytes_pdf, dpi=200)
      for img in imagenes:
        img_gris = img.convert("L")
        texto_ocr = pytesseract.image_to_string(
            img_gris, lang="spa", config="--psm 6"
        )
        texto_completo += texto_ocr + "\n"
      datos["Observaciones"] = "OCR Optimizado (Escaneado)"
    else:
      datos["Observaciones"] = "Texto Digital Directo"

    if not texto_completo.strip():
      datos["Estado_Extraccion"] = "Fallida (Sin contenido legible)"
      return datos

    # --- EXPRESIONES REGULARES REFINADAS (EVITAN ETIQUETAS FALSAS) ---

    # 1. Manifiesto / MCI (busca números de 4 a 12 dígitos tras palabras clave)
    match_mci = re.search(
        r"(?:NATIS|MANIFIESTO|MCI|N[°º])[^\d]*(\d{4,12})",
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

    # 3. Placa Camión (Evita palabras genéricas como HABILITA)
    matches_placas = re.findall(
        r"\b([A-Z]{3}\d{3}|[A-Z0-9]{5,6})\b", texto_completo
    )
    placas_validas = [
        p
        for p in matches_placas
        if p not in ["HABILITA", "VEHICULO", "TRANSPORTE"]
    ]
    if placas_validas:
      datos["Placa_Camion"] = placas_validas[0]
      if len(placas_validas) > 1:
        datos["Placa_Remolque"] = placas_validas[1]

    # 4. Cédula del Conductor (Números de identificación de 6 a 10 dígitos)
    match_doc = re.search(
        r"(?:Documento|C[eé]dula|Identidad|DNI)[^\d]*(\d{6,10})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_doc:
      datos["Conductor_Cedula"] = match_doc.group(1).strip()

    # 5. Nombre del Conductor (Busca líneas posteriores a etiquetas de conductor)
    match_cond = re.search(
        r"(?:CONDUCTOR PRINCIPAL|Conductor)[^\w\n]*([A-ZÁÉÍÓÚÑ\s]{6,40})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_cond:
      nombre = limpiar_texto(match_cond.group(1))
      if "NOMBRE" not in nombre.upper():
        datos["Conductor_Nombre"] = nombre

    # 6. Precintos (Busca códigos alfanuméricos de precintos)
    match_prec = re.search(
        r"(?:Precintos?|Sellos?)[^\w]*([A-Z0-9\-]{4,15})",
        texto_completo,
        re.IGNORECASE,
    )
    if match_prec:
      datos["Nro_Precintos"] = limpiar_texto(match_prec.group(1))

    # 7. Término de Negociación (Incoterms)
    match_incoterm = re.search(
        r"\b(FOB|CIF|EXW|CFR|DAP|DDP|FCA)\b", texto_completo, re.IGNORECASE
    )
    if match_incoterm:
      datos["Termino_Negociacion"] = match_incoterm.group(1).upper()

    # Validación de éxito
    if datos["Nro_Manifiesto_MCI"] != "No detectado" or placas_validas:
      datos["Estado_Extraccion"] = "Exitosa"
    else:
      datos["Estado_Extraccion"] = "Revisión requerida"

  except Exception as e:
    datos["Estado_Extraccion"] = f"Error: {str(e)}"

  return datos


# --- Interfaz Principal Streamlit ---
uploaded_files = st.file_uploader(
    "Selecciona los documentos PDF de transporte",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files:
  if st.button("⚡ Procesar en Paralelo (Alta Velocidad)", type="primary"):
    lista_resultados = []
    barra_progreso = st.progress(0)
    total_archivos = len(uploaded_files)

    # Procesamiento en paralelo con ThreadPoolExecutor para máxima velocidad
    with ThreadPoolExecutor(max_workers=4) as executor:
      futures = {
          executor.submit(extraer_datos_aduaneros, archivo): archivo
          for archivo in uploaded_files
      }

      for i, future in enumerate(as_completed(futures)):
        resultado_dict = future.result()
        lista_resultados.append(resultado_dict)
        barra_progreso.progress((i + 1) / total_archivos)

    # Métricas de rendimiento
    st.markdown("---")
    exitosas = sum(
        1 for r in lista_resultados if "Exitosa" in r["Estado_Extraccion"]
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("📁 Total Procesados", total_archivos)
    col2.metric("✅ Exitosas", exitosas)
    col3.metric("⏱️ Rendimiento", "Optimizado Multihilo")

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

    st.subheader("📊 Tabla Consolidada")
    st.dataframe(df_final, use_container_width=True)

    # Botón de descarga CSV
    csv_data = df_final.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Reporte en CSV",
        data=csv_data,
        file_name="reporte_aduanas_optimizado.csv",
        mime="text/csv",
    )
else:
  st.info("Sube tus archivos PDF para comenzar el procesamiento rápido.")
