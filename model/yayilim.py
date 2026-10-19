"""Tarama düzeyinde Gauss yayılım hesabı (Briggs kentsel katsayıları).

İki kullanım:
1) Uzun dönem (yıkım dönemi) ortalaması: ISCLT tipi sektör ortalaması; rüzgâr yönü × hız × kararlılık × karışım
   yüksekliği frekans tablosuyla. Komşu sektörler arasında doğrusal yumuşatma.
2) Kısa süreli senaryo: tek bir rüzgâr yönü/hızı/kararlılık/karışım yüksekliği için saatlik Gauss dumanı.

Model doğrusal olduğu için çıktı bir 'aktarım matrisi'dir: D[r, m] = kaynak mahalle m'den birim salımın
(1 lif/s, mahalle karelerine eşit dağıtılmış) alıcı mahalle r'de oluşturduğu ortalama derişim (lif/m³).
Herhangi bir salım senaryosu için C_r = Σ_m D[r, m] × Q_m.

Kısıtlar (tarama modeli): bina gövdeleri ve sokak kanyonları, deniz meltemi, arazi, ıslak/kuru çökelme yok;
kaynak yeri mahalle içinde eşit dağılımlı; 100 m ızgara; 2 km altında Gauss modelleri ölçüme göre 1,6-2,6 kat
düşük tahmin edebilir (Duke Forest 1996).
"""
from __future__ import annotations

import math

import numpy as np

# Briggs (1973) kentsel σ katsayıları — McElroy-Pooler St. Louis verisine dayalı (x: m, 100 m-10 km için)
def sigmalar(x: np.ndarray, grup: str):
    x = np.maximum(x, 1.0)
    if grup == "AB":
        sy = 0.32 * x / np.sqrt(1 + 0.0004 * x)
        sz = 0.24 * x * np.sqrt(1 + 0.001 * x)
    elif grup == "C":
        sy = 0.22 * x / np.sqrt(1 + 0.0004 * x)
        sz = 0.20 * x
    elif grup == "D":
        sy = 0.16 * x / np.sqrt(1 + 0.0004 * x)
        sz = 0.14 * x / np.sqrt(1 + 0.0003 * x)
    elif grup == "EF":
        sy = 0.11 * x / np.sqrt(1 + 0.0004 * x)
        sz = 0.08 * x / np.sqrt(1 + 0.0015 * x)
    else:
        raise ValueError(grup)
    return sy, sz


def dikey(sz: np.ndarray, h: float, zr: float, L: float) -> np.ndarray:
    """Zemin ve karışım tavanı yansımalı dikey terim V (σz < 1,6L); üstünde tekdüze karışım için NaN döner."""
    v = np.zeros_like(sz)
    for n in range(-2, 3):
        v += np.exp(-0.5 * ((zr - h + 2 * n * L) / sz) ** 2) + np.exp(-0.5 * ((zr + h + 2 * n * L) / sz) ** 2)
    return np.where(sz < 1.6 * L, v, np.nan)


def dikey_carpan(sz, h, zr, L):
    """Rüzgâr yönünde bütünleştirilmiş derişim çarpanı: V/(√(2π)σz) ya da tekdüze karışımda 1/L."""
    v = dikey(sz, h, zr, L)
    return np.where(np.isnan(v), 1.0 / L, np.nan_to_num(v) / (math.sqrt(2 * math.pi) * sz))


class Izgara:
    """Alıcı (Kadıköy) ve kaynak (Kadıköy + komşu) hücreleri."""

    def __init__(self, alici_xy: np.ndarray, alici_mah: np.ndarray, kaynak_xy: np.ndarray, kaynak_mah: np.ndarray,
                 hucre: float):
        self.alici_xy, self.alici_mah = alici_xy, alici_mah
        self.kaynak_xy, self.kaynak_mah = kaynak_xy, kaynak_mah
        self.hucre = hucre


