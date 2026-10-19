"""Kadıköy mahalle poligonlarına ad verir ve model için geometri tablosu üretir.

Girdiler:
- veri/ham/kadikoy/model/kadikoy-ilcesindeki-mahalle-sinirlari.shp (Kadıköy Açık Veri; öznitelik dosyası yok, yalnız geometri)
- OSM mahalle sınırları (sahircansurmeli/istanbul-geojson, ODbL) — yalnız ad eşleştirmek için

Çıktı: model/girdi/mahalle_geometri.csv (ad, alan, merkez TM30 x/y, merkez enlem/boylam, eşleşme IoU)
"""
import json, re, sys, csv
from pathlib import Path
import shapefile
from shapely.geometry import shape, Polygon, mapping
from shapely.ops import transform  # noqa
import warnings; warnings.filterwarnings('ignore', category=DeprecationWarning)
from pyproj import Transformer
from scipy.optimize import linear_sum_assignment
import numpy as np

KOK = Path(__file__).resolve().parents[1]
SHP = KOK / 'veri/ham/kadikoy/model/kadikoy-ilcesindeki-mahalle-sinirlari.shp'
OSM = Path(sys.argv[1])
CIKTI = KOK / 'model/girdi'; CIKTI.mkdir(parents=True, exist_ok=True)

ADLAR = ['19 Mayıs', 'Acıbadem', 'Bostancı', 'Caddebostan', 'Caferağa', 'Dumlupınar', 'Eğitim', 'Erenköy', 'Fenerbahçe',
         'Feneryolu', 'Fikirtepe', 'Göztepe', 'Hasanpaşa', 'Koşuyolu', 'Kozyatağı', 'Merdivenköy', 'Osmanağa',
         'Rasimpaşa', 'Sahrayıcedit', 'Suadiye', 'Zühtüpaşa']

s = OSM.read_text(encoding='utf-8')
dec = json.JSONDecoder(); feats = []
for m in re.finditer(r'\{\s*"type": "Feature",', s):
    try:
        feats.append(dec.raw_decode(s, m.start())[0])
    except Exception:
        pass

def kadikoy_mu(dn: str) -> bool:
    if ', Kadıköy, İstanbul' in dn:
        return True
    if any(x in dn for x in (', Şişli,', ', Büyükçekmece,', ', Ataşehir,', ', Üsküdar,')):
        return False
    pk = re.search(r'\b(34\d{3})\b', dn)
    return (pk is None) or pk.group(1).startswith('347')

osm = {}
for kesin in (True, False):  # önce adında 'Kadıköy' geçen kayıtlar, sonra posta koduyla eşleşenler
    for f in feats:
        dn = f['properties'].get('display_name', '')
        for a in ADLAR:
            if a in osm or not dn.startswith(a + ' Mahallesi'):
                continue
            if (kesin and ', Kadıköy, İstanbul' in dn) or (not kesin and kadikoy_mu(dn)):
                osm[a] = f
eksik = [a for a in ADLAR if a not in osm]
print('OSM eşleşen', len(osm), 'eksik', eksik)

to_tm30 = Transformer.from_crs('EPSG:4326', 'EPSG:5254', always_xy=True).transform
to_wgs = Transformer.from_crs('EPSG:5254', 'EPSG:4326', always_xy=True).transform
osm_poly = {a: transform(to_tm30, shape(f['geometry'])).buffer(0) for a, f in osm.items()}

r = shapefile.Reader(shp=open(SHP, 'rb'))
shp_poly = []
for sh in r.shapes():
    parts = list(sh.parts) + [len(sh.points)]
    rings = [sh.points[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]
    poly = Polygon(rings[0], rings[1:]).buffer(0)
    shp_poly.append(poly)

names = list(osm_poly)
iou = np.zeros((len(shp_poly), len(names)))
for i, p in enumerate(shp_poly):
    for j, a in enumerate(names):
        q = osm_poly[a]
        inter = p.intersection(q).area
        iou[i, j] = inter / p.union(q).area if inter > 0 else 0
row, col = linear_sum_assignment(-iou)
rows = []
for i, j in zip(row, col):
    p = shp_poly[i]
    c = p.representative_point() if not p.centroid.within(p) else p.centroid
    lon, lat = to_wgs(c.x, c.y)
    rows.append({'poligon': int(i), 'mahalle': names[j], 'iou': round(float(iou[i, j]), 3), 'alan_km2': round(p.area / 1e6, 4),
                 'x_tm30': round(c.x, 1), 'y_tm30': round(c.y, 1), 'enlem': round(lat, 6), 'boylam': round(lon, 6),
                 'osm_ad': osm[names[j]]['properties'].get('display_name', '')[:80]})
rows.sort(key=lambda d: d['mahalle'])
for d in rows:
    print(d)
with open(CIKTI / 'mahalle_geometri.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
# poligonları da kaydet (TM30, WKT) — harita ve kıyı mesafesi için
json.dump({d['mahalle']: shp_poly[d['poligon']].wkt for d in rows}, open(CIKTI / 'mahalle_poligon_tm30.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('min IoU', min(d['iou'] for d in rows))
