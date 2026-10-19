"""Aşama 3: Açık veri portalları (CKAN) taraması.

Kadıköy'ün CKAN tabanlı portalında asbest veri seti bulundu. Diğer ilçelerde
ve İBB'de benzer portal var mı, varsa asbest / yıkım / kentsel dönüşüm
veri setleri neler, API üzerinden bakar.

Çıktı: ciktilar/tarama/acikveri.csv
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from common import OUT, fetch, read_seeds, write_csv

PREFIXES = ("acikveri", "veri", "data", "opendata", "acikveriportali")
QUERIES = ("asbest", "yıkım", "kentsel dönüşüm", "tehlikeli atık", "inşaat atığı")
EXTRA = [{"ilce": "İBB", "slug": "ibb", "aday_alanlar": "", "portallar": ["https://data.ibb.gov.tr"]}]


def probe_portal(base: str) -> bool:
    r = fetch(f"{base}/api/3/action/status_show", purpose="ckan_kesif", check_robots=False, timeout=15)
    if not r["ok"]:
        return False
    try:
        return bool(json.loads(r["text"]).get("success"))
    except (ValueError, AttributeError):
        return False


def search(base: str, q: str) -> list[dict]:
    r = fetch(f"{base}/api/3/action/package_search?q={quote(q)}&rows=100", purpose="ckan_arama",
              check_robots=False)
    if not r["ok"]:
        return []
    try:
        return json.loads(r["text"])["result"]["results"]
    except (ValueError, KeyError):
        return []


def run(seed: dict) -> list[dict]:
    portals = seed.get("portallar") or [
        f"https://{p}.{d}" for d in seed["aday_alanlar"].split(";") for p in PREFIXES]
    rows = []
    for base in portals:
        if not probe_portal(base):
            continue
        hit = False
        for q in QUERIES:
            for pkg in search(base, q):
                hit = True
                rows.append({
                    "ilce": seed["ilce"], "portal": base, "sorgu": q,
                    "veri_seti": pkg.get("title"), "kurum": (pkg.get("organization") or {}).get("title", ""),
                    "guncelleme": pkg.get("metadata_modified", "")[:10],
                    "aciklama": (pkg.get("notes") or "").replace("\n", " ")[:300],
                    "kaynaklar": " ".join(f"{r.get('format')}:{r.get('url')}" for r in pkg.get("resources", [])),
                    "sayfa": f"{base}/dataset/{pkg.get('name')}",
                })
        if not hit:
            rows.append({"ilce": seed["ilce"], "portal": base, "sorgu": "*", "veri_seti": "(eşleşme yok)"})
    return rows


def main() -> None:
    seeds = read_seeds() + EXTRA
    with ThreadPoolExecutor(max_workers=12) as ex:
        results = [row for rows in ex.map(run, seeds) for row in rows]
    # aynı veri setinin farklı sorgulardan tekrarlarını birleştir
    merged: dict[tuple, dict] = {}
    for r in results:
        key = (r["portal"], r["veri_seti"])
        if key in merged:
            merged[key]["sorgu"] += "," + r["sorgu"]
        else:
            merged[key] = r
    rows = list(merged.values())
    write_csv(OUT / "acikveri.csv", rows,
              ["ilce", "portal", "sorgu", "veri_seti", "kurum", "guncelleme", "aciklama", "kaynaklar", "sayfa"])
    for r in rows:
        print(f"{r['ilce']:<10} {r['portal']:<40} [{r['sorgu']}] {r['veri_seti']} ({r.get('guncelleme','')})")


if __name__ == "__main__":
    main()
