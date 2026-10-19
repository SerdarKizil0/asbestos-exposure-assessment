# KARARLAR: tarihli yöntem kararları

En yeni karar üstte. Her kayıt: **karar**, **dayanak**, gerekiyorsa **sonuç ve açık noktalar**.
"Çalışma notu" diye anılan belgeler `gelen/` altındadır ve depoya girmez; dayanak olarak değil, kararın izini sürmek için anılır.

---

## [TARİH] — Odak PM'den asbeste kaydırıldı. Gerekçe: [GEREKÇE].
- **Önceki durum:** 21 Eylül 2026 sunumu PM'yi ana nicel eksen, asbesti katsayı belirsizliği korunarak senaryo ve
  duyarlılık analizi olarak tanımlamıştı (aşağıda 2026-09-21). Depo başlığı ve TÜBİTAK başvurusu artık "asbest lifi yayılımı
  ve maruziyeti, Kadıköy örneği"dir.

---

## 2026-10-20: Depo düzeni ve tek doğruluk kaynağı
- **Karar:** CSV tek doğruluk kaynağıdır; Excel kitapları betikle üretilir ve git'e girmez. asbest-tarama klasörü şöyle dağıtıldı:
  bot `src/tarama/`, model `model/`, ham indirmeler `veri/ham/` (git dışı), doğrulanmış tablolar `veri/dogrulanmis/`,
  tarama kayıtları `ciktilar/tarama/`. Literatür tabloları "doğrulanmış" sayılmadığı için ayrı bir klasörde,
  `veri/literatur/` altında tutulur.
- **Dayanak:** PLAN.md (Aşama 1, onaylı). Taşımadan sonra `kapsam.py`, `mahalle_tahmin.py`, `rapor_xlsx.py`, `girdiler.py`,
  `meteoroloji.py` bayt bayt aynı çıktıyı verdi. `excel_uret.py --karsilastir` literatür kitaplarında 0 farklı hücre verdi.
- **Açık:** Ham belediye PDF'leri bu kopyada yok; `veri_noktalari.py` ve `kadikoy_xlsx.py` belgeler gelene kadar çalıştırılmaz.

## 2026-10-20: İBB senaryo CSV'si = KRDAE 2019, Mw 7,5, üç yöntemin ortalaması, gece Model 2
- **Karar:** `ibb_deprem_senaryosu` (959 mahalle) hasar girdisi olarak KRDAE 2019 çalışmasının ürünü sayılır.
  Bina hasarı sütunları CSM, MADRS ve CM yöntemlerinin ortalamasıdır; can kaybı ve yaralı sütunları gece senaryosunun Model 2 sonucudur.
- **Dayanak:** 959 mahallenin toplamları ile rapor tabloları:

  | Gösterge | CSV | Rapor | Yer |
  |---|---:|---:|---|
  | Çok ağır hasarlı bina | 13.496 | 13.495 | Tablo 4-2, s.76 (PDF 112) |
  | Ağır hasarlı | 34.334 | 34.345 | aynı |
  | Orta hasarlı | 146.512 | 146.552 | aynı |
  | Hafif hasarlı | 301.524 | 301.626 | aynı |
  | Can kaybı | 14.145 | 14.148 | Tablo 4-19, s.123 (PDF 159) |
  | Ağır yaralı / hastanede tedavi / hafif yaralı | 8.090 / 39.636 / 75.240 | 8.088 / 39.641 / 75.245 | aynı |

  Farklar %0,04'ün altında; hücreden mahalleye aktarımdaki yuvarlamayla uyumlu. Model 1 sonuçları (Tablo 4-18) tutmuyor.
  Mahalle düzeyinde: Avcılar ilçe kitapçığı Tablo 5-1 (s.42) 10 mahallenin 8 sütununda, Fatih kitapçığı ilçe toplamında
  CSV ile birebir aynı. Ana raporda mahalle tablosu yok (analiz hücre bazlı).
- **Açık:** Veri seti sayfası çalışmanın adını yazmıyor; bağ sayısal eşleşmeye dayanıyor. Kadıköy kitapçığıyla mahalle düzeyinde karşılaştırma yapılmadı.

