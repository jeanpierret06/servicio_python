from flask import Flask, request, jsonify
from flask_mail import Mail, Message
from flask_cors import CORS
import mysql.connector 
import os # Permite leer las variables de entorno del servidor

app = Flask(__name__)
CORS(app)

# CONFIGURACIÓN DEL SERVIDOR DE CORREO 
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'manueldiazpena7@gmail.com' 
app.config['MAIL_PASSWORD'] = 'ucfcjsykhwxpubhl' 
app.config['MAIL_DEFAULT_SENDER'] = 'tu-correo@gmail.com'

mail = Mail(app)

@app.route('/api/enviar-enlace', methods=['POST'])
def enviar_enlace():
    try:
        data = request.get_json()
        email_destino = data.get('email')
        enlace_recuperacion = data.get('link')

        msg = Message('Restablecer Acceso - Compuedu', recipients=[email_destino])
        
        msg.html = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
            <div style="background-color: #343a40; padding: 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Compuedu</h1>
            </div>
            <div style="padding: 30px; background-color: #ffffff; line-height: 1.6;">
                <h2 style="color: #333333;">Hola,</h2>
                <p style="color: #666666; font-size: 16px;">
                    Has solicitado restablecer tu contraseña para acceder a nuestra plataforma académica. 
                    No te preocupes, estamos aquí para ayudarte.
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{enlace_recuperacion}" 
                       style="background-color: #343a40; color: #ffffff; padding: 15px 25px; text-decoration: none; border-radius: 50px; font-weight: bold; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                       Restablecer Contraseña
                    </a>
                </div>
                <p style="color: #888888; font-size: 13px;">
                    Si no solicitaste este cambio, puedes ignorar este correo de forma segura. El enlace expirará pronto.
                </p>
            </div>
            <div style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #999999;">
                &copy; 2026 Compuedu - Herramientas Académicas.
            </div>
        </div>
        """
        
        mail.send(msg)
        return jsonify({"status": "success", "message": "Correo enviado correctamente"}), 200

    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# [CORRECCIÓN CRÍTICA]: Adaptar la conexión para leer Aiven o Localhost automáticamente
def get_db_connection():
    # Intenta leer las credenciales de producción de Aiven, si no existen usa los valores locales
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = int(os.environ.get('DB_PORT', 3306))
    db_user = os.environ.get('DB_USER', 'root')
    db_password = os.environ.get('DB_PASSWORD', '')
    db_name = os.environ.get('DB_NAME', 'compuedu')

    # Configuración de los parámetros base de conexión
    config = {
        'host': db_host,
        'port': db_port,
        'user': db_user,
        'password': db_password,
        'database': db_name
    }

    # Si no es localhost, significa que estamos conectándonos a Aiven y se requiere SSL obligatorio
    if db_host != 'localhost':
        config['ssl_disabled'] = False
        # Le indicamos a mysql.connector que use el modo de verificación SSL requerido
        config['ssl_mode'] = 'REQUIRED'

    return mysql.connector.connect(**config)


@app.route('/api/stats/institucion/<int:creador_id>', methods=['GET'])
def get_stats(creador_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Distribución por estado
        query_estados = "SELECT estado, COUNT(*) as cantidad FROM convocatorias WHERE creador_id = %s GROUP BY estado"
        cursor.execute(query_estados, (creador_id,))
        distribucion = cursor.fetchall()
        
        # 2. Alertas de vencimiento
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
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Lee el puerto dinámico de Render o usa el 5000 por defecto en desarrollo local
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)