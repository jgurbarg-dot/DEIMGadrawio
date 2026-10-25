import streamlit as st
import google.generativeai as genai
import json
import fitz  # PyMuPDF para leer PDFs
from PIL import Image
import io

# 1. Configuración de la página
st.set_page_config(page_title="Img/PDF a Draw.io", layout="centered", page_icon="⚙️")

# 2. Función para generar el XML de Draw.io
def generar_drawio_xml(nodos, conexiones):
    xml = '''<mxfile host="Electron" modified="2023-10-01T12:00:00.000Z" agent="Python" version="21.0.0" type="device">
  <diagram id="diagrama_1" name="Página-1">
    <mxGraphModel dx="1000" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />'''

    for nodo in nodos:
        xml += f'''
        <mxCell id="{nodo.get('id', '')}" value="{nodo.get('texto', '')}" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
          <mxGeometry x="{nodo.get('x', 0)}" y="{nodo.get('y', 0)}" width="120" height="60" as="geometry" />
        </mxCell>'''

    for index, edge in enumerate(conexiones):
        edge_id = f"edge_{index}"
        xml += f'''
        <mxCell id="{edge_id}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;" edge="1" parent="1" source="{edge.get('origen', '')}" target="{edge.get('destino', '')}">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>'''

    xml += '''
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
    return xml

# 3. Interfaz Principal
st.title("⚙️ P&ID a Diagrama Editable (Draw.io)")
st.markdown("Sube imágenes o PDFs de tus diagramas. La IA extraerá los equipos y tuberías a un formato editable.")

# Sidebar para la API Key (Igual que en tu app de Mathcad)
st.sidebar.header("Configuración")
api_key = st.sidebar.text_input("Ingresa tu API Key de Gemini:", type="password")
st.sidebar.markdown("[Obtén tu API Key aquí](https://aistudio.google.com/app/apikey)")

archivo_subido = st.file_uploader("Sube tu archivo (PNG, JPG, PDF)", type=["png", "jpg", "jpeg", "pdf"])

if st.button("Procesar y Generar Archivo"):
    if not api_key:
        st.error("Por favor, ingresa tu API Key en el menú lateral.")
    elif not archivo_subido:
        st.warning("Sube al menos un archivo antes de continuar.")
    else:
        # Configurar API
        genai.configure(api_key=api_key)
        
        # Selección del modelo (Usamos directamente la versión que te funciona)
        model = genai.GenerativeModel('gemini-3.8-flash')

        with st.spinner("Procesando documento con IA..."):
            try:
                # Si es PDF, convertir la primera página a imagen
                if archivo_subido.name.lower().endswith('.pdf'):
                    doc = fitz.open(stream=archivo_subido.read(), filetype="pdf")
                    pagina = doc.load_page(0)
                    pix = pagina.get_pixmap(dpi=150)
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    st.image(img, caption="Primera página del PDF extraída", use_column_width=True)
                else:
                    img = Image.open(archivo_subido)
                    st.image(img, caption="Imagen cargada", use_column_width=True)
                
                # Prompt estricto
                prompt = """
                Analiza este diagrama de ingeniería. 
                Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura exacta, sin formato markdown:
                {
                  "nodos": [
                    {"id": "eq1", "texto": "Tanque", "x": 100, "y": 100},
                    {"id": "v1", "texto": "Válvula", "x": 100, "y": 250}
                  ],
                  "conexiones": [
                    {"origen": "eq1", "destino": "v1"}
                  ]
                }
                Asegúrate de que los IDs coincidan entre nodos y conexiones.
                """
                
                respuesta = model.generate_content([prompt, img])
                texto_respuesta = respuesta.text.strip()
                
                # Limpiar posibles comillas de Markdown
                if texto_respuesta.startswith("```json"):
                    texto_respuesta = texto_respuesta[7:-3]
                elif texto_respuesta.startswith("```"):
                    texto_respuesta = texto_respuesta[3:-3]
                
                datos_ia = json.loads(texto_respuesta.strip())
                
                xml_final = generar_drawio_xml(datos_ia.get("nodos", []), datos_ia.get("conexiones", []))
                
                st.success("¡Diagrama procesado con éxito!")
                
                st.download_button(
                    label="⬇️ Descargar archivo editable (.drawio)",
                    data=xml_final,
                    file_name="diagrama_generado.drawio",
                    mime="application/xml"
                )
                
            except json.JSONDecodeError:
                st.error("Error: El modelo no devolvió un formato JSON válido.")
                st.write(texto_respuesta)
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
