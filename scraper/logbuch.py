#!/usr/bin/env python3
"""Hängt einen Logbuch-Eintrag (eigenes Gefühl im Studio) an data/logbuch.csv an.

Eingaben kommen aus einem GitHub-Issue mit dem Titel „Logbuch: leer|ok|voll“.
Optional im Text: „Zeit: 2026-11-20 12:10“ (sonst Zeitpunkt des Issues)
und eine freie Notiz (alles andere im Text).
Die Personenzahl wird aus belegung.csv zur nächstgelegenen Messung (±15 Min.) ergänzt.

Umgebung: DATA_DIR, TITLE, BODY, CREATED (ISO-Zeit des Issues)
Ausgabe (stdout): eine Zeile Zusammenfassung für den Issue-Kommentar.
"""
import csv
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
DATA = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
LOG = DATA / "logbuch.csv"
LEVELS = {"leer": "leer", "ruhig": "leer", "frei": "leer",
          "ok": "ok", "okay": "ok", "mittel": "ok",
          "voll": "voll", "warten": "voll"}


def parse_level(title: str):
    m = re.match(r"\s*logbuch\s*:?\s*(\w+)", title, re.I)
    return LEVELS.get(m.group(1).lower()) if m else None


def parse_time(body: str, created: str) -> datetime:
    m = re.search(r"zeit\s*:\s*(\d{4}-\d\d-\d\d)[ T](\d\d:\d\d)", body, re.I)
    if m:
        return datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}").replace(tzinfo=TZ)
    return datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(TZ).replace(second=0, microsecond=0)


def nearest_count(t: datetime):
    path = DATA / "belegung.csv"
    if not path.exists():
        return None
    best = None
    with path.open() as f:
        for row in csv.DictReader(f):
            try:
                d = abs(datetime.fromisoformat(row["zeit"]) - t)
            except (KeyError, ValueError):
                continue
            if d <= timedelta(minutes=15) and (best is None or d < best[0]):
                best = (d, int(row["personen"]))
    return best[1] if best else None


def main() -> int:
    level = parse_level(os.environ.get("TITLE", ""))
    if not level:
        print("Titel nicht erkannt. Bitte „Logbuch: leer“, „Logbuch: ok“ oder „Logbuch: voll“ verwenden.")
        return 1
    body = os.environ.get("BODY", "") or ""
    t = parse_time(body, os.environ.get("CREATED", datetime.now(TZ).isoformat()))
    note = " ".join(l.strip() for l in body.splitlines()
                    if l.strip() and not re.match(r"\s*zeit\s*:", l, re.I) and not l.startswith("<!--"))
    note = note.replace(",", ";")[:200]
    n = nearest_count(t)
    new = not LOG.exists()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["zeit", "gefuehl", "personen", "notiz"])
        w.writerow([t.isoformat(), level, "" if n is None else n, note])
    print(f"Eingetragen: {t:%a %d.%m. %H:%M} · {level} · " + (f"{n} Personen" if n is not None else "keine Messung in der Nähe"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
