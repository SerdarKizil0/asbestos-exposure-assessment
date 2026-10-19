# Metin ve veri lisansı: CC BY 4.0

© 2026 Serdar Kızılkale

Bu depodaki **kendi yazdığımız metinler** (README.md, KARARLAR.md, CLAUDE.md, veri/README.md ve diğer belgeler)
ve **kendi derlediğimiz veriler** [Creative Commons Atıf 4.0 Uluslararası (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/deed.tr)
lisansı ile yayımlanır. Lisansın bağlayıcı metni: <https://creativecommons.org/licenses/by/4.0/legalcode.tr>

CC BY 4.0 kapsamındaki dosyalar:

- `veri/parametreler.csv`, `veri/literatur/*.csv`: literatürden derlenmiş parametre, ölçüm ve model tabloları.
  Sayılar yayımlanmış çalışmalardan alınmış olgulardır; her satırda kaynağı (`kaynak_id`) ve yeri (bölüm, tablo, sayfa) vardır.
- `veri/dogrulanmis/kapsam_39.csv`, `ciktilar/tarama/*`: 39 ilçe belediyesi taramasının kapsam ve kanıt kayıtları.
- `veri/dogrulanmis/veri_noktalari.csv`: belediye belgelerinden okunmuş sayılar. **Kadıköy satırları** Kadıköy
  Belediyesi açık verisinden geldiği için CC BY-NC 3.0 şartını taşır (aşağıya bakın).
- `kaynaklar.csv`: kaynak kaydı.

**Bu lisansın kapsamı dışında kalanlar** (kendi lisanslarını korur; ayrıntı README.md "Lisans" bölümünde):

| Veri | Lisans |
|---|---|
| Kadıköy Belediyesi Asbest Verileri ve Riskli Yapı verisi, bunlardan türetilen satırlar | CC BY-NC 3.0 (ticari olmayan kullanım) |
| Kadıköy Belediyesi mahalle sınırı, nüfus ve bina verileri | CC BY 4.0 (Kadıköy Belediyesi) |
| İBB açık verisi (`veri/dogrulanmis/ibb_*.csv`) | İBB Açık Veri Lisansı |
| OpenStreetMap'ten türetilen veriler (`model/girdi/komsu_mahalleler.csv`) | ODbL 1.0 |
| ERA5 / Open-Meteo'dan türetilen meteoroloji tabloları | CC BY 4.0 (Copernicus C3S, Open-Meteo) |

Kod MIT Lisansı ile yayımlanır (`LICENSE`).

Atıf önerisi: *Kızılkale, S. (2026). asbestos-exposure-assessment: Mw 7,5 İstanbul depremi sonrası yıkımlarda
asbest lifi yayılımı ve maruziyeti, Kadıköy örneği. https://github.com/SerdarKizil0/asbestos-exposure-assessment*
