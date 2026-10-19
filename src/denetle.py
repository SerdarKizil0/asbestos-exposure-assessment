"""Herkese açık depo kurallarının denetimi. Hata varsa çıkış kodu 1 olur; commit yapılmaz.

  python src/denetle.py            git'e girecek bütün dosyalar (izlenen + yeni, .gitignore dışı)
  python src/denetle.py --kanca    yalnız sahnelenmiş dosyalar (git pre-commit kancası)
  python src/denetle.py --liste    denetlenen dosyaların listesini de yazdır

Denetlenenler:
  1. 50 MB'tan büyük dosya, yasak uzantı (PDF, görüntü, Excel, arşiv, video), yasak klasör (gelen/, veri/ham/)
  2. Gizli bilgi: .env, anahtar dosyaları, API anahtarı ve şifre kalıpları
  3. Kişisel veri: e-posta, telefon, TC kimlik no (sağlama hanesiyle); unvan + ad kalıbı (uyarı)
  4. Kaynak bütünlüğü: her kaynak_id ve kaynak_url kaynaklar.csv'de var mı, SHA-256 biçimi
  5. Model ile parametre tablosunun tutarlılığı (EF, k_lif)
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
SINIR = 50 * 1024 * 1024

YASAK_UZANTI = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif",
                ".tiff", ".heic", ".zip", ".7z", ".rar", ".tar", ".gz", ".mp4", ".mov", ".avi", ".mkv", ".xlsx", ".xlsm",
                ".xls", ".shp", ".shx", ".dbf", ".npy", ".key", ".pem", ".p12", ".pfx"}
SEKIL_ISTISNA = ("ciktilar/sekiller/",)
YASAK_KLASOR = ("gelen/", "veri/ham/", "model/cikti/")
YASAK_AD = {".env", ".cdsapirc", "bulgular.csv", "bulgular_ocr.csv", "plan.md"}
METIN = {".csv", ".md", ".txt", ".py", ".js", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".gitignore",
         ".gitattributes", ""}

EPOSTA = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EPOSTA_IZIN = re.compile(r"@users\.noreply\.github\.com$|^noreply@")
TELEFON = re.compile(r"(?<![\w.])(?:\+90[\s-]?|0[\s-]?)?\(?[2-5]\d{2}\)?[\s-]\d{3}[\s-]\d{2}[\s-]\d{2}(?![\w.])"
                     r"|(?<![\w.])444[\s-]\d{2}[\s-]\d{2}(?![\w.])")
TCNO = re.compile(r"(?<![\w./=-])[1-9]\d{10}(?![\w./-])")
GIZLI = re.compile(r"AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}"
                   r"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
                   r"|(?i:\b(?:api[_-]?key|secret|password|passwd|şifre)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"])")
_U, _L = "A-ZÇĞİÖŞÜ", "a-zçğıöşü"
UNVAN_AD = re.compile(rf"(?:irtibat|[Ss]ayın|[Mm]üdürü|[Mm]ühendisi|[Uu]zmanı|[Mm]uhtarı)\s*:?\s+"
                      rf"[{_U}][{_L}]+\s+[{_U}][{_U}{_L}]+")


def tc_gecerli(s: str) -> bool:
    d = [int(c) for c in s]
    return ((sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10 == d[9]) and (sum(d[:10]) % 10 == d[10])


def dosyalar(kanca: bool) -> list[str]:
    if not (KOK / ".git").exists():
        sys.exit("git deposu yok: önce 'git init' (denetim git'e girecek dosya listesiyle çalışır).")
    komut = (["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if kanca
             else ["git", "ls-files", "--cached", "--others", "--exclude-standard"])
    cikti = subprocess.run(komut, cwd=KOK, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return [s for s in cikti.splitlines() if s]


def oku_csv(yol: Path) -> list[dict]:
    with open(yol, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def dosya_denetimi(adlar: list[str], hata: list, uyari: list) -> None:
    for ad in adlar:
        yol = KOK / ad
        if not yol.exists():
            continue
        kucuk = ad.lower()
        uz = yol.suffix.lower()
        if yol.stat().st_size > SINIR:
            hata.append(f"{ad}: 50 MB'tan büyük ({yol.stat().st_size / 1e6:.1f} MB)")
        if kucuk.startswith(YASAK_KLASOR):
            hata.append(f"{ad}: yasak klasör")
        if yol.name.lower() in YASAK_AD or yol.name.lower().startswith(".env"):
            if yol.name != ".env.example":
                hata.append(f"{ad}: yasak dosya adı")
        if uz in YASAK_UZANTI and not kucuk.startswith(SEKIL_ISTISNA):
            hata.append(f"{ad}: yasak uzantı ({uz})")
        if "chatgpt" in kucuk:
            hata.append(f"{ad}: ChatGPT notu")
        if uz not in METIN or yol.stat().st_size > SINIR:
            continue
        metin = yol.read_text(encoding="utf-8", errors="replace")
        for m in EPOSTA.finditer(metin):
            if not EPOSTA_IZIN.search(m.group()):
                hata.append(f"{ad}: e-posta adresi ({m.group()})")
        for m in TELEFON.finditer(metin):
            hata.append(f"{ad}: telefon numarası olabilir ({m.group().strip()})")
        for m in TCNO.finditer(metin):
            if tc_gecerli(m.group()):
                hata.append(f"{ad}: TC kimlik numarası olabilir ({m.group()[:3]}…)")
        for m in GIZLI.finditer(metin):
            hata.append(f"{ad}: gizli bilgi kalıbı ({m.group()[:12]}…)")
        for m in UNVAN_AD.finditer(metin):
            uyari.append(f"{ad}: unvan + ad kalıbı, kişi adı olabilir ({m.group()[:40]})")


def kaynak_denetimi(hata: list, uyari: list) -> None:
    kay = oku_csv(KOK / "kaynaklar.csv")
    idler = [k["kaynak_id"] for k in kay]
    for i in sorted({i for i in idler if idler.count(i) > 1}):
        hata.append(f"kaynaklar.csv: yinelenen kaynak_id {i}")
    for k in kay:
        if k["sha256"] and not re.fullmatch(r"[0-9a-f]{64}", k["sha256"]):
            hata.append(f"kaynaklar.csv: {k['kaynak_id']} SHA-256 biçimi bozuk")
        if not k["url"]:
            uyari.append(f"kaynaklar.csv: {k['kaynak_id']} URL'si yok")
    idset, urlset = set(idler), {k["url"] for k in kay if k["url"]}

    tablolar = [KOK / "veri" / "parametreler.csv", *sorted((KOK / "veri" / "literatur").glob("*.csv"))]
    for t in tablolar:
        for n, r in enumerate(oku_csv(t), 2):
            kid = r.get("kaynak_id")
            if kid is None:
                break
            if kid and kid not in idset:
                hata.append(f"{t.relative_to(KOK)} satır {n}: kaynak_id '{kid}' kaynaklar.csv'de yok")
    for n, r in enumerate(oku_csv(KOK / "veri" / "dogrulanmis" / "veri_noktalari.csv"), 2):
        if r["kaynak_url"] not in urlset:
            hata.append(f"veri_noktalari.csv satır {n}: kaynak_url kaynaklar.csv'de yok ({r['kaynak_url'][:60]})")
        if not r["alinti"]:
            uyari.append(f"veri_noktalari.csv satır {n}: alıntı boş")


def model_denetimi(hata: list) -> None:
    metin = (KOK / "model" / "model.py").read_text(encoding="utf-8")
    par = {r["parametre_id"]: r for r in oku_csv(KOK / "veri" / "parametreler.csv")}
    for anahtar, pid in (("EF", "P20"), ("k_lif", "P26")):
        m = re.search(rf'"{anahtar}":\s*\(\s*([0-9.eE+-]+)\s*,', metin)
        if not m:
            hata.append(f"model.py: P['{anahtar}'] okunamadı")
        elif abs(float(m.group(1)) - float(par[pid]["deger"])) > 1e-12 * max(1.0, abs(float(par[pid]["deger"]))):
            hata.append(f"model.py P['{anahtar}'] = {m.group(1)}, parametreler.csv {pid} = {par[pid]['deger']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kanca", action="store_true", help="yalnız sahnelenmiş dosyalar")
    ap.add_argument("--liste", action="store_true", help="denetlenen dosyaları yazdır")
    arg = ap.parse_args()
    adlar = dosyalar(arg.kanca)
    hata, uyari = [], []
    dosya_denetimi(adlar, hata, uyari)
    kaynak_denetimi(hata, uyari)
    model_denetimi(hata)
    if arg.liste:
        for a in adlar:
            print("  ", a)
    print(f"denetlenen dosya: {len(adlar)}")
    for u in uyari:
        print("UYARI", u)
    for h in hata:
        print("HATA ", h)
    print(f"{len(hata)} hata, {len(uyari)} uyarı")
    sys.exit(1 if hata else 0)


if __name__ == "__main__":
    main()
