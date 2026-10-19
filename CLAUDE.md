# CLAUDE.md: asbestos-exposure-assessment

Bitirme projesi ve TÜBİTAK 2209-A başvurusu: Mw 7,5 İstanbul depremi sonrası yıkımlarda asbest lifi yayılımı ve
maruziyeti, Kadıköy örneği. Depo **herkese açıktır** (github.com/SerdarKizil0/asbestos-exposure-assessment).
Genel tanıtım README.md'de, yöntem kararları KARARLAR.md'de. Bu dosya depoda çalışacak Claude Code içindir.

## Kurallar (değişmez)

### Herkese açık depo
- **Telifli belge girmez:** makaleler, KRDAE/Kandilli raporu, ilçe kitapçıkları, tezler, belediye faaliyet raporu PDF'leri,
  bunların metin çıkarımları ve sayfa görüntüleri. Yalnız bağlantı, erişim tarihi, SHA-256 ve varsa arşiv bağlantısı
  `kaynaklar.csv`'ye yazılır.
- **Kişisel veri girmez:** TC kimlik no, telefon, e-posta, kişi adı ve adresi, ekran görüntüleri. Belgelerde rastlarsan
  kullanıcıya bildir. Bina, parsel ve kişi düzeyine inilmez; en ince düzey mahalledir. Literatür künyelerindeki yazar
  adları yayımlanmış künye bilgisidir ve girer.
- **ChatGPT notları ve ham indirmeler girmez:** `gelen/` ve `veri/ham/` `.gitignore`'dadır. Notlar kaynak sayılmaz;
  nottaki bir sayı ancak birincil belgede bulunup `kaynak_id` + yer ile yazıldığında veriye girer.
- **50 MB'tan büyük dosya girmez.** API anahtarı, şifre, `.env`, `.cdsapirc` girmez.
- Commit'ten önce `python src/denetle.py` çalıştır. Kanca `src/kancalar/pre-commit`; klonda bir kez
  `git config core.hooksPath src/kancalar`. Hata varsa commit yapma, `--no-verify` kullanma.
- Commit e-postası GitHub noreply adresidir; üniversite adresi kullanılmaz.

### Tarama botu (`src/tarama/`, asbest-tarama'dan devralındı)
- Her HTTP isteği `src/tarama/common.py` içindeki `fetch()` (büyük dosyada `download()`) üzerinden gider: robots.txt
  kontrolü, host başına ≥2 sn hız sınırı ve `veri/ham/log/istekler.jsonl` günlüğü buradadır. Yeni modüller doğrudan
  `requests` çağırmaz. Tek belgelenmiş istisna: `model/indir.py` içindeki Open-Meteo ERA5 isteği (KARARLAR.md).
- Bot korumasını, CAPTCHA'yı, girişi ya da robots.txt yasağını aşmaya çalışma. Engellenen her durumu günlüğe yaz ve
  kapsam tablosunda "erişilemedi + neden" olarak göster.
- İndirilen her belge `veri/ham/` altında SHA-256 ve erişim zamanıyla (`*.meta.json`) saklanır; **silme**.
- Yayına girecek sayılar otomatik ayıklamadan (`ciktilar/tarama/bulgular.csv`) doğrudan alınmaz. Her veri noktası için
  belge URL'si, sayfa numarası ve kısa alıntı tutulur; gözle doğrulanır (`src/tarama/veri_noktalari.py` POINTS listesi).
- `bulgular.csv` belge bağlamından kişi adı ve kurum telefonu içerebilir: git dışında kalır.

### Veri ve kaynaklar
- **Tek doğruluk kaynağı CSV'dir.** Excel elle düzenlenmez; CSV düzeltilir, Excel yeniden üretilir:
  literatür kitapları `src/excel_uret.py`, tarama kitabı `src/tarama/rapor_xlsx.py`, Kadıköy kitabı
  `src/tarama/kadikoy_xlsx.py`, model kitabı `model/rapor_model_xlsx.py`.
- Belediye veri noktalarının kaynağı `src/tarama/veri_noktalari.py` içindeki POINTS listesidir; CSV onun çıktısıdır.
- Her sayısal satırda kaynak (`kaynak_id` ya da `kaynak_url`) ve yer (sayfa, tablo, bölüm) bulunur. Yeni belge önce
  `kaynaklar.csv`'ye girer (URL, erişim tarihi, SHA-256, lisans, `dagitim`).
- Türetilen değerler (oran, kg/bina, kümülatif toplam, mahalle tahmini) CSV'ye elle yazılmaz; betik hesaplar.
  Model tahminleri `veri/` altına değil `model/cikti/` ya da `ciktilar/` altına gider.
- Model parametresi değişirse `model/model.py` içindeki `P` sözlüğünü, model Excel'inin Parametreler sayfasını,
  `model/README.md`'yi ve gerekiyorsa `veri/parametreler.csv`'yi birlikte güncelle; KARARLAR.md'ye tarihli kayıt düş.
  `denetle.py`, `P` içindeki literatür değerlerinin (EF, k_lif) `parametreler.csv` ile aynı olduğunu kontrol eder.
