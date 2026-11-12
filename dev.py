"""Servidor local para probar la página: python dev.py  →  http://localhost:8000"""
import importlib.util
import os
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("index", os.path.join(ROOT, "api", "index.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    print("Abre http://localhost:8000  (Ctrl+C para salir)")
    ThreadingHTTPServer(("127.0.0.1", 8000), mod.handler).serve_forever()
