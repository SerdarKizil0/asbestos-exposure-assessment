"""Ortak HTTP katmanı: kibar istek (host başına hız sınırı), robots.txt kontrolü,
her isteğin kanıt günlüğüne yazılması.

Her istek veri/ham/log/istekler.jsonl dosyasına yazılır. "Dijital ortamı eledik"
diyebilmek için neyin, ne zaman, hangi sonuçla denendiğinin kaydı şarttır.
"""
from __future__ import annotations

import csv
import json
import re
import threading
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

# Depo kökü: src/tarama/common.py dosyasından iki üst klasör.
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ciktilar" / "tarama"          # tarama günlükleri ve aday URL listeleri
DOGRULANMIS = ROOT / "veri" / "dogrulanmis"  # elle doğrulanmış tablolar (veri_noktalari, kapsam_39)
RAW = ROOT / "veri" / "ham"                 # indirilen özgün belgeler; git'e girmez, silinmez
LOG = RAW / "log"                           # istek günlüğü; git'e girmez
XLSX = ROOT / "ciktilar" / "excel"          # betikle üretilen Excel kitapları; git'e girmez
for p in (OUT, DOGRULANMIS, LOG, RAW, XLSX):
    p.mkdir(parents=True, exist_ok=True)

# Kendini bot olarak tanıtan, dürüst bir User-Agent. Yerelde çalıştırırken
# buraya bir iletişim adresi eklemek iyi pratiktir.
UA = "Mozilla/5.0 (compatible; AsbestSeffaflikTaramasi/0.1; gazetecilik arastirmasi)"
MIN_INTERVAL = 2.0  # aynı hosta iki istek arası en az saniye

