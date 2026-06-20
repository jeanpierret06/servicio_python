from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector 
import os 
from threading import Thread
# Importaciones oficiales del SDK de Brevo
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

app = Flask(__name__)
CORS(app)

# CONFIGURACIÓN DEL SDK DE BREVO (OPCIÓN B: SEGURA POR VARIABLES DE ENTORNO)
configuration = sib_api_v3_sdk.Configuration()
# Lee tu llave 'xkeysib-...' directamente desde las variables de Render
configuration.api_key['api-key'] = os.environ.get('MAIL_PASSWORD')

# Instancia el cliente de correos transaccionales de Brevo
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))


def send_async_brevo_email(email_destino, enlace_recuperacion, sender_email):
    """Ejecuta el envío del correo transaccional utilizando el SDK oficial en segundo plano."""
    try:
        # Definición del contenido del correo
        html_content = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
            <div style="background-color: #343a40; padding: 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Compuedu</h1>
            </div>
            <div style="padding: 30px; background-color: #ffffff; line-height: 1.6;">
                <h2 style="color: #333333;">Hola,</h2>
                <p style="color: #666666; font-size: 16px;">
                    Has solicitado restablecer tu contraseña para acceder a nuestra plataforma académica. 
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{enlace_recuperacion}" 
                       style="background-color: #343a40; color: #ffffff; padding: 15px 25px; text-decoration: none; border-radius: 50px; font-weight: bold; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        Restablecer Contraseña
                    </a>
                </div>
                <p style="color: #888888; font-size: 13px;">
                    Si no solicitaste este cambio, puedes ignorar este correo de forma segura.
                </p>
            </div>
        </div>
        """

        # Estructura requerida por el objeto de Brevo
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": email_destino}],
            sender={"name": "Compuedu", "email": sender_email},
            subject="Restablecer Acceso - Compuedu",
            html_content=html_content
        )

        # Envío a través de la API
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(f"DEBUG BREVO API: Correo enviado con éxito. ID: {api_response.message_id}")

    except ApiException as e:
        print(f"DEBUG ERROR BREVO API: Fallo al enviar a través del SDK: {e}")
    except Exception as e:
        print(f"DEBUG ERROR HILO: {str(e)}")


@app.route('/api/enviar-enlace', methods=['POST'])
def enviar_enlace():
    try:
        data = request.get_json()
        email_destino = data.get('email') 
        enlace_recuperacion = data.get('link')

        if not email_destino or not enlace_recuperacion:
            return jsonify({"status": "error", "message": "Faltan parámetros obligatorios: email o link"}), 400

        sender_email = os.environ.get('MAIL_DEFAULT_SENDER')
        if not sender_email:
            return jsonify({"status": "error", "message": "Falta configurar la variable MAIL_DEFAULT_SENDER en Render"}), 500

        # Dispara el hilo asíncrono con el nuevo método del SDK
        thr = Thread(target=send_async_brevo_email, args=[email_destino, enlace_recuperacion, sender_email])
        thr.start()
        
        return jsonify({"status": "success", "message": "Proceso de envío iniciado"}), 200

    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    

def get_db_connection():
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = int(os.environ.get('DB_PORT', 3306))
    db_user = os.environ.get('DB_USER', 'root')
    db_password = os.environ.get('DB_PASSWORD', '')
    db_name = os.environ.get('DB_NAME', 'compuedu')

    config = {
        'host': db_host,
        'port': db_port,
        'user': db_user,
        'password': db_password,
        'database': db_name
    }
    return mysql.connector.connect(**config)


@app.route('/api/stats/institucion/<int:creador_id>', methods=['GET'])
def get_stats(creador_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query_estados = "SELECT estado, COUNT(*) as cantidad FROM convocatorias WHERE creador_id = %s GROUP BY estado"
        cursor.execute(query_estados, (creador_id,))
        distribucion = cursor.fetchall()
        
        query_urgentes = "SELECT titulo, DATEDIFF(fecha_fin, CURDATE()) as dias_restantes FROM convocatorias WHERE creador_id = %s AND fecha_fin > CURDATE() ORDER BY dias_restantes ASC LIMIT 3"
        cursor.execute(query_urgentes, (creador_id,))
        urgentes = cursor.fetchall()

        cursor.close()
        conn.close()
        
        return jsonify({
            "distribucion_estado": distribucion,
            "urgentes": urgentes
        })
    except Exception as e:
        print(f"Error en stats: {e}")
        if cursor: cursor.close()
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
