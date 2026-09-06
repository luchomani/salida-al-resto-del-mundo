import io
import re
import pandas as pd
import pdfplumber
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Salida al Resto del Mundo", page_icon="🌍", layout="wide"
)

st.title("🌍 Salida al Resto del Mundo")
st.markdown(
    "Extractor automatizado de documentos de transporte (Manifiestos y Cartas"
    " de Porte)."
)

# Componente de carga múltiple
uploaded_files = st.file_uploader(
    "Arrastra o selecciona tus archivos PDF aquí",
    type=["pdf"],
    accept_multiple_files=True,
)


def extraer_texto_rapido(uploaded_file):
  """Extrae texto de manera nativa y directa del PDF."""
  texto = ""
  try:
    with pdfplumber.open(uploaded_file) as pdf:
      for page in pdf.pages:
        t_pagina = page.extract_text()
        if t_pagina:
          texto += t_pagina + "\n"
  except Exception as e:
    st.error(f"Error leyendo {uploaded_file.name}: {e}")
  return texto


def parsear_datos(texto, nombre_archivo):
  """Aplica expresiones regulares flexibles para capturar los 12 campos clave."""
  datos = {"Archivo": nombre_archivo}

  # Normalizamos el texto (reemplazamos saltos de línea y espacios múltiples por un solo espacio)
  texto_limpio = re.sub(r"\s+", " ", texto)

  # 1. Número del Manifiesto de Carga Internacional (MCI)
  m_mci = re.search(
      r"(?:M\.?C\.?I\.?|Manifiesto|Mto\.?|No\.?\s*Manifesto)[:\s#]*([A-Z0-9\-]{4,15})",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Nro_Manifiesto_MCI"] = (
      m_mci.group(1).strip() if m_mci else "No detectado"
  )

  # 2. Carta de Porte (CPIC)
  m_cp = re.search(
      r"(?:Carta\s*de\s*Porte|CPIC|C[.]?P[.]?)[:\s#]*([A-Z0-9\-]{4,15})",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Carta_de_Porte"] = m_cp.group(1).strip() if m_cp else "No detectada"

  # 3. Placa y País del Camión / Tractocamión
  m_placa = re.search(
      r"(?:Placa\s*(?:Camion|Veh[ií]culo|Chuto)?|Veh[ií]culo)[:\s#]*([A-Z0-9\-]{5,8})",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Placa_Camion"] = (
      m_placa.group(1).strip() if m_placa else "No detectada"
  )

  # 4. Placa y País del Remolque
  m_rem = re.search(
      r"(?:Remolque|Semirremolque|Batea|Unidad)[:\s#]*([A-Z0-9\-]{5,8})",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Placa_Remolque"] = m_rem.group(1).strip() if m_rem else "No detectado"

  # 5. Nombre del Conductor
  m_cond = re.search(
      r"(?:Conductor|Chofer|Nombre)[:\s#]*([A-ZÁÉÍÓÚÑ\s]{5,30})",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Conductor"] = (
      m_cond.group(1).strip() if m_cond else "No detectado"
  )

  # 6. Documento de Identidad del Conductor
  m_doc_cond = re.search(
      r"(?:C[ée]dula|DNI|C\.I\.|Pasaporte)[:\s#]*([0-9\.]{6,12})",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Doc_Identidad_Conductor"] = (
      m_doc_cond.group(1).strip() if m_doc_cond else "No detectado"
  )

  # 7. Número de Precintos
  m_prec = re.search(
      r"(?:Precintos?|Precintos\s*N[°º])[:\s#]*([A-Z0-9\-\,\s]{3,20})",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Nro_Precintos"] = (
      m_prec.group(1).strip() if m_prec else "No detectado"
  )

  # 8. Peso Bruto (Kg)
  m_pb = re.search(
      r"(?:Peso\s*Bruto|Bruto)[:\s#]*([0-9\.,]+\s*(?:Kg|Kgs)?)",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Peso_Bruto"] = m_pb.group(1).strip() if m_pb else "No detectado"

  # 9. Peso Neto (Kg)
  m_pn = re.search(
      r"(?:Peso\s*Neto|Neto)[:\s#]*([0-9\.,]+\s*(?:Kg|Kgs)?)",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Peso_Neto"] = m_pn.group(1).strip() if m_pn else "No detectado"

  # 10. Término de Negociación (Incoterm)
  m_incoterm = re.search(
      r"(?:Incoterm|Condici[oó]n|T[ée]rmino|CPT|FOB|EXW|CIF)[:\s#]*([A-Z0-9\s\/]{3,15})",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Termino_Negociacion"] = (
      m_incoterm.group(1).strip() if m_incoterm else "No detectado"
  )

  # 11. Formulario Asociado (FMM)
  m_fmm = re.search(
      r"(?:FMM|Movimiento|Declaraci[oó]n)[:\s#]*([0-9\-]{5,15})",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Formulario_Asociado"] = (
      m_fmm.group(1).strip() if m_fmm else "No detectado"
  )

  # 12. Formulario de Salida
  m_salida = re.search(
      r"(?:Salida|ZFS|Formulario)[:\s#]*([0-9\-]{5,15})",
      texto_limpio,
      re.IGNORECASE,
  )
  datos["Formulario_Salida"] = (
      m_salida.group(1).strip() if m_salida else "No detectado"
  )

  return datos


if uploaded_files:
  resultados = []
  textos_crudos_dict = {}

  barra_progreso = st.progress(0)
  total_archivos = len(uploaded_files)

  for i, archivo in enumerate(uploaded_files):
    texto_crudo = extraer_texto_rapido(archivo)
    textos_crudos_dict[archivo.name] = texto_crudo  # Guardar para diagnóstico
    info_extraida = parsear_datos(texto_crudo, archivo.name)
    resultados.append(info_extraida)
    barra_progreso.progress((i + 1) / total_archivos)

  df_resultado = pd.DataFrame(resultados)
  barra_progreso.empty()

  # Métricas Visuales
  col1, col2 = st.columns(2)
  with col1:
    st.metric(
        label="📁 Documentos Procesados",
        value=total_archivos,
        delta="Lectura optimizada",
    )
  with col2:
    exitosos = (df_resultado["Nro_Manifiesto_MCI"] != "No detectado").sum()
    st.metric(label="⚡ Extracción Exitosa", value=f"{exitosos} / {total_archivos}")

  st.markdown("---")
  st.subheader("📋 Consolidado Logístico de Salidas")
  st.dataframe(df_resultado, use_container_width=True)

  # 🔍 HERRAMIENTA DE DIAGNÓSTICO: Ver qué leyó exactamente el PDF
  with st.expander("🔍 Ver Texto Crudo Extraído (Herramienta de Diagnóstico)"):
    archivo_sel = st.selectbox(
        "Selecciona un archivo para inspeccionar su texto:",
        list(textos_crudos_dict.keys()),
    )
    if archivo_sel:
      st.text_area(
          "Texto plano extraído por el sistema:",
          textos_crudos_dict[archivo_sel],
          height=250,
      )

  # Descarga a Excel
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_resultado.to_excel(
        writer, index=False, sheet_name="Consolidado_Salidas_Mundiales"
    )
  excel_data = output.getvalue()

  st.download_button(
      label="📥 Descargar Consolidado en Excel",
      data=excel_data,
      file_name="salida_al_resto_del_mundo_consolidado.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )
else:
  st.info(
      "👆 Sube tus manifiestos en PDF arriba para iniciar la extracción flexible."
  )
