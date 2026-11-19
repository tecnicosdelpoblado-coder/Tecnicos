-- =====================================================================
-- Técnicos del Poblado — Base de datos (Supabase / PostgreSQL)
-- Pegar completo en Supabase → SQL Editor → Run. Se puede correr de nuevo
-- sin perder datos (usa "if not exists" / "or replace").
-- =====================================================================

create extension if not exists pgcrypto;

-- Fecha de hoy en hora de Colombia (Supabase trabaja en UTC)
create or replace function hoy() returns date
language sql stable as $$ select (now() at time zone 'America/Bogota')::date $$;

-- ---------------------------------------------------------------------
-- Administradores: solo los correos de esta tabla pueden entrar al panel.
-- ---------------------------------------------------------------------
create table if not exists admins (
  email  text primary key,
  nombre text not null
);

create or replace function es_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from admins
    where lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

-- ---------------------------------------------------------------------
-- Configuración general (una sola fila)
-- ---------------------------------------------------------------------
create table if not exists config (
  id                 int primary key default 1 check (id = 1),
  visita_valor       numeric not null default 40000,
  garantia_meses     int     not null default 6,
  recordatorio_meses int     not null default 6
);
insert into config (id) values (1) on conflict (id) do nothing;

-- ---------------------------------------------------------------------
-- Socios y técnico
-- ---------------------------------------------------------------------
create table if not exists socios (
  id         uuid primary key default gen_random_uuid(),
  nombre     text not null unique,
  porcentaje numeric not null check (porcentaje >= 0 and porcentaje <= 100)
);
insert into socios (nombre, porcentaje) values
  ('Camilo', 33.3333), ('Juan', 33.3333), ('Mariana', 33.3334)
on conflict (nombre) do nothing;

create table if not exists tecnicos (
  id         uuid primary key default gen_random_uuid(),
  nombre     text not null unique,
  telefono   text,
  porcentaje numeric not null default 50 check (porcentaje >= 0 and porcentaje <= 100),
  activo     boolean not null default true
);
insert into tecnicos (nombre, porcentaje) values ('Héctor López', 50)
on conflict (nombre) do nothing;

-- ---------------------------------------------------------------------
-- Clientes y sus equipos (historial)
-- ---------------------------------------------------------------------
create table if not exists clientes (
  id         uuid primary key default gen_random_uuid(),
  nombre     text not null,
  telefono   text,
  barrio     text,
  direccion  text,
  notas      text,
  created_at timestamptz not null default now()
);
create index if not exists clientes_telefono_idx on clientes (telefono);

create table if not exists equipos (
  id         uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references clientes(id) on delete cascade,
  tipo       text not null,   -- Lavadora, Nevera, Calentador, Secadora, Aire acondicionado, Estufa, Otro
  marca      text,
  modelo     text,
  serial     text,
  notas      text,
  created_at timestamptz not null default now()
);
create index if not exists equipos_cliente_idx on equipos (cliente_id);

