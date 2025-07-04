from apps.clients import blueprint
from flask import render_template, request, jsonify,send_file
from flask_login import login_required
from bson import ObjectId
from apps import mongo
from apps.clients.models import Clients
from cerberus import Validator
import requests
import pandas as pd




       
def traducir_errores(errors):
    mensajes = []

    for campo, errores_campo in errors.items():
        for error in errores_campo:
            if "min length" in error:
                mensajes.append(f"'{campo}' debe tener al menos {error.split()[-1]} caracteres.")
            elif "regex" in error:
                if campo == 'phone' or campo == 'dni':
                    mensajes.append(f"'{campo}' solo debe contener números.")
                elif campo == 'email':
                    mensajes.append(f"'{campo}' debe ser un correo electrónico válido.")
                else:
                    mensajes.append(f"'{campo}' tiene un formato inválido.")
            elif "required field" in error:
                mensajes.append(f"El campo '{campo}' es obligatorio.")
            elif "empty values not allowed" in error:
                mensajes.append(f"El campo '{campo}' no puede estar vacío.")
            elif "min value" in error:
                mensajes.append(f"'{campo}' debe ser mayor o igual a {error.split()[-1]}.")
            else:
                mensajes.append(f"Error en el campo '{campo}': {error}")

    return mensajes

client_schema = {
    'first_name': {
        'type': 'string', 'minlength': 2, 'required': True, 'empty': False,
    },
    'second_name': {
        'type': 'string', 'minlength': 0, 'required': False,
    },
    'first_last_name': {
        'type': 'string', 'minlength': 2, 'required': True, 'empty': False,
    },
    'second_last_name': {
        'type': 'string', 'minlength': 0, 'required': False,
    },
    'dni': {
        'type': 'string', 'regex': '^[0-9]+$', 'required': False, 'empty': True,
    },
    'addres': {
        'type': 'string', 'minlength': 3, 'required': False,
    },
    'phone': {
        'type': 'string', 'minlength': 7, 'regex': '^[0-9]+$', 'required': True, 'empty': False,
    },
    'email': {
        'type': 'string', 'regex': r'^\S+@\S+\.\S+$', 'required': True, 'empty': False,
    },
    "age": {"nullable": True, "required": False},

    'medicall_info': {
        'type': 'string', 'required': False,
    },
}

@blueprint.route('/list_clients')
@login_required
def list_clients():
    return render_template('clients/list_clients.html',segment='estudiante')

@blueprint.route("/dataClients", methods=["GET"])
@login_required
def dataClients():
    clients = Clients.find_all()

    data_json = [
        {
            'id': str(item["_id"]),
            'names': item['first_name'] + " " + item['second_name'],
            'surnames': item['first_last_name'] + " " + item['second_last_name'],
            'document': item['dni'],
            'age': item['age'],
            'addres': item['addres'],
            'phone': item['phone'],
            'state': 'activado' if item['state'] else 'desactivado',
            'medicall_info': item['medicall_info'],
            'email': item['email'],
        } for item in clients
    ]

    return jsonify({'data': data_json})


@blueprint.route('/create_client', methods=['POST'])
@login_required
def create_client():
    data = request.get_json()

    # Validar si existe cliente con el mismo email
    existing_client_email = Clients.find_by_email(data.get('email'))
    if existing_client_email:
        return jsonify({'tipo': "error", 'message': 'Ya existe un cliente con ese email'}), 400

    # Validar si existe cliente con el mismo dni
    dni = data.get('dni')
    if dni:
        existing_client_dni = mongo.db.clients.find_one({'dni': dni})
        if existing_client_dni:
            return jsonify({'tipo': "error", 'message': 'Ya existe un cliente con esa identificación (DNI)'}), 400

    client = Clients(**data)
    client.save()

    return jsonify({'tipo': "success", 'message': 'Cliente creado correctamente'}), 200



