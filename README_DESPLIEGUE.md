# Técnicos del Poblado — página y panel

Todo es una página estática: GitHub guarda el código, Hostinger la publica y Supabase guarda los datos.
No hay servidor aparte.

```
index.html           Página pública (tecnicosdelpoblado.com)
admin/index.html     Panel de administración (tecnicosdelpoblado.com/admin)
config.js            Dirección y clave pública de Supabase, WhatsApp
img/                 Logo, íconos y plantillas de la orden y la factura
fonts/               Letra que usan la orden y la factura
supabase/schema.sql  Base de datos (ya está cargada en Supabase)
```

## Publicar en Hostinger
hPanel → sitio de tecnicosdelpoblado.com → **Avanzado → GIT**:
- Repositorio: `https://github.com/tecnicosdelpoblado-coder/Tecnicos.git`
- Rama: `main` · Directorio: vacío (public_html)
- **Crear** → **Desplegar**. Activar **Auto deployment** para que cada cambio en GitHub se publique solo.

El dominio debe apuntar a Hostinger (hoy apunta a Vercel).

## Administradores del panel
En Supabase → SQL Editor:
```sql
insert into admins (email, nombre) values ('correo@gmail.com', 'Nombre');
```
Luego Authentication → Users → **Invite user** con ese correo. Cada persona crea su contraseña desde el correo.

## Orden y factura
Se dibujan en el mismo navegador con las plantillas de `img/plantillas/`. Desde el celular, el botón
**Enviar por WhatsApp** abre el menú de compartir; desde el computador se descarga y se adjunta en el chat.

## Fotos
- `img/hero.jpg`: fondo del inicio · `img/hector.jpg`: foto de Héctor (vertical)
- Antes/después: subir a `img/trabajos/` y listarlas en `GALERIA` dentro de `config.js`.

## Cómo se calcula el dinero
- **Total del servicio**: si autoriza → mano de obra + repuestos − descuento (la visita queda descontada). Si no → la visita.
- **Héctor**: 50% de lo que paga el cliente menos el costo de los repuestos; los repuestos que él compre se le devuelven aparte.
- **Socios**: cobrado − repuestos − gastos − parte de Héctor, en tercios (Camilo, Juan, Mariana). Cada retiro se registra en Caja.
- **Deudas a socios**: lo que un socio pagó de su bolsillo o metió a la caja, menos lo que ya se le devolvió.
- **Garantía**: 6 meses desde que el servicio queda *Terminado* (si hubo reparación).
- **Recordatorio**: a los 6 meses el cliente aparece en *Recordatorios* para ofrecerle mantenimiento.
