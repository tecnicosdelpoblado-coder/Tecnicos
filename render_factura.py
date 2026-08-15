# -*- coding: utf-8 -*-
# Render headless de la Factura / Comprobante de Servicio (Técnicos del Poblado).
# Usa la plantilla PDF como fondo y monta los datos encima. Determinístico.
import io, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BG = os.path.join(HERE, "factura_fondo.png")
FB = os.path.join(HERE, "fonts", "LiberationSans-Bold.ttf")
FR = os.path.join(HERE, "fonts", "LiberationSans-Regular.ttf")
BLACK = (12, 12, 12)
NAVY = (11, 34, 90)

_bg = Image.open(BG).convert("RGB")
W, H = _bg.size

_cache = {}
def font(size, bold=True):
    k = (size, bold)
    if k not in _cache:
        _cache[k] = ImageFont.truetype(FB if bold else FR, size)
    return _cache[k]

def fit(draw, text, max_width, start, bold=True):
    s = start
    while s >= 14:
        if draw.textlength(text, font=font(s, bold)) <= max_width:
            return s
        s -= 1
    return 14

def val(draw, text, at, max_width, start, bold=False, color=BLACK, anchor="ls"):
    text = str(text or "")
    s = fit(draw, text, max_width, start, bold)
    draw.text((at[0], at[1]), text, font=font(s, bold), fill=color, anchor=anchor)

def wrap(text, max_width, size, draw, bold=False, max_lines=4):
    out = []
    for par in str(text or "").split("\n"):
        line = ""
        for word in par.split():
            t = (line + " " + word).strip()
            if draw.textlength(t, font=font(size, bold)) <= max_width:
                line = t
            else:
                if line: out.append(line)
                line = word
        if line: out.append(line)
    if len(out) > max_lines:
        out = out[:max_lines]; out[-1] += "…"
    return out or [""]

def money(v):
    s = str(v or "").strip()
    if s == "": return ""
    try:
        n = int(round(float(s.replace("$", "").replace(".", "").replace(",", "").strip())))
        return "$" + f"{n:,}".replace(",", ".")
    except Exception:
        return s

def render_factura(d):
    base = _bg.copy()
    dr = ImageDraw.Draw(base)

    # Fecha (header derecha, alineada a la derecha para no chocar con "Fecha:")
    val(dr, d.get("fecha",""), (1035,140), 150, 24, False, BLACK, anchor="rs")

    # Datos del cliente
    val(dr, d.get("cliente",""), (150,378), 780, 27, True, BLACK)
    val(dr, d.get("telefono",""), (168,421), 760, 27, True, BLACK)
    # Dirección (puede ser larga -> 1 o 2 líneas)
    dl = wrap(d.get("direccion",""), 870, 26, dr, False, 2)
    y = 463
    for ln in dl:
        val(dr, ln, (175,y), 900, 26, False, BLACK); y += 34

    # Detalle del servicio
    val(dr, d.get("equipo",""), (145,582), 800, 27, True, BLACK)
    val(dr, d.get("tecnico",""), (155,625), 800, 27, True, BLACK)
    # Servicio realizado (multilínea debajo del label)
    for i, ln in enumerate(wrap(d.get("servicio",""), 940, 25, dr, False, 4)):
        val(dr, ln, (54, 705 + i*34), 990, 25, False, BLACK)

    # Tabla de valores (una fila) + total
    tot = money(d.get("total"))
    valor = money(d.get("valor") or d.get("total"))
    val(dr, d.get("concepto",""), (68,1012), 640, 26, False, BLACK)
    val(dr, valor, (1000,1012), 220, 27, True, BLACK, anchor="rs")
    val(dr, tot, (1000,1218), 230, 32, True, NAVY, anchor="rs")

    out = io.BytesIO(); base.save(out, "PNG"); return out.getvalue()

if __name__ == "__main__":
    png = render_factura({
        "fecha": "15 de agosto",
        "cliente": "Carlos Agudelo",
        "telefono": "301 458 4396",
        "direccion": "Calle 29b #53-04 apto 301, La Florida, Bello",
        "equipo": "Nevera - Samsung",
        "tecnico": "Juan Camilo",
        "servicio": "Reparación: cambio de empaque de las 2 puertas. Se realizó limpieza general del sistema y prueba de enfriamiento.",
        "concepto": "Reparación de nevera - cambio de empaque",
        "valor": "$220.000",
        "total": "$220.000",
    })
    open(os.path.join(HERE, "_factura_test.png"), "wb").write(png)
    print("OK", len(png), "bytes")
