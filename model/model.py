"""Kadıköy, Mw 7,5 senaryosu sonrası yıkım/enkaz kaldırma kaynaklı asbest lifi yayılımı — tarama modeli.

Zincir (her kaynak mahalle m için, yıkım dönemi boyunca):
  yıkılan bina      N_m = (çok ağır + ağır + f_orta × orta hasarlı) × hasar_çarpanı          [İBB/KOERİ 2019 senaryosu]
  asbestli bina     × p_m                                                                     [Kadıköy açık veri 2015-2025]
  asbestli malzeme  × M_acm (kg/asbestli bina)                                               [Kadıköy açık veri 2015-2025]
  asbest kütlesi    × w (malzemedeki asbest oranı)                                           [varsayım; asbestli çimento]
  havaya geçen pay  × EF × (1 - önceden söküm) × (1 - ıslatma verimi)                        [Terazono 2000 / EPA; uygulama]
  lif sayısı        × k_lif (lif/ng)                                                          [Terazono 2000]
  salım hızı        Q_m = toplam lif / (yıkım süresi içindeki çalışma saati × 3600)          [lif/s]
  derişim           C_r = Σ_m D[r,m] × Q_m   (D: yayilim.py aktarım matrisi, lif/m³ per lif/s)

Çıktılar model/cikti altında (JSON/CSV); rapor_xlsx.py bunları Excel'e taşır.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np

from girdiler import kadikoy_asbest, kur as mahalle_tablosu
from izgara import kur as izgara_kur
from meteoroloji import calisma_saati, frekans_tablosu, yukle as meteo_yukle
from ortak import CIKTI, GIRDI, oku_csv, yaz_csv
from yayilim import kisa_sure_aktarim, tek_yikim_profili, uzun_donem_aktarim

AS = kadikoy_asbest()
CALISMA_SAATI_AY = 10 * 26  # 08-18, pazartesi-cumartesi
CALISMA_PAYI = 31310 / 87672  # ERA5 2015-2024: çalışma saatlerinin tüm saatlere oranı

# Parametreler: (temel, alt, üst, birim, açıklama, kaynak, tür)  tür: yerel veri / literatür / varsayım / uygulama
P = {
    "hasar_carpani": (1.0, 0.5, 2.0, "kat", "İBB senaryosundaki hasarlı bina sayılarının çarpanı (deprem ve zemin belirsizliği)",
                      "İBB/KOERİ 2019 senaryosu tek bir gerçekleşme; aralık varsayım", "varsayım"),
    "f_orta": (0.0, 0.0, 1.0, "oran", "Orta hasarlı binalardan yıkılan pay",
               "Politika kararı; 2023 depremlerinden sonra orta hasarlıların bir kısmı da yıkıldı", "uygulama"),
    "p_asbest": (AS["oran_havuz"], AS["oran_min"], AS["oran_max"], "oran", "Yıkılan binada asbestli malzeme bulunma olasılığı",
                 "Kadıköy Açık Veri 'Asbest Verileri' 2015-2025: tespit/denetim (havuz; yıllık en düşük-en yüksek)", "yerel veri"),
    "M_acm": (AS["kg_bina_havuz"], AS["kg_bina_min"], AS["kg_bina_max"], "kg/bina", "Asbestli binadan çıkan asbestli malzeme",
              "Kadıköy Açık Veri 2015-2025: bertaraf ton / tespit bina (havuz; yıllık en düşük-en yüksek)", "yerel veri"),
    "w_asbest": (0.12, 0.05, 0.25, "oran", "Asbestli malzemedeki asbest kütle oranı",
                 "Varsayım: asbestli çimento ürünleri için yaygın %10-15; boru/kazan yalıtımında daha yüksek. Doğrulanmalı", "varsayım"),
    "EF": (1e-4, 1e-5, 1e-3, "kg/kg", "Asbest kütlesinin havaya lif olarak geçen payı (kontrolsüz yıkım/enkaz)",
           "Terazono ve ark. 2000 (EPA faktörü, %0,01); aralık varsayım", "literatür"),
    "k_lif": (30.0, 10.0, 100.0, "lif/ng", "Kütleden lif sayısına dönüşüm",
              "Terazono ve ark. 2000 (Şekil 3); aralık varsayım", "literatür"),
    "r_sokum": (0.0, 0.0, 0.8, "oran", "Yıkımdan önce sökülen asbest payı",
                "Varsayım: acil yıkımlarda sıfır (2023 deneyimi); olağan Kadıköy uygulamasında yüksek", "uygulama"),
    "eta_islatma": (0.0, 0.0, 0.9, "oran", "Islatma/su püskürtme ile tutulan pay",
                    "Varsayım; Kobe'de eşya arandığı için su püskürtülmeyen yıkım (Terazono 2000)", "uygulama"),
    "T_ay": (12.0, 6.0, 24.0, "ay", "Yıkım ve enkaz kaldırma süresi",
             "Varsayım; ortalama derişimi değiştirir, toplam maruziyeti değiştirmez", "varsayım"),
    "kobe_duzeltme": (1.0, 1.0, 5.0, "kat", "Model/ölçüm farkı düzeltmesi",
                      "Terazono 2000: Kobe'de hesap, ölçülen artışın yaklaşık beşte biri", "literatür"),
}


def deger(ad, ozel=None):
    return (ozel or {}).get(ad, P[ad][0])


def salim(kaynak_adlari, mah, kom, ozel=None, mekansal="tekdüze", hasar_dagilimi="İBB"):
    """Her kaynak mahalle için toplam lif sayısı ve salım hızı (lif/s)."""
    o = ozel or {}
    v = {k: o.get(k, P[k][0]) for k in P}
    ilce_p1980 = sum(d["bina_1980_oncesi"] for d in mah) / sum(d["bina_toplam_2021"] for d in mah)
    kad = {d["mahalle"]: d for d in mah}
    komd = {f"{k['ilce']}/{k['mahalle']}": k for k in kom if "hucre_sayisi" in k}
    if hasar_dagilimi == "riskli yapı":
        top_ibb = sum(d["hasar_cok_agir"] + d["hasar_agir"] for d in mah)
        top_orta = sum(d["hasar_orta"] for d in mah)
        top_r = sum(d["riskli_yapi_2012_2022"] for d in mah)
    lif_kg = v["k_lif"] * 1e12  # lif/ng → lif/kg
    saat = v["T_ay"] * CALISMA_SAATI_AY
    N, Q = [], []
    for ad in kaynak_adlari:
        if ad in kad:
            d = kad[ad]
            if hasar_dagilimi == "riskli yapı":
                pay = d["riskli_yapi_2012_2022"] / top_r
                yik = (top_ibb + v["f_orta"] * top_orta) * pay
            else:
                yik = d["hasar_cok_agir"] + d["hasar_agir"] + v["f_orta"] * d["hasar_orta"]
            p = v["p_asbest"] * (d["pay_1980_oncesi"] / ilce_p1980 if mekansal == "1980 öncesi payına göre" else 1.0)
        else:
            k = komd[ad]
            yik = (k["hasar_cok_agir"] + k["hasar_agir"] + v["f_orta"] * k["hasar_orta"]) * k["pay_icerde"]
            p = v["p_asbest"]
        yik *= v["hasar_carpani"]
        kg_asbest = yik * min(p, 1.0) * v["M_acm"] * v["w_asbest"]
        kg_hava = kg_asbest * v["EF"] * (1 - v["r_sokum"]) * (1 - v["eta_islatma"]) * v["kobe_duzeltme"]
        lif = kg_hava * lif_kg
        N.append(yik)
        Q.append(lif / (saat * 3600))
    return np.array(N), np.array(Q)


def derisim(D, Q, ozel=None):
    """Alıcı mahalle derişimleri (lif/L): çalışma saatleri ortalaması ve dönem (tüm saatler) ortalaması."""
    c_calisma = D @ Q / 1000.0
    return c_calisma, c_calisma * CALISMA_PAYI


def aktarimlar(yeniden=False):
    """Aktarım matrislerini hesaplar ya da önbellekten okur."""
    iz, kad_adlari, kom, kom_adlari, atlanan = izgara_kur()
    kaynak_adlari = kad_adlari + kom_adlari
    m = meteo_yukle()
    cal = np.array([calisma_saati(t) for t in m["zaman"]])
    kis = cal & np.array([t.month in (12, 1, 2) for t in m["zaman"]])
    yaz = cal & np.array([t.month in (6, 7, 8) for t in m["zaman"]])
    tanim = {
        "temel": dict(frek=frekans_tablosu(m, cal)),
        "kis": dict(frek=frekans_tablosu(m, kis)),
        "yaz": dict(frek=frekans_tablosu(m, yaz)),
        "kentsel_kararlilik": dict(frek=frekans_tablosu(m, cal), kentsel_kararlilik=True),
        "h2": dict(frek=frekans_tablosu(m, cal), h=2.0),
        "h15": dict(frek=frekans_tablosu(m, cal), h=15.0),
    }
    sakin = [{"sektor": s, "hiz_ms": 1.0, "kararlilik": "D", "karisim_m": 275.0, "frekans": 1 / 36} for s in range(36)]
    D = {}
    for ad, t in tanim.items():
        f = CIKTI / f"D_{ad}.npy"
        if f.exists() and not yeniden:
            D[ad] = np.load(f)
            continue
        t0 = time.time()
        kw = {k: v for k, v in t.items() if k != "frek"}
        D[ad] = uzun_donem_aktarim(iz, t["frek"], kad_adlari, kaynak_adlari, **kw)
        np.save(f, D[ad])
        print(f"  aktarım {ad}: {time.time() - t0:.0f} sn")
    senaryolar = {
        "S1_poyraz": dict(gelen_yon=45.0, u=5.5, grup="D", L=950.0,
                          ad="Poyraz: kuzeydoğudan 5,5 m/s, nötr (D), karışım yüksekliği 950 m"),
        "S2_lodos": dict(gelen_yon=225.0, u=3.9, grup="C", L=485.0,
                         ad="Lodos: güneybatıdan 3,9 m/s, hafif kararsız (C), karışım yüksekliği 485 m"),
        "S3_kararli_sabah": dict(gelen_yon=180.0, u=1.5, grup="EF", L=125.0,
                                 ad="Kararlı sabah: güneyden 1,5 m/s, kararlı (E-F), karışım yüksekliği 125 m"),
    }
    for ad, s in senaryolar.items():
        f = CIKTI / f"D_{ad}.npy"
        if f.exists() and not yeniden:
            D[ad] = np.load(f)
            continue
        t0 = time.time()
        D[ad] = kisa_sure_aktarim(iz, kad_adlari, kaynak_adlari, s["gelen_yon"], s["u"], s["grup"], s["L"])
        np.save(f, D[ad])
        print(f"  aktarım {ad}: {time.time() - t0:.0f} sn")
    f = CIKTI / "D_S4_durgun.npy"
    if f.exists() and not yeniden:
        D["S4_durgun"] = np.load(f)
    else:
        D["S4_durgun"] = uzun_donem_aktarim(iz, sakin, kad_adlari, kaynak_adlari)
        np.save(f, D["S4_durgun"])
    senaryolar["S4_durgun"] = dict(ad="Durgun: 1 m/s, yön değişken (her yön eşit), nötr (D), karışım yüksekliği 275 m")
    return D, kad_adlari, kaynak_adlari, kom, senaryolar, iz


if __name__ == "__main__":
    t0 = time.time()
    D, kad_adlari, kaynak_adlari, kom, senaryolar, iz = aktarimlar()
    mah = mahalle_tablosu()
    N, Q = salim(kaynak_adlari, mah, kom)
    cc, cd = derisim(D["temel"], Q)
    print(f"toplam yıkılan (Kadıköy): {N[:len(kad_adlari)].sum():.0f}; komşu: {N[len(kad_adlari):].sum():.0f}")
    print(f"toplam lif (Kadıköy kaynakları): {Q[:len(kad_adlari)].sum() * deger('T_ay') * CALISMA_SAATI_AY * 3600:.3g}")
    pop = np.array([next(d for d in mah if d['mahalle'] == a)['nufus_2025'] for a in kad_adlari])
    print(f"nüfus ağırlıklı ortalama (çalışma saatleri): {np.sum(cc * pop) / pop.sum():.4g} lif/L; dönem: {np.sum(cd * pop) / pop.sum():.4g} lif/L")
    for i in np.argsort(-cc):
        print(f"  {kad_adlari[i]:<14} {cc[i]:.4f} lif/L (çalışma saati)   {cd[i]:.4f} (dönem)")
    print(f"{time.time() - t0:.0f} sn")
