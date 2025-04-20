import os
import telebot
from flask import Flask, request
import logging
import requests
import json

# Configuración inicial
TOKEN = os.getenv('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')  # Clave API de DeepSeek
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1')  # URL base de DeepSeek
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Conexión con DeepSeek API ---
def consultar_deepseek(pregunta: str, chat_id: str) -> str:
    """
    Envía consultas a la API de DeepSeek y devuelve la respuesta
    """
    try:
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Eres un asistente útil que responde consultas en español."},
                {"role": "user", "content": pregunta}
            ],
            "stream": False,
            "temperature": 0.7
        }
        
        logger.info(f"Consultando a DeepSeek: {pregunta[:50]}...")  # Log abreviado
        logger.debug(f"Endpoint: {DEEPSEEK_API_URL}/chat/completions")
        
        response = requests.post(
            f'{DEEPSEEK_API_URL}/chat/completions',
            headers=headers,
            json=payload,
            timeout=20
        )
        
        logger.info(f"Respuesta HTTP: {response.status_code}")
        
        if response.status_code == 200:
            respuesta = response.json().get('choices', [{}])[0].get('message', {}).get('content', 'No obtuve respuesta')
            logger.debug(f"Respuesta completa: {respuesta[:200]}...")  # Log parcial
            return respuesta
        else:
            error_msg = f"Error en API DeepSeek: {response.status_code} - {response.text[:200]}"
            logger.error(error_msg)
            return f"Error al consultar DeepSeek (Código: {response.status_code})"
            
    except requests.exceptions.Timeout:
        logger.error("Timeout al consultar DeepSeek")
        return "La consulta tardó demasiado, intenta nuevamente"
    except Exception as e:
        logger.error(f"Excepción al consultar DeepSeek: {str(e)}", exc_info=True)
        return "Ocurrió un error al conectarme con DeepSeek"

# --- Comandos del Bot ---
@bot.message_handler(commands=['start', 'help', 'adan'])
def send_welcome(message):
    welcome_text = """
    🤖 *Hola! Soy tu asistente con tecnología DeepSeek-V3* 🧠
    
    Puedes interactuar conmigo usando:
    /adan [tu pregunta] - Consulta directa
    O simplemente escribe tu pregunta
    
    📡 Estado: {"Operativo" if DEEPSEEK_API_KEY else "Sin conexión a DeepSeek"}
    """
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['ask', 'consulta'])
def handle_ask_command(message):
    """Maneja consultas con comandos alternativos"""
    pregunta = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    if not pregunta:
        bot.reply_to(message, "Por favor escribe tu pregunta después del comando")
        return
    
    bot.send_chat_action(message.chat.id, 'typing')
    respuesta = consultar_deepseek(pregunta, str(message.chat.id))
    bot.reply_to(message, f"🧠 *DeepSeek-V3 responde:*\n\n{respuesta}", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Maneja todos los mensajes que no son comandos"""
    if message.text.startswith('/'):
        return
        
    bot.send_chat_action(message.chat.id, 'typing')
    respuesta = consultar_deepseek(message.text, str(message.chat.id))
    bot.reply_to(message, f"💡 *Respuesta:*\n\n{respuesta}", parse_mode="Markdown")

# --- Webhook (Producción) ---
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Bad request', 400

def setup_webhook():
    try:
        bot.remove_webhook()
        time.sleep(1)
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
        bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook configurado en: {webhook_url}")
    except Exception as e:
        logger.error(f"Error al configurar webhook: {e}", exc_info=True)
        raise

# --- Inicialización ---
if __name__ == '__main__':
    # Verificación inicial de configuración
    required_vars = ['TELEGRAM_TOKEN', 'DEEPSEEK_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Variables faltantes: {', '.join(missing_vars)}")
        raise ValueError(f"Faltan variables de entorno: {', '.join(missing_vars)}")

    if os.getenv('RENDER'):
        logger.info("Iniciando en modo producción (webhook)")
        setup_webhook()
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
    else:
        logger.info("Iniciando en modo desarrollo (polling)")
        bot.remove_webhook()
        bot.infinity_polling()
