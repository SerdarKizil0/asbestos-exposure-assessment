"""Elle doğrulanmış veri noktaları → veri/dogrulanmis/veri_noktalari.csv

Her satır bir belgede gözle okunmuş bir sayıdır. Bu betik yalnızca kanıtı bağlar:
belgenin indirilmiş kopyasında ifadeyi arar, PDF sayfa numarasını ve kısa alıntıyı ekler.
İfade bulunamazsa satır "KONTROL_ET" olarak işaretlenir.

Yeni veri noktası eklemek için POINTS listesine (ilçe, yıl, gösterge, değer, birim,
URL parçası, arama ifadesi [regex], not) ekleyin.
"""
from __future__ import annotations

import glob
import json
import re
import subprocess
import sys
from pathlib import Path

from common import DOGRULANMIS, RAW, read_seeds, write_csv

SLUG = {x["ilce"]: x["slug"] for x in read_seeds()}

KADIKOY_CSV = ("https://acikveri.kadikoy.bel.tr/dataset/3f35ced9-0900-437e-82a0-51bfc4a2e32f/"
               "resource/63f4d582-38bc-4e77-b24d-1bf1e71eb31d/download/asbest_verileri.csv")
KADIKOY = {  # yıl: (denetlenen inşaat sahası, asbest tespit edilen bina, bertaraf ton)
    2015: (421, 134, 81.3), 2016: (796, 207, 386), 2017: (618, 221, 276.7), 2018: (284, 103, 52.8),
    2019: (144, 21, 17.53), 2020: (158, 23, 23.77), 2021: (186, 27, 50.1), 2022: (251, 17, 92.02),
    2023: (275, 9, 90.72), 2024: (525, 17, 10.4), 2025: (417, 10, 14.45),
}

MALTEPE_MAH_2016 = {"Zümrütevler": 84, "Yalı": 8, "Küçükyalı": 26, "İdealtepe": 31, "Gülsuyu": 11, "Gülensu": 0,
                    "Girne": 41, "Fındıklı": 43, "Feyzullah": 27, "Esenkent": 3, "Çınar": 8, "Cevizli": 95,
                    "Büyükbakkalköy": 0, "Başıbüyük": 0, "Bağlarbaşı": 48, "Aydınevler": 52, "Altıntepe": 22,
                    "Altayçeşme": 15}
MALTEPE_MAH_2019 = {"Zümrütevler": 15, "Yalı": 3, "Küçükyalı": 14, "İdealtepe": 5, "Gülsuyu": 4, "Gülensu": None,
                    "Girne": 6, "Fındıklı": 6, "Feyzullah": 14, "Esenkent": 24, "Çınar": 6, "Cevizli": 43,
                    "Büyükbakkalköy": None, "Başıbüyük": None, "Bağlarbaşı": 21, "Aydınevler": 13,
                    "Altıntepe": 7, "Altayçeşme": 14}

