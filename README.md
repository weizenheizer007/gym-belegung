# Gym-Belegung Uni Mannheim

Zeichnet alle 5 Minuten die Studiobelegung des Hochschulsport-Fitnessstudios auf
und zeigt sie als Wochen-Heatmap und Tagesverlauf.

## So funktioniert's

| Teil | Datei | Was passiert |
|---|---|---|
| Zeitplan | `.github/workflows/abfrage.yml` | GitHub startet alle 5 Min. einen kleinen Linux-Server |
| Abfrage | `scraper/fetch.py` | lädt das Zahlenbild der Uni (`studio.cgi?size=120`) |
| Erkennung | `scraper/digits.py` | zerlegt das Bild in Ziffern und vergleicht sie mit Vorlagen |
| Daten | Branch `data`: `data/belegung.csv`, `data/live.json` | Verlauf und neueste Messung (eigener Branch, damit die Webseite nicht bei jeder Messung neu gebaut wird) |
| Webseite | `index.html` | holt beim Öffnen die neueste Messung und den Verlauf direkt aus dem `data`-Branch |

Unsichere Bilder werden **nicht** gespeichert, sondern im `data`-Branch unter `data/unsicher/` abgelegt.
Sicher erkannte Uni-Ziffern landen als neue Vorlage in `data/glyphs/` (ebenfalls `data`-Branch), damit die
Erkennung mit der Zeit noch genauer wird.

## Einrichtung (einmalig, ca. 5 Min.)

1. **Repository anlegen:** github.com/new → Name z. B. `gym-belegung`, **Public**, sonst nichts anhaken → *Create repository*.
2. **Dateien hochladen:** *uploading an existing file* → ZIP entpacken, Ordner öffnen, im Finder **Cmd + Shift + .**
   (damit der versteckte Ordner `.github` sichtbar wird), **alles markieren** und ins Browserfenster ziehen → *Commit changes*.
   Prüfen: Im Repo gibt es den Ordner `.github/workflows`.
3. **Webseite einschalten:** *Settings* → *Pages* → *Deploy from a branch* → Branch **main**, Ordner **/ (root)** → *Save*.
4. **Erster Lauf:** *Actions* → *Belegung abfragen* → *Run workflow*. Nach ca. 30 Sek. grüner Haken.
   Dieser Lauf legt den Branch `data` mit den Messwerten automatisch an.

Die Seite liegt dann unter `https://ACCOUNT.github.io/REPO/`. Ampel und Warte-Empfehlung erscheinen ab 3 Messtagen.

**Warum nicht live direkt von der Uni?** Die Uni-Seite blockt Abrufe des Zahlenbilds von fremden Webseiten. Deshalb misst der Bot, und die Seite zeigt seine neueste Messung (meist höchstens 5–10 Min. alt).

## Gut zu wissen

- GitHub startet geplante Läufe manchmal 5–15 Minuten zu spät, vor allem zur vollen Stunde. Für Stoßzeiten ist das egal.
- Kosten: keine (öffentliches Repo).
- Die Uni-Seite wird 288× am Tag abgerufen (ein kleines Bild). Das ist vernachlässigbar wenig Last.

## Alternative: Raspberry Pi

```bash
sudo apt install -y python3-pil python3-numpy git
git clone https://github.com/DEINNAME/gym-belegung.git ~/gym && cd ~/gym
python3 scraper/fetch.py                       # Test
crontab -e                                     # Zeile einfügen:
*/5 * * * * cd ~/gym && python3 scraper/fetch.py >> fetch.log 2>&1
python3 -m http.server 8080                    # Seite: http://<pi-ip>:8080
```
Nachteil: Die Seite ist nur im Heim-WLAN erreichbar (außer mit z. B. Tailscale), und der Pi muss durchlaufen.
