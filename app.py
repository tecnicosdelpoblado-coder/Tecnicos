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
    Siempre responde 200 con una imagen-comprobante (verde=ok, rojo=error) para
    que Airtable pueda adjuntarla automaticamente via 'attachment by URL'.
    """
    to = (request.args.get("to", "") or "").strip()
    imagen_url = (request.args.get("imagen_url", "") or "").strip()

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
        png = _comprobante_png(False, f"Excepcion: {e}")
        return send_file(png, mimetype="image/png", download_name="comprobante-envio.png")

    ok = r.status_code == 200
    if ok:
        detalle = f"Enviado a {to}"
    else:
        detalle = str(data.get("error", {}).get("message", data))[:120]
    png = _comprobante_png(ok, detalle)
    return send_file(png, mimetype="image/png", download_name="comprobante-envio.png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
