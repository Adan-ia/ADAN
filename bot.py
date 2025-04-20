import os
import telebot
from flask import Flask, request

# Configuración inicial
TOKEN = os.getenv('TELEGRAM_TOKEN')  # Asegúrate de tener esta variable en Render
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Comando básico de ejemplo
@bot.message_handler(commands=['adan'])
def send_welcome(message):
    pregunta = message.text.split('/adan ')[1] if len(message.text.split()) > 1 else ""
    respuesta = f"Recibí tu pregunta: {pregunta}. Esto es un ejemplo de respuesta."
    bot.reply_to(message, respuesta)

# Configuración para Render (Webhook)
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Bad request', 403

def setup_webhook():
    bot.remove_webhook()  # Limpiar webhooks anteriores
    # Asegúrate de reemplazar con tu URL real en Render
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    bot.set_webhook(url=webhook_url)
    print(f"Webhook configurado en: {webhook_url}")

# Configuración para desarrollo local (Polling)
def setup_polling():
    bot.remove_webhook()
    print("Iniciando bot en modo polling...")
    bot.polling()

# Determinar el modo de ejecución
if __name__ == '__main__':
    if os.getenv('RENDER'):  # Si estamos en Render
        setup_webhook()
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
    else:  # Si estamos en desarrollo local
        setup_polling()
