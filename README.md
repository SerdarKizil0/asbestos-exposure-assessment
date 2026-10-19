# asbestos-exposure-assessment

**Mw 7,5 İstanbul depremi sonrası yıkımlarda asbest lifi yayılımı ve maruziyeti: Kadıköy örneği**

> *English summary.* Screening-level assessment of airborne asbestos fibre release and exposure from post-earthquake
> demolition in Kadıköy (Istanbul) under the IBB/KOERI 2019 Mw 7.5 scenario. The repository holds the municipal
> asbestos data survey (39 districts), a literature parameter library, a Gaussian dispersion model driven by ERA5,
> and a source register (`kaynaklar.csv`) that ties every number to a document, page and SHA-256 hash.
> Copyrighted documents are not redistributed. Text and data: CC BY 4.0 (with third-party exceptions); code: MIT.

İstanbul Üniversitesi-Cerrahpaşa Çevre Mühendisliği bitirme projesi ve TÜBİTAK 2209-A başvurusu için hazırlanmaktadır.

## Ne var, ne durumda

| Bileşen | Durum | Yer |
|---|---|---|
| 39 ilçe belediyesinin asbest verisi taraması | 12 belediyede sayısal veri; 215 veri noktası belge, sayfa ve alıntıyla bağlı | `src/tarama/`, `veri/dogrulanmis/` |
| Kadıköy asbest verileri 2015–2025 | Açık veri, faaliyet raporları, tutarlılık kontrolleri | `src/tarama/kadikoy_xlsx.py`, `veri/dogrulanmis/veri_noktalari.csv` |
| Hasar senaryosu | İBB açık verisi, 959 mahalle. KRDAE 2019 raporuyla aynı çalışma (bkz. KARARLAR.md) | `veri/dogrulanmis/ibb_*.csv` |
| Literatür parametre ve ölçüm kütüphanesi | 26 kaynak, 38 parametre, 53 ölçüm. **Değerler henüz birincil belgeyle karşılaştırılmadı** | `veri/parametreler.csv`, `veri/literatur/` |
| Yayılım modeli (Kadıköy) | Tarama modeli; İstanbul'da ölçümle doğrulanmadı | `model/` |
| Kaynak kaydı | 135 belge: URL, erişim tarihi, SHA-256, lisans, arşiv bağlantısı | `kaynaklar.csv` |

Model zinciri: İBB/KOERİ 2019 Mw 7,5 senaryosu (mahalle bazında hasarlı bina) → binada asbest bulunma olasılığı
(Kadıköy açık verisi) → bina başına asbestli malzeme → asbest oranı → salım faktörü ve lif dönüşümü (Terazono ve ark.
2000) → çalışma saatlerine yayılmış salım → sektör ortalamalı Gauss yayılımı (ERA5 2015–2024) → mahalle derişimi
ve nüfusla çakıştırma.

## Klasörler

```
README.md · CLAUDE.md · KARARLAR.md · kaynaklar.csv · LICENSE · LICENSE-CC-BY-4.0.md · requirements.txt
veri/
  parametreler.csv          literatür parametreleri (P01–P38), her satırda kaynak_id ve yer
  literatur/                ölçümler, model kurulumları, model sonuçları, hesaplar, standart değerler
  dogrulanmis/              belgeye bağlanmış tablolar: veri_noktalari, kapsam_39, İBB senaryo ve bina CSV'leri
  ham/                      GİT'E GİRMEZ: indirilen özgün belgeler (SHA-256 + erişim zamanı), istek günlüğü
  README.md                 veri sözlüğü ve dosya bazında lisanslar
src/
  tarama/                   belediye tarama botu (README'si içinde)
  ilk_aktarim.py            tek seferlik: eski Excel'lerden CSV'ye aktarım (20.10.2026)
  excel_uret.py             CSV → literatür Excel kitapları
  ibb_csv.py                İBB ham CSV → temiz kopya (SHA-256 kontrollü)
  arsiv_kontrol.py          Wayback Machine'de mevcut arşiv kopyalarını bulur (salt okuma)
  denetle.py                repo kurallarının denetimi (boyut, uzantı, kişisel veri, kaynak bütünlüğü)
  kancalar/pre-commit       commit öncesi denetim kancası (git config core.hooksPath src/kancalar)
model/                      yayılım modeli; girdi/ izlenir, cikti/ git dışında (README'si içinde)
ciktilar/tarama/            tarama kapsam ve kanıt kayıtları (erişim, site haritası, belge listesi)
gelen/                      GİT'E GİRMEZ: çalışma notları, PDF'ler, eski Excel'ler, arşivler
```

