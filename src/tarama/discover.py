"""Aşama 2: Erişilebilen sitelerde URL envanteri.

- robots.txt içindeki Sitemap satırları + /sitemap.xml, /sitemap_index.xml
- Site haritası indekslerini özyinelemeli açar (sınırlı)
- Tüm URL'leri ciktilar/tarama/urls/<slug>.txt'e yazar
- URL'si asbest terimlerinden birini içerenleri ve belge (pdf/doc/xls) bağlantılarını işaretler

Çıktı: ciktilar/tarama/sitemap_ozet.csv, ciktilar/tarama/urls/<slug>.txt
"""
from __future__ import annotations

import csv
import gzip
import io
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse, unquote

from lxml import etree

from common import ASBEST_RE, OUT, fetch, fold, robots_sitemaps, write_csv

MAX_SITEMAPS = 400
MAX_URLS = 400_000
DOC_RE = re.compile(r"\.(pdf|docx?|xlsx?|pptx?)(\?|$)", re.I)
REPORT_RE = re.compile(r"faaliyet|stratejik|performans|meclis|karar|rapor|cevre|imar|yikim|kentsel", re.I)


def parse_sitemap(content: bytes) -> tuple[list[str], list[str]]:
    """(alt site haritaları, sayfa URL'leri) döndürür."""
    if content[:2] == b"\x1f\x8b":
        try:
            content = gzip.decompress(content)
        except OSError:
            return [], []
    try:
        root = etree.fromstring(content, parser=etree.XMLParser(recover=True, huge_tree=True))
    except etree.XMLSyntaxError:
        return [], []
    if root is None:
        return [], []
    if not isinstance(root.tag, str):
        return [], []
    locs = [el.text.strip() for el in root.iter()
            if isinstance(el.tag, str) and el.tag.endswith("loc") and el.text]
    tag = root.tag.lower()
    if tag in ("html", "body") or tag.endswith("}html"):
        return [], []  # site haritası yerine HTML sayfası dönmüş
    if tag.endswith("sitemapindex"):
        return locs, []
    return [], locs


def crawl_sitemaps(base: str) -> tuple[list[str], list[str], list[str]]:
    seeds = robots_sitemaps(base)
    for extra in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"):
        u = urljoin(base, extra)
        if u not in seeds:
            seeds.append(u)
    queue, seen, urls, tried = list(seeds), set(), [], []
    while queue and len(seen) < MAX_SITEMAPS and len(urls) < MAX_URLS:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        r = fetch(sm, purpose="sitemap", max_bytes=40_000_000)
        tried.append(f"{sm} -> {r.get('status')} {r['durum']}")
        if not r["ok"]:
            continue
        subs, locs = parse_sitemap(r["content"])
        queue.extend(s for s in subs if s not in seen)
        urls.extend(locs)
    return urls, tried, list(seen)


def run(row: dict) -> dict:
    try:
        return _run(row)
    except Exception as e:  # tek site hatası tüm turu düşürmesin
        return {"ilce": row["ilce"], "slug": row["slug"], "kok": row["kanonik_url"],
                "sitemap_sayisi": 0, "url_sayisi": 0, "asbest_url_sayisi": 0, "belge_sayisi": 0,
                "rapor_benzeri_belge": 0, "asbest_urller": "", "denenen_sitemaplar": f"HATA {e!r}"[:300]}


def _run(row: dict) -> dict:
    base = row["kanonik_url"]
    p = urlparse(base)
    base = f"{p.scheme}://{p.hostname}"
    urls, tried, seen = crawl_sitemaps(base)
    urls = list(dict.fromkeys(urls))
    (OUT / "urls").mkdir(exist_ok=True)
    with open(OUT / "urls" / f"{row['slug']}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(urls))
    asb = [u for u in urls if ASBEST_RE.search(fold(unquote(u)))]
    docs = [u for u in urls if DOC_RE.search(u)]
    report_docs = [u for u in docs if REPORT_RE.search(fold(unquote(u)))]
    return {
        "ilce": row["ilce"], "slug": row["slug"], "kok": base,
        "sitemap_sayisi": len([t for t in tried if " 200 ok" in t]),
        "url_sayisi": len(urls), "asbest_url_sayisi": len(asb),
        "belge_sayisi": len(docs), "rapor_benzeri_belge": len(report_docs),
        "asbest_urller": " ".join(asb[:50]),
        "denenen_sitemaplar": " | ".join(tried[:15]),
    }


def main() -> None:
    rows = [r for r in csv.DictReader(open(OUT / "erisim.csv", encoding="utf-8-sig"))
            if r["durum"] == "erisildi"]
    with ThreadPoolExecutor(max_workers=13) as ex:
        res = list(ex.map(run, rows))
    write_csv(OUT / "sitemap_ozet.csv", res, list(res[0].keys()))
    for r in res:
        print(f"{r['ilce']:<14} sitemap={r['sitemap_sayisi']:<4} url={r['url_sayisi']:<7} "
              f"asbest_url={r['asbest_url_sayisi']:<4} belge={r['belge_sayisi']:<6} rapor={r['rapor_benzeri_belge']}")


if __name__ == "__main__":
    main()
