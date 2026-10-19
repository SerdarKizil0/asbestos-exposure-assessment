"""Excel ve yazı için sonuç tablolarını toplar → model/cikti/sonuclar.json"""
from __future__ import annotations

import json

import numpy as np

from girdiler import kadikoy_asbest, kur as mahalle_tablosu
from model import CALISMA_PAYI, P, aktarimlar, derisim, salim
from ortak import CIKTI, GIRDI
from yayilim import tek_yikim_profili

ARKA_PLAN = (0.19, 0.41)  # lif/L, Kobe 1995 olağan ortam (konut / ana yol), Terazono 2000
KOBE_DEPREM_SONRASI = (1.0, 2.0)  # lif/L, Kobe izleme noktaları Şubat-Haziran 1995
KOBE_SINIR = (160.0, 250.0)  # lif/L, asbesti sökülmeden yıkılan krokidolitli apartmanın parsel sınırı


def tek_yikim():
    """Asbestli tek bir binanın yıkımı: rüzgâr altı eksen derişimi (lif/L)."""
    M, w, k = P["M_acm"][0], P["w_asbest"][0], P["k_lif"][0]
    sure_saat = 40.0  # 4 iş günü makineli yıkım ve yükleme
    durumlar = {
        "Temel (EF %0,01, ıslatma yok)": dict(EF=1e-4, eta=0.0),
        "Gevrek malzeme / kuru kırma (EF %0,1)": dict(EF=1e-3, eta=0.0),
        "Islatmalı yıkım (EF %0,01, %70 tutma)": dict(EF=1e-4, eta=0.7),
    }
    hava = {
        "Poyraz (KD 5,5 m/s, D)": dict(u=5.5, grup="D", L=950.0),
        "Lodos (GB 3,9 m/s, C)": dict(u=3.9, grup="C", L=485.0),
        "Kararlı sabah (1,5 m/s, E-F, 125 m)": dict(u=1.5, grup="EF", L=125.0),
        "Durgun (1 m/s, D, 275 m)": dict(u=1.0, grup="D", L=275.0),
    }
    mesafe = [20, 50, 100, 200, 500, 1000]
    tablo = []
    for dad, d in durumlar.items():
        lif = M * w * d["EF"] * (1 - d["eta"]) * k * 1e12
        Q = lif / (sure_saat * 3600)
        for had, h in hava.items():
            c = tek_yikim_profili(Q, mesafe, h["u"], h["grup"], h["L"]) / 1000.0
            tablo.append({"salim_durumu": dad, "hava": had, "Q_lif_s": Q, "toplam_lif": lif,
                          **{f"{m}_m": float(v) for m, v in zip(mesafe, c)}})
    return {"mesafeler": mesafe, "sure_saat": sure_saat, "tablo": tablo,
            "varsayim": f"Asbestli bina başına {M:.0f} kg asbestli malzeme × %{100*w:.0f} asbest; {k:.0f} lif/ng; {sure_saat:.0f} saatlik yıkım; salım yüksekliği 5 m, ölçüm 1,5 m"}


