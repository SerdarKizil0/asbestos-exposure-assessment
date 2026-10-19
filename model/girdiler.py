"""Kadıköy mahalle girdi tablosunu kurar → model/girdi/mahalle_girdileri.csv

Kaynaklar (hepsi veri/ham altında, erişim zamanı ve SHA-256 ile):
- İBB Açık Veri, Deprem Senaryosu Analiz Sonuçları (Mw 7,5; mahalle bazında hasarlı bina, can kaybı, geçici barınma)
- Kadıköy Açık Veri: mahalle sınırları, 2025 nüfus, 2024 65+ nüfus, 2021 yapım yılı / kat / inşaat türü,
  afet toplanma alanları, 2022 konut-işyeri, riskli yapı 2012-2022, Asbest Verileri 2015-2025
"""
from __future__ import annotations

import math

from ortak import GIRDI, RAW, anahtar, oku_csv, sayi, yaz_csv

M = RAW / "kadikoy" / "model"


def tablo(yol, ad_sutunu, alanlar, ayrac=None):
    out = {}
    for r in oku_csv(yol, ayrac):
        k = anahtar(r[ad_sutunu])
        if k in ("toplam", "genel toplam", ""):
            continue
        out[k] = {yeni: sayi(r[eski]) for yeni, eski in alanlar.items()}
    return out


def kur() -> list[dict]:
    geo = {anahtar(r["mahalle"]): r for r in oku_csv(GIRDI / "mahalle_geometri.csv")}
    ibb = {}
    for r in oku_csv(RAW / "ibb" / "deprem_senaryosu_analiz_sonuclari.csv"):
        if anahtar(r["ilce_adi"]) == "kadikoy":
            ibb[anahtar(r["mahalle_adi"])] = {
                "hasar_cok_agir": sayi(r["cok_agir_hasarli_bina_sayisi"]),
                "hasar_agir": sayi(r["agir_hasarli_bina_sayisi"]),
                "hasar_orta": sayi(r["orta_hasarli_bina_sayisi"]),
                "hasar_hafif": sayi(r["hafif_hasarli_bina_sayisi"]),
                "can_kaybi": sayi(r["can_kaybi_sayisi"]),
                "gecici_barinma": sayi(r["gecici_barinma"]),
                "uavt": r["mahalle_koy_uavt"],
            }
    nuf = tablo(M / "mahalle-nufuslarinin-cinsiyete-gore-dagilimi.csv", "Mahalle", {"nufus_2025": "Toplam"})
    yasli = tablo(M / "65-uzeri-nufusun-mahalle-dagilimlari.csv", "Mahalle", {"nufus_65_ustu_2024": "Toplam_65_Yas_ve_Uzeri"})
    yapim = tablo(M / "yapim-yillarina-gore-binalarin-mekansal-dagilimi.csv", "Mahalleler",
                  {"bina_1980_oncesi": "1980_Oncesi", "bina_1980_2000": "1980-2000_Arasi",
                   "bina_2000_sonrasi": "2000_Sonrasi", "bina_toplam_2021": "Toplam"})
    kat = tablo(M / "kat-sayisina-gore-binalarin-mekansal-dagilimi.csv", "Mahalle",
                {"kat_1_3": "1-3_Kat", "kat_4_6": "4-6_Kat", "kat_7_9": "7-9_Kat", "kat_10_14": "10-14_Kat",
                 "kat_15_ustu": "15_Ve_Uzeri"})
    tur = tablo(M / "insaat-turlerine-gore-binalarin-mekansal-dagilimi.csv", "Mahalle",
                {"yapi_betonarme": "Betonarme", "yapi_yigma": "Yigma", "yapi_tunel_kalip": "Tunel_Kalip",
                 "yapi_ahsap": "Ahsap"})
    top = {}
    for r in oku_csv(M / "mahalle-afet-toplanma-alanlari-miktari.csv"):
        k = anahtar(r["Mahalle"])
        if k in ("genel toplam", "toplam"):
            continue
        alan_sutun = [c for c in r if c.strip().startswith("Toplanma_Alani")][0]
        top[k] = {"toplanma_alani_m2": sayi(r[alan_sutun]), "toplanma_alani_adet": sayi(r["Adet"])}
    konut = {}
    for r in oku_csv(M / "mahalle-bazinda-konut-isyeri-dagilimi.csv"):
        k = anahtar(r["Mahalle"])
        if k == "toplam":
            continue
        cols = {c.strip(): c for c in r}
        konut[k] = {"mesken": sayi(r[cols["Mesken"]]), "isyeri": sayi(r[cols["İsyeri"]])}
    riskli = {}
    for r in oku_csv(RAW / "kadikoy" / "riskli_yapi_mahalle_2012_2022.csv"):
        k = anahtar(r["Mahalle"])
        if k == "toplam":
            continue
        riskli[k] = {"riskli_yapi_2012_2022": sayi(r["Toplam_Riskli_Yapi"]), "yapi_riskli_tablosu": sayi(r["Toplam_Yapi"])}

    satirlar = []
    for k, g in sorted(geo.items()):
        d = {"mahalle": g["mahalle"], "anahtar": k, "alan_km2": sayi(g["alan_km2"]),
             "x_tm30": sayi(g["x_tm30"]), "y_tm30": sayi(g["y_tm30"]), "enlem": sayi(g["enlem"]), "boylam": sayi(g["boylam"])}
        for kaynak, ad in ((ibb, "İBB senaryo"), (nuf, "nüfus"), (yasli, "65+"), (yapim, "yapım yılı"), (kat, "kat"),
                           (tur, "inşaat türü"), (top, "toplanma"), (konut, "konut"), (riskli, "riskli yapı")):
            if k not in kaynak:
                raise SystemExit(f"{ad} tablosunda eksik mahalle: {k}")
            d.update(kaynak[k])
        d["yikilacak_temel"] = d["hasar_cok_agir"] + d["hasar_agir"]
        d["pay_1980_oncesi"] = d["bina_1980_oncesi"] / d["bina_toplam_2021"]
        d["pay_2000_oncesi"] = (d["bina_1980_oncesi"] + d["bina_1980_2000"]) / d["bina_toplam_2021"]
        d["nufus_yogunlugu_km2"] = d["nufus_2025"] / d["alan_km2"]
        d["pay_65_ustu"] = d["nufus_65_ustu_2024"] / d["nufus_2025"]
        satirlar.append(d)
    return satirlar


