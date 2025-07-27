import os
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
    try:
        return OpenAI(
            api_key=API_KEY,
            base_url=PROXY_BASE_URL,
            default_headers=PROXY_HEADERS
        )
    except Exception as e:
        print(f"Error al configurar el cliente de OpenAI: {e}")
        return None


def obtener_respuesta_chatgpt(cliente, historial):
    try:
        completion = cliente.chat.completions.create(
            model="gpt-4o",
            messages=historial
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error al contactar la API a través del proxy: {e}"


# --- Aplicación Flask ---
app = Flask(__name__)
# IMPORTANTE: Se necesita una 'secret_key' para poder usar sesiones en Flask.
# Para producción, usa una cadena de texto aleatoria y segura.
app.secret_key = FLASK_KEY

cliente_openai = configurar_cliente_proxy()

@app.route('/')
def index():
    return "<h1>Servidor del Chatbot funcionando</h1><p>Usa el endpoint /chat para interactuar y /reset para reiniciar la conversación.</p>"

@app.route('/chat', methods=['POST'])
def chat():
    if not cliente_openai:
        return jsonify({"error": "El cliente de OpenAI no está configurado."}), 500

    datos = request.json
    # Ahora esperamos una clave "mensaje", no "historial"
    if not datos or 'mensaje' not in datos:
        return jsonify({"error": "Cuerpo de la solicitud inválido. Se requiere la clave 'mensaje'."}), 400

    # 1. Recupera el historial de la sesión o crea uno nuevo si no existe.
    historial_conversacion = session.get('historial', [])

    # Añade el mensaje de sistema si la conversación es nueva
    if not historial_conversacion:
        historial_conversacion.append({"role": "system", "content": "You are a helpful assistant."})

    # 2. Añade el nuevo mensaje del usuario al historial
    historial_conversacion.append({"role": "user", "content": datos['mensaje']})

    # 3. Obtiene la respuesta del modelo
    respuesta_gpt = obtener_respuesta_chatgpt(cliente_openai, historial_conversacion)

    # 4. Añade la respuesta del asistente al historial
    historial_conversacion.append({"role": "assistant", "content": respuesta_gpt})

    # 5. Guarda el historial actualizado de vuelta en la sesión
    session['historial'] = historial_conversacion

    return jsonify({"respuesta": respuesta_gpt})

@app.route('/reset', methods=['POST'])
def reset_chat():
    """
    Endpoint para borrar el historial de la conversación actual.
    """
    session.pop('historial', None)  # Elimina el historial de la sesión
    return jsonify({"status": "Conversación reiniciada"})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