def topla():
    D, kad, kaynak, kom, senaryolar, iz = aktarimlar()
    mah = mahalle_tablosu()
    md = {d["mahalle"]: d for d in mah}
    du = json.loads((CIKTI / "duyarlilik.json").read_text())
    nK = len(kad)
    N, Q = salim(kaynak, mah, kom)
    cc, cd = derisim(D["temel"], Q)
    _, Qr = salim(kaynak, mah, kom, hasar_dagilimi="riskli yapı")
    cr, _ = derisim(D["temel"], Qr)
    pop = np.array([md[a]["nufus_2025"] for a in kad], float)
    yas = np.array([md[a]["nufus_65_ustu_2024"] for a in kad], float)
    bar = np.array([md[a]["gecici_barinma"] for a in kad], float)
    T = P["T_ay"][0]
    lif_toplam = Q * T * 260 * 3600
    mc = {m["mahalle"]: m for m in du["mc"]["mahalle"]}
    sira = np.argsort(np.argsort(-cc)) + 1
    sira_r = np.argsort(np.argsort(-cr)) + 1
    maruz = cc * pop
    satir = []
    for i, a in enumerate(kad):
        d = md[a]
        satir.append({
            "mahalle": a, "alan_km2": d["alan_km2"], "nufus_2025": d["nufus_2025"], "nufus_65_ustu": d["nufus_65_ustu_2024"],
            "gecici_barinma": d["gecici_barinma"], "pay_1980_oncesi": d["pay_1980_oncesi"],
            "hasar_cok_agir": d["hasar_cok_agir"], "hasar_agir": d["hasar_agir"], "hasar_orta": d["hasar_orta"],
            "yikilan_temel": float(N[i]), "yikim_yogunlugu_km2": float(N[i] / d["alan_km2"]),
            "salinan_lif": float(lif_toplam[i]),
            "c_calisma": float(cc[i]), "c_donem": float(cd[i]), "kumulatif_lif_L_yil": float(cd[i] * T / 12),
            "arka_plana_oran_ust": float(cc[i] / ARKA_PLAN[0]),
            "sira": int(sira[i]), "maruziyet_payi": float(maruz[i] / maruz.sum()),
            "c_kis": du["senaryo"]["kis"]["c"][i], "c_yaz": du["senaryo"]["yaz"]["c"][i],
            "c_S1": du["senaryo"]["S1_poyraz"]["c"][i], "c_S2": du["senaryo"]["S2_lodos"]["c"][i],
            "c_S3": du["senaryo"]["S3_kararli_sabah"]["c"][i], "c_S4": du["senaryo"]["S4_durgun"]["c"][i],
            "c_riskli_yapi": float(cr[i]), "sira_riskli_yapi": int(sira_r[i]),
            "mc_p5": mc[a]["c_p5"], "mc_p50": mc[a]["c_p50"], "mc_p95": mc[a]["c_p95"],
            "mc_ilk5": mc[a]["ilk5_olasiligi"], "mc_sira_p5": mc[a]["sira_p5"], "mc_sira_p95": mc[a]["sira_p95"],
        })
    komsu = [{"kaynak": a, "yikilan": float(N[nK + j]), "Q": float(Q[nK + j])} for j, a in enumerate(kaynak[nK:])]
    out = {"mahalle": satir, "pwm_calisma": float((cc * pop).sum() / pop.sum()),
           "pwm_donem": float((cd * pop).sum() / pop.sum()),
           "kadikoy_yikilan": float(N[:nK].sum()), "komsu_yikilan": float(N[nK:].sum()),
           "kadikoy_lif": float(lif_toplam[:nK].sum()), "komsu_lif": float(lif_toplam[nK:].sum()),
           "komsu_katki_payi": 1 - du["yapisal"][5]["pwm_carpan"],
           "tek_yikim": tek_yikim(), "kadikoy_asbest": kadikoy_asbest(), "arka_plan": ARKA_PLAN,
           "kobe_deprem_sonrasi": KOBE_DEPREM_SONRASI, "kobe_sinir": KOBE_SINIR, "senaryolar": {k: v["ad"] for k, v in senaryolar.items()},
           "calisma_payi": CALISMA_PAYI, "komsu": komsu}
    (CIKTI / "sonuclar.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    o = topla()
    print(f"Kadıköy yıkılan {o['kadikoy_yikilan']:.0f}, komşu {o['komsu_yikilan']:.0f}; lif Kadıköy {o['kadikoy_lif']:.3g}, komşu {o['komsu_lif']:.3g}")
    print(f"pwm çalışma {o['pwm_calisma']:.4g} lif/L, dönem {o['pwm_donem']:.4g}; komşu katkı payı %{100*o['komsu_katki_payi']:.0f}")
    for s in sorted(o["mahalle"], key=lambda s: s["sira"]):
        print(f"{s['sira']:>2} {s['mahalle']:<13} {s['c_calisma']:.4f}  maruziyet %{100*s['maruziyet_payi']:4.1f}  S1 {s['c_S1']:.4f} S2 {s['c_S2']:.4f} S3 {s['c_S3']:.4f} S4 {s['c_S4']:.4f}  MC {s['mc_p5']:.4f}-{s['mc_p95']:.3f}  ilk5 %{100*s['mc_ilk5']:.0f}  riskli-yapı sırası {s['sira_riskli_yapi']}")
    print(o["tek_yikim"]["varsayim"])
    for r in o["tek_yikim"]["tablo"]:
        print(f"  {r['salim_durumu'][:28]:<28} {r['hava'][:28]:<28} " + "  ".join(f"{m}m {r[f'{m}_m']:.3g}" for m in o["tek_yikim"]["mesafeler"]))