## Her sayının kaynağı nasıl izlenir

- **Belediye verisi:** `veri/dogrulanmis/veri_noktalari.csv` her satırda `kaynak_url`, `sayfa` (PDF sayfası) ve belgedeki
  yazımla kısa bir `alinti` tutar. Aynı URL `kaynaklar.csv`'de SHA-256 ve erişim zamanıyla kayıtlıdır. Elde kopyası olan
  belge `veri/ham/` altındaki dosyayla SHA-256 üzerinden eşleştirilir.
- **Literatür:** `veri/parametreler.csv` ve `veri/literatur/*.csv` her satırda `kaynak_id` ve `yer` (bölüm, tablo, sayfa)
  tutar. `okuma` sütunu notu yazanın kaynağı ne kadar okuduğunu söyler (`tam_metin`, `ozet`, `ikincil`, `acilamadi`).
  `dogrulandi` sütunu bizim birincil belgeyle karşılaştırıp karşılaştırmadığımızı söyler; şu an hepsi `hayir`.
- **Hasar senaryosu:** İBB CSV'si, KRDAE 2019 raporunun Tablo 4-2 (s.76) ve Tablo 4-19 (s.123) değerleriyle karşılaştırıldı
  (KARARLAR.md, 2026-10-20).
- Telifli belgeler (raporlar, makaleler, tezler, faaliyet raporları) depoda **yoktur**; yalnız bağlantıları, SHA-256 özetleri
  ve varsa Wayback Machine bağlantıları `kaynaklar.csv`'dedir.

## Kurulum ve çalıştırma

```bash
pip install -r requirements.txt -r model/requirements.txt
python src/excel_uret.py            # literatür Excel kitapları → ciktilar/excel/
python src/denetle.py               # commit öncesi kural denetimi
```

### Commit öncesi denetim kancası

Depo herkese açık olduğu için her commit'ten önce `src/denetle.py` sahnelenen dosyaları denetler: 50 MB sınırı, yasak
uzantı ve klasörler (PDF, görüntü, Excel, `gelen/`, `veri/ham/`), kişisel veri (e-posta, telefon, TC kimlik no), gizli bilgi,
kaynak bütünlüğü. Hata varsa commit yapılmaz. Kanca depoda `src/kancalar/pre-commit` dosyasıdır; klonladıktan sonra bir
kez etkinleştirin:

```bash
git config core.hooksPath src/kancalar
```

