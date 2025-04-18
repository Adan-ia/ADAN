import telebot
import replicate

bot = telebot.TeleBot("7853734167:AAEhM-yMWZt8EHYXYfYTRLJoBtoHk6K3W5g")

@bot.message_handler(func=lambda m: True)
def responder(m):
    respuesta = replicate.run(
        "meta/llama-3-70b-instruct",
        input={
            "prompt": f"Eres A.D.A.N. Responde a Adam con estilo técnico y cercano. Pregunta: {m.text}",
            "max_tokens": 150
        }
    )
    bot.reply_to(m, respuesta[0])

bot.polling()
