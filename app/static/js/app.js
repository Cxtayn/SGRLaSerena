/* SGR · utilidades comunes. Sin dependencias salvo SweetAlert2 (CDN).
   Todas las alertas, confirmaciones y resultados pasan por SGR.msg.*  */
(function () {
  "use strict";

  const metaCsrf = document.querySelector('meta[name="csrf-token"]');
  const COLOR = "#920000";

  /* Si el CDN de SweetAlert2 no cargó, se degrada a diálogos nativos para no bloquear la operación.
     Para producción se recomienda alojar el archivo en /static/vendor (ver README). */
  const Swal = window.Swal || {
    fire(o) {
      const texto = [o.title, o.text || (o.html || "").replace(/<[^>]+>/g, " ")].filter(Boolean).join("\n\n");
      if (o.showCancelButton) return Promise.resolve({ isConfirmed: window.confirm(texto) });
      window.alert(texto);
      return Promise.resolve({ isConfirmed: true });
    },
  };

  class ApiError extends Error {
    constructor(status, datos) {
      super((datos && datos.mensaje) || "Ocurrió un error inesperado.");
      this.status = status;
      this.codigo = datos && datos.error;
      this.campos = (datos && datos.campos) || null;
      this.datos = datos || {};
    }
  }

  function escapar(valor) {
    return String(valor == null ? "" : valor).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  async function api(url, opciones) {
    const o = opciones || {};
    const cab = { Accept: "application/json", "X-CSRF-Token": metaCsrf ? metaCsrf.content : "" };
    if (o.body !== undefined) cab["Content-Type"] = "application/json";
    let resp;
    try {
      resp = await fetch(url, {
        method: o.method || "GET", headers: cab, credentials: "same-origin",
        body: o.body !== undefined ? JSON.stringify(o.body) : undefined,
      });
    } catch (e) {
      throw new ApiError(0, { mensaje: "No se pudo conectar con el servidor. Revisa tu conexión e inténtalo nuevamente.", error: "red" });
    }
    if (o.blob && resp.ok) return resp.blob();
    let datos = null;
    try { datos = await resp.json(); } catch (e) { /* respuesta sin cuerpo JSON */ }
    if (resp.status === 401 && !o.sinRedireccion) {
      await msg.aviso("Tu sesión expiró", "Inicia sesión nuevamente para continuar.");
      window.location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search);
      throw new ApiError(401, datos);
    }
    if (!resp.ok) {
      if (!datos) datos = { mensaje: resp.status >= 500 ? "Error del servidor. Inténtalo nuevamente en unos minutos." : "No se pudo completar la solicitud." };
      throw new ApiError(resp.status, datos);
    }
    return datos;
  }

  /* ---------- Mensajes SweetAlert2 ---------- */
  const base = { confirmButtonColor: COLOR, cancelButtonColor: "#55575c", focusConfirm: true };
  const msg = {
    exito: (titulo, texto) => Swal.fire({ ...base, icon: "success", title: titulo, text: texto, confirmButtonText: "Aceptar" }),
    aviso: (titulo, texto) => Swal.fire({ ...base, icon: "warning", title: titulo, text: texto, confirmButtonText: "Entendido" }),
    info: (titulo, texto) => Swal.fire({ ...base, icon: "info", title: titulo, text: texto, confirmButtonText: "Entendido" }),
    error: (titulo, texto) => Swal.fire({ ...base, icon: "error", title: titulo, text: texto, confirmButtonText: "Cerrar" }),
    toast: (icono, titulo) => Swal.fire({ toast: true, position: "top-end", icon: icono, title: titulo, showConfirmButton: false, timer: 3200, timerProgressBar: true }),
    async confirmar({ titulo, texto, si, no, peligro }) {
      const r = await Swal.fire({
        ...base, icon: peligro ? "warning" : "question", title: titulo, text: texto, showCancelButton: true,
        confirmButtonText: si || "Confirmar", cancelButtonText: no || "Cancelar", reverseButtons: true,
        focusCancel: !!peligro, focusConfirm: !peligro, confirmButtonColor: peligro ? "#b3261e" : COLOR,
      });
      return !!r.isConfirmed;
    },
    /* Convierte un ApiError en el mensaje SweetAlert2 apropiado. */
    desdeError(e, titulo) {
      if (e.status === 422) return msg.aviso(titulo || "Revisa los datos", e.message);
      if (e.status === 409) return msg.aviso(titulo || "No se pudo completar", e.message);
      if (e.status === 403) return msg.error("Acción no permitida", e.message);
      return msg.error(titulo || "No se pudo completar la operación", e.message);
    },
  };

  /* ---------- Validación de contraseña (misma regla que el servidor) ---------- */
  const REQ_PASS = [
    ["len", "Al menos 10 caracteres", (p) => p.length >= 10],
    ["may", "Una letra mayúscula", (p) => /[A-ZÁÉÍÓÚÑ]/.test(p)],
    ["min", "Una letra minúscula", (p) => /[a-záéíóúñ]/.test(p)],
    ["num", "Un número", (p) => /[0-9]/.test(p)],
    ["sim", "Un símbolo", (p) => /[^A-Za-z0-9ÁÉÍÓÚÑáéíóúñ\s]/.test(p)],
  ];
  function errorPassword(p) {
    if (!p) return "Ingresa la contraseña.";
    const faltan = REQ_PASS.filter((r) => !r[2](p)).map((r) => r[1].toLowerCase());
    return faltan.length ? "La contraseña no cumple: " + faltan.join("; ") + "." : "";
  }

  /* ---------- Cambios sin guardar ---------- */
  const SGR = { Swal, api, msg, escapar, ApiError, REQ_PASS, errorPassword, sucio: false };
  window.SGR = SGR;
  window.addEventListener("beforeunload", (ev) => { if (SGR.sucio) { ev.preventDefault(); ev.returnValue = ""; } });

  /* ---------- Mostrar / ocultar contraseña ---------- */
  document.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-mostrar]");
    if (!b) return;
    const campo = document.getElementById(b.dataset.mostrar);
    const oculto = campo.type === "password";
    campo.type = oculto ? "text" : "password";
    b.textContent = oculto ? "Ocultar" : "Mostrar";
    b.setAttribute("aria-pressed", String(oculto));
  });

  /* ---------- Cabecera: menú, contexto y salida ---------- */
  const btnMenu = document.getElementById("btn-menu");
  const menu = document.getElementById("menu-lateral");
  const velo = document.getElementById("velo-menu");
  function alternarMenu(abrir) {
    if (!menu) return;
    menu.classList.toggle("abierto", abrir);
    velo.classList.toggle("abierto", abrir);
    btnMenu.setAttribute("aria-expanded", String(abrir));
  }
  if (btnMenu) {
    btnMenu.addEventListener("click", () => alternarMenu(!menu.classList.contains("abierto")));
    velo.addEventListener("click", () => alternarMenu(false));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") alternarMenu(false); });
  }

  const selector = document.getElementById("selector-delegacion");
  if (selector) {
    selector.addEventListener("change", async () => {
      const nuevo = selector.value;
      const previo = selector.dataset.actual;
      if (SGR.sucio) {
        const ok = await msg.confirmar({
          titulo: "Hay cambios sin guardar",
          texto: "Si cambias de delegación se perderán los datos que no guardaste. ¿Deseas continuar?",
          si: "Cambiar de delegación", no: "Quedarme aquí", peligro: true,
        });
        if (!ok) { selector.value = previo; return; }
      }
      try {
        SGR.sucio = false;
        await api("/api/contexto", { method: "POST", body: { delegacion_id: Number(nuevo) } });
        window.location.reload();
      } catch (e) {
        selector.value = previo;
        msg.desdeError(e, "No se pudo cambiar de delegación");
      }
    });
  }

  const salir = document.getElementById("btn-salir");
  if (salir) {
    salir.addEventListener("click", async () => {
      if (SGR.sucio) {
        const ok = await msg.confirmar({ titulo: "Hay cambios sin guardar", texto: "Si cierras sesión se perderán. ¿Cerrar sesión igualmente?",
          si: "Cerrar sesión", no: "Volver", peligro: true });
        if (!ok) return;
      }
      try {
        const r = await api("/api/auth/logout", { method: "POST", sinRedireccion: true });
        SGR.sucio = false;
        window.location.href = r.destino || "/login";
      } catch (e) { msg.desdeError(e, "No se pudo cerrar la sesión"); }
    });
  }
})();
