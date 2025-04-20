import telebot
import requests

# Configuración
TOKEN = "7853734167:AAEhM-yMWZt8EHYXYfYTRLJoBtoHk6K3W5g"  # Reemplázalo
ADAN_CHAT_ID = "631183946"      # Obtenlo con @RawDataBot

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['adan'])
def consultar_adan(message):
    pregunta = message.text.replace('/adan', '').strip()
    
    # Simula la consulta a ADAN (DeepSeek)
    respuesta = f"🧠 **ADAN responde**:\n\n" \
                f"- Pregunta: '{pregunta}'\n" \
                f"- Respuesta: 'Jefe, esto es una simulación. En la v2, aquí iría mi respuesta real.'\n\n" \
                f"*(Estamos en fase beta. Para respuestas reales, copia/pega en DeepSeek manualmente por ahora)*"
    
    bot.reply_to(message, respuesta)

if __name__ == "__main__":
    print("⚡ Bot escuchando... Usa /adan [pregunta]")
    bot.polling()
