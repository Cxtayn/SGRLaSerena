/* SGR · login y recuperación de contraseña (3 pasos). */
(function () {
  "use strict";
  const { api, msg } = window.SGR;
  const $ = (id) => document.getElementById(id);

  function marcar(idCampo, idError, texto) {
    const campo = $(idCampo);
    const caja = $(idError);
    if (caja) caja.textContent = texto || "";
    if (campo) { if (texto) campo.setAttribute("aria-invalid", "true"); else campo.removeAttribute("aria-invalid"); }
  }
  function aplicarCampos(mapa, campos) {
    let primero = null;
    Object.keys(mapa).forEach((k) => {
      const texto = campos && campos[k];
      marcar(mapa[k][0], mapa[k][1], texto);
      if (texto && !primero) primero = $(mapa[k][0]);
    });
    if (primero) primero.focus();
  }
  async function enviando(boton, fn) {
    const texto = boton.textContent;
    boton.disabled = true;
    boton.textContent = "Procesando...";
    try { return await fn(); } finally { boton.disabled = false; boton.textContent = texto; }
  }

  /* ----------------------------- Login ----------------------------- */
  const formLogin = $("form-login");
  if (formLogin) {
    const mapa = { usuario: ["usuario", "err-usuario"], password: ["password", "err-password"] };
    formLogin.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      $("err-general").textContent = "";
      const datos = { usuario: $("usuario").value.trim(), password: $("password").value };
      const locales = {};
      if (!datos.usuario) locales.usuario = "Ingresa tu usuario o correo.";
      if (!datos.password) locales.password = "Ingresa tu contraseña.";
      aplicarCampos(mapa, locales);
      if (Object.keys(locales).length) {
        msg.aviso("Faltan datos", "Completa usuario y contraseña para ingresar.");
        return;
      }
      await enviando($("btn-ingresar"), async () => {
        try {
          const r = await api("/api/auth/login", { method: "POST", sinRedireccion: true,
            body: { ...datos, next: formLogin.dataset.next || "" } });
          window.location.href = r.destino || "/";
        } catch (e) {
          $("password").value = "";
          if (e.status === 422) { aplicarCampos(mapa, e.campos); msg.aviso("Faltan datos", e.message); return; }
          $("err-general").textContent = e.message;
          if (e.status === 401) msg.error("No se pudo iniciar sesión", e.message);
          else if (e.status === 429) msg.aviso("Acceso bloqueado temporalmente", e.message);
          else if (e.status === 403) msg.aviso("Acceso no disponible", e.message);
          else msg.error("No se pudo iniciar sesión", e.message);
          $("usuario").focus();
        }
      });
    });
  }

  /* ------------------- Paso 1: solicitar código -------------------- */
  const formRec = $("form-recuperar");
  if (formRec) {
    formRec.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const correo = $("correo").value.trim();
      const re = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$/;
      if (!correo) { marcar("correo", "err-correo", "El correo es obligatorio."); msg.aviso("Falta el correo", "Ingresa el correo asociado a tu cuenta."); $("correo").focus(); return; }
      if (!re.test(correo)) { marcar("correo", "err-correo", "Escribe un correo válido, por ejemplo nombre@dominio.cl."); msg.aviso("Correo no válido", "Revisa el formato del correo."); $("correo").focus(); return; }
      marcar("correo", "err-correo", "");
      await enviando($("btn-enviar"), async () => {
        try {
          const r = await api("/api/recuperar/solicitar", { method: "POST", body: { correo }, sinRedireccion: true });
          await msg.info("Revisa tu correo", r.mensaje);
          window.location.href = r.destino;
        } catch (e) {
          if (e.status === 429) { await msg.aviso("Espera un momento", e.message); window.location.href = "/recuperar/validar"; return; }
          if (e.status === 422) { marcar("correo", "err-correo", (e.campos && e.campos.correo) || e.message); msg.aviso("Revisa el correo", e.message); return; }
          msg.error("No se pudo enviar la solicitud", e.message);
        }
      });
    });
  }

  /* ----------------- Paso 2: validar código (OTP) ------------------ */
  const formVal = $("form-validar");
  if (formVal) {
    const casillas = Array.from(document.querySelectorAll("#otp input"));
    const leer = () => casillas.map((c) => c.value).join("");
    const limpiarMarcas = () => { casillas.forEach((c) => c.removeAttribute("aria-invalid")); $("err-codigo").textContent = ""; };
    casillas.forEach((c, i) => {
      c.addEventListener("input", () => {
        c.value = c.value.replace(/\D/g, "").slice(-1);
        limpiarMarcas();
        if (c.value && i < casillas.length - 1) casillas[i + 1].focus();
      });
      c.addEventListener("keydown", (e) => {
        if (e.key === "Backspace" && !c.value && i > 0) { casillas[i - 1].focus(); casillas[i - 1].value = ""; e.preventDefault(); }
        else if (e.key === "ArrowLeft" && i > 0) { casillas[i - 1].focus(); e.preventDefault(); }
        else if (e.key === "ArrowRight" && i < casillas.length - 1) { casillas[i + 1].focus(); e.preventDefault(); }
      });
      c.addEventListener("focus", () => c.select());
      c.addEventListener("paste", (e) => {
        const txt = (e.clipboardData || window.clipboardData).getData("text").replace(/\D/g, "").slice(0, 6);
        if (!txt) return;
        e.preventDefault();
        txt.split("").forEach((d, k) => { if (casillas[k]) casillas[k].value = d; });
        casillas[Math.min(txt.length, 5)].focus();
        limpiarMarcas();
      });
    });
    casillas[0].focus();

    formVal.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const codigo = leer();
      if (codigo.length !== 6) {
        $("err-codigo").textContent = "Ingresa los 6 dígitos del código.";
        casillas.forEach((c) => c.setAttribute("aria-invalid", "true"));
        msg.aviso("Código incompleto", "Debes ingresar los 6 dígitos que recibiste por correo.");
        (casillas.find((c) => !c.value) || casillas[0]).focus();
        return;
      }
      await enviando($("btn-verificar"), async () => {
        try {
          const r = await api("/api/recuperar/validar", { method: "POST", body: { codigo }, sinRedireccion: true });
          window.location.href = r.destino;
        } catch (e) {
          casillas.forEach((c) => { c.value = ""; c.setAttribute("aria-invalid", "true"); });
          $("err-codigo").textContent = e.message;
          casillas[0].focus();
          if (e.codigo === "intentos_agotados") await msg.aviso("Intentos agotados", e.message);
          else if (e.status === 409) { await msg.aviso("Solicitud no encontrada", e.message); window.location.href = "/recuperar"; }
          else {
            const rest = e.datos && typeof e.datos.restantes === "number" ? ` Te quedan ${e.datos.restantes} intento(s).` : "";
            msg.error("Código no válido", e.message + rest);
          }
        }
      });
    });

    // Reenvío con cuenta regresiva
    const texto = $("texto-reenvio");
    const boton = $("btn-reenviar");
    let restante = parseInt(formVal.dataset.restante || "0", 10);
    let reloj = null;
    const fmt = (s) => String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
    function pintar() {
      if (restante > 0) { texto.textContent = "Reenviar código en " + fmt(restante); boton.hidden = true; }
      else { texto.textContent = "¿No llegó el código? "; boton.hidden = false; clearInterval(reloj); }
    }
    function iniciarReloj(seg) {
      restante = seg; clearInterval(reloj); pintar();
      if (restante > 0) reloj = setInterval(() => { restante -= 1; pintar(); }, 1000);
    }
    iniciarReloj(restante);
    boton.addEventListener("click", async () => {
      boton.disabled = true;
      try {
        const r = await api("/api/recuperar/reenviar", { method: "POST", sinRedireccion: true });
        casillas.forEach((c) => { c.value = ""; }); limpiarMarcas(); casillas[0].focus();
        msg.toast("success", r.mensaje);
        iniciarReloj(r.espera || parseInt(formVal.dataset.espera, 10));
      } catch (e) {
        if (e.status === 429 && e.datos && e.datos.espera) iniciarReloj(e.datos.espera);
        if (e.status === 409) { await msg.aviso("Solicitud no encontrada", e.message); window.location.href = "/recuperar"; return; }
        msg.aviso("No se pudo reenviar", e.message);
      } finally { boton.disabled = false; }
    });
  }

  /* ----------------- Paso 3: nueva contraseña ---------------------- */
  const formNueva = $("form-nueva");
  if (formNueva) {
    const p1 = $("password"), p2 = $("confirmacion");
    const items = {};
    document.querySelectorAll("#requisitos li").forEach((li) => { items[li.dataset.req] = li; });
    const tilde = '<svg class="icono" aria-hidden="true"><use href="#i-check"></use></svg>';
    const punto = '<svg class="icono" aria-hidden="true"><use href="#i-pausa"></use></svg>';
    function pintarReq() {
      const v = p1.value;
      window.SGR.REQ_PASS.forEach((r) => marcarItem(r[0], r[1], r[2](v)));
      marcarItem("coincide", "Ambas contraseñas coinciden", v.length > 0 && v === p2.value);
    }
    function marcarItem(k, texto, ok) {
      const li = items[k];
      li.dataset.ok = String(ok);
      li.innerHTML = (ok ? tilde : punto) + "<span>" + texto + (ok ? " <span class='sr-only'>(cumplido)</span>" : "") + "</span>";
    }
    [p1, p2].forEach((e) => e.addEventListener("input", pintarReq));
    pintarReq();
    formNueva.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const errs = {};
      const ep = window.SGR.errorPassword(p1.value);
      if (ep) errs.password = ep;
      if (!p2.value) errs.confirmacion = "Confirma la nueva contraseña.";
      else if (p1.value !== p2.value) errs.confirmacion = "Las contraseñas no coinciden.";
      const mapa = { password: ["password", "err-password"], confirmacion: ["confirmacion", "err-confirmacion"] };
      aplicarCampos(mapa, errs);
      if (Object.keys(errs).length) { msg.aviso("Revisa la contraseña", errs.password || errs.confirmacion); return; }
      await enviando($("btn-guardar"), async () => {
        try {
          const r = await api("/api/recuperar/nueva", { method: "POST", sinRedireccion: true, body: { password: p1.value, confirmacion: p2.value } });
          await msg.exito("Contraseña actualizada", r.mensaje);
          window.location.href = r.destino;
        } catch (e) {
          if (e.status === 422) { aplicarCampos(mapa, e.campos); msg.aviso("Revisa la contraseña", e.message); return; }
          if (e.status === 403) { await msg.aviso("Verificación necesaria", e.message); window.location.href = "/recuperar"; return; }
          msg.error("No se pudo guardar la contraseña", e.message);
        }
      });
    });
  }
})();
