#!/usr/bin/env python3
"""
Recordatorios automáticos para el canal de anuncios del equipo de LoL.

Lee eventos.yaml y publica avisos en Discord mediante un webhook.
Pensado para ejecutarse cada 10 minutos (cron o similar).

Uso:
    python3 avisos.py            # envía los avisos que toquen ahora
    python3 avisos.py --listar   # muestra los próximos avisos programados
    python3 avisos.py --prueba   # muestra lo que enviaría ahora, sin enviar

La URL del webhook se toma de la variable de entorno DISCORD_WEBHOOK
(recomendado) o del campo webhook_url de eventos.yaml.
"""
import json
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

TZ = ZoneInfo("Europe/Madrid")
BASE = Path(__file__).resolve().parent
CONFIG = BASE / "eventos.yaml"
ESTADO = BASE / "enviados.json"

# Si el script estuvo parado, no manda avisos con más de este retraso
MARGEN = timedelta(hours=2)

DIAS = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2, "jueves": 3,
    "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6,
}

ESTILO = {  # tipo: (emoji, color, título)
    "partido": ("🏆", 0xE74C3C, "Partido hoy"),
    "entrenamiento": ("🎯", 0x3498DB, "Entrenamiento"),
    "deadline": ("⏰", 0xF1C40F, "Deadline"),
    "encuesta": ("📊", 0x9B59B6, "Encuesta pendiente"),
}


def a_las(h, m=0):
    """Aviso el mismo día del evento a una hora fija."""
    return lambda f: f.replace(hour=h, minute=m, second=0, microsecond=0)


def antes(**kw):
    """Aviso un tiempo antes del evento."""
    return lambda f: f - timedelta(**kw)


# Cuándo se avisa de cada tipo de evento. Cámbialo a tu gusto.
AVISOS = {
    "partido": [("mañana-del-dia", a_las(10)), ("1h", antes(hours=1))],
    "entrenamiento": [("2h", antes(hours=2))],
    "deadline": [("24h", antes(hours=24)), ("3h", antes(hours=3))],
    "encuesta": [("24h", antes(hours=24)), ("3h", antes(hours=3))],
}


# ---------------------------------------------------------------- lectura

def parse_fecha(v):
    if isinstance(v, datetime):
        dt = v
    elif isinstance(v, date):
        dt = datetime.combine(v, time(23, 59))
    else:
        s = str(v).strip()
        if len(s) == 10:  # solo fecha: cuenta como final del día
            s += " 23:59"
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                pass
        else:
            raise ValueError(f"Fecha no válida: {v!r} (usa 'AAAA-MM-DD HH:MM')")
    return dt if dt.tzinfo else dt.replace(tzinfo=TZ)


def parse_hora(v):
    if isinstance(v, int):  # YAML convierte 21:00 sin comillas en 1260
        return divmod(v, 60)
    h, m = str(v).split(":")
    return int(h), int(m)


def cargar_eventos(cfg, ahora):
    eventos = []
    for e in cfg.get("eventos") or []:
        tipo = e.get("tipo", "").lower()
        if tipo not in AVISOS:
            print(f"Aviso: tipo desconocido '{tipo}' en '{e.get('titulo')}'", file=sys.stderr)
            continue
        eventos.append({**e, "tipo": tipo, "fecha": parse_fecha(e["fecha"])})

    saltar = {parse_fecha(d).date() if not isinstance(d, date) else d
              for d in cfg.get("saltar_entrenamientos") or []}
    for e in cfg.get("entrenamientos_semanales") or []:
        dia = DIAS[e["dia"].lower()]
        h, m = parse_hora(e["hora"])
        for delta in range(-1, 8):
            d = (ahora + timedelta(days=delta)).date()
            if d.weekday() == dia and d not in saltar:
                eventos.append({
                    "tipo": "entrenamiento",
                    "titulo": e.get("titulo", "Entrenamiento"),
                    "detalles": e.get("detalles"),
                    "enlace": e.get("enlace"),
                    "fecha": datetime.combine(d, time(h, m), TZ),
                })
    return eventos


def avisos_de(eventos):
    for ev in eventos:
        for etiqueta, regla in AVISOS[ev["tipo"]]:
            cuando = regla(ev["fecha"])
            if cuando < ev["fecha"]:
                clave = f"{ev['tipo']}|{ev['titulo']}|{ev['fecha'].isoformat()}|{etiqueta}"
                yield cuando, etiqueta, clave, ev


# ---------------------------------------------------------------- mensaje

def construir_mensaje(ev, cfg):
    emoji, color, nombre = ESTILO[ev["tipo"]]
    ts = int(ev["fecha"].timestamp())
    # <t:..:F> y <t:..:R> se muestran en la hora local de cada usuario
    prefijo = "Cierra" if ev["tipo"] in ("deadline", "encuesta") else "Empieza"
    lineas = [f"{prefijo} <t:{ts}:F> (<t:{ts}:R>)"]
    if ev.get("detalles"):
        lineas.append(str(ev["detalles"]))
    if ev.get("enlace"):
        lineas.append(f"🔗 {ev['enlace']}")

    payload = {
        "username": cfg.get("nombre_bot", "Avisos del equipo"),
        "embeds": [{
            "title": f"{emoji} {nombre}: {ev['titulo']}",
            "description": "\n".join(lineas),
            "color": color,
        }],
    }
    rol = cfg.get("rol_mencion")
    if rol and ev["tipo"] in (cfg.get("mencionar_en") or AVISOS.keys()):
        payload["content"] = f"<@&{rol}>"
        payload["allowed_mentions"] = {"roles": [str(rol)]}
    return payload


# ---------------------------------------------------------------- main

def main():
    listar = "--listar" in sys.argv
    prueba = "--prueba" in sys.argv

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    ahora = datetime.now(TZ)
    eventos = cargar_eventos(cfg, ahora)

    if listar:
        proximos = sorted(a for a in avisos_de(eventos) if a[0] >= ahora)
        if not proximos:
            print("No hay avisos programados.")
        for cuando, etiqueta, _, ev in proximos:
            print(f"{cuando:%a %d/%m %H:%M}  [{ev['tipo']:<13}] {ev['titulo']}  ({etiqueta})")
        return

    url = os.environ.get("DISCORD_WEBHOOK") or cfg.get("webhook_url")
    if not url and not prueba:
        sys.exit("Falta la URL del webhook (variable DISCORD_WEBHOOK o webhook_url en eventos.yaml)")

    enviados = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}

    for cuando, etiqueta, clave, ev in sorted(avisos_de(eventos), key=lambda a: a[0]):
        if clave in enviados:
            continue
        if not (cuando <= ahora < ev["fecha"]) or ahora - cuando > MARGEN:
            continue
        payload = construir_mensaje(ev, cfg)
        if prueba:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            continue
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        enviados[clave] = ev["fecha"].isoformat()
        print(f"Enviado: {ev['titulo']} ({etiqueta})")

    if not prueba:
        limite = ahora - timedelta(days=14)
        enviados = {k: v for k, v in enviados.items()
                    if datetime.fromisoformat(v) > limite}
        ESTADO.write_text(json.dumps(enviados, indent=2))


if __name__ == "__main__":
    main()
