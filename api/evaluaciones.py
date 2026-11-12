"""GET /api/evaluaciones → JSON con todas las pruebas y exámenes publicados (lo usa la página)."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
import _uai  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            d = _uai.cargar()
            body = json.dumps({
                "actualizado": d["actualizado"],
                "descargado": d["descargado"],
                "evaluaciones": [e.to_json() for e in d["evaluaciones"]],
            }, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            # caché en el CDN de Vercel: 30 min, y sirve la copia anterior mientras refresca
            self.send_header("Cache-Control", "public, s-maxage=1800, stale-while-revalidate=86400")
        except Exception as ex:  # noqa: BLE001
            body = json.dumps({"error": str(ex)}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)
