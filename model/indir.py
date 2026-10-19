"""Model girdilerini indirir → veri/ham/{ibb,kadikoy,meteo}

Bütün istekler src/tarama/common.py fetch() üzerinden gider (robots.txt, host başına ≥2 sn, veri/ham/log/istekler.jsonl).

Tek istisna: archive-api.open-meteo.com'un robots.txt dosyası tüm yolları kapatıyor. Burası tarama yapılan bir site
değil, programla kullanılmak üzere belgelenmiş ücretsiz bir API (https://open-meteo.com/en/docs/historical-weather-api);
bu yüzden yalnız bu istek check_robots=False ile yapılır ve günlüğe gerekçesiyle yazılır. İstemezseniz --meteo-yok
verin ve aynı ERA5 verisini Copernicus CDS'ten (hesap gerekir) indirin.

Kullanım:  python3 indir.py [--hedef KLASÖR] [--meteo-yok]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "tarama"))
from common import fetch  # noqa: E402

from ortak import RAW  # noqa: E402

KAD = "https://acikveri.kadikoy.bel.tr/dataset/"
KADIKOY_MODEL = {  # dosya adı: CKAN kaynak adresi (paketler 2026-10-13'te package_show ile bulundu)
    "kadikoy-ilcesindeki-mahalle-sinirlari.shp": KAD + "1f49bf03-cea5-40b9-9604-5f71c6f71e22/resource/c7a8a9dc-c78f-417a-9e2c-42ec4d3436e7/download/mahalle_sinir.shp",
    "mahalle-nufuslarinin-cinsiyete-gore-dagilimi.csv": KAD + "5b0637d0-0188-428f-a88a-93c04e299749/resource/0f1e8f07-6bdd-4115-8fb0-231657411a27/download/mahalle-nufuslarnn-cinsiyete-gore-dalm-2025.csv",
    "65-uzeri-nufusun-mahalle-dagilimlari.csv": KAD + "da28ac0a-78cf-41cf-89b1-dd8bdf379127/resource/ec0b1af9-822d-4017-80b0-dcc4ffc2e08f/download/65-ya-ve-uzeri-nufusun-mahalle-dalm-2024.csv",
    "0-14-yas-cocuk-nufusunun-mahallelere-gore-dagilimi.csv": KAD + "a227a7bf-1760-4d9c-ad5c-259022345091/resource/9dd4b54f-3a76-42c4-9579-aa83f62ad1ac/download/0-14-ya-cocuk-nufusun-mahallelere-gore-dalm-2024.csv",
    "yapim-yillarina-gore-binalarin-mekansal-dagilimi.csv": KAD + "b5acdd59-7caf-4b8d-ac74-6c0b38f25a16/resource/2632008c-8120-4403-8154-9cde1ab7eb39/download/2021_yapm-yllarna-gore-binalarn-mahalle-dalm.csv",
    "kat-sayisina-gore-binalarin-mekansal-dagilimi.csv": KAD + "60e67797-a5b6-438c-9f98-ffac5e16a63f/resource/e22127c6-1ade-4e42-bbe5-45f1e9f60e19/download/2021_kat-saysna-gore-binalarn-mahalle-dalm.csv",
    "insaat-turlerine-gore-binalarin-mekansal-dagilimi.csv": KAD + "f6b24afc-3512-455e-91f1-009da95007a6/resource/a1a00743-45ef-454c-aa16-85cea942f7a3/download/2021_inaat-turlerine-gore-binalarn-mahalle-dalm.csv",
    "mahalle-afet-toplanma-alanlari-miktari.csv": KAD + "7955961c-298a-4121-92d2-c77c53b2783c/resource/9328e758-cc03-4945-a4d9-17381d0e3a8b/download/mahalle_afet_toplanma_alanlari_miktari.csv",
    "mahalle-bazinda-konut-isyeri-dagilimi.csv": KAD + "82e2fa23-0ece-4601-b0dc-a37be013d228/resource/e046563f-70f5-4954-af6e-05de7c67ec6f/download/2022_mahalle-baznda-konut-iyeri-dalm.csv",
}
KADIKOY_DIGER = {
    "asbest_verileri.csv": KAD + "3f35ced9-0900-437e-82a0-51bfc4a2e32f/resource/63f4d582-38bc-4e77-b24d-1bf1e71eb31d/download/asbest_verileri.csv",
    "riskli_yapi_mahalle_2012_2022.csv": KAD + "834a160d-3c0b-42b8-baca-f6b16fe75738/resource/0a8282aa-d1ef-4548-a786-7cb9f1ba109b/download/kadkoy-riskli-yap-tespiti-yaplan-binalarn-mahalle-dalmlar-2012-2022.csv",
}
IBB = ("deprem_senaryosu_analiz_sonuclari.csv",
       "https://data.ibb.gov.tr/dataset/c13514d9-86b1-4b83-a9b9-1a15cb5f254c/resource/9c3ac492-de4b-4245-b418-7ad3df67a193/download/deprem-senaryosu-analiz-sonuclar.csv")
ERA5 = ("era5_kadikoy_2015_2024.json",
        "https://archive-api.open-meteo.com/v1/archive?latitude=40.985&longitude=29.06&start_date=2015-01-01&end_date=2024-12-31"
        "&hourly=wind_speed_10m,wind_direction_10m,shortwave_radiation,cloud_cover,precipitation,boundary_layer_height,temperature_2m"
        "&models=era5&wind_speed_unit=ms&timezone=Europe%2FIstanbul")
ERA5_LISANS = "ERA5 (Copernicus C3S) üzerinden Open-Meteo Historical Weather API; CC BY 4.0, atıf: Open-Meteo.com ve Hersbach ve ark. 2020"


def indir(url: str, yol: Path, **kw) -> dict | None:
    r = fetch(url, timeout=120, purpose="yayılım modeli girdisi", **kw)
    if not r["ok"]:
        print(f"  ALINAMADI {yol.name}: {r.get('durum') or r.get('status')}")
        return None
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(r["content"])
    meta = {"dosya": yol.name, "url": url, "erisim": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(r["content"]).hexdigest(), "bytes": len(r["content"])}
    print(f"  {yol.name}: {meta['bytes']:,} bayt, sha256 {meta['sha256'][:12]}…")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hedef", type=Path, default=RAW)
    ap.add_argument("--meteo-yok", action="store_true")
    a = ap.parse_args()
    h = a.hedef
    m = indir(IBB[1], h / "ibb" / IBB[0])
    if m:
        (h / "ibb" / IBB[0].replace(".csv", ".meta.json")).write_text(json.dumps(m, ensure_ascii=False, indent=1))
    liste = [x for d, u in KADIKOY_MODEL.items() if (x := indir(u, h / "kadikoy" / "model" / d))]
    (h / "kadikoy" / "model" / "indirilenler.json").write_text(json.dumps(liste, ensure_ascii=False, indent=1))
    for d, u in KADIKOY_DIGER.items():
        indir(u, h / "kadikoy" / d)
    if not a.meteo_yok:
        m = indir(ERA5[1], h / "meteo" / ERA5[0], check_robots=False)
        if m:
            m["lisans"] = ERA5_LISANS
            (h / "meteo" / ERA5[0].replace(".json", ".meta.json")).write_text(json.dumps(m, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
