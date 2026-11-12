"""Lectura del calendario oficial UAI (uaidocs) y generación de .ics.

Lo usan las funciones de /api. Los archivos que empiezan con "_" no son rutas públicas en Vercel.
"""
from __future__ import annotations

import io
import re
import time as _time
import unicodedata
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import openpyxl

BASE = "https://uaidocs.z20.web.core.windows.net"
FUENTES = {
    "pruebas": f"{BASE}/pruebas/",
    "examenes": f"{BASE}/examenes/",
}
TZ = ZoneInfo("America/Santiago")
CALENDAR_NAME = "UAI Evaluaciones"
CACHE_SEGUNDOS = 30 * 60

_cache: dict = {"t": 0.0, "data": None}


@dataclass
class Evaluacion:
    uid: str
    tipo: str
    sigla: str
    seccion: int
    asignatura: str
    profesor: str
    sede: str  # texto original
    sede_id: str  # "santiago" | "vina" | otro
    inicio: datetime
    fin: datetime

    @property
    def titulo(self) -> str:
        return f"{self.tipo}: {bonito(self.asignatura)} ({self.sigla}-{self.seccion})"

    def to_json(self) -> dict:
        d = asdict(self)
        d["asignatura"] = bonito(self.asignatura)
        d["inicio"] = self.inicio.isoformat()
        d["fin"] = self.fin.isoformat()
        return d


# ---------- utilidades ----------

_MINUSC = {"y", "e", "o", "u", "de", "del", "la", "las", "el", "los", "en", "a", "al", "para", "por", "con"}
_MAYUSC = {"ti", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}


def bonito(s: str) -> str:
    """'CORE: LITERATURA Y HUMANIDADES II' -> 'Core: Literatura y Humanidades II'"""
    out = []
    for i, w in enumerate(str(s).split()):
        lw = w.lower()
        if lw.strip(":,.") in _MAYUSC:
            out.append(w.upper())
        elif i > 0 and lw in _MINUSC:
            out.append(lw)
        else:
            out.append(lw[:1].upper() + lw[1:])
    return " ".join(out)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def sede_canonica(s: str) -> str:
    n = norm(s)
    if "vina" in n:
        return "vina"
    if "santiago" in n or "penalolen" in n:
        return "santiago"
    return n


def _hora(s) -> time:
    h, m = str(s).strip().split(":")[:2]
    return time(int(h), int(m))


