// «Hisobotlar» sahifasi — index.html dagi umumiy yordamchilar ustida ishlaydi:
// api(), NAMUNA, INIT, oynaOch(), oynaYop(), xabar(), tebran(), e(), $().
// Ma'lumot: GET /app/api/hisobot[/kategoriya|/rasxodlar] (worker/src/miniapp_hisobot.js).
// Sahifa ichida o'z steki: Hisobotlar → kategoriya → ichki kategoriya / ro'yxat;
// orqaga — ← tugmasi va Telegram BackButton.
// Chuqur havolalar (skrinshot va sinov uchun): #hisobotlar, #hisobotlar/shaxsiy,
// #hisobotlar/davr, #hisobotlar/kat/<id>, #hisobotlar/ichki/<id>, #hisobotlar/royxat/<id>.
(() => {
  const ILOVA = location.protocol === "file:" ? "" : "/app/";
  const NB = " ";
  const fmt = (s) => String(Math.abs(Math.round(Number(s) || 0))).replace(/\B(?=(\d{3})+(?!\d))/g, NB);
  const uzs = (s) => `${fmt(s)}${NB}UZS`;
  const OY_Q = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"];
  const OY_T = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];
  const HAFTA = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
  // Desktop `theme.TUR_RANG` («oq» rejim) — doira rangi bo'lakning O'RNI bo'yicha.
  const TUR_RANG = ["#2A78D6", "#EB6834", "#1BAF7A", "#EDA100", "#E87BA4", "#008300", "#4A3AA7", "#E34948"];
  const KUL_OCH = "#9aa1ae", KUL_XIRA = "#c9ced8";
  const tg = window.Telegram && Telegram.WebApp;

  const IK = {
    taqvim: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>`,
    past: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>`,
    ong: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 5 7 7-7 7"/></svg>`,
    ongKatta: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 5 7 7-7 7"/></svg>`,
    chap: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 5-7 7 7 7"/></svg>`,
    orqa: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12H4.5M10.5 5.5 4 12l6.5 6.5"/></svg>`,
    x: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>`,
    odam: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4.5 20.5a7.5 7.5 0 0 1 15 0"/></svg>`,
    nuqta: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><circle cx="5.5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="18.5" cy="12" r="1.8"/></svg>`,
    kebab: `<svg width="4" height="16" viewBox="0 0 4 16" fill="currentColor"><circle cx="2" cy="2" r="1.7"/><circle cx="2" cy="8" r="1.7"/><circle cx="2" cy="14" r="1.7"/></svg>`,
    yorliq: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="M3.5 12.6V4.5a1 1 0 0 1 1-1h8.1l8 8a1.5 1.5 0 0 1 0 2.1l-6 6a1.5 1.5 0 0 1-2.1 0Z"/><circle cx="8.5" cy="8.5" r="1.4"/></svg>`,
  };

  // ── Sana yordamchilari (Toshkent kuni server'dan — `bugun`) ─────────
  const isoD = (d) => `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
  const dan = (s) => new Date(Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)));
  const kunQosh = (s, n) => { const d = dan(s); d.setUTCDate(d.getUTCDate() + n); return isoD(d); };
  const oyBoshi = (s) => s.slice(0, 8) + "01";
  const oyOxiri = (s) => isoD(new Date(Date.UTC(+s.slice(0, 4), +s.slice(5, 7), 0)));
  const oySur = (s, n) => isoD(new Date(Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1 + n, 1)));
  const kunOy = (s) => [+s.slice(8, 10), +s.slice(5, 7) - 1, +s.slice(0, 4)];
  function davrMatn(a, b) {
    const [d1, m1, y1] = kunOy(a), [d2, m2, y2] = kunOy(b);
    if (a === b) return `${d1} ${OY_Q[m1]}, ${y1}`;
    if (y1 === y2 && m1 === m2) return `${d1}–${d2} ${OY_Q[m1]}, ${y1}`;
    if (y1 === y2) return `${d1} ${OY_Q[m1]} – ${d2} ${OY_Q[m2]}, ${y1}`;
    return `${d1} ${OY_Q[m1]}, ${y1} – ${d2} ${OY_Q[m2]}, ${y2}`;
  }
  const kunSarlavha = (s) => { const [d, m, y] = kunOy(s); return `${d} ${OY_T[m]}, ${y}`; };

  // ── Holat ──────────────────────────────────────────────────────────
  const H = {
    bugun: null, dan: null, gacha: null, qolda: false,
    doira: "umumiy",        // "umumiy" | "<odam_id>"
    shaxsiy: false, odamId: null, odamlar: [], ochgan: null,
    stek: [{ tur: "bosh" }],
    data: null, yuklanmoqda: false, xato: "", soni: 0,
  };
  const joriy = () => H.stek[H.stek.length - 1];
  const korinadimi = () => { const s = $("sahifa-hisobotlar"); return s && !s.hidden; };

  // ── Namuna (file://) — dizayn namunasi bilan aynan bir xil ma'lumot ─
  const NB_ = {
    bugun: "2026-09-30",
    odamlar: [{ id: 1, nom: "Fayzulloxon" }, { id: 2, nom: "Otabek" }, { id: 3, nom: "Abbosxon" }],
    kat: [
      { id: 11, nom: "Oziq-ovqat", belgi: "life_16.svg", summa: 681600, reja: 800000 },
      { id: 12, nom: "Uy-joy", belgi: "life_14.svg", summa: 511200, reja: 600000 },
      { id: 13, nom: "Transport", belgi: "transportation_02.svg", summa: 319500, reja: 400000 },
      { id: 16, nom: "Boshqa", belgi: null, summa: 234300, reja: null },
      { id: 14, nom: "Maishiy tovarlar", belgi: "life_08.svg", summa: 213000, reja: 250000 },
      { id: 15, nom: "Sog‘liq", belgi: "health_11.svg", summa: 170400, reja: 200000 },
    ],
    shaxsiy: {
      1: { reja: 1200000, kat: [[11, 300000, 450000], [13, 180000, 250000], [15, 140000, 200000], [14, 120000, 150000], [16, 80000, null]] },
      2: { reja: 900000, kat: [[13, 260000, 300000], [11, 190000, 300000], [16, 90000, null]] },
      3: { reja: null, kat: [[11, 230000, null], [15, 180000, null]] },
    },
    ichki: [
      { turi_id: 21, nom: "Meva-sabzavot", belgi: "food_13.svg", summa: 230000, reja: 300000 },
      { turi_id: 22, nom: "Go‘sht-mahsulotlari", belgi: "food_06.svg", summa: 150000, reja: 200000 },
      { turi_id: 23, nom: "Sut va sut mahsulotlari", belgi: "food_08.svg", summa: 110000, reja: 120000 },
      { turi_id: 24, nom: "Non va un mahsulotlari", belgi: "food_01.svg", summa: 80000, reja: 80000 },
      { turi_id: 25, nom: "Ichimliklar", belgi: "life_01.svg", summa: 60000, reja: null },
      { turi_id: 11, ozi: true, nom: "Boshqa", belgi: null, summa: 51600, reja: null },
    ],
  };
  function nbRasxod(id, sana, vaqt, nom, summa, ichki = 21, m = []) {
    const ic = NB_.ichki.find((x) => x.turi_id === ichki && !x.ozi) || NB_.ichki[0];
    return { id, sana, vaqt, nom, summa, jami: summa, kategoriya: ic.nom, ichki: ic.nom, yol: `Oziq-ovqat → ${ic.nom}`, belgi: ic.belgi,
      mahsulotlar: m, tafsilot: { izoh: "", kim_toladi: "Fayzulloxon", doira: "Umumiy", joy: "Naqd",
        ulushlar: [{ nom: "Fayzulloxon", summa: Math.ceil(summa / 3) }, { nom: "Otabek", summa: Math.floor(summa / 3) }, { nom: "Abbosxon", summa: summa - Math.ceil(summa / 3) - Math.floor(summa / 3) }],
        mahsulotlar: m } };
  }
  const NB_MEVA = [
    nbRasxod(1, "2026-09-14", "14:30", "Olma", 25000), nbRasxod(2, "2026-09-14", "12:15", "Banan", 18000),
    nbRasxod(3, "2026-09-14", "09:40", "Pomidor", 20000), nbRasxod(4, "2026-09-14", "09:10", "Bodring", 12000),
    nbRasxod(5, "2026-09-12", "18:20", "Kartoshka", 25000), nbRasxod(6, "2026-09-12", "17:10", "Piyoz", 20000),
    nbRasxod(7, "2026-09-09", "19:05", "Olma", 30000), nbRasxod(8, "2026-09-09", "19:00", "Sabzi", 15000),
    nbRasxod(9, "2026-09-05", "11:30", "Bozorlik", 65000, 21, [{ nom: "Uzum", miqdor: 2, summa: 40000 }, { nom: "Nok", miqdor: 1, summa: 25000 }]),
  ];
  const foizF = (q, b) => (b > 0 ? Math.floor((q * 200 + b) / (2 * b)) : null);
  const holatF = (r, f) => (!r ? "rejasiz" : f > r ? "oshdi" : foizF(f, r) >= 80 ? "yaqin" : "yaxshi");
  const xulosaF = (fakt, reja) => ({ fakt, reja: reja || null, foiz: reja ? foizF(fakt, reja) : null, holat: holatF(reja, fakt) });
  function ulushlar(arr) {               // 0,1% birligida, yig'indisi 1000 (namuna uchun)
    const jami = arr.reduce((s, x) => s + x, 0); if (!jami) return arr.map(() => 0);
    const xom = arr.map((x) => (x * 1000) / jami), asos = xom.map(Math.floor);
    let q = 1000 - asos.reduce((s, x) => s + x, 0);
    xom.map((x, i) => [x - asos[i], i]).sort((a, b) => b[0] - a[0]).slice(0, q).forEach(([, i]) => asos[i]++);
    return asos;
  }
  function namunaKatlar() {
    if (H.doira === "umumiy") return NB_.kat;
    const s = NB_.shaxsiy[H.doira] || NB_.shaxsiy[1];
    return s.kat.map(([id, summa, reja]) => ({ ...NB_.kat.find((k) => k.id === id), summa, reja }));
  }
  function namuna(v) {
    const katlar = namunaKatlar().slice().sort((a, b) => b.summa - a.summa);
    const asos = { ok: true, bugun: NB_.bugun, dan: H.dan, gacha: H.gacha, doira: H.doira };
    if (v.tur === "bosh") {
      const u = ulushlar(katlar.map((k) => k.summa));
      const fakt = katlar.reduce((s, k) => s + k.summa, 0);
      const reja = H.doira === "umumiy" ? 3000000 : (NB_.shaxsiy[H.doira] || {}).reja;
      return { ...asos, odam: NB_.odamlar[0], odamlar: NB_.odamlar, xulosa: xulosaF(fakt, reja),
        bolaklar: katlar.map((k, i) => ({ tur: "turi", nom: k.nom, belgi: k.belgi, summa: k.summa, ulush: u[i], idlar: [k.id] })),
        jadval: katlar.map((k, i) => ({ turi_id: k.id, nom: k.nom, belgi: k.belgi, summa: k.summa, reja: k.reja, ulush: u[i] })) };
    }
    const kat = NB_.kat.find((k) => k.id === (v.idlar ? v.idlar[0] : v.turi_id));
    if (v.tur === "kat") {
      const k = katlar.find((x) => x.id === v.idlar[0]) || kat;
      const ichki = k.id === 11 && H.doira === "umumiy" ? NB_.ichki.map((x) => ({ ...x })) : [];
      const u = ulushlar(ichki.map((x) => x.summa)); ichki.forEach((x, i) => { x.ulush = u[i]; });
      const songgi = k.id === 11 && H.doira === "umumiy" ? [NB_MEVA[0], NB_MEVA[1],
        { ...nbRasxod(20, "2026-09-14", "10:20", "Go‘sht", 45000, 22) }] : [];
      return { ...asos, nom: k.nom, belgi: k.belgi, xulosa: xulosaF(k.summa, k.reja), ichki, songgi, soni: songgi.length };
    }
    const ic = NB_.ichki.find((x) => x.turi_id === v.turi_id && !!x.ozi === !!v.ozi);
    const rows = v.tur === "ichki" && v.turi_id === 21 ? NB_MEVA : v.tur === "royxat" && (v.idlar || [])[0] === 11 ? NB_MEVA : [];
    const kunlar = [];
    for (const q of rows) {
      let k = kunlar[kunlar.length - 1];
      if (!k || k.sana !== q.sana) kunlar.push(k = { sana: q.sana, jami: 0, qatorlar: [] });
      k.jami += q.summa; k.qatorlar.push(q);
    }
    const src = v.tur === "ichki" ? ic : kat;
    return { ...asos, nom: src ? src.nom : v.nom, belgi: src ? src.belgi : null,
      xulosa: v.tur === "ichki" && ic ? xulosaF(ic.summa, ic.reja) : xulosaF(src ? src.summa : 0, src ? src.reja : null), kunlar };
  }

  // ── Ma'lumot ───────────────────────────────────────────────────────
  function sorov(v) {
    const p = new URLSearchParams({ dan: H.dan, gacha: H.gacha, doira: H.doira });
    if (v.tur === "bosh") return "hisobot?" + p;
    if (v.tur === "kat") { p.set("idlar", v.idlar.join(",")); return "hisobot/kategoriya?" + p; }
    if (v.tur === "royxat") { p.set("idlar", v.idlar.join(",")); return "hisobot/rasxodlar?" + p; }
    p.set("turi_id", v.turi_id); if (v.ozi) p.set("ozi", "1");
    return "hisobot/rasxodlar?" + p;
  }

  let navbat = 0;
  async function yukla() {
    const v = joriy(), mening = ++navbat;
    if (!H.dan) birlamchiDavr(H.bugun || (NAMUNA ? NB_.bugun : isoD(new Date(Date.now() + 5 * 3600e3))));
    H.yuklanmoqda = true; H.xato = "";
    chiz();
    try {
      let j;
      if (NAMUNA) j = namuna(v);
      else if (!INIT) throw new Error("Bu sahifani Telegram'dagi Farovon Uy botidan oching.");
      else j = await api(sorov(v));
      if (mening !== navbat) return;
      if (j.bugun && j.bugun !== H.bugun) {
        H.bugun = j.bugun;
        if (!H.qolda && (H.dan !== oyBoshi(j.bugun) || H.gacha !== j.bugun)) {
          birlamchiDavr(j.bugun); return yukla();
        }
      }
      if (j.odamlar) {
        H.odamlar = j.odamlar; H.ochgan = j.odam;
        if (H.odamId == null && j.odam) H.odamId = j.odam.id;
        if (H.shaxsiy && H.doira === "umumiy" && H.odamId != null) { H.doira = String(H.odamId); return yukla(); }
      }
      H.data = j; v.data = j;
    } catch (err) {
      if (mening !== navbat) return;
      H.xato = err.message || String(err); H.data = null;
    }
    H.yuklanmoqda = false;
    chiz();
  }
  // Birlamchi oraliq — joriy oyning 1-kunidan BUGUNGACHA (`plan.oy_bugungacha`).
  function birlamchiDavr(bugun) { H.dan = oyBoshi(bugun); H.gacha = bugun; }

  // ── Chizish ────────────────────────────────────────────────────────
  const ikon = (fayl, rang, cls = "") => {
    const fon = rang ? `style="background:${rang}1f;color:${rang}"` : "";
    return `<span class="hs-ik ${cls}" ${fon}>${fayl ? `<img src="${ILOVA}belgilar/${e(fayl)}" alt="">` : IK.nuqta}</span>`;
  };
  const davrTugma = () => `<button class="hs-davr" data-hs="davr" aria-label="Davrni tanlash">${IK.taqvim}<span class="hs-num">${e(davrMatn(H.dan, H.gacha))}</span>${IK.past}</button>`;

  function xulosaKarta({ yorliq, x, ik = "", rang = "kok" }) {
    const f = x.foiz;
    const en = f == null ? 0 : Math.min(100, f);
    return `<div class="hs-karta hs-xulosa"><div class="hs-q">${ik}
      <div class="hs-chap"><div class="hs-yorliq">${e(yorliq)}</div><div class="hs-summa hs-num">${uzs(x.fakt)}</div></div>
      <div class="hs-ong"><div class="hs-yorliq">Reja</div><div class="hs-reja hs-num">${x.reja ? uzs(x.reja) : "—"}</div></div></div>
      <div class="hs-chiziqcha ${rang}"><div class="hs-yol"><i style="width:${en}%"></i></div><b class="hs-num">${f == null ? "—" : f + "%"}</b></div></div>`;
  }
  const barRang = (x) => (x.holat === "oshdi" || x.holat === "yaqin" ? "qizil" : "yashil");

  // Desktop `bolak_ranglari()` (sahifa_analitika.py:39) — rangli bo'laklarga palitra aylanadi.
  function bolakRanglari(turlar) {
    const n = TUR_RANG.length, rang = []; let k = 0;
    for (const t of turlar) { if (t === "turi") { rang.push(TUR_RANG[k % n]); k++; } else rang.push(null); }
    if (k > 2 && turlar[turlar.length - 1] === "turi" && rang[rang.length - 1] === rang[0]) {
      const old = rang[rang.length - 2];
      rang[rang.length - 1] = [...TUR_RANG.slice(n / 2), ...TUR_RANG].find((c) => c !== rang[0] && c !== old);
    }
    return rang.map((r, i) => r || (turlar[i] === "qolgan" ? KUL_OCH : KUL_XIRA));
  }

  function doiraSvg(bolaklar, ranglar, jami) {
    const R = 86, r = 48, C = 100;
    const jamiU = bolaklar.reduce((s, b) => s + b.ulush, 0) || 1;
    const nuqta = (rad, a) => [C + rad * Math.sin(a), C - rad * Math.cos(a)];
    let a0 = 0, yol = "", yozuv = "";
    bolaklar.forEach((b, i) => {
      if (!b.ulush) return;
      const a1 = a0 + (b.ulush / jamiU) * Math.PI * 2;
      const kat = a1 - a0 > Math.PI ? 1 : 0;
      let d;
      if (b.ulush >= jamiU) {
        d = `M${C} ${C - R}A${R} ${R} 0 1 1 ${C - .01} ${C - R}Z M${C} ${C - r}A${r} ${r} 0 1 0 ${C + .01} ${C - r}Z`;
      } else {
        const [x1, y1] = nuqta(R, a0), [x2, y2] = nuqta(R, a1), [x3, y3] = nuqta(r, a1), [x4, y4] = nuqta(r, a0);
        d = `M${x1} ${y1}A${R} ${R} 0 ${kat} 1 ${x2} ${y2}L${x3} ${y3}A${r} ${r} 0 ${kat} 0 ${x4} ${y4}Z`;
      }
      yol += `<path d="${d}" fill="${ranglar[i]}" stroke="#fff" stroke-width="1.6" fill-rule="evenodd" data-i="${i}"><title>${e(b.nom)}</title></path>`;
      const f = Math.round(b.ulush / 10);
      if (f >= 2) {
        const [x, y] = nuqta(R + 15, (a0 + a1) / 2);
        yozuv += `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" text-anchor="middle" dominant-baseline="central" font-size="11.5" font-weight="600" fill="#3b4657">${f}%</text>`;
      }
      a0 = a1;
    });
    if (!yol) yol = `<circle cx="${C}" cy="${C}" r="${(R + r) / 2}" fill="none" stroke="#eef1f6" stroke-width="${R - r}"/>`;
    return `<svg viewBox="0 0 200 200" role="img" aria-label="Kategoriyalar bo‘yicha ulush">${yol}${yozuv}
      <text x="${C}" y="${C - 8}" text-anchor="middle" dominant-baseline="central" font-size="14.5" font-weight="700" fill="#18222f">${fmt(jami)}</text>
      <text x="${C}" y="${C + 11}" text-anchor="middle" dominant-baseline="central" font-size="12.5" font-weight="600" fill="#18222f">UZS</text></svg>`;
  }

  function boshChiz(d) {
    const odamlar = H.odamlar.length ? H.odamlar : [];
    const segment = `<div class="hs-seg" role="tablist">
      <button class="${H.shaxsiy ? "" : "faol"}" data-hs="umumiy">Umumiy</button>
      <button class="${H.shaxsiy ? "faol" : ""}" data-hs="shaxsiy">Shaxsiy</button></div>
      ${H.shaxsiy ? `<div class="hs-kim"><h3>Kimning hisoboti?</h3><div class="hs-odamlar">${odamlar.map((o) =>
        `<button class="${String(o.id) === H.doira ? "faol" : ""}" data-hs="odam" data-id="${o.id}">${IK.odam}${e(o.nom)}</button>`).join("")}</div></div>` : ""}`;
    let tana = "";
    if (d) {
      const ranglar = bolakRanglari(d.bolaklar.map((b) => b.tur));
      H.ranglar = ranglar;
      tana = xulosaKarta({ yorliq: "Umumiy xarajatlar", x: d.xulosa }) +
        `<div class="hs-bolim"><h2>Kategoriyalar bo‘yicha ulush</h2>${d.jadval.length ? `<button class="hs-havola" data-hs="jadvalga" aria-label="Jadvalga o‘tish">${IK.ongKatta}</button>` : ""}</div>` +
        (d.bolaklar.length ? `<div class="hs-doira">${doiraSvg(d.bolaklar, ranglar, d.xulosa.fakt)}
          <div class="hs-afsona">${d.bolaklar.map((b, i) => `<button data-hs="bolak" data-i="${i}">${ikon(b.belgi, ranglar[i], "")}
            <span class="hs-m"><b>${e(b.nom)}</b><span class="hs-num">${uzs(b.summa)}</span></span></button>`).join("")}</div></div>`
          : `<div class="hs-bosh-holat">Bu davrda xarajat yo‘q</div>`) +
        (d.jadval.length ? `<div class="hs-karta hs-jadval"><h2>Kategoriyalar bo‘yicha</h2>
          <div class="hs-jq sar"><span>Kategoriya</span><span>Xarajat</span><span>Reja</span><span>Ulush</span><span></span></div>
          ${d.jadval.map((j) => {
            const bi = d.bolaklar.findIndex((b) => b.idlar.length === 1 && b.idlar[0] === j.turi_id);
            const rang = bi >= 0 ? ranglar[bi] : KUL_OCH;
            return `<button class="hs-jq" data-hs="jadval" data-id="${j.turi_id}">
              <span class="hs-nom">${ikon(j.belgi, rang, "s")}<span>${e(j.nom)}</span></span>
              <span class="r hs-num">${fmt(j.summa)}</span><span class="r kul hs-num">${j.reja ? fmt(j.reja) : "—"}</span>
              <span class="r hs-num">${Math.round(j.ulush / 10)}%</span>${IK.ong}</button>`;
          }).join("")}</div>` : "");
    }
    return `<div class="hs-bosh"><h1>Hisobotlar</h1>${davrTugma()}</div>${segment}${tana}`;
  }

  function rasxodQator(q, ikonFayl, ost) {
    return `<div class="hs-rasxod">${ikon(ikonFayl ?? q.belgi, null, "k")}
      <div class="hs-m"><b>${e(q.nom)}</b><span>${e(ost)}</span></div>
      <span class="hs-minus hs-num">- ${uzs(q.summa)}</span>
      <button class="hs-kebab" data-hs="rasxod" data-id="${q.id}" aria-label="Tafsilot">${IK.kebab}</button></div>`;
  }

  function katChiz(v, d) {
    let tana = "";
    if (d) {
      const yorliq = d.nom;
      tana = xulosaKarta({ yorliq, x: d.xulosa, ik: ikon(d.belgi, null, "xl"), rang: barRang(d.xulosa) }) +
        (d.ichki.length ? `<div class="hs-bolim"><h2>${(v.idlar || []).length > 1 ? "Kategoriyalar" : "Ichki kategoriyalar"}</h2></div>
          <div class="hs-karta hs-royxat">${d.ichki.map((x, i) => `<button class="hs-qator" data-hs="ichki" data-i="${i}">
            ${ikon(x.belgi, null, "")}<span class="hs-nom">${e(x.nom)}</span>
            <span class="hs-sum hs-num">${uzs(x.summa)}</span><span class="hs-foiz hs-num">${Math.round(x.ulush / 10)}%</span>
            <svg class="hs-ong-ok" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 5 7 7-7 7"/></svg></button>`).join("")}</div>` : "") +
        `<div class="hs-bolim"><h2>So‘nggi rasxodlar</h2>${d.soni ? `<button class="hs-havola" data-hs="hammasi">Barchasini ko‘rish</button>` : ""}</div>` +
        (d.songgi.length ? `<div class="hs-karta hs-royxat">${d.songgi.map((q) =>
          rasxodQator(q, null, `${q.ichki || q.kategoriya}${q.vaqt ? " • " + q.vaqt : ""}`)).join("")}</div>`
          : `<div class="hs-bosh-holat">Bu davrda rasxod yo‘q</div>`);
    }
    return `<div class="hs-bosh"><div class="hs-ort"><button class="hs-orqa" data-hs="orqa" aria-label="Orqaga">${IK.orqa}</button>
      <h1>${e(d ? d.nom : v.nom || "")}</h1></div>${davrTugma()}</div>${tana}`;
  }

  function royxatChiz(v, d) {
    let tana = "";
    if (d) {
      tana = xulosaKarta({ yorliq: d.nom, x: d.xulosa, ik: ikon(d.belgi, null, "xl"), rang: barRang(d.xulosa) }) +
        `<div class="hs-bolim"><h2>Rasxodlar ro‘yxati</h2></div>` +
        (d.kunlar.length ? d.kunlar.map((k) => `<div class="hs-karta hs-kun">
          <div class="hs-kun-bosh"><span>${kunSarlavha(k.sana)}</span><span class="hs-num">${uzs(k.jami)}</span></div>
          <div class="hs-royxat">${k.qatorlar.map((q) => {
            const ost = `${q.vaqt ? q.vaqt + " • " : ""}${q.yol}`;
            if (q.mahsulotlar && q.mahsulotlar.length) {
              return q.mahsulotlar.map((m) => rasxodQator({ ...m, id: q.id, nom: m.miqdor > 1 ? `${m.nom} ×${m.miqdor}` : m.nom }, q.belgi, ost)).join("");
            }
            return rasxodQator(q, null, ost);
          }).join("")}</div></div>`).join("") : `<div class="hs-bosh-holat">Bu davrda rasxod yo‘q</div>`);
    }
    return `<div class="hs-bosh"><div class="hs-ort"><button class="hs-orqa" data-hs="orqa" aria-label="Orqaga">${IK.orqa}</button>
      <h1>${e(d ? d.nom : v.nom || "")}</h1></div>${davrTugma()}</div>${tana}`;
  }

  function chiz() {
    const s = $("sahifa-hisobotlar"); if (!s) return;
    const v = joriy();
    const d = H.data && !H.xato ? H.data : (v.data || null);
    let html = v.tur === "bosh" ? boshChiz(d) : v.tur === "kat" ? katChiz(v, d) : royxatChiz(v, d);
    if (H.xato) html += `<div class="hs-bosh-holat">${e(H.xato)}</div>`;
    else if (!d) html += `<div class="hs-bosh-holat">Yuklanmoqda…</div>`;
    s.innerHTML = `<div class="${H.yuklanmoqda && d ? "hs-yuklanmoqda" : ""}">${html}</div>`;
    orqaTugma();
  }

  // ── Navigatsiya ─────────────────────────────────────────────────────
  function och(v) { H.stek.push(v); H.data = null; window.scrollTo(0, 0); yukla(); }
  function orqaga() {
    if (H.stek.length <= 1) return false;
    H.stek.pop(); H.data = joriy().data || null; window.scrollTo(0, 0); yukla(); return true;
  }
  let tgBog = false;
  function orqaTugma() {
    if (!tg || !tg.BackButton) return;
    if (!tgBog) { tg.BackButton.onClick(() => { if (korinadimi()) { tebran("soft"); orqaga(); } }); tgBog = true; }
    if (korinadimi() && H.stek.length > 1) tg.BackButton.show(); else tg.BackButton.hide();
  }
  function bolakOch(b) {
    if (!b) return;
    tebran("soft");
    och({ tur: "kat", idlar: b.idlar, nom: b.nom });
  }

  $("sahifa-hisobotlar").addEventListener("click", (ev) => {
    const t = ev.target.closest("[data-hs]"); if (!t) return;
    const d = H.data, v = joriy();
    switch (t.dataset.hs) {
      case "davr": davrOyna(); break;
      case "orqa": tebran("soft"); orqaga(); break;
      case "umumiy": if (H.shaxsiy) { H.shaxsiy = false; H.doira = "umumiy"; tebran("soft"); yukla(); } break;
      case "shaxsiy": if (!H.shaxsiy) {
        H.shaxsiy = true; if (H.odamId == null && H.ochgan) H.odamId = H.ochgan.id;
        H.doira = String(H.odamId ?? (H.odamlar[0] || {}).id ?? "umumiy"); tebran("soft"); yukla();
      } break;
      case "odam": if (H.doira !== t.dataset.id) { H.odamId = Number(t.dataset.id); H.doira = t.dataset.id; tebran("soft"); yukla(); } break;
      case "jadvalga": { const j = document.querySelector("#sahifa-hisobotlar .hs-jadval"); if (j) j.scrollIntoView({ behavior: "smooth", block: "start" }); break; }
      case "bolak": if (d && d.bolaklar) bolakOch(d.bolaklar[Number(t.dataset.i)]); break;
      case "jadval": if (d) { const id = Number(t.dataset.id); tebran("soft"); och({ tur: "kat", idlar: [id], nom: (d.jadval.find((j) => j.turi_id === id) || {}).nom }); } break;
      case "ichki": if (d && d.ichki) {
        const x = d.ichki[Number(t.dataset.i)]; tebran("soft");
        if (x.idlar) och({ tur: "kat", idlar: x.idlar, nom: x.nom });
        else och({ tur: "ichki", turi_id: x.turi_id, ozi: !!x.ozi, nom: x.nom });
      } break;
      case "hammasi": tebran("soft"); och({ tur: "royxat", idlar: v.idlar, nom: d ? d.nom : v.nom }); break;
      case "rasxod": if (d) tafsilot(Number(t.dataset.id)); break;
    }
  });
  $("sahifa-hisobotlar").addEventListener("click", (ev) => {
    const p = ev.target.closest("path[data-i]");
    if (p && H.data && H.data.bolaklar) bolakOch(H.data.bolaklar[Number(p.dataset.i)]);
  });

  function tafsilot(id) {
    const d = H.data;
    const hammasi = d.songgi || (d.kunlar || []).flatMap((k) => k.qatorlar);
    const q = hammasi.find((x) => x.id === id); if (!q) return;
    const t = q.tafsilot || {};
    const qator = (a, b) => `<div class="hs-t-q"><span>${e(a)}</span><b class="hs-num">${b}</b></div>`;
    oynaOch(`<div class="hs-taf"><h3>${e(q.nom)}</h3><div class="hs-t-summa hs-num" style="color:#f04646">- ${uzs(q.summa)}</div>
      <dl><dt>Sana</dt><dd>${kunSarlavha(q.sana)}${q.vaqt ? ", " + q.vaqt : ""}</dd>
      <dt>Kategoriya</dt><dd>${e(q.yol)}</dd>
      <dt>Kim to‘ladi</dt><dd>${e(t.kim_toladi || "—")}</dd>
      <dt>Turi</dt><dd>${e(t.doira || "")}</dd>
      <dt>To‘lov</dt><dd>${e(t.joy || "Naqd")}</dd>
      ${q.jami && q.jami !== q.summa ? `<dt>Rasxod jami</dt><dd class="hs-num">${uzs(q.jami)}</dd>` : ""}
      ${t.izoh ? `<dt>Izoh</dt><dd>${e(t.izoh)}</dd>` : ""}</dl>
      ${t.ulushlar && t.ulushlar.length ? `<h4>Ulushlar</h4>${t.ulushlar.map((u) => qator(u.nom, uzs(u.summa))).join("")}` : ""}
      ${t.mahsulotlar && t.mahsulotlar.length ? `<h4>Mahsulotlar</h4>${t.mahsulotlar.map((m) =>
        qator(m.miqdor > 1 ? `${m.nom} ×${m.miqdor}` : m.nom, uzs(m.summa))).join("")}` : ""}</div>`);
  }

  // ── «Davrni tanlang» oynasi ─────────────────────────────────────────
  const TEZ = [
    ["buoy", "Bu oy"], ["otgan", "O‘tgan oy"], ["7", "So‘nggi 7 kun"],
    ["30", "So‘nggi 30 kun"], ["yil", "Bu yil"], ["maxsus", "Maxsus davr"],
  ];
  function tezDavr(k, bugun) {
    switch (k) {
      case "buoy": return [oyBoshi(bugun), bugun];
      case "otgan": { const b = oySur(bugun, -1); return [b, oyOxiri(b)]; }
      case "7": return [kunQosh(bugun, -6), bugun];
      case "30": return [kunQosh(bugun, -29), bugun];
      case "yil": return [bugun.slice(0, 4) + "-01-01", bugun];
    }
    return null;
  }
  function davrOyna(boshlangich) {
    const bugun = H.bugun || (NAMUNA ? NB_.bugun : H.gacha);
    const Q = { a: (boshlangich || [H.dan])[0], b: (boshlangich || [, H.gacha])[1], oy: oyBoshi((boshlangich || [, H.gacha])[1]), tez: null };
    Q.tez = (TEZ.find(([k]) => { const r = tezDavr(k, bugun); return r && r[0] === Q.a && r[1] === Q.b; }) || ["maxsus"])[0];
    const p = document.createElement("div");
    p.className = "hs-parda";
    p.innerHTML = `<div class="hs-modal" role="dialog" aria-label="Davrni tanlang"></div>`;
    document.body.appendChild(p);
    const m = p.firstChild;
    const yop = () => { p.classList.remove("ochiq"); setTimeout(() => p.remove(), 180); document.removeEventListener("keydown", tugma); };
    const tugma = (ev) => { if (ev.key === "Escape") yop(); };
    document.addEventListener("keydown", tugma);
    function qur() {
      const boshKun = dan(Q.oy), offset = (boshKun.getUTCDay() + 6) % 7, kunlar = +oyOxiri(Q.oy).slice(8);
      let katak = "";
      for (let i = 0; i < offset; i++) katak += `<button disabled></button>`;
      for (let d = 1; d <= kunlar; d++) {
        const s = Q.oy.slice(0, 8) + String(d).padStart(2, "0");
        const b = Q.b || Q.a;
        const cls = [s === Q.a ? "hs-b0" : "", s === b ? "hs-b1" : "", s > Q.a && s < b ? "ora" : "",
          s === bugun ? "bugun" : "", s > bugun ? "kelajak" : ""].filter(Boolean).join(" ");
        katak += `<button class="${cls}" data-kun="${s}"><span>${d}</span></button>`;
      }
      const [, mo, y] = kunOy(Q.oy);
      m.innerHTML = `<div class="hs-modal-bosh"><h3>Davrni tanlang</h3><button class="hs-x" data-q="yop" aria-label="Yopish">${IK.x}</button></div>
        <div class="hs-modal-ich"><div class="hs-tez">${TEZ.map(([k, nom]) => `<button class="${Q.tez === k ? "faol" : ""}" data-tez="${k}">${nom}</button>`).join("")}</div>
        <div class="hs-taqvim"><div class="hs-oy"><button data-q="oldin" aria-label="Oldingi oy">${IK.chap}</button><b>${OY_T[mo]} ${y}</b><button data-q="keyin" aria-label="Keyingi oy">${IK.ong}</button></div>
        <div class="hs-kunlar">${HAFTA.map((h) => `<span class="hk">${h}</span>`).join("")}${katak}</div></div></div>
        <p class="hs-modal-izoh">${Q.b ? e(davrMatn(Q.a, Q.b)) : "Oxirgi kunni tanlang"}</p>
        <div class="hs-modal-past"><button class="hs-bekor" data-q="yop">Bekor qilish</button><button class="hs-qollash" data-q="qollash">Qo‘llash</button></div>`;
    }
    m.addEventListener("click", (ev) => {
      const t = ev.target.closest("button"); if (!t || t.disabled) return;
      if (t.dataset.kun) {
        const s = t.dataset.kun;
        if (!Q.a || Q.b) { Q.a = s; Q.b = null; }           // 1-bosish — boshlanish
        else if (s < Q.a) { Q.b = Q.a; Q.a = s; }           // teskari tanlansa — almashtiriladi
        else Q.b = s;                                       // 2-bosish — oxiri (bir kun ham mumkin)
        Q.tez = "maxsus"; tebran("soft"); return qur();
      }
      if (t.dataset.tez) {
        Q.tez = t.dataset.tez;
        const r = tezDavr(Q.tez, bugun);
        if (r) { [Q.a, Q.b] = r; Q.oy = oyBoshi(r[1]); }
        tebran("soft"); return qur();
      }
      switch (t.dataset.q) {
        case "yop": yop(); break;
        case "oldin": Q.oy = oySur(Q.oy, -1); qur(); break;
        case "keyin": Q.oy = oySur(Q.oy, 1); qur(); break;
        case "qollash": {
          const b = Q.b || Q.a;
          H.dan = Q.a; H.gacha = b;
          H.qolda = !(Q.a === oyBoshi(bugun) && b === bugun);   // «Bu oy» — avtomatik holatga qaytadi
          tebran(); yop(); H.stek.forEach((x) => { delete x.data; }); H.data = null; yukla(); break;
        }
      }
    });
    p.addEventListener("click", (ev) => { if (ev.target === p) yop(); });
    qur();
    requestAnimationFrame(() => p.classList.add("ochiq"));
  }

  // ── Sahifa hayoti ───────────────────────────────────────────────────
  let boshlandi = false;
  function boshla() {
    if (!boshlandi) { boshlandi = true; yukla(); }
    else if (!H.yuklanmoqda) yukla();      // qaytib kelinganda — yangi ma'lumot
  }
  window.addEventListener("sahifa", (ev) => {
    if (ev.detail && ev.detail.nom === "hisobotlar") boshla();
    else orqaTugma();
  });
  window.addEventListener("rasxod-saqlandi", () => { H.stek.forEach((x) => { delete x.data; }); if (korinadimi()) yukla(); });
  document.addEventListener("visibilitychange", () => { if (!document.hidden && korinadimi() && !NAMUNA && INIT) yukla(); });

  // Chuqur havola: #hisobotlar/kat/<id> …
  function xeshdan() {
    const m = /^#hisobotlar(?:\/(\w+)(?:\/(\d+))?)?$/.exec(location.hash);
    if (!m) return false;
    const [, tur, id] = m;
    if (NAMUNA && tur) {
      H.dan = "2026-09-01"; H.gacha = "2026-09-30"; H.bugun = NB_.bugun;
    }
    if (tur === "shaxsiy") { H.shaxsiy = true; H.odamId = NAMUNA ? 1 : null; H.doira = NAMUNA ? "1" : "umumiy"; }
    if (tur === "kat" && id) H.stek.push({ tur: "kat", idlar: [Number(id)] });
    if (tur === "royxat" && id) H.stek.push({ tur: "royxat", idlar: [Number(id)] });
    if (tur === "ichki" && id) {
      if (NAMUNA) H.stek.push({ tur: "kat", idlar: [11], nom: "Oziq-ovqat" });
      H.stek.push({ tur: "ichki", turi_id: Number(id), ozi: false });
    }
    if (window.sahifaga) window.sahifaga("hisobotlar", { xesh: false });
    boshla();
    if (tur === "davr") setTimeout(() => davrOyna(NAMUNA ? ["2026-09-05", "2026-09-14"] : null), 30);
    return true;
  }
  if (!xeshdan() && korinadimi()) boshla();
  window.addEventListener("hashchange", () => { if (/^#hisobotlar\//.test(location.hash)) { H.stek = [{ tur: "bosh" }]; xeshdan(); } });
})();
