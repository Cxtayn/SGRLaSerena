#!/usr/bin/env python3
"""Prueba de estrés escalonada (solo librería estándar).

Aumenta la concurrencia por etapas y, en cada etapa, ejecuta una mezcla de operaciones
reales: login, listado, búsqueda, exportación a Excel y registro de atención.
Registra solicitudes/s, latencia promedio, p95, errores y, si se pide, CPU/memoria local.

Uso (contra el despliegue AWS):
  python tests/stress/stress_test.py --base https://TU-DOMINIO --usuario delegado --clave 'Demo#2026Sgr!' \
      --etapas 1,5,10,25,50 --duracion 30 --umbral-p95 800 --umbral-errores 1 --salida evidencias/estres_aws

NO ejecutar contra sistemas de terceros ni sin autorización. Los resultados de un servidor local NO
sustituyen la prueba en AWS exigida por la rúbrica."""
import argparse
import http.cookiejar
import json
import re
import statistics
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime


class Sesion:
    def __init__(self, base, usuario, clave):
        self.base = base.rstrip("/")
        self.cj = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.tok = ""
        self._login(usuario, clave)

    def _pedir(self, metodo, ruta, cuerpo=None, leer=True):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(self.base + ruta, data=datos, method=metodo,
                                     headers={"Content-Type": "application/json", "X-CSRF-Token": self.tok})
        with self.op.open(req, timeout=30) as r:
            return r.status, (r.read() if leer else b"")

    def _token(self, ruta):
        _, html = self._pedir("GET", ruta)
        m = re.search(rb'csrf-token" content="([^"]+)"', html)
        if m:
            self.tok = m.group(1).decode()

    def _login(self, usuario, clave):
        self._token("/login")
        self._pedir("POST", "/api/auth/login", {"usuario": usuario, "password": clave})
        self._token("/")
        _, op = self._pedir("GET", "/api/atencion/opciones")
        o = json.loads(op)
        self.sub = o["subtipos"][0]
        self.vecino = 1

    def op_listado(self):
        return self._pedir("GET", "/api/atenciones?page=1&per_page=10")

    def op_busqueda(self):
        return self._pedir("GET", "/api/atenciones?q=prueba&per_page=25")

    def op_exportar(self):
        return self._pedir("GET", "/api/atenciones/exportar?q=prueba")

    def op_registrar(self):
        return self._pedir("POST", "/api/atenciones", {
            "vecino_id": self.vecino, "tipo_id": self.sub["tipo_id"], "subtipo_id": self.sub["id"],
            "descripcion": "Atención generada por la prueba de estrés.", "token_envio": uuid.uuid4().hex})


MEZCLA = ["op_listado"] * 5 + ["op_busqueda"] * 3 + ["op_registrar"] * 2 + ["op_exportar"]


def etapa(args, concurrencia):
    lat, errores, codigos = [], [], {}
    lock = threading.Lock()
    fin = time.time() + args.duracion

    def trabajador(n):
        try:
            s = Sesion(args.base, args.usuario, args.clave)
        except Exception as e:  # noqa: BLE001
            with lock:
                errores.append(f"login: {e}")
            return
        i = n
        while time.time() < fin:
            op = MEZCLA[i % len(MEZCLA)]
            i += 1
            t0 = time.perf_counter()
            try:
                codigo, _ = getattr(s, op)()
            except urllib.error.HTTPError as e:
                codigo = e.code
            except Exception as e:  # noqa: BLE001
                codigo = 0
                with lock:
                    errores.append(f"{op}: {e}")
            dt = (time.perf_counter() - t0) * 1000
            with lock:
                lat.append(dt)
                codigos[codigo] = codigos.get(codigo, 0) + 1

    hilos = [threading.Thread(target=trabajador, args=(k,)) for k in range(concurrencia)]
    t0 = time.time()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    dur = time.time() - t0
    malos = sum(v for c, v in codigos.items() if not (200 <= c < 300))
    lat.sort()
    p95 = lat[int(len(lat) * 0.95) - 1] if lat else 0
    return {"concurrencia": concurrencia, "duracion_s": round(dur, 1), "solicitudes": len(lat),
            "rps": round(len(lat) / dur, 1) if dur else 0, "lat_prom_ms": round(statistics.mean(lat), 1) if lat else 0,
            "p95_ms": round(p95, 1), "errores": malos, "pct_errores": round(100 * malos / len(lat), 2) if lat else 100,
            "codigos": codigos, "muestra_errores": errores[:3]}