## 2026-10-20: "Doğrulandı" ne demek
- **Karar:** Literatür satırlarında iki ayrı alan tutulur. `okuma`, notu yazanın kaynağı ne kadar okuduğunu söyler
  (`tam_metin`, `ozet`, `ikincil`, `acilamadi`). `dogrulandi`, değerin bizim elimizdeki birincil belgede görülüp
  görülmediğini söyler. Birincil belgeler depoda olmadığı için 20.10.2026 itibarıyla bütün literatür satırları `dogrulandi = hayir`.
- **Dayanak:** PLAN.md §3.3; çalışma notlarındaki sayılar kaynak sayılmaz.

## 2026-10-20: Mahalle düzeyindeki model çıktıları depo dışında
- **Karar:** `model/cikti/` (derişim, sıralama, haritalar) ve `ciktilar/tarama/mahalle_tahmin.csv` yayımlama kararı
  verilene kadar git'e girmez. Model kodu ve girdileri girer.
- **Dayanak:** Mutlak değerler 2–3 mertebe belirsiz, sonuçlar ölçümle doğrulanmadı. Mahalle damgalama riski
  (çalışma notu, ek görevler §4.4).

## 2026-10-20: Arşiv bağlantıları salt okumayla
- **Karar:** `kaynaklar.csv`'deki `arsiv_url` yalnız Wayback Machine'de **var olan** kopyalardan doldurulur
  (`src/arsiv_kontrol.py`, robots.txt'ye uyar). Yeni arşivleme isteği (`web.archive.org/save`) göndermek ayrı bir karardır.

## 2026-10-19: Kadıköy asbest verileri
- **Karar:** "Bertaraf edilen asbest atığı" asbestli malzemenin (eternit levha, marley, kazan yalıtımı) toplam kütlesidir,
  saf asbest değildir. Tespit oranı = asbest tespit edilen bina / denetlenen inşaat sahası (pay ve payda farklı birim;
  belgelerde her sahaya bir bina sayılmış görünüyor). Model 2015–2025 havuz değerlerini kullanır: tespit oranı
  789 / 4.075 = 0,194; tespit edilen bina başına 1.389 kg asbestli malzeme.
- **Dayanak:** Kadıköy Açık Veri "Asbest Verileri" (6 Nisan 2026 güncellemesi), 2018 ve 2021–2024 faaliyet raporları
  (`kaynaklar.csv`: `kadikoy_*`).
- **Açık:** Havuz oranı zamandaki düşüşü gizliyor: 2015–2018'de 665 / 2.119 = 0,314, 2022–2025'te 53 / 1.468 = 0,036
  (yaklaşık 9 kat). Modelde yıllık en düşük ve en yüksek değerler duyarlılık aralığı olarak kullanılıyor; havuz değerinin
  temel değer olarak kalıp kalmayacağı tartışılmalı. Çevre birimi sayfasındaki "bugüne kadar" toplamları (3.379 saha,
  923,76 ton) ve 2021 raporundaki "2015–2021 toplamı" yıllık seriyle tutmuyor.

## 2026-10-14: Yayılım modeli kurulumu
- **Karar:** Pilot ilçe Kadıköy. Zincir: İBB Mw 7,5 senaryosu (çok ağır + ağır hasarlı bina; orta hasarlıların yıkılan payı
  `f_orta` = 0, aralık 0–1) → asbest bulunma olasılığı (Kadıköy havuzu) → bina başına asbestli malzeme → malzemedeki asbest
  oranı `w_asbest` = 0,12 (varsayım, aralık 0,05–0,25) → salım faktörü `EF` = 1×10⁻⁴ kg/kg (Terazono 2000; aralık
  10⁻⁵–10⁻³) × 30 lif/ng → 12 ay, çalışma saatleri 08–18, pazartesi–cumartesi → ISCLT tipi sektör ortalamalı Gauss yayılımı
  (Briggs kentsel σ, 100 m ızgara, ERA5 2015–2024 saatlik meteoroloji; komşu ilçelerin 2,5 km içindeki mahalleleri de kaynak).
  Önceden söküm ve ıslatma temel senaryoda 0.
- **Dayanak:** Kadıköy tek ilçede 11 yıllık asbest açık verisi ile mahalle bazında nüfus, 65 yaş üstü, bina yaşı, riskli yapı,
  toplanma alanı ve sınır verisini birlikte sunuyor. Parametre tablosu: `model/model.py` `P`.
- **İstisna:** Open-Meteo'nun robots.txt dosyası tüm yolları kapatıyor. Belgelenmiş ücretsiz bir API olduğu için yalnız ERA5
  isteğinde robots kontrolü kapatıldı (`model/indir.py`); aynı veri Copernicus CDS'ten de indirilebilir.
- **Kullanılmayan veri:** Kadıköy 0–14 yaş dosyası tutarsız (ör. Koşuyolu'nda 6.648 nüfusa 4.312 çocuk).
- **Sınırlar:** Bina gövdeleri, deniz meltemi, yağışla bastırma, çökme anının toz bulutu, enkaz taşıma ve döküm sahaları
  modelde yok; kaynaklar mahalle içinde eşit dağıtıldı.

## 2026-10-13: Belediye taraması ve mahalle dağıtımı
- **Karar:** Tarama robots.txt'ye uyar, aynı hosta ≥2 sn aralıkla istek atar, bot korumasını aşmaz; erişilemeyen siteler
  kanıtla "erişilemedi" olarak işaretlenir. Kadıköy ve Maltepe için mahalle dağılımı bir **model tahminidir**, veri değildir:
  Kadıköy'de ilçe tespitleri o yılın riskli yapı tespitlerine orantılı dağıtıldı; Maltepe'de ilçe tespit oranı her mahalleye
  eşit uygulandı.
- **Dayanak:** asbest-tarama README ve CLAUDE.md (13 Ekim 2026).

## 2026-10-05: Standart değer seti
- **Karar:** Modelin standart değerleri: binadaki asbest yükü 0,086 kg/m² kat alanı, salım faktörü %0,01, 30 lif/ng;
  ince lif çökelmesi ihmal edilir (0,5 µm lif için 0,07 mm/s); kaynağa 200 m'den yakın noktalarda Gauss modeli sonucu
  1,6–2,6 katsayısıyla düzeltilebilir. Karşılaştırma değerleri: olağan kent havası 0,19–0,41 lif/L, Kobe deprem sonrası
  1–2 (en yüksek 6) lif/L, Türkiye işyeri sınırı 0,1 lif/cm³ (halk için değil).
- **Dayanak:** `veri/literatur/standart_degerler.csv` (her satırın `dayanak` sütunu P/M kimliğini gösterir).
  Değerler birincil belgeyle henüz karşılaştırılmadı.

## 2026-09-27: Salım faktörü belirsizliği
- **Karar:** %0,01 salım faktörü alt değer sayılır, daha yüksek değerlerle duyarlılık analizi yapılır. Kobe'de hesap ölçülen
  artışın yaklaşık beşte biriydi ve korelasyon ancak üç nokta çıkarılınca kuruldu (R² = 0,411); bu güçlü bir doğrulama değildir.
- **Dayanak:** Terazono, Sakai ve Takatsuki (2000) özeti (çalışma notu, 27.09.2026); `veri/literatur/kobe_karsilastirma.csv`.

## 2026-09-21: Hasar girdisi ve yöntem ilkeleri
- **Karar:** CSM, MADRS ve CM yöntemlerinin sonuçları ayrı senaryolar olarak tutulur; aralarındaki fark güven aralığı değildir
  (enkaz: 19,10 / 24,02 / 31,89 milyon ton, KRDAE 2019 Tablo 7-2, s.293). Tablo 7-1'deki %100/80/40/10/0 katsayıları mali
  kayba katılım oranıdır, enkaz ya da salım oranı değildir. Hasar ve bina verisi mahalle adıyla değil **UAVT koduyla**
  birleştirilir (959 kayıt tam eşleşiyor; `bina2017` dosyasında "19 MAYIS" adı "19.May" olarak bozulmuş).
  PM ölçümleriyle sınama, asbest katsayılarını doğrulamaz.
- **Dayanak:** KRDAE 2019 (`krdae2019`), İBB açık veri CSV'leri; sunum ve araştırma notu (21.09.2026).