@blueprint.route('/get_customer/<id>', methods=['GET'])
@login_required
def get_customer(id):
    client = mongo.db.clients.find_one({"_id": ObjectId(id)})

    if client:
        client["_id"] = str(client["_id"])  # Convertir ObjectId a string
        return jsonify(client)

    return jsonify({'error': 'Cliente no encontrado'}), 404

@blueprint.route('/edit_customer', methods=['POST'])
@login_required
def edit_customer():
    data = request.get_json()
    client_id = data.pop("id", None)

    if not client_id:
        return jsonify({'tipo': 'error', 'message': 'ID no proporcionado'}), 400

    # Validación parcial (no requiere todos los campos)
    partial_schema = {key: {**value, 'required': False} for key, value in client_schema.items()}
    v = Validator(partial_schema)
    if not v.validate(data):
        errores = traducir_errores(v.errors)
        return jsonify({'tipo': 'error', 'message': 'Datos inválidos', 'errores': errores}), 400

    Clients.update_client(ObjectId(client_id), data)

    return jsonify({'tipo': 'success', 'message': 'Cliente actualizado correctamente'})


@blueprint.route('/edit_state_client', methods=['POST'])
@login_required
def edit_state_client():
    try:
        data = request.form
        client_id = data.get('id')
        state = data.get('state')

        if not client_id or state not in ["0", "1"]:
            return jsonify({'tipo': 'error', 'message': 'Datos inválidos'}), 400

        state_value = True if state == "1" else False
        Clients.update_client(ObjectId(client_id), {"state": state_value})

        return jsonify({'tipo': 'success', 'message': f"Cliente {'activado' if state_value else 'desactivado'} correctamente"})
    
    except Exception as e:
        return jsonify({'tipo': 'error', 'message': str(e)}), 400


@blueprint.route('/webhook', methods=['GET'])
def verificar_token():
    # print(request)
    try:
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        print(token,"   ",challenge)
        # if token == "bigdateros" and challenge != None:
        # print("entro",WEBHOOK_TOKEN)
        return challenge
        # else:
        #     return 'token incorrecto', 403
    except Exception as e:
        print(e)
        return e,403


import websocket
import json
import threading
from urllib.parse import urlparse
from datetime import datetime, timedelta

WHATSAPP_TOKEN = "EAANk3r9coXsBOZCBvvRROZCZBLZBdVEPuGs3x05sSg9cpO9gRavbGSaBHElN2Un1lFeUQZCmg4Jz03qbgqXBeodrOyzkno1LKm5WwUOhKvvJ5MZBB0LZCf7pMNdCvbrSgZB3fEf3i9QQLgs777Pk6CuQRXaPZCxVossuhmwqwqFoPPJz1st1t1vNMdNtxmoZCv26lHZA1FXqkwUk9chStaw"
WHATSAPP_SEND_MESSAGE_URL = "https://graph.facebook.com/v20.0/268918076304714/messages"

# Diccionario para almacenar conversaciones activas por usuario
active_conversations = {}

class UserConversation:
    def __init__(self, user_id, conversation_id, token, expires_in, stream_url):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.token = token
        self.stream_url = stream_url
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # 1 minuto de buffer
        self.websocket = None
        self.watermark = None
        
    def is_expired(self):
        return datetime.now() > self.expires_at
    
    def refresh_token(self, new_token, expires_in):
        """Actualizar token cuando se renueva"""
        self.token = new_token
        self.expires_at = datetime.now() + timedelta(seconds=expires_in - 60)

def create_or_get_conversation(user_id, user_name):
    """Crear nueva conversación o obtener una existente"""
    
    # Verificar si ya existe una conversación activa para este usuario
    if user_id in active_conversations:
        conversation = active_conversations[user_id]
        
        # Si la conversación no ha expirado, reutilizarla
        if not conversation.is_expired():
            print(f"Reutilizando conversación existente para {user_id}: {conversation.conversation_id}")
            return conversation
        else:
            # Si expiró, intentar renovar el token
            print(f"Conversación expirada para {user_id}, intentando renovar...")
            renewed_conversation = renew_conversation_token(conversation)
            if renewed_conversation:
                return renewed_conversation
            else:
                # Si no se puede renovar, eliminar la conversación expirada
                print(f"No se pudo renovar, eliminando conversación expirada para {user_id}")
                del active_conversations[user_id]
    
    # Crear nueva conversación
    print(f"Creando nueva conversación para {user_id}")
    return create_new_conversation(user_id, user_name)

