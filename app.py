# -*- coding: utf-8 -*-
"""
Servidor de Técnicos del Poblado (Render).

- POST /orden          -> imagen PNG de la orden de servicio
- POST /factura        -> imagen PNG de la factura / comprobante
- POST /enviar-factura -> genera la factura y la envía al WhatsApp del cliente
- GET  /               -> estado del servidor (sirve para "despertarlo")

Todo (menos "/") exige haber iniciado sesión en el panel: el panel manda el
token de Supabase y aquí se verifica que el correo sea administrador.
Variables de entorno en Render:
  SUPABASE_URL, SUPABASE_ANON_KEY, WHATSAPP_TOKEN, WHATSAPP_PHONE_ID,
  ALLOWED_ORIGINS (opcional, separados por coma)
"""
import io, os, time
from functools import wraps

import requests
from flask import Flask, request, send_file, jsonify

from render_orden import render_orden
from render_factura import render_factura

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
WHATSAPP_API_VERSION = "v21.0"
WHATSAPP_TEMPLATE_NAME = os.environ.get("WHATSAPP_TEMPLATE_NAME", "factura_servicio")
WHATSAPP_TEMPLATE_LANG = "es_CO"

ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS",
    "https://tecnicosdelpoblado.com,https://www.tecnicosdelpoblado.com,http://localhost:8080",
).split(",") if o.strip()]

CAMPOS_ORDEN = ["cliente", "direccion", "telefono", "fecha", "hora", "servicio"]
CAMPOS_FACTURA = [
    "fecha", "cliente", "telefono", "direccion", "equipo", "tecnico",
    "servicio", "concepto", "valor", "total", "garantia", "vence_garantia",
]


# ---------------------------------------------------------------- CORS
@app.after_request
def _cors(resp):
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS or origin.endswith(".vercel.app"):
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


# --------------------------------------------------------------- Login
_tokens_ok = {}  # token -> vence (cache de 5 min para no consultar Supabase cada vez)


def _es_admin(token):
    ahora = time.time()
    if _tokens_ok.get(token, 0) > ahora:
        return True
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return False
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/es_admin",
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={}, timeout=10,
        )
        ok = r.status_code == 200 and r.json() is True
    except Exception:
        ok = False
    if ok:
        if len(_tokens_ok) > 500:
            _tokens_ok.clear()
        _tokens_ok[token] = ahora + 300
    return ok


def solo_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method == "OPTIONS":
            return ("", 204)
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.lower().startswith("bearer ") else ""
        if not token or not _es_admin(token):
            return jsonify({"ok": False, "error": "No autorizado. Inicia sesión en el panel."}), 401
        return f(*args, **kwargs)
    return wrapper


def _datos(campos):
    d = request.get_json(silent=True) or {}
    return {k: str(d.get(k, "") or "") for k in campos}


# -------------------------------------------------------------- Rutas
@app.get("/")
def home():
    return "Técnicos del Poblado: OK"


@app.route("/orden", methods=["POST", "OPTIONS"])
@solo_admin
def orden():
    png = render_orden(_datos(CAMPOS_ORDEN))
    return send_file(io.BytesIO(png), mimetype="image/png", download_name="orden-servicio.png")


@app.route("/factura", methods=["POST", "OPTIONS"])
@solo_admin
def factura():
    png = render_factura(_datos(CAMPOS_FACTURA))
    return send_file(io.BytesIO(png), mimetype="image/png", download_name="factura.png")


@app.route("/enviar-factura", methods=["POST", "OPTIONS"])
@solo_admin
def enviar_factura():
    """
    JSON: { "to": "573001234567", "tipo": "factura" | "orden", "datos": {...},
            "plantilla": true }
    Genera la imagen aquí mismo, la sube a WhatsApp y la envía.
    Con plantilla=true usa la plantilla aprobada (funciona aunque el cliente
    no haya escrito en las últimas 24 h).
    """
    body = request.get_json(silent=True) or {}
    to = "".join(ch for ch in str(body.get("to", "")) if ch.isdigit())
    if len(to) == 10:
        to = "57" + to
    tipo = body.get("tipo", "factura")
    datos = body.get("datos") or {}
    usar_plantilla = body.get("plantilla", True)

    if len(to) < 11:
        return jsonify({"ok": False, "error": "Número de WhatsApp inválido"}), 400
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return jsonify({"ok": False, "error": "Faltan WHATSAPP_TOKEN / WHATSAPP_PHONE_ID en Render"}), 500

    if tipo == "orden":
        png = render_orden({k: str(datos.get(k, "") or "") for k in CAMPOS_ORDEN})
        nombre_archivo = "orden-servicio.png"
    else:
        png = render_factura({k: str(datos.get(k, "") or "") for k in CAMPOS_FACTURA})
        nombre_archivo = "factura.png"

    base = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_ID}"
    auth = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    # 1) Subir la imagen a WhatsApp (así no necesita una URL pública)
    try:
        up = requests.post(
            f"{base}/media", headers=auth, timeout=30,
            data={"messaging_product": "whatsapp", "type": "image/png"},
            files={"file": (nombre_archivo, png, "image/png")},
        )
        media_id = up.json().get("id")
    except Exception as e:
        return jsonify({"ok": False, "error": f"No se pudo subir la imagen: {e}"}), 502
    if not media_id:
        return jsonify({"ok": False, "error": up.json()}), 502

    # 2) Enviar el mensaje
    if usar_plantilla:
        payload = {
            "messaging_product": "whatsapp", "to": to, "type": "template",
            "template": {
                "name": WHATSAPP_TEMPLATE_NAME,
                "language": {"code": WHATSAPP_TEMPLATE_LANG},
                "components": [{"type": "header",
                                "parameters": [{"type": "image", "image": {"id": media_id}}]}],
            },
        }
    else:
        payload = {"messaging_product": "whatsapp", "to": to, "type": "image",
                   "image": {"id": media_id}}

    try:
        r = requests.post(f"{base}/messages", headers={**auth, "Content-Type": "application/json"},
                          json=payload, timeout=20)
        data = r.json()
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    if r.status_code == 200:
        return jsonify({"ok": True, "to": to})
    msg = (data.get("error") or {}).get("message") or str(data)
    return jsonify({"ok": False, "error": msg}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
