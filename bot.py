import os
import telebot
from flask import Flask, request
import logging
import requests
import time
from threading import Thread
from urllib.parse import urlparse
import json

# =============================================
# CONFIGURACIÓN INICIAL Y VALIDACIÓN
# =============================================

def validar_url_api(url: str) -> str:
    """Valida y normaliza la URL de la API"""
    url = url.strip().lower()
    
    # Asegurar que comience con https://
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    elif url.startswith('http://'):
        url = url.replace('http://', 'https://')
    
    # Eliminar duplicados de esquema
    url = url.replace('https://https://', 'https://')
    
    # Asegurar versión API
    if not url.endswith('/v1'):
        url = url.rstrip('/') + '/v1'
    
    # Validación final
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            raise ValueError("URL inválida")
        return url
    except Exception as e:
        raise ValueError(f"URL de API inválida: {str(e)}")

# Carga de configuraciones con validación
try:
    TOKEN = os.environ['TELEGRAM_TOKEN']
    DEEPSEEK_API_KEY = os.environ['DEEPSEEK_API_KEY']
    DEEPSEEK_API_URL = validar_url_api(os.getenv('DEEPSEEK_API_URL', 'api.deepseek.com'))
    
    if not TOKEN or not DEEPSEEK_API_KEY:
        raise ValueError("Credenciales esenciales no configuradas")

except (KeyError, ValueError) as e:
    raise SystemExit(f"Error de configuración: {str(e)}")

# =============================================
# INICIALIZACIÓN
# =============================================

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Configuración de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_debug.log')
    ]
)
logger = logging.getLogger(__name__)

# =============================================
# CLASE DE CONEXIÓN API MEJORADA
# =============================================

