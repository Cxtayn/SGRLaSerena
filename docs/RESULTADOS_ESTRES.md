# Registro de la prueba de estrés (plantilla a completar con la ejecución en AWS)

> **Estado: pendiente.** El script se validó en local solo para comprobar su funcionamiento; esas cifras no son resultados de la entrega.

## Definición previa (completar ANTES de ejecutar)
- Herramienta: `tests/stress/stress_test.py` (alternativa: Locust/JMeter/k6)
- Entorno AWS: tipo de instancia ____ · región ____ · almacenamiento ____ · versión/commit desplegado ____
- Volumen de datos: ____ atenciones, ____ vecinos (`python manage.py init-db --demo --volumen N`)
- Escenarios: listado, búsqueda, registro de atención, exportación a Excel (mezcla 5:3:2:1)
- Cuenta usada: `delegado` · Etapas de concurrencia: 1, 5, 10, 25, 50 · Duración por etapa: 30 s
- Umbrales de aceptación: p95 ≤ ____ ms · errores ≤ ____ % · CPU ≤ ____ %

## Comando
```
python tests/stress/stress_test.py --base https://TU-DOMINIO --usuario delegado --clave '...' \
  --etapas 1,5,10,25,50 --duracion 30 --umbral-p95 800 --umbral-errores 1 --salida evidencias/estres_aws
```

## Resultados (copiar de `evidencias/estres_aws.md`)
| Concurrencia | Duración (s) | Solicitudes | Req/s | Prom. (ms) | p95 (ms) | Errores % | CPU % | Mem % | Resultado |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

## Análisis
- Punto de degradación observado: ____
- Cuello de botella (CPU, memoria, SQLite, red): ____
- Recuperación tras la carga: ____
- Medidas tomadas y nueva medición: ____

(CPU y memoria: obtener de CloudWatch o `top`/`htop` en la instancia durante la prueba.)
