import streamlit as st
import google.generativeai as genai
import json
from PIL import Image

# 1. Configuración de la página
st.set_page_config(page_title="Img to Draw.io", layout="centered")

# 2. Configuración de la API de Gemini (Usando los Secrets de Streamlit)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Usamos Gemini 1.5 Pro o Flash por sus excelentes capacidades de visión
    model = genai.GenerativeModel('gemini-1.5-flash') 
except Exception as e:
    st.error("Error al configurar la API. Verifica tus Secrets en Streamlit.")

# 3. Función para generar el XML de Draw.io
def generar_drawio_xml(nodos, conexiones):
    xml = '''<mxfile host="Electron" modified="2023-10-01T12:00:00.000Z" agent="Python" version="21.0.0" type="device">
  <diagram id="diagrama_1" name="Página-1">
    <mxGraphModel dx="1000" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />'''

    # Generar Nodos
    for nodo in nodos:
        xml += f'''
        <mxCell id="{nodo.get('id', '')}" value="{nodo.get('texto', '')}" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
          <mxGeometry x="{nodo.get('x', 0)}" y="{nodo.get('y', 0)}" width="120" height="60" as="geometry" />
        </mxCell>'''

    # Generar Conexiones
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

# 4. Interfaz Principal
st.title("Diagram Extract: Imagen a Draw.io")
st.write("Sube una imagen de un diagrama. La IA extraerá los nodos y conexiones para crear un archivo `.drawio` editable.")

imagen_subida = st.file_uploader("Sube tu imagen (PNG, JPG)", type=["png", "jpg", "jpeg"])

if imagen_subida:
    img = Image.open(imagen_subida)
    st.image(img, caption="Imagen cargada", use_column_width=True)
    
    if st.button("Procesar y Generar Archivo"):
        with st.spinner("Analizando topología del diagrama..."):
            try:
                # Prompt estricto para forzar la salida en JSON puro
                prompt = """
                Analiza el diagrama de esta imagen. 
                Extrae los bloques/nodos y las líneas que los conectan.
                Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura exacta, sin formato markdown ni texto adicional:
                {
                  "nodos": [
                    {"id": "n1", "texto": "Texto del bloque", "x": 100, "y": 100},
                    {"id": "n2", "texto": "Otro bloque", "x": 100, "y": 250}
                  ],
                  "conexiones": [
                    {"origen": "n1", "destino": "n2"}
                  ]
                }
                Intenta estimar las posiciones x, y basándote en la imagen (usa valores de 0 a 800 aproximadamente).
                Asegúrate de que los IDs coincidan entre nodos y conexiones.
                """
                
                respuesta = model.generate_content([prompt, img])
                texto_respuesta = respuesta.text.strip()
                
                # Limpieza por si el modelo incluye marcas de bloque de código Markdown
                if texto_respuesta.startswith("```json"):
                    texto_respuesta = texto_respuesta[7:-3]
                elif texto_respuesta.startswith("```"):
                    texto_respuesta = texto_respuesta[3:-3]
                
                datos_ia = json.loads(texto_respuesta.strip())
                
                nodos = datos_ia.get("nodos", [])
                conexiones = datos_ia.get("conexiones", [])
                
                xml_final = generar_drawio_xml(nodos, conexiones)
                
                st.success(f"¡Análisis completo! Se detectaron {len(nodos)} nodos y {len(conexiones)} conexiones.")
                
                st.download_button(
                    label="⬇️ Descargar archivo editable (.drawio)",
                    data=xml_final,
                    file_name="diagrama_generado.drawio",
                    mime="application/xml"
                )
                
            except json.JSONDecodeError:
                st.error("Error al procesar los datos de la IA. El modelo no devolvió un JSON válido. Intenta de nuevo.")
                with st.expander("Ver salida cruda de la IA para depurar"):
                    st.write(texto_respuesta)
            except Exception as e:
                st.error(f"Ocurrió un error inesperado: {e}")
