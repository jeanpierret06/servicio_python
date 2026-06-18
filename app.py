from flask import Flask, request, jsonify
from flask_mail import Mail, Message
from flask_cors import CORS
import mysql.connector 
import os 

app = Flask(__name__)
CORS(app)

# CONFIGURACIÓN DEL SERVIDOR DE CORREO - TOTALMENTE DINÁMICO
app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

# Credenciales extraídas de forma segura desde el entorno de Render
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME') 
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') 

# El remitente DEBE ser tu correo verificado en Brevo para que el servidor acepte el envío
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

mail = Mail(app)

@app.route('/api/enviar-enlace', methods=['POST'])
def enviar_enlace():
    try:
        data = request.get_json()
        email_destino = data.get('email') # <-- Esto lee CUALQUIER correo enviado desde Java
        enlace_recuperacion = data.get('link')

        # El mensaje se envía dinámicamente al correo extraído de la petición
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

# (El resto de tus funciones como get_db_connection() y get_stats() quedan igual)
# Adaptar la conexión para leer Aiven o Localhost automáticamente (CORREGIDO)
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

    # Configuración de SSL compatible con todas las versiones del conector de MySQL
    if db_host != 'localhost':
        config['ssl'] = {}  # Activa SSL seguro para Aiven eliminando ssl_mode

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
        # Asegurar el cierre de conexiones en caso de caída para no bloquear Aiven
        if cursor: cursor.close()
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)