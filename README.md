# 📅 Calendario de evaluaciones UAI

Página web para ver tus **pruebas y exámenes UAI** en una tabla y agregarlos a tu calendario
(**iPhone/Mac, Google Calendar u Outlook**) con un link que **se actualiza solo** cuando la UAI cambia una fecha.

> Herramienta **no oficial** hecha por estudiantes. Usa los datos públicos de
> [pruebas](https://uaidocs.z20.web.core.windows.net/pruebas/) y
> [exámenes](https://uaidocs.z20.web.core.windows.net/examenes/). Las fechas pueden cambiar: manda la fuente oficial.

## Cómo se usa

1. Entra a la página y elige tu sede.
2. Escribe tus ramos (`TICS312 1`, `TICS316-2`, o pega tu lista completa).
3. Mira tus fechas en la tabla, descárgalas para Excel o imprímelas.
4. (Opcional) Toca **iPhone / Mac**, **Google Calendar** u **Outlook** para suscribirte.

Tus ramos quedan guardados en tu navegador y también en la dirección de la página: puedes guardarla en favoritos.

## Cómo funciona

```
uaidocs (pruebas.xlsx, examenes.xlsx)
        │  se descargan cada ~30 min (caché)
        ▼
api/_uai.py ── lee los Excel y genera el .ics
   ├── /api/evaluaciones      → JSON con todas las evaluaciones (lo usa la tabla)
   └── /calendario.ics?r=...  → calendario personal para suscribirse
public/index.html             → la página (HTML + JS, sin frameworks)
```

| Parámetro de `/calendario.ics` | Ejemplo | |
|---|---|---|
| `r` | `TICS312-1,TICS400-1` | ramos `SIGLA-SECCIÓN` separados por coma |
| `sede` | `santiago` / `vina` | |
| `alarmas` | `1440,60` | minutos antes {1 dia antes, 1 hora antes} (opcional) |
| `descargar` | `1` | descarga el archivo en vez de mostrarlo |

## Desarrollo

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python dev.py        # → http://localhost:8000
```

Publicado en [Vercel](https://vercel.com) (plan gratuito). Cada `git push` a `main` actualiza la página.

## Limitaciones

- No incluye salas, controles ni entregas de Webcursos/Canvas (la UAI no las publica ahí).
- En exámenes orales y presentaciones la UAI publica el bloque completo; la hora exacta la define el profesor.
- Cada app decide cada cuánto revisa el calendario suscrito: Google tarda 8–24 h; Apple y Outlook, algunas horas.
- Si la UAI cambia el formato de sus Excel, hay que ajustar `api/_uai.py`.
