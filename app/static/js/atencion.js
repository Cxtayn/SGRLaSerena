/* SGR · ingreso de atención: solicitante, Tipo → Sub Atención dependiente, guardado seguro. */
(function () {
  "use strict";
  const { api, msg, escapar } = window.SGR;
  const $ = (id) => document.getElementById(id);
  const form = $("form-atencion");
  if (!form) return;

  let tipos = [], subtipos = [], vecino = null, enviando = false, resultados = [], indice = -1, temporizador = null;
  const nuevoToken = () => (window.crypto && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2));
  let token = nuevoToken(); // un token por formulario: el servidor ignora reenvíos duplicados

  function error(k, texto) {
    const caja = $("err-" + k); if (caja) caja.textContent = texto || "";
    const campo = { vecino_id: $("vecino-buscar"), tipo_id: $("tipo_id"), subtipo_id: $("subtipo_id"), descripcion: $("descripcion") }[k];
    if (campo) { if (texto) campo.setAttribute("aria-invalid", "true"); else campo.removeAttribute("aria-invalid"); }
  }
  const limpiarErrores = () => ["vecino_id", "tipo_id", "subtipo_id", "descripcion"].forEach((k) => error(k, ""));

  /* ---------------- catálogos ---------------- */
  async function cargarOpciones() {
    try {
      const d = await api("/api/atencion/opciones");
      tipos = d.tipos; subtipos = d.subtipos;
      $("tipo_id").innerHTML = '<option value="">Selecciona un tipo</option>' +
        tipos.map((t) => `<option value="${t.id}">${escapar(t.nombre)}</option>`).join("");
    } catch (e) { msg.desdeError(e, "No se pudieron cargar los catálogos"); }
  }
  $("tipo_id").addEventListener("change", () => {
    const sel = $("subtipo_id"), previo = sel.value;
    const tid = Number($("tipo_id").value);
    const validas = subtipos.filter((s) => s.tipo_id === tid);
    sel.disabled = !tid;
    sel.innerHTML = (tid ? '<option value="">Selecciona una subatención</option>' : '<option value="">Primero elige el tipo</option>') +
      validas.map((s) => `<option value="${s.id}">${escapar(s.nombre)}</option>`).join("");
    // la selección anterior solo se conserva si sigue siendo válida para el nuevo tipo
    if (previo && validas.some((s) => String(s.id) === previo)) sel.value = previo;
    error("tipo_id", ""); error("subtipo_id", "");
  });

  /* ---------------- solicitante (combobox accesible) ---------------- */
  const entrada = $("vecino-buscar"), lista = $("vecino-lista");
  function cerrarLista() { lista.hidden = true; entrada.setAttribute("aria-expanded", "false"); entrada.removeAttribute("aria-activedescendant"); indice = -1; }
  function pintarLista() {
    if (!resultados.length) { lista.innerHTML = `<li role="option" aria-disabled="true">Sin resultados. Puedes registrar un nuevo solicitante.</li>`; }
    else lista.innerHTML = resultados.map((v, i) => `<li role="option" id="vopt-${i}" data-i="${i}" aria-selected="${i === indice}">${escapar(v.nombre_completo)} <span class="ayuda">· ${escapar(v.rut)}</span></li>`).join("");
    lista.hidden = false; entrada.setAttribute("aria-expanded", "true");
    if (indice >= 0) entrada.setAttribute("aria-activedescendant", "vopt-" + indice);
  }
  function elegir(v) {
    vecino = v;
    $("vecino-entrada").hidden = true;
    $("vecino-elegido").hidden = false;
    $("vecino-elegido-texto").textContent = `${v.nombre_completo} · RUT ${v.rut}`;
    error("vecino_id", ""); cerrarLista(); marcarSucio();
  }
  entrada.addEventListener("input", () => {
    clearTimeout(temporizador);
    const q = entrada.value.trim();
    if (q.length < 2) { cerrarLista(); return; }
    temporizador = setTimeout(async () => {
      try { resultados = (await api("/api/vecinos/buscar?q=" + encodeURIComponent(q))).items; indice = -1; pintarLista(); }
      catch (e) { msg.desdeError(e, "No se pudo buscar"); }
    }, 250);
  });
  entrada.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && resultados.length) { indice = (indice + 1) % resultados.length; pintarLista(); e.preventDefault(); }
    else if (e.key === "ArrowUp" && resultados.length) { indice = (indice - 1 + resultados.length) % resultados.length; pintarLista(); e.preventDefault(); }
    else if (e.key === "Enter" && indice >= 0) { elegir(resultados[indice]); e.preventDefault(); }
    else if (e.key === "Escape") cerrarLista();
  });
  lista.addEventListener("mousedown", (e) => { const li = e.target.closest("[data-i]"); if (li) { e.preventDefault(); elegir(resultados[Number(li.dataset.i)]); } });
  entrada.addEventListener("blur", () => setTimeout(cerrarLista, 120));
  $("vecino-cambiar").addEventListener("click", () => {
    vecino = null; $("vecino-elegido").hidden = true; $("vecino-entrada").hidden = false; entrada.value = ""; entrada.focus();
  });

  /* ---------------- alta rápida de solicitante ---------------- */
  const dlg = $("modal-vecino"), campos = ["rut", "nombres", "apellidos", "correo", "telefono"];
  $("btn-nuevo-vecino").addEventListener("click", () => { campos.forEach((k) => { $("v-" + k).value = ""; $("err-v-" + k).textContent = ""; }); dlg.showModal(); $("v-rut").focus(); });
  const cerrarDlg = () => dlg.close();
  $("vecino-cerrar").addEventListener("click", cerrarDlg); $("vecino-cancelar").addEventListener("click", cerrarDlg);
  $("form-vecino").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const btn = $("vecino-guardar"); if (btn.disabled) return;
    const cuerpo = {}; campos.forEach((k) => { cuerpo[k] = $("v-" + k).value.trim(); $("err-v-" + k).textContent = ""; });
    const loc = {};
    if (!cuerpo.rut) loc.rut = "El RUT es obligatorio.";
    if (!cuerpo.nombres) loc.nombres = "Los nombres son obligatorios.";
    if (!cuerpo.apellidos) loc.apellidos = "Los apellidos son obligatorios.";
    if (Object.keys(loc).length) { Object.keys(loc).forEach((k) => { $("err-v-" + k).textContent = loc[k]; }); msg.aviso("Revisa los campos", "Completa los datos obligatorios del solicitante."); return; }
    btn.disabled = true;
    try {
      const r = await api("/api/vecinos", { method: "POST", body: cuerpo });
      dlg.close(); elegir(r.item); await msg.exito("Solicitante registrado", r.mensaje);
    } catch (e) {
      if (e.campos) Object.keys(e.campos).forEach((k) => { const c = $("err-v-" + k); if (c) c.textContent = e.campos[k]; });
      msg.desdeError(e, e.status === 409 ? "El solicitante ya existe" : undefined);
    } finally { btn.disabled = false; }
  });

  /* ---------------- descripción y estado del formulario ---------------- */
  const marcarSucio = () => { window.SGR.sucio = true; };
  $("descripcion").addEventListener("input", () => { $("contador-desc").textContent = $("descripcion").value.length; marcarSucio(); });
  $("tipo_id").addEventListener("change", marcarSucio); $("subtipo_id").addEventListener("change", marcarSucio);

  function reiniciar() {
    form.reset(); vecino = null; limpiarErrores();
    $("vecino-elegido").hidden = true; $("vecino-entrada").hidden = false;
    $("subtipo_id").disabled = true; $("subtipo_id").innerHTML = '<option value="">Primero elige el tipo</option>';
    $("contador-desc").textContent = "0"; token = nuevoToken(); window.SGR.sucio = false;
  }
  $("btn-cancelar-atencion").addEventListener("click", async () => {
    if (window.SGR.sucio) {
      const ok = await msg.confirmar({ titulo: "¿Cancelar el ingreso?", texto: "Se descartarán los datos escritos. No se creará ninguna atención.",
        si: "Sí, cancelar", no: "Seguir editando", peligro: true });
      if (!ok) return;
    }
    reiniciar(); msg.toast("info", "Ingreso cancelado: no se creó ningún registro");
  });

  /* ---------------- guardado ---------------- */
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (enviando) return; // prevención de doble envío
    limpiarErrores();
    const e = {};
    if (!vecino) e.vecino_id = "Selecciona o registra al solicitante.";
    if (!$("tipo_id").value) e.tipo_id = "Selecciona el Tipo de Atención.";
    if (!$("subtipo_id").value) e.subtipo_id = "Selecciona la Sub Atención.";
    const desc = $("descripcion").value.trim();
    if (desc.length < 10) e.descripcion = "Describe la atención con al menos 10 caracteres.";
    Object.keys(e).forEach((k) => error(k, e[k]));
    if (Object.keys(e).length) {
      msg.aviso("Revisa los campos", "Completa los datos obligatorios antes de guardar la atención.");
      const primero = form.querySelector('[aria-invalid="true"]'); if (primero) primero.focus();
      return;
    }
    enviando = true;
    const btn = $("btn-guardar-atencion"), texto = btn.textContent;
    btn.disabled = true; btn.textContent = "Guardando...";
    try {
      const r = await api("/api/atenciones", { method: "POST", body: {
        vecino_id: vecino.id, tipo_id: Number($("tipo_id").value), subtipo_id: Number($("subtipo_id").value),
        descripcion: desc, token_envio: token } });
      const a = r.atencion;
      reiniciar();
      await window.SGR.Swal.fire({
        icon: "success", title: "Atención registrada", confirmButtonColor: "#920000", confirmButtonText: "Aceptar",
        html: `<p>Identificador de atención: <strong>${escapar(a.folio)}</strong></p>
               <p style="margin:6px 0 0;font-size:14px">${escapar(a.delegacion)} · ${escapar(a.fecha)}<br>Responsable: ${escapar(a.responsable)}</p>`,
      });
      if (window.SGRLista) window.SGRLista.recargar();
    } catch (err) {
      if (err.campos) Object.keys(err.campos).forEach((k) => error(k, err.campos[k]));
      msg.desdeError(err, "No se registró la atención");
    } finally { enviando = false; btn.disabled = false; btn.textContent = texto; }
  });

  cargarOpciones();
})();
