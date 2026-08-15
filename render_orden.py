# -*- coding: utf-8 -*-
# Render headless de la Orden de Servicio (Técnicos del Poblado).
# Réplica EXACTA del generador: mismo fondo, coordenadas y máscaras. Determinístico.
import io, os
from PIL import Image, ImageDraw, ImageFont

W, H = 1023, 1537
BLUE = (11, 67, 168)   # #0b43a8
BLACK = (12, 12, 12)   # #0c0c0c
HERE = os.path.dirname(os.path.abspath(__file__))
BG = os.path.join(HERE, "orden_plantilla_fondo.png")
FB = os.path.join(HERE, "fonts", "LiberationSans-Bold.ttf")
FR = os.path.join(HERE, "fonts", "LiberationSans-Regular.ttf")

_cache = {}
def font(size, bold=True):
    k = (size, bold)
    if k not in _cache:
        _cache[k] = ImageFont.truetype(FB if bold else FR, size)
    return _cache[k]

def fit(draw, text, max_width, start, bold=True):
    s = start
    while s >= 18:
        if draw.textlength(text, font=font(s, bold)) <= max_width:
            return s
        s -= 1
    return 18

def val(draw, text, at, max_width, start, bold=True, color=BLACK):
    s = fit(draw, text, max_width, start, bold)
    draw.text((at[0], at[1]), text, font=font(s, bold), fill=color, anchor="ls")

def render_orden(d):
    base = Image.open(BG).convert("RGB").resize((W, H))
    dr = ImageDraw.Draw(base)
    for r in [(225,515,950,570),(225,645,950,755),(225,835,950,880),
              (225,968,950,1020),(225,1105,950,1160),(225,1235,950,1365)]:
        dr.rectangle(r, fill=(255,255,255))
    val(dr, d.get("cliente",""), (237,555), 700, 40, True, BLACK)
    address = [l for l in str(d.get("direccion","")).split("\n") if l][:3]
    for i, line in enumerate(address):
        col = BLUE if (i == len(address)-1 and len(address) > 1) else BLACK
        val(dr, line, (237, 690 + i*49), 700, 40, True, col)
    val(dr, d.get("telefono",""), (237,875), 700, 40, True, BLACK)
    val(dr, d.get("fecha",""), (237,1008), 700, 40, True, BLACK)
    val(dr, d.get("hora",""), (237,1145), 700, 38, True, BLACK)
    service = [l for l in str(d.get("servicio","")).split("\n") if l][:4]
    for i, line in enumerate(service):
        val(dr, line, (237, 1275 + i*42), 700, 40 if i==0 else 34, i==0, BLACK)
    out = io.BytesIO(); base.save(out, "PNG"); return out.getvalue()
