/* SGR · mantenedor genérico: listado, búsqueda, filtros, paginación, exportación y formularios.
   Se configura con el JSON de #datos-pagina (ver app/ui_config.py). La validación definitiva
   siempre ocurre en el servidor; aquí solo se anticipa para guiar a la persona. */
(function () {
  "use strict";
  const nodoCfg = document.getElementById("datos-pagina");
  if (!nodoCfg) return;
  const { api, msg, escapar } = window.SGR;
  const cfg = JSON.parse(nodoCfg.textContent);
  const $ = (id) => document.getElementById(id);
  const zona = $("zona-tabla"), paginador = $("paginador");
  const ICONO = (n) => `<svg class="icono" aria-hidden="true" focusable="false"><use href="#i-${n}"></use></svg>`;

  const est = { page: 1, per_page: 10, q: "", estado: "", ambito: "", sort: "", dir: "asc" };
  let ultimo = null, secuencia = 0, temporizador = null;

  /* ---------------- estado en la URL (conserva filtros al paginar o recargar) ---------------- */
  (function leerUrl() {
    const p = new URLSearchParams(location.search);
    if (cfg.clave === "atenciones" && !cfg.puede.crear) { /* la página solo lista */ }
    est.q = (p.get("q") || "").slice(0, 100);
    est.estado = ["activo", "inactivo"].includes(p.get("estado")) ? p.get("estado") : "";
    est.ambito = p.get("ambito") === "autorizadas" ? "autorizadas" : "";
    est.page = Math.max(1, parseInt(p.get("page") || "1", 10) || 1);
    est.per_page = [5, 10, 25, 50, 100].includes(parseInt(p.get("per_page"), 10)) ? parseInt(p.get("per_page"), 10) : 10;
    est.sort = p.get("sort") || "";
    est.dir = p.get("dir") === "desc" ? "desc" : "asc";
  })();

  function parametros(conPagina) {
    const p = new URLSearchParams();
    if (est.q) p.set("q", est.q);
    if (est.estado) p.set("estado", est.estado);
    if (est.ambito) p.set("ambito", est.ambito);
    if (est.sort) { p.set("sort", est.sort); p.set("dir", est.dir); }
    if (conPagina) { p.set("page", est.page); p.set("per_page", est.per_page); }
    return p;
  }
  function sincronizarUrl() {
    const p = parametros(true);
    if (est.page === 1) p.delete("page");
    if (est.per_page === 10) p.delete("per_page");
    const s = p.toString();
    history.replaceState(null, "", location.pathname + (s ? "?" + s : ""));
  }
  const hayFiltros = () => !!(est.q || est.estado || est.ambito);

  /* ----------------------------------- carga ----------------------------------- */
  async function cargar() {
    const mia = ++secuencia;
    zona.setAttribute("aria-busy", "true");
    if (!ultimo) zona.innerHTML = `<div class="cargando"><span class="girando" aria-hidden="true"></span>Cargando registros...</div>`;
    else zona.style.opacity = ".55";
    try {
      const datos = await api(`/api/${cfg.slug}?${parametros(true)}`);
      if (mia !== secuencia) return; // llegó una respuesta más nueva
      ultimo = datos;
      est.page = datos.page;
      sincronizarUrl();
      pintar(datos);
    } catch (e) {
      if (mia !== secuencia) return;
      zona.innerHTML = `<div class="estado-vacio" role="alert">${ICONO("alerta")}<h3>No se pudo cargar el listado</h3>
        <p>${escapar(e.message)}</p><button type="button" class="btn btn-primario" data-acc="reintentar">${ICONO("recarga")} Reintentar</button></div>`;
      paginador.innerHTML = "";
    } finally {
      if (mia === secuencia) { zona.removeAttribute("aria-busy"); zona.style.opacity = ""; }
    }
  }

  function celda(c, item) {
    const v = item[c.k];
    if (c.fmt === "estado") {
      return item.activo
        ? `<span class="estado on">${ICONO("check")}${escapar(v)}</span>`
        : `<span class="estado off">${ICONO("pausa")}${escapar(v)}</span>`;
    }
    if (c.fmt === "cuenta") return `${(v || []).length} permiso(s)`;
    return v === "" || v == null ? "—" : escapar(v);
  }

  function pintar(d) {
    if (d.total === 0) {
      if (hayFiltros()) {
        zona.innerHTML = `<div class="estado-vacio">${ICONO("buscar")}<h3>Sin coincidencias</h3>
          <p>No encontramos registros con los filtros aplicados. Prueba con otras palabras o quita los filtros.</p>
          <button type="button" class="btn btn-suave" data-acc="limpiar">Limpiar filtros</button></div>`;
      } else {
        zona.innerHTML = `<div class="estado-vacio">${ICONO("bandeja")}<h3>Aún no hay registros</h3>
          <p>${cfg.puede.crear ? "Crea el primero con el botón «Nuevo registro»." : "Todavía no hay información para mostrar."}</p></div>`;
      }
      paginador.innerHTML = `<span role="status">Mostrando 0 de 0 registros</span>`;
      return;
    }
    const encabezado = cfg.columnas.map((c) => {
      if (!c.sort) return `<th scope="col">${escapar(c.t)}</th>`;
      const activo = est.sort === c.sort;
      const aria = activo ? (est.dir === "asc" ? "ascending" : "descending") : "none";
      return `<th scope="col" aria-sort="${aria}"><button type="button" data-sort="${c.sort}">${escapar(c.t)}${ICONO("orden")}</button></th>`;
    }).join("") + `<th scope="col">Acciones</th>`;
    const filas = d.items.map((it) => {
      const etiqueta = escapar(it.nombre || it.folio || it.codigo || it.id);
      const celdas = cfg.columnas.map((c) => `<td data-label="${escapar(c.t)}">${celda(c, it)}</td>`).join("");
      const acc = [`<button type="button" class="btn-enlace" data-acc="ver" data-id="${it.id}" aria-label="Ver ${etiqueta}">Ver</button>`];
      if (!cfg.solo_lectura && cfg.puede.editar) {
        acc.push(`<button type="button" class="btn-enlace" data-acc="editar" data-id="${it.id}" aria-label="Editar ${etiqueta}">Editar</button>`);
        if ("activo" in it) {
          acc.push(`<button type="button" class="btn-enlace" data-acc="estado" data-id="${it.id}" data-activo="${it.activo}" aria-label="${it.activo ? "Desactivar" : "Activar"} ${etiqueta}">${it.activo ? "Desactivar" : "Activar"}</button>`);
        }
      }
      if (!cfg.solo_lectura && cfg.puede.eliminar) {
        acc.push(`<button type="button" class="btn-enlace peligro" data-acc="eliminar" data-id="${it.id}" aria-label="Eliminar ${etiqueta}">Eliminar</button>`);
      }
      return `<tr>${celdas}<td class="celda-acciones"><div class="acciones">${acc.join("")}</div></td></tr>`;
    }).join("");
    zona.innerHTML = `<table class="tabla"><caption class="sr-only">Listado de ${escapar(cfg.titulo)}</caption><thead><tr>${encabezado}</tr></thead><tbody>${filas}</tbody></table>`;

    const desde = (d.page - 1) * d.per_page + 1, hasta = desde + d.items.length - 1;
    const paginas = [];
    const ini = Math.max(1, Math.min(d.page - 2, d.paginas - 4)), fin = Math.min(d.paginas, ini + 4);
    for (let i = ini; i <= fin; i++) paginas.push(`<button type="button" data-pagina="${i}" ${i === d.page ? 'aria-current="page"' : ""} aria-label="Página ${i}">${i}</button>`);
    paginador.innerHTML = `
      <span role="status">Mostrando ${desde} a ${hasta} de ${d.total} registro${d.total === 1 ? "" : "s"}</span>
      <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
        <label>Por página <select id="por-pagina" class="entrada" style="width:auto;min-height:36px;padding:4px 8px">${[5, 10, 25, 50, 100].map((n) => `<option ${n === d.per_page ? "selected" : ""}>${n}</option>`).join("")}</select></label>
        <nav aria-label="Paginación">
          <button type="button" data-pagina="${d.page - 1}" ${d.page <= 1 ? "disabled" : ""}>Anterior</button>
          ${paginas.join("")}
          <button type="button" data-pagina="${d.page + 1}" ${d.page >= d.paginas ? "disabled" : ""}>Siguiente</button>
        </nav>
      </div>`;
  }

  /* ------------------------------ filtros y eventos ------------------------------ */
  const buscador = $("buscador"), fEstado = $("filtro-estado"), fAmbito = $("filtro-ambito");
  buscador.value = est.q;
  if (fEstado) fEstado.value = est.estado;
  if (fAmbito) fAmbito.value = est.ambito;
  const refiltrar = () => { est.page = 1; cargar(); };
  buscador.addEventListener("input", () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => { est.q = buscador.value.trim(); refiltrar(); }, 300);
  });
  buscador.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); clearTimeout(temporizador); est.q = buscador.value.trim(); refiltrar(); }
  });
  if (fEstado) fEstado.addEventListener("change", () => { est.estado = fEstado.value; refiltrar(); });
  if (fAmbito) fAmbito.addEventListener("change", () => { est.ambito = fAmbito.value; refiltrar(); });

  paginador.addEventListener("click", (e) => {
    const b = e.target.closest("[data-pagina]");
    if (b && !b.disabled) { est.page = parseInt(b.dataset.pagina, 10); cargar(); }
  });
  paginador.addEventListener("change", (e) => {
    if (e.target.id === "por-pagina") { est.per_page = parseInt(e.target.value, 10); est.page = 1; cargar(); }
  });

  zona.addEventListener("click", (e) => {
    const s = e.target.closest("[data-sort]");
    if (s) {
      if (est.sort === s.dataset.sort) est.dir = est.dir === "asc" ? "desc" : "asc"; else { est.sort = s.dataset.sort; est.dir = "asc"; }
      est.page = 1; cargar(); return;
    }
    const b = e.target.closest("[data-acc]");
    if (!b) return;
    const id = parseInt(b.dataset.id, 10);
    switch (b.dataset.acc) {
      case "reintentar": cargar(); break;
      case "limpiar":
        est.q = ""; est.estado = ""; est.ambito = ""; buscador.value = "";
        if (fEstado) fEstado.value = ""; if (fAmbito) fAmbito.value = "";
        refiltrar(); break;
      case "ver": abrir("ver", id); break;
      case "editar": abrir("editar", id); break;
      case "estado": cambiarEstado(id, b.dataset.activo === "true"); break;
      case "eliminar": eliminar(id); break;
    }
  });

  /* ------------------------------- exportar a Excel ------------------------------- */
  const btnExp = $("btn-exportar");
  if (btnExp) {
    btnExp.addEventListener("click", async () => {
      if (ultimo && ultimo.total === 0) { msg.info("No hay datos para exportar", "El filtro actual no tiene registros."); return; }
      btnExp.disabled = true;
      try {
        // Sin page/per_page: el servidor exporta TODAS las páginas del filtro aplicado.
        const blob = await api(`/api/${cfg.slug}/exportar?${parametros(false)}`, { blob: true });
        const t = new Date(), z = (n) => String(n).padStart(2, "0");
        const nombre = `${cfg.slug}_${t.getFullYear()}${z(t.getMonth() + 1)}${z(t.getDate())}_${z(t.getHours())}${z(t.getMinutes())}.xlsx`;
        const url = URL.createObjectURL(blob), a = document.createElement("a");
        a.href = url; a.download = nombre; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 2000);
        msg.toast("success", "Archivo Excel generado");
      } catch (e) { msg.desdeError(e, "No se pudo exportar"); } finally { btnExp.disabled = false; }
    });
  }

  /* ---------------------------- acciones: estado y eliminar ---------------------------- */
  const etiquetaDe = (it) => it.nombre || it.folio || it.codigo || `#${it.id}`;
  async function filaPorId(id) { return (await api(`/api/${cfg.slug}/${id}`)).item; }

  async function cambiarEstado(id, estabaActivo) {
    let it;
    try { it = await filaPorId(id); } catch (e) { msg.desdeError(e); cargar(); return; }
    const accion = estabaActivo ? "desactivar" : "activar";
    const ok = await msg.confirmar({
      titulo: `¿${accion[0].toUpperCase() + accion.slice(1)} ${cfg.singular}?`,
      texto: `«${etiquetaDe(it)}» quedará ${estabaActivo ? cfg.estados[1].toLowerCase() : cfg.estados[0].toLowerCase()}.`,
      si: `Sí, ${accion}`, no: "Cancelar", peligro: estabaActivo,
    });
    if (!ok) { msg.toast("info", "Operación cancelada"); return; }
    try {
      const r = await api(`/api/${cfg.slug}/${id}/estado`, { method: "PATCH", body: { activo: !estabaActivo } });
      await msg.exito("Estado actualizado", r.mensaje);
      cargar();
    } catch (e) { msg.desdeError(e, "No se pudo cambiar el estado"); cargar(); }
  }

  async function eliminar(id) {
    let it;
    try { it = await filaPorId(id); } catch (e) { msg.desdeError(e); cargar(); return; }
    const ok = await msg.confirmar({
      titulo: `Eliminar ${cfg.singular}`, texto: `Vas a eliminar «${etiquetaDe(it)}». Esta acción no se puede deshacer.`,
      si: "Sí, eliminar", no: "Cancelar", peligro: true,
    });
    if (!ok) { msg.toast("info", "Eliminación cancelada: no se modificó ningún registro"); return; }
    try {
      const r = await api(`/api/${cfg.slug}/${id}`, { method: "DELETE" });
      await msg.exito("Registro eliminado", r.mensaje);
      cargar();
    } catch (e) { msg.desdeError(e, "No se pudo eliminar"); cargar(); }
  }

  /* --------------------------------- formularios --------------------------------- */
  const modal = $("modal-registro"), cuerpo = $("modal-cuerpo"), pie = $("modal-pie"), form = $("form-registro");
  let modo = "crear", idActual = null, enviando = false, catalogoPerm = null, alcanceRoles = {};
  const femenino = cfg.genero === "f";
  const tituloModo = {
    crear: `${femenino ? "Nueva" : "Nuevo"} ${cfg.singular}`,
    editar: `Editar ${cfg.singular}`, ver: `Consulta de ${cfg.singular}`,
  };

  async function opcionesRemotas(url) { return (await api(url)).items; }

  async function matrizPermisos(seleccion, soloVer) {
    if (!catalogoPerm) catalogoPerm = await api("/api/permisos/catalogo");
    const cat = catalogoPerm, sel = new Set(seleccion || []), propios = new Set(cat.propios);
    const cab = cat.acciones.map((a) => `<th scope="col">${escapar(a.t)}</th>`).join("");
    const filas = cat.modulos.map((m) => {
      const celdas = cat.acciones.map((a) => {
        if (!m.acciones.includes(a.k)) return `<td class="na" aria-label="No aplica">—</td>`;
        const p = `${m.k}:${a.k}`;
        const dis = soloVer || !propios.has(p);
        return `<td><input type="checkbox" data-perm="${p}" ${sel.has(p) ? "checked" : ""} ${dis ? "disabled" : ""} aria-label="${escapar(a.t)} en ${escapar(m.t)}"></td>`;
      }).join("");
      return `<tr><td>${escapar(m.t)}${m.operativo ? "" : ' <span class="etiqueta-plantilla">Plantilla</span>'}</td>${celdas}</tr>`;
    }).join("");
    return `<div style="overflow-x:auto"><table class="matriz"><thead><tr><th scope="col">Módulo</th>${cab}</tr></thead><tbody>${filas}</tbody></table></div>
      ${soloVer ? "" : '<p class="ayuda">Solo puedes otorgar permisos que tu propio perfil tiene. Toda acción requiere «Ver».</p>'}`;
  }

  function obligatorio(c) { return c.req || (c.req_crear && modo === "crear"); }
  function etiquetaCampo(c, forId) {
    return `<label for="${forId}">${escapar(c.t)}${obligatorio(c) ? ' <span class="req" aria-hidden="true">*</span>' : ""}</label>`;
  }
  function envoltura(c, interior, forId) {
    const ayuda = c.ayuda ? `<div class="ayuda" id="ay-${c.k}">${escapar(c.ayuda)}</div>` : "";
    return `<div class="campo" data-campo="${c.k}">${etiquetaCampo(c, forId)}${interior}${ayuda}<div class="error-campo" id="err-${c.k}" role="alert"></div></div>`;
  }

  async function construirCampo(c, item) {
    const id = `f-${c.k}`;
    const v = item[c.k];
    const desc = `aria-describedby="${c.ayuda ? "ay-" + c.k + " " : ""}err-${c.k}"`;
    const req = obligatorio(c) ? 'required aria-required="true"' : "";
    switch (c.tipo) {
      case "texto": case "email":
        return envoltura(c, `<input id="${id}" data-k="${c.k}" type="${c.tipo === "email" ? "email" : "text"}" value="${escapar(v == null ? "" : v)}" maxlength="${c.max || 255}" ${req} ${desc} autocomplete="off" ${c.mayus ? 'style="text-transform:uppercase"' : ""}>`, id);
      case "area":
        return envoltura(c, `<textarea id="${id}" data-k="${c.k}" maxlength="${c.max || 255}" ${req} ${desc}>${escapar(v == null ? "" : v)}</textarea>`, id);
      case "select": {
        const ops = c.opciones_kv || c.opciones.map((o) => [o, o]);
        const html = ops.map(([val, txt]) => `<option value="${escapar(val)}" ${String(v) === String(val) ? "selected" : ""}>${escapar(txt)}</option>`).join("");
        return envoltura(c, `<select id="${id}" data-k="${c.k}" ${req} ${desc}><option value="">Selecciona una opción</option>${html}</select>`, id);
      }
      case "estado": {
        const act = modo === "crear" ? true : item.activo;
        return envoltura(c, `<select id="${id}" data-k="activo" ${desc}><option value="true" ${act ? "selected" : ""}>${escapar(cfg.estados[0])}</option><option value="false" ${act ? "" : "selected"}>${escapar(cfg.estados[1])}</option></select>`, id);
      }
      case "select_remoto": {
        const ops = await opcionesRemotas(c.url);
        if (c.k === "rol_id") alcanceRoles = Object.fromEntries(ops.map((o) => [o.id, o.alcance]));
        let html = ops.map((o) => `<option value="${o.id}" ${Number(v) === o.id ? "selected" : ""}>${escapar(o.texto)}</option>`).join("");
        // conserva el valor actual aunque ya no sea asignable (p. ej. tipo inactivo)
        if (v && !ops.some((o) => o.id === Number(v))) {
          const nombre = item.rol || item.tipo_nombre || `#${v}`;
          html += `<option value="${v}" selected>${escapar(nombre)} (actual)</option>`;
        }
        return envoltura(c, `<select id="${id}" data-k="${c.k}" ${req} ${desc}><option value="">Selecciona una opción</option>${html}</select>`, id);
      }
      case "checks_remoto": {
        const ops = await opcionesRemotas(c.url);
        const marcadas = new Set(item[c.k] || item.delegaciones_ids || []);
        const html = ops.map((o) => `<label><input type="checkbox" name="${c.k}" value="${o.id}" ${marcadas.has(o.id) ? "checked" : ""}> ${escapar(o.texto)}</label>`).join("");
        return `<fieldset class="campo" data-campo="${c.k}"><legend>${escapar(c.t)}${obligatorio(c) ? ' <span class="req" aria-hidden="true">*</span>' : ""}</legend>
          <div class="checks" id="${id}">${html}</div><div class="ayuda" id="ay-${c.k}">${escapar(c.ayuda || "")}</div><div class="error-campo" id="err-${c.k}" role="alert"></div></fieldset>`;
      }
      case "password":
        return envoltura(c, `<div class="fila-clave"><input id="${id}" data-k="${c.k}" type="password" maxlength="128" autocomplete="new-password" ${req} ${desc}>
          <button type="button" class="btn" data-mostrar="${id}" aria-pressed="false" aria-controls="${id}">Mostrar</button></div>`, id);
      case "permisos":
        return `<fieldset class="campo" data-campo="permisos"><legend>${escapar(c.t)} <span class="req" aria-hidden="true">*</span></legend>
          ${await matrizPermisos(item.permisos, false)}<div class="error-campo" id="err-permisos" role="alert"></div></fieldset>`;
      default: return "";
    }
  }

  function aplicarReglaAlcance() {
    const rol = $("f-rol_id");
    const checks = cuerpo.querySelectorAll('input[name="delegaciones_ids"]');
    if (!rol || !checks.length) return;
    rol.addEventListener("change", () => { if (alcanceRoles[rol.value] === "UNA") { let visto = false; checks.forEach((c) => { if (c.checked && visto) c.checked = false; if (c.checked) visto = true; }); } });
    checks.forEach((c) => c.addEventListener("change", () => {
      if (alcanceRoles[rol.value] === "UNA" && c.checked) checks.forEach((o) => { if (o !== c) o.checked = false; });
    }));
  }

  function enlazarMatriz() {
    cuerpo.querySelectorAll("input[data-perm]").forEach((chk) => chk.addEventListener("change", () => {
      const [mod, acc] = chk.dataset.perm.split(":");
      const ver = cuerpo.querySelector(`input[data-perm="${mod}:ver"]`);
      if (acc !== "ver" && chk.checked && ver && !ver.disabled) ver.checked = true;
      if (acc === "ver" && !chk.checked) cuerpo.querySelectorAll(`input[data-perm^="${mod}:"]`).forEach((o) => { if (!o.disabled) o.checked = false; });
    }));
  }

  function enlazarMayusculas() {
    cuerpo.querySelectorAll("input[data-k]").forEach((i) => {
      if (i.style.textTransform === "uppercase") i.addEventListener("blur", () => { i.value = i.value.trim().toUpperCase(); });
    });
  }

  async function vistaDetalle(item) {
    const filas = [];
    for (const [k, t] of cfg.vista) {
      if (k === "permisos") {
        filas.push(`<dt>${escapar(t)}</dt><dd>${await matrizPermisos(item.permisos, true)}</dd>`);
        continue;
      }
      let v = item[k];
      if (Array.isArray(v)) v = v.join(", ");
      filas.push(`<dt>${escapar(t)}</dt><dd>${v === "" || v == null ? "—" : escapar(v)}</dd>`);
    }
    return `<dl class="dato-vista">${filas.join("")}</dl>`;
  }

  async function abrir(m, id) {
    modo = m; idActual = id || null;
    window.SGR.sucio = false;
    let item = { activo: true };
    try {
      if (id) item = await filaPorId(id);
    } catch (e) { msg.desdeError(e, "No se pudo abrir el registro"); cargar(); return; }
    $("modal-titulo").textContent = tituloModo[m];
    cuerpo.innerHTML = `<div class="cargando"><span class="girando" aria-hidden="true"></span>Cargando formulario...</div>`;
    pie.innerHTML = "";
    if (!modal.open) modal.showModal();
    try {
      if (m === "ver") {
        cuerpo.innerHTML = await vistaDetalle(item);
        pie.innerHTML = `<button type="button" class="btn" data-modal="cerrar">Cerrar</button>` +
          (!cfg.solo_lectura && cfg.puede.editar ? `<button type="button" class="btn btn-primario" data-modal="editar">Editar</button>` : "");
      } else {
        const partes = [`<p class="ayuda" style="margin-top:0">Los campos con <span class="req">*</span> son obligatorios.</p>`];
        for (const c of cfg.campos) partes.push(await construirCampo(c, item));
        cuerpo.innerHTML = partes.join("");
        pie.innerHTML = `<button type="button" class="btn" data-modal="cancelar">Cancelar</button><button type="submit" class="btn btn-primario" id="btn-guardar">Guardar</button>`;
        enlazarMatriz(); aplicarReglaAlcance(); enlazarMayusculas();
        const primero = cuerpo.querySelector("input:not([disabled]), select, textarea");
        if (primero) primero.focus();
      }
    } catch (e) {
      cuerpo.innerHTML = `<div class="estado-vacio" role="alert">${ICONO("alerta")}<h3>No se pudo preparar el formulario</h3><p>${escapar(e.message)}</p></div>`;
      pie.innerHTML = `<button type="button" class="btn" data-modal="cerrar">Cerrar</button>`;
    }
  }

  async function cerrar(forzar) {
    if (!forzar && window.SGR.sucio) {
      const ok = await msg.confirmar({ titulo: "¿Descartar los cambios?", texto: "Tienes datos sin guardar. Si cierras el formulario se perderán.",
        si: "Descartar cambios", no: "Seguir editando", peligro: true });
      if (!ok) return;
    }
    window.SGR.sucio = false;
    if (modal.open) modal.close();
  }
  modal.addEventListener("cancel", (e) => { e.preventDefault(); cerrar(false); });
  $("modal-cerrar").addEventListener("click", () => cerrar(false));
  pie.addEventListener("click", (e) => {
    const b = e.target.closest("[data-modal]");
    if (!b) return;
    if (b.dataset.modal === "editar") abrir("editar", idActual);
    else cerrar(false);
  });
  cuerpo.addEventListener("input", () => { if (modo !== "ver") window.SGR.sucio = true; });
  cuerpo.addEventListener("change", () => { if (modo !== "ver") window.SGR.sucio = true; });

  const btnNuevo = $("btn-nuevo");
  if (btnNuevo) btnNuevo.addEventListener("click", () => abrir("crear"));

  /* ------------------------ lectura y validación del formulario ------------------------ */
  function leerFormulario() {
    const v = {};
    cfg.campos.forEach((c) => {
      if (c.tipo === "checks_remoto") v[c.k] = Array.from(cuerpo.querySelectorAll(`input[name="${c.k}"]:checked`)).map((i) => Number(i.value));
      else if (c.tipo === "permisos") v[c.k] = Array.from(cuerpo.querySelectorAll("input[data-perm]:checked")).map((i) => i.dataset.perm);
      else if (c.tipo === "estado") v.activo = cuerpo.querySelector('[data-k="activo"]').value === "true";
      else if (c.tipo === "select_remoto") { const x = cuerpo.querySelector(`[data-k="${c.k}"]`).value; v[c.k] = x ? Number(x) : ""; }
      else {
        const el = cuerpo.querySelector(`[data-k="${c.k}"]`);
        let val = el.value;
        if (c.tipo !== "password") val = val.trim();
        if (c.mayus) val = val.toUpperCase();
        v[c.k] = val;
      }
    });
    return v;
  }

  function validarLocal(v) {
    const e = {}, re = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$/;
    cfg.campos.forEach((c) => {
      const val = v[c.k === "activo" ? "activo" : c.k];
      if (c.tipo === "estado") return;
      if (c.tipo === "checks_remoto") { if (obligatorio(c) && !val.length) e[c.k] = "Selecciona al menos una opción."; return; }
      if (c.tipo === "permisos") { if (!val.length) e[c.k] = "Selecciona al menos un permiso."; return; }
      if (c.tipo === "password") {
        if (modo === "crear" && !val) e[c.k] = "Ingresa una contraseña.";
        else if (val) { const m = window.SGR.errorPassword(val); if (m) e[c.k] = m; }
        return;
      }
      if (obligatorio(c) && (val === "" || val == null)) { e[c.k] = c.tipo === "select" || c.tipo === "select_remoto" ? "Selecciona una opción." : "Este campo es obligatorio."; return; }
      if (c.tipo === "email" && val && !re.test(val)) e[c.k] = "Escribe un correo válido, por ejemplo nombre@dominio.cl.";
    });
    return e;
  }

  function mostrarErrores(errs) {
    cuerpo.querySelectorAll(".error-campo").forEach((n) => { n.textContent = ""; });
    cuerpo.querySelectorAll("[aria-invalid]").forEach((n) => n.removeAttribute("aria-invalid"));
    let primero = null;
    Object.keys(errs || {}).forEach((k) => {
      const caja = $(`err-${k}`);
      if (!caja) return;
      caja.textContent = errs[k];
      const campo = cuerpo.querySelector(`[data-k="${k}"]`) || cuerpo.querySelector(`[name="${k}"]`) || $(`f-${k}`);
      if (campo) { campo.setAttribute("aria-invalid", "true"); if (!primero) primero = campo; }
    });
    if (primero) primero.focus();
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (modo === "ver" || enviando) return; // evita doble envío
    const valores = leerFormulario();
    const locales = validarLocal(valores);
    mostrarErrores(locales);
    if (Object.keys(locales).length) {
      msg.aviso("Revisa los campos", "Hay datos obligatorios o con formato incorrecto. Corrige los campos marcados y guarda de nuevo.");
      return;
    }
    enviando = true;
    const botones = pie.querySelectorAll("button");
    botones.forEach((b) => { b.disabled = true; });
    const guardar = $("btn-guardar"); const textoOriginal = guardar.textContent; guardar.textContent = "Guardando...";
    try {
      const r = modo === "crear"
        ? await api(`/api/${cfg.slug}`, { method: "POST", body: valores })
        : await api(`/api/${cfg.slug}/${idActual}`, { method: "PUT", body: valores });
      window.SGR.sucio = false;
      cerrar(true);
      await msg.exito(modo === "crear" ? "Registro creado" : "Cambios guardados", r.mensaje);
      cargar();
    } catch (e) {
      if (e.campos) mostrarErrores(e.campos);
      msg.desdeError(e, e.status === 409 ? "No se pudo guardar" : undefined);
    } finally {
      enviando = false;
      botones.forEach((b) => { b.disabled = false; });
      guardar.textContent = textoOriginal;
    }
  });

  window.SGRLista = { recargar: cargar };
  cargar();
})();
