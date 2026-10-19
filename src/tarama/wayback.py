"""Aşama 7: Wayback Machine (web.archive.org) arşivinde silinmiş/eski içerik.

Not: Bu modül bulut çalışma ortamından test EDİLEMEDİ (web.archive.org bağlantısı
proxy tarafından kesiliyor). Yerelde (Türkiye IP'si ile) çalıştırın.

Her belediye alan adı (alt alan adları dahil) için CDX dizininden:
  - URL'sinde asbest terimi geçen tüm arşivlenmiş sayfalar
  - faaliyet raporu PDF'leri (eski sürümler, silinmiş yıllar)
listelenir; istenirse arşiv kopyaları indirilir (harvest.py ile aynı işleme girer).

Çıktı: ciktilar/tarama/wayback.csv, ciktilar/tarama/aday_urller_wayback.txt
"""
from __future__ import annotations

import csv
import json
import sys
from urllib.parse import quote

from common import OUT, fetch, read_seeds, write_csv

CDX = "https://web.archive.org/cdx/search/cdx"
FILTERS = {
    "asbest_url": "original:.*[Aa][Ss][Bb][Ee][Ss][Tt].*",
    "faaliyet_pdf": "original:.*[Ff]aaliyet.*\\.[Pp][Dd][Ff].*",
}


def cdx(domain: str, flt: str) -> list[list[str]]:
    url = (f"{CDX}?url={quote(domain)}&matchType=domain&output=json&collapse=urlkey"
           f"&fl=original,timestamp,statuscode,mimetype&filter={quote(flt)}&filter=statuscode:200&limit=5000")
    r = fetch(url, purpose="wayback_cdx", check_robots=False, timeout=90)
    if not r["ok"]:
        return []
    try:
        rows = json.loads(r["text"] or "[]")
    except ValueError:
        return []
    return rows[1:] if rows and rows[0] and rows[0][0] == "original" else rows


def main() -> None:
    out = []
    for s in read_seeds():
        for dom in s["aday_alanlar"].split(";"):
            for kind, flt in FILTERS.items():
                for original, ts, status, mime in cdx(dom, flt):
                    out.append({"ilce": s["ilce"], "alan": dom, "tur": kind, "orijinal_url": original,
                                "zaman": ts, "mime": mime,
                                "arsiv_url": f"https://web.archive.org/web/{ts}id_/{original}"})
    write_csv(OUT / "wayback.csv", out, ["ilce", "alan", "tur", "orijinal_url", "zaman", "mime", "arsiv_url"])
    if "--indir" in sys.argv:
        with open(OUT / "aday_urller_wayback.txt", "w", encoding="utf-8") as f:
            for o in out:
                f.write(f"{o['ilce']}\t{o['arsiv_url']}\tWayback {o['zaman'][:8]} | {o['orijinal_url']}\n")
    print(f"{len(out)} arşiv kaydı")


if __name__ == "__main__":
    main()
