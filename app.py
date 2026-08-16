# -*- coding: utf-8 -*-
import io, os, requests
from flask import Flask, request, send_file, jsonify
from render_orden import render_orden
from render_factura import render_factura

app = Flask(__name__)

CAMPOS = ["cliente", "direccion", "telefono", "fecha", "hora", "servicio"]
CAMPOS_FACTURA = [
    "fecha", "cliente", "telefono", "direccion", "equipo", "tecnico",
    "servicio", "concepto", "valor", "total", "garantia", "vence_garantia",
]

# Credenciales de WhatsApp Cloud API (se configuran como variables de entorno en Render,
# NO se escriben aqui en el codigo por seguridad).
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
WHATSAPP_API_VERSION = "v21.0"

@app.get("/")
def home():
    return "Render Orden de Servicio - Técnicos del Poblado: OK"

@app.get("/orden")
def orden():
    d = {k: (request.args.get(k, "") or "").replace("|", "\n") for k in CAMPOS}
    png = render_orden(d)
    return send_file(io.BytesIO(png), mimetype="image/png", download_name="orden-servicio.png")

@app.get("/factura")
def factura():
    d = {k: (request.args.get(k, "") or "").replace("|", "\n") for k in CAMPOS_FACTURA}
    png = render_factura(d)
    return send_file(io.BytesIO(png), mimetype="image/png", download_name="factura.png")

@app.get("/enviar-factura")
def enviar_factura():
    """
    Envia una imagen (por ejemplo la factura o la orden de servicio) directamente
    al WhatsApp del cliente usando la API de Meta.
    Parametros por query string:
      - to: numero del cliente, solo digitos con codigo de pais (ej: 573001234567)
      - imagen_url: URL publica de la imagen a enviar (ej: la URL de /factura)
    """
    to = (request.args.get("to", "") or "").strip()
    imagen_url = (request.args.get("imagen_url", "") or "").strip()

    if not to or not imagen_url:
        return jsonify({"ok": False, "error": "Faltan parametros 'to' o 'imagen_url'"}), 400
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return jsonify({"ok": False, "error": "Faltan variables de entorno WHATSAPP_TOKEN / WHATSAPP_PHONE_ID en Render"}), 500

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {"link": imagen_url},
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        data = r.json()
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    ok = r.status_code == 200
    return jsonify({"ok": ok, "status": r.status_code, "respuesta": data}), (200 if ok else 502)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
