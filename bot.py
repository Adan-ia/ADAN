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


from flask import Flask
   app = Flask(__name__)

   @app.route('/')
   def home():
       return "Bot activo (ignorar este mensaje)", 200

   if __name__ == "__main__":
       import threading
       threading.Thread(target=bot.polling).start()
       app.run(host='0.0.0.0', port=10000)
