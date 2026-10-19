"""Aşama 5: Aday belgeleri indir, metni çıkar, asbest bağlamlarını ve sayıları ayıkla.

Girdi: ciktilar/tarama/aday_urller_*.txt (ilce<TAB>url<TAB>başlık) + sitemap_ozet.csv'deki asbest URL'leri
Çıktı:
  veri/ham/<slug>/<hash>.<uzantı> + .meta.json  (kanıt: SHA-256, erişim zamanı)
  ciktilar/tarama/belgeler.csv  (her belge için erişim/çıkarım durumu = kapsam günlüğü)
  ciktilar/tarama/bulgular.csv  (kişi adı içerebilir, git'e girmez; her asbest geçişi için bağlam, sayfa, ayıklanan sayılar)

Kullanım: python3 harvest.py [--sadece-yeni]
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from common import ASBEST_RE, OUT, RAW, download, fetch, fold, read_seeds, write_csv

NUM_UNIT_RE = re.compile(
    r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)\s*"
    r"(ton|kg|kilogram|m2|m²|metrekare|adet|bina|yap[ıi]|numune|ruhsat|saha|şantiye|santiye|rapor|denetim)",
    re.I)
CTX = 350


def seed_index() -> dict[str, tuple[str, str]]:
    idx = {}
    for s in read_seeds():
        for d in s["aday_alanlar"].split(";"):
            idx[d] = (s["ilce"], s["slug"])
    return idx


SEEDS = seed_index()
SLUG_BY_ILCE = {s["ilce"]: s["slug"] for s in read_seeds()}


def owner(url: str) -> tuple[str, str]:
    host = (urlparse(url).hostname or "").lower()
    for dom, val in SEEDS.items():
        if host == dom or host.endswith("." + dom):
            return val
    return ("?", "diger")


def fold_with_map(text: str) -> tuple[str, list[int]]:
    out, idx = [], []
    for i, ch in enumerate(text):
        f = fold(ch)
        out.append(f)
        idx.extend([i] * len(f))
    return "".join(out), idx


def pdf_text_path(p: Path) -> tuple[str, int]:
    try:
        txt = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True,
                             timeout=600).stdout.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        txt = ""
    try:
        info = subprocess.run(["pdfinfo", str(p)], capture_output=True, timeout=60).stdout.decode(
            "utf-8", errors="replace")
        pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    except Exception:
        pages = txt.count("\f") + 1
    return txt, pages


def pdf_text(content: bytes) -> tuple[str, int]:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "d.pdf"
        p.write_bytes(content)
        return pdf_text_path(p)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def html_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    return soup.get_text("\n", strip=True)


def contexts(text: str) -> list[dict]:
    folded, idx = fold_with_map(text)
    spans = []
    for m in ASBEST_RE.finditer(folded):
        a, b = idx[m.start()], idx[min(m.end(), len(idx)) - 1] + 1
        s, e = max(0, a - CTX), min(len(text), b + CTX)
        if spans and s <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], e)
            spans[-1][2] += 1
        else:
            spans.append([s, e, 1])
    out = []
    for s, e, n in spans:
        snippet = re.sub(r"\s+", " ", text[s:e]).strip()
        page = text.count("\f", 0, s) + 1
        nums = ["{} {}".format(v, u) for v, u in NUM_UNIT_RE.findall(snippet)]
        out.append({"sayfa": page, "esleme_sayisi": n, "baglam": snippet, "sayilar": "; ".join(nums[:20]),
                    "sinif": "sayisal" if nums else "metin"})
    return out


def process(item: tuple[str, str, str]) -> tuple[dict, list[dict]]:
    ilce, url, title = item
    oi, slug = owner(url)
    ilce = ilce if ilce and ilce != "?" else oi
    if slug == "diger" and ilce in SLUG_BY_ILCE:
        # belge belediyenin kendi alan adında değil (ör. Beşiktaş → r2web.besiktasplus.app)
        slug = SLUG_BY_ILCE[ilce]
    r = fetch(url, purpose="hasat", max_bytes=80_000_000, timeout=90)
    doc = {"ilce": ilce, "url": url, "baslik": title, "durum": r["durum"], "http": r.get("status"),
           "bytes": r.get("bytes", 0), "tur": "", "sayfa_sayisi": "", "metin_uzunlugu": 0,
           "asbest_gecisi": 0, "ocr_gerekli": "", "sha256": "",
           "erisim": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    d = RAW / slug
    d.mkdir(parents=True, exist_ok=True)
    stem = hashlib.sha1(url.encode()).hexdigest()[:16]
    on_disk = False
    if not r["ok"] and "Connection broken" in r.get("hata", ""):
        # aktarım yarıda kesildi: bir kez, diske akıtarak yeniden dene
        dl = download(url, d / f"{stem}.pdf", purpose="hasat_yeniden")
        if dl["ok"]:
            r = {**dl, "ok": True, "content": (d / f"{stem}.pdf").read_bytes()[:8], "kesildi": True,
                 "ctype": dl.get("ctype") or "application/pdf"}
            doc["durum"], on_disk = "ok", True
    if not r["ok"]:
        return doc, []
    content = r["content"]
    ctype = r.get("ctype", "")
    is_pdf = content[:5] == b"%PDF-" or "pdf" in ctype
    ext = "pdf" if is_pdf else ("html" if "html" in ctype else "bin")
    path = d / f"{stem}.{ext}"
    if r.get("kesildi"):
        # 80 MB sınırını aşan dosya: tamamını diske akıt (bellekte tutmadan)
        del content
        if not on_disk:
            dl = download(url, path)
            if not dl["ok"]:
                doc["durum"] = "buyuk_dosya_" + dl["durum"]
                return doc, []
        size, sha = path.stat().st_size, sha256_file(path)
    else:
        path.write_bytes(content)
        size, sha = len(content), hashlib.sha256(content).hexdigest()
    doc["bytes"] = size
    (d / f"{stem}.meta.json").write_text(json.dumps(
        {"url": url, "final_url": r.get("final_url"), "erisim": doc["erisim"], "sha256": sha,
         "ctype": ctype, "bytes": size}, ensure_ascii=False, indent=1), encoding="utf-8")
    if is_pdf:
        text, pages = pdf_text_path(path)
        doc["sayfa_sayisi"] = pages
        if len(text.strip()) < 200 * max(1, pages) * 0.1:
            doc["ocr_gerekli"] = "evet"
    elif ext == "html":
        text = html_text(r["text"])
    else:
        text = ""
    doc.update({"tur": ext, "metin_uzunlugu": len(text), "sha256": sha})
    found = contexts(text)
    doc["asbest_gecisi"] = sum(f["esleme_sayisi"] for f in found)
    rows = [{"ilce": ilce, "url": url, "baslik": title, "tur": ext, "sha256": sha, **f} for f in found]
    return doc, rows


def load_candidates() -> list[tuple[str, str, str]]:
    items: dict[str, tuple[str, str, str]] = {}
    for path in sorted(glob.glob(str(OUT / "aday_urller_*.txt"))):
        for line in open(path, encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and parts[1].startswith("http"):
                items.setdefault(parts[1], (parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    sm = OUT / "sitemap_ozet.csv"
    if sm.exists():
        for row in csv.DictReader(open(sm, encoding="utf-8-sig")):
            for u in (row.get("asbest_urller") or "").split():
                items.setdefault(u, (row["ilce"], u, "(site haritası)"))
    # Sunucular arasında sırayla dağıt (round-robin): aynı belediyeye yığılmayı önler, turu hızlandırır.
    by_host: dict[str, list] = {}
    for it in items.values():
        by_host.setdefault(urlparse(it[1]).hostname or "", []).append(it)
    ordered, queues = [], list(by_host.values())
    while queues:
        for qu in list(queues):
            ordered.append(qu.pop(0))
            if not qu:
                queues.remove(qu)
    return ordered


def main() -> None:
    only_new = "--sadece-yeni" in sys.argv
    cands = load_candidates()
    done_docs, done_hits = [], []
    if only_new and (OUT / "belgeler.csv").exists():
        done_docs = list(csv.DictReader(open(OUT / "belgeler.csv", encoding="utf-8-sig")))
        done_hits = list(csv.DictReader(open(OUT / "bulgular.csv", encoding="utf-8-sig")))
        # 80 MB'de kesilmiş eski indirmeler tamamlanmamış sayılır ve yeniden işlenir.
        # 80 MB'yi aşan ama diske tam inmiş dosyalar (boyutu kayıtla aynı) tamam sayılır.
        def complete(d: dict) -> bool:
            if d["durum"] != "ok":
                return False
            size = int(d.get("bytes") or 0)
            if size < 80_000_000:
                return True
            oi, slug = owner(d["url"])
            if slug == "diger":
                slug = SLUG_BY_ILCE.get(d["ilce"], "diger")
            stem = hashlib.sha1(d["url"].encode()).hexdigest()[:16]
            f = RAW / slug / f"{stem}.pdf"
            return f.exists() and f.stat().st_size == size
        seen = {d["url"] for d in done_docs if complete(d)}
        cands = [c for c in cands if c[1] not in seen]
        done_docs = [d for d in done_docs if complete(d)]
        done_hits = [h for h in done_hits if h["url"] in seen]
    print(f"{len(cands)} aday belge işlenecek")
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(process, cands))
    docs = done_docs + [d for d, _ in results]
    hits = done_hits + [h for _, hs in results for h in hs]
    write_csv(OUT / "belgeler.csv", docs, ["ilce", "url", "baslik", "durum", "http", "tur", "bytes",
                                            "sayfa_sayisi", "metin_uzunlugu", "asbest_gecisi", "ocr_gerekli",
                                            "sha256", "erisim"])
    write_csv(OUT / "bulgular.csv", hits, ["ilce", "url", "baslik", "tur", "sayfa", "esleme_sayisi", "sinif",
                                            "sayilar", "baglam", "sha256"])
    ok = sum(d["durum"] == "ok" for d in docs)
    print(f"Belge: {ok}/{len(docs)} indirildi; asbest geçen: {sum(int(d['asbest_gecisi'] or 0) > 0 for d in docs)}; "
          f"bağlam: {len(hits)} (sayısal: {sum(h['sinif'] == 'sayisal' for h in hits)})")


if __name__ == "__main__":
    main()
