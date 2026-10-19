// Tarayıcı konsolu için PDF asbest tarayıcısı (ikinci turda kullanıldı, 13 Ekim 2026).
//
// Ne işe yarar: Buluttan/bottan açılmayan belediye sitelerinde, sayfadaki faaliyet raporu PDF'lerini
// tarayıcının kendi bağlantısıyla (Türkiye IP'si) indirir, pdf.js ile metnini okur ve "asbest/amyant/eternit/krizotil"
// geçen sayfaları bağlamıyla listeler. Dosya diske kaydedilmez; yalnız bellekte okunur.
//
// Kullanım (belediyenin faaliyet raporları sayfasında, F12 → Konsol):
//   1) Bu dosyanın tamamını yapıştırın.
//   2) __kuyruk(__pdfBaglantilari(/Faaliyet Raporu/i))   // sayfadaki PDF bağlantılarını sırayla tarar
//   3) __durum()            // özet: sayfa sayısı, metin uzunluğu, az metinli (taranmış) sayfa, eşleşme sayfaları
//      __durum(null, true)  // eşleşmelerin bağlamıyla tam çıktı
//   4) await __sayfa(url, [64])  // bir PDF'in belirli sayfasının tam metni (doğrulama için)
//
// Notlar:
// - Yalnız aynı alan adındaki PDF'ler okunabilir (tarayıcı güvenliği). Başka alan adındaki PDF için o siteye gidin.
// - Site robots.txt'si bir yolu botlara kapatıyorsa (ör. Beykoz /api/) bu betiği o yol için kullanmayın; elle açın.
// - Sayfa numaraları PDF sayfasıdır (basılı sayfa numarası farklı olabilir).
// - "az_metinli" yüksekse rapor taranmış görüntüdür; asbest araması için OCR gerekir (src/ocr.py).

window.__asb = async (url, maxHits = 10) => {
  if (!window.pdfjsLib) {
    await new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
      s.onload = res; s.onerror = () => rej('pdf.js yüklenemedi');
      (document.head || document.documentElement).appendChild(s);
    });
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  }
  const r = await fetch(url);
  if (!r.ok) return { url, http: r.status };
  const buf = await r.arrayBuffer();
  const bayt = buf.byteLength;
  const doc = await pdfjsLib.getDocument({ data: buf }).promise;
  window.__pdfcache = window.__pdfcache || {};
  __pdfcache[url] = doc;
  const out = []; let metin = 0, az = 0, bosluksuz = 0;
  for (let i = 1; i <= doc.numPages; i++) {
    const tc = await (await doc.getPage(i)).getTextContent();
    const t = tc.items.map(x => x.str).join(' ').replace(/\s+/g, ' ');
    // Türkçe karakterleri ayrı parçalara bölen PDF'ler için boşluksuz ikinci arama
    const t2 = tc.items.map(x => x.str).join('').replace(/[\s\-­]+/g, '').toLocaleLowerCase('tr');
    if (t2.length < 80) az++;
    bosluksuz += (t2.match(/asbest|amyant|eternit|krizotil/g) || []).length;
    metin += t.length;
    const re = /a\s?s\s?b\s?e\s?s\s?t|amyant|eternit|krizotil/gi; let m;
    while ((m = re.exec(t))) { out.push({ s: i, b: t.slice(Math.max(0, m.index - 220), m.index + 330) }); re.lastIndex = m.index + 330; }
  }
  return { url, bayt, sayfa: doc.numPages, metin, az_metinli: az, bosluksuz_eslesme: bosluksuz, eslesme: out.length, ilk: out.slice(0, maxHits) };
};

window.__pdfBaglantilari = (etiketRe = /faaliyet/i) =>
  [...document.querySelectorAll('a')]
    .filter(a => /\.pdf(\?|$)|\/download|isDosyalar|uploads/i.test(a.href) && etiketRe.test(a.textContent + ' ' + a.href))
    .map(a => [((a.textContent.match(/20\d\d/) || a.href.match(/20\d\d/) || ['?'])[0]) + ' ' + a.href.split('/').pop().slice(0, 40), a.href]);

window.__isler = window.__isler || {};
window.__kuyruk = async (ciftler) => {          // [[anahtar, url], ...] — sırayla, sayfayı kilitlemeden
  for (const [k] of ciftler) __isler[k] = { durum: 'sırada' };
  for (const [k, u] of ciftler) {
    __isler[k] = { durum: 'çalışıyor', t0: Date.now() };
    try { __isler[k] = await __asb(u, 8); } catch (e) { __isler[k] = { hata: String(e) }; }
  }
};

window.__durum = (anahtarlar = null, tam = false) => JSON.stringify(Object.fromEntries(
  (anahtarlar || Object.keys(__isler)).map(k => {
    const v = __isler[k] || { durum: 'yok' };
    if (v.durum) return [k, v.durum];
    const ozet = { sayfa: v.sayfa, metin: v.metin, az_metinli: v.az_metinli, bosluksuz: v.bosluksuz_eslesme,
                   eslesme: v.eslesme, hata: v.hata, http: v.http };
    ozet.sayfalar = [...new Set((v.ilk || []).map(h => h.s))];
    if (tam) ozet.ilk = (v.ilk || []).map(h => ({ s: h.s, b: h.b.slice(0, 480) }));
    return [k, ozet];
  })), null, 1);

window.__sayfa = async (url, sayfalar) => {
  let doc = (window.__pdfcache || {})[url];
  if (!doc) { await __asb(url, 0); doc = __pdfcache[url]; }
  const o = {};
  for (const p of sayfalar) {
    const tc = await (await doc.getPage(p)).getTextContent();
    o[p] = tc.items.map(x => x.str).join(' ').replace(/\s+/g, ' ');
  }
  return o;
};

'hazır: __kuyruk(__pdfBaglantilari()) ile başlayın, __durum() ile izleyin';