def create_new_conversation(user_id, user_name):
    """Crear una nueva conversación en Direct Line"""
    direct_line_secret = "1i8qbDxKds0nkteopPjR55k7ewIZza5BZlzkjyGpjnJ4JuGm3HNAJQQJ99BCACYeBjFAArohAAABAZBS2rnE.2xgQCZ3cksVNd9BvrpeR3Rncc5LYmMsOl6ljGW7AQT2ZuATDJAHdJQQJ99BCACYeBjFAArohAAABAZBS2FyG"
    direct_line_url = "https://directline.botframework.com/v3/directline/conversations"
    
    headers = {
        'Authorization': f'Bearer {direct_line_secret}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(direct_line_url, headers=headers, timeout=30)
        
        if response.status_code in [200, 201]:
            data = response.json()
            conversation = UserConversation(
                user_id=user_id,
                conversation_id=data['conversationId'],
                token=data['token'],
                expires_in=data['expires_in'],
                stream_url=data.get('streamUrl', '')
            )
            
            # Almacenar la conversación
            active_conversations[user_id] = conversation
            
            # Iniciar WebSocket para esta conversación
            if conversation.stream_url:
                start_websocket_for_user(conversation)
            
            print(f"Nueva conversación creada: {conversation.conversation_id}")
            return conversation
        else:
            print(f"Error al crear conversación: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error creando conversación: {str(e)}")
        return None

def renew_conversation_token(conversation):
    """Renovar el token de una conversación existente"""
    renew_url = f"https://directline.botframework.com/v3/directline/tokens/refresh"
    
    headers = {
        'Authorization': f'Bearer {conversation.token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(renew_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            conversation.refresh_token(data['token'], data['expires_in'])
            print(f"Token renovado para conversación: {conversation.conversation_id}")
            return conversation
        else:
            print(f"Error renovando token: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error renovando token: {str(e)}")
        return None

def send_message_to_bot(conversation, message_text, user_name):
    """Enviar mensaje al bot usando una conversación existente"""
    send_message_url = f"https://directline.botframework.com/v3/directline/conversations/{conversation.conversation_id}/activities"
    
    message_payload = {
        "locale": "es-ES",
        "type": "message",
        "from": {
            "id": conversation.user_id,
            "name": user_name
        },
        "text": message_text
    }
    
    headers = {
        'Authorization': f'Bearer {conversation.token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            send_message_url,
            json=message_payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"Mensaje enviado exitosamente. ID: {result.get('id')}")
            return True
        else:
            print(f"Error enviando mensaje: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error enviando mensaje: {str(e)}")
        return False

def start_websocket_for_user(conversation):
    """Iniciar WebSocket específico para una conversación de usuario"""
    def run_websocket():
        def on_message(ws, message):
            on_websocket_message_for_user(ws, message, conversation.user_id)
        
        def on_error(ws, error):
            print(f"Error WebSocket para {conversation.user_id}: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print(f"WebSocket cerrado para {conversation.user_id}")
        
        def on_open(ws):
            print(f"WebSocket abierto para {conversation.user_id}")
        
        ws = websocket.WebSocketApp(
            conversation.stream_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        conversation.websocket = ws
        ws.run_forever()
    
    websocket_thread = threading.Thread(target=run_websocket)
    websocket_thread.daemon = True
    websocket_thread.start()

def on_websocket_message_for_user(ws, message, user_id):
    """Callback específico para mensajes de WebSocket por usuario"""
    try:
        data = json.loads(message)
        print(f"Mensaje recibido para {user_id}: {data}")
        
        if 'activities' in data:
            for activity in data['activities']:
                if activity.get('type') == 'message' and activity.get('from', {}).get('id') != user_id:
                    bot_message = activity.get('text', '')
                    if bot_message:
                        print(f"Respuesta del bot para {user_id}: {bot_message}")
                        
                        # Obtener número de WhatsApp del usuario
                        if user_id in active_conversations:
                            whatsapp_number = get_whatsapp_number_from_user_id(user_id)
                            if whatsapp_number:
                                whatsapp_data = text_Message(whatsapp_number, bot_message)
                                result = enviar_Mensaje_whatsapp(whatsapp_data)
                                print(f"Resultado envío WhatsApp para {user_id}: {result}")
                    
    except json.JSONDecodeError as e:
        print(f"Error parseando mensaje WebSocket para {user_id}: {e}")

def get_whatsapp_number_from_user_id(user_id):
    """Convertir user_id de vuelta a número de WhatsApp"""
    # Asumiendo que user_id es el número sin prefijo, agregar el prefijo
    return f"57{user_id}"

@blueprint.route('/webhook', methods=['POST'])
def recibir_mensajes():
    try:
        body = request.get_json()
        print(f"Webhook recibido: {body}")
        
        # Validar estructura del mensaje de WhatsApp
        if not body or 'entry' not in body:
            return jsonify({'status': 'ignored', 'message': 'No es un mensaje válido de WhatsApp'}), 200
        
        entry = body.get('entry', [])
        if not entry:
            return jsonify({'status': 'ignored', 'message': 'Entry vacío'}), 200
            
        first_entry = entry[0]
        changes = first_entry.get('changes', [])
        if not changes:
            return jsonify({'status': 'ignored', 'message': 'Changes vacío'}), 200
            
        first_change = changes[0]
        value = first_change.get('value', {})
        
        if 'messages' not in value:
            return jsonify({'status': 'ignored', 'message': 'No es un mensaje entrante'}), 200
            
        messages = value['messages']
        if not messages:
            return jsonify({'status': 'ignored', 'message': 'Lista de mensajes vacía'}), 200
            
        message = messages[0]
        type = message.get('type', '')
        number = message.get('from', '')
        number_without_prefix = number.replace('57', '', 1) if number else ''
        
        contacts = value.get('contacts', [])
        if not contacts:
            return jsonify({'status': 'ignored', 'message': 'No hay información de contacto'}), 200
            
        name = contacts[0].get('profile', {}).get('name', '')
        
        message_body = ""
        if type == "text" and "text" in message and "body" in message['text']:
            message_body = message['text']['body']
        
        print(f"Procesando mensaje de {name} ({number}): {message_body}")
        
        # Obtener o crear conversación para este usuario
        conversation = create_or_get_conversation(number_without_prefix, name)
        
        if not conversation:
            return jsonify({
                'status': 'error',
                'message': 'No se pudo crear o obtener conversación'
            }), 500
        
        # Enviar mensaje al bot usando la conversación existente
        success = send_message_to_bot(conversation, message_body, name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Mensaje enviado al bot exitosamente',
                'conversation_id': conversation.conversation_id,
                'user_id': number_without_prefix
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Error al enviar mensaje al bot'
            }), 500
            
    except Exception as e:
        print(f"Error general: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error al procesar el webhook',
            'error': str(e)
        }), 500

# Mantener las funciones existentes
def enviar_Mensaje_whatsapp(data):
    try:
        whatsapp_token = WHATSAPP_TOKEN
        whatsapp_url = WHATSAPP_SEND_MESSAGE_URL
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + whatsapp_token}
        print("se envia ", data)
        response = requests.post(whatsapp_url, 
                                 headers=headers, 
                                 data=data)
        
        if response.status_code == 200:
            return 'mensaje enviado', 200
        else:
            print(response.text)
            return 'error al enviar mensaje', response.status_code
            
    except Exception as e:
        print(e)
        return e, 403

def text_Message(number, text):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",    
            "recipient_type": "individual",
            "to": number,
            "type": "text",
            "text": {
                "body": text
            }
        }
    )
    return data




