"""ERA5 saatlik verisinden (Open-Meteo, 41,0K 29,0D hücresi, 2015-2024) kararlılık sınıfı ve frekans tabloları.

Kararlılık: Pasquill-Gifford, Turner yöntemi (gündüz güneş ışınımı + rüzgâr; gece bulutluluk + rüzgâr).
Kentsel düzeltme: kentte gece E/F sınıfları ısı adası nedeniyle seyrek gözlenir; modelde E ve F tek grup (E-F)
olarak Briggs kentsel katsayılarıyla kullanılır, ayrıca 'kentsel düzeltme' duyarlılığında E-F → D yapılır.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np

from ortak import GIRDI, RAW, yaz_csv

SINIFLAR = ["A", "B", "C", "D", "E", "F"]


def gunduz_sinifi(u: float, rad: float) -> str:
    """Turner: güçlü (>600 W/m²), orta (300-600), zayıf (<300) ışınım."""
    if rad > 600:
        tab = ["A", "A", "B", "C", "C"]  # u <2, 2-3, 3-5, 5-6, >6  (A-B → A, B-C → B yuvarlaması: muhafazakâr değil, ortalama)
    elif rad > 300:
        tab = ["A", "B", "B", "C", "D"]
    else:
        tab = ["B", "C", "C", "D", "D"]
    i = 0 if u < 2 else 1 if u < 3 else 2 if u < 5 else 3 if u < 6 else 4
    return tab[i]


def gece_sinifi(u: float, bulut: float) -> str:
    if bulut >= 95:
        return "D"
    if bulut >= 50:  # ≥4/8
        tab = ["E", "E", "D", "D", "D"]
    else:
        tab = ["F", "F", "E", "D", "D"]
    i = 0 if u < 2 else 1 if u < 3 else 2 if u < 5 else 3 if u < 6 else 4
    return tab[i]


def yukle():
    j = json.loads((RAW / "meteo" / "era5_kadikoy_2015_2024.json").read_text())
    h = j["hourly"]
    zaman = [datetime.fromisoformat(t) for t in h["time"]]
    u = np.array(h["wind_speed_10m"], dtype=float)
    yon = np.array(h["wind_direction_10m"], dtype=float)  # rüzgârın geldiği yön
    rad = np.array(h["shortwave_radiation"], dtype=float)
    bulut = np.array(h["cloud_cover"], dtype=float)
    yagis = np.array(h["precipitation"], dtype=float)
    blh = np.array([np.nan if v is None else v for v in h["boundary_layer_height"]], dtype=float)
    sinif = np.array([gunduz_sinifi(a, r) if r > 10 else gece_sinifi(a, b) for a, r, b in zip(u, rad, bulut)])
    return {"zaman": zaman, "u": u, "yon": yon, "rad": rad, "bulut": bulut, "yagis": yagis, "blh": blh, "sinif": sinif,
            "hucre": (j["latitude"], j["longitude"], j["elevation"])}


def calisma_saati(t: datetime, bas=8, son=18, cumartesi=True) -> bool:
    """Yıkım/enkaz işleri: 08:00-18:00, pazartesi-cumartesi (pazar yok)."""
    if t.weekday() == 6 or (t.weekday() == 5 and not cumartesi):
        return False
    return bas <= t.hour < son


YON_ADLARI = ["K", "KKD", "KD", "DKD", "D", "DGD", "GD", "GGD", "G", "GGB", "GB", "BGB", "B", "BKB", "KB", "KKB"]


def ozet(m, maske):
    u, yon, s, blh, yagis = m["u"][maske], m["yon"][maske], m["sinif"][maske], m["blh"][maske], m["yagis"][maske]
    n = maske.sum()
    sektor = ((yon + 11.25) % 360 // 22.5).astype(int)
    gul = Counter(sektor)
    st = Counter(s)
    return {
        "saat": int(n),
        "ruzgar_ortalama": float(np.mean(u)),
        "ruzgar_medyan": float(np.median(u)),
        "sakin_payi_<1ms": float(np.mean(u < 1)),
        "hafif_payi_<2ms": float(np.mean(u < 2)),
        "yagisli_saat_payi_>0.1mm": float(np.mean(yagis > 0.1)),
        "blh_medyan": float(np.nanmedian(blh)),
        "blh_p10": float(np.nanpercentile(blh, 10)),
        "sinif": {k: st.get(k, 0) / n for k in SINIFLAR},
        "gul": {YON_ADLARI[i]: gul.get(i, 0) / n for i in range(16)},
    }


def frekans_tablosu(m, maske, n_sektor=36):
    """Uzun dönem ortalaması için ortak frekans: yön sektörü × hız sınıfı × kararlılık grubu × karışım yüksekliği sınıfı."""
    hiz_sinirlari = [0, 1.5, 2.5, 3.5, 5.0, 7.0, 99]
    hiz_temsil = [1.0, 2.0, 3.0, 4.2, 5.8, 8.0]
    blh_sinirlari = [0, 300, 700, 1500, 9999]
    blh_temsil = [200, 500, 1000, 1800]
    grup = {"A": "AB", "B": "AB", "C": "C", "D": "D", "E": "EF", "F": "EF"}
    u, yon, s, blh = m["u"][maske], m["yon"][maske], m["sinif"][maske], m["blh"][maske]
    blh = np.where(np.isnan(blh), np.nanmedian(blh), blh)
    sek = ((yon + 180 / n_sektor) % 360 // (360 / n_sektor)).astype(int)
    hi = np.clip(np.searchsorted(hiz_sinirlari, u, side="right") - 1, 0, len(hiz_temsil) - 1)
    bi = np.clip(np.searchsorted(blh_sinirlari, blh, side="right") - 1, 0, len(blh_temsil) - 1)
    say = Counter(zip(sek, hi, [grup[x] for x in s], bi))
    n = len(u)
    satirlar = []
    for (a, b, c, d), k in sorted(say.items()):
        satirlar.append({"sektor": int(a), "yon_derece": a * 360 / n_sektor, "hiz_ms": hiz_temsil[b], "kararlilik": c,
                         "karisim_m": blh_temsil[d], "frekans": k / n})
    return satirlar


if __name__ == "__main__":
    m = yukle()
    print("ERA5 hücresi:", m["hucre"])
    tum = np.ones(len(m["zaman"]), bool)
    cal = np.array([calisma_saati(t) for t in m["zaman"]])
    kis = np.array([t.month in (12, 1, 2) for t in m["zaman"]]) & cal
    yaz = np.array([t.month in (6, 7, 8) for t in m["zaman"]]) & cal
    sabah = np.array([t.hour in (8, 9) for t in m["zaman"]]) & cal
    ozetler = {"tum_saatler": ozet(m, tum), "calisma_saatleri": ozet(m, cal), "kis_calisma": ozet(m, kis),
               "yaz_calisma": ozet(m, yaz), "sabah_08_10": ozet(m, sabah)}
    for k, v in ozetler.items():
        print(f"\n== {k}: {v['saat']} saat; ort. rüzgâr {v['ruzgar_ortalama']:.2f} m/s; <1 m/s %{100*v['sakin_payi_<1ms']:.1f}; "
              f"<2 m/s %{100*v['hafif_payi_<2ms']:.1f}; yağışlı %{100*v['yagisli_saat_payi_>0.1mm']:.1f}; BLH medyan {v['blh_medyan']:.0f} m (p10 {v['blh_p10']:.0f})")
        print("   kararlılık:", {a: f"{100*b:.1f}" for a, b in v["sinif"].items()})
        print("   rüzgâr gülü (gelen yön):", {a: f"{100*b:.1f}" for a, b in v["gul"].items()})
    (GIRDI / "meteo_ozet.json").write_text(json.dumps(ozetler, ensure_ascii=False, indent=1))
    fr = frekans_tablosu(m, cal)
    yaz_csv(GIRDI / "meteo_frekans_calisma.csv", fr)
    fr_k = frekans_tablosu(m, kis)
    yaz_csv(GIRDI / "meteo_frekans_kis.csv", fr_k)
    fr_y = frekans_tablosu(m, yaz)
    yaz_csv(GIRDI / "meteo_frekans_yaz.csv", fr_y)
    print("\nfrekans kutusu:", len(fr), "toplam", round(sum(r['frekans'] for r in fr), 6))
