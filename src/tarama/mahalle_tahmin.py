"""İlçe verisini mahallelere dağıtma (model tahmini, veri değil) → ciktilar/tarama/mahalle_tahmin.csv

Yöntem (dasimetrik dağıtım): Bir yılda ilçede asbest tespit edilen bina sayısı (ve tonaj),
o yılın mahalle bazlı bir faaliyet göstergesine orantılı dağıtılır.
  - Kadıköy: gösterge = mahalle bazlı riskli yapı tespiti (Kadıköy açık veri, 2012-2022);
    asbest serisi = Kadıköy açık veri (2015-2025). Ortak dönem: 2015-2022.
  - Maltepe: gösterge = mahalle bazlı asbest denetim sayısı (2016 ve 2019 faaliyet raporları);
    o yılın ilçe tespit oranı her mahalleye uygulanır.
Varsayım: aynı yıl içinde tespit olasılığı mahalleler arasında eşittir. Bu varsayım bina yaşı
farkları nedeniyle bozulabilir; bağlam için İBB 2017 mahalle bina yaşı verisi (1980 öncesi pay) eklenir.
Riskli yapı tespiti ile yıkım arasında 1-3 yıl gecikme olabilir; tahmin bu nedenle kabadır.
"""
from __future__ import annotations

import csv

from common import OUT, RAW, fold, tr_lower, write_csv
from veri_noktalari import KADIKOY, MALTEPE_MAH_2016, MALTEPE_MAH_2019


def ibb_age() -> dict[tuple[str, str], dict]:
    out = {}
    with open(RAW / "ibb" / "mahalle_bina_2017.csv", encoding="iso-8859-9") as f:
        for r in csv.DictReader(f, delimiter=";"):
            tot = sum(int(r[k] or 0) for k in ("1980_oncesi", "1980-2000_arasi", "2000_sonrasi"))
            out[(fold(r["ilce_adi"]), key(r["mahalle_adi"]))] = {
                "bina_2017": tot, "oncesi_1980": int(r["1980_oncesi"] or 0),
                "pay_1980_oncesi": round(int(r["1980_oncesi"] or 0) / tot, 3) if tot else ""}
    return out


def key(m: str) -> str:
    k = fold(m).replace(" mahallesi", "").strip()
    return {"b.bakkalkoy": "buyukbakkalkoy", "19.may": "19 mayis", "kucukyali merkez": "kucukyali"}.get(k, k)


def tr_title(s: str) -> str:
    out = []
    for w in tr_lower(s).split(" "):
        out.append(({"i": "İ", "ı": "I"}.get(w[:1], w[:1].upper()) + w[1:]) if w else w)
    return " ".join(out)


def main() -> None:
    age = ibb_age()
    rows = []
    # --- Kadıköy ---
    rk = list(csv.DictReader(open(RAW / "kadikoy" / "riskli_yapi_mahalle_2012_2022.csv", encoding="utf-8-sig"),
                             delimiter=";"))
    rk = [r for r in rk if r["Mahalle"] != "TOPLAM"]
    years = [y for y in range(2015, 2023)]
    tot = {y: sum(int(r[str(y)]) for r in rk) for y in years}
    for r in rk:
        est_b = sum(KADIKOY[y][1] * int(r[str(y)]) / tot[y] for y in years if tot[y])
        est_t = sum(KADIKOY[y][2] * int(r[str(y)]) / tot[y] for y in years if tot[y])
        a = age.get(("kadikoy", key(r["Mahalle"])), {})
        rows.append({"ilce": "Kadıköy", "mahalle": tr_title(r["Mahalle"]), "donem": "2015-2022",
                     "gosterge_kaynagi": "riskli yapı tespiti (Kadıköy açık veri)",
                     "gosterge_toplam": sum(int(r[str(y)]) for y in years),
                     "tahmini_asbestli_bina": round(est_b, 1), "tahmini_ton": round(est_t, 1),
                     "toplam_yapi": r["Toplam_Yapi"],
                     "bin_yapida_tahmini_asbestli": round(1000 * est_b / int(r["Toplam_Yapi"]), 1),
                     "pay_1980_oncesi_ibb2017": a.get("pay_1980_oncesi", ""), "uyari": "model tahmini"})
    # --- Maltepe ---
    for tablo, yil, denetim, pozitif in ((MALTEPE_MAH_2016, 2016, 514, 120), (MALTEPE_MAH_2019, 2019, 195, 20)):
        oran = pozitif / denetim
        for mah, v in tablo.items():
            a = age.get(("maltepe", key(mah)), {})
            rows.append({"ilce": "Maltepe", "mahalle": mah, "donem": str(yil),
                         "gosterge_kaynagi": "mahalle asbest denetim sayısı (faaliyet raporu)",
                         "gosterge_toplam": "" if v is None else v,
                         "tahmini_asbestli_bina": "" if v is None else round(v * oran, 1), "tahmini_ton": "",
                         "toplam_yapi": a.get("bina_2017", ""), "bin_yapida_tahmini_asbestli": "",
                         "pay_1980_oncesi_ibb2017": a.get("pay_1980_oncesi", ""),
                         "uyari": f"model tahmini; ilçe tespit oranı %{oran * 100:.1f} uygulandı"})
    write_csv(OUT / "mahalle_tahmin.csv", rows, list(rows[0].keys()))
    print(f"{len(rows)} satır")
    for r in sorted([r for r in rows if r["ilce"] == "Kadıköy"], key=lambda r: -r["tahmini_asbestli_bina"])[:8]:
        print(f"  {r['mahalle']:<14} tahmini {r['tahmini_asbestli_bina']:>6} bina, {r['tahmini_ton']:>6} t, "
              f"binde {r['bin_yapida_tahmini_asbestli']}, 1980 öncesi pay {r['pay_1980_oncesi_ibb2017']}")


if __name__ == "__main__":
    main()
