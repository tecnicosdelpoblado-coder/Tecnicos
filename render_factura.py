# -*- coding: utf-8 -*-
# Render de la Factura / Comprobante de Servicio (Técnicos del Poblado).
import io, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BG = os.path.join(HERE, "factura_fondo.png")
FB = os.path.join(HERE, "fonts", "LiberationSans-Bold.ttf")
FR = os.path.join(HERE, "fonts", "LiberationSans-Regular.ttf")
BLACK = (12, 12, 12)
NAVY = (11, 34, 90)

_bg = None
_cache = {}

def _bg_img():
    global _bg
    if _bg is None:
        _bg = Image.open(BG).convert("RGB")
    return _bg

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
    text = str(text or "").replace("\n", " ").strip()
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
    base = _bg_img().copy()
    dr = ImageDraw.Draw(base)
    val(dr, d.get("fecha", ""), (1035, 140), 150, 24, False, BLACK, anchor="rs")

    val(dr, d.get("cliente", ""), (150, 378), 780, 27, True, BLACK)
    val(dr, d.get("telefono", ""), (168, 421), 760, 27, True, BLACK)
    dl = wrap(d.get("direccion", ""), 870, 26, dr, False, 2)
    y = 463
    for ln in dl:
        val(dr, ln, (175, y), 900, 26, False, BLACK)
        y += 34

    val(dr, d.get("equipo", ""), (145, 582), 800, 27, True, BLACK)
    val(dr, d.get("tecnico", ""), (155, 625), 800, 27, True, BLACK)
    for i, ln in enumerate(wrap(d.get("servicio", ""), 940, 25, dr, False, 4)):
        val(dr, ln, (54, 705 + i * 34), 990, 25, False, BLACK)

    # Garantía: se muestra antes de la tabla de valores.
    garantia = str(d.get("garantia", "")).strip()
    vence = str(d.get("vence_garantia", "")).strip()
    if garantia or vence:
        val(dr, "GARANTÍA:", (54, 850), 165, 25, True, NAVY)
        detalle = garantia
        if vence:
            detalle += (" — " if detalle else "") + "Vigente hasta: " + vence
        val(dr, detalle, (205, 850), 800, 25, False, BLACK)

    tot = money(d.get("total"))
    valor = money(d.get("valor") or d.get("total"))
    cy = 1012
    for ln in wrap(d.get("concepto", ""), 640, 25, dr, False, 5):
        val(dr, ln, (68, cy), 640, 25, False, BLACK)
        cy += 32
    val(dr, valor, (1000, 1012), 220, 27, True, BLACK, anchor="rs")
    val(dr, tot, (1000, 1218), 230, 32, True, NAVY, anchor="rs")

    out = io.BytesIO()
    base.save(out, "PNG")
    return out.getvalue()
