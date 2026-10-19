"""Model için ortak yardımcılar: yollar, ad anahtarı, CSV okuma."""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
RAW = KOK / "veri" / "ham"  # git'e girmez
GIRDI = KOK / "model" / "girdi"
CIKTI = KOK / "model" / "cikti"
GIRDI.mkdir(parents=True, exist_ok=True)
CIKTI.mkdir(parents=True, exist_ok=True)

_TR = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u",
                     "ö": "o", "Ö": "o", "ç": "c", "Ç": "c", "â": "a", "î": "i", "û": "u"})


def anahtar(ad: str) -> str:
    """Mahalle adlarını kaynaklar arasında eşleştirmek için sadeleştirir."""
    s = (ad or "").strip().translate(_TR).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace(" mahallesi", "")
    if s in ("19 may", "on dokuz mayis", "on dakuz mayis", "19 mayis", "ondokuz mayis"):
        return "19 mayis"
    return s


def oku_csv(yol: Path, ayrac: str | None = None) -> list[dict]:
    ham = yol.read_bytes()
    for enc in ("utf-8-sig", "iso-8859-9", "cp1254"):
        try:
            metin = ham.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if ayrac is None:
        ilk = metin.splitlines()[0]
        ayrac = ";" if ilk.count(";") >= ilk.count(",") else ","
    return list(csv.DictReader(io.StringIO(metin), delimiter=ayrac))


def sayi(v) -> float:
    """'175.286,61' veya '13.921' gibi Türkçe biçimli sayıları çevirir."""
    if v is None:
        return float("nan")
    s = str(v).strip().replace(" ", "")
    if s == "":
        return float("nan")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    return float(s)


def yaz_csv(yol: Path, satirlar: list[dict], alanlar: list[str] | None = None) -> None:
    alanlar = alanlar or list(satirlar[0].keys())
    with open(yol, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=alanlar, extrasaction="ignore")
        w.writeheader()
        w.writerows(satirlar)


def tr_baslik(s: str) -> str:
    """'ALTUNİZADE' → 'Altunizade' (Türkçe büyük/küçük harf kuralıyla)."""
    def kelime(w):
        if not w:
            return w
        bas = w[0]
        govde = w[1:].replace("I", "ı").replace("İ", "i").lower()
        return bas + govde
    return " ".join(kelime(w) for w in s.split(" "))
