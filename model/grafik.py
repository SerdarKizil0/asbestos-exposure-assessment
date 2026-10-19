"""Yazı ve Excel için grafikler → model/cikti/*.png

Renk: dataviz referans paleti (sıralı mavi rampa; ıraksak mavi↔kırmızı; kategorik 1-4 doğrudan etiketli).
"""
from __future__ import annotations

import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import FancyArrow, Patch
import matplotlib.patheffects as pe
from matplotlib.ticker import FixedLocator, FuncFormatter
from shapely import wkt

from ortak import CIKTI, GIRDI

YUZEY = "#fcfcfb"
MUREKKEP, IKINCIL, SOLUK = "#0b0b0b", "#52514e", "#898781"
IZGARA, EKSEN = "#e1e0d9", "#c3c2b7"
MAVI = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
KAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
IRAK = ("#2a78d6", "#e34948")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": EKSEN, "axes.labelcolor": IKINCIL,
                     "xtick.color": SOLUK, "ytick.color": SOLUK, "text.color": MUREKKEP, "figure.facecolor": YUZEY,
                     "axes.facecolor": YUZEY, "savefig.facecolor": YUZEY})

S = json.loads((CIKTI / "sonuclar.json").read_text())
DU = json.loads((CIKTI / "duyarlilik.json").read_text())
POLY = {a: wkt.loads(w) for a, w in json.load(open(GIRDI / "mahalle_poligon_tm30.json", encoding="utf-8")).items()}
KOMSU = []
try:
    from izgara import kadikoy_poligonlari, komsular
    from shapely.ops import unary_union
    _b = unary_union(list(kadikoy_poligonlari().values()))
    KOMSU = [wkt.loads(k["wkt"]) for k in komsular(_b, 1500)[0]]
except Exception:
    pass


ETIKET_KAYDIR = {"Osmanağa": (120, 150), "Zühtüpaşa": (60, -60), "Dumlupınar": (80, -80), "Fikirtepe": (40, 40)}


def ciz_poligon(ax, g, **kw):
    geoms = getattr(g, "geoms", [g])
    for p in geoms:
        x, y = p.exterior.xy
        ax.fill(x, y, **kw)


def harita(ax, degerler: dict, sinirlar, renkler, baslik, etiket=True, ok=None, alt=None):
    for g in KOMSU:
        ciz_poligon(ax, g, facecolor="#f0efec", edgecolor="#ffffff", linewidth=0.6)
    for ad, g in POLY.items():
        v = degerler[ad]
        i = int(np.clip(np.searchsorted(sinirlar, v, side="right") - 1, 0, len(renkler) - 1))
        ciz_poligon(ax, g, facecolor=renkler[i], edgecolor=YUZEY, linewidth=1.2)
        if etiket:
            c = g.centroid if g.centroid.within(g) else g.representative_point()
            dx, dy = ETIKET_KAYDIR.get(ad, (0, 0))
            koyu = i >= len(renkler) // 2 + 1
            ax.text(c.x + dx, c.y + dy, ad, ha="center", va="center", fontsize=5.6,
                    color="#ffffff" if koyu else MUREKKEP,
                    path_effects=[pe.withStroke(linewidth=1.6, foreground=renkler[i])])
    minx, miny, maxx, maxy = (417000, 4535300, 425300, 4542500)
    ax.set_xlim(minx, maxx); ax.set_ylim(miny, maxy)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(baslik, fontsize=9, color=MUREKKEP, loc="left", pad=4)
    if ok is not None:  # rüzgârın geldiği yön (derece) → okun gittiği yön
        git = math.radians((ok + 180) % 360)
        x0, y0 = maxx - 1100, maxy - 1100
        dx, dy = 700 * math.sin(git), 700 * math.cos(git)
        ax.add_patch(FancyArrow(x0 - dx / 2, y0 - dy / 2, dx, dy, width=60, head_width=260, head_length=260,
                                color=IKINCIL, length_includes_head=True))
    if alt:
        ax.text(minx + 150, miny + 150, alt, fontsize=6.5, color=IKINCIL, va="bottom")


def lejant(fig, sinirlar, renkler, baslik, konum):
    etiketler = []
    for i in range(len(renkler)):
        a, b = sinirlar[i], sinirlar[i + 1] if i + 1 < len(sinirlar) else None
        etiketler.append(f"{a:g}–{b:g}" if b is not None else f"{a:g} ve üstü")
    h = [Patch(facecolor=r, edgecolor="none", label=e) for r, e in zip(renkler, etiketler)]
    fig.legend(handles=h, title=baslik, loc=konum, frameon=False, fontsize=7, title_fontsize=7.5, ncol=len(h))