def kadikoy_asbest() -> dict:
    """Kadıköy açık veri asbest serisi: yıllar, denetim, tespit, ton."""
    rows = oku_csv(RAW / "kadikoy" / "asbest_verileri.csv")
    yillar = [c for c in rows[0] if c.strip().isdigit()]
    seri = {}
    for r in rows:
        ad = r[list(r.keys())[0]]
        seri[ad] = [sayi(r[y]) for y in yillar]
    den = seri["Denetlenen İnşaat Sahası Sayısı"]
    tes = seri["Asbest Tespit Edilen Bina Sayısı"]
    ton = seri["Bertaraf Edilen Asbest Atığı Miktarı (ton)"]
    oran = [t / d for t, d in zip(tes, den)]
    kg_bina = [1000 * a / b for a, b in zip(ton, tes)]
    return {"yillar": [int(y) for y in yillar], "denetim": den, "tespit": tes, "ton": ton,
            "oran": oran, "kg_bina": kg_bina,
            "oran_havuz": sum(tes) / sum(den), "kg_bina_havuz": 1000 * sum(ton) / sum(tes),
            "oran_min": min(oran), "oran_max": max(oran), "kg_bina_min": min(kg_bina), "kg_bina_max": max(kg_bina)}


if __name__ == "__main__":
    s = kur()
    yaz_csv(GIRDI / "mahalle_girdileri.csv", s)
    a = kadikoy_asbest()
    print(len(s), "mahalle; yıkılacak (çok ağır+ağır):", sum(d["yikilacak_temel"] for d in s),
          "orta:", sum(d["hasar_orta"] for d in s), "nüfus:", sum(d["nufus_2025"] for d in s),
          "alan:", round(sum(d["alan_km2"] for d in s), 2))
    print("Kadıköy asbest: havuz oran %.3f, kg/bina %.0f; oran aralığı %.3f-%.3f; kg/bina %.0f-%.0f" % (
        a["oran_havuz"], a["kg_bina_havuz"], a["oran_min"], a["oran_max"], a["kg_bina_min"], a["kg_bina_max"]))
    for d in sorted(s, key=lambda d: -d["yikilacak_temel"] / d["alan_km2"]):
        print(f"{d['mahalle']:<14} yık {d['yikilacak_temel']:>4.0f} ({d['yikilacak_temel']/d['alan_km2']:6.1f}/km²) orta {d['hasar_orta']:>4.0f}"
              f"  nüfus {d['nufus_2025']:>6.0f}  1980< %{100*d['pay_1980_oncesi']:4.1f}  2000< %{100*d['pay_2000_oncesi']:4.1f}"
              f"  geçici barınma {d['gecici_barinma']:>5.0f}  65+ %{100*d['pay_65_ustu']:4.1f}")
