"""Doğrulama yardımcısı: indirilmiş bir belgenin belirli sayfasını düzenli metin olarak basar.

Kullanım: python3 sayfa.py <url-parçası> <sayfa> [bitiş_sayfa] [--grep KELIME]
Örnek:    python3 sayfa.py 2019_Faaliyet_Raporu 165 166
"""
from __future__ import annotations

import glob
import json
import subprocess
import sys

from common import RAW


def find(fragment: str) -> str:
    hits = []
    for m in glob.glob(str(RAW / "*" / "*.meta.json")):
        j = json.load(open(m, encoding="utf-8"))
        if fragment in j["url"]:
            hits.append((m[:-10], j["url"]))
    if not hits:
        sys.exit(f"bulunamadı: {fragment}")
    if len(hits) > 1:
        print("birden çok eşleşme, ilki kullanılıyor:", *[h[1] for h in hits], sep="\n  ")
    base = hits[0][0]
    return [p for p in glob.glob(base + ".*") if not p.endswith(".json")][0]


def main() -> None:
    frag, first = sys.argv[1], int(sys.argv[2])
    last = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else first
    path = find(frag)
    out = subprocess.run(["pdftotext", "-layout", "-f", str(first), "-l", str(last), path, "-"],
                         capture_output=True).stdout.decode("utf-8", "replace")
    lines = [l for l in out.splitlines() if l.strip()]
    if "--grep" in sys.argv:
        kw = sys.argv[sys.argv.index("--grep") + 1].lower()
        keep = set()
        for i, l in enumerate(lines):
            if kw in l.lower():
                keep.update(range(max(0, i - 12), min(len(lines), i + 25)))
        lines = [lines[i] for i in sorted(keep)]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
