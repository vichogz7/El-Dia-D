"""Punto de entrada único (Vercel): atiende todas las rutas.

    /                      → la página (public/index.html)
    /api/evaluaciones      → JSON con todas las pruebas y exámenes publicados
    /calendario.ics?r=...  → calendario personal para suscribirse (también /api/calendario)

Parámetros de /calendario.ics: r=TICS312-1,TICS400-1  sede=santiago|vina  alarmas=1440,60  descargar=1
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import _uai  # noqa: E402

PUBLIC = os.path.join(os.path.dirname(AQUI), "public")
CACHE = "public, s-maxage=1800, stale-while-revalidate=86400"


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        ruta = url.path.rstrip("/") or "/"
        q = parse_qs(url.query)
        if ruta == "/api/evaluaciones":
            return self._evaluaciones()
        if ruta in ("/calendario.ics", "/api/calendario"):
            return self._calendario(q)
        if ruta in ("/", "/index.html"):
            try:  # normalmente Vercel sirve public/ directo; esto es por si la petición llega aquí
                with open(os.path.join(PUBLIC, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8", {"Cache-Control": "public, max-age=300"})
            except OSError:
                pass
        return self._send(404, "No encontrado".encode(), "text/plain; charset=utf-8")

    def _evaluaciones(self):
        try:
            d = _uai.cargar()
            body = json.dumps({
                "actualizado": d["actualizado"],
                "descargado": d["descargado"],
                "evaluaciones": [e.to_json() for e in d["evaluaciones"]],
            }, ensure_ascii=False).encode()
        except Exception as ex:  # noqa: BLE001
            return self._send(502, json.dumps({"error": str(ex)}).encode(), "application/json; charset=utf-8")
        self._send(200, body, "application/json; charset=utf-8", {"Cache-Control": CACHE})

    def _calendario(self, q: dict):
        ramos = _uai.parse_ramos(q.get("r", [""])[0])
        sede = q.get("sede", [""])[0].lower() or None
        alarmas = [int(x) for x in q.get("alarmas", [""])[0].split(",") if x.strip().isdigit()][:3]
        if not ramos:
            return self._send(400, "Falta ?r=SIGLA-SECCION,... (ej: ?r=TICS312-1,TICS400-1)".encode(),
                              "text/plain; charset=utf-8")
        try:
            evals = _uai.filtrar(_uai.cargar()["evaluaciones"], ramos, sede)
            body = _uai.generar_ics(evals, alarmas).encode("utf-8")
        except Exception as ex:  # noqa: BLE001
            return self._send(502, f"No se pudo leer el calendario UAI: {ex}".encode(), "text/plain; charset=utf-8")
        disp = "attachment" if q.get("descargar") else "inline"
        self._send(200, body, "text/calendar; charset=utf-8", {
            "Content-Disposition": f'{disp}; filename="uai-evaluaciones.ics"',
            "Cache-Control": CACHE,
        })
