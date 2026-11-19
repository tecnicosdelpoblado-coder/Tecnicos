# Técnicos del Poblado — página, panel y servidor

```
web/                 Página pública + panel (se publica en Vercel)
  index.html         Página tecnicosdelpoblado.com
  admin/index.html   Panel de administración (tecnicosdelpoblado.com/admin)
  config.js          URL y anon key de Supabase, URL de Render
  img/               Logo, íconos. Aquí van hero.jpg, hector.jpg y fotos de trabajos
supabase/schema.sql  Base de datos completa (tablas, cálculos y seguridad)
app.py               Servidor en Render: imágenes de orden/factura y envío por WhatsApp
render_*.py, *.png, fonts/   Plantillas de la orden y la factura
```

## 1. Supabase (base de datos y login)
1. Crear proyecto **Técnicos del Poblado** en supabase.com.
2. **SQL Editor → New query** → pegar todo `supabase/schema.sql` → **Run**.
3. Agregar a los administradores (mismo SQL Editor):
   ```sql
   insert into admins (email, nombre) values
     ('correo-de-juan@gmail.com', 'Juan'),
     ('correo-de-camilo@gmail.com', 'Camilo'),
     ('correo-de-mariana@gmail.com', 'Mariana');
   ```
4. **Authentication → Sign In / Providers**: desactivar "Allow new users to sign up".
5. **Authentication → URL Configuration**: Site URL = `https://tecnicosdelpoblado.com/admin/`.
6. **Authentication → Users → Invite user** con cada correo. Cada uno abre el correo y crea su contraseña.
7. **Project Settings → API**: copiar *Project URL* y *anon public key* en `web/config.js`.

## 2. Render (servidor de facturas)
En el servicio `tecnicos` → **Environment**:
- `SUPABASE_URL` y `SUPABASE_ANON_KEY` (los mismos de config.js)
- `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` (ya estaban)
- Borrar `AIRTABLE_TOKEN` (ya no se usa)

## 3. Vercel (página)
En el proyecto de tecnicosdelpoblado.com: conectar este repositorio con **Root Directory = `web`**.

**Orden para no dañar nada:** primero Supabase → luego Vercel (página nueva) → por último Render.
Si se actualiza Render antes que la página, el formulario de la página vieja deja de guardar solicitudes.

## Fotos
- `web/img/hero.jpg`: foto de fondo del inicio (la de la página actual).
- `web/img/hector.jpg`: foto de Héctor (vertical, 4:5).
- Antes/después: subirlas a `web/img/trabajos/` y listarlas en `GALERIA` dentro de `config.js`.

## Cómo se calcula el dinero
- **Total de un servicio**: si el cliente autoriza → mano de obra + repuestos cobrados − descuento (la visita queda descontada). Si no autoriza → solo la visita.
- **Héctor**: 50% de lo que paga el cliente menos el costo de los repuestos. Si él compra un repuesto con su plata, se le devuelve aparte.
- **Socios**: lo cobrado − repuestos − gastos − parte de Héctor, en tercios (Camilo, Juan, Mariana). Cada retiro se registra en Caja.
- **Deudas a socios**: gastos o repuestos que un socio pagó de su bolsillo, más lo que metió a la caja, menos lo que ya se le devolvió.
- **Garantía**: 6 meses desde que el servicio queda *Terminado* (solo si hubo reparación).
- **Recordatorio**: 6 meses después de terminar, el cliente aparece en *Recordatorios* para ofrecerle mantenimiento.
