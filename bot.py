import os
import telebot
from flask import Flask, request
import logging
import requests
import json

# Configuración inicial
TOKEN = os.getenv('TELEGRAM_TOKEN')
ADAN_API_KEY = os.getenv('ADAN_API_KEY')  # Tu clave API de DeepSeek
ADAN_API_URL = os.getenv('ADAN_API_URL', 'https://api.deepseek.com/v1')  # URL base
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Conexión con DeepSeek API ---
def consultar_deepseek(pregunta: str, chat_id: str) -> str:
    """
    Envía consultas a la API de DeepSeek y devuelve la respuesta
    """
    try:
        headers = {
            'Authorization': f'Bearer {ADAN_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "deepseek-chat",  # Usando el modelo DeepSeek-V3
            "messages": [
                {"role": "system", "content": "Eres un asistente útil que responde consultas en español."},
                {"role": "user", "content": pregunta}
            ],
            "stream": False
        }
        
        response = requests.post(
            f'{DEEPSEEK_API_URL}/chat/completions',
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json().get('choices', [{}])[0].get('message', {}).get('content', 'No obtuve respuesta')
        else:
            logger.error(f"Error en API DeepSeek: {response.status_code} - {response.text}")
            return f"Error al consultar DeepSeek (Código: {response.status_code})"
            
    except Exception as e:
        logger.error(f"Excepción al consultar DeepSeek: {str(e)}")
        return "Ocurrió un error al conectarme con DeepSeek"

# --- Comandos del Bot ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
    🤖 *Hola! Soy tu asistente con DeepSeek-V3* 🧠
    
    Puedes interactuar conmigo:
    /ask [tu pregunta] - Consulta directa
    O simplemente escribe tu pregunta
    """
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['ask'])
def handle_ask_command(message):
    """Maneja consultas con el comando /ask"""
    pregunta = message.text.split('/ask ')[1] if len(message.text.split()) > 1 else ""
    if not pregunta:
        bot.reply_to(message, "Por favor escribe tu pregunta después de /ask")
        return
    
    bot.send_chat_action(message.chat.id, 'typing')
    respuesta = consultar_deepseek(pregunta, str(message.chat.id))
    bot.reply_to(message, f"🧠 *Respuesta de DeepSeek-V3:*\n\n{respuesta}", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Maneja todos los mensajes que no son comandos"""
    if message.text.startswith('/'):
        return
        
    bot.send_chat_action(message.chat.id, 'typing')
    respuesta = consultar_deepseek(message.text, str(message.chat.id))
    bot.reply_to(message, f"💡 *DeepSeek dice:*\n\n{respuesta}", parse_mode="Markdown")

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
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
        bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook configurado en: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ Error al configurar webhook: {e}")

# --- Polling (Desarrollo Local) ---
def setup_polling():
    bot.remove_webhook()
    logger.info("🔄 Iniciando bot en modo polling...")
    bot.infinity_polling()

# --- Inicialización ---
if __name__ == '__main__':
    if os.getenv('RENDER'):
        setup_webhook()
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
    else:
        setup_polling()
