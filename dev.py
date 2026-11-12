"""Servidor local para probar la página: python dev.py  →  http://localhost:8000"""
import importlib.util
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))


def cargar_handler(nombre):
    spec = importlib.util.spec_from_file_location(nombre, os.path.join(ROOT, "api", nombre + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.handler


API = {"/api/evaluaciones": cargar_handler("evaluaciones"), "/api/calendario": cargar_handler("calendario")}
API["/calendario.ics"] = API["/api/calendario"]


class Dev(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=os.path.join(ROOT, "public"), **k)

    def do_GET(self):
        h = API.get(self.path.split("?")[0])
        if h:
            h.do_GET(self)
        else:
            super().do_GET()


if __name__ == "__main__":
    print("http://localhost:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Dev).serve_forever()
