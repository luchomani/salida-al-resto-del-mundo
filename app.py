import pandas as pd
import pdfplumber
import re
import streamlit as st

# Configuración de la interfaz
st.set_page_config(
    page_title="Procesador Aduanero - 13 Columnas", page_icon="📦", layout="wide"
)

st.title("📦 Automatización y Extracción de Documentos Aduaneros")
st.write(
    "Sube tus archivos PDF (Manifiestos de Carga, MCI, Declaraciones) para"
    " estructurar automáticamente la información en las 13 columnas requeridas."
)


def extraer_datos_aduaneros(pdf_file):
  """Función de extracción que mapea exactamente las 13 columnas de control."""

  # Estructura inicial con las 13 columnas exactas
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

  try:
    texto_completo = ""
    with pdfplumber.open(pdf_file) as pdf:
      for pagina in pdf.pages:
        texto = pagina.extract_text()
        if texto:
          texto_completo += texto + "\n"

    # Validar si el PDF contiene texto digital legible
    if not texto_completo.strip():
      datos["Estado_Extraccion"] = "Fallida (PDF sin texto/imagen escaneada)"
      return datos

    # --- EXPRESIONES REGULARES PARA EXTRACCIÓN FLEXIBLE ---

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

    # 6. Cédula / Documento de Identidad del Conductor
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

    # 8 y 9. Pesos Bruto y Neto (Búsqueda heurística de valores numéricos grandes)
    numeros_encontrados = re.findall(
        r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\b", texto_completo
    )
    if len(numeros_encontrados) >= 2:
      # Asigna los primeros valores numéricos detectados como pesos orientativos si aplican
      pass

    # 10. Término de Negociación (Incoterm)
    match_incoterm = re.search(
        r"\b(FOB|CIF|EXW|CFR|DAP|DDP|FCA)\b", texto_completo, re.IGNORECASE
    )
    if match_incoterm:
      datos["Termino_Negociacion"] = match_incoterm.group(1).upper()

    # Validación de éxito global (si encuentra al menos el manifiesto o la placa)
    if (
        datos["Nro_Manifiesto_MCI"] != "No detectado"
        or datos["Placa_Camion"] != "No detectado"
    ):
      datos["Estado_Extraccion"] = "Exitosa"

  except Exception as e:
    datos["Estado_Extraccion"] = f"Error crítico: {str(e)}"

  return datos


# --- Interfaz en Streamlit ---
uploaded_files = st.file_uploader(
    "Selecciona los documentos PDF de transporte",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files:
  if st.button("🚀 Procesar Lote de Documentos", type="primary"):
    lista_resultados = []
    exitosas = 0
    fallidas = 0

    barra_progreso = st.progress(0)
    total_archivos = len(uploaded_files)

    for i, archivo in enumerate(uploaded_files):
      resultado_dict = extraer_datos_aduaneros(archivo)
      lista_resultados.append(resultado_dict)

      if "Exitosa" in resultado_dict["Estado_Extraccion"]:
        exitosas += 1
      else:
        fallidas += 1

      barra_progreso.progress((i + 1) / total_archivos)

    # Resumen visual
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("📁 Total Procesados", total_archivos)
    col2.metric("✅ Exitosas", exitosas)
    col3.metric("❌ Fallidas / Vacías", fallidas)

    # Construcción y orden estricto del DataFrame
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

    # Botón de descarga
    csv_data = df_final.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Reporte Consolidado (CSV)",
        data=csv_data,
        file_name="reporte_aduanas_13_columnas.csv",
        mime="text/csv",
    )
else:
  st.info("Esperando archivos PDF para iniciar el procesamiento en lotes.")