- Model Excel formüllerinde `-x^2` yazma (Excel'de tekli eksi önce uygulanır, +x² olur); `-0.5*(x)^2` kullan.
- Yöntemle ilgili her karar KARARLAR.md'ye tarih, karar ve dayanakla yazılır.

## Mevcut durum (20 Ekim 2026)

- Depo düzeni kuruldu; asbest-tarama klasörü `src/tarama/`, `model/`, `veri/ham/`, `veri/dogrulanmis/`,
  `ciktilar/tarama/` altına taşındı. Yol sabitleri güncellendi. `kapsam.py`, `mahalle_tahmin.py`, `rapor_xlsx.py`,
  `girdiler.py`, `meteoroloji.py` taşımadan sonra bayt bayt aynı çıktıyı verdi.
- **Ham belediye PDF'leri (yaklaşık 7 GB, 312 belge) bu kopyada yok**; yalnız `veri/ham/{ibb,kadikoy,meteo}` var.
  `veri_noktalari.py` ve `kadikoy_xlsx.py` ham belge eksikse eksikleri listeleyip çıkış kodu 1 ile durur ve hiçbir
  çıktıyı değiştirmez (20.10.2026 eklendi). Belgeler geri gelene kadar CSV'ler olduğu gibi korunur.
- `model/izgara.py` OSM sınırlarını `veri/ham/osm/istanbul-geojson/mahalle_geojson.json`'dan okur (ya da
  `ASBEST_OSM_GEOJSON`); bu dosya yerelde yok, model aktarım matrisleri yeniden hesaplanamaz.
- Literatür kitapları CSV'ye aktarıldı (`src/ilk_aktarim.py`); `excel_uret.py --karsilastir` özgünlerle 0 farklı hücre verdi.
- İBB senaryo CSV'si KRDAE 2019 ile aynı çalışmadan (KARARLAR.md 2026-10-20).
- Literatür değerlerinin hiçbiri birincil belgeyle karşılaştırılmadı (`dogrulandi = hayir`); birincil belgeler depoda yok.
- `kaynaklar.csv`: 135 belge. Erişim tarihi kaydedilmemiş yerel raporlar ve 7 eksik URL "not" sütununda işaretli.

## Sıradaki işler (öncelik sırasıyla)

1. Ham belediye belgelerini geri getir (eski çalışma ortamından kopyala ya da Türkiye'den `harvest.py` ile indir);
   ardından `veri_noktalari.py` ile tüm noktaları yeniden bağla, `belgeler.csv` SHA-256'larıyla karşılaştır.
2. Kartal, Şişli, Bayrampaşa belgelerini indir (`TARAYICI` ve `HABER` listeleri): şu an SHA-256'sız.
3. Literatür parametrelerini birincil belgede doğrula: önce modelde kullanılanlar (Terazono 2000: 0,086 kg/m², %0,01,
   30 lif/ng; Kobe hesap/ölçüm oranı). Belgeyi `gelen/` altına koy, SHA-256'yı `kaynaklar.csv`'ye yaz,
   `dogrulandi = evet` yap.
4. Kadıköy ilçe kitapçığını indir; İBB CSV'sindeki 21 Kadıköy mahallesini mahalle düzeyinde karşılaştır.
5. `kaynaklar.csv`'de eksik URL'leri doldur (OYO 2009, İRAP, Üçüncü 2022 tezi, JSMCWM 2022, AP-42 §13.2.4,
   Asbest Yönetmeliği, Tetik 2024).
6. OSM geojson'u `veri/ham/osm/` altına klonla (commit c9bf151) ve modeli baştan çalıştır; `sonuclar.json` aynı mı bak.
7. Model çıktılarının (mahalle düzeyinde derişim, haritalar) yayımlanıp yayımlanmayacağına karar ver (README etik bölümü).
8. KARARLAR.md'deki proje odağı kaydında `[TARİH]` ve `[GEREKÇE]` yer tutucularını doldur (kullanıcı verecek).
9. Tarama botunun açık işleri: OCR (`ocr.py --dil tur`; Üsküdar 2016–2021, Şile, Tuzla 2023, Sultangazi 2015, Ümraniye),
   `wayback.py --indir`, JavaScript'li site aramaları (Playwright), faaliyet raporu sayfası bulunamayan 5 ilçe
   (Beşiktaş, Beykoz, Çatalca, Güngören, Silivri), meclis kararları, aylık izleme.
10. Bilinen çelişkiler: Kağıthane 2020/2021 tonajı (raporlarda 34/50 t, 2024 grafiğinde 11/11 t); Maltepe 2017 denetim
    sayısı (2017 raporu 651, 2019 grafiği 641); Baran ve ark. 2024/2026 künye farkı; Oral ve ark. 2025 kapsam farkı.

## Kaynak ekleme akışı

1. Belgeyi `fetch()` ya da `download()` ile `veri/ham/<klasör>/` altına indir (meta.json SHA-256 ve erişim zamanını yazar).
   Elle indirilen belge `gelen/` altına konur, SHA-256'sı hesaplanır.
2. `kaynaklar.csv`'ye satır ekle: `kaynak_id` (küçük harf, `yazar2024` ya da `ilce_fr2024`), künye, URL, erişim tarihi,
   SHA-256, lisans, `dagitim` (`yalniz_baglanti` ya da türetilmiş satırların yeri).
3. Sayıyı ilgili CSV'ye `kaynak_id` + yer + kısa alıntıyla yaz (belediye verisinde POINTS listesine).
4. `python src/arsiv_kontrol.py` (mevcut arşiv kopyası), `python src/denetle.py`, gerekirse Excel'i yeniden üret.
