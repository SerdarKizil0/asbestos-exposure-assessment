"""kaynaklar.csv'deki her URL için Wayback Machine'de var olan en yakın arşiv kopyasını bulur (salt okuma).

Yeni arşivleme isteği (web.archive.org/save) GÖNDERMEZ; bu dış bir eylemdir ve ayrıca karar gerektirir.
İstekler src/tarama/common.py fetch() üzerinden gider: robots.txt'ye uyulur, aynı hosta ≥2 sn aralık,
her istek veri/ham/log/istekler.jsonl günlüğüne yazılır.

Kullanım:  python src/arsiv_kontrol.py [--hepsi]     (varsayılan: arsiv_url'si boş satırlar)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.parse import quote

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src" / "tarama"))
from common import fetch  # noqa: E402

API = "https://archive.org/wayback/available?url="


def en_yakin(url: str) -> tuple[str, str]:
    r = fetch(API + quote(url, safe=""), purpose="wayback_available", timeout=60)
    if not r["ok"]:
        return "", r.get("durum") or str(r.get("status"))
    try:
        snap = json.loads(r["text"]).get("archived_snapshots", {}).get("closest") or {}
    except ValueError:
        return "", "json_hatasi"
    if snap.get("available") and str(snap.get("status")) == "200":
        return snap["url"].replace("http://", "https://", 1), snap.get("timestamp", "")
    return "", "arsiv_yok"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hepsi", action="store_true", help="arsiv_url'si dolu satırları da yeniden sorgula")
    arg = ap.parse_args()
    yol = KOK / "kaynaklar.csv"
    with open(yol, encoding="utf-8") as f:
        okuyucu = csv.DictReader(f)
        alanlar, satirlar = okuyucu.fieldnames, list(okuyucu)
    bulunan = yok = 0
    for s in satirlar:
        if not s["url"] or (s["arsiv_url"] and not arg.hepsi):
            continue
        arsiv, bilgi = en_yakin(s["url"])
        if arsiv:
            s["arsiv_url"] = arsiv
            bulunan += 1
        else:
            yok += 1
        print(f"{'+' if arsiv else '-'} {s['kaynak_id']}: {arsiv or bilgi}", flush=True)
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alanlar, lineterminator="\n")
        w.writeheader()
        w.writerows(satirlar)
    print(f"arşiv kopyası bulunan: {bulunan}, bulunamayan: {yok}")


if __name__ == "__main__":
    main()
