# -*- coding: utf-8 -*-
import io, os, requests
from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
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
WHATSAPP_TEMPLATE_NAME = "factura_servicio"
WHATSAPP_TEMPLATE_LANG = "es_CO"

# Airtable (para recibir solicitudes desde la pagina web).
AIRTABLE_TOKEN = os.environ.get("AIRTABLE_TOKEN", "")
AIRTABLE_BASE_ID = "appo1SZqj8heuR6z0"
AIRTABLE_TABLA_CLIENTES = "tblArYxaTHwB6MjZi"
# IDs de los campos de la tabla Clientes.
F_NOMBRE = "fldcQJCU3BxTM8qEd"
F_WHATSAPP = "fldTjPFqz2WvlzL5D"
F_BARRIO = "fldKJADhr3nBstWOW"
F_DIRECCION = "fldLFDSNVPgdDvPoH"
F_QUE_NECESITA = "fld1Oo2ySeODDnAj5"
F_ELECTRODOMESTICO = "fldxqnIX7JfDeTAlY"

ELECTRODOMESTICOS_VALIDOS = [
    "Lavadora", "Nevera", "Calentador", "Aire acondicionado",
    "Secadora", "Estufa", "Otro",
]


@app.after_request
def _cors(resp):
    """Permite que la pagina web (en otro dominio) llame a este servidor."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.route("/solicitud", methods=["POST", "OPTIONS"])
def solicitud():
    """
    Recibe una solicitud de servicio desde la pagina web y crea el
    registro en la tabla Clientes de Airtable.
    Espera JSON con: nombre, telefono, electrodomestico, barrio, mensaje.
    """
    if request.method == "OPTIONS":
        return ("", 204)

    if not AIRTABLE_TOKEN:
        return jsonify({"ok": False, "error": "Falta la variable AIRTABLE_TOKEN en Render"}), 500

    d = request.get_json(silent=True) or {}
    nombre = (d.get("nombre") or "").strip()
    telefono = (d.get("telefono") or "").strip()
    electro = (d.get("electrodomestico") or "").strip()
    barrio = (d.get("barrio") or "").strip()
    mensaje = (d.get("mensaje") or "").strip()

    if not nombre or not telefono:
        return jsonify({"ok": False, "error": "Nombre y telefono son obligatorios"}), 400

    fields = {F_NOMBRE: nombre, F_WHATSAPP: telefono}
    if barrio:
        fields[F_BARRIO] = barrio
    if mensaje:
        fields[F_QUE_NECESITA] = mensaje
    if electro in ELECTRODOMESTICOS_VALIDOS:
        fields[F_ELECTRODOMESTICO] = electro

    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLA_CLIENTES}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(url, headers=headers, json={"records": [{"fields": fields}]}, timeout=20)
        data = r.json()
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    if r.status_code in (200, 201):
        return jsonify({"ok": True}), 200
    return jsonify({"ok": False, "error": data}), 502

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

def _comprobante_png(ok, detalle):
    """
    Genera una imagen pequeña de comprobante (verde=enviado, rojo=error).
    Se usa como respuesta de /enviar-factura para que Airtable pueda
    adjuntarla vía 'attachment by URL' y así quede registro visual del envío.
    """
    w, h = 640, 220
    bg = (22, 130, 70) if ok else (170, 30, 30)
    img = Image.new("RGB", (w, h), bg)
    dr = ImageDraw.Draw(img)
    try:
        f_big = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "LiberationSans-Bold.ttf"), 34)
        f_small = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "LiberationSans-Regular.ttf"), 18)
    except Exception:
        f_big = ImageFont.load_default()
        f_small = ImageFont.load_default()
    titulo = "✔ FACTURA ENVIADA" if ok else "✖ ERROR AL ENVIAR"
    dr.text((30, 40), titulo, font=f_big, fill=(255, 255, 255))
    detalle = (detalle or "")[:120]
    dr.text((30, 110), detalle, font=f_small, fill=(235, 235, 235))
    from datetime import datetime
    dr.text((30, 180), datetime.now().strftime("%Y-%m-%d %H:%M"), font=f_small, fill=(220, 220, 220))
    out = io.BytesIO()
    img.save(out, "PNG")
    out.seek(0)
    return out

@app.get("/enviar-factura")
def enviar_factura():
    """
    Envia una imagen (por ejemplo la factura o la orden de servicio) directamente
    al WhatsApp del cliente usando la API de Meta.
    Parametros por query string:
      - to: numero del cliente, solo digitos con codigo de pais (ej: 573001234567)
      - imagen_url: URL publica de la imagen a enviar (ej: la URL de /factura)
      - nombre: nombre del cliente (opcional, solo se usa si plantilla=1)
      - plantilla: si es "1", envia usando la plantilla aprobada 'factura_servicio'
        (funciona siempre, sin depender de la ventana de 24h). Si no se manda,
        se envia como imagen suelta (solo funciona si hay conversacion abierta).
    Siempre responde 200 con una imagen-comprobante (verde=ok, rojo=error) para
    que Airtable pueda adjuntarla automaticamente via 'attachment by URL'.
    """
    to = (request.args.get("to", "") or "").strip()
    imagen_url = (request.args.get("imagen_url", "") or "").strip()
    nombre = (request.args.get("nombre", "") or "Cliente").strip()
    usar_plantilla = (request.args.get("plantilla", "") or "") == "1"
    plantilla_nombre = (request.args.get("plantilla_nombre", "") or WHATSAPP_TEMPLATE_NAME).strip()
    # La plantilla aprobada por Meta quedo sin la variable {{1}} en el cuerpo
    # (texto fijo, 0 parametros). Por eso el body NO se manda a menos que se
    # pida explicitamente con con_variable=1 (por si en el futuro se aprueba
    # una version con variable).
    con_variable = (request.args.get("con_variable", "") or "") == "1"

    if not to or not imagen_url:
        png = _comprobante_png(False, "Faltan parametros 'to' o 'imagen_url'")
        return send_file(png, mimetype="image/png", download_name="comprobante-envio.png")
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        png = _comprobante_png(False, "Faltan variables WHATSAPP_TOKEN / WHATSAPP_PHONE_ID en Render")
        return send_file(png, mimetype="image/png", download_name="comprobante-envio.png")

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    if usar_plantilla:
        componentes = [
            {
                "type": "header",
                "parameters": [{"type": "image", "image": {"link": imagen_url}}],
            },
        ]
        if con_variable:
            componentes.append({
                "type": "body",
                "parameters": [{"type": "text", "text": nombre}],
            })
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": plantilla_nombre,
                "language": {"code": WHATSAPP_TEMPLATE_LANG},
                "components": componentes,
            },
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {"link": imagen_url},
        }

    debug = request.args.get("debug", "") == "1"

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        data = r.json()
    except Exception as e:
        if debug:
            return jsonify({"ok": False, "excepcion": str(e)}), 200
        png = _comprobante_png(False, f"Excepcion: {e}")
        return send_file(png, mimetype="image/png", download_name="comprobante-envio.png")

    ok = r.status_code == 200
    if debug:
        return jsonify({"ok": ok, "status": r.status_code, "to": to, "imagen_url": imagen_url, "respuesta": data}), 200

    if ok:
        detalle = f"Enviado a {to}"
    else:
        detalle = str(data.get("error", {}).get("message", data))[:120]
    png = _comprobante_png(ok, detalle)
    return send_file(png, mimetype="image/png", download_name="comprobante-envio.png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
