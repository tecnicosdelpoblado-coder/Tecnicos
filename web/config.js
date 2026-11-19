// Configuración compartida por la página y el panel.
// La clave "publishable" de Supabase es pública por diseño: la seguridad la dan las reglas (RLS) de la base de datos.
window.TDP = {
  SUPABASE_URL: "https://hlljfqdfzcnrllunucki.supabase.co",
  SUPABASE_ANON_KEY: "sb_publishable_WqVDZXDv8JnPNT7Mtzo0Ww_bfu9qJm-",  // clave pública (publishable)
  RENDER_URL: "https://tecnicos-190r.onrender.com",  // servidor de facturas y WhatsApp
  WHATSAPP: "573108421131",
  TELEFONO: "+573108421131",
  // Fotos de trabajos (antes / después). Subir a web/img/trabajos/ y listarlas así:
  // { antes: "img/trabajos/nevera-antes.jpg", despues: "img/trabajos/nevera-despues.jpg", texto: "Nevera LG · no enfriaba" }
  GALERIA: []
};