def endeks(c):
    tmax = max(S["mahalle"], key=lambda s: s["c_calisma"])["c_calisma"]
    return {s["mahalle"]: 100 * s[c] / tmax for s in S["mahalle"]}


def sekil_temel():
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    sin = [0, 30, 45, 60, 75, 90]
    ren = MAVI[1:]
    harita(ax, endeks("c_calisma"), sin, ren,
           "Mw 7,5 sonrası yıkım döneminde göreli asbest lifi artışı (temel durum, en yüksek = 100)")
    fig.text(0.02, 0.115, "Çalışma saatleri ortalaması; ERA5 2015-2024 rüzgârı; komşu ilçe yıkımları dahil. Gri: komşu mahalleler.",
             fontsize=6.8, color=IKINCIL)
    lejant(fig, sin, ren, "Göreli endeks", "lower center")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.14)
    fig.savefig(CIKTI / "harita_temel.png", dpi=220)
    plt.close(fig)


def sekil_meteoroloji():
    fig, axs = plt.subplots(1, 5, figsize=(13.5, 3.6))
    sin = [0, 25, 50, 100, 200, 400]
    ren = MAVI[1:]
    paneller = [("c_calisma", "Uzun dönem ortalaması", None),
                ("c_S1", "Poyraz (KD 5,5 m/s)", 45), ("c_S2", "Lodos (GB 3,9 m/s)", 225),
                ("c_S3", "Kararlı sabah (G 1,5 m/s)", 180), ("c_S4", "Durgun (1 m/s, yön değişken)", None)]
    for ax, (k, b, ok) in zip(axs, paneller):
        harita(ax, endeks(k), sin, ren, b, etiket=False, ok=ok)
    lejant(fig, sin, ren, "Göreli endeks (uzun dönem en yüksek mahalle = 100); aynı ölçek", "lower center")
    fig.suptitle("Aynı yıkımlar, farklı hava: hangi mahalle daha çok etkilenir?", x=0.01, ha="left", fontsize=10.5)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.84, bottom=0.17, wspace=0.04)
    fig.savefig(CIKTI / "harita_meteoroloji.png", dpi=220)
    plt.close(fig)


def sekil_dagilim():
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.6))
    sin = [0, 30, 45, 60, 75, 90]
    ren = MAVI[1:]
    tmax = max(s["c_calisma"] for s in S["mahalle"])
    rmax = max(s["c_riskli_yapi"] for s in S["mahalle"])
    harita(axs[0], {s["mahalle"]: 100 * s["c_calisma"] / tmax for s in S["mahalle"]}, sin, ren,
           "Yıkımlar İBB deprem senaryosuna göre", alt="İBB/KOERİ 2019, Mw 7,5: çok ağır + ağır hasarlı")
    harita(axs[1], {s["mahalle"]: 100 * s["c_riskli_yapi"] / rmax for s in S["mahalle"]}, sin, ren,
           "Yıkımlar kentsel dönüşüm dağılımına göre", alt="Kadıköy riskli yapı tespitleri 2012-2022 oranında")
    lejant(fig, sin, ren, "Göreli endeks (her harita kendi en yükseğine göre)", "lower center")
    fig.suptitle("Sonucu en çok değiştiren varsayım: binalar nerede yıkılacak?", x=0.01, ha="left", fontsize=10.5)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.12, wspace=0.03)
    fig.savefig(CIKTI / "harita_dagilim_karsilastirma.png", dpi=220)
    plt.close(fig)


ETIKET = {
    "EF": "Havaya geçen pay (EF)", "k_lif": "Kütleden lif sayısına dönüşüm", "M_acm": "Bina başına asbestli malzeme",
    "kobe_duzeltme": "Model/ölçüm farkı (Kobe ×5)", "p_asbest": "Binada asbest bulunma olasılığı",
    "f_orta": "Orta hasarlıların yıkılan payı", "hasar_carpani": "Hasarlı bina sayısı (deprem)",
    "T_ay": "Yıkım süresi (ortalamayı değiştirir)", "eta_islatma": "Islatma verimi", "w_asbest": "Malzemedeki asbest oranı",
    "r_sokum": "Yıkımdan önce söküm",
}


