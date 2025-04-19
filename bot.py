import os
from flask import Flask
import telebot

# 1. Verificación robusta del token
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

if not TELEGRAM_TOKEN:
    print("❌ ERROR CRÍTICO: Token no encontrado")
    print("Solución:")
    print("1. Ve a Render → Tu servicio → Environment")
    print("2. Añade variable 'TELEGRAM_TOKEN'")
    print("3. Pega tu token de @BotFather")
    raise RuntimeError("Configura el token como variable de entorno")

# 2. Inicialización segura
app = Flask(__name__)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@app.route('/')
def home():
    return "¡Bot operativo!"

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "¡Funcionando correctamente!")

if __name__ == '__main__':
    # Configuración óptima para Render
    PORT = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=PORT)