def _fecha(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Fecha no reconocida: {v!r}")


def _at(d: date, t: time) -> datetime:
    return datetime.combine(d, t, tzinfo=TZ)


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "uai-calendario/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def _xlsx(url: str) -> list[dict]:
    ws = openpyxl.load_workbook(io.BytesIO(_get(url)), read_only=True).worksheets[0]
    ws.reset_dimensions()  # el archivo trae dimensiones incorrectas
    rows = [r for r in ws.iter_rows(values_only=True) if any(c is not None for c in r)]
    if not rows:
        raise RuntimeError(f"Excel vacío: {url}")
    hdr = [str(h).strip() if h is not None else "" for h in rows[0]]
    return [dict(zip(hdr, r)) for r in rows[1:]]


def _col(row: dict, *nombres: str):
    for n in nombres:
        if n in row:
            return row[n]
    raise KeyError(f"No encontré la columna {nombres} (columnas: {list(row)}). ¿Cambió el formato del Excel?")


def _actualizado(url: str) -> str | None:
    """Lee 'Actualizado el dd-mm-aaaa' de la página HTML."""
    try:
        m = re.search(r"Actualizado el\s*([0-9]{1,2}-[0-9]{1,2}-[0-9]{4})", _get(url).decode("utf-8", "ignore"))
        return m.group(1) if m else None
    except Exception:
        return None


# ---------- fuentes ----------

def _pruebas() -> list[Evaluacion]:
    out = []
    for r in _xlsx(FUENTES["pruebas"] + "pruebas.xlsx"):
        sigla = str(_col(r, "Sigla")).strip().upper()
        sec = int(_col(r, "Sec.", "Sección", "Seccion"))
        sede = str(_col(r, "Sede")).strip()
        d = _fecha(_col(r, "Fecha"))
        out.append(Evaluacion(
            uid=f"prueba-{sigla}-{sec}-{sede_canonica(sede)}-{d.isoformat()}",
            tipo="Prueba", sigla=sigla, seccion=sec,
            asignatura=str(_col(r, "Asignatura")).strip(), profesor=str(_col(r, "Prof.", "Profesor")).strip(),
            sede=sede, sede_id=sede_canonica(sede),
            inicio=_at(d, _hora(_col(r, "Hora Inicio"))), fin=_at(d, _hora(_col(r, "Hora Fin"))),
        ))
    return out


def _examenes() -> list[Evaluacion]:
    out = []
    for r in _xlsx(FUENTES["examenes"] + "examenes.xlsx"):
        sigla = str(_col(r, "Sigla")).strip().upper()
        sec = int(_col(r, "Sección", "Seccion", "Sec."))
        sede = str(_col(r, "Sede", "Unidad Académica")).strip()
        d = _fecha(_col(r, "Fecha"))
        h_ini, h_fin = [x.strip() for x in str(_col(r, "Hora")).split("-")]
        tipo_ex = str(_col(r, "TipoExamen", "Tipo Examen") or "").strip()
        out.append(Evaluacion(
            uid=f"examen-{_col(r, 'Id')}",  # Id estable: si cambia la fecha se actualiza el mismo evento
            tipo=f"Examen {tipo_ex}".strip(), sigla=sigla, seccion=sec,
            asignatura=str(_col(r, "Asignatura")).strip(), profesor=str(_col(r, "Profesor")).strip(),
            sede=sede, sede_id=sede_canonica(sede),
            inicio=_at(d, _hora(h_ini)), fin=_at(d, _hora(h_fin)),
        ))
    return out


def cargar() -> dict:
    """Todas las evaluaciones + fechas de actualización (con caché en memoria)."""
    if _cache["data"] is not None and _time.time() - _cache["t"] < CACHE_SEGUNDOS:
        return _cache["data"]
    data = {
        "evaluaciones": sorted(_pruebas() + _examenes(), key=lambda e: e.inicio),
        "actualizado": {k: _actualizado(u) for k, u in FUENTES.items()},
        "descargado": datetime.now(TZ).isoformat(timespec="minutes"),
    }
    _cache.update(t=_time.time(), data=data)
    return data


# ---------- filtros y .ics ----------

def parse_ramos(texto: str) -> list[tuple[str, int]]:
    """'TICS312-1,TICS400-1' → [('TICS312', 1), ('TICS400', 1)]. La sección va después del ÚLTIMO guion
    (hay siglas que llevan guion, ej. 'ABC123-1-2' = sigla ABC123-1, sección 2)."""
    out = []
    for item in re.split(r"[,;]+", texto or ""):
        item = item.strip().upper()
        if "-" not in item:
            continue
        sigla, sec = item.rsplit("-", 1)
        sec = sec.strip().lstrip("S")
        if sigla.strip() and sec.isdigit():
            par = (sigla.replace(" ", ""), int(sec))
            if par not in out:
                out.append(par)
    return out


def filtrar(evals: list[Evaluacion], ramos: list[tuple[str, int]], sede: str | None) -> list[Evaluacion]:
    want = set(ramos)
    return [e for e in evals if (e.sigla, e.seccion) in want and (not sede or e.sede_id == sede)]


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Corta líneas a 75 bytes como pide el estándar iCalendar."""
    b = line.encode("utf-8")
    if len(b) <= 75:
        return line
    parts, cur = [], b""
    for ch in line:
        c = ch.encode("utf-8")
        if len(cur) + len(c) > (75 if not parts else 74):
            parts.append(cur.decode("utf-8"))
            cur = b""
        cur += c
    parts.append(cur.decode("utf-8"))
    return "\r\n ".join(parts)


def generar_ics(evals: list[Evaluacion], alarmas: list[int]) -> str:
    utc = ZoneInfo("UTC")
    fmt = "%Y%m%dT%H%M%SZ"
    stamp = datetime.now(utc).strftime(fmt)
    L = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//uai-calendario//ES", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH", f"X-WR-CALNAME:{CALENDAR_NAME}", "X-WR-TIMEZONE:America/Santiago",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H",
    ]
    for e in evals:
        notas = (f"{e.sigla} sección {e.seccion}\nProfesor: {e.profesor}\nSede: {e.sede}\n"
                 "Fuente: calendario oficial UAI (las fechas pueden cambiar).")
        L += [
            "BEGIN:VEVENT",
            f"UID:{e.uid}@uai-calendario",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{e.inicio.astimezone(utc).strftime(fmt)}",
            f"DTEND:{e.fin.astimezone(utc).strftime(fmt)}",
            f"SUMMARY:{_esc(e.titulo)}",
            f"DESCRIPTION:{_esc(notas)}",
            f"LOCATION:{_esc(e.sede)}",
        ]
        for m in alarmas:
            L += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(e.titulo)}",
                  f"TRIGGER:-PT{int(m)}M", "END:VALARM"]
        L.append("END:VEVENT")
    L.append("END:VCALENDAR")
    return "\r\n".join(_fold(x) for x in L) + "\r\n"