def sekil_tornado():
    oat = DU["oat"]
    par = {}
    for o in oat:
        par.setdefault(o["parametre"], {})[o["uc"]] = o
    sira = sorted(par, key=lambda p: max(abs(math.log10(v["pwm_carpan"])) for v in par[p].values()))
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for i, p in enumerate(sira):
        for uc, o in par[p].items():
            f = o["pwm_carpan"]
            renk = IRAK[1] if f > 1 else IRAK[0]
            ax.barh(i, math.log10(f), left=0, height=0.62, color=renk, edgecolor=YUZEY, linewidth=1.5)
            x = math.log10(f)
            ax.text(x + (0.04 if x > 0 else -0.04), i, f"×{f:.2g}".replace(".", ","), va="center",
                    ha="left" if x > 0 else "right", fontsize=7, color=IKINCIL)
    ax.set_yticks(range(len(sira)))
    ax.set_yticklabels([ETIKET[p] for p in sira], fontsize=8, color=MUREKKEP)
    ax.axvline(0, color=EKSEN, linewidth=1)
    ax.set_xlim(-1.45, 1.45)
    ax.set_xticks([-1, -0.5, 0, 0.5, 1])
    ax.set_xticklabels(["×0,1", "×0,3", "×1", "×3", "×10"])
    ax.grid(axis="x", color=IZGARA, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel("İlçe geneli nüfus ağırlıklı derişimin temel duruma göre değişimi (log ölçek)", fontsize=8)
    fig.suptitle("Mutlak düzeyi en çok değiştiren varsayımlar", x=0.02, ha="left", fontsize=10.5)
    ax.set_title("Her varsayım tek başına aralığının ucuna çekildiğinde", loc="left", fontsize=8, color=IKINCIL)
    h = [Patch(color=IRAK[1], label="artırır"), Patch(color=IRAK[0], label="azaltır")]
    ax.legend(handles=h, loc="lower right", frameon=False, fontsize=7.5)
    fig.subplots_adjust(left=0.33, right=0.97, top=0.86, bottom=0.14)
    fig.savefig(CIKTI / "tornado.png", dpi=220)
    plt.close(fig)


def sekil_yakin_alan():
    ty = S["tek_yikim"]
    m = ty["mesafeler"]
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    temel = [r for r in ty["tablo"] if r["salim_durumu"].startswith("Temel")]
    ax.axhspan(S["arka_plan"][0], S["arka_plan"][1], color="#f0efec", zorder=0)
    ax.text(11, math.sqrt(S["arka_plan"][0] * S["arka_plan"][1]), "olağan kent havası (Kobe 1995)", ha="left", va="center", fontsize=6.8, color=IKINCIL)
    ax.axhspan(S["kobe_deprem_sonrasi"][0], S["kobe_deprem_sonrasi"][1], color="#e1e0d9", zorder=0)
    ax.text(11, math.sqrt(S["kobe_deprem_sonrasi"][0] * S["kobe_deprem_sonrasi"][1]), "Kobe, deprem sonrası kent havası", ha="left", va="center", fontsize=6.8, color=IKINCIL)
    adlar = ["Poyraz", "Lodos", "Kararlı sabah", "Durgun"]
    for r, renk, ad in zip(temel, KAT, adlar):
        y = [r[f"{x}_m"] for x in m]
        ax.plot(m, y, color=renk, linewidth=2, marker="o", markersize=4.5, zorder=3)
        ax.text(m[-1] * 1.12, y[-1], ad, ha="left", va="center", fontsize=7.5, color=MUREKKEP)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(9, 2600)
    ax.yaxis.set_major_locator(FixedLocator([0.01, 0.1, 1, 10]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
    ax.set_xticks(m); ax.set_xticklabels([f"{x}" for x in m]); ax.xaxis.set_minor_locator(FixedLocator([]))
    ax.set_xlabel("Yıkımdan rüzgâr altı uzaklık (m)", fontsize=8)
    ax.set_ylabel("Lif/L (artış)", fontsize=8)
    ax.grid(which="major", color=IZGARA, linewidth=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("Asbestli tek bir binanın kontrolsüz yıkımı: rüzgâr altında derişim", loc="left", fontsize=10)
    ax.text(0.0, -0.2, ty["varsayim"] + ".\nGevrek malzeme ya da kuru kırmada (EF %0,1) değerler 10 kat; ıslatmayla %70 düşer. Kobe'de sökümsüz yıkımın parsel sınırı: 160-250 lif/L.",
            transform=ax.transAxes, fontsize=6.5, color=IKINCIL, va="top")
    fig.subplots_adjust(left=0.12, right=0.97, top=0.9, bottom=0.24)
    fig.savefig(CIKTI / "yakin_alan.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    sekil_temel(); sekil_meteoroloji(); sekil_dagilim(); sekil_tornado(); sekil_yakin_alan()
    print("tamam")
