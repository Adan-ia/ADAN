import os
import telebot
from flask import Flask, request
import logging
import requests
import time
from threading import Thread
import json

# Configuración inicial con verificación estricta
try:
    TOKEN = os.environ['TELEGRAM_TOKEN']
    DEEPSEEK_API_KEY = os.environ['DEEPSEEK_API_KEY']
    DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1')
    
    # Validación básica de las credenciales
    if not TOKEN or not DEEPSEEK_API_KEY:
        raise ValueError("Credenciales esenciales no configuradas")
        
except KeyError as e:
    raise SystemExit(f"Error: Variable de entorno faltante - {str(e)}")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Configuración avanzada de logging
logging.basicConfig(
    level=logging.DEBUG,  # Cambiado a DEBUG para máxima visibilidad
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_debug.log')  # Logs persistentes
    ]
)
logger = logging.getLogger(__name__)

class DeepSeekConnector:
    """Clase dedicada para manejar la conexión con DeepSeek API"""
    
    @staticmethod
    def verify_connection() -> dict:
        """Verificación detallada de la conexión"""
        if not DEEPSEEK_API_KEY:
            return {
                'status': False,
                'message': 'API Key no configurada',
                'details': None
            }
        
        try:
            start_time = time.time()
            response = requests.get(
                f"{DEEPSEEK_API_URL}/models",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
                timeout=10
            )
            
            latency = round((time.time() - start_time) * 1000, 2)
            
            if response.status_code == 200:
                return {
                    'status': True,
                    'message': 'Conexión exitosa',
                    'details': {
                        'latency_ms': latency,
                        'response': response.json()
                    }
                }
            else:
                return {
                    'status': False,
                    'message': f'Error HTTP {response.status_code}',
                    'details': {
                        'response': response.text[:500],
                        'headers': dict(response.headers)
                    }
                }
                
        except Exception as e:
            return {
                'status': False,
                'message': str(e),
                'details': {
                    'type': type(e).__name__
                }
            }

    @staticmethod
    def query(prompt: str) -> dict:
        """Método robusto para consultar a la API"""
        connection = DeepSeekConnector.verify_connection()
        if not connection['status']:
            return {
                'success': False,
                'response': None,
                'error': connection['message'],
                'details': connection['details']
            }
        
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Eres un asistente útil en español"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": False
            }
            
            headers = {
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.debug(f"Enviando payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                f"{DEEPSEEK_API_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30  # Timeout generoso
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'response': response.json(),
                    'error': None,
                    'details': {
                        'status_code': response.status_code,
                        'latency_ms': response.elapsed.total_seconds() * 1000
                    }
                }
            else:
                return {
                    'success': False,
                    'response': None,
                    'error': f"HTTP {response.status_code}",
                    'details': {
                        'response_text': response.text[:500],
                        'headers': dict(response.headers)
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'response': None,
                'error': str(e),
                'details': {
                    'type': type(e).__name__
                }
            }

# Handlers de Telegram mejorados
@bot.message_handler(commands=['start', 'help', 'adan'])
def send_welcome(message):
    """Mensaje de bienvenida con diagnóstico completo"""
    connection = DeepSeekConnector.verify_connection()
    
    status_icon = "✅" if connection['status'] else "❌"
    status_text = (f"{status_icon} *Estado:* {connection['message']}\n\n"
                  f"*Detalles técnicos:*\n"
                  f"```{json.dumps(connection.get('details', {}), indent=2)}```")
    
    welcome_msg = f"""
    🤖 *Asistente ADAN con DeepSeek-V3* 🧠
    
    {status_text}
    
    *Cómo usarme:*
    - Escribe tu pregunta directamente
    - O usa /adan [tu pregunta]
    """
    
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Manejador principal con respuesta detallada"""
    if message.text.startswith('/'):
        return
        
    bot.send_chat_action(message.chat.id, 'typing')
    
    if not message.text.strip():
        bot.reply_to(message, "Por favor escribe una pregunta válida")
        return
    
    result = DeepSeekConnector.query(message.text)
    
    if result['success']:
        try:
            answer = result['response']['choices'][0]['message']['content']
            bot.reply_to(message, f"🧠 *Respuesta:*\n\n{answer}", parse_mode="Markdown")
        except KeyError:
            error_msg = "Recibí una respuesta inesperada de la API"
            logger.error(f"{error_msg}: {json.dumps(result['response'], indent=2)}")
            bot.reply_to(message, f"🔴 {error_msg}. Por favor intenta nuevamente.")
    else:
        error_msg = (f"No pude obtener una respuesta. Error: {result['error']}\n\n"
                    f"Detalles: {result.get('details', {}).get('response_text', '')}")
        bot.reply_to(message, error_msg)

# Configuración del servidor web optimizada
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Endpoint para webhook con manejo robusto de errores"""
    try:
        if request.headers.get('content-type') == 'application/json':
            update = telebot.types.Update.de_json(request.get_json())
            bot.process_new_updates([update])
            return '', 200
        return 'Bad request', 400
    except Exception as e:
        logger.error(f"Error en webhook: {str(e)}", exc_info=True)
        return 'Internal Server Error', 500

def configure_webhook():
    """Configuración del webhook con reintentos"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            bot.remove_webhook()
            time.sleep(1)
            webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
            bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook configurado exitosamente en {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Intento {attempt + 1} fallido: {str(e)}")
            if attempt < max_attempts - 1:
                time.sleep(2)
    
    logger.critical("No se pudo configurar el webhook después de varios intentos")
    return False

def run_server():
    """Inicia el servidor web con configuración optimizada"""
    port = int(os.getenv('PORT', 10000))
    app.run(
        host='0.0.0.0',
        port=port,
        threaded=True,
        debug=False,
        use_reloader=False
    )

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("Iniciando servicio ADAN")
    logger.info(f"Versión API: {DEEPSEEK_API_URL}")
    logger.info("="*60)
    
    # Verificación inicial de conexión
    initial_check = DeepSeekConnector.verify_connection()
    logger.info(f"Verificación inicial: {json.dumps(initial_check, indent=2)}")
    
    if os.getenv('RENDER'):
        logger.info("Modo: Producción (Render.com)")
        
        if not configure_webhook():
            logger.critical("Error crítico al configurar webhook. Saliendo.")
            exit(1)
            
        server_thread = Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        logger.info("Servicio iniciado. Esperando mensajes...")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            logger.info("Recibida señal de interrupción. Saliendo.")
    else:
        logger.info("Modo: Desarrollo (Polling)")
        bot.remove_webhook()
        bot.infinity_polling()