M = "maltepe.bel.tr/upload/strateji/"
POINTS = [
    # --- Maltepe (faaliyet raporları) ---
    ("Maltepe", 2016, "denetlenen bina (Mart-Aralık)", 514, "bina", M + "2016_Faaliyet", r"514 binada", ""),
    ("Maltepe", 2016, "asbest sökümü yaptırılan bina", 120, "bina", M + "2016_Faaliyet", r"120 binada asbest", ""),
    ("Maltepe", 2017, "denetlenen bina", 651, "bina", M + "2017_Faaliyet", r"651 binada", "2019 raporundaki grafikte 641"),
    ("Maltepe", 2017, "asbest sökümü yaptırılan bina", 101, "bina", M + "2017_Faaliyet", r"101 binada asbest", ""),
    ("Maltepe", 2018, "denetlenen bina", 256, "bina", M + "2018_Faaliyet", r"256 binada", "PDF yazı tipi bozuk; metin okunabilir"),
    ("Maltepe", 2018, "asbest sökümü yaptırılan bina", 41, "bina", M + "2018_Faaliyet", r"41 binada asbest", ""),
    ("Maltepe", 2019, "denetlenen bina", 195, "bina", M + "2019_Faaliyet", r"195\s+binada", ""),
    ("Maltepe", 2019, "asbest sökümü yaptırılan bina", 20, "bina", M + "2019_Faaliyet", r"20 binada asbest", ""),
    ("Maltepe", 2020, "asbest denetimi", 152, "adet", M + "2020_Faaliyet", r"2020 Yılında 152 Adet", ""),
    ("Maltepe", 2020, "asbest tespit edilen bina", 30, "bina", M + "2020_Faaliyet", r"30 binanın", ""),
    ("Maltepe", 2021, "asbest denetimi", 281, "adet", M + "2021_Faaliyet", r"Asbest Denetimi Yapmak; 2019 Yılında 195", "cümle 2019-2021 serisini verir"),
    ("Maltepe", 2021, "asbest tespit edilen bina", 26, "bina", M + "2021_Faaliyet", r"26 adet binada", ""),
    ("Maltepe", 2022, "asbest denetimi", 280, "adet", M + "2022_Faaliyet", r"2022\s+Yılında 280 adet", ""),
    ("Maltepe", 2022, "asbest tespit edilen bina", 12, "bina", M + "2022_Faaliyet", r"12 binada tespit", ""),
    ("Maltepe", 2023, "asbest denetimi", 309, "adet", "maltepe.bel.tr/upload/files/2023%20Y", r"Asbest Denetimi Sayısı Adet 440,00 309,00", "performans tablosu"),
    ("Maltepe", 2023, "asbest tespit edilen bina", 4, "bina", "maltepe.bel.tr/upload/files/2023%20Y", r"4 adet binada tespit", ""),
    ("Maltepe", 2024, "asbest denetimi", 256, "adet", M + "2024YiliFaaliyet", r"256 Adet olarak", ""),
    ("Maltepe", 2024, "asbest tespit edilen bina", 7, "bina", M + "2024YiliFaaliyet", r"7 adet binada", ""),
    ("Maltepe", 2025, "asbest denetimi", 367, "adet", "Maltepe%20Belediyesi%202025", r"367 adet binada", "tespit sayısı verilmemiş"),
    # --- Bağcılar ---
    ("Bağcılar", 2017, "asbest kontrolü yapılan yapı (Eylül'den itibaren)", 70, "yapı", "faaliyetraporu_2017", r"70 tane yapıda", ""),
    ("Bağcılar", 2017, "asbest tespit edilen yapı", 15, "yapı", "faaliyetraporu_2017", r"15 tane yapıda asbest", ""),
    ("Bağcılar", 2018, "asbest kontrolü yapılan yapı", 161, "yapı", "faaliyetraporu2018.pdf", r"161 yapıda", ""),
    ("Bağcılar", 2018, "asbest tespit edilen yapı", 41, "yapı", "faaliyetraporu2018.pdf", r"41 yapıda ise asbest", ""),
    ("Bağcılar", 2019, "asbest kontrolü yapılan yapı", 187, "yapı", "bb_faaliyetraporu2019", r"187 yapıda", ""),
    ("Bağcılar", 2019, "asbest tespit edilen yapı", 47, "yapı", "bb_faaliyetraporu2019", r"47 yapıda asbest", ""),
    ("Bağcılar", 2020, "asbest kontrolü yapılan yapı", 110, "yapı", "bb_faaliyetraporu2020", r"110 tane yapıda", ""),
    ("Bağcılar", 2020, "asbest tespit edilen yapı", 27, "yapı", "bb_faaliyetraporu2020", r"27 yapıda asbest", ""),
    ("Bağcılar", 2021, "asbest kontrolü yapılan yapı", 270, "yapı", "bb_faaliyetraporu2021", r"270 yapıda", ""),
    ("Bağcılar", 2021, "asbest tespit edilen yapı", 61, "yapı", "bb_faaliyetraporu2021", r"61 yapıda asbest", ""),
    ("Bağcılar", 2022, "asbest kontrolü yapılan yapı", 219, "yapı", "bb_faaliyetraporu2022", r"219 yapıda", ""),
    ("Bağcılar", 2022, "asbest tespit edilen yapı", 62, "yapı", "bb_faaliyetraporu2022", r"62 yapıda asbest", ""),
    ("Bağcılar", 2022, "bertaraf edilen asbestli malzeme", 72996, "kg", "bb_faaliyetraporu2022", r"72\.996 kg", ""),
    ("Bağcılar", 2023, "asbest kontrolü yapılan yapı", 235, "yapı", "bb_faaliyetraporu2023", r"235 yapıda", ""),
    ("Bağcılar", 2023, "asbest tespit edilen yapı", 25, "yapı", "bb_faaliyetraporu2023", r"25 yapıda asbest", ""),
    ("Bağcılar", 2023, "bertaraf edilen asbestli malzeme", 21190, "kg", "bb_faaliyetraporu2023", r"21\.190 kg", ""),
    ("Bağcılar", 2024, "asbest kontrolü yapılan yapı", 198, "yapı", "bb_faaliyetraporu2024", r"198 yapı denetimi", ""),
    ("Bağcılar", 2024, "asbest tespit edilen yapı", 22, "yapı", "bb_faaliyetraporu2024", r"22 yapıda asbest", ""),
    ("Bağcılar", 2024, "bertaraf edilen asbestli malzeme", 78550, "kg", "bb_faaliyetraporu2024", r"78\.550 kg", ""),
    ("Bağcılar", 2025, "asbest kontrolü yapılan yapı", 504, "yapı", "bb_faaliyetraporu2025", r"504 yapıda", ""),
    ("Bağcılar", 2025, "asbest tespit edilen yapı", 44, "yapı", "bb_faaliyetraporu2025", r"44 yapıda asbest", ""),
    ("Bağcılar", 2025, "bertaraf edilen asbestli malzeme", 37199, "kg", "bb_faaliyetraporu2025", r"37\.199 kg", ""),
    # --- Kağıthane ---
    ("Kağıthane", 2019, "asbest envanter raporu hazırlanan bina", 16, "bina", "2019_yili_faaliyet", r"16 bina için asbest", ""),
    ("Kağıthane", 2019, "sökülen asbestli malzeme", 22, "ton", "2019_yili_faaliyet", r"22 ton asbestli", ""),
    ("Kağıthane", 2020, "asbest envanter raporu hazırlanan bina", 268, "bina", "2020-Faaliyet-Raporu", r"268 binaya", ""),
    ("Kağıthane", 2020, "sökülen asbestli malzeme", 34, "ton", "2020-Faaliyet-Raporu", r"34 ton asbestli", "2024 raporundaki grafikte 11 ton: çelişki"),
    ("Kağıthane", 2021, "asbest envanter raporu hazırlanan bina", 420, "bina", "2021-Faaliyet-Raporu", r"420 binaya", "aynı raporun performans tablosunda '41 Asbest Denetimi'"),
    ("Kağıthane", 2021, "sökülen asbestli malzeme", 50, "ton", "2021-Faaliyet-Raporu", r"50 ton asbestli", "2024 raporundaki grafikte 11 ton: çelişki"),
    ("Kağıthane", 2022, "asbest envanter raporu hazırlanan bina", 175, "bina", "2022-Faaliyet-Raporu", r"175 binaya", ""),
    ("Kağıthane", 2022, "sökülen asbestli malzeme", 21.77, "ton", "2022-Faaliyet-Raporu", r"21 ton 770 kg", ""),
    ("Kağıthane", 2023, "asbest envanter raporu hazırlanan bina", 146, "bina", "Faaliyet-Raporu-2023", r"146 binaya", ""),
    ("Kağıthane", 2023, "sökülen asbestli malzeme", 15, "ton", "Faaliyet-Raporu-2023", r"15 ton asbestli", "yaklaşık"),
    ("Kağıthane", 2024, "asbest envanter raporu hazırlanan bina", 141, "bina", "Faaliyet-Raporu-2024", r"141 binaya", ""),
    ("Kağıthane", 2024, "sökülen asbestli malzeme", 15.68, "ton", "Faaliyet-Raporu-2024", r"15 ton 680 Kg", ""),
    ("Kağıthane", 2025, "asbest envanter raporu hazırlanan bina", 174, "bina", "Faaliyet-Raporu-2025", r"174 bina için", ""),
    ("Kağıthane", 2025, "bertaraf edilen asbest içerikli malzeme", 31, "ton", "Faaliyet-Raporu-2025", r"31 ton asbest", "hedef 13 ton"),
    # --- Ataşehir ---
    ("Ataşehir", 2017, "asbest araştırması yapılan bina", 161, "bina", "2017-faaliyet-raporu-946af710", r"161 binada asbest", "113 dosya"),
    ("Ataşehir", 2017, "asbest tespit edilen bina", 27, "bina", "2017-faaliyet-raporu-946af710", r"27 binada asbeste", ""),
    ("Ataşehir", 2017, "bertaraf edilen asbestli malzeme", 6972, "kg", "2017-faaliyet-raporu-946af710", r"6972 kg", ""),
    ("Ataşehir", 2018, "asbest araştırması yapılan bina", 57, "bina", "faaliyet-raporu-ed3f8463", r"57 binada asbest", "45 dosya"),
    ("Ataşehir", 2018, "asbest tespit edilen bina", 11, "bina", "faaliyet-raporu-ed3f8463", r"11 binada asbeste", ""),
    ("Ataşehir", 2018, "bertaraf edilen asbestli malzeme", 7930, "kg", "faaliyet-raporu-ed3f8463", r"7930 kg", ""),
    ("Ataşehir", 2019, "asbest araştırması yapılan bina", 69, "bina", "faaliyet-raporu-f9ecdee8", r"69 binada asbest", ""),
    ("Ataşehir", 2019, "asbest tespit edilen bina", 7, "bina", "faaliyet-raporu-f9ecdee8", r"7 binada asbeste", ""),
    ("Ataşehir", 2019, "bertaraf edilen asbestli malzeme", 4000, "kg", "faaliyet-raporu-f9ecdee8", r"4 ton asbestli", ""),
    ("Ataşehir", 2020, "asbest araştırması yapılan adres", 58, "adres", "faaliyet-raporu-e6ca4427", r"58 adreste", "tespit sayısı verilmemiş"),
    ("Ataşehir", 2020, "bertaraf edilen asbestli malzeme", 3899, "kg", "faaliyet-raporu-e6ca4427", r"3899 kg", ""),
    ("Ataşehir", 2021, "asbest araştırması yapılan adres", 124, "adres", "faaliyet-raporu-4b64c029", r"124 adreste", ""),
    ("Ataşehir", 2021, "bertaraf edilen asbestli malzeme", 5922, "kg", "faaliyet-raporu-4b64c029", r"5922 kg", ""),
    ("Ataşehir", 2023, "asbest araştırması yapılan adres", 119, "adres", "faaliyet-raporu-496bde90", r"119 adreste", ""),
    ("Ataşehir", 2023, "toplanan asbestli malzeme", 3444, "kg", "faaliyet-raporu-496bde90", r"3\s*\.\s*444 kg", ""),
    ("Ataşehir", 2024, "asbest araştırması yapılan adres", 127, "adres", "faaliyet-raporu-e11b5ce2", r"127 adreste", ""),
    ("Ataşehir", 2024, "toplanan asbestli malzeme", 3195, "kg", "faaliyet-raporu-e11b5ce2", r"3\.195 kg", ""),
    ("Ataşehir", 2025, "asbest araştırması yapılan adres", 150, "adres", "faaliyet-raporu-d36dccac", r"150 adreste", ""),
    ("Ataşehir", 2025, "toplanan asbestli malzeme", 1100, "kg", "faaliyet-raporu-d36dccac", r"1\s*\.\s*100 kg", ""),
    # --- Avcılar ---
    ("Avcılar", 2020, "asbest yönetimi yapılan bina (15.06.2020 itibarıyla, kümülatif)", 218, "bina", "2020-yili-faaliyet-raporu_9477", r"218 adet bina", "14 binadan ort. 15 ton"),
    ("Avcılar", 2021, "asbest yönetimi yapılan bina", 698, "bina", "2021-yili-faaliyet-raporu_9693", r"698 adet binada", ""),
    ("Avcılar", 2021, "uzaklaştırılan asbestli malzeme", 17, "ton", "2021-yili-faaliyet-raporu_9693", r"17 ton asbestli", "ortalama"),
    ("Avcılar", 2022, "asbest yönetimi yapılan bina", 126, "bina", "2022-yili-faaliyet-raporu_9241", r"126 adet binada", ""),
    ("Avcılar", 2022, "uzaklaştırılan asbestli malzeme", 600, "kg", "2022-yili-faaliyet-raporu_9241", r"600 kg asbestli", "yaklaşık"),
    ("Avcılar", 2023, "asbest yönetimi yapılan bina", 92, "bina", "2023-yili-faaliyet-raporu_2379", r"92 adet binada", ""),
    ("Avcılar", 2024, "asbest yönetimi yapılan bina", 167, "bina", "2024-yili-faaliyet-raporu_369", r"167 adet binada", ""),
    ("Avcılar", 2025, "asbest yönetimi yapılan bina", 630, "bina", "2025-yili-faaliyet-raporu_6729", r"630 adet binada", ""),
    # --- Büyükçekmece ---
    ("Büyükçekmece", 2022, "denetlenen yapı", 131, "yapı", "2022-faaliyet-raporu-553e58e7", r"Denetlenen Yapı Sayısı 131", ""),
    ("Büyükçekmece", 2022, "asbest tespit edilen yapı", 3, "yapı", "2022-faaliyet-raporu-553e58e7", r"Tespit Edilen Yapı Sayısı 3", ""),
    ("Büyükçekmece", 2022, "uzaklaştırılan atık", 700, "kg", "2022-faaliyet-raporu-553e58e7", r"Miktarı \(kg\) 700", ""),
    ("Büyükçekmece", 2023, "denetlenen yapı", 156, "yapı", "2023-faaliyet-raporu-e69d1fc6", r"Denetlenen Yapı Sayısı 156", ""),
    ("Büyükçekmece", 2023, "asbest tespit edilen yapı", 1, "yapı", "2023-faaliyet-raporu-e69d1fc6", r"Tespit Edilen Yapı Sayısı 1", ""),
    ("Büyükçekmece", 2023, "uzaklaştırılan atık", 700, "kg", "2023-faaliyet-raporu-e69d1fc6", r"Miktarı \(kg\) 700", "2022 ile aynı değer"),
    ("Büyükçekmece", 2024, "incelenen yapı (asbest görüşü)", 157, "yapı", "2024-faaliyet-raporu-aee904e1", r"157 adet yapı", ""),
    ("Büyükçekmece", 2025, "incelenen yapı (asbest görüşü)", 130, "yapı", "2025-faaliyet-raporu-714a5680", r"130 adet yapı", ""),
    # --- Eyüpsultan ---
    ("Eyüpsultan", 2025, "asbest dosyası değerlendirmesi", 143, "dosya", "Belediyesi%202025%20Y%C4%B1l%C4%B1", r"143 adet asbest dos", "tespit/tonaj verilmemiş"),
    # --- Beşiktaş (raporlar r2web.besiktasplus.app adresinde; ikinci turda bulundu) ---
    ("Beşiktaş", 2020, "asbest denetimi (yıkım öncesi)", 37, "adet", "2020_yili_faaliyet_raporu", r"37 adet asbest denetimi", "tespit/miktar verilmemiş"),
    ("Beşiktaş", 2021, "asbest denetimi (yıkım öncesi)", 69, "adet", "2021_yili_faaliyet_raporu", r"69 adet asbest denetimi", ""),
    ("Beşiktaş", 2021, "asbestli malzeme tespit edilen nokta", 21, "nokta", "2021_yili_faaliyet_raporu", r"21 noktada", ""),
    ("Beşiktaş", 2021, "bertaraf edilen asbestli malzeme", 159857, "kg", "2021_yili_faaliyet_raporu", r"159\.857 kg", ""),
    ("Beşiktaş", 2021, "asbest mühendislik denetim ücreti tahsilatı", 279416.93, "TL", "2021_yili_faaliyet_raporu", r"279\.416,93 TL", ""),
    ("Beşiktaş", 2022, "asbest denetimi yapılan bina", 212, "bina", "2022_yili_faaliyet_raporu", r"212 binada asbest denetimi", "tespit sayısı verilmemiş"),
    ("Beşiktaş", 2022, "bertaraf edilen asbestli malzeme", 10026, "kg", "2022_yili_faaliyet_raporu", r"10026 kg", ""),
    ("Beşiktaş", 2022, "asbest mühendislik denetim ücreti tahsilatı", 411299.99, "TL", "2022_yili_faaliyet_raporu", r"411\.299,99 TL", ""),
    ("Beşiktaş", 2023, "asbest denetimi yapılan bina", 777, "bina", "2023_yili_faaliyet_raporu", r"777 binada asbest denetimi", "Şubat 2023 depremleri sonrası sıçrama; tespit sayısı verilmemiş"),
    ("Beşiktaş", 2023, "bertaraf edilen asbestli malzeme", 302055, "kg", "2023_yili_faaliyet_raporu", r"302\.055,00 kg", "önceki ve sonraki yılların 30-50 katı; belediyeye teyit ettirilmeli"),
    ("Beşiktaş", 2024, "asbest denetimi yapılan bina", 118, "bina", "2024YiliFaaliyetRaporu", r"118 binada asbest denetimi", ""),
    ("Beşiktaş", 2024, "bertaraf edilen asbestli malzeme", 6370, "kg", "2024YiliFaaliyetRaporu", r"6\.370\s?kg", ""),
    ("Beşiktaş", 2025, "bertarafa gönderilen asbestli malzeme (yıl; performans tablosu, hedef 4.500)", 10160, "kg", "3dcc0392-43db", r"10\.160", "tablo: hedef 4.500, gerçekleşme 10.160, %225"),
    ("Beşiktaş", 2025, "asbest denetimi yapılan bina (yalnız 4. çeyrek)", 48, "bina", "3dcc0392-43db", r"48 binada asbest denetimi", "rapor yalnız 4. çeyreği veriyor; 1.560 kg"),
    # --- Bahçelievler ---
    ("Bahçelievler", 2024, "asbest belgesi (Kentsel Dönüşüm Md. iş tablosu)", 436, "adet", "2024-yili-faaliyet-raporu_4387", r"Asbest Belge 436", "aynı yıl yıkım ruhsatı 436"),
    ("Bahçelievler", 2025, "asbest belgesi (Kentsel Dönüşüm Md. iş tablosu)", 1255, "adet", "2025-yili-faaliyet-raporu_7327", r"Asbest Belge 1255", "aynı yıl yıkım ruhsatı 1100"),
]


