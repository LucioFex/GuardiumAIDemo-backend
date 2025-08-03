import os
import fitz
import base64
import binascii
from openai import OpenAI
from flask import Flask, request, jsonify, session
from flask_cors import CORS
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

def obtener_respuesta_chatgpt(cliente, historial, max_tokens=1024):
    """Obtiene una respuesta del modelo de chat. Se añade max_tokens."""
    try:
        completion = cliente.chat.completions.create(
            model="gpt-4o",
            messages=historial,
            max_tokens=max_tokens
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error al contactar la API: {e}"

# --- Aplicación Flask ---
app = Flask(__name__)
app.secret_key = FLASK_KEY
CORS(app, resources={r"/*": {"origins": "*"}}) # Habilitar CORS para todos los orígenes

@app.route('/')
def index():
    return "<h1>Servidor del Chatbot funcionando</h1>"

@app.route('/chat', methods=['POST'])
def chat():
    datos = request.json
    if not datos or 'mensaje' not in datos:
        return jsonify({"error": "Cuerpo de la solicitud inválido. Se requiere la clave 'mensaje'."}), 400

    usar_guardium = datos.get("GuardiumAI", True)
    cliente_openai = configurar_cliente_proxy() if usar_guardium else configurar_cliente_vanilla()

    if not cliente_openai:
        return jsonify({"error": "No se pudo configurar el cliente de OpenAI."}), 500

    texto_completo = datos['mensaje']
    if 'archivo_pdf_b64' in datos and datos['archivo_pdf_b64']:
        try:
            pdf_bytes = base64.b64decode(datos['archivo_pdf_b64'])
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                texto_pdf = "".join(page.get_text() for page in doc)
            if texto_pdf:
                texto_completo += f"\n\n{texto_pdf}\n"
        except (binascii.Error, Exception) as e:
            return jsonify({"error": f"Error al procesar el PDF: {e}"}), 400

    historial_conversacion = session.get('historial', [])
    if not historial_conversacion:
        historial_conversacion.append({"role": "system", "content": "You are a helpful assistant."})

    historial_conversacion.append({"role": "user", "content": texto_completo})
    
    # --- LÓGICA PRINCIPAL ---
    respuesta_gpt = obtener_respuesta_chatgpt(cliente_openai, historial_conversacion)
    
    historial_conversacion.append({"role": "assistant", "content": respuesta_gpt})
    session['historial'] = historial_conversacion

    # --- LÓGICA DE EVALUACIÓN MEJORADA ---
    estado_aprobacion = "Unknown"

    # 1. Verificar error de seguridad de prompt injection
    if "'message': 'Blocked: PII detected in input'" in respuesta_gpt:
        estado_aprobacion = "Prompt-Injection-Detected"
    else:
        # 3. Si no hay errores, proceder con la evaluación SI/NO
        try:
            prompt_evaluacion = (
                f"En base al veredicto anterior, responde únicamente con la palabra 'SI' o 'NO' a si el candidato es un buen fit para la posición.\n\nTexto a analizar: '{respuesta_gpt}'"
            )
            historial_evaluacion = [{"role": "user", "content": prompt_evaluacion}]
            veredicto_raw = obtener_respuesta_chatgpt(cliente_openai, historial_evaluacion, max_tokens=5)
            veredicto_limpio = veredicto_raw.strip().upper()

            if "SI" in veredicto_limpio:
                estado_aprobacion = "YES"
            elif "NO" in veredicto_limpio:
                estado_aprobacion = "NO"

        except Exception as e:
            print(f"Error durante la evaluación SI/NO: {e}")

    # Devolver la respuesta combinada
    return jsonify({
        "respuesta": respuesta_gpt,
        "aprobado": estado_aprobacion
    })

@app.route('/reset', methods=['POST'])
def reset_chat():
    session.pop('historial', None)
    return jsonify({"status": "Conversación reiniciada"})

if __name__ == '__main__':
    app.run(debug=True, port=5001)