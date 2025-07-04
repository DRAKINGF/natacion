# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.index import blueprint
from flask import render_template, request,redirect,url_for,jsonify
from flask_login import login_required
from jinja2 import TemplateNotFound


@blueprint.route('/')
def index():

    return render_template('index/index.html',segment='index')



@blueprint.route('/prueba', methods=['POST', 'GET'])
def prueba():
    print("📩 Solicitud recibida")

    try:
        # Intentar leer el cuerpo como JSON aunque no tenga el Content-Type correcto
        data = request.get_json(force=True)
        print("✅ JSON recibido correctamente:", data)
    except Exception as e:
        # Si no se pudo leer como JSON, mostrar el cuerpo crudo
        raw_data = request.data.decode('utf-8', errors='replace')
        print(f"❌ Error al procesar JSON: {str(e)}")
        print("📦 Cuerpo recibido (raw):", raw_data)
        return jsonify({
            "reply": f"Error: contenido no válido como JSON.",
            "debug_raw_body": raw_data
        }), 400

    # Verificar campos
    expected_keys = ["app", "sender", "message", "group_name", "phone"]
    missing_keys = [key for key in expected_keys if key not in data]

    if missing_keys:
        print(f"❌ Faltan los campos: {missing_keys}")
        return jsonify({"reply": f"Error: faltan los campos {missing_keys}"}), 400

    # Imprimir datos correctamente recibidos
    print("✅ Todos los campos presentes:")
    for key in expected_keys:
        print(f"  {key}: {data[key]}")

    respuesta = "Hola, recibimos tu mensaje correctamente."
    return jsonify({"reply": respuesta})
