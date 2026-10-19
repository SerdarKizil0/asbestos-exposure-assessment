"""Aşama 1: 39 belediyenin sitesine erişim kontrolü ve kanonik alan adı seçimi.

Çıktı: ciktilar/tarama/erisim.csv
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from common import OUT, fetch, read_seeds, write_csv

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def probe(seed: dict) -> dict:
    attempts = []
    best = None
    for dom in seed["aday_alanlar"].split(";"):
        for prefix in ("https://www.", "https://"):
            url = f"{prefix}{dom}/"
            # Ana sayfa erişim testi; robots.txt ana sayfayı nadiren yasaklar ama yine de bakılır.
            r = fetch(url, purpose="erisim", max_bytes=3_000_000)
            attempts.append(f"{url} -> {r.get('status')} {r['durum']}")
            if r["ok"] and r.get("status") == 200:
                m = TITLE_RE.search(r["text"] or "")
                best = {
                    "kanonik_url": r["final_url"],
                    "http": r["status"],
                    "baslik": (m.group(1).strip()[:120] if m else ""),
                    "sunucu": r["headers"].get("server", ""),
                    "durum": "erisildi",
                }
                break
            if r["durum"] == "challenge" and best is None:
                best = {"kanonik_url": r["final_url"], "http": r.get("status"),
                        "durum": "bot_korumasi", "sunucu": r["headers"].get("server", ""), "baslik": ""}
        if best and best["durum"] == "erisildi":
            break
    if best is None:
        best = {"kanonik_url": "", "http": "", "durum": "ulasilamadi", "sunucu": "", "baslik": ""}
    return {"ilce": seed["ilce"], "slug": seed["slug"], "yaka": seed["yaka"], **best,
            "denemeler": " | ".join(attempts)}


def main() -> None:
    seeds = read_seeds()
    with ThreadPoolExecutor(max_workers=10) as ex:
        rows = list(ex.map(probe, seeds))
    write_csv(OUT / "erisim.csv", rows,
              ["ilce", "slug", "yaka", "durum", "http", "kanonik_url", "baslik", "sunucu", "denemeler"])
    ok = sum(r["durum"] == "erisildi" for r in rows)
    print(f"Erişilen: {ok}/{len(rows)}")
    for r in rows:
        print(f"{r['ilce']:<14} {r['durum']:<13} {r['http']!s:<4} {r['kanonik_url'][:60]:<60} {r['baslik'][:50]}")


if __name__ == "__main__":
    main()
