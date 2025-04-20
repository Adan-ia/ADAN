import os
import telebot
from flask import Flask, request
import logging
import requests
import time
from threading import Thread

# Configuración inicial
TOKEN = os.getenv('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Configuración avanzada de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verificar_conexion() -> bool:
    """Verifica si la API de DeepSeek está disponible"""
    if not DEEPSEEK_API_KEY:
        logger.error("No hay clave API configurada")
        return False
    
    try:
        test_response = requests.get(
            f"{DEEPSEEK_API_URL}/models",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            timeout=5
        )
        return test_response.status_code == 200
    except Exception as e:
        logger.error(f"Error verificando conexión: {str(e)}")
        return False

def consultar_deepseek(pregunta: str) -> str:
    """Consulta mejorada a la API de DeepSeek con manejo de errores"""
    if not DEEPSEEK_API_KEY:
        return "🔴 Error: No tengo configurada la clave API de DeepSeek"
    
    try:
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Eres un asistente útil y preciso que responde en español"},
                {"role": "user", "content": pregunta}
            ],
            "temperature": 0.7,
            "max_tokens": 500,
            "stream": False
        }
        
        logger.info(f"Consultando a DeepSeek: {pregunta[:50]}...")
        
        response = requests.post(
            f"{DEEPSEEK_API_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=20  # Timeout aumentado para Render
        )
        
        logger.info(f"Respuesta HTTP: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            logger.error(f"Error API: {response.status_code} - {response.text[:200]}")
            return f"🔴 Error en API (Código {response.status_code})"
            
    except requests.exceptions.Timeout:
        logger.error("Timeout al consultar DeepSeek")
        return "🕒 La consulta tardó demasiado, intenta nuevamente"
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        return "🔴 Error técnico al procesar tu solicitud"

@bot.message_handler(commands=['start', 'help', 'adan'])
def send_welcome(message):
    """Mensaje de bienvenida mejorado con estado de conexión"""
    estado = "✅ Operativo" if verificar_conexion() else "❌ Sin conexión"
    
    welcome_text = f"""
    🤖 *Asistente ADAN con DeepSeek-V3* 🧠
    
    *Estado:* {estado}
    *Modo de uso:*
    - Escribe tu pregunta directamente
    - O usa /adan [tu pregunta]
    """
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Manejador principal para todas las preguntas"""
    if message.text.startswith('/'):  # Ignorar otros comandos
        return
        
    bot.send_chat_action(message.chat.id, 'typing')
    
    if not message.text.strip():
        bot.reply_to(message, "Por favor escribe una pregunta válida")
        return
    
    respuesta = consultar_deepseek(message.text)
    bot.reply_to(message, f"🧠 *Respuesta:*\n\n{respuesta}", parse_mode="Markdown")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint para webhook de Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Bad request', 400

def setup_webhook():
    """Configuración del webhook para producción"""
    try:
        bot.remove_webhook()
        time.sleep(1)
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
        bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook configurado en: {webhook_url}")
    except Exception as e:
        logger.error(f"Error configurando webhook: {str(e)}")
        raise

def run_flask_app():
    """Inicia la aplicación Flask en el puerto correcto"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    if os.getenv('RENDER'):
        logger.info("Iniciando en modo producción (Render.com)")
        
        # Configura el webhook primero
        setup_webhook()
        
        # Inicia Flask en un hilo separado
        flask_thread = Thread(target=run_flask_app)
        flask_thread.daemon = True
        flask_thread.start()
        
        # Mantén el proceso principal vivo
        while True:
            time.sleep(3600)  # Evita que el proceso termine
    else:
        logger.info("Iniciando en modo desarrollo (polling)")
        bot.remove_webhook()
        bot.infinity_polling()
