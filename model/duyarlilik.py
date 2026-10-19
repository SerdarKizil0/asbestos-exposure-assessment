"""Duyarlılık analizi: tek tek değiştirme (tornado), yapısal seçenekler ve Monte Carlo.

İki ayrı soru:
  1) 'Ne kadar?' — nüfus ağırlıklı ortalama derişim (ilçe geneli) ve en yüksek mahalle derişimi
  2) 'Nerede?'   — mahalle sıralamasının temel duruma benzerliği (Spearman ρ, ilk 5'te kalan mahalle sayısı)
Çarpımsal parametreler (EF, lif dönüşümü, asbest oranı, olasılık, kg/bina, söküm, ıslatma, süre) tüm mahalleleri
aynı oranda değiştirir: 'ne kadar'ı değiştirir, 'nerede'yi değiştirmez.
"""
from __future__ import annotations

import json
import math

import numpy as np
from scipy.stats import spearmanr

from girdiler import kur as mahalle_tablosu
from model import CALISMA_PAYI, P, aktarimlar, derisim, salim
from ortak import CIKTI

RNG = np.random.default_rng(20261014)


def ozet_metrikler(c, pop, temel_c=None):
    pwm = float(np.sum(c * pop) / pop.sum())
    out = {"pwm": pwm, "maks": float(c.max()), "maks_mahalle_index": int(np.argmax(c))}
    if temel_c is not None:
        out["rho"] = float(spearmanr(c, temel_c).statistic)
        ilk5 = set(np.argsort(-temel_c)[:5])
        out["ilk5_kalan"] = int(len(ilk5 & set(np.argsort(-c)[:5])))
    return out


