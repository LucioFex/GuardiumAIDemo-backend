import os
import fitz
import base64
import binascii
from openai import OpenAI
from flask import Flask, request, jsonify, session
from dotenv import load_dotenv

# Carga de las vars de entorno desde el archivo .env
load_dotenv()

# --- Configuración y Cliente ---
API_KEY = os.getenv("OPENAI_API_KEY")
FLASK_KEY = os.getenv("FLASK_SECRET_KEY")
PROXY_BASE_URL = os.getenv("PROXY_BASE_URL")
PROXY_HEADER_VALUE = os.getenv("PROXY_HEADER_IDENTIFIER")
PROXY_HEADERS = {"x-alltrue-llm-endpoint-identifier": PROXY_HEADER_VALUE}


def configurar_cliente_proxy():
    """Configura el cliente para usar el proxy de Guardium AI."""
    try:
        return OpenAI(
            api_key=API_KEY,
            base_url=PROXY_BASE_URL,
            default_headers=PROXY_HEADERS
        )
    except Exception as e:
        print(f"Error al configurar el cliente PROXY de OpenAI: {e}")
        return None


def configurar_cliente_vanilla():
    """Configura el cliente para usar OpenAI directamente."""
    try:
        return OpenAI(api_key=API_KEY)
    except Exception as e:
        print(f"Error al configurar el cliente VANILLA de OpenAI: {e}")
        return None


def obtener_respuesta_chatgpt(cliente, historial):
    try:
        completion = cliente.chat.completions.create(
            model="gpt-4o",
            messages=historial
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error al contactar la API: {e}"


# --- Aplicación Flask ---
app = Flask(__name__)
app.secret_key = FLASK_KEY

# Ya no se configura un cliente global aquí


@app.route('/')
def index():
    return "<h1>Servidor del Chatbot funcionando</h1><p>Usa el endpoint /chat para interactuar y /reset para reiniciar la conversación.</p>"


@app.route('/chat', methods=['POST'])
def chat():
    datos = request.json
    if not datos or 'mensaje' not in datos:
        return jsonify({"error": "Cuerpo de la solicitud inválido. Se requiere la clave 'mensaje'."}), 400

    # 1. Decide qué cliente usar basado en el parámetro "GuardiumAI"
    # Por defecto, usa Guardium si el parámetro no se especifica.
    usar_guardium = datos.get("GuardiumAI", True)

    if usar_guardium:
        print("Usando configuración de Guardium AI...")
        cliente_openai = configurar_cliente_proxy()
    else:
        print("Usando configuración de OpenAI Vanilla...")
        cliente_openai = configurar_cliente_vanilla()

    if not cliente_openai:
        return jsonify({"error": "No se pudo configurar el cliente de OpenAI."}), 500

    # El resto de la lógica permanece igual
    texto_usuario = datos['mensaje']
    texto_completo = texto_usuario

    if 'archivo_pdf_b64' in datos and datos['archivo_pdf_b64']:
        try:
            pdf_bytes = base64.b64decode(datos['archivo_pdf_b64'])
            documento_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

            texto_extraido_pdf = ""
            for pagina in documento_pdf:
                texto_extraido_pdf += pagina.get_text()
            documento_pdf.close()

            if texto_extraido_pdf:
                texto_completo += f"\n\n{texto_extraido_pdf}\n"

        except binascii.Error:
            return jsonify({"error": "El string Base64 para el archivo PDF es inválido."}), 400
        except Exception as e:
            return jsonify({"error": f"Ocurrió un error al procesar el archivo PDF desde Base64: {e}"}), 500

    historial_conversacion = session.get('historial', [])
    if not historial_conversacion:
        historial_conversacion.append({"role": "system", "content": "You are a helpful assistant."})

    historial_conversacion.append({"role": "user", "content": texto_completo})
    respuesta_gpt = obtener_respuesta_chatgpt(cliente_openai, historial_conversacion)
    historial_conversacion.append({"role": "assistant", "content": respuesta_gpt})
    session['historial'] = historial_conversacion

    return jsonify({"respuesta": respuesta_gpt})


@app.route('/reset', methods=['POST'])
def reset_chat():
    session.pop('historial', None)
    return jsonify({"status": "Conversación reiniciada"})


if __name__ == '__main__':
    app.run(debug=True, port=5001)