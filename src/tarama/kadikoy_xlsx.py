"""Kadıköy asbest verileri → ciktilar/excel/kadikoy_asbest_verileri.xlsx

İçerik: açık veri yıllık serisi (2015-2025), faaliyet raporlarındaki malzeme türü dağılımı (marley, kazan, eternit),
belediye sayfası ve haberlerdeki toplamlar, tutarlılık kontrolleri ve kaynak listesi.
Belgeden alınan her değerin alıntısı yerel kopyada (veri/ham/kadikoy) aranır; bulunamazsa betik durur.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

KOK = Path(__file__).resolve().parents[2]
RAW = KOK / "veri" / "ham" / "kadikoy"
CIKTI = KOK / "ciktilar" / "excel" / "kadikoy_asbest_verileri.xlsx"

F = "Arial"
MAVI = Font(name=F, size=10, color="0000FF")
SIYAH = Font(name=F, size=10)
GRI = Font(name=F, size=10, color="7F7F7F")
KALIN = Font(name=F, size=10, bold=True)
BASLIK = Font(name=F, size=12, bold=True)
BEYAZ = Font(name=F, size=10, bold=True, color="FFFFFF")
HDR = PatternFill("solid", fgColor="404040")
SAR = Alignment(wrap_text=True, vertical="top")

BELGE = {  # anahtar: (yerel kopya, URL, ad)
    "acikveri": ("asbest_verileri.csv", "https://acikveri.kadikoy.bel.tr/dataset/3f35ced9-0900-437e-82a0-51bfc4a2e32f/resource/"
                 "63f4d582-38bc-4e77-b24d-1bf1e71eb31d/download/asbest_verileri.csv", "Kadıköy Açık Veri: Asbest Verileri (CSV)"),
    "fr2018": ("06492c72e8fcd7d4.pdf", "https://anlat.kadikoy.bel.tr/kbpanel/Uploads/Files/2018-faaliyet.pdf", "2018 Faaliyet Raporu"),
    "fr2021": ("99f0a31dc8225e58.pdf", "https://kadikoyapi.kadikoy.bel.tr/86e4a6a02544421ab4d4fb261d73b47b.pdf", "2021 Faaliyet Raporu"),
    "fr2022": ("8b85b2502c962c58.pdf", "https://anlat.kadikoy.bel.tr/kbpanel/Uploads/Files/FaaliyetRaporu2022.pdf", "2022 Faaliyet Raporu"),
    "fr2023": ("b52a26483ea866c8.pdf", "https://kadikoyapi.kadikoy.bel.tr/2f0f441bd04c46d0a31249fd08d76947.pdf", "2023 Faaliyet Raporu"),
    "fr2024": ("32b3e5883c25c665.pdf", "https://kadikoyapi.kadikoy.bel.tr/564fd14596d14f41a76de32bc12b5899.pdf", "2024 Faaliyet Raporu"),
    "cevre": ("bc146e9cbd83acb6.html", "https://cevre.kadikoy.bel.tr/icerik/insaat-sahalarinda-asbest-atiklarinin-kontrolu",
              "Çevre birimi sayfası: İnşaat Sahalarında Asbest Atıklarının Kontrolü"),
    "haber_doga": ("1cf22eefcbc430be.html", "https://www.kadikoy.bel.tr/tr/haber-detay/kadikoyde-dogaya-emek-veriliyor-5150",
                   "Haber: Kadıköy'de Doğaya Emek Veriliyor"),
    "haber_1yil": ("e66615bcec3b4fab.html", "https://www.kadikoy.bel.tr/en/news/kadikoy-belediyesinin-1-yili-5161",
                   "Haber: Kadıköy Belediyesi'nin 1 Yılı"),
    "haber_yikim": ("4dee58f9dc7a22c5.html", "https://www.kadikoy.bel.tr/tr/haber-detay/asbestli-binalara-yikim-izni-yok-4885",
                    "Haber: Asbestli Binalara Yıkım İzni Yok"),
    "tarife": ("f5752bd9e80a50b4.pdf", "https://cevre.kadikoy.bel.tr/Uploads/Files/Kadikoy_Belediyesi_Asbest_Ucret_Tarifesi.pdf",
               "Asbest Ücret Tarifesi (PDF, Temmuz 2018)"),
}


@lru_cache(maxsize=None)
def metin(anahtar: str, sayfa: int | None = None) -> str:
    yol = RAW / BELGE[anahtar][0]
    if yol.suffix == ".pdf":
        t = subprocess.run(["pdftotext", "-f", str(sayfa), "-l", str(sayfa), str(yol), "-"],
                           capture_output=True, text=True, check=True).stdout
    else:
        s = BeautifulSoup(yol.read_text(encoding="utf-8", errors="replace"), "lxml")
        for x in s(["script", "style"]):
            x.decompose()
        t = s.get_text(" ")
    t = re.sub(r"-\s*\n\s*", "", t)  # satır sonu tirelemesi
    return re.sub(r"\s+", " ", t)


def dogrula(anahtar: str, sayfa: int | None, alinti: str) -> str:
    if alinti not in metin(anahtar, sayfa):
        raise SystemExit(f"Alıntı belgede yok: {anahtar} s.{sayfa}: {alinti}")
    return alinti


def kaynak_adi(anahtar: str, sayfa: int | None) -> str:
    return BELGE[anahtar][2] + (f", PDF s.{sayfa}" if sayfa else "")


def baslik_satiri(ws, satir, basliklar, genislik=None):
    for j, b in enumerate(basliklar, 1):
        c = ws.cell(row=satir, column=j, value=b)
        c.font, c.fill, c.alignment = BEYAZ, HDR, Alignment(wrap_text=True, vertical="top")
    for j, w in enumerate(genislik or [], 1):
        ws.column_dimensions[chr(64 + j)].width = w


def yaz(ws, r, c, v, font=SIYAH, fmt=None, wrap=False):
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = font
    if fmt:
        cell.number_format = fmt
    if wrap:
        cell.alignment = SAR
    return cell


def acik_veri():
    satirlar = list(csv.reader(open(RAW / "asbest_verileri.csv", encoding="utf-8-sig"), delimiter=";"))
    yillar = [int(y) for y in satirlar[0][1:]]
    sayi = lambda s: float(s.replace(",", ".")) if "," in s else int(s)
    seri = {r[0]: [sayi(x) for x in r[1:]] for r in satirlar[1:]}
    return satirlar, yillar, seri


# Yıllık seriyle karşılaştırma notları (her biri belgede doğrulanan alıntıya dayanır)
KARSILASTIRMA = {
    2015: ("2018 FR tablosu ve 2017 haberi: 421 / 134 / 81,3", "fr2018", 166, "ASBEST VERILERI"),
    2016: ("2018 FR tablosu ve 2017 haberi: 796 / 207 / 386", "fr2018", 166, "ASBEST VERILERI"),
    2017: ("2018 FR tablosu ve 2017 haberi: 618 / 221 / 276,7", "haber_1yil", None, "2017 yilinda 618 insaat sahasi denetlendi ve 276,7 ton asbest atigi bertaraf edildi"),
    2018: ("2018 FR metni: 284 / 103 / 52,8", "fr2018", 166, "2018 yılında 284 inşaat sahası denetlenmiştir. 103 inşaat sahasında asbestli malzeme tespit edilmiş"),
    2019: ("2021-2023 FR tabloları: 144 / 21 / 17,53", "fr2021", 257, "17,53"),
    2020: ("2021-2024 FR tabloları: 158 / 23 / 23,77", "fr2021", 257, "23,77"),
    2021: ("2021 FR metni: 186 / 27 / 50.090 kg", "fr2021", 257, "2021 yılında 186 inşaat sahası denetlenmiştir. 27 inşaat sahasında asbestli malzeme tespit edilmiş"),
    2022: ("2022 FR metni: 251 / 17 / 92.025 kg", "fr2022", 288, "2022 yılında 251 inşaat sahası denetlenmiştir. 17 inşaat sahasında asbestli malzeme tespit edilmiş"),
    2023: ("2023 FR metni: 275 / 9 / 90.720 kg", "fr2023", 222, "2023 yılında 275 inşaat sahası denetlenmiştir. 9 inşaat sahasında asbestli malzeme tespit edilmiş"),
    2024: ("2024 FR metni: 525 / 17 / 10.400 kg", "fr2024", 200, "2024 yılında 525 inşaat sahası denetlenmiştir. 17 inşaat sahasında asbestli malzeme tespit edilmiş"),
    2025: ("Çevre birimi sayfası: 417 / 10 / 14,45 ton", "cevre", None, "2025 yılında 417 inşaat sahası denetlenmiş 10 inşaat sahasında asbestli malzeme tespit edilmiş; 14,45 ton asbest atığının bertarafı sağlanmıştır"),
}

# Malzeme türü: (dönem, marley bina, marley kg, kazan bina, kazan kg, eternit bina, eternit kg, diğer kg, belge, sayfa, alıntı)
MALZEME = [
    ("2015-2017", None, 310000, None, 206000, None, 218000, 10000, "haber_doga", None,
     "310 ton marley, 206 ton kazan, 218 ton eternit, 10 ton diger malzemeler olmak üzere toplam 744 ton asbest atigi"),
    ("2018", 24, 9720, 61, 21105, 18, 22000, None, "fr2018", 166,
     "24 binada marley (9.720 kg), 61 binada kazan (21.105 kg) ve 18 binada ethernit (22.000 kg) olmak üzere toplam 52,8 ton"),
    ("2019", None, None, None, None, None, None, None, None, None, None),
    ("2020", None, None, None, None, None, None, None, None, None, None),
    ("2021", 5, 3110, 14, 8550, 8, 38430, None, "fr2021", 257,
     "5 binada marley (3.110 kg), 14 binada kazan (8.550 kg) ve 8 binada eternit (38.430 kg) olmak üzere toplam 50.090 kg"),
    ("2022", None, None, 8, 4175, 9, 87850, None, "fr2022", 288,
     "8 binada kazan (4.175 kg) ve 9 binada ethernit (87.850 kg) olmak üzere toplam 92.025 kg"),
    ("2023", None, None, 1, 420, 8, 90300, None, "fr2023", 222,
     "1 binada kazan (420 kg) ve 8 binada ethernit (90.300 kg) olmak üzere toplam 90.720 kg"),
    ("2024", None, None, 10, 650, 7, 9750, None, "fr2024", 200,
     "10 binada kazan (650 kg) ve 7 binada ethernit (9.750 kg) olmak üzere toplam 10.400 kg"),
    ("2025", None, None, None, None, None, None, None, None, None, None),
]
MALZEME_YOK = {"2019": "2019 ve 2020 faaliyet raporları belediye sitesinde bulunamadı; açık veride tür dağılımı yok.",
               "2020": "2019 ve 2020 faaliyet raporları belediye sitesinde bulunamadı; açık veride tür dağılımı yok.",
               "2025": "Çevre birimi sayfası yalnız toplamı veriyor (14,45 ton); 2025 faaliyet raporu henüz yok."}


def eksik_belgeler() -> list[str]:
    """BELGE tablosundaki yerel kopyalardan veri/ham/kadikoy altında bulunmayanlar."""
    return [f"{BELGE[k][2]} ({BELGE[k][0]})" for k in BELGE if not (RAW / BELGE[k][0]).is_file()]


def main():
    eksik = eksik_belgeler()
    if eksik:
        raise SystemExit(
            f"DURDU: {len(eksik)} belgenin yerel kopyası {RAW.relative_to(KOK)} altında yok; "
            f"{CIKTI.relative_to(KOK)} DEĞİŞTİRİLMEDİ.\n" + "\n".join(f"  - {e}" for e in eksik)
            + "\nBelgeleri harvest.py ile indirin ya da eski çalışma ortamından veri/ham/kadikoy/ altına kopyalayın.")
    satirlar, yillar, seri = acik_veri()
    B, C, D = seri["Denetlenen İnşaat Sahası Sayısı"], seri["Asbest Tespit Edilen Bina Sayısı"], seri["Bertaraf Edilen Asbest Atığı Miktarı (ton)"]
    n = len(yillar)
    wb = Workbook()

    # ---- Okuma notu
    ws = wb.active
    ws.title = "Okuma notu"
    ws.column_dimensions["A"].width = 62
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 70
    yaz(ws, 1, 1, "Kadıköy Belediyesi asbest verileri, 2015-2025 (derleme: 19 Ekim 2026)", BASLIK)
    yaz(ws, 2, 1, "Belediyenin açık verisi, faaliyet raporları, çevre birimi sayfası ve haberlerinden; her değer belgesiyle bağlı.", GRI)
    yaz(ws, 4, 1, "Özet (Yıllık seri sayfasından formülle)", KALIN)
    son = 3 + n
    ozet = [("Denetlenen inşaat sahası, 2015-2025", f"=SUM('Yıllık seri'!B4:B{son})", "#,##0"),
            ("Asbest tespit edilen bina, 2015-2025", f"=SUM('Yıllık seri'!C4:C{son})", "#,##0"),
            ("Bertaraf edilen asbest atığı (ton), 2015-2025", f"=SUM('Yıllık seri'!D4:D{son})", "#,##0.00"),
            ("Tespit oranı (bina / denetlenen saha), havuz", f"=B6/B5", "0.0%"),
            ("Tespit edilen bina başına atık (kg), havuz", f"=1000*B7/B6", "#,##0"),
            ("Tespit oranı, 2015-2018", f"=SUM('Yıllık seri'!C4:C7)/SUM('Yıllık seri'!B4:B7)", "0.0%"),
            ("Tespit oranı, 2022-2025", f"=SUM('Yıllık seri'!C11:C{son})/SUM('Yıllık seri'!B11:B{son})", "0.0%")]
    for i, (et, f, fmt) in enumerate(ozet, 5):
        yaz(ws, i, 1, et)
        yaz(ws, i, 2, f, KALIN, fmt)
    yaz(ws, 8, 3, "Yayılım modelinde kullanılan iki değer: tespit oranı ve bina başına atık (havuz)", GRI)
    r = 13
    yaz(ws, r, 1, "Sayfalar", KALIN)
    sayfa_ack = [
        ("Yıllık seri", "Açık verideki üç gösterge, oran ve kümülatif toplamlar; her yılın faaliyet raporu ya da belediye sayfasıyla karşılaştırması."),
        ("Malzeme türü", "Faaliyet raporlarında yıllara göre marley, kazan ve eternit dağılımı (bina sayısı ve kg). Açık veride bu ayrım yok."),
        ("Tutarlılık ve bağlam", "Belgelerdeki toplamların yıllık seriyle karşılaştırması; başlangıç tarihi, envanter raporu ve tanım sorunları."),
        ("Açık veri (özgün)", "Belediyenin yayımladığı tablo, olduğu gibi."),
        ("Kaynaklar", "Bağlantılar, erişim zamanı, SHA-256 ve kullanılan sayfalar."),
    ]
    for j, (a, b) in enumerate(sayfa_ack, r + 1):
        yaz(ws, j, 1, a)
        yaz(ws, j, 3, b, wrap=True)
    r = r + len(sayfa_ack) + 2
    yaz(ws, r, 1, "Okurken dikkat", KALIN)
    notlar = [
        "Açık veri 'Asbest Tespit Edilen Bina Sayısı' diyor; faaliyet raporları aynı sayıyı 'asbestli malzeme tespit edilen inşaat sahası' olarak veriyor. Sayılar aynı.",
        "'Bertaraf edilen asbest atığı' asbestli malzemenin (eternit levha, marley, kazan yalıtımı) toplam kütlesidir; saf asbest miktarı değildir.",
        "Kadıköy veriyi yalnız ilçe toplamı olarak yayımlıyor; mahalle dağılımı yok. Belediye her yıkımda 'Asbest Envanter Raporu' istiyor (Tutarlılık ve bağlam sayfası): mahalle bazında dağılım bilgi edinme başvurusuyla istenebilir.",
        "Çevre birimi sayfasındaki 'bugüne kadar' toplamları (3.379 saha, 923,76 ton) ve 2021 faaliyet raporundaki '2015-2021 toplamı' yıllık tabloyla tutmuyor.",
    ]
    for j, t in enumerate(notlar, r + 1):
        yaz(ws, j, 1, "•")
        yaz(ws, j, 3, t, wrap=True)
    r = r + len(notlar) + 2
    yaz(ws, r, 1, "Renkler", KALIN)
    yaz(ws, r + 1, 1, "Mavi yazı: belgeden alınan değer", MAVI)
    yaz(ws, r + 2, 1, "Siyah yazı: formül", SIYAH)
    yaz(ws, r + 3, 1, "Gri yazı: açıklama", GRI)

    # ---- Yıllık seri
    ws = wb.create_sheet("Yıllık seri")
    yaz(ws, 1, 1, "Kadıköy asbest verileri, yıllık (Kadıköy Açık Veri, 6 Nisan 2026 güncellemesi)", BASLIK)
    baslik_satiri(ws, 3, ["Yıl", "Denetlenen inşaat sahası", "Asbest tespit edilen bina", "Bertaraf edilen asbest atığı (ton)",
                          "Tespit oranı", "Tespit edilen bina başına atık (kg)", "Kümülatif denetlenen saha", "Kümülatif bertaraf (ton)",
                          "Başka belgeyle karşılaştırma", "Karşılaştırma kaynağı"],
                  [8, 13, 13, 14, 11, 15, 13, 13, 40, 42])
    for i, y in enumerate(yillar):
        rr = 4 + i
        yaz(ws, rr, 1, y)
        yaz(ws, rr, 2, B[i], MAVI, "#,##0")
        yaz(ws, rr, 3, C[i], MAVI, "#,##0")
        yaz(ws, rr, 4, D[i], MAVI, "#,##0.00")
        yaz(ws, rr, 5, f"=C{rr}/B{rr}", fmt="0.0%")
        yaz(ws, rr, 6, f"=1000*D{rr}/C{rr}", fmt="#,##0")
        yaz(ws, rr, 7, f"=SUM($B$4:B{rr})", fmt="#,##0")
        yaz(ws, rr, 8, f"=SUM($D$4:D{rr})", fmt="#,##0.00")
        not_, k, s, al = KARSILASTIRMA[y]
        dogrula(k, s, al)
        yaz(ws, rr, 9, not_ + " (aynı)", wrap=True)
        yaz(ws, rr, 10, kaynak_adi(k, s), GRI, wrap=True)
    rt = 4 + n
    yaz(ws, rt, 1, "Toplam", KALIN)
    for col in "BCD":
        yaz(ws, rt, " ABCD".index(col), f"=SUM({col}4:{col}{rt-1})", KALIN, "#,##0" if col != "D" else "#,##0.00")
    yaz(ws, rt, 5, f"=C{rt}/B{rt}", KALIN, "0.0%")
    yaz(ws, rt, 6, f"=1000*D{rt}/C{rt}", KALIN, "#,##0")
    notlar = [
        "Tespit oranı = asbest tespit edilen bina / denetlenen inşaat sahası. Payda ve pay farklı birimler (saha, bina); belgelerde her sahaya bir bina sayılmış görünüyor.",
        "Bina başına atık, yıkılan binadan çıkan asbestli malzemenin (eternit levha, marley, kazan yalıtımı) kütlesidir; saf asbest değildir.",
        "2015-2017 değerleri 2018 faaliyet raporunun 166. sayfasındaki tabloda ve 2017 haberinde; 2019-2020 değerleri 2021-2024 raporlarının tablolarında aynı.",
    ]
    for j, t in enumerate(notlar, rt + 2):
        yaz(ws, j, 1, t, GRI)
    ws.freeze_panes = "B4"

    # ---- Malzeme türü
    ws = wb.create_sheet("Malzeme türü")
    yaz(ws, 1, 1, "Bertaraf edilen asbest atığının malzeme türüne göre dağılımı (faaliyet raporları ve 2017 haberi)", BASLIK)
    yaz(ws, 2, 1, "Açık veride bu ayrım yok. Boş hücre: belgede o yıl için değer yok.", GRI)
    baslik_satiri(ws, 4, ["Dönem", "Marley: bina", "Marley: kg", "Kazan: bina", "Kazan: kg", "Eternit: bina", "Eternit: kg", "Diğer: kg",
                          "Toplam bina", "Toplam kg", "Açık veri: bina", "Açık veri: kg", "Fark (kg)", "Kaynak", "Alıntı (belgedeki yazımla)"],
                  [11, 9, 10, 9, 10, 9, 11, 9, 9, 11, 10, 11, 9, 34, 70])
    ilk = 5
    for i, (donem, mb, mk, kb, kk, eb, ek, dk, k, s, al) in enumerate(MALZEME):
        rr = ilk + i
        yaz(ws, rr, 1, donem)
        for col, v in zip(range(2, 9), (mb, mk, kb, kk, eb, ek, dk)):
            if v is not None:
                yaz(ws, rr, col, v, MAVI, "#,##0")
        if k is None:
            yaz(ws, rr, 14, MALZEME_YOK[donem], GRI, wrap=True)
            continue
        dogrula(k, s, al)
        yaz(ws, rr, 9, f'=IF(COUNT(B{rr},D{rr},F{rr})=0,"",SUM(B{rr},D{rr},F{rr}))', fmt="#,##0")
        yaz(ws, rr, 10, f"=SUM(C{rr},E{rr},G{rr},H{rr})", fmt="#,##0")
        if donem == "2015-2017":
            yaz(ws, rr, 11, "=SUM('Yıllık seri'!C4:C6)", fmt="#,##0")
            yaz(ws, rr, 12, "=1000*SUM('Yıllık seri'!D4:D6)", fmt="#,##0")
        else:
            sat = 4 + yillar.index(int(donem))
            yaz(ws, rr, 11, f"='Yıllık seri'!C{sat}", fmt="#,##0")
            yaz(ws, rr, 12, f"=1000*'Yıllık seri'!D{sat}", fmt="#,##0")
        yaz(ws, rr, 13, f"=J{rr}-L{rr}", fmt="#,##0")
        yaz(ws, rr, 14, kaynak_adi(k, s), GRI, wrap=True)
        yaz(ws, rr, 15, al, wrap=True)
    son_m = ilk + len(MALZEME) - 1
    # Türe göre özet
    r = son_m + 3
    yaz(ws, r, 1, "Türe göre özet", KALIN)
    baslik_satiri(ws, r + 1, ["Malzeme", "Bina (2018, 2021-24)", "kg (2018, 2021-24)", "kg / bina", "Kütle payı (2018, 2021-24)",
                              "Kütle payı (2015-17)", "Kütle payı (2021-24)"])
    c = yaz(ws, r + 1, 14, "Ne olduğu (genel bilgi, belgede yok)", BEYAZ)
    c.fill = HDR
    tur = [("Marley", "B", "C", "vinil-asbest yer karosu; bağlı (kolay ufalanmayan) malzeme"),
           ("Kazan", "D", "E", "kazan dairesi ve tesisat ısı yalıtımı; ufalanabilir (gevrek) olabilir"),
           ("Eternit", "F", "G", "asbestli çimento levha ve boru; bağlı malzeme, kırılınca toz çıkarır")]
    satir_2018 = ilk + 1
    satir_21 = ilk + 4
    satir_24 = ilk + 7
    for j, (ad, cb, ck, ack) in enumerate(tur, r + 2):
        aralik_b = f"{cb}{satir_2018},{cb}{satir_21}:{cb}{satir_24}"
        aralik_k = f"{ck}{satir_2018},{ck}{satir_21}:{ck}{satir_24}"
        yaz(ws, j, 1, ad)
        yaz(ws, j, 2, f"=SUM({aralik_b})", fmt="#,##0")
        yaz(ws, j, 3, f"=SUM({aralik_k})", fmt="#,##0")
        yaz(ws, j, 4, f"=C{j}/B{j}", fmt="#,##0")
        yaz(ws, j, 5, f"=C{j}/SUM($C${r+2}:$C${r+4})", fmt="0.0%")
        yaz(ws, j, 6, f"={ck}{ilk}/J{ilk}", fmt="0.0%")
        yaz(ws, j, 7, f"=SUM({ck}{satir_21}:{ck}{satir_24})/SUM(J{satir_21}:J{satir_24})", fmt="0.0%")
        yaz(ws, j, 14, ack, GRI, wrap=True)
    j = r + 5
    yaz(ws, j, 1, "Diğer")
    yaz(ws, j, 6, f"=H{ilk}/J{ilk}", fmt="0.0%")
    yaz(ws, j + 2, 1, "Her binanın tek bir türe yazıldığı görülüyor (2018: 24+61+18 = 103 bina, açık veriyle aynı). Bir binada birden çok tür varsa belge bunu göstermiyor.", GRI)
    yaz(ws, j + 3, 1, "2015-2017 için yalnız kütle var, bina sayısı türe göre verilmemiş. Fark sütunundaki küçük değerler yuvarlamadan (ör. 2018: 52.825 kg ve 52,8 ton).", GRI)
    ws.freeze_panes = "B5"

    # ---- Tutarlılık ve bağlam
    ws = wb.create_sheet("Tutarlılık ve bağlam")
    yaz(ws, 1, 1, "A) Belgelerdeki toplamlar yıllık seriyle tutuyor mu?", BASLIK)
    baslik_satiri(ws, 2, ["Belgedeki ifade", "Belgedeki değer", "Yıllık seriden aynı dönem", "Fark", "Değere denk gelen toplam",
                          "Değerlendirme", "Kaynak", "Alıntı (belgedeki yazımla)"],
                  [34, 12, 14, 11, 14, 46, 34, 60])
    Y = "'Yıllık seri'!"
    kontroller = [
        ("Çevre birimi sayfası: 'bugüne kadar' denetlenen saha (2015-2025)", 3379, f"=SUM({Y}B4:B14)", None,
         "Tutmuyor; 3.379 hiçbir yılın kümülatif toplamına denk gelmiyor (Yıllık seri, G sütunu).", "cevre", None, "bugüne kadar 3.379 inşaat sahası denetlenmiş"),
        ("Çevre birimi sayfası: 'bugüne kadar' bertaraf (ton, 2015-2025)", 923.76, f"=SUM({Y}D4:D14)", None,
         "Tutmuyor; 923,76 ton hiçbir yılın kümülatif toplamına denk gelmiyor (Yıllık seri, H sütunu).", "cevre", None, "toplam 923,76 ton asbest atığı"),
        ("2021 FR: '2015-2021 Yılları Arası Toplam' denetlenen saha", 2263, f"=SUM({Y}B4:B10)", f"=SUM({Y}B4:B8)",
         "Tutmuyor; 2.263 aslında 2015-2019 toplamı.", "fr2021", 257, "Arası Toplam"),
        ("2021 FR: '2015-2021 Yılları Arası Toplam' tespit edilen bina", 686, f"=SUM({Y}C4:C10)", f"=SUM({Y}C4:C8)",
         "Tutmuyor; 686 aslında 2015-2019 toplamı.", "fr2021", 257, "Arası Toplam"),
        ("2021 FR: '2015-2021 Yılları Arası Toplam' bertaraf (ton)", 838.1, f"=SUM({Y}D4:D10)", f"=SUM({Y}D4:D9)",
         "Tutmuyor; 838,1 ton aslında 2015-2020 toplamı.", "fr2021", 257, "838,1 ton"),
        ("2018 FR: 2015-2018 TOPLAM denetlenen saha", 2119, f"=SUM({Y}B4:B7)", None, "Tutuyor.", "fr2018", 166, "2.119"),
        ("2018 FR: 2015-2018 TOPLAM tespit edilen bina", 665, f"=SUM({Y}C4:C7)", None, "Tutuyor.", "fr2018", 166, "665"),
        ("2018 FR: 2015-2018 TOPLAM bertaraf (ton)", 796.8, f"=SUM({Y}D4:D7)", None, "Tutuyor.", "fr2018", 166, "796,8"),
        ("2017 haberi: 2015-2017 toplam denetlenen saha", 1835, f"=SUM({Y}B4:B6)", None, "Tutuyor.", "haber_doga", None, "bugüne kadar 1835 insaat sahasi denetlendi"),
        ("2017 haberi: 2015-2017 toplam bertaraf (ton)", 744, f"=SUM({Y}D4:D6)", None, "Tutuyor.", "haber_doga", None, "toplam 744 ton asbest atigi"),
    ]
    for i, (ifade, deger, hesap, denk, deg, k, s, al) in enumerate(kontroller, 3):
        dogrula(k, s, al)
        fmt = "#,##0.00" if isinstance(deger, float) else "#,##0"
        yaz(ws, i, 1, ifade, wrap=True)
        yaz(ws, i, 2, deger, MAVI, fmt)
        yaz(ws, i, 3, hesap, fmt=fmt)
        yaz(ws, i, 4, f"=B{i}-C{i}", fmt=fmt)
        if denk:
            yaz(ws, i, 5, denk, fmt=fmt)
        yaz(ws, i, 6, deg, wrap=True)
        yaz(ws, i, 7, kaynak_adi(k, s), GRI, wrap=True)
        yaz(ws, i, 8, al, wrap=True)
    r = 3 + len(kontroller) + 2
    yaz(ws, r, 1, "B) Bağlam ve belirsizlikler", BASLIK)
    baslik_satiri(ws, r + 1, ["Konu", "", "", "", "", "Ne söylüyor / neden önemli", "Kaynak", "Alıntı (belgedeki yazımla)"])
    baglam = [
        ("Uygulamanın başlangıcı (1)", "Ücret tarifesine göre yıkım öncesi tehlikeli madde zorunluluğu 8 Ocak 2014 tarihli, 2014/6 sayılı meclis kararıyla başladı.",
         "tarife", 3, "denetim yetkisi 08/01/2014 tarih ve 2014/6 sayılı Kadıköy Belediyesi Meclis Kararı ile uygulanmaya başlanmıştır"),
        ("Uygulamanın başlangıcı (2)", "Belediye haberi meclis kararının tarihini 21 Ağustos 2015 olarak veriyor. İki tarih çelişiyor; meclis kararı belediyeden istenmeli.",
         "haber_yikim", None, "21 Agustos 2015 tarihinde Meclis karari ile uygulanmaya baslanan"),
        ("Uygulamanın başlangıcı (3)", "Faaliyet raporları ve çevre birimi sayfası çalışmanın 2015'te başladığını söylüyor; açık veri de 2015'ten başlıyor.",
         "cevre", None, "2015 yılında başlatılan çalışma kapsamında"),
        ("Bina bazında envanter var", "Her yıkımda asbest envanter raporu, atık yönetim planı ve risk analizi isteniyor. Mahalle ve malzeme dağılımı bu raporlardan bilgi edinme yoluyla istenebilir.",
         "tarife", 4, "Asbest Envanter Raporu, Atık Yönetim Planı, Risk Analiz Raporu"),
        ("Temiz rapor sonrası yıkım ruhsatı", "Haber, uygulama başladığından beri 113 eski binaya asbest raporu temiz çıktıktan sonra yıkım ruhsatı verildiğini söylüyor. Haberin tarihi sayfada yok.",
         "haber_yikim", None, "toplamda 113 eski bina için Asbest Raporu temiz çiktiktan sona yikim ruhsati verildi"),
        ("Bina mı, inşaat sahası mı?", "Açık veri 'asbest tespit edilen bina' diyor, raporlar aynı sayıyı 'inşaat sahası' olarak veriyor. Tür dağılımında ise 'bina' kullanılıyor.",
         "fr2021", 257, "27 inşaat sahasında asbestli malzeme tespit edilmiş"),
    ]
    for i, (konu, ack, k, s, al) in enumerate(baglam, r + 2):
        dogrula(k, s, al)
        yaz(ws, i, 1, konu, wrap=True)
        c = yaz(ws, i, 6, ack, wrap=True)
        yaz(ws, i, 7, kaynak_adi(k, s), GRI, wrap=True)
        yaz(ws, i, 8, al, wrap=True)
    ws.freeze_panes = "A3"

    # ---- Açık veri (özgün)
    ws = wb.create_sheet("Açık veri (özgün)")
    yaz(ws, 1, 1, "Kadıköy Açık Veri, 'Asbest Verileri' (CSV), olduğu gibi", BASLIK)
    sayi = lambda s: float(s.replace(",", ".")) if "," in s else int(s)
    for i, satir in enumerate(satirlar, 3):
        for j, v in enumerate(satir, 1):
            if i == 3 or j == 1:
                yaz(ws, i, j, int(v) if v.isdigit() else v, KALIN if i == 3 else SIYAH)
            else:
                yaz(ws, i, j, sayi(v), MAVI)
    ws.column_dimensions["A"].width = 44
    yaz(ws, 8, 1, BELGE["acikveri"][1], GRI)
    yaz(ws, 9, 1, "Veri seti sayfası: https://acikveri.kadikoy.bel.tr/dataset/asbest-verileri (İklim Değişikliği ve Sıfır Atık Müdürlüğü; lisans CC BY-NC 3.0)", GRI)

    # ---- Kaynaklar
    ws = wb.create_sheet("Kaynaklar")
    baslik_satiri(ws, 1, ["Belge", "Kullanılan sayfa", "Bağlantı", "Erişim (UTC)", "SHA-256", "Not"], [44, 14, 70, 22, 24, 50])
    kullanilan = {"acikveri": "tümü", "fr2018": "166", "fr2021": "257", "fr2022": "288", "fr2023": "222", "fr2024": "200",
                  "cevre": "tümü", "haber_doga": "tümü", "haber_1yil": "tümü", "haber_yikim": "tümü", "tarife": "3, 4"}
    notlar = {"acikveri": "Veri seti güncellemesi 6 Nisan 2026; lisans CC BY-NC 3.0 (atıf zorunlu, ticari olmayan kullanım). 14 Ekim 2026'da yeniden indirildi, dosya aynı.",
              "fr2018": "Aynı dosya https://kadikoyapi.kadikoy.bel.tr/f1b6b05e66ab4a33bb627b34892e1223.pdf adresinde de var.",
              "fr2021": "Basılı sayfa 256.", "fr2022": "Basılı sayfa 286.", "fr2023": "Basılı sayfa 221.", "fr2024": "Basılı sayfa 199.",
              "haber_doga": "2015-2017 verisi; yazım Türkçe karaktersiz.", "haber_1yil": "2017 verisi; yazım Türkçe karaktersiz.",
              "haber_yikim": "Tarih sayfada yok; yazım Türkçe karaktersiz.", "tarife": "PDF oluşturma tarihi 26 Temmuz 2018."}
    for i, (k, (dosya, url, ad)) in enumerate(BELGE.items(), 2):
        yol = RAW / dosya
        meta = yol.with_suffix(".meta.json")
        erisim = json.load(open(meta))["erisim"] if meta.exists() else "2026-10-13"
        sha = hashlib.sha256(yol.read_bytes()).hexdigest()
        yaz(ws, i, 1, ad, wrap=True)
        yaz(ws, i, 2, kullanilan[k])
        c = yaz(ws, i, 3, url, wrap=True)
        c.hyperlink = url
        c.font = Font(name=F, size=10, color="0563C1", underline="single")
        yaz(ws, i, 4, erisim)
        yaz(ws, i, 5, sha, GRI)
        yaz(ws, i, 6, notlar.get(k, ""), GRI, wrap=True)
    wb.save(CIKTI)
    print(CIKTI)


if __name__ == "__main__":
    main()
