import pdfplumber
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Prueba de Extracción - Diagnóstico PDF", layout="wide"
)

st.title("🧪 Laboratorio de Pruebas: Diagnóstico de Texto PDF")
st.write(
    "Sube un archivo PDF problemático para ver exactamente qué información"
    " está extrayendo el sistema en crudo."
)

# Selector de un solo archivo para prueba rápida
archivo_subido = st.file_uploader(
    "Sube tu documento PDF de prueba", type=["pdf"]
)

if archivo_subido is not None:
  st.success("¡Archivo cargado correctamente!")

  texto_total = ""

  try:
    with pdfplumber.open(archivo_subido) as pdf:
      st.info(
          f"📄 El documento tiene **{len(pdf.pages)}** página(s) detectada(s)."
      )

      for i, pagina in enumerate(pdf.pages):
        texto_pagina = pagina.extract_text()
        if texto_pagina:
          texto_total += f"\n--- PÁGINA {i + 1} ---\n" + texto_pagina + "\n"
        else:
          st.warning(
              f"⚠️ La página {i + 1} no tiene texto digital seleccionable"
              " (podría ser una imagen escaneada)."
          )

    # Mostrar resultados en pantalla
    if texto_total.strip():
      st.subheader("📝 Texto crudo extraído:")
      st.write(
          "Revisa este texto y busca las etiquetas reales (ej. ¿Dice"
          " 'Manifiesto:', 'MCI:', 'Placa:', etc.?)"
      )

      # Área de texto amplia para visualizar y copiar el contenido extraído
      st.text_area(
          "Contenido detectado en el PDF", value=texto_total, height=450
      )
    else:
      st.error(
          "❌ El texto está completamente vacío. Esto significa que el PDF es"
          " una imagen escaneada y las expresiones regulares no funcionarán"
          " porque no hay texto que leer directamente."
      )

  except Exception as e:
    st.error(f"❌ Ocurrió un error al abrir el archivo: {str(e)}")
else:
  st.info("Por favor, sube un archivo PDF para iniciar la prueba.")
