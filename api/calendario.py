"""GET /api/calendario?r=TICS312-1,TICS400-1&sede=santiago&alarmas=1440,60[&descargar=1]

Devuelve un .ics. Si te suscribes a esta URL, tu calendario se actualiza solo.
"""
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(__file__))
import _uai  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        ramos = _uai.parse_ramos(q.get("r", [""])[0])
        sede = q.get("sede", [""])[0].lower() or None
        alarmas = [int(x) for x in q.get("alarmas", [""])[0].split(",") if x.strip().isdigit()][:3]
        if not ramos:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Falta ?r=SIGLA-SECCION,... (ej: ?r=TICS312-1,TICS400-1)".encode())
            return
        try:
            evals = _uai.filtrar(_uai.cargar()["evaluaciones"], ramos, sede)
            body = _uai.generar_ics(evals, alarmas).encode("utf-8")
        except Exception as ex:  # noqa: BLE001
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"No se pudo leer el calendario UAI: {ex}".encode())
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/calendar; charset=utf-8")
        disp = "attachment" if q.get("descargar") else "inline"
        self.send_header("Content-Disposition", f'{disp}; filename="uai-evaluaciones.ics"')
        self.send_header("Cache-Control", "public, s-maxage=1800, stale-while-revalidate=86400")
        self.end_headers()
        self.wfile.write(body)
