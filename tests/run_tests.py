#!/usr/bin/env python3
"""Ejecuta la suite y guarda evidencia en evidencias/resultados_automaticos.md (y .json)."""
import json, os, sys, unittest
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ); sys.path.insert(0, os.path.join(RAIZ, "tests"))
import test_sgr  # noqa: E402


class R(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.filas = []
    def _add(self, t, estado, detalle=""):
        self.filas.append({"id": t._testMethodName.split("_")[1] + "-" + t._testMethodName.split("_")[2] + "-" + t._testMethodName.split("_")[3],
                           "prueba": t._testMethodName, "descripcion": (t._testMethodDoc or "").strip().split("\n")[0],
                           "estado": estado, "detalle": detalle[:300]})
    def addSuccess(self, t): super().addSuccess(t); self._add(t, "Aprobada")
    def addFailure(self, t, e): super().addFailure(t, e); self._add(t, "Fallida", self._exc_info_to_string(e, t))
    def addError(self, t, e): super().addError(t, e); self._add(t, "Error", self._exc_info_to_string(e, t))


suite = unittest.defaultTestLoader.loadTestsFromModule(test_sgr)
res = unittest.TextTestRunner(resultclass=R, verbosity=1).run(suite)
os.makedirs(os.path.join(RAIZ, "evidencias"), exist_ok=True)
ahora = datetime.now().strftime("%d-%m-%Y %H:%M")
ap = sum(f["estado"] == "Aprobada" for f in res.filas)
with open(os.path.join(RAIZ, "evidencias", "resultados_automaticos.json"), "w", encoding="utf-8") as fh:
    json.dump({"fecha": ahora, "total": len(res.filas), "aprobadas": ap, "filas": res.filas}, fh, ensure_ascii=False, indent=1)
with open(os.path.join(RAIZ, "evidencias", "resultados_automaticos.md"), "w", encoding="utf-8") as fh:
    fh.write(f"# Resultados de pruebas automáticas\n\nEjecución: {ahora} · Entorno: local (SQLite temporal, cliente de pruebas Flask)\n\n")
    fh.write(f"**{ap} de {len(res.filas)} pruebas aprobadas.**\n\n| Prueba | Descripción | Resultado |\n|---|---|---|\n")
    for f in sorted(res.filas, key=lambda x: x["prueba"]):
        fh.write(f"| {f['prueba']} | {f['descripcion'].replace('|', '/')} | {f['estado']} |\n")
sys.exit(0 if res.wasSuccessful() else 1)