-- ---------------------------------------------------------------------
-- Solicitudes que llegan desde el formulario de la página web
-- ---------------------------------------------------------------------
create table if not exists solicitudes (
  id          uuid primary key default gen_random_uuid(),
  nombre      text not null check (char_length(nombre) between 2 and 120),
  telefono    text not null check (char_length(telefono) between 7 and 20),
  tipo_equipo text check (char_length(tipo_equipo) <= 40),
  barrio      text check (char_length(barrio) <= 120),
  mensaje     text check (char_length(mensaje) <= 1500),
  estado      text not null default 'nueva' check (estado in ('nueva','convertida','descartada')),
  servicio_id uuid,
  created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Servicios (órdenes)
-- ---------------------------------------------------------------------
create sequence if not exists servicios_numero_seq start 1001;

create table if not exists servicios (
  id                  uuid primary key default gen_random_uuid(),
  numero              int  not null unique default nextval('servicios_numero_seq'),
  cliente_id          uuid not null references clientes(id) on delete restrict,
  equipo_id           uuid references equipos(id) on delete set null,
  tecnico_id          uuid references tecnicos(id),
  solicitud_id        uuid references solicitudes(id) on delete set null,
  estado              text not null default 'por_confirmar' check (estado in
                        ('por_confirmar','agendado','en_proceso','esperando_repuesto','terminado','cancelado')),
  fecha               date,
  franja              text,
  direccion           text,
  falla               text,
  diagnostico         text,
  trabajo             text,
  -- Cobro. Si el cliente autoriza la reparación, la visita se descuenta:
  -- total = mano de obra + repuestos − descuento. Si no autoriza: total = visita.
  valor_visita        numeric not null default 40000,
  autorizado          boolean not null default false,
  mano_obra           numeric not null default 0,
  descuento           numeric not null default 0,
  -- Garantía
  es_garantia         boolean not null default false,
  servicio_origen_id  uuid references servicios(id) on delete set null,
  fecha_terminado     date,
  garantia_hasta      date,
  -- Recordatorio de mantenimiento
  recordatorio_fecha  date,
  recordatorio_estado text not null default 'pendiente' check (recordatorio_estado in ('pendiente','contactado','no_aplica')),
  notas               text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index if not exists servicios_cliente_idx on servicios (cliente_id);
create index if not exists servicios_estado_idx  on servicios (estado);

alter table solicitudes drop constraint if exists solicitudes_servicio_fk;
alter table solicitudes add constraint solicitudes_servicio_fk
  foreign key (servicio_id) references servicios(id) on delete set null;

-- Repuestos usados en cada servicio
create table if not exists repuestos (
  id             uuid primary key default gen_random_uuid(),
  servicio_id    uuid not null references servicios(id) on delete cascade,
  descripcion    text not null,
  costo          numeric not null default 0 check (costo >= 0),          -- lo que costó
  precio_cliente numeric not null default 0 check (precio_cliente >= 0), -- lo que se le cobra al cliente
  pagado_por     text not null default 'caja' check (pagado_por in ('caja','tecnico','socio','cliente')),
  cuenta         text check (cuenta in ('efectivo','nequi','bancolombia','daviplata')), -- si lo pagó la caja
  socio_id       uuid references socios(id),                               -- si lo pagó un socio
  fecha          date not null default hoy(),
  created_at     timestamptz not null default now(),
  check (pagado_por <> 'caja'  or cuenta   is not null),
  check (pagado_por <> 'socio' or socio_id is not null)
);
create index if not exists repuestos_servicio_idx on repuestos (servicio_id);

-- ---------------------------------------------------------------------
-- Caja: todos los movimientos de dinero
--   pago_servicio    ingreso  cliente paga un servicio (o abona)
--   gasto            egreso   gasto del negocio (cuenta 'socio' = lo pagó un socio de su bolsillo → deuda)
--   pago_tecnico     egreso   pago a Héctor
--   aporte_socio     ingreso  un socio mete plata a la caja (→ la empresa le debe)
--   devolucion_socio egreso   la empresa le devuelve plata a un socio (baja la deuda)
--   retiro_socio     egreso   un socio retira utilidades
--   ajuste           ingreso/egreso  correcciones de saldo
-- ---------------------------------------------------------------------
create table if not exists movimientos (
  id          uuid primary key default gen_random_uuid(),
  fecha       date not null default hoy(),
  tipo        text not null check (tipo in ('ingreso','egreso')),
  categoria   text not null check (categoria in
                ('pago_servicio','gasto','pago_tecnico','aporte_socio','devolucion_socio','retiro_socio','ajuste')),
  valor       numeric not null check (valor > 0),
  cuenta      text not null check (cuenta in ('efectivo','nequi','bancolombia','daviplata','socio')),
  descripcion text,
  servicio_id uuid references servicios(id) on delete cascade,
  socio_id    uuid references socios(id),
  tecnico_id  uuid references tecnicos(id),
  created_by  text default (auth.jwt() ->> 'email'),
  created_at  timestamptz not null default now(),
  check (categoria <> 'pago_servicio' or (tipo = 'ingreso' and servicio_id is not null)),
  check (categoria not in ('aporte_socio','devolucion_socio','retiro_socio') or socio_id is not null),
  check (categoria <> 'pago_tecnico' or tecnico_id is not null),
  check (cuenta <> 'socio' or (categoria = 'gasto' and socio_id is not null))
);
create index if not exists movimientos_fecha_idx on movimientos (fecha);
create index if not exists movimientos_servicio_idx on movimientos (servicio_id);

-- ---------------------------------------------------------------------
-- Automático: fechas de garantía y recordatorio al terminar un servicio
-- ---------------------------------------------------------------------
create or replace function servicios_antes_de_guardar() returns trigger
language plpgsql as $$
declare c config%rowtype;
begin
  select * into c from config where id = 1;
  new.updated_at := now();
  if new.estado = 'terminado' and new.fecha_terminado is null then
    new.fecha_terminado := hoy();
  end if;
  if new.estado <> 'terminado' then
    new.fecha_terminado := null;
  end if;
  if new.fecha_terminado is not null then
    -- Garantía solo si hubo reparación autorizada
    if new.autorizado and new.garantia_hasta is null then
      new.garantia_hasta := (new.fecha_terminado + make_interval(months => c.garantia_meses))::date;
    end if;
    if new.recordatorio_fecha is null and not new.es_garantia then
      new.recordatorio_fecha := (new.fecha_terminado + make_interval(months => c.recordatorio_meses))::date;
    end if;
  else
    new.garantia_hasta := null;
    if new.recordatorio_estado = 'pendiente' then new.recordatorio_fecha := null; end if;
  end if;
  return new;
end $$;

drop trigger if exists servicios_antes_de_guardar on servicios;
create trigger servicios_antes_de_guardar before insert or update on servicios
for each row execute function servicios_antes_de_guardar();

-- ---------------------------------------------------------------------
-- Vistas (los cálculos viven aquí para que el panel siempre cuadre)
-- ---------------------------------------------------------------------
create or replace view v_servicios with (security_invoker = true) as
with r as (
  select servicio_id,
         sum(costo) filter (where pagado_por <> 'cliente') as rep_costo,
         sum(precio_cliente)                              as rep_precio
  from repuestos group by servicio_id
), p as (
  select servicio_id, sum(valor) as pagado
  from movimientos where categoria = 'pago_servicio' group by servicio_id
), base as (
  select s.*,
         c.nombre   as cliente_nombre,
         c.telefono as cliente_telefono,
         c.barrio   as cliente_barrio,
         e.tipo     as equipo_tipo,
         e.marca    as equipo_marca,
         e.modelo   as equipo_modelo,
         t.nombre   as tecnico_nombre,
         coalesce(t.porcentaje, 0)  as tecnico_pct,
         coalesce(r.rep_costo, 0)   as repuestos_costo,
         coalesce(r.rep_precio, 0)  as repuestos_precio,
         coalesce(p.pagado, 0)      as pagado,
         greatest(0, case
           when s.estado = 'cancelado' then 0
           when s.autorizado then s.mano_obra + coalesce(r.rep_precio, 0) - s.descuento
           when s.es_garantia then 0
           else s.valor_visita - s.descuento
         end) as total
  from servicios s
  join clientes c on c.id = s.cliente_id
  left join equipos  e on e.id = s.equipo_id
  left join tecnicos t on t.id = s.tecnico_id
  left join r on r.servicio_id = s.id
  left join p on p.servicio_id = s.id
)
select base.*,
       total - pagado as saldo,
       -- Héctor gana su % sobre lo cobrado menos el costo de los repuestos
       round(tecnico_pct / 100.0 * greatest(0, pagado - repuestos_costo)) as tecnico_gana
from base;

-- Caja: movimientos + repuestos pagados con plata de la caja
create or replace view v_caja with (security_invoker = true) as
select m.id, m.fecha, m.tipo, m.categoria, m.valor, m.cuenta, m.descripcion,
       m.servicio_id, m.socio_id, m.tecnico_id, m.created_at, 'movimiento' as origen,
       case when m.tipo = 'ingreso' then m.valor else -m.valor end as neto
from movimientos m
where m.cuenta <> 'socio'
union all
select r.id, r.fecha, 'egreso', 'repuesto', r.costo, r.cuenta,
       'Repuesto: ' || r.descripcion, r.servicio_id, null, null, r.created_at, 'repuesto',
       -r.costo
from repuestos r
where r.pagado_por = 'caja' and r.costo > 0;

create or replace view v_saldos_cuentas with (security_invoker = true) as
select cuenta, sum(neto) as saldo from v_caja group by cuenta;

-- Héctor (técnico): lo que ha ganado, repuestos que puso de su bolsillo, lo pagado y el saldo
create or replace view v_tecnicos with (security_invoker = true) as
select t.id, t.nombre, t.porcentaje,
       coalesce((select sum(tecnico_gana) from v_servicios v where v.tecnico_id = t.id), 0) as ganado,
       coalesce((select sum(r.costo) from repuestos r join servicios s on s.id = r.servicio_id
                 where r.pagado_por = 'tecnico' and s.tecnico_id = t.id), 0) as reembolsos,
       coalesce((select sum(valor) from movimientos m
                 where m.categoria = 'pago_tecnico' and m.tecnico_id = t.id), 0) as pagado
from tecnicos t;

-- Resumen del negocio (acumulado)
create or replace view v_resumen with (security_invoker = true) as
select
  coalesce((select sum(valor) from movimientos where categoria = 'pago_servicio'), 0)  as ingresos,
  coalesce((select sum(costo) from repuestos where pagado_por <> 'cliente'), 0)       as repuestos,
  coalesce((select sum(valor) from movimientos where categoria = 'gasto'), 0)          as gastos,
  coalesce((select sum(tecnico_gana) from v_servicios), 0)                              as tecnico,
  coalesce((select sum(valor) from movimientos where categoria = 'ajuste' and tipo = 'ingreso'), 0)
  - coalesce((select sum(valor) from movimientos where categoria = 'ajuste' and tipo = 'egreso'), 0) as ajustes;

-- Socios: deuda de la empresa con cada uno y utilidades disponibles
create or replace view v_socios with (security_invoker = true) as
with u as (
  select ingresos - repuestos - gastos - tecnico as utilidad from v_resumen
)
select s.id, s.nombre, s.porcentaje,
       round((select utilidad from u) * s.porcentaje / 100.0) as utilidad_asignada,
       coalesce((select sum(valor) from movimientos m where m.categoria = 'retiro_socio' and m.socio_id = s.id), 0) as retiros,
       -- Deuda: lo que el socio puso de su bolsillo y no se le ha devuelto
         coalesce((select sum(valor) from movimientos m where m.cuenta = 'socio' and m.socio_id = s.id), 0)
       + coalesce((select sum(costo) from repuestos r where r.pagado_por = 'socio' and r.socio_id = s.id), 0)
       + coalesce((select sum(valor) from movimientos m where m.categoria = 'aporte_socio' and m.socio_id = s.id), 0)
       - coalesce((select sum(valor) from movimientos m where m.categoria = 'devolucion_socio' and m.socio_id = s.id), 0)
         as deuda
from socios s;

-- ---------------------------------------------------------------------
-- Seguridad (RLS): todo es solo para administradores, excepto que
-- cualquiera puede ENVIAR una solicitud desde la página web.
-- ---------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['admins','config','socios','tecnicos','clientes','equipos',
                           'solicitudes','servicios','repuestos','movimientos']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists admin_todo on %I', t);
    execute format('create policy admin_todo on %I for all to authenticated using (es_admin()) with check (es_admin())', t);
  end loop;
end $$;

drop policy if exists web_crea_solicitud on solicitudes;
create policy web_crea_solicitud on solicitudes for insert to anon, authenticated
  with check (estado = 'nueva' and servicio_id is null);

grant usage on schema public to anon, authenticated;
grant insert (nombre, telefono, tipo_equipo, barrio, mensaje) on solicitudes to anon;
grant select, insert, update, delete on all tables in schema public to authenticated;
grant usage, select on all sequences in schema public to authenticated;
grant execute on function es_admin() to anon, authenticated;
