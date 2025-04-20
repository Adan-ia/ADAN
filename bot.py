import os
import logging
from typing import Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import asyncio

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        self.TOKEN = os.getenv('TELEGRAM_TOKEN')
        self.API_KEY = os.getenv('DEEPSEEK_API_KEY')
        self.PORT = int(os.getenv('PORT', 8000))
        self.WEBHOOK_URL = os.getenv('WEBHOOK_URL')

class DeepSeekAPI:
    def __init__(self, api_key: str):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        self.base_url = 'https://api.deepseek.com/v1'

    def query(self, prompt: str) -> Dict[str, Any]:
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API Error: {str(e)}")
            raise

# Inicialización
config = Config()
api_client = DeepSeekAPI(config.API_KEY)
app = Flask(__name__)
bot_app = Application.builder().token(config.TOKEN).build()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = api_client.query(update.message.text)
        answer = response['choices'][0]['message']['content']
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text("⚠️ Error procesando tu mensaje")

bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_data = request.get_json()
        update = Update.de_json(json_data, bot_app.bot)
        bot_app.update_queue.put(update)
        return '', 200
    return 'Bad Request', 400

@app.route('/')
def health_check():
    return jsonify({"status": "active"})

async def setup_webhook():
    if config.WEBHOOK_URL:
        await bot_app.bot.set_webhook(
            url=f"{config.WEBHOOK_URL}/webhook",
            allowed_updates=Update.ALL_TYPES
        )

def run():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_webhook())
    
    from waitress import serve
    serve(app, host="0.0.0.0", port=config.PORT)

if __name__ == '__main__':
    run()
