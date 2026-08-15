# -*- coding: utf-8 -*-
# Servicio web que genera la Orden de Servicio como imagen PNG.
# GET /orden?cliente=...&direccion=...&telefono=...&fecha=...&hora=...&servicio=...
# Los saltos de línea (dirección / servicio) se envían con el carácter "|".
import io, os
from flask import Flask, request, send_file
from render_orden import render_orden

app = Flask(__name__)

CAMPOS = ["cliente", "direccion", "telefono", "fecha", "hora", "servicio"]

@app.get("/")
def home():
    return "Render Orden de Servicio - Técnicos del Poblado: OK"

@app.get("/orden")
def orden():
    d = {k: (request.args.get(k, "") or "").replace("|", "\n") for k in CAMPOS}
    png = render_orden(d)
    return send_file(io.BytesIO(png), mimetype="image/png", download_name="orden-servicio.png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
