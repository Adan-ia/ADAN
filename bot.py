import os
import logging
from typing import Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Configuración mejorada del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')  # Log a archivo
    ]
)
logger = logging.getLogger(__name__)

class Config:
    """Configuración validada con mejor manejo de errores"""
    def __init__(self):
        self._validate_env_vars()
        
        self.TOKEN = os.getenv('TELEGRAM_TOKEN')
        self.API_KEY = self._validate_api_key(os.getenv('DEEPSEEK_API_KEY'))
        self.API_URL = self._normalize_url(os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com'))
        self.WEBHOOK_URL = os.getenv('WEBHOOK_URL')
        self.PORT = int(os.getenv('PORT', 8000))

    def _validate_env_vars(self):
        """Valida que todas las variables requeridas existan"""
        required_vars = {
            'TELEGRAM_TOKEN': 'Token de Telegram',
            'DEEPSEEK_API_KEY': 'API Key de DeepSeek'
        }
        
        missing = [name for var, name in required_vars.items() if not os.getenv(var)]
        if missing:
            error_msg = f"Faltan variables de entorno: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _validate_api_key(self, api_key: str) -> str:
        """Valida el formato básico de la API key"""
        if not api_key or len(api_key.strip()) < 20:  # Longitud mínima aproximada
            error_msg = "API Key de DeepSeek no válida o demasiado corta"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return api_key.strip()

    def _normalize_url(self, url: str) -> str:
        """Normaliza la URL de la API"""
        url = url.strip().lower().replace('http://', 'https://')
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        return url.rstrip('/') + '/v1'

class DeepSeekAPI:
    """Cliente mejorado para DeepSeek con mejor manejo de errores"""
    def __init__(self, api_key: str, base_url: str):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.base_url = base_url
        logger.info(f"DeepSeekAPI configurado con URL: {base_url}")

    def query(self, prompt: str) -> Dict[str, Any]:
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Eres un asistente útil en español"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            logger.info(f"Enviando consulta a DeepSeek: {prompt[:50]}...")
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            # Loggear la respuesta (sin el contenido completo por seguridad)
            logger.info(f"Respuesta de DeepSeek - Status: {response.status_code}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as http_err:
            error_detail = response.json().get('error', {}) if response else {}
            logger.error(f"Error HTTP en DeepSeek API: {http_err}. Detalles: {error_detail}")
            raise Exception(f"Error en la API: {error_detail.get('message', str(http_err))}")
        except Exception as e:
            logger.error(f"Error inesperado al consultar DeepSeek: {str(e)}", exc_info=True)
            raise Exception("Error procesando tu solicitud. Por favor intenta nuevamente.")

# Inicialización
try:
    config = Config()
    api_client = DeepSeekAPI(config.API_KEY, config.API_URL)
    app = Flask(__name__)
    bot_app = Application.builder().token(config.TOKEN).build()
except Exception as e:
    logger.critical(f"Error de inicialización: {str(e)}")
    raise

# Handlers de Telegram mejorados
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            logger.warning("Mensaje recibido sin contenido")
            await update.message.reply_text("Por favor envía un mensaje de texto.")
            return
            
        logger.info(f"Mensaje recibido de {update.effective_user.id}: {update.message.text}")
        
        response = api_client.query(update.message.text)
        answer = response['choices'][0]['message']['content']
        await update.message.reply_text(answer)
        
    except Exception as e:
        logger.error(f"Error manejando mensaje: {str(e)}", exc_info=True)
        error_msg = (
            "⚠️ Lo siento, hubo un error procesando tu mensaje. "
            "Por favor verifica que tu API key de DeepSeek sea correcta "
            "y que el servicio esté disponible."
        )
        await update.message.reply_text(error_msg)

bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook para Render
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        if request.headers.get('content-type') == 'application/json':
            json_data = request.get_json()
            update = Update.de_json(json_data, bot_app.bot)
            bot_app.update_queue.put(update)
            return '', 200
        return 'Bad Request', 400
    except Exception as e:
        logger.error(f"Error en webhook: {str(e)}", exc_info=True)
        return 'Internal Server Error', 500

@app.route('/')
def health_check():
    return jsonify({
        "status": "active",
        "service": "Telegram Bot",
        "deepseek_status": "configured" if hasattr(app, 'api_client') else "not configured"
    })

# Inicialización mejorada
async def setup_webhook():
    try:
        if config.WEBHOOK_URL:
            webhook_url = f"{config.WEBHOOK_URL}/webhook"
            logger.info(f"Configurando webhook en: {webhook_url}")
            await bot_app.bot.set_webhook(
                url=webhook_url,
                allowed_updates=Update.ALL_TYPES
            )
            logger.info("Webhook configurado exitosamente")
    except Exception as e:
        logger.error(f"Error configurando webhook: {str(e)}", exc_info=True)
        raise

def run():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(setup_webhook())
        
        if config.WEBHOOK_URL:
            from waitress import serve
            logger.info(f"Iniciando servidor web en puerto {config.PORT}")
            serve(app, host="0.0.0.0", port=config.PORT)
        else:
            logger.info("Iniciando bot en modo polling")
            bot_app.run_polling()
    except Exception as e:
        logger.critical(f"Error fatal: {str(e)}", exc_info=True)
    finally:
        loop.close()

if __name__ == '__main__':
    run()