def recursos_locales():
    try:
        import psutil  # opcional
        return {"cpu_pct": psutil.cpu_percent(interval=0.5), "mem_pct": psutil.virtual_memory().percent}
    except Exception:  # noqa: BLE001
        return {}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--usuario", default="delegado")  # necesita permisos de crear y exportar atenciones
    p.add_argument("--clave", required=True)
    p.add_argument("--etapas", default="1,5,10,25,50")
    p.add_argument("--duracion", type=int, default=30)
    p.add_argument("--umbral-p95", type=float, default=800.0, help="ms")
    p.add_argument("--umbral-errores", type=float, default=1.0, help="%% de solicitudes con error")
    p.add_argument("--salida", default="evidencias/estres")
    args = p.parse_args()
    resultados, limite = [], None
    for c in [int(x) for x in args.etapas.split(",")]:
        print(f"Etapa con {c} usuarios concurrentes durante {args.duracion}s ...", flush=True)
        r = etapa(args, c)
        r.update(recursos_locales())
        r["cumple"] = r["p95_ms"] <= args.umbral_p95 and r["pct_errores"] <= args.umbral_errores
        resultados.append(r)
        print(f"  rps={r['rps']} prom={r['lat_prom_ms']}ms p95={r['p95_ms']}ms errores={r['pct_errores']}% -> {'CUMPLE' if r['cumple'] else 'NO CUMPLE'}")
        if not r["cumple"]:
            limite = c
            break  # degradación observada: se detiene la escalada
    # recuperación: una carga mínima tras la prueba
    rec = etapa(argparse.Namespace(**{**vars(args), "duracion": 10}), 1)
    informe = {"fecha": datetime.now().isoformat(timespec="seconds"), "base": args.base, "usuario": args.usuario,
               "umbral_p95_ms": args.umbral_p95, "umbral_errores_pct": args.umbral_errores,
               "limite_observado": limite, "etapas": resultados, "recuperacion": rec}
    with open(args.salida + ".json", "w", encoding="utf-8") as fh:
        json.dump(informe, fh, ensure_ascii=False, indent=1)
    with open(args.salida + ".md", "w", encoding="utf-8") as fh:
        fh.write(f"# Resultado de prueba de estrés\n\nFecha: {informe['fecha']}  \nObjetivo: {args.base}\n\n")
        fh.write(f"Umbrales: p95 ≤ {args.umbral_p95} ms; errores ≤ {args.umbral_errores} %\n\n")
        fh.write("| Concurrencia | Duración (s) | Solicitudes | Req/s | Prom. (ms) | p95 (ms) | Errores % | Resultado |\n|---|---|---|---|---|---|---|---|\n")
        for r in resultados:
            fh.write(f"| {r['concurrencia']} | {r['duracion_s']} | {r['solicitudes']} | {r['rps']} | {r['lat_prom_ms']} | {r['p95_ms']} | {r['pct_errores']} | {'Cumple' if r['cumple'] else 'No cumple'} |\n")
        fh.write(f"\nLímite observado: {limite or 'no se alcanzó degradación en las etapas ejecutadas'}\n")
        fh.write(f"\nRecuperación (1 usuario, 10 s): p95 = {rec['p95_ms']} ms, errores = {rec['pct_errores']} %\n")
    print("Informe:", args.salida + ".md")


if __name__ == "__main__":
    main()
