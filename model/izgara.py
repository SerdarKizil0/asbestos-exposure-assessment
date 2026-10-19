"""100 m'lik hesap ızgarası: Kadıköy mahalleleri (alıcı + kaynak) ve 2,5 km içindeki komşu mahalleler (yalnız kaynak).

Komşu mahalle sınırları OSM'den (sahircansurmeli/istanbul-geojson, ODbL); hasar sayıları İBB deprem senaryosundan.
"""
from __future__ import annotations

import json
import os
import re
import warnings

import numpy as np
import shapely
from pyproj import Transformer
from shapely import wkt
from shapely.geometry import shape
from shapely.ops import transform, unary_union

from ortak import GIRDI, RAW, anahtar, oku_csv, sayi, tr_baslik, yaz_csv
from yayilim import Izgara

warnings.filterwarnings("ignore", category=DeprecationWarning)
# OSM mahalle sınırları (sahircansurmeli/istanbul-geojson, commit c9bf151; ODbL). Yol ortam değişkeniyle değiştirilebilir.
OSM_YOLU = os.environ.get("ASBEST_OSM_GEOJSON", str(RAW / "osm" / "istanbul-geojson" / "mahalle_geojson.json"))
KOMSU_ILCE = {"ÜSKÜDAR": "Üsküdar", "ATAŞEHİR": "Ataşehir", "MALTEPE": "Maltepe", "ÜMRANİYE": "Ümraniye"}


def kadikoy_poligonlari() -> dict:
    d = json.load(open(GIRDI / "mahalle_poligon_tm30.json", encoding="utf-8"))
    return {ad: wkt.loads(w) for ad, w in d.items()}


def komsular(kad_birlesik, yaricap=2500.0) -> list[dict]:
    s = open(OSM_YOLU, encoding="utf-8").read()
    dec = json.JSONDecoder()
    feats = []
    for m in re.finditer(r'\{\s*"type": "Feature",', s):
        try:
            feats.append(dec.raw_decode(s, m.start())[0])
        except Exception:
            pass
    ibb = {}
    for r in oku_csv(RAW / "ibb" / "deprem_senaryosu_analiz_sonuclari.csv"):
        ibb.setdefault(anahtar(r["mahalle_adi"]).replace(" ", ""), []).append(r)
    to_tm30 = Transformer.from_crs("EPSG:4326", "EPSG:5254", always_xy=True).transform
    out, atlanan = [], []
    for f in feats:
        dn = f["properties"].get("display_name", "")
        g = transform(to_tm30, shape(f["geometry"])).buffer(0)
        if kad_birlesik.contains(g.centroid) or kad_birlesik.distance(g) > yaricap:
            continue
        ad = dn.split(" Mahallesi")[0]
        aday = [r for r in ibb.get(anahtar(ad).replace(" ", ""), []) if r["ilce_adi"] in KOMSU_ILCE]
        etiket = [k for k, v in KOMSU_ILCE.items() if f", {v}," in dn]
        if etiket:
            aday = [r for r in aday if r["ilce_adi"] == etiket[0]]
        if len(aday) != 1:
            atlanan.append((ad, dn[:70], [r["ilce_adi"] for r in aday]))
            continue
        r = aday[0]
        out.append({"ilce": tr_baslik(r["ilce_adi"]), "mahalle": tr_baslik(r["mahalle_adi"]), "osm_ad": dn[:90],
                    "mesafe_m": round(kad_birlesik.distance(g)), "hasar_cok_agir": sayi(r["cok_agir_hasarli_bina_sayisi"]),
                    "hasar_agir": sayi(r["agir_hasarli_bina_sayisi"]), "hasar_orta": sayi(r["orta_hasarli_bina_sayisi"]),
                    "wkt": g.wkt})
    return out, atlanan


def kur(hucre=100.0, yaricap=2500.0, komsu_dahil=True):
    kp = kadikoy_poligonlari()
    birlesik = unary_union(list(kp.values()))
    kom, atlanan = komsular(birlesik, yaricap) if komsu_dahil else ([], [])
    minx, miny, maxx, maxy = birlesik.bounds
    m = yaricap if komsu_dahil else 0
    xs = np.arange(minx - m, maxx + m, hucre) + hucre / 2
    ys = np.arange(miny - m, maxy + m, hucre) + hucre / 2
    X, Y = np.meshgrid(xs, ys)
    X, Y = X.ravel(), Y.ravel()
    mah = np.array([""] * len(X), dtype=object)
    for ad, p in kp.items():
        mah[shapely.contains_xy(p, X, Y)] = ad
    alici = mah != ""
    kay_mah = mah.copy()
    kom_adlari = []
    for k in kom:
        p = wkt.loads(k["wkt"])
        ad = f"{k['ilce']}/{k['mahalle']}"
        sec = shapely.contains_xy(p, X, Y) & (kay_mah == "") & (shapely.distance(birlesik, shapely.points(X, Y)) <= yaricap)
        if sec.sum() > 0:
            kay_mah[sec] = ad
            k["hucre_sayisi"] = int(sec.sum())
            # mahallenin yalnız yarıçap içindeki payı kaynak olur (salım bu payla ölçeklenir)
            k["pay_icerde"] = min(1.0, sec.sum() * hucre * hucre / p.area)
            kom_adlari.append(ad)
    kaynak = kay_mah != ""
    iz = Izgara(np.c_[X[alici], Y[alici]], mah[alici], np.c_[X[kaynak], Y[kaynak]], kay_mah[kaynak], hucre)
    return iz, sorted(kp), kom, kom_adlari, atlanan


if __name__ == "__main__":
    iz, kad, kom, kom_adlari, atlanan = kur()
    print("alıcı hücre", len(iz.alici_xy), "kaynak hücre", len(iz.kaynak_xy), "komşu mahalle", len(kom_adlari))
    for k in sorted(kom, key=lambda d: d["mesafe_m"]):
        if "hucre_sayisi" in k:
            print(f"  {k['ilce']:<9} {k['mahalle']:<20} {k['mesafe_m']:>5} m  çok ağır+ağır {k['hasar_cok_agir']+k['hasar_agir']:>4.0f}  orta {k['hasar_orta']:>4.0f}  hücre {k['hucre_sayisi']}  içerde %{100*k['pay_icerde']:.0f}")
    print("atlanan:", atlanan)
    yaz_csv(GIRDI / "komsu_mahalleler.csv", [{k: v for k, v in d.items() if k != "wkt"} for d in kom if "hucre_sayisi" in d])
