# Servicio de generación de Orden de Servicio — Técnicos del Poblado

Genera la imagen de la orden (idéntica a tu diseño) de forma automática, headless y determinística.
No usa IA ni servicios de plantillas: usa tu propia imagen de fondo + texto en coordenadas fijas.

## Contenido
- `app.py` — servidor web (Flask). Endpoint `GET /orden`.
- `render_orden.py` — el render (réplica exacta de tu generador).
- `orden_plantilla_fondo.png` — tu diseño de fondo.
- `fonts/` — fuentes (Liberation Sans = métricas de Arial).
- `requirements.txt` — dependencias.

## Cómo funciona el endpoint
```
GET /orden?cliente=NOMBRE&direccion=DIR&telefono=TEL&fecha=FECHA&hora=HORA&servicio=SERVICIO
```
Devuelve un PNG. Los saltos de línea (dirección y servicio) se envían con el carácter `|`.

Ejemplo:
```
/orden?cliente=Scoth Machado M&direccion=Cr 105 #40-26 apto 301|San Javier&telefono=3205485149&fecha=14 de agosto&hora=1:00 p. m. - 2:00 p. m.&servicio=Nevera centrales|Cambio de empaque|las 2 puertas
```

## Desplegar GRATIS en Render (recomendado, ~5 min)
1. Crea un repo en GitHub y sube esta carpeta (`orden_servicio_app`).
2. Entra a https://render.com → New → Web Service → conecta el repo.
3. Configura:
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Deploy. Te dan una URL tipo: `https://tecnicos-orden.onrender.com`
5. Prueba en el navegador: `https://TU-URL/orden?cliente=Prueba&telefono=3001234567&fecha=Hoy&hora=10am&servicio=Lavadora`
   Debe descargar/mostrar la imagen.

(También sirve Railway, Fly.io o cualquier host de Python. Nota: el plan gratis de Render "duerme" el servicio; la primera petición del día puede tardar ~30s.)

## Probar localmente
```
pip install -r requirements.txt
python app.py
# abre http://localhost:8000/orden?cliente=Prueba&telefono=3001234567&fecha=Hoy&hora=10am&servicio=Lavadora
```

## Siguiente paso (automatización en Airtable)
Cuando tengas la URL pública, se conecta a Airtable así:
- Automatización en la tabla **Servicios** (trigger: registro creado o Estado = "Agendado").
- Acción: poner en el campo **"Orden de servicio"** un adjunto cuya URL sea:
  `https://TU-URL/orden?cliente={Cliente - Nombre}&direccion={Cliente - Dirección}|{Cliente - Barrio}&telefono={Cliente - WhatsApp}&fecha={Fecha del servicio}&hora={Hora / Franja}&servicio={Electrodoméstico}|{Problema / Diagnóstico}`
- Airtable descarga esa URL y guarda la imagen en el registro.
- Marca **"Estado orden de servicio"** = Generada.

Pásame la URL desplegada y te dejo la automatización de Airtable creada y probada con un registro real.