_session = requests.Session()
_session.headers.update({
    "User-Agent": UA,
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

_host_locks: dict[str, threading.Lock] = {}
_host_last: dict[str, float] = {}
_global_lock = threading.Lock()
_log_lock = threading.Lock()
_robots: dict[str, RobotFileParser | None] = {}


def _host(url: str) -> str:
    return urlparse(url).netloc.lower()


def _wait_turn(host: str) -> None:
    with _global_lock:
        lock = _host_locks.setdefault(host, threading.Lock())
    with lock:
        last = _host_last.get(host, 0.0)
        delta = time.monotonic() - last
        if delta < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - delta)
        _host_last[host] = time.monotonic()


def log_event(kind: str, **fields) -> None:
    rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tur": kind, **fields}
    with _log_lock:
        with open(LOG / "istekler.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


CF_MARKERS = ("Just a moment", "challenge-platform", "cf-chl", "Attention Required!", "cf_chl_opt")


def looks_like_challenge(resp: requests.Response | None, text: str = "") -> bool:
    if resp is None:
        return False
    if resp.headers.get("cf-mitigated", "").lower() == "challenge":
        return True
    if resp.status_code in (403, 429, 503):
        return any(m in text[:20000] for m in CF_MARKERS)
    return False


def fetch(url: str, *, timeout: float = 25, max_bytes: int = 15_000_000,
          check_robots: bool = True, purpose: str = "") -> dict:
    """Kibar GET. Sonucu sözlük olarak döndürür ve günlüğe yazar."""
    host = _host(url)
    if check_robots and not robots_allowed(url):
        rec = {"url": url, "durum": "robots_engelli", "amac": purpose}
        log_event("fetch", **rec)
        return {**rec, "ok": False, "text": "", "content": b"", "status": None,
                "final_url": url, "headers": {}}
    _wait_turn(host)
    t0 = time.monotonic()
    try:
        r = _session.get(url, timeout=timeout, allow_redirects=True, stream=True)
        chunks, size = [], 0
        for chunk in r.iter_content(65536):
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                break
        content = b"".join(chunks)
        r._content = content  # text erişimi için
        ctype = r.headers.get("content-type", "")
        text = ""
        if any(k in ctype for k in ("html", "xml", "text", "json", "javascript")) or ctype == "":
            r.encoding = r.encoding or r.apparent_encoding
            try:
                text = content.decode(r.encoding or "utf-8", errors="replace")
            except LookupError:
                text = content.decode("utf-8", errors="replace")
        challenge = looks_like_challenge(r, text)
        durum = "challenge" if challenge else ("ok" if r.ok else f"http_{r.status_code}")
        rec = {"url": url, "final_url": r.url, "status": r.status_code, "durum": durum,
               "bytes": len(content), "kesildi": size > max_bytes,
               "sure_s": round(time.monotonic() - t0, 2), "ctype": ctype, "amac": purpose}
        log_event("fetch", **rec)
        return {**rec, "ok": r.ok and not challenge, "text": text, "content": content,
                "headers": dict(r.headers)}
    except requests.RequestException as e:
        rec = {"url": url, "durum": "hata", "hata": f"{type(e).__name__}: {str(e)[:200]}",
               "sure_s": round(time.monotonic() - t0, 2), "amac": purpose}
        log_event("fetch", **rec)
        return {**rec, "ok": False, "text": "", "content": b"", "status": None,
                "final_url": url, "headers": {}}


def download(url: str, dest: Path, *, max_bytes: int = 1_500_000_000, timeout: float = 120,
             purpose: str = "buyuk_indirme") -> dict:
    """Büyük dosyayı belleğe almadan diske akıtır (ör. 80 MB üstü faaliyet raporları)."""
    host = _host(url)
    if not robots_allowed(url):
        log_event("download", url=url, durum="robots_engelli", amac=purpose)
        return {"ok": False, "durum": "robots_engelli"}
    _wait_turn(host)
    t0, size = time.monotonic(), 0
    try:
        with _session.get(url, timeout=timeout, stream=True, allow_redirects=True) as r:
            if not r.ok:
                log_event("download", url=url, status=r.status_code, durum=f"http_{r.status_code}", amac=purpose)
                return {"ok": False, "durum": f"http_{r.status_code}", "status": r.status_code}
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
                    size += len(chunk)
                    if size > max_bytes:
                        break
            rec = {"url": url, "final_url": r.url, "status": r.status_code, "durum": "ok",
                   "bytes": size, "kesildi": size > max_bytes, "ctype": r.headers.get("content-type", ""),
                   "sure_s": round(time.monotonic() - t0, 1), "amac": purpose}
            log_event("download", **rec)
            return {**rec, "ok": size <= max_bytes}
    except requests.RequestException as e:
        log_event("download", url=url, durum="hata", hata=str(e)[:200], amac=purpose)
        return {"ok": False, "durum": "hata", "hata": str(e)[:200]}


def robots_allowed(url: str) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = RobotFileParser()
        robots_url = base + "/robots.txt"
        _wait_turn(p.netloc.lower())
        try:
            r = _session.get(robots_url, timeout=20)
            if r.status_code == 200 and "html" not in r.headers.get("content-type", ""):
                rp.parse(r.text.splitlines())
            else:
                rp.parse([])  # robots yok/erişilemez: izinli say
            log_event("robots", url=robots_url, status=r.status_code)
        except requests.RequestException as e:
            rp.parse([])
            log_event("robots", url=robots_url, hata=str(e)[:200])
        _robots[base] = rp
    rp = _robots[base]
    return True if rp is None else rp.can_fetch(UA, url)


def robots_sitemaps(base: str) -> list[str]:
    robots_allowed(base + "/")
    rp = _robots.get(base)
    try:
        return list(rp.site_maps() or []) if rp else []
    except Exception:
        return []


# ---- Kişisel/iletişim verisini maskeleme (depo herkese açık) ----
_TELEFON_RE = re.compile(r"(?<![\w.])(?:\+90[\s-]?|0[\s-]?)?\(?[2-5]\d{2}\)?[\s-]\d{3}[\s-]\d{2}[\s-]\d{2}(?![\w.])"
                         r"|(?<![\w.])444[\s-]\d{2}[\s-]\d{2}(?![\w.])")
_EPOSTA_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def maskele(s: str) -> str:
    """Sayfadan alınan metinlerdeki telefon ve e-posta adreslerini gizler (kurumsal olsalar da)."""
    return _EPOSTA_RE.sub("[e-posta]", _TELEFON_RE.sub("[telefon]", s or ""))


# ---- Türkçe duyarlı metin normalleştirme ----
_TR_MAP = str.maketrans({"İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç"})


def tr_lower(s: str) -> str:
    return s.translate(_TR_MAP).lower()


def fold(s: str) -> str:
    """Eşleştirme için: Türkçe küçük harf + aksan kaldırma (ı->i, ş->s ...)."""
    s = tr_lower(s).replace("ı", "i")
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


ASBEST_RE = re.compile(r"asbest|amyant|eternit|krizotil|krosidolit|krokidolit|amosit|17\s?06\s?0[15]")


def read_seeds() -> list[dict]:
    with open(Path(__file__).resolve().parent / "seeds" / "belediyeler.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)
