"""Ziffernerkennung per Formvergleich (ohne Tesseract).

1. Bild in einzelne Ziffern zerlegen (Spalten ohne Farbe = Lücke).
2. Jede Ziffer auf ein 20x28-Raster normieren (Seitenverhältnis bleibt erhalten).
3. Mit Vorlagen vergleichen: echte Uni-Ziffern (data/glyphs/*.png, exakt)
   plus Ziffern aus ähnlichen Schriften (Fallback für noch nie gesehene Ziffern).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image

W, H = 20, 28
ROOT = Path(__file__).resolve().parent.parent
GLYPH_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data")) / "glyphs"  # echte Ziffern, Dateiname beginnt mit der Ziffer


def alpha(img: Image.Image) -> np.ndarray:
    """Farbmenge 0..1 pro Pixel (Transparenz oder dunkle Farbe)."""
    rgba = np.array(img.convert("RGBA")).astype(float) / 255
    dark = 1 - rgba[:, :, :3].mean(axis=2)
    return np.clip(np.minimum(rgba[:, :, 3], 1.0) * dark, 0, 1)


def segment(a: np.ndarray, thr: float = 0.3) -> list[np.ndarray]:
    ink = list(a.max(axis=0) > thr) + [False]
    out, start = [], None
    for x, v in enumerate(ink):
        if v and start is None:
            start = x
        elif not v and start is not None:
            g = a[:, start:x]
            rows = np.where(g.max(axis=1) > thr)[0]
            out.append(g[rows.min(): rows.max() + 1])
            start = None
    return out


def normalize(g: np.ndarray) -> np.ndarray:
    h, w = g.shape
    scale = H / h
    nw = max(1, min(W, round(w * scale)))
    small = np.array(Image.fromarray((g * 255).astype("uint8")).resize((nw, H), Image.BILINEAR)) / 255
    box = np.zeros((H, W))
    off = (W - nw) // 2
    box[:, off: off + nw] = small
    return box


FONT_DIR = Path(__file__).resolve().parent / "vorlagen"  # vorgerenderte Schrift-Ziffern


def _font_templates() -> list[tuple[str, np.ndarray]]:
    return [(f.name[0], normalize(np.array(Image.open(f).convert("L")) / 255))
            for f in sorted(FONT_DIR.glob("*.png"))]


def _real_templates() -> list[tuple[str, np.ndarray]]:
    out = []
    for f in sorted(GLYPH_DIR.glob("*.png")):
        out.append((f.name[0], normalize(np.array(Image.open(f).convert("L")) / 255)))
    return out


_TEMPLATES: list[tuple[str, np.ndarray, bool]] | None = None


def templates():
    global _TEMPLATES
    if _TEMPLATES is None:
        _TEMPLATES = [(d, t, True) for d, t in _real_templates()] + \
                     [(d, t, False) for d, t in _font_templates()]
    return _TEMPLATES


def classify(g: np.ndarray) -> tuple[str, float, float, bool]:
    """-> (ziffer, abstand, abstand zur zweitbesten anderen Ziffer, echte Vorlage?)"""
    n = normalize(g)
    best: dict[str, tuple[float, bool]] = {}
    for d, t, real in templates():
        dist = float(np.abs(n - t).mean())
        if d not in best or dist < best[d][0]:
            best[d] = (dist, real)
    ranked = sorted(best.items(), key=lambda kv: kv[1][0])
    (d1, (s1, r1)), (_, (s2, _)) = ranked[0], ranked[1]
    return d1, s1, s2, r1


def tesseract_digit(g: np.ndarray) -> str | None:
    """Zweite Meinung für eine einzelne Ziffer (nur falls Tesseract installiert ist)."""
    import io
    import shutil
    import subprocess
    if not shutil.which("tesseract"):
        return None
    glyph = Image.fromarray((255 - g * 255).astype("uint8"))
    im = Image.new("L", (glyph.width + 80, glyph.height + 80), 255)
    im.paste(glyph, (40, 40))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    out = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "10",
                          "-c", "tessedit_char_whitelist=0123456789"],
                         input=buf.getvalue(), capture_output=True).stdout.decode().strip()
    return out if len(out) == 1 and out.isdigit() else None


def learn(d: str, g: np.ndarray) -> None:
    """Sicher erkannte echte Ziffer als Vorlage speichern (max. 3 pro Ziffer)."""
    global _TEMPLATES
    if len(list(GLYPH_DIR.glob(f"{d}_*.png"))) >= 3:
        return
    GLYPH_DIR.mkdir(parents=True, exist_ok=True)
    i = len(list(GLYPH_DIR.glob(f"{d}_*.png")))
    Image.fromarray((g * 255).astype("uint8")).save(GLYPH_DIR / f"{d}_auto{i}.png")
    _TEMPLATES = None


def read_number(img: Image.Image) -> tuple[int | None, str]:
    """-> (zahl oder None, info). None = unsicher, lieber nicht speichern."""
    glyphs = segment(alpha(img))
    if not glyphs or len(glyphs) > 3:
        return None, f"{len(glyphs)} Zeichen gefunden"
    digits, info, to_learn = "", [], []
    for g in glyphs:
        d, s1, s2, real = classify(g)
        tag = f"{d}(d={s1:.3f},next={s2:.3f},{'echt' if real else 'schrift'})"
        if real and s1 < 0.03:
            pass  # deckt sich mit einer echten Uni-Ziffer -> sicher
        elif s1 < 0.20 and s2 - s1 > 0.04:
            to_learn.append((d, g))  # klar besser als alle anderen Ziffern
        elif tesseract_digit(g) == d:
            tag += "+tesseract"
            to_learn.append((d, g))
        else:
            return None, "unsicher: " + " ".join(info + [tag])
        info.append(tag)
        digits += d
    for d, g in to_learn:
        learn(d, g)
    return int(digits), " ".join(info)
