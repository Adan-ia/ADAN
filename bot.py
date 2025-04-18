import telebot
     import replicate

     bot = telebot.TeleBot("7853734167:AAEhM-yMWZt8EHYXYfYTRLJoBtoHk6K3W5g:
     import telebot

bot = telebot.TeleBot("TU_TOKEN_DE_TELEGRAM")  # Reemplaza con tu token real

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "¡Recibí tu mensaje! Prueba exitosa.")

bot.polling()