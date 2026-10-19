"""Aşama 4: Sitelerin kendi arama kutusunda "asbest" araması.

1) Ana sayfadaki GET arama formunu bulur (input adı + action).
2) Form yoksa yaygın URL kalıplarını dener.
3) "asbest" sonuç sayfası ile anlamsız bir sorgunun (taban) sonuç sayfasını
   karşılaştırır; yalnızca asbest sorgusunda görünen site içi bağlantıları aday sayar.

POST formlarına dokunmaz. JS ile sonuç getiren sitelerde fark çıkmazsa
"js_olabilir" olarak işaretler; bunlar tarayıcı ile ayrıca bakılmalı.

Çıktı: ciktilar/tarama/site_arama.csv, ciktilar/tarama/aday_urller_sitearama.txt
"""
from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urljoin, urlparse

from bs4 import BeautifulSoup

from common import ASBEST_RE, OUT, fetch, fold, maskele, write_csv

TERM, BASE_TERM = "asbest", "zqxjvkwpt"
PATTERNS = [
    "/arama?q={q}", "/arama?kelime={q}", "/arama?search={q}", "/arama?s={q}", "/Arama?q={q}",
    "/Arama?kelime={q}", "/tr/arama?q={q}", "/search?q={q}", "/arama/{q}", "/Arama/{q}",
    "/ara?q={q}", "/?s={q}", "/tr/search?q={q}", "/Search?q={q}",
]
SKIP_EXT = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".ico", ".webp", ".mp4")


def find_get_form(html: str, base: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    for form in soup.find_all("form"):
        method = (form.get("method") or "get").lower()
        if method != "get":
            continue
        inputs = form.find_all("input")
        text_inputs = [i for i in inputs if (i.get("type") or "text").lower() in ("text", "search") and i.get("name")]
        if not text_inputs:
            continue
        name = text_inputs[0]["name"]
        params = {i["name"]: i.get("value", "") for i in inputs
                  if i.get("name") and (i.get("type") or "").lower() == "hidden"}
        params[name] = "{q}"
        action = urljoin(base, form.get("action") or base)
        return action + ("&" if "?" in action else "?") + urlencode(params).replace("%7Bq%7D", "{q}")
    return None


def links(html: str, base: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    host = urlparse(base).hostname or ""
    root = ".".join(host.split(".")[-3:]) if host.endswith(".bel.tr") else ".".join(host.split(".")[-2:])
    out = {}
    for a in soup.find_all("a", href=True):
        u = urljoin(base, a["href"]).split("#")[0]
        h = urlparse(u).hostname or ""
        if not h.endswith(root) or u.lower().endswith(SKIP_EXT):
            continue
        out[u] = a.get_text(" ", strip=True)[:160]
    return out


def try_template(tpl: str, base: str) -> dict | None:
    r1 = fetch(tpl.format(q=TERM), purpose="site_arama")
    if not r1["ok"] or "html" not in r1.get("ctype", ""):
        return None
    r0 = fetch(tpl.format(q=BASE_TERM), purpose="site_arama_taban")
    l1, l0 = links(r1["text"], r1["final_url"]), links(r0["text"], r0["final_url"]) if r0["ok"] else {}
    # Arama sayfasının kendine/sayfalamaya verdiği bağlantılar (sorgu dizesinde terim geçen) sonuç sayılmaz.
    l1 = {u: t for u, t in l1.items() if TERM not in fold(urlparse(u).query) and
          not urlparse(u).path.rstrip("/").lower().endswith("/" + TERM)}
    new = {u: t for u, t in l1.items() if u not in l0}
    asb = {u: t for u, t in l1.items() if ASBEST_RE.search(fold(u + " " + t))}
    cand = {**new, **asb}
    # arama sayfası sorgu terimini sayfada geri basmıyorsa muhtemelen gerçek arama sayfası değil
    echoes = TERM in fold(r1["text"])
    return {"sablon": tpl, "son_url": r1["final_url"], "yeni_link": len(new), "asbest_link": len(asb),
            "adaylar": cand, "terim_yankisi": echoes}


def run(row: dict) -> dict:
    base = row["kanonik_url"]
    home = fetch(base, purpose="ana_sayfa")
    tried, best = [], None
    form_tpl = find_get_form(home["text"], home["final_url"]) if home["ok"] else None
    templates = ([form_tpl] if form_tpl else []) + [urljoin(base, p) for p in PATTERNS]
    for tpl in templates:
        res = try_template(tpl, base)
        tried.append(tpl)
        if res and res["terim_yankisi"]:
            if best is None or len(res["adaylar"]) > len(best["adaylar"]):
                best = res
            if res["asbest_link"] > 0:
                break
        if len(tried) >= 6 and best:
            break
    if best is None:
        return {"ilce": row["ilce"], "durum": "arama_bulunamadi", "denenen": len(tried), "adaylar": {}}
    # sonuc_yok_veya_js: arama sayfası çalışıyor ama asbest başlıklı sonuç yok; ya gerçekten
    # içerik yok ya da sonuçlar JavaScript ile yükleniyor -> tarayıcıyla teyit edilmeli.
    durum = "sonuc_var" if best["asbest_link"] else ("sonuc_yok_veya_js" if best["yeni_link"] == 0
                                                      else "sonuc_basliksiz")
    return {"ilce": row["ilce"], "durum": durum, "form_bulundu": bool(form_tpl), "sablon": best["sablon"],
            "son_url": best["son_url"], "yeni_link": best["yeni_link"], "asbest_link": best["asbest_link"],
            "denenen": len(tried), "adaylar": best["adaylar"]}


def main() -> None:
    rows = [r for r in csv.DictReader(open(OUT / "erisim.csv", encoding="utf-8-sig")) if r["durum"] == "erisildi"]
    with ThreadPoolExecutor(max_workers=13) as ex:
        res = list(ex.map(run, rows))
    with open(OUT / "aday_urller_sitearama.txt", "w", encoding="utf-8") as f:
        for r in res:
            for u, t in r["adaylar"].items():
                if ASBEST_RE.search(fold(u + " " + t)):
                    f.write(f"{r['ilce']}\t{u}\t{maskele(t)}\n")
    for r in res:
        r["ornekler"] = " | ".join(f"{maskele(t)} <{u}>" for u, t in list(r["adaylar"].items())[:8]
                                   if ASBEST_RE.search(fold(u + " " + t)))
    write_csv(OUT / "site_arama.csv", res, ["ilce", "durum", "form_bulundu", "sablon", "son_url",
                                            "yeni_link", "asbest_link", "denenen", "ornekler"])
    for r in res:
        print(f"{r['ilce']:<14} {r['durum']:<17} asbest_link={r.get('asbest_link', 0):<4} {r.get('son_url', '')[:70]}")


if __name__ == "__main__":
    main()