def uzun_donem_aktarim(iz: Izgara, frek: list[dict], alici_adlari: list[str], kaynak_adlari: list[str],
                       h=5.0, zr=1.5, sz0=7.0, n_sektor=36, kentsel_kararlilik=False) -> np.ndarray:
    """D[r, m] (lif/m³ per lif/s). frek: meteoroloji.frekans_tablosu çıktısı."""
    a = iz.hucre
    sy0 = a / 4.3
    dteta = 2 * math.pi / n_sektor
    # birleşik sınıflar: (hız, kararlılık, karışım) → 36 sektörlük 'gelen yön' frekansı
    kombo: dict[tuple, np.ndarray] = {}
    for r in frek:
        grup = r["kararlilik"]
        if kentsel_kararlilik and grup == "EF":
            grup = "D"
        k = (float(r["hiz_ms"]), grup, float(r["karisim_m"]))
        kombo.setdefault(k, np.zeros(n_sektor))[int(r["sektor"])] += float(r["frekans"])
    nR, nM = len(alici_adlari), len(kaynak_adlari)
    D = np.zeros((nR, nM))
    rid = {ad: i for i, ad in enumerate(alici_adlari)}
    alici_index = np.array([rid[m] for m in iz.alici_mah])
    sayac_r = np.bincount(alici_index, minlength=nR).astype(float)
    for mi, mad in enumerate(kaynak_adlari):
        js = np.where(iz.kaynak_mah == mad)[0]
        if len(js) == 0:
            continue
        dx = iz.alici_xy[:, 0][:, None] - iz.kaynak_xy[js, 0][None, :]
        dy = iz.alici_xy[:, 1][:, None] - iz.kaynak_xy[js, 1][None, :]
        x = np.hypot(dx, dy)
        oz = x < 1e-6
        xe = np.maximum(x, a / 2)
        yon = (np.degrees(np.arctan2(dx, dy)) + 360) % 360  # kaynaktan alıcıya (gidilen yön), kuzeyden saat yönünde
        c = np.zeros_like(x)
        for (u, grup, L), f_gelen in kombo.items():
            f_giden = np.roll(f_gelen, -n_sektor // 2)  # gelen yön θ → gidilen yön θ+180
            aci = np.arange(n_sektor) * 360 / n_sektor
            g = np.interp(yon, np.r_[aci, 360.0], np.r_[f_giden, f_giden[0]])
            sy, sz = sigmalar(xe, grup)
            szt = np.hypot(sz, sz0)
            # ISCLT sektör ortalaması: yön frekansı yoğunluğu (f/Δθ) × rüzgâr yönünde bütünleşik derişim / x.
            # Alan kaynağı ve yumuşak rüzgâr gülü için yakın alanda da geçerlidir (σy formülde yer almaz).
            radyal = dikey_carpan(szt, h, zr, L) / (u * xe * dteta)
            # kendi hücresi: rüzgâr yönünden bağımsız; hücrenin rüzgâr üstündeki yarısı, genişlik a
            sy_s, sz_s = sigmalar(np.array([a / 2]), grup)
            self_terim = 0.5 * dikey_carpan(np.hypot(sz_s, sz0), h, zr, L)[0] / (u * a) * f_gelen.sum()
            c += np.where(oz, self_terim, g * radyal)
        katki = c.mean(axis=1)  # kaynak mahalle içinde eşit dağılım: Q_m / N_m her hücreye
        D[:, mi] = np.bincount(alici_index, weights=katki, minlength=nR) / sayac_r
    return D


def kisa_sure_aktarim(iz: Izgara, alici_adlari: list[str], kaynak_adlari: list[str], gelen_yon: float, u: float,
                      grup: str, L: float, h=5.0, zr=1.5, sz0=7.0) -> np.ndarray:
    a = iz.hucre
    sy0 = a / 4.3
    giden = math.radians((gelen_yon + 180) % 360)
    ex, ey = math.sin(giden), math.cos(giden)
    nR, nM = len(alici_adlari), len(kaynak_adlari)
    D = np.zeros((nR, nM))
    rid = {ad: i for i, ad in enumerate(alici_adlari)}
    alici_index = np.array([rid[m] for m in iz.alici_mah])
    sayac_r = np.bincount(alici_index, minlength=nR).astype(float)
    sy_s, sz_s = sigmalar(np.array([a / 2]), grup)
    self_terim = 0.5 * dikey_carpan(np.hypot(sz_s, sz0), h, zr, L)[0] / (u * a)
    for mi, mad in enumerate(kaynak_adlari):
        js = np.where(iz.kaynak_mah == mad)[0]
        if len(js) == 0:
            continue
        dx = iz.alici_xy[:, 0][:, None] - iz.kaynak_xy[js, 0][None, :]
        dy = iz.alici_xy[:, 1][:, None] - iz.kaynak_xy[js, 1][None, :]
        xd = dx * ex + dy * ey
        yc = -dx * ey + dy * ex
        oz = np.hypot(dx, dy) < 1e-6
        xe = np.maximum(xd, a / 2)
        sy, sz = sigmalar(xe, grup)
        syt, szt = np.hypot(sy, sy0), np.hypot(sz, sz0)
        c = np.exp(-0.5 * (yc / syt) ** 2) / (math.sqrt(2 * math.pi) * syt) * dikey_carpan(szt, h, zr, L) / u
        c = np.where(xd > 0, c, 0.0)
        c = np.where(oz, self_terim, c)
        katki = c.mean(axis=1)
        D[:, mi] = np.bincount(alici_index, weights=katki, minlength=nR) / sayac_r
    return D


def tek_yikim_profili(Q: float, mesafeler, u: float, grup: str, L: float, h=5.0, zr=1.5, sy0=5.0, sz0=7.0):
    """Tek bir yıkımın rüzgâr altı eksen derişimi (lif/m³)."""
    x = np.asarray(mesafeler, float)
    sy, sz = sigmalar(x, grup)
    syt, szt = np.hypot(sy, sy0), np.hypot(sz, sz0)
    return Q * dikey_carpan(szt, h, zr, L) / (math.sqrt(2 * math.pi) * syt * u)
