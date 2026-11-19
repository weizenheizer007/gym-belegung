#!/usr/bin/env python3
"""Fragt die aktuelle Studiobelegung des Hochschulsport Mannheim ab
und hängt sie an data/belegung.csv an.

Die Uni liefert die Zahl nur als Bild (GIF). Wir laden es groß (size=120)
und lesen die Ziffern per Formvergleich (siehe digits.py).
Unsichere Bilder werden NICHT gespeichert, sondern unter data/unsicher/ abgelegt.

Aufruf:  python scraper/fetch.py            -> abfragen + speichern
         python scraper/fetch.py bild.gif   -> nur testen
"""
import csv
import io
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import digits  # noqa: E402

URL = "https://www.hochschulsport.uni-mannheim.de/cgi/studio.cgi?size=120"
ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("DATA_DIR", ROOT / "data"))
CSV_PATH = DATA / "belegung.csv"
LIVE_PATH = DATA / "live.json"   # immer nur die neueste Messung (für die Startseite)
UNSURE_DIR = DATA / "unsicher"
TZ = ZoneInfo("Europe/Berlin")


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.hochschulsport.uni-mannheim.de/angebote/aktueller_zeitraum_0/_T1_FitnessGym_Studiobelegung.html",
}


def download() -> bytes:
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
        if not data.startswith(b"GIF"):
            raise RuntimeError(f"kein GIF erhalten: HTTP {r.status} {r.headers.get('Content-Type')} "
                               f"{len(data)} Bytes, Anfang: {data[:400]!r}")
        return data


def main() -> int:
    now = datetime.now(TZ).replace(second=0, microsecond=0)
    try:
        gif = download()
    except Exception as e:  # Uni-Server down -> diesen Lauf überspringen
        print(f"Download fehlgeschlagen: {e}", file=sys.stderr)
        return 0
    value, info = digits.read_number(Image.open(io.BytesIO(gif)))
    print(f"{now.isoformat()}  {value}  [{info}]")
    if value is None:
        UNSURE_DIR.mkdir(parents=True, exist_ok=True)
        (UNSURE_DIR / f"{now:%Y%m%d-%H%M}.gif").write_bytes(gif)
        return 0
    new_file = not CSV_PATH.exists()
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["zeit", "personen"])
        w.writerow([now.isoformat(), value])
    LIVE_PATH.write_text(json.dumps({"zeit": now.isoformat(), "personen": value}))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(digits.read_number(Image.open(sys.argv[1])))
    else:
        sys.exit(main())