class DeepSeekConnector:
    @staticmethod
    def verificar_conexion() -> dict:
        """Verifica el estado de conexión con la API"""
        endpoint = f"{DEEPSEEK_API_URL}/models"
        logger.debug(f"Verificando conexión con: {endpoint}")
        
        try:
            start = time.time()
            response = requests.get(
                endpoint,
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
                timeout=15
            )
            latency = round((time.time() - start) * 1000, 2)
            
            if response.status_code == 200:
                return {
                    'conectado': True,
                    'mensaje': '✅ Conexión exitosa',
                    'latencia_ms': latency,
                    'detalles': response.json().get('data', [])[:3]
                }
            else:
                return {
                    'conectado': False,
                    'mensaje': f'❌ Error HTTP {response.status_code}',
                    'error': response.text[:500],
                    'headers': dict(response.headers)
                }
                
        except requests.exceptions.SSLError:
            return {
                'conectado': False,
                'mensaje': '❌ Error SSL - Verifica el certificado',
                'solucion': 'Usa una URL válida con HTTPS'
            }
        except requests.exceptions.Timeout:
            return {
                'conectado': False,
                'mensaje': '❌ Timeout - API no respondió',
                'solucion': 'Revisa tu conexión o aumenta el timeout'
            }
        except requests.exceptions.ConnectionError:
            return {
                'conectado': False,
                'mensaje': f'❌ No se pudo conectar a {DEEPSEEK_API_URL}',
                'solucion': 'Verifica la URL y tu conexión a internet'
            }
        except Exception as e:
            return {
                'conectado': False,
                'mensaje': f'❌ Error inesperado: {type(e).__name__}',
                'error': str(e)
            }

    @staticmethod
    def consultar(pregunta: str) -> dict:
        """Realiza una consulta a la API"""
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Eres un asistente útil en español"},
                    {"role": "user", "content": pregunta}
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": False
            }
            
            headers = {
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.debug(f"Enviando consulta a DeepSeek: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                f"{DEEPSEEK_API_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    'exito': True,
                    'respuesta': response.json(),
                    'latencia_ms': response.elapsed.total_seconds() * 1000
                }
            else:
                return {
                    'exito': False,
                    'error': f"HTTP {response.status_code}",
                    'detalles': response.text[:500]
                }
                
        except requests.exceptions.Timeout:
            return {
                'exito': False,
                'error': "Timeout después de 30 segundos",
                'solucion': "Intenta nuevamente más tarde"
            }
        except Exception as e:
            return {
                'exito': False,
                'error': f"Error inesperado: {type(e).__name__}",
                'detalles': str(e)
            }

# =============================================
# MANEJADORES DE TELEGRAM
# =============================================

@bot.message_handler(commands=['start', 'help', 'adan'])  # Decorador corregido
def enviar_bienvenida(message):
    """Mensaje de bienvenida con diagnóstico completo"""
    conexion = DeepSeekConnector.verificar_conexion()
    
    status_msg = [
        f"*Estado:* {conexion['mensaje']}",
        f"*URL API:* `{DEEPSEEK_API_URL}`"
    ]
    
    if conexion.get('latencia_ms'):
        status_msg.append(f"*Latencia:* {conexion['latencia_ms']} ms")
    
    if not conexion['conectado']:
        if 'solucion' in conexion:
            status_msg.append(f"\\n*Solución:* {conexion['solucion']}")  # Escape correcto de \n
        if 'error' in conexion:
            status_msg.append(f"\\n*Error:* `{conexion['error'][:200]}`")

    # Usamos join() fuera del f-string para evitar problemas
    mensaje_status = "\n".join(status_msg)
    
    welcome_msg = f"""
🤖 *Asistente ADAN con DeepSeek* 🧠

{mensaje_status}

*Cómo usarme:*
- Escribe tu pregunta directamente
- O usa /adan [tu pregunta]
"""
    
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)  # Decorador corregido
def manejar_mensaje(message):
    """Procesa todos los mensajes de texto"""
    if message.text.startswith('/'):
        return
        
    bot.send_chat_action(message.chat.id, 'typing')
    
    if not message.text.strip():
        bot.reply_to(message, "Por favor escribe una pregunta válida")
        return
    
    resultado = DeepSeekConnector.consultar(message.text)
    
    if resultado['exito']:
        try:
            respuesta = resultado['respuesta']['choices'][0]['message']['content']
            tiempo_respuesta = resultado.get('latencia_ms', 0)
            mensaje = (
                f"🧠 *Respuesta:*\n\n{respuesta}\n\n"
                f"⏱ *Tiempo:* {tiempo_respuesta:.0f} ms"
            )
            bot.reply_to(message, mensaje, parse_mode="Markdown")
        except (KeyError, TypeError):
            error_msg = "⚠️ Ocurrió un error al procesar la respuesta"
            logger.error(f"{error_msg}: {json.dumps(resultado.get('respuesta', {}), indent=2)}")
            bot.reply_to(message, f"{error_msg}. Por favor intenta nuevamente.")
    else:
        error_msg = [
            "🔴 *No pude obtener una respuesta*",
            f"*Error:* {resultado['error']}"
        ]
        
        if 'detalles' in resultado:
            error_msg.append(f"*Detalles:* `{resultado['detalles'][:200]}`")
        if 'solucion' in resultado:
            error_msg.append(f"\n*Solución:* {resultado['solucion']}")
        
        bot.reply_to(message, "\n".join(error_msg), parse_mode="Markdown")

# =============================================
# CONFIGURACIÓN DEL SERVIDOR WEB
# =============================================

@app.route('/webhook', methods=['POST'])
def manejar_webhook():
    """Endpoint para webhook de Telegram"""
    try:
        if request.headers.get('content-type') == 'application/json':
            update = telebot.types.Update.de_json(request.get_json())
            bot.process_new_updates([update])
            return '', 200
        return 'Bad request', 400
    except Exception as e:
        logger.error(f"Error en webhook: {str(e)}", exc_info=True)
        return 'Internal Server Error', 500

def configurar_webhook():
    """Configura el webhook con reintentos"""
    max_intentos = 3
    for intento in range(max_intentos):
        try:
            bot.remove_webhook()
            time.sleep(1)
            webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
            bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook configurado en: {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Intento {intento+1} fallido: {str(e)}")
            if intento < max_intentos - 1:
                time.sleep(2)
    
    logger.critical("No se pudo configurar el webhook")
    return False

def iniciar_servidor():
    """Inicia el servidor web"""
    puerto = int(os.getenv('PORT', 10000))
    logger.info(f"Iniciando servidor en puerto {puerto}")
    app.run(
        host='0.0.0.0',
        port=puerto,
        threaded=True,
        debug=False,
        use_reloader=False
    )

# =============================================
# INICIALIZACIÓN PRINCIPAL
# =============================================

if __name__ == '__main__':
    logger.info("="*60)
    logger.info(f"Iniciando Bot ADAN - DeepSeek")
    logger.info(f"URL API: {DEEPSEEK_API_URL}")
    logger.info("="*60)
    
    # Verificación inicial de conexión
    estado = DeepSeekConnector.verificar_conexion()
    logger.info(f"Estado inicial: {json.dumps(estado, indent=2)}")
    
    if os.getenv('RENDER'):
        logger.info("Modo: Producción (Render.com)")
        
        if not configurar_webhook():
            logger.critical("Error crítico al configurar webhook")
            exit(1)
            
        # Iniciar servidor en segundo plano
        servidor = Thread(target=iniciar_servidor)
        servidor.daemon = True
        servidor.start()
        
        logger.info("Servicio iniciado. Esperando mensajes...")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            logger.info("Deteniendo servicio...")
    else:
        logger.info("Modo: Desarrollo (Polling)")
        bot.remove_webhook()
        bot.infinity_polling()
