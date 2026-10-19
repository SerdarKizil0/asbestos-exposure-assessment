"""Aşama 6: Faaliyet raporlarının keşfi (hedefli, sığ tarama).

Faaliyet raporları (5018 s. Kanun md. 41, 5393 s. Kanun md. 56 gereği yayımlanır)
belediyelerin asbest sayılarını en düzenli verdiği yer çıktı. Bu modül her sitede
ana sayfadan başlayıp yalnızca "faaliyet/rapor/stratejik/kurumsal..." gibi
bağlantıları izleyerek (derinlik <= 3, site başına <= 80 sayfa) PDF/DOC
faaliyet raporu bağlantılarını toplar.

Çıktı: ciktilar/tarama/faaliyet_raporlari.csv, ciktilar/tarama/aday_urller_faaliyet.txt
"""
from __future__ import annotations

import csv
import re
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse, unquote

from bs4 import BeautifulSoup

from common import OUT, fetch, fold, write_csv

NAV_RE = re.compile(r"faaliyet|rapor|stratejik|kurumsal|yayin|belge|dokuman|seffaf|mali|yonetim|plan|hakkimizda")
REPORT_RE = re.compile(r"faaliyet")
DOC_RE = re.compile(r"\.(pdf|docx?)(\?|$)", re.I)
YEAR_RE = re.compile(r"(20[0-2]\d)")
SKIP_RE = re.compile(r"\.(jpe?g|png|gif|svg|css|js|ico|webp|mp4|zip|rar|xlsx?)(\?|$)", re.I)
MAX_PAGES, MAX_DEPTH = 80, 3


def reg_domain(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[-3:]) if host.endswith(".bel.tr") or host.endswith(".gov.tr") else ".".join(parts[-2:])


def crawl(row: dict) -> list[dict]:
    start = row["kanonik_url"]
    root = reg_domain(urlparse(start).hostname or "")
    q, seen, found = deque([(start, 0)]), {start}, {}
    pages = 0
    while q and pages < MAX_PAGES:
        url, depth = q.popleft()
        r = fetch(url, purpose="rapor_kesif", max_bytes=5_000_000)
        pages += 1
        if not r["ok"] or "html" not in r.get("ctype", ""):
            continue
        soup = BeautifulSoup(r["text"], "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            u = urljoin(r["final_url"], href).split("#")[0]
            host = urlparse(u).hostname or ""
            if not host.endswith(root):
                continue
            label = fold(a.get_text(" ", strip=True) + " " + unquote(u))
            if DOC_RE.search(u):
                if REPORT_RE.search(label) and u not in found:
                    ym = YEAR_RE.findall(a.get_text(" ", strip=True) + " " + unquote(u))
                    found[u] = {"ilce": row["ilce"], "yil": ym[0] if ym else "", "url": u,
                                "baglanti_metni": a.get_text(" ", strip=True)[:120], "kaynak_sayfa": r["final_url"]}
                continue
            if SKIP_RE.search(u) or u in seen or depth >= MAX_DEPTH:
                continue
            if NAV_RE.search(label):
                seen.add(u)
                # faaliyet geçen sayfalara öncelik ver
                (q.appendleft if REPORT_RE.search(label) else q.append)((u, depth + 1))
    if not found:
        return [{"ilce": row["ilce"], "yil": "", "url": "", "baglanti_metni": f"(bulunamadı; {pages} sayfa tarandı)",
                 "kaynak_sayfa": ""}]
    return list(found.values())


def main() -> None:
    rows = [r for r in csv.DictReader(open(OUT / "erisim.csv", encoding="utf-8-sig")) if r["durum"] == "erisildi"]
    with ThreadPoolExecutor(max_workers=13) as ex:
        res = [x for xs in ex.map(crawl, rows) for x in xs]
    res.sort(key=lambda x: (x["ilce"], x["yil"]))
    write_csv(OUT / "faaliyet_raporlari.csv", res, ["ilce", "yil", "url", "baglanti_metni", "kaynak_sayfa"])
    with open(OUT / "aday_urller_faaliyet.txt", "w", encoding="utf-8") as f:
        for x in res:
            if x["url"]:
                f.write(f"{x['ilce']}\t{x['url']}\tFaaliyet raporu {x['yil']} | {x['baglanti_metni']}\n")
    from collections import Counter
    c = Counter(x["ilce"] for x in res if x["url"])
    for r in rows:
        yrs = sorted({x["yil"] for x in res if x["ilce"] == r["ilce"] and x["url"] and x["yil"]})
        print(f"{r['ilce']:<14} {c.get(r['ilce'], 0):>3} rapor  yıllar: {', '.join(yrs)}")


if __name__ == "__main__":
    main()
