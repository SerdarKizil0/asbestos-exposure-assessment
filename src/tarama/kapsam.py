"""39 ilçe için kapsam tablosu: neye bakıldı, ne bulundu, ne kaldı → veri/dogrulanmis/kapsam_39.csv"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict

import re

from common import DOGRULANMIS, OUT, fold, read_seeds, write_csv

YEAR = re.compile(r"(20[0-2]\d)")


def load(name: str) -> list[dict]:
    p = (DOGRULANMIS if name == "veri_noktalari.csv" else OUT) / name
    return list(csv.DictReader(open(p, encoding="utf-8-sig"))) if p.exists() else []


NEDEN = {
    "Arnavutköy": "bağlantı sıfırlanıyor (yurtdışı IP engeli olası)",
    "Başakşehir": "TLS sertifika zinciri doğrulanamıyor",
    "Bayrampaşa": "403 bot koruması",
    "Çekmeköy": "TLS sertifika zinciri doğrulanamıyor",
    "Esenler": "403 bot koruması",
    "Esenyurt": "TLS sertifika zinciri doğrulanamıyor",
    "Gaziosmanpaşa": "403 (WAF)",
    "Kartal": "TLS sertifika zinciri doğrulanamıyor",
    "Pendik": "bağlantı sıfırlanıyor (yurtdışı IP engeli olası)",
    "Sancaktepe": "zaman aşımı (yurtdışı IP engeli olası)",
    "Sultanbeyli": "TLS hatası / zaman aşımı",
    "Şişli": "zaman aşımı (yurtdışı IP engeli olası)",
    "Zeytinburnu": "bağlantı sıfırlanıyor (yurtdışı IP engeli olası)",
}

# Arama motoru dizininde görülen asbest içerikleri ve Türkiye IP'li tarayıcıdaki doğrulama sonucu
DIZINDE = {
    "Kartal": "2 asbest haberi ve İDSAMB sayfası → tarayıcıda doğrulandı (haber 19267: 2018-2020 serisi)",
    "Şişli": "2022 ve 2023 faaliyet raporları → doğrulandı; dizinde 2010-2023 arası 9 rapor daha bulundu",
    "Zeytinburnu": "Abdi İpekçi Spor Salonu asbest duyurusu → doğrulandı (asbest bulunmadı denmiş; ekli rapor 404)",
    "Arnavutköy": "Yıkım ruhsatı sayfası → doğrulandı: başvuruda 'Asbest Raporu' isteniyor",
    "Çekmeköy": "Yapı Kontrol Müdürlüğü hizmetleri sayfası → güncel sayfada asbest geçmiyor",
    "Başakşehir": "2017 ve 2018 faaliyet raporları, Fen İşleri sayfası → metinde asbest bulunamadı",
    "Gaziosmanpaşa": "2019 faaliyet raporu → metinde (boşluksuz aramayla da) asbest bulunamadı",
    "Beşiktaş": "cevre.besiktas.bel.tr 'Tehlikeli Atıklar (Asbestle Mücadele)' sayfası → alt alan adı tarayıcıdan da açılmadı",
}

# Buluttan açılamayan 13 site + rapor sayfası bulunamayan 5 ilçe: kullanıcının bilgisayarındaki tarayıcıda
# (Türkiye IP'si) bakıldı, PDF'ler pdf.js ile okundu (13 Ekim 2026). Ayrıntı: ciktilar/tarama/turkiye_tarayici_notlar.md
TARAYICI = {
    "Kartal": {"yillar": "2017–2025", "arama": "arama formu yok"},
    "Şişli": {"yillar": "2010, 2011, 2013, 2014, 2015, 2018, 2020, 2022, 2023", "arama": "arama formu yok",
              "not": "Sitede faaliyet raporu sayfası yok; raporlar bağlantısız duruyor, adresler arama motorundan bulundu. 2016, 2017, 2019, 2021, 2024, 2025 raporları bulunamadı."},
    "Zeytinburnu": {"yillar": "2015–2025", "arama": "asbest: 1 sonuç (Abdi İpekçi duyurusu, 2018)",
                    "ocr": "2015 raporu taranmış (184 s.)", "asbest": True},
    "Başakşehir": {"yillar": "2015–2025", "arama": "denenmedi (token'lı form)"},
    "Gaziosmanpaşa": {"yillar": "2015–2025", "arama": "asbest: 0 (kontrol 'deprem': 14)"},
    "Arnavutköy": {"yillar": "2015–2025", "arama": "JavaScript; denenmedi",
                   "ocr": "2015, 2017, 2018 raporları taranmış; diğerlerinde sayfaların %8-27'si görüntü", "asbest": True},
    "Esenyurt": {"yillar": "2023–2025 (sitede yalnız bunlar var)", "arama": "asbest: 0 (kontrol 'deprem': 20)"},
    "Pendik": {"yillar": "2015–2025", "arama": "POST formu; gönderilmedi"},
    "Çekmeköy": {"yillar": "2015–2025", "arama": "asbest: 0 (kontrol 'deprem': 6)",
                 "ocr": "2015-2020 raporlarında sayfaların %19-33'ü görüntü"},
    "Sancaktepe": {"yillar": "", "arama": "asbest: 0 (kontrol 'deprem' sonuç veriyor)",
                   "not": "Sitede ve arama motorunda faaliyet raporu yok (yalnız Sayıştay denetim raporları)."},
    "Sultanbeyli": {"yillar": "2015–2025", "arama": "asbest: bulunamadı", "ocr": "2016 raporunun %63'ü görüntü"},
    "Esenler": {"yillar": "2015–2025", "arama": "asbest: 0 (kontrol 'deprem' sonuç veriyor)"},
    "Bayrampaşa": {"yillar": "2015–2025", "arama": "asbest: eşleşme yok (kontrol 'deprem' sonuç veriyor)",
                   "ocr": "2024 raporu tamamen taranmış (276 s.); 2021 raporunun yarısı görüntü"},
    "Beykoz": {"yillar": "", "arama": "asbest: sonuç yok (tek arama; robots.txt /arama'yı botlara kapatıyor)", "robots": True,
               "not": "Faaliyet raporları 2011–2025 sitede var ama /api/media yolundan sunuluyor; robots.txt /api/'yi botlara kapatıyor, bot indirmedi. Muhabir elle açmalı."},
    "Güngören": {"yillar": "", "arama": "arama kutusu yok",
                 "not": "Faaliyet raporu sayfası var (2019–2025) ama indirme bağlantıları JavaScript/GraphQL ile geliyor; PDF adresleri alınamadı."},
}

NOTLAR = {
    "Kadıköy": "En şeffaf kaynak: açık veri portalında 2015-2025 yıllık 'Asbest Verileri' (CSV/XLSX) ve mahalle bazlı riskli yapı verisi. Uygulama 08.01.2014 tarihli 2014/6 sayılı meclis kararıyla başlamış.",
    "Maltepe": "Faaliyet raporlarında 2016-2025 yıllık seri; 2016 ve 2019 raporlarında mahalle bazlı asbest denetim tablosu. 2017 denetim sayısı raporlar arasında 651/641.",
    "Bağcılar": "2017-2025 her yıl kontrol ve tespit sayısı; 2022'den itibaren kg. Ücret tarifesinde asbest durum tespiti bedeli var.",
    "Ataşehir": "2017-2025 seri (2022 raporunda sayı yok); 2020'den itibaren tespit sayısı verilmiyor. Eski sitedeki sunumda İçerenköy ve Küçükbakkalköy numune çalışmaları.",
    "Kağıthane": "2019-2025 envanter raporu sayısı ve ton; 2020-2021 tonajı raporlar arasında çelişkili (34/50 t ile 11/11 t).",
    "Avcılar": "2020-2025 'asbest yönetimi yapılan bina' sayısı; tespit sayısı verilmiyor; tonaj yalnız 2020-2022.",
    "Büyükçekmece": "2022-2023 denetim/tespit/kg tablosu; 2024-2025 yalnız incelenen yapı sayısı.",
    "Bahçelievler": "Kentsel Dönüşüm Md. iş tablosunda 'Asbest Belge' sayısı (2024: 436, 2025: 1.255); tespit verisi yok.",
    "Eyüpsultan": "2025 raporunda 143 asbest dosyası değerlendirmesi; 2025 tarihli haberde süreç anlatımı.",
    "Üsküdar": "2022-2025 raporlarında yalnız süreç anlatımı. 2016, 2019, 2020, 2021 raporları taranmış görüntü; 2021 dosyasının adı 'Kopyalanamaz'.",
    "Sarıyer": "2025 raporunda asbest envanter raporu denetimi anlatılıyor, sayı yok.",
    "Bakırköy": "2026 ücret tarifesinde 'Asbest Dosya İnceleme' kalemi; raporlarda sayı yok.",
    "Fatih": "2015 raporunda kamu binalarında eternit çatı yenileme işleri (asbestli olabilir); asbest denetim verisi yok.",
    "Ümraniye": "Faaliyet raporu bölümleri taranmış görüntü (13 PDF); OCR gerekli.",
    "Şile": "3 faaliyet raporu taranmış görüntü; OCR gerekli.",
    "Tuzla": "2023 raporu taranmış görüntü; açık veri portalında hafriyat ve riskli yapı verisi var, asbest yok.",
    "Sultangazi": "2015 raporu taranmış; 2022 ve 2025 raporları indirilemedi (bağlantı kesildi).",
    "Kartal": "Faaliyet raporlarında 2020-2025 yıllık seri (denetim, tespit, kg); 2018-2020 belediye haberinde. 2019 raporunda asbest yok. 2024 raporunda '2023 yılında yıkılan 453 yapı' yazıyor (muhtemel kopyala-yapıştır hatası).",
    "Şişli": "Denetim Mayıs 2016'da başlamış; 2018 raporunda o güne kadar 461 yapının 70'inde asbest, 50 tonu aşan bertaraf. 2018, 2020, 2022, 2023 yıllık tablo. ASUD 2021 haritasında 'az riskli' 7 ilçeden biri.",
    "Bayrampaşa": "14.02.2025'ten beri yıkım ruhsatında asbest araştırma raporu şartı; 2025'te 277 adres, 49 bina, 40,5 ton ve aylık dağılım. Önceki raporlarda asbest yok.",
    "Arnavutköy": "Yıkım ruhsatı başvurusunda 'Asbest Raporu' isteniyor (sayfa 27.01.2021'de güncellenmiş); faaliyet raporlarında sayı yok.",
    "Zeytinburnu": "2018 Abdi İpekçi duyurusu (36 numune, asbest yok); 2018 raporunda 'riskli alanlarda yıkım işlerinde asbest ölçümü' ihale kalemi. Sayısal denetim verisi yok.",
    "Esenyurt": "Yeni sitede yalnız 2023-2025 raporları ve kısa haber arşivi var; eski site için Wayback gerekli.",
    "Beşiktaş": "Faaliyet raporları r2web.besiktasplus.app adresinde (JavaScript ile listeleniyor). 2020-2025 asbest denetim serisi; 2023'te 777 bina ve 302 ton (deprem sonrası sıçrama, teyit edilmeli); tespit sayısı yalnız 2021'de. Asbest denetim ücreti tahsil ediliyor. ASUD 2021 haritasında 'az riskli' 7 ilçeden biri.",
    "Silivri": "2015–2024 metinli raporlarda asbest yok. 2025 raporu büyük ölçüde görüntü (345 sayfada ~28 bin karakter) → OCR öncelikli: 23 Nisan 2025 depremi Silivri açıklarındaydı.",
    "Çatalca": "Sitede yalnız 2021–2025 raporları var; 2022 ve 2023 raporları taranmış görüntü.",
}


def main() -> None:
    seeds = read_seeds()
    er = {r["ilce"]: r for r in load("erisim.csv")}
    sm = {r["ilce"]: r for r in load("sitemap_ozet.csv")}
    sa = {r["ilce"]: r for r in load("site_arama.csv")}
    av = defaultdict(list)
    for r in load("acikveri.csv"):
        av[r["ilce"]].append(r)
    fr = defaultdict(set)
    for r in load("faaliyet_raporlari.csv"):
        if r["url"]:
            fr[r["ilce"]].add(r["yil"])
    docs = defaultdict(list)
    for d in load("belgeler.csv"):
        docs[d["ilce"]].append(d)
    pts = defaultdict(list)
    for p in load("veri_noktalari.csv"):
        pts[p["ilce"]].append(p)

    rows = []
    for s in seeds:
        i = s["ilce"]
        e = er.get(i, {})
        ds = docs.get(i, [])
        ok = [d for d in ds if d["durum"] == "ok"]
        asb = [d for d in ok if int(d["asbest_gecisi"] or 0) > 0]
        ocr = [d for d in ok if d["ocr_gerekli"] == "evet"]
        p = pts.get(i, [])
        years = sorted({x["yil"] for x in p})
        mah = any(x["duzey"] == "mahalle" for x in p)
        portal = "; ".join(sorted({f"{x['portal']} ({x['veri_seti']})" for x in av.get(i, [])
                                   if x["veri_seti"] and "eşleşme yok" not in x["veri_seti"]})) or \
                 ("portal var, eşleşme yok" if av.get(i) else "")
        rap_yil = set()
        for d in ok:
            lab = fold(d["baslik"] + " " + d["url"])
            if "faaliyet" in lab:
                ys = YEAR.findall(d["baslik"]) or YEAR.findall(d["url"])
                if ys:
                    rap_yil.add(ys[0])
        tb = TARAYICI.get(i)
        bulut_yok = e.get("durum") != "erisildi"
        if p:
            sonuc = f"sayısal veri: {len(p)} nokta, yıllar {years[0]}–{years[-1]}" + (" (mahalle kırılımı var)" if mah else "")
        elif tb and tb.get("robots") and not ok:
            sonuc = "raporlar robots.txt ile botlara kapalı — muhabir elle açmalı"
        elif asb or (tb and tb.get("asbest")):
            sonuc = "asbest geçiyor, sayı yok (süreç anlatımı/ücret tarifesi/ruhsat koşulu)"
        elif tb and bulut_yok and tb.get("yillar"):
            sonuc = "tarayıcıda taranan raporlarda asbest yok" + ("; taranmış sayfalar OCR bekliyor" if tb.get("ocr") else "")
        elif tb and not tb.get("yillar") and not ok:
            sonuc = "faaliyet raporu yok ya da PDF adresi alınamadı (bkz. not)"
        elif bulut_yok:
            sonuc = "buradan erişilemedi"
        elif not ok:
            sonuc = "belge bulunamadı — elle bakılmalı"
        elif ocr:
            sonuc = f"metinli belgelerde asbest yok; {len(ocr)} taranmış PDF OCR bekliyor"
        else:
            sonuc = "taranan belgelerde asbest yok"
        kalan = []
        if bulut_yok:
            kalan.append("Türkiye'den harvest.py ile belgelerin kanıt kopyasını al" if tb else
                         "Türkiye IP'si ile tüm aşamaları yeniden çalıştır")
        if ocr:
            kalan.append(f"{len(ocr)} taranmış PDF için OCR")
        if tb and tb.get("ocr"):
            kalan.append("OCR: " + tb["ocr"])
        if not tb and sa.get(i, {}).get("durum") in ("arama_bulunamadi", "sonuc_yok_veya_js", "js_olabilir"):
            kalan.append("site içi aramayı tarayıcıyla teyit et")
        if not rap_yil and not (tb and tb.get("yillar")):
            kalan.append("faaliyet raporu için bilgi edinme başvurusu" if tb else "faaliyet raporu sayfasını elle bul")
        kalan.append("Wayback (yerelde)")
        erisim = e.get("durum", "") + (f" — {NEDEN[i]}" if i in NEDEN else "")
        if tb and bulut_yok:
            erisim += "; Türkiye IP'li tarayıcıdan erişildi"
        arama = sa.get(i, {}).get("durum", "")
        if tb:
            arama = (arama + " | " if arama else "") + "tarayıcı: " + tb["arama"]
        yillar = ", ".join(sorted(rap_yil))
        if tb and tb.get("yillar") and bulut_yok:
            yillar = tb["yillar"] + " (tarayıcı)"
        not_ = " ".join(x for x in (NOTLAR.get(i, ""), (tb or {}).get("not", "")) if x)
        rows.append({
            "ilce": i, "yaka": s["yaka"],
            "erisim": erisim,
            "site": e.get("kanonik_url", ""),
            "site_haritasi_url": sm.get(i, {}).get("url_sayisi", ""),
            "site_ici_arama": arama,
            "acik_veri": portal,
            "taranan_faaliyet_raporu_yillari": yillar,
            "indirilen_belge": len(ok), "asbest_gecen_belge": len(asb), "ocr_gereken": len(ocr),
            "sonuc": sonuc, "not": not_, "dizinde_gorulen": DIZINDE.get(i, ""), "sonraki_adim": "; ".join(kalan),
        })
    write_csv(DOGRULANMIS / "kapsam_39.csv", rows, list(rows[0].keys()))
    c = Counter(r["sonuc"].split(":")[0] for r in rows)
    print(c)


if __name__ == "__main__":
    main()