# Buluttan açılamayan sitelerde, kullanıcının bilgisayarındaki tarayıcıda (Türkiye IP'si) pdf.js ile okunan
# değerler. PDF'lerin kopyası bu klasörde yok; URL + PDF sayfa no + alıntı elle kaydedildi (13 Ekim 2026).
# Yerelde (Türkiye'den) harvest.py çalıştırılınca bu belgeler de veri/ham altına inecek ve locate() ile doğrulanabilecek.
KR = "https://www.kartal.bel.tr/_Dokumanlar/faaliyet_raporu/"
SI = "https://www.sisli.bel.tr/Content/directorate/document/"
BY25 = "https://www.bayrampasa.bel.tr/isDosyalar/2026/04/21/is_4692.pdf"
TARAYICI = [  # (ilçe, yıl, gösterge, değer, birim, url, pdf sayfası, alıntı, not)
    ("Kartal", 2018, "yıkım öncesi denetlenen yapı (Temmuz-Aralık)", 62, "yapı", KR + "2010-2019/2018_Yili_Faaliyet_Raporu.pdf", 54,
     "2018 yılı Temmuz ayından itibaren yıkılacak 62 yapının tehlikeli ve tehlikesiz atıklar yönünden denetimi", "tespit sayısı bu raporda yok; belediye haberine göre 2018'de 15"),
    ("Kartal", 2020, "yıkım öncesi denetlenen yapı", 325, "yapı", KR + "2020-2029/2020_Yili_Faaliyet_Raporu.pdf", 74,
     "Kartal'da yıkılacak 325 yapının yıkılmadan önce tehlikeli ve tehlikesiz atıklar yönünden denetimi yapılmış", ""),
    ("Kartal", 2020, "asbest tespit edilen yapı", 34, "yapı", KR + "2020-2029/2020_Yili_Faaliyet_Raporu.pdf", 74, "34 yapıda asbest olduğu belirlenmiştir", ""),
    ("Kartal", 2020, "bertaraf edilen asbestli malzeme", 87357, "kg", KR + "2020-2029/2020_Yili_Faaliyet_Raporu.pdf", 74, "87.357 kg asbestli malzemenin bertarafı sağlanmıştır", ""),
    ("Kartal", 2021, "yıkım öncesi denetlenen yapı/site", 359, "yapı", KR + "2020-2029/2021_Yili_Faaliyet_Raporu.pdf", 73, "2021 yılında yıkılacak 359 yapının/sitenin yıkılmadan önce ... denetimi yapılmıştır", ""),
    ("Kartal", 2021, "asbest tespit edilen yapı", 25, "yapı", KR + "2020-2029/2021_Yili_Faaliyet_Raporu.pdf", 73, "25 yapıda asbest olduğu belirlenmiş", ""),
    ("Kartal", 2021, "bertaraf edilen asbestli malzeme", 33370, "kg", KR + "2020-2029/2021_Yili_Faaliyet_Raporu.pdf", 73, "33.370 kg asbestli malzemenin bertarafı sağlanmıştır", ""),
    ("Kartal", 2022, "yıkım öncesi denetlenen yapı/site", 398, "yapı", KR + "2020-2029/2022_Yili_Faaliyet_Raporu.pdf", 70, "2022 yılında yıkılan 398 yapının/sitenin yıkılmadan önce ... denetimi yapılmıştır", ""),
    ("Kartal", 2022, "asbest tespit edilen yapı", 27, "yapı", KR + "2020-2029/2022_Yili_Faaliyet_Raporu.pdf", 70, "27 yapıda asbest olduğu belirlenmiş", ""),
    ("Kartal", 2022, "bertaraf edilen asbestli malzeme", 38970, "kg", KR + "2020-2029/2022_Yili_Faaliyet_Raporu.pdf", 70, "38.970 kg asbestli malzemenin bertarafı sağlanmıştır", ""),
    ("Kartal", 2023, "yıkım öncesi denetlenen yapı/site", 483, "yapı", KR + "2020-2029/2023_Yili_Faaliyet_Raporu.pdf", 67, "2023 yılında yıkılan 483 yapının/sitenin yıkılmadan önce ... denetimi yapılmıştır", ""),
    ("Kartal", 2023, "asbest tespit edilen yapı", 31, "yapı", KR + "2020-2029/2023_Yili_Faaliyet_Raporu.pdf", 67, "31 yapıda asbest olduğu belirlenmiş", ""),
    ("Kartal", 2023, "bertaraf edilen asbestli malzeme", 14900, "kg", KR + "2020-2029/2023_Yili_Faaliyet_Raporu.pdf", 67, "14.900 kg asbestli malzemenin bertaraf edilmesi sağlanmıştır", ""),
    ("Kartal", 2024, "yıkım öncesi denetlenen yapı/site", 453, "yapı", KR + "2020-2029/2024_Yili_Faaliyet_Raporu.pdf", 67, "2023 yılında yıkılan 453 yapının/sitenin ... denetimi yapılmıştır", "2024 raporu ama metinde '2023 yılında' yazıyor; muhtemel kopyala-yapıştır hatası, belediyeye sorulmalı"),
    ("Kartal", 2024, "asbest tespit edilen yapı", 33, "yapı", KR + "2020-2029/2024_Yili_Faaliyet_Raporu.pdf", 67, "33 yapıda asbest olduğu belirlenmiş", ""),
    ("Kartal", 2024, "bertaraf edilen asbestli malzeme", 22719, "kg", KR + "2020-2029/2024_Yili_Faaliyet_Raporu.pdf", 67, "22.719 kg asbestli malzemenin bertaraf edilmesi sağlanmıştır", ""),
    ("Kartal", 2025, "yıkım öncesi denetlenen yapı/site", 772, "yapı", KR + "2020-2029/2025_Yili_Faaliyet_Raporu.pdf", 76, "Tehlikeli-Tehlikesiz Atık Denetimi (Yıkım Öncesi Yapı/Site) 772", "tablo"),
    ("Kartal", 2025, "asbest tespit edilen yapı", 55, "yapı", KR + "2020-2029/2025_Yili_Faaliyet_Raporu.pdf", 76, "Asbest Tespit Edilen Yapı Sayısı 55", "tablo"),
    ("Kartal", 2025, "bertaraf edilen asbestli malzeme", 18035, "kg", KR + "2020-2029/2025_Yili_Faaliyet_Raporu.pdf", 76, "Bertaraf Edilen Asbestli Malzeme Miktarı (Kg.) 18.035", "tablo"),
    ("Şişli", 2018, "denetlenen yapı", 111, "yapı", SI + "file-632677a1.pdf", 61, "Denetlenen Yapı Sayısı ... 111 7 13075", "tablo; 2018 raporu"),
    ("Şişli", 2018, "asbest tespit edilen yapı", 7, "yapı", SI + "file-632677a1.pdf", 61, "Asbest Tespit Edilen Yapı Sayısı ... 7", "tablo"),
    ("Şişli", 2018, "uzaklaştırılan atık", 13075, "kg", SI + "file-632677a1.pdf", 61, "Uzaklaştırılan Atık Miktarı (kg) ... 13075", "tablo"),
    ("Şişli", 2018, "Mayıs 2016'dan rapora kadar denetlenen yapı (kümülatif)", 461, "yapı", SI + "file-632677a1.pdf", 61,
     "toplamda 461 yapının 70'inde 50 tondan fazla asbestli malzemenin bertarafı sağlanmıştır", "denetim Mayıs 2016'da başlamış"),
    ("Şişli", 2018, "Mayıs 2016'dan rapora kadar asbest bulunan yapı (kümülatif)", 70, "yapı", SI + "file-632677a1.pdf", 61,
     "toplamda 461 yapının 70'inde 50 tondan fazla asbestli malzemenin bertarafı", ""),
    ("Şişli", 2020, "denetlenen yapı", 54, "yapı", SI + "file-67339504.pdf", 50, "2020 Yılında Gerçekleştirilen Asbest Denetimleri ... 54 5 1.352", "tablo"),
    ("Şişli", 2020, "asbest tespit edilen yapı", 5, "yapı", SI + "file-67339504.pdf", 50, "Asbest Tespit Edilen Yapı Sayısı ... 5", "tablo"),
    ("Şişli", 2020, "uzaklaştırılan atık", 1352, "kg", SI + "file-67339504.pdf", 50, "Uzaklaştırılan Atık Miktarı (kg) ... 1.352", "tablo"),
    ("Şişli", 2022, "denetlenen yapı", 80, "yapı", SI + "file-f6cc2edf.pdf", 78, "Denetlenen Yapı Sayısı (Adet) 80", "tablo"),
    ("Şişli", 2022, "asbest tespit edilen yapı", 20, "yapı", SI + "file-f6cc2edf.pdf", 78, "Asbest Tespit Edilen Yapı Sayısı (Adet) 20", "tablo"),
    ("Şişli", 2022, "uzaklaştırılan atık", 28950, "kg", SI + "file-f6cc2edf.pdf", 78, "Uzaklaştırılan Atık Miktarı (Kg) 28.950", "tablo"),
    ("Şişli", 2023, "denetlenen yapı", 99, "yapı", SI + "file-a271bfc6.pdf", 68, "Denetlenen Yapı Sayısı 99 adet", "tablo"),
    ("Şişli", 2023, "asbest tespit edilen yapı", 21, "yapı", SI + "file-a271bfc6.pdf", 68, "Asbest Tespit Edilen Yapı Sayısı 21 adet", "tablo"),
    ("Şişli", 2023, "uzaklaştırılan asbestli malzeme", 4396, "kg", SI + "file-a271bfc6.pdf", 68, "Uzaklaştırılan Asbestli Malzeme Miktarı 4.396 kg", "tablo"),
    ("Bayrampaşa", 2025, "yıkım öncesi numune alınan adres", 277, "adres", BY25, 64,
     "yıkım yapılacak olan 277 adreste numune alımı gerçekleştirmiştir", "uygulama 14.02.2025'te başlamış; aylık: Şub 10, Mar 15, Nis 8, May 28, Haz 11, Tem 20, Ağu 24, Eyl 24, Eki 44, Kas 40, Ara 53"),
    ("Bayrampaşa", 2025, "asbest tespit edilen bina", 49, "bina", BY25, 64, "49 adet binada asbest tespit edilmiştir", ""),
    ("Bayrampaşa", 2025, "ayrı toplanıp bertaraf edilen asbestli malzeme", 40500, "kg", BY25, 64,
     "40.500 kg asbestli malzeme ayrı toplanarak ... bertaraf edilmiştir", ""),
]
# Belediye haberi (tarayıcıda okundu). 2019 için Kartal'ın tek kaynağı bu haber; 2019 faaliyet raporunda asbest geçmiyor.
KH = "https://www.kartal.bel.tr/Belediyemiz/Haberler/19267"
HABER = [
    ("Kartal", 2018, "asbest tespit edilen yapı", 15, "yapı", KH, "", "2018'de 15, 2019'da 24, 2020'de 34 olmak üzere toplam 73 yapıda asbest", "haber tarihi sayfada yok (2020 verisi içeriyor)"),
    ("Kartal", 2019, "yıkım öncesi incelenen yapı", 180, "yapı", KH, "", "2018'de 62, 2019'da 180, 2020'de 325 olmak üzere toplam 567 yapının", ""),
    ("Kartal", 2019, "asbest tespit edilen yapı", 24, "yapı", KH, "", "2018'de 15, 2019'da 24, 2020'de 34 olmak üzere toplam 73 yapıda asbest", ""),
]


