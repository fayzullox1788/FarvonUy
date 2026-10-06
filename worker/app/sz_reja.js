// Sozlamalar → «Reja (budget)» — desktop «Analitika → Reja va fakt» paneli
// (sahifa_reja_fakt.py: RejaFaktPanel, RejaDialog, RejaYozuvDialog, RejaKategoriyaOyna).
// index.html yordamchilari ustida: api(), NAMUNA, INIT, xabar(), tebran(), e().
// API: worker/src/miniapp_sz_reja.js (/app/api/reja*), hisob — plan.js (Python
// core/plan.py egizagi). Doira: «Umumiy» — uyniki, «Shaxsiy» — ochgan odamniki.
// Qoidalar desktopniki: limit oynasi FAQAT limitni tahrirlaydi (yozuvlar limitga
// aylanmaydi), reja — faqat mo‘ljal (pul hech kimdan chiqmaydi), foiz 100 dan
// oshadi va yashirilmaydi, «Limitga yaqin» — 80% dan.
// Ekranlar — Sozlamalar ustidagi to‘liq sahifa (← va Telegram BackButton), manzil:
//   #sozlamalar/reja · …/reja/kat/<turi_id> · …/reja/yangi · …/reja/limitlar
(() => {
  const NB = " ";
  const fmt = (s) => String(Math.abs(Math.round(Number(s) || 0))).replace(/\B(?=(\d{3})+(?!\d))/g, NB);
  const som = (s) => `${s < 0 ? "−" : ""}${fmt(s)}${NB}so‘m`;
  const OYLAR = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];
  const oyNomi = (oy) => `${OYLAR[Number(oy.slice(5, 7)) - 1]} ${oy.slice(0, 4)}`;
  const oySur = (oy, q) => {
    const m = Number(oy.slice(5, 7)) - 1 + q, y = Number(oy.slice(0, 4)) + Math.floor(m / 12);
    return `${y}-${String(((m % 12) + 12) % 12 + 1).padStart(2, "0")}`;
  };
  const kunOy = (s) => `${s.slice(8, 10)}.${s.slice(5, 7)}`;
  const ILOVA = location.protocol === "file:" ? "" : "/app/";

  const svg = (d, o = 20, w = 1.8) => `<svg width="${o}" height="${o}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const IK = {
    orqa: svg(`<path d="M19.5 12h-15M10.5 5.5 4 12l6.5 6.5"/>`, 22, 2.1),
    chap: svg(`<path d="m14.5 5.5-6.5 6.5 6.5 6.5"/>`, 20, 2.2),
    ong: svg(`<path d="m9.5 5.5 6.5 6.5-6.5 6.5"/>`, 20, 2.2),
    ongK: `<svg class="ong" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="m9.5 5.5 6.5 6.5-6.5 6.5"/></svg>`,
    pastga: svg(`<path d="m6 9.5 6 6 6-6"/>`, 18, 2.1),
    plyus: svg(`<path d="M12 5v14M5 12h14"/>`, 18, 2.2),
    x: svg(`<path d="M6 6l12 12M18 6 6 18"/>`, 15, 2.4),
    sozla: svg(`<path d="M4 6.5h9M17 6.5h3M4 12h3M11 12h9M4 17.5h11M19 17.5h1"/><circle cx="15" cy="6.5" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="17.5" r="2"/>`, 19, 1.8),
    qalam: svg(`<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>`, 19, 1.9),
    nusxa: svg(`<rect x="8.5" y="8.5" width="12" height="12" rx="2.2"/><path d="M15.5 8.5V5.7a2.2 2.2 0 0 0-2.2-2.2H5.7a2.2 2.2 0 0 0-2.2 2.2v7.6a2.2 2.2 0 0 0 2.2 2.2h2.8"/>`, 19, 1.8),
    savat: svg(`<path d="M4 7h16M10 11v6M14 11v6"/><path d="M5.5 7l1 12a2 2 0 0 0 2 2h7a2 2 0 0 0 2-2l1-12M9 7V4.5h6V7"/>`, 19, 1.9),
    kochir: svg(`<path d="M4 12a8 8 0 0 1 13.7-5.6L20 8.5M20 4v4.5h-4.5M20 12a8 8 0 0 1-13.7 5.6L4 15.5M4 20v-4.5h4.5"/>`, 18, 1.9),
    ogoh: svg(`<path d="M12 3.5 2.5 20h19L12 3.5Z"/><path d="M12 10v4.5M12 17.5v.01"/>`, 18, 2),
    tamom: svg(`<path d="m5 12.5 4.5 4.5L19 7.5"/>`, 18, 2.4),
    oshdi: svg(`<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>`, 18, 2),
    reja: svg(`<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M8 3v4M16 3v4M3.5 10h17"/><path d="M8 14h3M8 17h6"/>`, 26, 1.7),
    yorliq: `<svg width="58%" height="58%" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="M3.5 12.2V4.5a1 1 0 0 1 1-1h7.7a1 1 0 0 1 .7.3l7.8 7.8a1 1 0 0 1 0 1.4l-7.7 7.7a1 1 0 0 1-1.4 0l-7.8-7.8a1 1 0 0 1-.3-.7Z"/><circle cx="8" cy="8" r="1.4"/></svg>`,
  };
  const HOLAT = {
    yaxshi: { rang: "#1fb76c", matn: "" },
    yaqin: { rang: "#f08a24", matn: "Limitga yaqin" },
    oshdi: { rang: "#f04646", matn: "Rejadan oshdi" },
    rejasiz: { rang: "#b7bfcc", matn: "Reja qo‘yilmagan" },
  };
  const belgi = (fayl, cls = "") => `<span class="sz-belgi rj-belgi ${cls}">${fayl
    ? `<img src="${ILOVA}belgilar/${e(fayl)}" alt="" decoding="async">` : IK.yorliq}</span>`;

  // ── Holat ──────────────────────────────────────────────────────────
  let el = null;           // sahifa (yopiq — null)
  let stek = [];           // [{t:"bosh"}] | [..., {t:"kat", id}]
  let oy = null;           // "YYYY-MM"; null — serverning joriy oyi
  let doira = "umumiy";    // umumiy | shaxsiy
  let bugun = "";
  let d = null;            // GET /reja javobi
  let kat = null;          // GET /reja/kategoriya javobi
  let F = null;            // forma: kategoriyalar, mahsulotlar
  let L = null;            // limitlar oynasi ma’lumoti
  let xatoMatn = "";
  let varaq = null;        // pastdan oyna
  let band = false;        // yozuv ketmoqda

  const ochiqmi = () => !!el;
  const joriy = () => stek[stek.length - 1];
  const joriyOy = () => oy || (bugun ? bugun.slice(0, 7) : "2026-10");

  // ── Namuna (file://) ───────────────────────────────────────────────
  const NM = {
    kategoriyalar: [
      { id: 2, nom: "Bozorlik", belgi_fayl: "food_17.svg", ichki: [{ id: 21, nom: "Mevalar", belgi_fayl: "food_11.svg", chuq: 0 }, { id: 22, nom: "Sabzavotlar", belgi_fayl: "personal_10.svg", chuq: 0 }] },
      { id: 5, nom: "Transport", belgi_fayl: "transportation_09.svg", ichki: [] },
      { id: 6, nom: "Kommunal", belgi_fayl: "transportation_05.svg", ichki: [] },
      { id: 3, nom: "Ro‘zg‘or", belgi_fayl: "life_08.svg", ichki: [] },
      { id: 8, nom: "Sog‘liq", belgi_fayl: "health_02.svg", ichki: [] },
      { id: 9, nom: "Ta’lim", belgi_fayl: "education_02.svg", ichki: [] },
    ],
    mahsulotlar: [
      { id: 101, nom: "Non", narx: 5000, turi_id: 2 }, { id: 102, nom: "Sut", narx: 14000, turi_id: 2 },
      { id: 103, nom: "Go‘sht", narx: 95000, turi_id: 2 }, { id: 104, nom: "Olma", narx: 18000, turi_id: 21 },
      { id: 105, nom: "Kartoshka", narx: 6000, turi_id: 22 },
    ],
  };
  function namunaQator(t, reja, fakt) {
    const k = NM.kategoriyalar.find((x) => x.id === t);
    const foiz = reja > 0 ? Math.floor((fakt * 200 + reja) / (2 * reja)) : null;
    const holat = reja <= 0 ? "rejasiz" : fakt > reja ? "oshdi" : foiz >= 80 ? "yaqin" : "yaxshi";
    return { turi_id: t, nom: k.nom, belgi_fayl: k.belgi_fayl, reja, fakt, qolgan: reja - fakt, foiz, holat };
  }
  function namunaAsosiy() {
    const o = joriyOy();
    const bor = o === "2026-10" || o === "2026-09";
    const qatorlar = !bor ? [] : doira === "umumiy" ? [
      namunaQator(2, 2_400_000, 1_860_000), namunaQator(5, 400_000, 455_000), namunaQator(6, 650_000, 540_000),
      namunaQator(3, 300_000, 96_000), namunaQator(8, 0, 120_000),
    ] : [namunaQator(9, 500_000, 210_000), namunaQator(5, 150_000, 132_000)];
    const reja = doira === "umumiy" ? (bor ? 4_000_000 : 0) : qatorlar.reduce((s, q) => s + q.reja, 0);
    const fakt = qatorlar.reduce((s, q) => s + q.fakt, 0);
    const foiz = reja > 0 ? Math.floor((fakt * 200 + reja) / (2 * reja)) : null;
    const oshgan = qatorlar.filter((q) => q.holat === "oshdi");
    return {
      bugun: "2026-10-02", oy: o, odam: { id: 1, nom: "Behruz" },
      rf: { oy: o, reja_bor: bor, umumiy_qoyilgan: bor && doira === "umumiy", reja, fakt, qolgan: reja - fakt, foiz,
        holat: reja <= 0 ? "rejasiz" : fakt > reja ? "oshdi" : foiz >= 80 ? "yaqin" : "yaxshi",
        turi_reja_jami: qatorlar.reduce((s, q) => s + q.reja, 0), qatorlar, diqqat: oshgan[0] || qatorlar.filter((q) => q.holat === "yaqin").sort((a, b) => b.foiz - a.foiz)[0] || null },
      kochir_mumkin: o === "2026-11", otgan: { oy: oySur(o, -1), bor: o === "2026-11" },
    };
  }
  function namunaKat(id) {
    const q = namunaAsosiy().rf.qatorlar.find((x) => x.turi_id === id) || namunaQator(id, 0, 0);
    const o = joriyOy();
    const yozuvlar = id === 2 ? [
      { id: 1, sana: o + "-01", nom: "Haftalik bozorlik", summa: 600_000, umumiymi: 1, turi_nom: "Bozorlik", mahsulotlar: [{ nom: "Go‘sht", miqdor: 4, summa: 380_000 }, { nom: "Non", miqdor: 20, summa: 100_000 }, { nom: "Sut", miqdor: 8, summa: 120_000 }] },
      { id: 2, sana: o + "-08", nom: "Haftalik bozorlik", summa: 600_000, umumiymi: 1, turi_nom: "Bozorlik", mahsulotlar: [{ nom: "Go‘sht", miqdor: 4, summa: 380_000 }, { nom: "Non", miqdor: 20, summa: 100_000 }, { nom: "Sut", miqdor: 8, summa: 120_000 }] },
      { id: 3, sana: o + "-12", nom: "Mevalar", summa: 200_000, umumiymi: 1, turi_nom: "Mevalar", mahsulotlar: [] },
    ] : [{ id: 4, sana: o + "-05", nom: q.nom, summa: q.reja, umumiymi: 1, turi_nom: q.nom, mahsulotlar: [] }];
    const limit = q.reja - yozuvlar.reduce((s, y) => s + y.summa, 0);
    return {
      turi: { id, nom: q.nom, belgi_fayl: q.belgi_fayl }, reja: q.reja, fakt: q.fakt, qolgan: q.qolgan, limit: Math.max(0, limit),
      yozuvlar,
      kunlar: [
        { sana: o + "-01", reja: 600_000, fakt: 640_000, royxatlar: ["Haftalik bozorlik"], holat: "40 000 oshdi" },
        { sana: o + "-04", reja: 0, fakt: 120_000, royxatlar: [], holat: "rejasiz" },
        { sana: o + "-08", reja: 600_000, fakt: 0, royxatlar: ["Haftalik bozorlik"], holat: "sarflanmagan" },
      ].filter(() => id === 2),
    };
  }
  function namunaLimit() {
    return {
      umumiy: 4_000_000, yozuv_jami: 1_400_000,
      kategoriyalar: NM.kategoriyalar.map((k, i) => ({ turi_id: k.id, nom: k.nom, belgi_fayl: k.belgi_fayl,
        reja: [1_000_000, 400_000, 650_000, 300_000, 0, 0][i], fakt: [1_860_000, 455_000, 540_000, 96_000, 120_000, 0][i],
        yozuv: [1_400_000, 0, 0, 0, 0, 0][i] })),
      otgan: { oy: oySur(joriyOy(), -1), bor: true, umumiy: 3_800_000, limitlar: { 2: 900_000, 5: 400_000 } },
    };
  }

  // ── Ma’lumot ───────────────────────────────────────────────────────
  const qs = (x) => Object.entries(x).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  async function yukla() {
    if (!el) return;
    const s = joriy();
    if (NAMUNA) {
      d = namunaAsosiy(); bugun = d.bugun;
      if (s.t === "kat") kat = namunaKat(s.id);
      return chiz();
    }
    if (!INIT) { xatoMatn = "Bu sahifani Telegram'dagi Farovon Hayot botidan oching."; return chiz(); }
    try {
      const so = { oy: joriyOy(), doira };
      if (!bugun) delete so.oy;
      const [j, k] = await Promise.all([
        api("reja?" + qs(so)),
        s.t === "kat" && bugun ? api("reja/kategoriya?" + qs({ ...so, turi_id: s.id })) : null,
      ]);
      d = j; bugun = j.bugun; xatoMatn = "";
      if (s.t === "kat") kat = k || await api("reja/kategoriya?" + qs({ oy: joriyOy(), doira, turi_id: s.id }));
    } catch (err) { xatoMatn = err.message; }
    chiz();
  }
  async function formaOl() {
    if (F) return F;
    F = NAMUNA ? NM : await api("reja/forma");
    return F;
  }
  async function yoz(yol, tana) {
    if (NAMUNA) { xabar("Namuna — saqlanmadi"); return { ok: true, id: 0 }; }
    return api("reja/" + yol, tana);
  }

  // ── Ochish / yopish / manzil ───────────────────────────────────────
  function och(yol = []) {
    if (!el) {
      el = document.createElement("section");
      el.className = "rj-sahifa";
      el.setAttribute("role", "dialog");
      el.setAttribute("aria-label", "Reja (budget)");
      el.addEventListener("click", bosildi);
      document.body.appendChild(el);
    }
    stek = [{ t: "bosh" }];
    if (yol[0] === "kat" && Number(yol[1])) stek.push({ t: "kat", id: Number(yol[1]) });
    kat = null;
    chiz();
    yukla().then(() => {
      if (yol[0] === "yangi") yozuvOch(null);
      if (yol[0] === "limitlar") limitOch();
    });
  }
  function yop() {
    oynaYop(true);
    if (el) { el.remove(); el = null; }
    stek = [];
    try { if (location.hash.startsWith("#sozlamalar/reja")) history.replaceState(null, "", "#sozlamalar"); } catch (err) {}
    tgOrqa();
  }
  function orqa() {
    if (varaq) {
      if (varaq.t === "tanla") { varaq = varaq.forma; return oynaChiz(); }
      return oynaYop();
    }
    if (stek.length > 1) { stek.pop(); kat = null; chiz(); el.scrollTop = 0; tebran("soft"); return; }
    yop();
  }
  function xeshYoz() {
    if (!el) return;
    const s = joriy();
    let x = "#sozlamalar/reja" + (s?.t === "kat" ? "/kat/" + s.id : "");
    if (varaq?.t === "yozuv" && !varaq.id) x = "#sozlamalar/reja/yangi";
    if (varaq?.t === "limit") x = "#sozlamalar/reja/limitlar";
    if (location.hash !== x) { try { history.replaceState(null, "", x); } catch (err) {} }
  }

  // ── Chizish ────────────────────────────────────────────────────────
  function chiz() {
    if (!el) return;
    el.innerHTML = joriy().t === "kat" ? katEkran() : boshEkran();
    xeshYoz();
    tgOrqa();
  }
  const sarlavha = (nom, ong = "") => `<div class="sz-bosh ichki rj-bosh">
      <button class="sz-orqa" data-amal="orqa" aria-label="Orqaga">${IK.orqa}</button><h1>${e(nom)}</h1>${ong}</div>`;
  function xatoHtml() {
    return xatoMatn ? `<div class="sz-royxat"><div class="sz-bosh-holat">${e(xatoMatn)}<br><button data-amal="qayta">Qayta urinish</button></div></div>` : "";
  }
  const chiziq = (foiz, holat, katta = false) => `<div class="rj-yol${katta ? " katta" : ""}"><i style="width:${Math.min(100, Math.max(0, foiz || 0))}%;background:${HOLAT[holat]?.rang || HOLAT.yaxshi.rang}"></i></div>`;

  function boshEkran() {
    const o = joriyOy();
    const umumiy = doira === "umumiy";
    const ong = d && umumiy ? `<button class="sz-ikon-tugma" data-amal="limit" aria-label="Umumiy reja va limitlar">${IK.sozla}</button>` : "";
    const yuqori = `${sarlavha("Reja (budget)", ong)}
      <div class="rj-oy">
        <button data-amal="oy-" aria-label="Oldingi oy">${IK.chap}</button>
        <b>${oyNomi(o)}</b>
        <button data-amal="oy+" aria-label="Keyingi oy">${IK.ong}</button>
        ${bugun && o !== bugun.slice(0, 7) ? `<button class="rj-buoy" data-amal="buoy">Bu oy</button>` : ""}
      </div>
      <div class="rj-seg" role="tablist">
        <button class="${umumiy ? "faol" : ""}" data-doira="umumiy">Umumiy</button>
        <button class="${umumiy ? "" : "faol"}" data-doira="shaxsiy">Shaxsiy</button>
      </div>`;
    if (xatoMatn) return yuqori + xatoHtml();
    if (!d) return yuqori + `<div class="rj-jami rj-skelet-jami"></div><div class="sz-royxat" style="margin-top:14px">${"<div class=\"sz-skelet\"></div>".repeat(4)}</div>`;
    const r = d.rf;
    if (!r.reja_bor) return yuqori + boshHolat(r);
    const oshdi = r.qolgan < 0;
    const izoh = !r.umumiy_qoyilgan && umumiy ? "Kategoriyalar rejasi yig‘indisi"
      : r.umumiy_qoyilgan && r.turi_reja_jami > r.reja ? `Kategoriyalar jami ko‘proq: ${fmt(r.turi_reja_jami)}` : "";
    const rejali = r.qatorlar.filter((q) => q.reja).length;
    const oshgan = r.qatorlar.filter((q) => q.holat === "oshdi").length;
    const rejasiz = r.qatorlar.filter((q) => !q.reja).reduce((s, q) => s + q.fakt, 0);
    const xulosa = [`${rejali} ta toifada reja`, oshgan ? `${oshgan} tasi oshdi` : "", rejasiz ? `rejasiz ${som(rejasiz)}` : ""].filter(Boolean).join(" · ");
    return `${yuqori}
      <div class="rj-jami ${r.holat}">
        <div class="ust"><span class="yorliq">${umumiy ? "Umumiy reja" : `${e(d.odam.nom)} — shaxsiy reja`}</span>
          <span class="foiz">${r.foiz ?? 0}%</span></div>
        <div class="summa">${fmt(r.reja)}<span>${NB}so‘m</span></div>
        ${izoh ? `<div class="izoh${r.umumiy_qoyilgan ? " ogoh" : ""}">${e(izoh)}</div>` : ""}
        ${chiziq(r.foiz, r.holat, true)}
        <div class="taqsim">
          <span><b style="background:${HOLAT[r.holat]?.rang}"></b>Sarflandi<em>${som(r.fakt)}</em></span>
          <span><b style="background:${oshdi ? "#ff8a8a" : "rgba(255,255,255,.55)"}"></b>${oshdi ? "Rejadan oshdi" : "Qolgan reja"}<em class="${oshdi ? "qizil" : ""}">${som(Math.abs(r.qolgan))}</em></span>
        </div>
      </div>
      ${diqqatHtml(r)}
      <div class="rj-tugmalar${umumiy ? "" : " bitta"}">
        <button class="sz-kok-tugma" data-amal="yangi">${IK.plyus}Reja qo‘shish</button>
        ${umumiy ? `<button class="sz-och-tugma rj-och" data-amal="limit">${IK.sozla}Limitlar</button>` : ""}
      </div>
      <div class="sz-bolim rj-bolim">Toifalar bo‘yicha<small class="alohida">${e(xulosa)}</small></div>
      ${r.qatorlar.length ? `<div class="sz-royxat rj-royxat">${r.qatorlar.map(qatorHtml).join("")}</div>`
        : `<div class="sz-royxat"><div class="sz-bosh-holat">Bu oyda hali rasxod ham, kategoriya rejasi ham yo‘q</div></div>`}
      <p class="rj-izoh">Toifani bosing — reja ro‘yxatlari, kunlar bo‘yicha sarf va qolgani. Reja faqat mo‘ljal: pul hech kimdan chiqmaydi, sarf rasxodlardan o‘zi hisoblanadi.</p>`;
  }
  function boshHolat(r) {
    const umumiy = doira === "umumiy";
    const otgan = oySur(r.oy, -1);
    return `<div class="rj-bosh-holat">
        <span class="rj-katta-belgi">${IK.reja}</span>
        <h3>Bu oy uchun ${umumiy ? "" : "shaxsiy "}reja yo‘q</h3>
        <p>Rejani rasxod kabi qo‘shing — kategoriya va ichidagi mahsulotlar bilan${umumiy ? " — yoki umumiy summa va limit qo‘ying" : ""}. Sarf rasxodlardan o‘zi hisoblanadi.</p>
        <p class="kul">${oyNomi(r.oy)} — hozirgacha sarflandi: <b>${som(r.fakt)}</b></p>
        <button class="sz-kok-tugma" data-amal="yangi">${IK.plyus}Reja qo‘shish</button>
        ${umumiy ? `<button class="sz-och-tugma" data-amal="limit">${IK.sozla}Umumiy summa yoki limit</button>` : ""}
        ${d.kochir_mumkin ? `<button class="sz-och-tugma" data-amal="kochir">${IK.kochir}${oyNomi(otgan)} rejasini ko‘chirish</button>` : ""}
      </div>`;
  }
  function diqqatHtml(r) {
    const q = r.diqqat;
    let holat, matn;
    if (q) {
      holat = q.holat;
      matn = holat === "oshdi" ? `<b>${e(q.nom)}</b> rejadan <b>${som(-q.qolgan)}</b> oshib ketdi — rejaning ${q.foiz}% i sarflandi.`
        : `<b>${e(q.nom)}</b> rejaning ${q.foiz}% ini ishlatdi. Qolgan limit: <b>${som(q.qolgan)}</b>.`;
    } else if (r.holat === "oshdi" || r.holat === "yaqin") {
      holat = r.holat;
      matn = holat === "oshdi" ? `Umumiy reja <b>${som(-r.qolgan)}</b> ga oshib ketdi.`
        : `Umumiy rejaning ${r.foiz}% i ishlatildi. Qolgan: <b>${som(r.qolgan)}</b>.`;
    } else { holat = "yaxshi"; matn = "Hamma toifalar reja doirasida."; }
    const ik = { oshdi: IK.oshdi, yaqin: IK.ogoh }[holat] || IK.tamom;
    return `<div class="rj-diqqat ${holat}">${ik}<span>${matn}</span></div>`;
  }
  function qatorHtml(q) {
    const h = HOLAT[q.holat] || HOLAT.yaxshi;
    const tegi = q.turi_id != null ? `data-kat="${q.turi_id}"` : "";
    const teg = q.turi_id != null ? "button" : "div";
    return `<${teg} class="sz-q rj-q" ${tegi}>
        ${belgi(q.belgi_fayl)}
        <span class="rj-q-ichi">
          <span class="rj-q-ust"><b>${e(q.nom)}</b><em style="color:${q.holat === "yaxshi" || q.holat === "rejasiz" ? "#5f6878" : h.rang}">${q.foiz == null ? "—" : q.foiz + "%"}</em></span>
          ${chiziq(q.foiz, q.holat)}
          <span class="rj-q-ost"><small>${fmt(q.fakt)} / ${q.reja ? fmt(q.reja) : "—"}</small>
            ${h.matn ? `<small class="holat" style="color:${q.holat === "rejasiz" ? "var(--kulrang)" : h.rang}">${h.matn}</small>`
              : `<small>qoldi ${fmt(q.qolgan)}</small>`}</span>
        </span>${q.turi_id != null ? IK.ongK : ""}</${teg}>`;
  }

  function katEkran() {
    const s = joriy();
    const q = d?.rf.qatorlar.find((x) => x.turi_id === s.id);
    const nom = kat?.turi.nom || q?.nom || "Kategoriya";
    const yuqori = sarlavha(nom);
    if (xatoMatn) return yuqori + xatoHtml();
    if (!kat) return yuqori + `<div class="sz-xulosa rj-skelet-xulosa"></div><div class="sz-royxat" style="margin-top:14px">${"<div class=\"sz-skelet\"></div>".repeat(3)}</div>`;
    const k = kat;
    const holat = k.reja <= 0 ? "rejasiz" : k.fakt > k.reja ? "oshdi" : (k.fakt * 100 >= 80 * k.reja ? "yaqin" : "yaxshi");
    const foiz = k.reja > 0 ? Math.floor((k.fakt * 200 + k.reja) / (2 * k.reja)) : null;
    const royxat = k.yozuvlar.map((y) => {
      const n = y.mahsulotlar.length;
      const qism = [n ? `${n} ta mahsulot` : "mahsulotsiz", y.turi_nom && y.turi_nom !== k.turi.nom ? e(y.turi_nom) : "", y.umumiymi ? "" : "shaxsiy"].filter(Boolean).join(" · ");
      return `<button class="sz-q rj-y" data-yozuv="${y.id}">
          <span class="rj-sana"><b>${y.sana.slice(8, 10)}</b>${OYLAR[Number(y.sana.slice(5, 7)) - 1].slice(0, 3).toLowerCase()}</span>
          <span class="rj-y-ichi"><b>${e(y.nom)}</b><small>${qism}</small></span>
          <span class="rj-y-summa">${fmt(y.summa)}</span>${IK.ongK}</button>`;
    }).join("") + (k.limit ? `<button class="sz-q rj-y" data-amal="limit-qator">
          <span class="rj-sana limit">${IK.sozla}</span>
          <span class="rj-y-ichi"><b>Limit</b><small>mahsulotsiz, butun oyga</small></span>
          <span class="rj-y-summa">${fmt(k.limit)}</span>${IK.ongK}</button>` : "");
    const kunlar = k.kunlar.map((x) => {
      const rang = /oshdi/.test(x.holat) ? "#e0393a" : /qoldi|sarflanmagan/.test(x.holat) ? "#1d9d63" : x.holat === "rejasiz" ? "#b4690e" : "#5f6878";
      return `<div class="rj-kun">
          <span class="rj-kun-sana">${kunOy(x.sana)}</span>
          <span class="rj-kun-ichi"><b>${x.royxatlar.length ? e(x.royxatlar.join(", ")) : "— rejasiz rasxod"}</b>
            <small>reja ${x.reja ? fmt(x.reja) : "—"} · sarf ${x.fakt ? fmt(x.fakt) : "—"}</small></span>
          <span class="rj-kun-holat" style="color:${rang}">${e(x.holat)}</span></div>`;
    }).join("");
    return `${yuqori}
      <div class="sz-xulosa rj-xulosa">
        ${belgi(k.turi.belgi_fayl, "katta")}
        <div class="rj-x-ichi">
          <div class="rj-x-ust"><small>${oyNomi(joriyOy())} · ${doira === "umumiy" ? "umumiy" : "shaxsiy"}</small><em style="color:${holat === "yaxshi" || holat === "rejasiz" ? "#5f6878" : HOLAT[holat].rang}">${foiz == null ? "" : foiz + "%"}</em></div>
          ${chiziq(foiz, holat)}
          <div class="rj-uch">
            <span>Reja<b>${fmt(k.reja)}</b></span><span>Sarflandi<b>${fmt(k.fakt)}</b></span>
            <span>${k.qolgan < 0 ? "Oshdi" : "Qoldi"}<b class="${k.qolgan < 0 ? "qizil" : "yashil"}">${fmt(Math.abs(k.qolgan))}</b></span>
          </div>
        </div>
      </div>
      <div class="sz-bolim rj-bolim">Reja ro‘yxatlari<small>${k.yozuvlar.length ? k.yozuvlar.length + " ta" : ""}</small></div>
      <button class="sz-och-tugma" data-amal="yangi">${IK.plyus}Yangi ro‘yxat</button>
      ${royxat ? `<div class="sz-royxat">${royxat}</div>` : `<div class="sz-royxat"><div class="sz-bosh-holat">Bu toifada hali reja ro‘yxati yo‘q</div></div>`}
      <div class="sz-bolim rj-bolim">Kunlar bo‘yicha</div>
      ${kunlar ? `<div class="sz-royxat rj-kunlar">${kunlar}</div>` : `<div class="sz-royxat"><div class="sz-bosh-holat">Bu oy bu toifada reja ham, rasxod ham yo‘q</div></div>`}
      <p class="rj-izoh">Reja — kategoriyaga ajratilgan pul: shu kategoriyadan qilingan har qanday rasxod undan ayiriladi, ro‘yxatdagi mahsulotlar faqat tafsilot.</p>`;
  }

  // ── Pastdan oynalar ────────────────────────────────────────────────
  let parda, oyna;
  function oynaElementlari() {
    if (oyna) return;
    parda = document.createElement("div"); parda.className = "sz-parda rj-parda";
    oyna = document.createElement("div"); oyna.className = "sz-oyna rj-oyna"; oyna.setAttribute("role", "dialog");
    document.body.append(parda, oyna);
    parda.onclick = () => oynaYop();
    oyna.addEventListener("click", oynaBosildi);
    oyna.addEventListener("input", oynaKiritildi);
    oyna.addEventListener("change", oynaKiritildi);
  }
  function oynaOch(v, fokus) {
    varaq = v; oynaChiz(); xeshYoz(); tgOrqa();
    if (fokus) setTimeout(() => document.getElementById(fokus)?.focus(), 260);
  }
  function oynaYop(jim = false) {
    varaq = null;
    if (oyna) { parda.classList.remove("ochiq"); oyna.classList.remove("ochiq"); }
    if (!jim) { xeshYoz(); tgOrqa(); }
  }
  const oynaSarlavha = (matn, orqaga = false) => `<div class="sz-oyna-bosh">${orqaga
    ? `<button class="sz-orqa" data-o="orqa" aria-label="Orqaga">${IK.orqa}</button>` : ""}<h3>${matn}</h3>
      <button class="sz-yop" data-o="yop" aria-label="Yopish">${IK.x}</button></div>`;
  function oynaChiz() {
    oynaElementlari();
    const och = !!varaq && !!el;
    parda.classList.toggle("ochiq", och);
    oyna.classList.toggle("ochiq", och);
    if (!och) return;
    oyna.classList.toggle("toliq", varaq.t === "yozuv" || varaq.t === "tanla" || varaq.t === "limit");
    const sc = oyna.querySelector(".rj-aylan")?.scrollTop || 0;
    oyna.innerHTML = { yozuv: yozuvHtml, tanla: tanlaHtml, limit: limitHtml, menyu: menyuHtml, tasdiq: tasdiqHtml }[varaq.t](varaq);
    const a = oyna.querySelector(".rj-aylan");
    if (a && varaq.t !== "tanla") a.scrollTop = sc;
  }
  const pulInput = (id, qiymat, attr = "") => `<label class="rj-pul"><input class="sz-kirit" id="${id}" inputmode="numeric" autocomplete="off" value="${qiymat ? fmt(qiymat) : ""}" placeholder="0" ${attr}><span>so‘m</span></label>`;
  const raqam = (s) => { const t = String(s ?? "").replace(/\D/g, ""); return t ? Number(t) : 0; };

  // · Reja yozuvi (RejaYozuvDialog)
  async function yozuvOch(id, turi = null) {
    if (band) return;
    try { await formaOl(); } catch (err) { return xabar(err.message); }
    const o = joriyOy();
    const sana = bugun && bugun.slice(0, 7) === o ? bugun : o + "-01";
    let f = { t: "yozuv", id: null, sana, kat: null, ichki: null, nom: "", summa: 0, mahsulotlar: [], doira, xato: "" };
    if (turi != null) {
      if (F.kategoriyalar.some((k) => k.id === turi)) f.kat = turi;
    }
    if (id != null) {
      try {
        const y = NAMUNA ? { ...kat.yozuvlar.find((x) => x.id === id), turi_id: kat.turi.id, ildiz: kat.turi.id, umumiymi: 1 }
          : (await api("reja/yozuv/" + id)).yozuv;
        f = { ...f, id, sana: y.sana || sana, kat: y.ildiz ?? y.turi_id, ichki: y.ildiz != null && y.ildiz !== y.turi_id ? y.turi_id : null,
          nom: y.nom || "", summa: y.summa, doira: y.umumiymi ? "umumiy" : "shaxsiy",
          mahsulotlar: (y.mahsulotlar || []).map((m) => ({ item_id: m.item_id ?? null, nom: m.nom, miqdor: m.miqdor || 1, summa: m.summa })) };
      } catch (err) { return xabar(err.message); }
    }
    oynaOch(f, id == null && turi == null ? null : null);
  }
  const katOl = (id) => F?.kategoriyalar.find((k) => k.id === id) || null;
  /** Tanlangan kategoriya va ichkilaridagi mahsulotlar (datalist uchun). */
  function katMahsulotlari(f) {
    const k = katOl(f.kat); if (!k) return [];
    const idlar = new Set(f.ichki != null ? [f.ichki] : [k.id, ...k.ichki.map((x) => x.id)]);
    if (f.ichki != null) {
      // ichkining avlodlari (chuqurroq) — tekis ro‘yxatdan
      const i = k.ichki.findIndex((x) => x.id === f.ichki);
      for (let j = i + 1; j < k.ichki.length && k.ichki[j].chuq > k.ichki[i].chuq; j++) idlar.add(k.ichki[j].id);
    }
    return F.mahsulotlar.filter((m) => idlar.has(m.turi_id));
  }
  const mJami = (f) => f.mahsulotlar.reduce((s, m) => s + (Number(m.summa) || 0), 0);
  function yozuvHtml(f) {
    const k = katOl(f.kat);
    const ik = k && f.ichki != null ? k.ichki.find((x) => x.id === f.ichki) : null;
    const mahs = katMahsulotlari(f);
    const bormi = f.mahsulotlar.length > 0;
    const mq = f.mahsulotlar.map((m, i) => `<div class="rj-m" data-i="${i}">
        <input class="sz-kirit rj-m-nom" data-m="nom" list="rjMahs" value="${e(m.nom)}" placeholder="Mahsulot" autocomplete="off">
        <input class="sz-kirit rj-m-son" data-m="miqdor" inputmode="numeric" value="${m.miqdor || ""}" placeholder="1" aria-label="Miqdor">
        <input class="sz-kirit rj-m-sum" data-m="summa" inputmode="numeric" value="${m.summa ? fmt(m.summa) : ""}" placeholder="Summa" aria-label="Summa">
        <button class="rj-m-x" data-o="m-x" aria-label="Olib tashlash">${IK.x}</button></div>`).join("");
    return `${oynaSarlavha(f.id ? "Rejani tahrirlash" : `Rejaga qo‘shish — ${oyNomi(joriyOy())}`)}
      <div class="rj-aylan">
        <span class="sz-yorliq">Reja kimniki</span>
        <div class="rj-seg kichik">
          <button class="${f.doira === "umumiy" ? "faol" : ""}" data-o="doira" data-v="umumiy">Umumiy</button>
          <button class="${f.doira === "shaxsiy" ? "faol" : ""}" data-o="doira" data-v="shaxsiy">Shaxsiy</button>
        </div>
        <label class="sz-yorliq" for="rjSana">Sana</label>
        <input class="sz-kirit" type="date" id="rjSana" value="${e(f.sana)}">
        <span class="sz-yorliq">Kategoriya <i class="rj-shart">*</i></span>
        <button class="sz-boshqa rj-tanla" data-o="tanla" data-v="kat">${k ? belgi(k.belgi_fayl, "kichik") : belgi(null, "kichik")}<span class="${k ? "" : "bosh"}">${k ? e(k.nom) : "Kategoriyani tanlang"}</span>${IK.pastga}</button>
        ${k && k.ichki.length ? `<span class="sz-yorliq">Pad kategoriya</span>
        <button class="sz-boshqa rj-tanla" data-o="tanla" data-v="ichki">${belgi(ik ? ik.belgi_fayl : k.belgi_fayl, "kichik")}<span class="${ik ? "" : "bosh"}">${ik ? e(ik.nom) : "— ichki kategoriyasiz —"}</span>${IK.pastga}</button>` : ""}
        <span class="sz-yorliq">Mahsulotlar <i class="ixtiyoriy">(ixtiyoriy)</i></span>
        ${bormi ? `<div class="rj-m-sar"><span>Mahsulot</span><span>Soni</span><span>Summa</span><span></span></div>${mq}` : ""}
        <datalist id="rjMahs">${mahs.map((m) => `<option value="${e(m.nom)}">${m.narx ? fmt(m.narx) + " so‘m" : ""}</option>`).join("")}</datalist>
        <button class="rj-m-qosh" data-o="m-qosh">${IK.plyus}Mahsulot qo‘shish</button>
        <label class="sz-yorliq" for="rjNom">Nomi / sabab <i class="rj-shart">*</i></label>
        <input class="sz-kirit" id="rjNom" value="${e(f.nom)}" placeholder="masalan: Haftalik bozorlik" autocomplete="off">
        <label class="sz-yorliq" for="rjSumma">Summa${bormi ? ` <i class="ixtiyoriy">— mahsulotlar yig‘indisi</i>` : ""}</label>
        ${pulInput("rjSumma", bormi ? mJami(f) : f.summa, bormi ? "readonly" : "")}
        <p class="sz-izoh rj-oyna-izoh">Reja — faqat mo‘ljal: pul hech kimdan chiqmaydi. Sana qaysi oyga tushsa, o‘sha oyning rejasiga qo‘shiladi.</p>
        ${f.xato ? `<div class="rj-xato">${e(f.xato)}</div>` : ""}
        <div class="${f.id ? "sz-ikki" : ""}">
          ${f.id ? `<button class="sz-kulrang-tugma rj-qizil-matn" data-o="ochirSora">O‘chirish</button>` : ""}
          <button class="sz-kok-tugma" data-o="saqla"${band ? " disabled" : ""}>Saqlash</button>
        </div>
      </div>`;
  }
  function tanlaHtml(v) {
    const f = v.forma;
    let qatorlar, sarlavha;
    if (v.qaysi === "kat") {
      sarlavha = "Kategoriya";
      qatorlar = F.kategoriyalar.map((x) => ({ id: x.id, nom: x.nom, belgi_fayl: x.belgi_fayl, chuq: 0, tanlangan: x.id === f.kat, ichki: x.ichki.length }));
    } else {
      const k = katOl(f.kat);
      sarlavha = "Pad kategoriya";
      qatorlar = [{ id: "", nom: "— ichki kategoriyasiz —", belgi_fayl: k.belgi_fayl, chuq: 0, tanlangan: f.ichki == null },
        ...k.ichki.map((x) => ({ ...x, tanlangan: x.id === f.ichki }))];
    }
    return `${oynaSarlavha(sarlavha, true)}
      <div class="rj-aylan"><div class="sz-royxat rj-tanla-royxat">${qatorlar.map((x) => `<button class="sz-q${x.tanlangan ? " tanlangan" : ""}" data-o="tanlandi" data-v="${x.id}" style="padding-left:${10 + x.chuq * 18}px">
        ${belgi(x.belgi_fayl)}<span class="nom">${e(x.nom)}</span>${x.ichki ? `<span class="son">${x.ichki}</span>` : ""}${x.tanlangan ? `<span class="rj-tik">${IK.tamom}</span>` : ""}</button>`).join("")}</div></div>`;
  }

  // · Umumiy reja va limitlar (RejaDialog)
  async function limitOch() {
    if (band) return;
    try {
      L = NAMUNA ? namunaLimit() : await api("reja/limitlar?" + qs({ oy: joriyOy() }));
    } catch (err) { return xabar(err.message); }
    oynaOch({ t: "limit", umumiy: L.umumiy || 0, qiymat: Object.fromEntries(L.kategoriyalar.map((k) => [k.turi_id, k.reja])), xato: "" });
  }
  function limitJami(v) {
    return Object.values(v.qiymat).reduce((s, x) => s + (Number(x) || 0), 0) + (L?.yozuv_jami || 0);
  }
  function limitJamiMatn(v) {
    const j = limitJami(v);
    return `Kategoriyalar jami (yozuvlar bilan): <b>${som(j)}</b>` +
      (v.umumiy && j > v.umumiy ? ` — umumiy rejadan ${som(j - v.umumiy)} ko‘p` : "");
  }
  function limitHtml(v) {
    return `${oynaSarlavha("Umumiy reja va limitlar")}
      <div class="rj-aylan">
        <p class="sz-matn rj-oy-izoh">${oyNomi(joriyOy())}</p>
        <label class="sz-yorliq" for="rjUmumiy">Umumiy oylik reja</label>
        ${pulInput("rjUmumiy", v.umumiy, `placeholder="kategoriyalar yig‘indisi"`)}
        <p class="sz-izoh">Bo‘sh qoldirilsa, oylik reja kategoriyalar rejasining yig‘indisi bo‘ladi.</p>
        <span class="sz-yorliq">Kategoriya limitlari</span>
        <p class="sz-izoh">Limit kiritilgan reja yozuvlariga QO‘SHILADI. Mahsulotlar bilan reja — «Reja qo‘shish».</p>
        <div class="sz-royxat rj-limitlar">${L.kategoriyalar.map((k) => {
          const qism = [k.yozuv ? `yozuvlar ${fmt(k.yozuv)}` : "", k.fakt ? `fakt ${fmt(k.fakt)}` : ""].filter(Boolean).join(" · ");
          return `<div class="sz-q rj-l">${belgi(k.belgi_fayl)}<span class="rj-l-ichi"><b>${e(k.nom)}</b>${qism ? `<small>${qism}</small>` : ""}</span>
            <input class="sz-kirit rj-l-pul" data-l="${k.turi_id}" inputmode="numeric" autocomplete="off" value="${v.qiymat[k.turi_id] ? fmt(v.qiymat[k.turi_id]) : ""}" placeholder="0"></div>`;
        }).join("")}</div>
        <p class="rj-jami-matn" id="rjLJami">${limitJamiMatn(v)}</p>
        ${v.xato ? `<div class="rj-xato">${e(v.xato)}</div>` : ""}
        <div class="${L.otgan.bor ? "sz-ikki" : ""}">
          ${L.otgan.bor ? `<button class="sz-kulrang-tugma" data-o="otgan">${oyNomi(L.otgan.oy).split(" ")[0]}dan olish</button>` : ""}
          <button class="sz-kok-tugma" data-o="limitSaqla"${band ? " disabled" : ""}>Saqlash</button>
        </div>
      </div>`;
  }

  // · Ro‘yxat amallari va tasdiq
  function menyuHtml(v) {
    const y = v.y;
    const m = y.mahsulotlar || [];
    return `${oynaSarlavha(e(y.nom))}
      <p class="sz-matn rj-menyu-izoh">${kunOy(y.sana)} · ${som(y.summa)} · ${y.umumiymi ? "umumiy" : "shaxsiy"}</p>
      ${m.length ? `<div class="rj-menyu-m">${m.map((x) => `<span><b>${e(x.nom)}</b><i>× ${x.miqdor}</i><em>${fmt(x.summa)}</em></span>`).join("")}</div>` : ""}
      <div class="rj-menyu">
        <button data-o="tahrir">${IK.qalam}<span>Tahrirlash<small>sana, mahsulotlar, umumiy/shaxsiy</small></span></button>
        <button data-o="nusxa">${IK.nusxa}<span>Nusxa olish<small>keyingi kunga, mahsulotlari bilan</small></span></button>
        <button class="xavf" data-o="ochirSora">${IK.savat}<span>O‘chirish</span></button>
      </div>`;
  }
  function tasdiqHtml(v) {
    return `${oynaSarlavha(v.sarlavha)}<p class="sz-matn">${v.matn}</p>
      ${v.xato ? `<div class="rj-xato">${e(v.xato)}</div>` : ""}
      <div class="sz-ikki"><button class="sz-kulrang-tugma" data-o="yop">Bekor qilish</button>
        <button class="sz-qizil-tugma" data-o="tasdiq"${band ? " disabled" : ""}>${v.tugma || "O‘chirish"}</button></div>`;
  }

  // ── Hodisalar ──────────────────────────────────────────────────────
  function bosildi(ev) {
    const t = ev.target.closest("button"); if (!t) return;
    if (t.dataset.doira) {
      if (doira !== t.dataset.doira) { doira = t.dataset.doira; d = null; kat = null; chiz(); yukla(); tebran("soft"); }
      return;
    }
    if (t.dataset.kat) { stek.push({ t: "kat", id: Number(t.dataset.kat) }); kat = null; chiz(); el.scrollTop = 0; tebran("soft"); yukla(); return; }
    if (t.dataset.yozuv) {
      const y = kat?.yozuvlar.find((x) => x.id === Number(t.dataset.yozuv));
      if (y) { tebran("soft"); oynaOch({ t: "menyu", y }); }
      return;
    }
    const a = t.dataset.amal;
    if (a === "orqa") return orqa();
    if (a === "qayta") { xatoMatn = ""; chiz(); return yukla(); }
    if (a === "oy-" || a === "oy+" || a === "buoy") {
      oy = a === "buoy" ? null : oySur(joriyOy(), a === "oy-" ? -1 : 1);
      if (bugun && oy === bugun.slice(0, 7)) oy = null;
      d = null; kat = null; chiz(); tebran("soft"); return yukla();
    }
    if (a === "yangi") return yozuvOch(null, joriy().t === "kat" ? joriy().id : null);
    if (a === "limit") return limitOch();
    if (a === "kochir") return kochir();
    if (a === "limit-qator" && kat) {
      return oynaOch({ t: "tasdiq", sarlavha: "Limitni olib tashlash", tugma: "Olib tashlash", amal: "limitOchir",
        matn: `<b>${e(kat.turi.nom)}</b> limiti (${som(kat.limit)}) shu oy rejasidan olib tashlansinmi? Limitni o‘zgartirish — «Limitlar» oynasida.` });
    }
  }
  async function kochir() {
    if (band) return;
    band = true;
    try { await yoz("kochir", { oy: joriyOy() }); tebran("medium"); xabar("Reja ko‘chirildi"); }
    catch (err) { xabar(err.message); }
    band = false;
    d = null; chiz(); yukla();
  }

  function oynaKiritildi(ev) {
    const t = ev.target;
    if (!varaq) return;
    if (varaq.t === "yozuv") {
      const f = varaq;
      if (t.id === "rjSana") f.sana = t.value;
      if (t.id === "rjNom") f.nom = t.value;
      if (t.id === "rjSumma") { f.summa = raqam(t.value); t.value = f.summa ? fmt(f.summa) : ""; }
      const qator = t.closest(".rj-m");
      if (qator && t.dataset.m) {
        const m = f.mahsulotlar[Number(qator.dataset.i)];
        if (t.dataset.m === "nom") {
          m.nom = t.value;
          const top = katMahsulotlari(f).find((x) => x.nom.toLowerCase() === t.value.trim().toLowerCase());
          m.item_id = top ? top.id : null;
          if (top && top.narx && !m.summa && ev.type === "input") {
            m.summa = top.narx * (m.miqdor || 1);
            qator.querySelector(".rj-m-sum").value = fmt(m.summa);
          }
        } else if (t.dataset.m === "miqdor") {
          const eski = m.miqdor || 1;
          m.miqdor = raqam(t.value) || 0;
          t.value = m.miqdor || "";
          // Katalog narxi bilan to‘ldirilgan summa miqdorga ergashadi
          const top = F.mahsulotlar.find((x) => x.id === m.item_id);
          if (top && top.narx && m.summa === top.narx * eski && m.miqdor) {
            m.summa = top.narx * m.miqdor; qator.querySelector(".rj-m-sum").value = fmt(m.summa);
          }
        } else {
          m.summa = raqam(t.value); t.value = m.summa ? fmt(m.summa) : "";
        }
        const s = document.getElementById("rjSumma");
        if (s) s.value = mJami(f) ? fmt(mJami(f)) : "";
      }
      return;
    }
    if (varaq.t === "limit") {
      if (t.id === "rjUmumiy") { varaq.umumiy = raqam(t.value); t.value = varaq.umumiy ? fmt(varaq.umumiy) : ""; }
      if (t.dataset.l) { varaq.qiymat[t.dataset.l] = raqam(t.value); t.value = varaq.qiymat[t.dataset.l] ? fmt(varaq.qiymat[t.dataset.l]) : ""; }
      const j = document.getElementById("rjLJami"); if (j) j.innerHTML = limitJamiMatn(varaq);
    }
  }

  async function oynaBosildi(ev) {
    const t = ev.target.closest("button"); if (!t) return;
    const o = t.dataset.o; if (!o || !varaq) return;
    const v = varaq;
    if (o === "yop") return oynaYop();
    if (o === "orqa") return orqa();
    if (o === "doira") { v.doira = t.dataset.v; return oynaChiz(); }
    if (o === "tanla") {
      if (t.dataset.v === "ichki" && !katOl(v.kat)) return;
      varaq = { t: "tanla", qaysi: t.dataset.v, forma: v }; return oynaChiz();
    }
    if (o === "tanlandi") {
      const f = v.forma, id = t.dataset.v === "" ? null : Number(t.dataset.v);
      if (v.qaysi === "kat") {
        if (id !== f.kat) { f.kat = id; f.ichki = null; }
        const k = katOl(id);
        varaq = f;
        if (k && k.ichki.length && v.qaysi === "kat") { varaq = { t: "tanla", qaysi: "ichki", forma: f }; }
      } else { f.ichki = id; varaq = f; }
      tebran("soft");
      return oynaChiz();
    }
    if (o === "m-qosh") {
      v.mahsulotlar.push({ item_id: null, nom: "", miqdor: 1, summa: 0 });
      oynaChiz();
      const n = oyna.querySelectorAll(".rj-m-nom"); n[n.length - 1]?.focus();
      return;
    }
    if (o === "m-x") {
      v.mahsulotlar.splice(Number(t.closest(".rj-m").dataset.i), 1);
      if (!v.mahsulotlar.length) v.summa = 0;
      return oynaChiz();
    }
    if (o === "saqla") return yozuvSaqla(v);
    if (o === "otgan") {
      v.umumiy = L.otgan.umumiy || 0;
      for (const k of Object.keys(v.qiymat)) v.qiymat[k] = L.otgan.limitlar[k] || 0;
      tebran("soft");
      return oynaChiz();
    }
    if (o === "limitSaqla") return limitSaqla(v);
    if (o === "tahrir") return yozuvOch(v.y.id);
    if (o === "nusxa") return bajar(() => yoz(`yozuv/${v.y.id}/nusxa`, {}), "Nusxa keyingi kunga qo‘shildi");
    if (o === "ochirSora") {
      const y = v.t === "menyu" ? v.y : { id: v.id, nom: v.nom, summa: v.mahsulotlar.length ? mJami(v) : v.summa };
      return oynaOch({ t: "tasdiq", sarlavha: "Rejani o‘chirish", amal: "yozuvOchir", id: y.id,
        matn: `«<b>${e(y.nom)}</b>» (${som(y.summa)}) rejadan o‘chirilsinmi? Unga yozilgan haqiqiy rasxod bo‘lsa — o‘chmaydi.` });
    }
    if (o === "tasdiq") {
      if (v.amal === "yozuvOchir") return bajar(() => yoz(`yozuv/${v.id}/ochir`, {}), "Reja o‘chirildi");
      if (v.amal === "limitOchir") return bajar(() => yoz("limit/ochir", { oy: joriyOy(), turi_id: kat.turi.id }), "Limit olib tashlandi");
    }
  }
  /** Yozuv amali → oyna yopiladi, ekran yangilanadi; xato — oynada. */
  async function bajar(fn, ok) {
    if (band) return;
    band = true;
    try { await fn(); band = false; oynaYop(); tebran("medium"); xabar(ok); await yukla(); }
    catch (err) { band = false; if (varaq) { varaq.xato = err.message; oynaChiz(); } else xabar(err.message); }
  }
  function yozuvSaqla(f) {
    let nom = f.nom.trim();
    const mahsulotlar = f.mahsulotlar.filter((m) => m.nom.trim() || m.summa);
    if (!nom && mahsulotlar.length) {
      // desktop MahsulotRoyxat: sabab bo‘sh bo‘lsa — mahsulot nomlari (rk.qatorlar_nomi)
      nom = mahsulotlar.map((m) => (m.miqdor > 1 ? `${m.nom.trim()} ×${m.miqdor}` : m.nom.trim())).join(", ");
      if (nom.length > 60) nom = nom.slice(0, 59) + "…";
    }
    const tana = {
      sana: f.sana, nom, turi_id: f.ichki ?? f.kat, doira: f.doira,
      summa: mahsulotlar.length ? mJami({ mahsulotlar }) : f.summa,
      mahsulotlar: mahsulotlar.map((m) => ({ item_id: m.item_id, nom: m.nom.trim(), miqdor: m.miqdor || 1, summa: m.summa })),
    };
    if (f.kat == null) { f.xato = "Kategoriyani tanlang."; return oynaChiz(); }
    // Sana boshqa oyga tushsa — o‘sha oyga o‘tamiz (yozuv o‘sha oy rejasiga qo‘shiladi)
    return bajar(async () => {
      await yoz(f.id ? `yozuv/${f.id}` : "yozuv", tana);
      if (tana.sana && tana.sana.slice(0, 7) !== joriyOy()) {
        oy = bugun && tana.sana.slice(0, 7) === bugun.slice(0, 7) ? null : tana.sana.slice(0, 7);
      }
    }, f.id ? "Reja saqlandi" : "Rejaga qo‘shildi");
  }
  function limitSaqla(v) {
    return bajar(() => yoz("limitlar", { oy: joriyOy(), umumiy: v.umumiy || 0, limitlar: v.qiymat }), "Reja saqlandi");
  }

  // ── Telegram «Orqaga» ──────────────────────────────────────────────
  const TB = window.Telegram && Telegram.WebApp && Telegram.WebApp.BackButton;
  let tbKorinadi = false;
  if (TB) { try { TB.onClick(() => { if (ochiqmi()) orqa(); }); } catch (err) {} }
  function tgOrqa() {
    if (!TB) return;
    const kerak = ochiqmi();
    try {
      if (kerak && !tbKorinadi) TB.show();
      if (!kerak && tbKorinadi) TB.hide();
    } catch (err) {}
    tbKorinadi = kerak;
  }

  // ── Ro‘yxatdan o‘tish va havola ────────────────────────────────────
  window.SozlamaBolimi = window.SozlamaBolimi || {};
  window.SozlamaBolimi.reja = () => och();

  /** «#sozlamalar/reja[/kat/<id>|/yangi|/limitlar]» → ochish. */
  function havola(xesh) {
    const m = String(xesh || "").match(/^#sozlamalar\/reja(?:\/(kat\/\d+|yangi|limitlar))?\/?$/);
    if (!m) return false;
    if (document.getElementById("sahifa-sozlamalar")?.hidden) return false;
    och(m[1] ? m[1].split("/") : []);
    return true;
  }
  // sozlama.js xeshni o‘zinikiga qaytarib yozadi — boshlang‘ich manzil navigatsiya
  // yozuvidan ham olinadi; u qayta chizganda manzil va BackButton bizga qaytadi.
  let boshXesh = location.hash;
  try { const n = performance.getEntriesByType("navigation")[0]; if (n && n.name.includes("#")) boshXesh = "#" + n.name.split("#")[1]; } catch (err) {}
  if (!havola(location.hash)) havola(boshXesh);
  const sz = document.getElementById("sahifa-sozlamalar");
  if (sz) new MutationObserver(() => { if (ochiqmi()) { xeshYoz(); tbKorinadi = false; tgOrqa(); } }).observe(sz, { childList: true });
  window.addEventListener("hashchange", (ev) => {
    try { const x = new URL(ev.newURL).hash; if (!ochiqmi()) havola(x); } catch (err) {}
  });
  window.addEventListener("sahifa", (ev) => { if (ev.detail?.nom !== "sozlamalar" && ochiqmi()) yop(); });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && ochiqmi() && !NAMUNA && INIT && !varaq) yukla();
  });
})();