def calistir():
    D, kad, kaynak, kom, senaryolar, iz = aktarimlar()
    mah = mahalle_tablosu()
    md = {d["mahalle"]: d for d in mah}
    pop = np.array([md[a]["nufus_2025"] for a in kad], float)
    nK = len(kad)

    def hesap(ozel=None, Dk="temel", mekansal="tekdüze", hasar="İBB", komsu=True):
        N, Q = salim(kaynak, mah, kom, ozel, mekansal, hasar)
        if not komsu:
            Q = Q.copy(); Q[nK:] = 0
        cc, cd = derisim(D[Dk], Q)
        return cc, N, Q

    temel_cc, temel_N, temel_Q = hesap()
    temel = ozet_metrikler(temel_cc, pop)
    sonuc = {"temel": temel, "mahalleler": kad}

    # --- 1) Tek tek değiştirme (OAT) ---
    oat = []
    for ad, (b, lo, hi, birim, acik, kaynakc, tur) in P.items():
        for etiket, v in (("alt", lo), ("üst", hi)):
            if v == b:
                continue
            cc, _, _ = hesap({ad: v})
            m = ozet_metrikler(cc, pop, temel_cc)
            oat.append({"parametre": ad, "aciklama": acik, "tur": tur, "uc": etiket, "deger": v, "temel_deger": b,
                        "pwm_carpan": m["pwm"] / temel["pwm"], "maks_carpan": m["maks"] / temel["maks"],
                        "rho": m["rho"], "ilk5_kalan": m["ilk5_kalan"]})
    # --- 2) Yapısal seçenekler ---
    yapisal_tanim = [
        ("Meteoroloji: yalnız kış (Ara-Şub) çalışma saatleri", dict(Dk="kis")),
        ("Meteoroloji: yalnız yaz (Haz-Ağu) çalışma saatleri", dict(Dk="yaz")),
        ("Kentsel kararlılık düzeltmesi (E-F → D)", dict(Dk="kentsel_kararlilik")),
        ("Salım yüksekliği 2 m (enkaz yükleme)", dict(Dk="h2")),
        ("Salım yüksekliği 15 m (bina yıkımı)", dict(Dk="h15")),
        ("Komşu ilçelerin yıkımları hariç", dict(komsu=False)),
        ("Asbest olasılığı mahallenin 1980 öncesi bina payına göre", dict(mekansal="1980 öncesi payına göre")),
        ("Hasar dağılımı İBB senaryosu yerine riskli yapı (2012-2022) dağılımına göre", dict(hasar="riskli yapı")),
        ("Orta hasarlıların tamamı yıkılır (f_orta = 1)", dict(ozel={"f_orta": 1.0})),
    ]
    yapisal = []
    for ad, kw in yapisal_tanim:
        cc, _, _ = hesap(**kw)
        m = ozet_metrikler(cc, pop, temel_cc)
        sira = list(np.array(kad)[np.argsort(-cc)[:5]])
        yapisal.append({"secenek": ad, "pwm_carpan": m["pwm"] / temel["pwm"], "maks_carpan": m["maks"] / temel["maks"],
                        "rho": m["rho"], "ilk5_kalan": m["ilk5_kalan"], "ilk5": ", ".join(sira)})

    # --- 3) Kısa süreli meteoroloji senaryoları (temel salım, aynı hava yıkım süresince sürerse) ---
    senaryo = {}
    for s in ("S1_poyraz", "S2_lodos", "S3_kararli_sabah", "S4_durgun"):
        cc, _ = derisim(D[s], temel_Q)
        m = ozet_metrikler(cc, pop, temel_cc)
        senaryo[s] = {"ad": senaryolar[s]["ad"], "c": cc.tolist(), "pwm_carpan": m["pwm"] / temel["pwm"],
                      "maks_carpan": m["maks"] / temel["maks"], "rho": m["rho"], "ilk5_kalan": m["ilk5_kalan"],
                      "ilk5": ", ".join(np.array(kad)[np.argsort(-cc)[:5]])}
    for s in ("kis", "yaz"):
        cc, _ = derisim(D[s], temel_Q)
        senaryo[s] = {"c": cc.tolist()}

    # --- 4) Monte Carlo ---
    n = 4000
    def logu(a, b, k): return np.exp(RNG.uniform(math.log(a), math.log(b), k))
    def tri(a, m, b, k): return RNG.triangular(a, m, b, k)
    def logtri(a, m, b, k): return np.exp(RNG.triangular(math.log(a), math.log(m), math.log(b), k))
    orn = {
        "hasar_carpani": logu(0.5, 2.0, n),
        "f_orta": RNG.uniform(0, 1, n),
        "p_asbest": tri(P["p_asbest"][1], P["p_asbest"][0], P["p_asbest"][2], n),
        "M_acm": logtri(P["M_acm"][1], P["M_acm"][0], P["M_acm"][2], n),
        "w_asbest": tri(0.05, 0.12, 0.25, n),
        "EF": logu(1e-5, 1e-3, n),
        "k_lif": logu(10, 100, n),
        "r_sokum": tri(0, 0, 0.8, n),
        "eta_islatma": tri(0, 0, 0.9, n),
        "T_ay": RNG.uniform(6, 24, n),
        "kobe_duzeltme": logu(1, 5, n),
    }
    Dsec = RNG.choice(["temel", "kentsel_kararlilik", "h2", "h15"], size=n, p=[0.4, 0.2, 0.2, 0.2])
    mek = RNG.choice(["tekdüze", "1980 öncesi payına göre"], size=n)
    has = np.array(["İBB"] * n)  # hasar dağılımı: İBB senaryosu; riskli yapı dağılımı ayrı senaryo olarak raporlanır
    # İBB senaryosu tek bir gerçekleşme: mahalle bazında hasar sayısına bağımsız log-normal gürültü (σ=0,5)
    gurultu = np.exp(RNG.normal(0, 0.5, (n, len(kaynak))))
    C = np.zeros((n, nK))
    for i in range(n):
        oz = {k: float(v[i]) for k, v in orn.items()}
        _, Q = salim(kaynak, mah, kom, oz, mek[i], has[i])
        C[i], _ = derisim(D[Dsec[i]], Q * gurultu[i])
    pwm = (C * pop).sum(1) / pop.sum()
    # toplam maruziyet (lif/L·yıl, dönem ortalaması × süre) — süreden bağımsız
    kum = pwm * CALISMA_PAYI * orn["T_ay"] / 12
    sira = np.argsort(np.argsort(-C, axis=1), axis=1) + 1
    # log-doğrusal regresyonla varyans payları (standartlaştırılmış regresyon katsayısı karesi)
    X, adlar = [], []
    for k, v in orn.items():
        x = np.log(v) if k not in ("f_orta", "r_sokum", "eta_islatma") else v
        if k == "r_sokum":
            x = np.log(1 - v)
        if k == "eta_islatma":
            x = np.log(1 - v)
        if k == "f_orta":
            x = v
        X.append(x); adlar.append(k)
    for ad, arr in (("dağılım: meteoroloji/salım yüksekliği", Dsec), ("dağılım: asbest olasılığı mekânsal", mek)):
        for kat in sorted(set(arr))[1:]:
            X.append((arr == kat).astype(float)); adlar.append(f"{ad} = {kat}")
    X.append(np.log((gurultu[:, :nK] * pop).sum(1) / pop.sum())); adlar.append("mahalle hasar sayısı belirsizliği (gürültü)")
    X = np.array(X).T
    y = np.log(pwm)
    Xs = (X - X.mean(0)) / X.std(0)
    beta, *_ = np.linalg.lstsq(np.c_[np.ones(n), Xs], (y - y.mean()) / y.std(), rcond=None)
    src = beta[1:]
    r2 = 1 - np.sum((y - np.c_[np.ones(n), X] @ np.linalg.lstsq(np.c_[np.ones(n), X], y, rcond=None)[0]) ** 2) / np.sum((y - y.mean()) ** 2)
    pay = src ** 2 / np.sum(src ** 2)
    varyans = sorted([{"girdi": a, "src": float(s), "pay": float(p)} for a, s, p in zip(adlar, src, pay)], key=lambda d: -d["pay"])
    mc = {
        "n": n, "r2_logdogrusal": float(r2),
        "pwm_yuzdelik": {q: float(np.percentile(pwm, q)) for q in (5, 25, 50, 75, 95)},
        "kumulatif_yuzdelik": {q: float(np.percentile(kum, q)) for q in (5, 25, 50, 75, 95)},
        "mahalle": [{"mahalle": kad[j],
                     "c_p5": float(np.percentile(C[:, j], 5)), "c_p50": float(np.percentile(C[:, j], 50)),
                     "c_p95": float(np.percentile(C[:, j], 95)),
                     "sira_medyan": float(np.median(sira[:, j])), "sira_p5": float(np.percentile(sira[:, j], 5)),
                     "sira_p95": float(np.percentile(sira[:, j], 95)), "ilk5_olasiligi": float(np.mean(sira[:, j] <= 5))}
                    for j in range(nK)],
        "varyans": varyans,
    }
    sonuc.update({"oat": oat, "yapisal": yapisal, "senaryo": senaryo, "mc": mc,
                  "temel_c": temel_cc.tolist(), "temel_N": temel_N.tolist(), "temel_Q": temel_Q.tolist(),
                  "kaynak_adlari": kaynak, "pop": pop.tolist()})
    (CIKTI / "duyarlilik.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1))
    return sonuc


if __name__ == "__main__":
    s = calistir()
    t = s["temel"]
    print(f"Temel: nüfus ağırlıklı {t['pwm']:.4g} lif/L, en yüksek {t['maks']:.4g} ({s['mahalleler'][t['maks_mahalle_index']]})")
    print("\nOAT (pwm çarpanı, sıralama ρ, ilk5 kalan):")
    for o in sorted(s["oat"], key=lambda o: -abs(math.log(o["pwm_carpan"]))):
        print(f"  {o['parametre']:<14} {o['uc']:<3} {o['deger']:<10.4g} ×{o['pwm_carpan']:.3g}  ρ={o['rho']:.3f}  ilk5={o['ilk5_kalan']}")
    print("\nYapısal:")
    for y in s["yapisal"]:
        print(f"  {y['secenek']:<75} ×{y['pwm_carpan']:.2f}  maks ×{y['maks_carpan']:.2f}  ρ={y['rho']:.3f}  ilk5={y['ilk5_kalan']}  [{y['ilk5']}]")
    print("\nSenaryolar:")
    for k, v in s["senaryo"].items():
        if "ad" in v:
            print(f"  {k:<18} ×{v['pwm_carpan']:.2f}  maks ×{v['maks_carpan']:.2f}  ρ={v['rho']:.3f}  ilk5={v['ilk5_kalan']}  [{v['ilk5']}]")
    mc = s["mc"]
    print(f"\nMC n={mc['n']} R²(log-doğrusal)={mc['r2_logdogrusal']:.3f}")
    print("  pwm yüzdelikleri:", {k: f"{v:.3g}" for k, v in mc["pwm_yuzdelik"].items()})
    print("  kümülatif (lif/L·yıl):", {k: f"{v:.3g}" for k, v in mc["kumulatif_yuzdelik"].items()})
    for v in mc["varyans"]:
        print(f"  {v['girdi']:<55} pay %{100*v['pay']:.1f}")
    print("  ilk 5'te olma olasılığı:")
    for m in sorted(mc["mahalle"], key=lambda m: -m["ilk5_olasiligi"])[:10]:
        print(f"    {m['mahalle']:<14} %{100*m['ilk5_olasiligi']:.0f}  sıra medyan {m['sira_medyan']:.0f} ({m['sira_p5']:.0f}-{m['sira_p95']:.0f})")
