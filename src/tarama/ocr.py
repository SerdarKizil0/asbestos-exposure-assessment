"""Aşama 8: Taranmış (metin katmanı olmayan) PDF'ler için OCR.

belgeler.csv'de ocr_gerekli=evet olan PDF'leri sayfa sayfa görüntüye çevirip tesseract ile okur,
metni ciktilar/tarama/ocr/<sha256>.txt dosyasına (sayfalar \\f ile ayrılmış) yazar ve asbest bağlamlarını
ciktilar/tarama/bulgular_ocr.csv'ye ekler. Uzun sürer (sayfa başına birkaç saniye): yerelde, çok çekirdekle çalıştırın.

Gereken: poppler-utils (pdftoppm), tesseract + Türkçe dil paketi (tesseract-ocr-tur).
Kullanım: python3 ocr.py [--dil tur] [--is 4] [--en-eski-yil 2016] [--sadece ILCE]
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from common import OUT, RAW, write_csv
from harvest import contexts

YEAR = re.compile(r"(20[0-2]\d)")


def raw_path(url: str) -> Path | None:
    for m in glob.glob(str(RAW / "*" / "*.meta.json")):
        if json.load(open(m, encoding="utf-8"))["url"] == url:
            return Path(m[:-10] + ".pdf")
    return None


def ocr_pdf(args: tuple[str, str, str, str]) -> tuple[str, list[dict]]:
    ilce, url, sha, lang = args
    out_txt = OUT / "ocr" / f"{sha}.txt"
    if not out_txt.exists():
        pdf = raw_path(url)
        if pdf is None or not pdf.exists():
            return url, []
        pages = []
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["pdftoppm", "-r", "150", "-gray", "-png", str(pdf), f"{td}/s"], check=False)
            for img in sorted(Path(td).glob("s-*.png")):
                res = subprocess.run(["tesseract", str(img), "-", "-l", lang, "--psm", "3"],
                                     capture_output=True, env={**os.environ, "OMP_THREAD_LIMIT": "1"})
                pages.append(res.stdout.decode("utf-8", "replace"))
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text("\f".join(pages), encoding="utf-8")
    text = out_txt.read_text(encoding="utf-8")
    return url, [{"ilce": ilce, "url": url, "baslik": "(OCR)", "tur": "pdf-ocr", "sha256": sha, **c}
                 for c in contexts(text)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dil", default="tur")
    ap.add_argument("--is", dest="jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--en-eski-yil", type=int, default=2016)
    ap.add_argument("--sadece", default="")
    a = ap.parse_args()
    docs = [d for d in csv.DictReader(open(OUT / "belgeler.csv", encoding="utf-8-sig"))
            if d["ocr_gerekli"] == "evet" and d["durum"] == "ok" and int(d["sayfa_sayisi"] or 0) > 20]
    sel = []
    for d in docs:
        ys = [int(y) for y in YEAR.findall(d["url"] + " " + d["baslik"])]
        if ys and max(ys) < a.en_eski_yil:
            continue
        if a.sadece and d["ilce"] != a.sadece:
            continue
        sel.append((d["ilce"], d["url"], d["sha256"], a.dil))
    print(f"{len(sel)} PDF OCR'lanacak ({sum(int(d['sayfa_sayisi']) for d in docs if d['url'] in {s[1] for s in sel})} sayfa)")
    rows = []
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for url, found in ex.map(ocr_pdf, sel):
            rows.extend(found)
            print(f"  {len(found):>3} asbest bağlamı  {url[-70:]}")
    write_csv(OUT / "bulgular_ocr.csv", rows, ["ilce", "url", "baslik", "tur", "sayfa", "esleme_sayisi", "sinif",
                                                "sayilar", "baglam", "sha256"])


if __name__ == "__main__":
    main()
