// Configuración compartida por la página y el panel.
// La "anon key" de Supabase es pública por diseño: la seguridad la dan las reglas (RLS) de la base de datos.
window.TDP = {
  SUPABASE_URL: "PEGAR_AQUI_URL_DE_SUPABASE",        // ej: https://abcdxyz.supabase.co
  SUPABASE_ANON_KEY: "PEGAR_AQUI_ANON_KEY",          // Project Settings → API → anon public
  RENDER_URL: "https://tecnicos-190r.onrender.com",  // servidor de facturas y WhatsApp
  WHATSAPP: "573108421131",
  TELEFONO: "+573108421131",
  // Fotos de trabajos (antes / después). Subir a web/img/trabajos/ y listarlas así:
  // { antes: "img/trabajos/nevera-antes.jpg", despues: "img/trabajos/nevera-despues.jpg", texto: "Nevera LG · no enfriaba" }
  GALERIA: []
};
