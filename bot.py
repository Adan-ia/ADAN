import os
import telebot
import replicate

bot = telebot.TeleBot(os.environ['TOKEN_TELEGRAM'])

@bot.message_handler(func=lambda m: True)
def responder(m):
    output = replicate.run(
        "meta/llama-3-70b-instruct",
        input={"prompt": f"Eres J.A.R.V.I.S. Responde como mentor técnico. Pregunta: {m.text}"}
    )
    bot.reply_to(m, output[0])

if __name__ == "__main__":
    print("⚡ Bot iniciado")
    bot.polling()
