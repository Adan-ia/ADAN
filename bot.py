import telebot

bot = telebot.TeleBot("7853734167:AAEhM-yMWZt8EHYXYfYTRLJoBtoHk6K3W5g")  # ¡Pega tu token real aquí!

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "¡Funcionando en la nube! 🚀")

bot.polling()
