"""İBB açık veri CSV'lerinin temiz kopyaları: veri/ham/ibb → veri/dogrulanmis (UTF-8, virgül ayırıcı).

Özgün dosyalar Windows-1254 kodlamalı ve ';' ayırıcılıdır. İçerik değiştirilmez; yalnız kodlama ve ayırıcı
değişir. Özgün dosyanın SHA-256'sı kaynaklar.csv'deki kayıtla aynı değilse betik durur (yeni sürüm indirilmiş
demektir: önce kaynaklar.csv'yi güncelleyin).

Lisans: İBB Açık Veri Lisansı (atıf zorunlu; CC BY 4.0 ile uyumlu).
Bilinen sorun: mahalle_bina_2017 dosyasında "19 MAYIS" mahalle adı "19.May" olarak bozulmuş; dosyaları
mahalle adıyla değil UAVT koduyla birleştirin.

Kullanım:  python src/ibb_csv.py
"""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
HAM = KOK / "veri" / "ham" / "ibb"
HEDEF = KOK / "veri" / "dogrulanmis"

DOSYALAR = {  # ham dosya: (kaynak_id, temiz kopya)
    "deprem_senaryosu_analiz_sonuclari.csv": ("ibb_deprem_senaryosu", "ibb_deprem_senaryosu_mw75_mahalle.csv"),
    "mahalle_bina_2017.csv": ("ibb_bina_2017", "ibb_bina_2017_mahalle.csv"),
}


def main() -> None:
    kayit = {r["kaynak_id"]: r for r in csv.DictReader(open(KOK / "kaynaklar.csv", encoding="utf-8"))}
    for ham, (kid, temiz) in DOSYALAR.items():
        icerik = (HAM / ham).read_bytes()
        sha = hashlib.sha256(icerik).hexdigest()
        if sha != kayit[kid]["sha256"]:
            raise SystemExit(f"{ham}: SHA-256 kaynaklar.csv ile uyuşmuyor ({sha[:12]}… ≠ {kayit[kid]['sha256'][:12]}…)")
        satirlar = list(csv.reader(io.StringIO(icerik.decode("cp1254").lstrip("﻿")), delimiter=";"))
        with open(HEDEF / temiz, "w", newline="", encoding="utf-8") as f:
            csv.writer(f, lineterminator="\n").writerows(satirlar)
        print(f"{temiz}: {len(satirlar) - 1} satır (kaynak_id {kid}, sha256 {sha[:12]}…)")


if __name__ == "__main__":
    main()