def locate(fragment: str, pattern: str, ilce: str = "*") -> tuple[str, str, str]:
    for m in glob.glob(str(RAW / SLUG.get(ilce, "*") / "*.meta.json")):
        j = json.load(open(m, encoding="utf-8"))
        if fragment not in j["url"]:
            continue
        pdf = m[:-10] + ".pdf"
        try:
            txt = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, timeout=300).stdout.decode("utf-8", "replace")
        except Exception:
            continue
        for i, page in enumerate(txt.split("\f"), 1):
            flat = re.sub(r"\s+", " ", page)
            mm = re.search(pattern, flat, re.I)
            if mm:
                s = max(0, mm.start() - 90)
                return j["url"], str(i), flat[s:mm.end() + 90].strip()
        return j["url"], "", "KONTROL_ET: ifade bulunamadı"
    return "", "", "KONTROL_ET: belge yok"


def eksik_belgeler() -> list[str]:
    """Kanıtı yerel kopyada aranacak belgelerden (Maltepe mahalle tabloları + POINTS) veri/ham altında olmayanlar.
    TARAYICI ve HABER listelerinin zaten yerel kopyası yok; onlar elle kaydedildiği için denetlenmez."""
    gerekli = [("Maltepe", M + "2016_Faaliyet"), ("Maltepe", M + "2019_Faaliyet")] + [(p[0], p[5]) for p in POINTS]
    eksik = []
    for ilce, frag in dict.fromkeys(gerekli):
        var = False
        for m in glob.glob(str(RAW / SLUG.get(ilce, "*") / "*.meta.json")):
            if frag in json.load(open(m, encoding="utf-8"))["url"] and Path(m[:-10] + ".pdf").is_file():
                var = True
                break
        if not var:
            eksik.append(f"{ilce}: …{frag}")
    return eksik


