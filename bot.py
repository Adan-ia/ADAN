import os
from flask import Flask, request
import telebot

app = Flask(__name__)
TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TOKEN:
    raise RuntimeError("Token no configurado")

bot = telebot.TeleBot(TOKEN)

# Handler básico
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "¡Hola! Estoy funcionando correctamente.")

# Webhook para producción
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.method == "POST":
        json_data = request.get_json()
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
    return "OK", 200

if __name__ == '__main__':
    # Configuración para Render
    if os.getenv('RENDER'):
        bot.remove_webhook()
        bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
        app.run(host='0.0.0.0', port=10000)
    else:
        # Para desarrollo local
        bot.polling()
