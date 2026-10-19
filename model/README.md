# Yayılım modeli: Kadıköy, Mw 7,5 sonrası yıkım (14 Ekim 2026)

Kadıköy seçildi, çünkü tek ilçede hem 11 yıllık asbest açık verisi (tespit oranı, bina başına ton) hem de mahalle bazında
nüfus, 65 yaş üstü, bina yaşı, riskli yapı, toplanma alanı ve sınır verisi var.

**Zincir:** İBB/KOERİ 2019 Mw 7,5 senaryosu (mahalle bazında çok ağır + ağır hasarlı bina) → binada asbest bulunma olasılığı
(Kadıköy havuzu %19,4) → bina başına asbestli malzeme (1.389 kg) × asbest oranı (%12) → salım faktörü (%0,01) × 30 lif/ng →
12 ay, çalışma saatleri (08–18, pazartesi–cumartesi) → ISCLT tipi sektör ortalamalı Gauss yayılımı (Briggs kentsel σ,
100 m ızgara, ERA5 2015–2024 saatlik meteoroloji; komşu ilçelerin 2,5 km içindeki mahalleleri de kaynak).

Parametreler ve dayanakları `model.py` içindeki `P` sözlüğündedir (temel, alt, üst, birim, açıklama, kaynak, tür).
Literatürden gelen değerler `veri/parametreler.csv` ile aynı olmalıdır (`src/denetle.py` kontrol eder).
Yöntem kararları: `KARARLAR.md` (2026-10-14).

## Çalıştırma

```bash
pip install -r model/requirements.txt
cd model
python indir.py                        # girdiler → veri/ham/{ibb,kadikoy,meteo} (zaten varsa gerek yok)
git clone https://github.com/sahircansurmeli/istanbul-geojson ../veri/ham/osm/istanbul-geojson
git -C ../veri/ham/osm/istanbul-geojson checkout c9bf151
python mahalle_geometri.py ../veri/ham/osm/istanbul-geojson/mahalle_geojson.json   # SHP poligonlarına OSM adları (IoU ≥ 0,945)
python girdiler.py && python meteoroloji.py && python izgara.py
python model.py                        # aktarım matrisleri, ~10 dk (cikti/D_*.npy)
python duyarlilik.py                   # tek tek, yapısal, Monte Carlo (4.000)
python sonuclar.py && python grafik.py
python rapor_model_xlsx.py             # canlı Excel; LibreOffice/Excel'de açıp kaydedin (formül değerleri)
python dogrula_xlsx.py                 # Excel = Python kontrolü
```

`izgara.py` OSM dosyasını varsayılan olarak `veri/ham/osm/istanbul-geojson/mahalle_geojson.json` yolundan okur;
başka bir yer için `ASBEST_OSM_GEOJSON` ortam değişkenini verin. `model.py` aktarım matrislerini `cikti/D_*.npy` olarak
önbelleğe alır; geometri, ızgara ya da meteoroloji değişirse `aktarimlar(yeniden=True)`.

## Girdiler ve çıktılar

- `girdi/` depoda izlenir: mahalle girdi tablosu, geometri, komşu mahalleler, meteoroloji frekans tabloları.
  Lisansları `veri/README.md`'de (Kadıköy CC BY 4.0 ve CC BY-NC 3.0, İBB Açık Veri Lisansı, OSM ODbL, ERA5 CC BY 4.0).
- `cikti/` **git dışında**: `kadikoy_asbest_yayilim_modeli.xlsx` (Parametreler sayfasındaki sarı/mavi hücreler değişince
  salım, derişim, sıra ve maruziyet yeniden hesaplanır), haritalar ve grafikler (PNG), `sonuclar.json`, `duyarlilik.json`,
  aktarım matrisleri. Mahalle düzeyindeki sonuçların yayımlanmasına ayrıca karar verilecek (KARARLAR.md, 2026-10-20).

## Kurallar

- Excel'deki salım ve derişim zinciri canlıdır; Python ile aynı sonucu verdiği `dogrula_xlsx.py` ile kontrol edilir.
  Excel formüllerinde `-x^2` yazmayın (Excel'de tekli eksi önce uygulanır, +x² olur); `-0.5*(x)^2` kullanın.
- Parametre değeri değişirse `model.py` içindeki `P` sözlüğünü, Excel'in Parametreler sayfasını, bu README'yi ve
  gerekiyorsa `veri/parametreler.csv`'yi birlikte güncelleyin; KARARLAR.md'ye tarihli kayıt düşün.
- Kadıköy 0–14 yaş dosyası tutarsız (ör. Koşuyolu'nda 6.648 nüfusa 4.312 çocuk): kullanılmadı.
- Bütün indirmeler `src/tarama/common.py` `fetch()` üzerinden gider. Tek istisna: Open-Meteo'nun robots.txt dosyası tüm
  yolları kapatıyor; belgelenmiş ücretsiz bir API olduğu için yalnız ERA5 isteğinde robots kontrolü kapatıldı (`indir.py`
  açıklaması). İstenirse aynı veri Copernicus CDS'ten indirilebilir (hesap gerekir; `.cdsapirc` depoya girmez).

## Sınırlar

Tarama modelidir, İstanbul'da ölçümle doğrulanmadı. Bina gövdeleri, deniz meltemi, yağışla bastırma, çökme anının toz
bulutu, enkaz taşıma ve döküm sahaları yok; kaynaklar mahalle içinde eşit dağıtıldı. Mutlak değerler 2–3 mertebe belirsiz
(en çok salım faktörü); mahalle sıralaması yıkımın nerede olacağına bağlı.

En değerli yeni veri: Türkiye'de yıkım sahası çevresinde PCM + TEM ölçümü; belediyelerin bina bazında asbest envanter
raporları (malzeme türü ve miktarı); deprem sonrası yıkım kararlarının mahalle dağılımı.
