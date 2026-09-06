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
    "Procesamiento ultrarrápido y unificado de **Manifiestos de Carga** y"
    " **Cartas de Porte**."
)

# Componente de carga múltiple
uploaded_files = st.file_uploader(
    "Arrastra o selecciona tus archivos PDF aquí",
    type=["pdf"],
    accept_multiple_files=True,
)


def extraer_texto_rapido(uploaded_file):
  """Extrae texto de manera nativa y directa del PDF en milisegundos."""
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
  """Aplica expresiones regulares para capturar la información clave."""
  datos = {"Archivo": nombre_archivo}

  # Nro de Documento / Manifiesto / MCI / CPIC
  m_doc = re.search(
      r"(?:Manifiesto|MCI|Carta\s*de\s*Porte|CPIC|N[°º]\s*Manifesto)[:\s]*([A-Z0-9\-]+)",
      texto,
      re.IGNORECASE,
  )
  datos["Nro_Documento"] = (
      m_doc.group(1).strip() if m_doc else "No detectado"
  )

  # Placa del Vehículo (Chuto)
  m_placa = re.search(
      r"(?:Placa|Veh[ií]culo|Chuto|Placa\s*Camion)[:\s]*([A-Z0-9\-]{5,8})",
      texto,
      re.IGNORECASE,
  )
  datos["Placa_Vehiculo"] = (
      m_placa.group(1).strip() if m_placa else "No detectada"
  )

  # Remolque / Unidad de Carga
  m_rem = re.search(
      r"(?:Remolque|Semirremolque|Batea|Unidad)[:\s]*([A-Z0-9\-]{5,8})",
      texto,
      re.IGNORECASE,
  )
  datos["Placa_Remolque"] = (
      m_rem.group(1).strip() if m_rem else "No detectado"
  )

  # Conductor
  m_cond = re.search(
      r"(?:Conductor|Chofer|Nombre\s*Conductor)[:\s]*([A-ZÁÉÍÓÚÑ\s]+)",
      texto,
      re.IGNORECASE,
  )
  datos["Conductor"] = (
      m_cond.group(1).strip() if m_cond else "No detectado"
  )

  # Destinatario
  m_dest = re.search(
      r"(?:Destinatario|Consignatario)[:\s]*([A-ZÁÉÍÓÚÑ0-9\.\,\s]+)",
      texto,
      re.IGNORECASE,
  )
  datos["Destinatario"] = (
      m_dest.group(1).strip() if m_dest_destinatario else "No detectado"
  )

  return datos


if uploaded_files:
  resultados = []

  # Barra de progreso visual para mejor experiencia
  barra_progreso = st.progress(0)
  total_archivos = len(uploaded_files)

  for i, archivo in enumerate(uploaded_files):
    texto_crudo = extraer_texto_rapido(archivo)
    info_extraida = parsear_datos(texto_crudo, archivo.name)
    resultados.append(info_extraida)
    barra_progreso.progress((i + 1) / total_archivos)

  df_resultado = pd.DataFrame(resultados)
  barra_progreso.empty()  # Limpiar barra al terminar

  # Tarjetas de Métricas Visuales
  col1, col2 = st.columns(2)
  with col1:
    st.metric(
        label="📁 Documentos Procesados",
        value=total_archivos,
        delta="Carga completa",
    )
  with col2:
    exitosos = (df_resultado["Nro_Documento"] != "No detectado").sum()
    st.metric(
        label="⚡ Tasa de Extracción Exitosa",
        value=f"{exitosos} / {total_archivos}",
    )

  st.markdown("---")
  st.subheader("📋 Consolidado Logístico Extraído")
  st.dataframe(df_resultado, use_container_width=True)

  # Botón de descarga optimizado
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_resultado.to_excel(writer, index=False, sheet_name="Consolidado_Salidas")
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
  st.info("👆 Sube tus manifiestos en PDF arriba para iniciar la lectura.")
