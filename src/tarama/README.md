# Asbest şeffaflık taraması: İstanbul'un 39 ilçe belediyesi

Amaç: İstanbul'daki 39 ilçe belediyesinin dijital ortamda yayımladığı her türlü asbest verisini (denetim, tespit edilen bina,
bertaraf edilen miktar, mahalle bilgisi) sistematik olarak bulmak. Bir de "yok" diyebilmek için neyin, ne zaman, nasıl
arandığını kanıtlı biçimde kaydetmek. (Özgün adı: asbest-tarama; 20 Ekim 2026'da bu depoya taşındı.)

## Aşamalar

| Aşama | Modül | Ne arar | Çıktı |
|---|---|---|---|
| 1 | `reach.py` | 39 belediyenin sitesine erişim (alan adı, TLS, bot koruması) | `ciktilar/tarama/erisim.csv` |
| 2 | `discover.py` | robots.txt + site haritaları; URL'de asbest geçen sayfalar | `ciktilar/tarama/sitemap_ozet.csv`, `ciktilar/tarama/urls/` |
| 3 | `opendata.py` | CKAN açık veri portalları (ilçeler + İBB), API ile "asbest", "yıkım"… | `ciktilar/tarama/acikveri.csv` |
| 4 | `sitesearch.py` | Sitenin kendi arama kutusunda "asbest" (taban sorguyla karşılaştırmalı) | `ciktilar/tarama/site_arama.csv` |
| 5 | `reports.py` | Faaliyet raporu PDF'lerinin hedefli keşfi | `ciktilar/tarama/faaliyet_raporlari.csv` |
| 6 | `harvest.py` | Aday belgeleri indirir, metni çıkarır, asbest bağlamını ve sayıları ayıklar | `ciktilar/tarama/belgeler.csv`, `bulgular.csv` (git dışı), `veri/ham/` |
| 7 | `wayback.py` | Wayback Machine'de silinmiş/eski asbest sayfaları ve raporlar | `ciktilar/tarama/wayback.csv` |
| 8 | `ocr.py` | Taranmış (metinsiz) PDF'lerde OCR ile asbest araması | `ciktilar/tarama/ocr/`, `bulgular_ocr.csv` (git dışı) |
| — | `veri_noktalari.py` | Elle doğrulanmış sayıların kanıta bağlanması (URL, PDF sayfası, alıntı) | `veri/dogrulanmis/veri_noktalari.csv` |
| — | `kapsam.py` | 39 ilçe için neye bakıldı / ne bulundu / ne kaldı tablosu | `veri/dogrulanmis/kapsam_39.csv` |
| — | `mahalle_tahmin.py` | İlçe verisini mahallelere dağıtan model (Kadıköy, Maltepe) | `ciktilar/tarama/mahalle_tahmin.csv` (git dışı) |
| — | `rapor_xlsx.py` | Hepsini tek Excel kitabında toplar | `ciktilar/excel/asbest_istanbul_ikinci_tur.xlsx` |
| — | `kadikoy_xlsx.py` | Kadıköy açık verisi, faaliyet raporlarındaki malzeme türü dağılımı, tutarlılık kontrolleri | `ciktilar/excel/kadikoy_asbest_verileri.xlsx` |
| — | `sayfa.py` | Doğrulama: indirilmiş bir belgenin belirli sayfasını metin olarak basar | ekrana |
| — | `tarayici_pdf_asbest.js` | Tarayıcı konsolu için: botun erişemediği sitelerde sayfadaki PDF'leri pdf.js ile okuyup asbest arar | konsol |

`ciktilar/tarama/aday_urller_*.txt` dosyalarına elle (ör. arama motoru sonuçları) URL eklenebilir; `harvest.py` hepsini
birlikte işler. Biçim: `ilçe<TAB>url<TAB>başlık`.

Yeni bir veri noktası okuduğunuzda `veri_noktalari.py` içindeki `POINTS` listesine ekleyin; betik ifadeyi belgede bulup
sayfa numarasını ve alıntıyı kendisi bağlar. Ham belgelerden biri `veri/ham/` altında yoksa betik eksikleri listeler,
çıkış kodu 1 ile durur ve `veri_noktalari.csv`'yi değiştirmez. `kadikoy_xlsx.py` de `veri/ham/kadikoy/` altındaki
belgelerden biri eksikse aynı biçimde durur; belge varken bir alıntı bulunamazsa yine durur.

## Kanıt ve kapsam günlüğü

- `veri/ham/log/istekler.jsonl`: yapılan her isteğin zaman damgası, URL'si, HTTP durumu ve hatası. "Bu sitede şu belgeler
  tarandı, asbest geçmiyor" iddiasının dayanağı budur. Git'e girmez.
- `veri/ham/<ilçe>/*.meta.json`: indirilen her belgenin SHA-256 özeti ve erişim zamanı. Belge sonradan silinirse elinizdeki
  kopyanın orijinal olduğunu gösterir. `ciktilar/tarama/belgeler.csv` aynı SHA-256'ları depoda tutar.
- Mevcut arşiv kopyaları: `python src/arsiv_kontrol.py` (`kaynaklar.csv` → `arsiv_url`).

## Çalıştırma

```bash
pip install -r requirements.txt
# pdftotext (poppler-utils) gerekli; taranmış PDF'ler için tesseract + Türkçe dil paketi (tur)
cd src/tarama
python reach.py && python discover.py && python opendata.py && python sitesearch.py
python reports.py && python harvest.py && python harvest.py --sadece-yeni   # ikinci tur: kesilen/büyük dosyalar
python wayback.py --indir && python harvest.py --sadece-yeni                  # yalnızca yerelde
python ocr.py --dil tur                                                       # uzun sürer
python veri_noktalari.py && python kapsam.py && python mahalle_tahmin.py && python rapor_xlsx.py
```

## İlk tur (13 Ekim 2026, bulut ortamı)

- 26/39 siteye erişildi; 355 belge denendi, 312'si indirildi (yaklaşık 7 GB), 100'ünde asbest geçiyor.
- Sayısal asbest verisi yayımlayan 9 belediye: Kadıköy (açık veri, 2015–2025), Maltepe (2016–2025; 2016 ve 2019'da mahalle
  tablosu), Bağcılar (2017–2025), Ataşehir (2017–2025), Kağıthane (2019–2025), Avcılar (2020–2025), Büyükçekmece (2022–2025),
  Bahçelievler (2024–2025), Eyüpsultan (2025).
- Erişilemeyen 13 site: Arnavutköy, Başakşehir, Bayrampaşa, Çekmeköy, Esenler, Esenyurt, Gaziosmanpaşa, Kartal, Pendik,
  Sancaktepe, Sultanbeyli, Şişli, Zeytinburnu (TLS zinciri hatası, yurt dışı IP engeli/zaman aşımı, 403 bot koruması).

## İkinci tur (13 Ekim 2026, Türkiye IP'li tarayıcı)

- Buluttan açılmayan 13 sitenin hepsine kullanıcının tarayıcısından erişildi (bot doğrulaması çıkmadı). Ayrıntı:
  `ciktilar/tarama/turkiye_tarayici_notlar.md`.
- Yeni sayısal veri: Kartal (2018–2025), Şişli (2018, 2020, 2022, 2023; Mayıs 2016–2018 kümülatif 461 yapı / 70 asbestli /
  50+ ton), Bayrampaşa (2025: 277 adres, 49 bina, 40,5 ton, aylık dağılım). Bunlar `veri_noktalari.py` içinde `TARAYICI` ve
  `HABER` listelerinde; PDF kopyaları `veri/ham` altında **yok**. Türkiye'den `harvest.py` çalıştırılınca inecekler; o zaman
  `POINTS` biçimine taşıyıp `locate()` ile doğrulayın.
- Sayısal verisi olan belediye sayısı 12'ye çıktı.

## Bilinen sınırlar

- web.archive.org bulut ortamından erişilemedi; `wayback.py` orada test edilemedi.
- 26 faaliyet raporu taranmış görüntü (yaklaşık 5.600 sayfa: Ümraniye, Üsküdar, Şile, Tuzla 2023, Sultangazi 2015,
  Beyoğlu'nun eski yılları); OCR çalıştırılmadı.
- Beşiktaş, Beykoz, Çatalca, Güngören ve Silivri'de faaliyet raporu sayfası otomatik bulunamadı. Beykoz raporları
  robots.txt'nin kapattığı /api/ yolunda; Güngören'de PDF adresleri JavaScript/GraphQL ile geliyor.
- Sonuçları JavaScript ile yükleyen site aramaları `sonuc_yok_veya_js` olarak işaretlenir; tarayıcı otomasyonuyla bakılmalı.
- robots.txt'nin yasakladığı yollara bot girmez (durum: `robots_engelli`); bu sayfalar tarayıcıda elle açılabilir.
- Sayı ayıklama düzenli ifadeyle yapılır. Yayına girecek her sayı belgenin ilgili sayfasında gözle doğrulanmalıdır.

## Etik ve hukuki çerçeve

Bot kendini dürüst bir User-Agent ile tanıtır, robots.txt'ye uyar, aynı siteye en fazla 2 saniyede bir istek atar. Giriş,
CAPTCHA ya da bot korumasını aşmaya çalışmaz; yalnızca kamuya açık sayfaları ve belgeleri okur. Kişisel veri toplamaz.
User-Agent'a iletişim adresi eklenecekse kişisel değil kurumsal ya da proje adresi kullanın ve bu adresi depoya yazmayın
(ortam değişkeninden okuyun).
