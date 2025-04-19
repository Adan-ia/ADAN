from flask import Flask, request
import telebot
import os

# Configuración inicial
app = Flask(__name__)
TOKEN = os.getenv('7853734167:AAEhM-yMWZt8EHYXYfYTRLJoBtoHk6K3W5g')  # Usa variables de entorno para el token
bot = telebot.TeleBot(TOKEN)

# Ruta para el webhook (opcional, depende de tu configuración)
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_update = request.stream.read().decode('utf-8')
    update = telebot.types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return "!", 200

# Comandos del bot
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hola, soy tu bot!")

# Manejo de errores
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    try:
        bot.reply_to(message, message.text)
    except Exception as e:
        print(f"Error: {e}")

# Inicio de la aplicación
if __name__ == '__main__':
    # Elimina cualquier webhook previo para evitar conflictos
    bot.remove_webhook()
    
    # Configuración para Render
    PORT = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=PORT)