def main() -> None:
    eksik = eksik_belgeler()
    if eksik:
        sys.exit(f"DURDU: {len(eksik)} belgenin yerel kopyası veri/ham altında yok; "
                 "veri/dogrulanmis/veri_noktalari.csv DEĞİŞTİRİLMEDİ.\n" + "\n".join(f"  - {e}" for e in eksik)
                 + "\nBelgeleri harvest.py ile indirin ya da eski çalışma ortamından veri/ham/ altına kopyalayın.")
    rows = []
    for yil, (saha, bina, ton) in KADIKOY.items():
        for g, v, b in (("denetlenen inşaat sahası", saha, "saha"), ("asbest tespit edilen bina", bina, "bina"),
                        ("bertaraf edilen asbest atığı", ton, "ton")):
            rows.append({"ilce": "Kadıköy", "duzey": "ilçe", "mahalle": "", "yil": yil, "gosterge": g, "deger": v,
                         "birim": b, "kaynak_turu": "açık veri (CSV)", "kaynak_url": KADIKOY_CSV, "sayfa": "",
                         "alinti": "Asbest_Verileri;2015;...;2025", "not": "2026-04-06 güncellemesi"})
    for tablo, yil, src, note in ((MALTEPE_MAH_2016, 2016, M + "2016_Faaliyet", "Mart-Aralık; toplam 514"),
                                  (MALTEPE_MAH_2019, 2019, M + "2019_Faaliyet", "toplam 195; boş = raporda değer yok")):
        url, page, quote = locate(src, r"Zümrütevler", "Maltepe")
        for mah, v in tablo.items():
            rows.append({"ilce": "Maltepe", "duzey": "mahalle", "mahalle": mah, "yil": yil,
                         "gosterge": "asbest denetimi (mahalle)", "deger": "" if v is None else v, "birim": "adet",
                         "kaynak_turu": "faaliyet raporu", "kaynak_url": url, "sayfa": page,
                         "alinti": "MAHALLE BAZLI ASBEST DENETİM SAYISI" if yil == 2019 else "ASBEST DENETİM SAYISI (ADET)",
                         "not": note})
    for ilce, yil, g, v, b, frag, pat, note in POINTS:
        url, page, quote = locate(frag, pat, ilce)
        rows.append({"ilce": ilce, "duzey": "ilçe", "mahalle": "", "yil": yil, "gosterge": g, "deger": v, "birim": b,
                     "kaynak_turu": "faaliyet raporu", "kaynak_url": url, "sayfa": page, "alinti": quote, "not": note})
    for liste, tur in ((TARAYICI, "faaliyet raporu (Türkiye IP'li tarayıcıda okundu; kopya yok)"),
                       (HABER, "belediye haberi (Türkiye IP'li tarayıcıda okundu)")):
        for ilce, yil, g, v, b, url, page, quote, note in liste:
            rows.append({"ilce": ilce, "duzey": "ilçe", "mahalle": "", "yil": yil, "gosterge": g, "deger": v, "birim": b,
                         "kaynak_turu": tur, "kaynak_url": url, "sayfa": str(page), "alinti": quote, "not": note})
    write_csv(DOGRULANMIS / "veri_noktalari.csv", rows, ["ilce", "duzey", "mahalle", "yil", "gosterge", "deger", "birim",
                                                  "kaynak_turu", "kaynak_url", "sayfa", "alinti", "not"])
    bad = [r for r in rows if str(r["alinti"]).startswith("KONTROL_ET")]
    print(f"{len(rows)} veri noktası; kontrol gereken: {len(bad)}")
    for r in bad:
        print("  ", r["ilce"], r["yil"], r["gosterge"], r["alinti"])


if __name__ == "__main__":
    main()
