# veri/: veri sözlüğü ve dosya bazında lisanslar

Biçim: UTF-8, virgül ayırıcı, ondalık nokta, tarihler ISO 8601. **Boş hücre "belgede yok" demektir, sıfır değildir.**
Oranlar kesir olarak tutulur (0,0001 = %0,01). Aralık verilen değerler `alt` / `ust`, tek değerler `deger` sütunundadır.
Her belge `kaynaklar.csv`'de kayıtlıdır (`kaynak_id` ya da `url` ile birleştirilir).

## Ortak sütunlar

| Sütun | Anlamı |
|---|---|
| `kaynak_id` | `kaynaklar.csv`'deki belge kimliği |
| `yer` | Belgede değerin bulunduğu yer: bölüm (§), tablo, şekil ya da sayfa |
| `okuma` | Notu yazanın kaynağı ne kadar okuduğu: `tam_metin`, `ozet`, `ikincil` (basın özeti, derleme), `acilamadi` |
| `dogrulandi` | Değer bizim elimizdeki birincil belgede görüldü mü: `evet` / `hayir` (20.10.2026: hepsi `hayir`) |

## Dosyalar

| Dosya | Satır | İçerik | Kaynak / üretici | Lisans |
|---|---:|---|---|---|
| `parametreler.csv` | 38 | Literatür parametreleri P01–P38: kaynak terimi, salım, dönüşüm, lif fiziği, model belirsizliği | Eski "veri tablosu" Excel'i (`src/ilk_aktarim.py`) | CC BY 4.0 |
| `literatur/olcumler.csv` | 53 | Saha ölçümleri M01–M53 (Kobe, WTC, Tōhoku, Malatya, Kahramanmaraş, yıkım ve patlatmalar) | aynı | CC BY 4.0 |
| `literatur/model_kurulumlari.csv` | 4 | Dört modelleme çalışmasının kurulumu | aynı | CC BY 4.0 |
| `literatur/wtc_seyrelme.csv` | 16 | WTC 2001 CALPUFF seyrelme–mesafe–meteoroloji sonuçları (Gilliam ve ark. 2005) | aynı | CC BY 4.0 |
| `literatur/kobe_karsilastirma.csv` | 6 | Kobe 1995 hesap–ölçüm karşılaştırması (Terazono ve ark. 2000) | aynı | CC BY 4.0 |
| `literatur/hesaplar.csv` | 73 | Makale hesaplarının formüllerle yeniden yapılması. **Hücre düzeni korunur:** `satir` Excel satırıdır, formüller (`=B13*B15…`) bu satırlara başvurur. `girdi`: `kaynak` / `formul` / `varsayim` | aynı | CC BY 4.0 |
| `literatur/kaynak_rolleri.csv` | 26 | Literatür kaynaklarının rolü ve okuma durumu; künye ve bağlantı `kaynaklar.csv`'de | aynı | CC BY 4.0 |
| `literatur/standart_degerler.csv` | 13 | Modelin standart değer seti; `gosterim` Excel'deki yazım, `dayanak` P/M kimliği | Eski "standart değerler" Excel'i | CC BY 4.0 |
| `literatur/standart_degerler_kaynaklari.csv` | 6 | Standart değerler kitabına özgü künye ek notları | aynı | CC BY 4.0 |
| `dogrulanmis/veri_noktalari.csv` | 215 | Belediye belgelerinden okunmuş sayılar: `kaynak_url`, `sayfa` (PDF sayfası), `alinti` | `src/tarama/veri_noktalari.py` (POINTS listesi) | CC BY 4.0; **Kadıköy satırları CC BY-NC 3.0** |
| `dogrulanmis/kapsam_39.csv` | 39 | 39 ilçe için neye bakıldı, ne bulundu, ne kaldı | `src/tarama/kapsam.py` | CC BY 4.0 |
| `dogrulanmis/ibb_deprem_senaryosu_mw75_mahalle.csv` | 959 | Mw 7,5 gece senaryosu, mahalle bazında hasarlı bina, can kaybı, altyapı hasarı, geçici barınma | İBB Açık Veri (`src/ibb_csv.py`) | İBB Açık Veri Lisansı |
| `dogrulanmis/ibb_bina_2017_mahalle.csv` | 959 | 2017 mahalle bazında bina sayıları: 3 yaş × 3 kat sınıfı | İBB Açık Veri (`src/ibb_csv.py`) | İBB Açık Veri Lisansı |
| `ham/` | — | İndirilen özgün belgeler, `*.meta.json` (URL, erişim, SHA-256), istek günlüğü. **Git'e girmez, silinmez.** | bot ve `model/indir.py` | kaynağına göre |

Depodaki diğer veri dosyaları:

| Dosya | İçerik | Lisans |
|---|---|---|
| `ciktilar/tarama/*.csv`, `*.txt`, `turkiye_tarayici_notlar.md` | Tarama kapsam ve kanıt kayıtları: erişim, site haritası, açık veri portalı, site araması, faaliyet raporu keşfi, belge listesi (SHA-256), aday URL listeleri | CC BY 4.0 |
| `model/girdi/mahalle_girdileri.csv` | Kadıköy 21 mahalle: İBB hasar, nüfus, bina yaşı ve kat, yapı türü, toplanma alanı, konut-işyeri, riskli yapı | İBB AVL + Kadıköy CC BY 4.0; riskli yapı sütunları **CC BY-NC 3.0** |
| `model/girdi/mahalle_geometri.csv`, `mahalle_poligon_tm30.json` | Kadıköy mahalle poligonları (EPSG:5254) ve merkezleri; adlar OSM ile eşleştirildi | Kadıköy CC BY 4.0; `osm_ad` sütunu ODbL 1.0 |
| `model/girdi/komsu_mahalleler.csv` | Kadıköy'e 2,5 km içindeki komşu ilçe mahalleleri ve İBB hasarı | ODbL 1.0 (OSM geometrisi) + İBB AVL |
| `model/girdi/meteo_*` | ERA5 2015–2024 saatlik verisinden rüzgâr–kararlılık–karışım yüksekliği frekans tabloları | CC BY 4.0 (Copernicus C3S / Open-Meteo) |

## Bilinen veri sorunları

- `ibb_bina_2017_mahalle.csv`: "19 MAYIS" mahallesi "19.May" yazılmış. Dosyaları **UAVT koduyla** birleştirin (959 kayıt tam eşleşir).
- Kadıköy açık verisi "asbest tespit edilen bina" diyor; faaliyet raporları aynı sayıyı "asbestli malzeme tespit edilen inşaat sahası" olarak veriyor.
- "Bertaraf edilen asbest atığı" asbestli malzemenin kütlesidir, saf asbest değildir.
- Kadıköy 0–14 yaş dosyası tutarsız; kullanılmadı.