Kancanın çalıştığını görmek için `python src/denetle.py --kanca` (yalnız sahnelenenler) ya da `python src/denetle.py`
(git'e girecek bütün dosyalar). Kancayı kapatmak için `git config --unset core.hooksPath`. Kancayı `--no-verify` ile
atlamayın; hata çıkarsa dosyayı düzeltin ya da `.gitignore`'a ekleyin.

Tarama botu için `src/tarama/README.md`, yayılım modeli için `model/README.md`. Ham veriler depoda olmadığından
modeli sıfırdan çalıştırmak için önce `python model/indir.py` (girdiler → `veri/ham/`) ve OSM sınırlarının klonlanması
gerekir. Tarama ham belgeleri (yaklaşık 7 GB) `src/tarama/harvest.py` ile yeniden indirilir.

## Yorum sınırları ve etik

- Model bir **tarama modelidir**: mutlak derişimler 2–3 mertebe belirsizdir (en çok salım faktörü yüzünden); mahalle
  sıralaması yıkımın nerede olacağına bağlıdır. Sonuçlar "belirtilen deprem, meteoroloji ve enkaz kaldırma varsayımları
  altında tahmini ek derişim" olarak okunmalıdır.
- Nüfusla çakıştırma kişi bazlı maruziyet ölçümü değildir. Mahalleleri "asbestli" ya da "güvenli" diye etiketleyen bir
  dil kullanılmaz. Mahalle düzeyindeki model çıktıları bu nedenle şimdilik depoya konmamıştır.
- Bina, parsel ya da kişi düzeyinde veri toplanmaz ve yayımlanmaz; mahalle düzeyinin altına inilmez.

## Lisans

| Ne | Lisans |
|---|---|
| Kod (`src/`, `model/*.py`) | [MIT](LICENSE) |
| Kendi metinlerimiz ve derlediğimiz veriler (`veri/parametreler.csv`, `veri/literatur/`, `kaynaklar.csv`, tarama kayıtları) | [CC BY 4.0](LICENSE-CC-BY-4.0.md) |
| Kadıköy Belediyesi Asbest Verileri ve Riskli Yapı Tespiti verisi; bunları içeren satırlar (`veri_noktalari.csv` Kadıköy satırları, `model/girdi/mahalle_girdileri.csv`) | CC BY-NC 3.0, Kadıköy Belediyesi (ticari olmayan kullanım) |
| Kadıköy Belediyesi mahalle sınırı, nüfus, bina ve konut-işyeri verileri; Kadıköy'ün 21 mahalle poligonu (`model/girdi/mahalle_poligon_tm30.json`, `mahalle_geometri.csv` ve `mahalle_girdileri.csv` içinde türetilmiş) | CC BY 4.0, Kadıköy Belediyesi (afet toplanma alanları: CC BY 3.0) |
| İBB açık verisi (`veri/dogrulanmis/ibb_*.csv`, model girdilerindeki hasar sütunları) | İBB Açık Veri Lisansı: "Atıf 4.0 Uluslararası (CC BY 4.0) kapsamında lisanslanan kamu sektörü bilgilerini içerir." |
| **OpenStreetMap'ten türetilen mahalle geometrisi:** komşu ilçelerin (Üsküdar, Ataşehir, Maltepe, Ümraniye) OSM mahalle sınırları (`veri/ham/osm/`, depoda yok) ve bu sınırlardan hesaplanan mesafe, hücre sayısı ve alan payı değerleri (`model/girdi/komsu_mahalleler.csv`) | **ODbL 1.0**, © OpenStreetMap katkıcıları. Bu geometriden türetilen veritabanları ODbL ile paylaşılır. |
| OSM ile yapılan mahalle adı eşleştirmesi (`model/girdi/mahalle_geometri.csv` ve `komsu_mahalleler.csv` içindeki `osm_ad` sütunu) | ODbL 1.0, © OpenStreetMap katkıcıları. Kadıköy poligonlarının geometrisi OSM'den değil, Kadıköy Belediyesi'nin sınır verisinden gelir. |
| ERA5 meteorolojisinden türetilenler (`model/girdi/meteo_*`) | CC BY 4.0: Copernicus İklim Değişikliği Servisi bilgisi içerir (Hersbach ve ark. 2020), Open-Meteo.com aracılığıyla |
| Raporlar, makaleler, tezler, belediye faaliyet raporları | Depoda yok; yalnız `kaynaklar.csv`'de bağlantı ve SHA-256 |

Her dosyanın lisansı `veri/README.md`'de, her belgenin lisansı `kaynaklar.csv`'nin `lisans` sütunundadır.

## Atıf

Kızılkale, S. (2026). *asbestos-exposure-assessment: Mw 7,5 İstanbul depremi sonrası yıkımlarda asbest lifi yayılımı ve
maruziyeti, Kadıköy örneği.* https://github.com/SerdarKizil0/asbestos-exposure-assessment
