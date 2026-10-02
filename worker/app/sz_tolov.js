// Sozlamalar → «To‘lov usullari» — desktop «Hamyon» (pulim qayerda: naqd + kartalar).
// index.html yordamchilari ustida: api(), NAMUNA, INIT, xabar(), tebran(), e().
// API: worker/src/miniapp_sz_tolov.js (/app/api/tolov*), hisob — hamyon.js (Python
// core/hamyon.py egizagi). Faqat ochgan odamning O‘Z puli.
// Qoidalar desktopniki: naqd saqlanmaydi (jami − kartalar); yangi karta qoldig‘i va
// «Qoldiqni to‘g‘irlash» — naqd bilan o‘tkazma (jami o‘zgarmaydi); o‘chirilgan karta
// puli naqdga qaytadi, yozuvlari o‘chmaydi.
// Ekranlar — Sozlamalar ustidagi to‘liq sahifa (← va Telegram BackButton), manzil:
//   #sozlamalar/tolov · #sozlamalar/tolov/karta/<id>  (skrinshot va havola uchun).
(() => {
  const NB = " ";
  const fmt = (s) => String(Math.abs(Math.round(Number(s) || 0))).replace(/\B(?=(\d{3})+(?!\d))/g, NB);
  const som = (s, belgi = false) => `${s < 0 ? "−" : belgi && s > 0 ? "+" : ""}${fmt(s)}${NB}so‘m`;
  const OYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];

  const svg = (d, o = 20, w = 1.8) => `<svg width="${o}" height="${o}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const IK = {
    orqa: svg(`<path d="M19.5 12h-15M10.5 5.5 4 12l6.5 6.5"/>`, 22, 2.1),
    ong: `<svg class="ong" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="m9.5 5.5 6.5 6.5-6.5 6.5"/></svg>`,
    plyus: svg(`<path d="M12 5v14M5 12h14"/>`, 18, 2.2),
    qalam: svg(`<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>`, 20, 1.9),
    savat: svg(`<path d="M4 7h16M10 11v6M14 11v6"/><path d="M5.5 7l1 12a2 2 0 0 0 2 2h7a2 2 0 0 0 2-2l1-12M9 7V4.5h6V7"/>`, 20, 1.9),
    x: svg(`<path d="M6 6l12 12M18 6 6 18"/>`, 15, 2.4),
    ogoh: svg(`<path d="M12 3.5 2.5 20h19L12 3.5Z"/><path d="M12 10v4.5M12 17.5v.01"/>`, 18, 2),
    otkazma: svg(`<path d="M4 8h14.5M15 4.5 18.5 8 15 11.5M20 16H5.5M9 12.5 5.5 16 9 19.5"/>`, 19, 1.9),
    togirla: svg(`<path d="M4 6.5h9M17 6.5h3M4 12h3M11 12h9M4 17.5h11M19 17.5h1"/><circle cx="15" cy="6.5" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="17.5" r="2"/>`, 19, 1.8),
    karta: svg(`<rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="M2.5 10h19M6.5 15h4"/>`, 19, 1.8),
    naqd: svg(`<rect x="2.5" y="6" width="19" height="12" rx="2.2"/><circle cx="12" cy="12" r="2.6"/><path d="M6 9.5v.01M18 14.5v.01"/>`, 19, 1.8),
    kirim: svg(`<path d="M12 5v14M6 13l6 6 6-6"/>`, 16, 2.1),
    rasxod: svg(`<path d="M12 19V5M6 11l6-6 6 6"/>`, 16, 2.1),
    almash: svg(`<path d="M5 9h13l-3.5-3.5M19 15H6l3.5 3.5"/>`, 16, 2.1),
    chip: `<svg width="34" height="26" viewBox="0 0 34 26"><rect x=".5" y=".5" width="33" height="25" rx="5" fill="rgba(255,255,255,.28)" stroke="rgba(255,255,255,.45)"/><path d="M11 .5v25M23 .5v25M.5 9h10.5M23 9h10.5M.5 17h10.5M23 17h10.5" stroke="rgba(255,255,255,.45)"/></svg>`,
  };
  // Karta ranglari — tartibi bo‘yicha (id bo‘yicha emas: qo‘shnilari doim farqli)
  const RANG = [
    { a: "#3b7bff", b: "#1f4fc9", fon: "#e8f0ff", ik: "#2f6ff5" },
    { a: "#8b5cf6", b: "#5b34d1", fon: "#efe9ff", ik: "#7444e6" },
    { a: "#14b8a6", b: "#0b7f78", fon: "#e2f6f3", ik: "#0e958b" },
    { a: "#f59e0b", b: "#d0661a", fon: "#fff1df", ik: "#e07b12" },
    { a: "#ec4899", b: "#b5306f", fon: "#ffe9f3", ik: "#d23c82" },
    { a: "#334155", b: "#1f2e3f", fon: "#edf1f6", ik: "#3b4657" },
  ];
  const NAQD_RANG = "#22c27a";

  // ── Holat ──────────────────────────────────────────────────────────
  let el = null;            // sahifa elementi (yopiq bo‘lsa null)
  let stek = [];            // [{t:"bosh"}] | [..., {t:"karta", id}]
  let h = null;             // {jami, naqd, karta, kartalar:[{id, nom, qoldiq}]}
  let tafsilot = new Map(); // karta_id → harakatlar
  let bugun = "";
  let xatoMatn = "";
  let yuklanmoqda = false;
  let varaq = null;         // ochiq oyna (pastdan)

  const ochiqmi = () => !!el;
  const joriy = () => stek[stek.length - 1];
  const karta = (id) => h?.kartalar.find((k) => k.id === id) || null;
  const rang = (id) => RANG[Math.max(0, h ? h.kartalar.findIndex((k) => k.id === id) : 0) % RANG.length];

  // ── Namuna (file://) — API'siz, xotirada ───────────────────────────
  let N = null;
  function namuna() {
    if (N) return;
    const bg = new Date(); bugun = isoSana(bg);
    const kun = (n) => isoSana(new Date(bg.getFullYear(), bg.getMonth(), bg.getDate() - n));
    let i = 100;
    const t = (tur, sana, nima, summa) => ({ tur, id: i++, sana, nima, summa });
    N = {
      jami: 6_480_000,
      kartalar: [
        { id: 1, nom: "Humo", tarix: [t("rasxod", kun(0), "Non, sut", -48_000), t("kirim", kun(1), "Kirim: Oylik", 3_500_000),
          t("rasxod", kun(1), "Bozorlik", -415_000), t("otkazma", kun(2), "Shu karta → Naqd (bankomatdan yechdim)", -300_000),
          t("rasxod", kun(3), "Internet", -120_000), t("otkazma", kun(9), "Naqd → shu karta (Boshlang'ich qoldiq)", 800_000)] },
        { id: 2, nom: "Uzcard", tarix: [t("rasxod", kun(0), "Taksi", -32_000), t("rasxod", kun(2), "Dorixona", -86_000),
          t("otkazma", kun(4), "Humo → shu karta", 250_000), t("otkazma", kun(9), "Naqd → shu karta (Boshlang'ich qoldiq)", 1_100_000)] },
        { id: 3, nom: "Visa", tarix: [t("otkazma", kun(6), "Naqd → shu karta (Boshlang'ich qoldiq)", 1_500_000)] },
      ],
    };
    // Humo → Uzcard o‘tkazmasi Humo tarixida ham
    N.kartalar[0].tarix.push(t("otkazma", kun(4), "Shu karta → Uzcard", -250_000));
    namunaHisob();
  }
  function namunaHisob() {
    const kartalar = N.kartalar.map((k) => {
      k.tarix.sort((a, b) => (a.sana < b.sana ? 1 : a.sana > b.sana ? -1 : b.id - a.id));
      return { id: k.id, nom: k.nom, qoldiq: k.tarix.reduce((s, x) => s + x.summa, 0) };
    });
    const kj = kartalar.reduce((s, k) => s + k.qoldiq, 0);
    h = { jami: N.jami, naqd: N.jami - kj, karta: kj, kartalar };
    tafsilot = new Map(N.kartalar.map((k) => [k.id, k.tarix.map((x) => ({ ...x }))]));
  }
  function namunaYoz(yol, b) {
    const nk = (id) => N.kartalar.find((k) => k.id === id);
    const nomi = (id) => (id == null ? "Naqd" : nk(id).nom);
    const qoldiq = (id) => (id == null ? h.naqd : karta(id).qoldiq);
    const nid = () => Math.max(99, ...N.kartalar.flatMap((k) => k.tarix.map((x) => x.id))) + 1;
    const otk = (dan, ga, summa, izoh) => {
      if (!(summa > 0)) throw new Error("Summa kiritilmagan.");
      if (dan === ga) throw new Error("Qayerdan va qayerga bir xil.");
      const id = nid(), q = izoh ? ` (${izoh})` : "";
      if (dan != null) nk(dan).tarix.push({ tur: "otkazma", id, sana: bugun, nima: `Shu karta → ${nomi(ga)}${q}`, summa: -summa });
      if (ga != null) nk(ga).tarix.push({ tur: "otkazma", id, sana: bugun, nima: `${nomi(dan)} → shu karta${q}`, summa });
      return id;
    };
    const bor = (nom, tashqari) => N.kartalar.some((k) => k.id !== tashqari && k.nom.toLowerCase() === nom.toLowerCase());
    let m;
    if (yol === "karta") {
      const nom = String(b.nom || "").trim();
      if (!nom) throw new Error("Karta nomini yozing (masalan: Humo, Uzcard).");
      if (bor(nom)) throw new Error(`Sizda «${nom}» degan karta bor.`);
      const id = Math.max(0, ...N.kartalar.map((k) => k.id)) + 1;
      N.kartalar.push({ id, nom, tarix: [] });
      if (b.qoldiq > 0) otk(null, id, b.qoldiq, "Boshlang'ich qoldiq");
      namunaHisob(); return { id };
    }
    if (yol === "otkazma") { otk(b.dan, b.ga, b.summa, b.izoh); namunaHisob(); return {}; }
    if ((m = yol.match(/^otkazma\/(\d+)\/ochir$/))) {
      N.kartalar.forEach((k) => { k.tarix = k.tarix.filter((x) => !(x.tur === "otkazma" && x.id === Number(m[1]))); });
      namunaHisob(); return {};
    }
    if ((m = yol.match(/^karta\/(\d+)\/(togirla|nom|ochir)$/))) {
      const id = Number(m[1]);
      if (m[2] === "ochir") { N.kartalar = N.kartalar.filter((k) => k.id !== id); namunaHisob(); return {}; }
      if (m[2] === "nom") {
        const nom = String(b.nom || "").trim();
        if (!nom) throw new Error("Karta nomini yozing.");
        if (bor(nom, id)) throw new Error(`«${nom}» degan karta bor.`);
        nk(id).nom = nom; namunaHisob(); return {};
      }
      if (b.qoldiq < 0) throw new Error("Qoldiq manfiy bo'lmaydi.");
      const farq = b.qoldiq - qoldiq(id);
      if (farq > 0) otk(null, id, farq, "Qoldiq to'g'irlandi");
      if (farq < 0) otk(id, null, -farq, "Qoldiq to'g'irlandi");
      namunaHisob(); return { ozgardi: farq !== 0 };
    }
    throw new Error("Topilmadi");
  }

  // ── Ma'lumot ───────────────────────────────────────────────────────
  function qabul(j) {
    h = j.hamyon; bugun = j.bugun || bugun;
    if (j.karta) tafsilot.set(j.karta.id, j.karta.harakatlar);
    // O‘chgan karta ekranida qolmaslik
    if (joriy()?.t === "karta" && !karta(joriy().id)) stek = [{ t: "bosh" }];
  }
  async function yukla() {
    if (NAMUNA) { namuna(); return chiz(); }
    if (!INIT) { xatoMatn = "Bu sahifani Telegram'dagi Farovon Uy botidan oching."; return chiz(); }
    if (yuklanmoqda) return;
    yuklanmoqda = true;
    const s = joriy();
    try {
      qabul(await api(s?.t === "karta" ? `tolov/karta/${s.id}` : "tolov"));
      xatoMatn = "";
    } catch (err) { xatoMatn = err.message; }
    yuklanmoqda = false;
    chiz();
  }
  /** Yozish: namunada xotirada, aks holda API (javobda yangi holat). */
  async function yoz(yol, tana) {
    if (NAMUNA) return namunaYoz(yol, tana);
    const s = joriy();
    const j = await api("tolov/" + yol, { ...tana, ...(s?.t === "karta" && !("karta" in tana) ? { karta: s.id } : {}) });
    qabul(j);
    return j;
  }

  // ── Ochish / yopish ────────────────────────────────────────────────
  function och(kartaId = null) {
    if (!el) {
      el = document.createElement("section");
      el.className = "szt-sahifa";
      el.setAttribute("role", "dialog");
      el.setAttribute("aria-label", "To‘lov usullari");
      el.addEventListener("click", bosildi);
      document.body.appendChild(el);
    }
    stek = [{ t: "bosh" }];
    if (kartaId != null) stek.push({ t: "karta", id: kartaId });
    chiz();
    yukla();
  }
  function yop() {
    oynaYop(true);
    if (el) { el.remove(); el = null; }
    stek = [];
    try { if (location.hash.startsWith("#sozlamalar/tolov")) history.replaceState(null, "", "#sozlamalar"); } catch (err) {}
    tgOrqa();
  }
  function orqa() {
    if (varaq) return oynaYop();
    if (stek.length > 1) { stek.pop(); chiz(); el.scrollTop = 0; tebran("soft"); return; }
    yop();
  }
  function xeshYoz() {
    const s = joriy();
    const x = "#sozlamalar/tolov" + (s?.t === "karta" ? "/karta/" + s.id : "");
    if (location.hash !== x) { try { history.replaceState(null, "", x); } catch (err) {} }
  }

  // ── Chizish ────────────────────────────────────────────────────────
  function chiz() {
    if (!el) return;
    const s = joriy();
    el.innerHTML = s.t === "karta" ? kartaEkran(s.id) : boshEkran();
    xeshYoz();
    tgOrqa();
  }
  const sarlavha = (nom, ong = "") => `<div class="sz-bosh ichki szt-bosh">
      <button class="sz-orqa" data-amal="orqa" aria-label="Orqaga">${IK.orqa}</button><h1>${e(nom)}</h1>${ong}</div>`;
  function holatHtml(skelet) {
    if (xatoMatn) return `<div class="sz-royxat"><div class="sz-bosh-holat">${e(xatoMatn)}<br><button data-amal="qayta">Qayta urinish</button></div></div>`;
    if (!h) return skelet;
    return "";
  }

  function boshEkran() {
    const skelet = `<div class="szt-jami szt-skelet-jami"></div><div class="sz-bolim">Hamyon</div>
      <div class="sz-royxat">${"<div class=\"sz-skelet\"></div>".repeat(3)}</div>`;
    const bosh = sarlavha("To‘lov usullari", h && h.kartalar.length
      ? `<button class="sz-ikon-tugma" data-amal="otkazma" aria-label="O‘tkazma">${IK.otkazma}</button>` : "");
    const hol = holatHtml(skelet);
    if (hol) return bosh + hol;
    const n = h.kartalar.length;
    // Taqsimot chizig‘i: naqd va har karta ulushi (manfiylar 0 deb)
    const qism = [{ q: Math.max(0, h.naqd), r: NAQD_RANG }, ...h.kartalar.map((k) => ({ q: Math.max(0, k.qoldiq), r: rang(k.id).a }))];
    const jamiM = qism.reduce((s, x) => s + x.q, 0);
    const chiziq = jamiM > 0 ? qism.filter((x) => x.q > 0).map((x) => `<i style="flex:${x.q};background:${x.r}"></i>`).join("") : "<i style=\"flex:1;background:rgba(255,255,255,.18)\"></i>";
    const naqdIzoh = h.naqd < 0 ? "Kartalardagi pul jamidan ko‘p — qoldiqlarni tekshiring" : "Qo‘ldagi naqd pul";
    return `${bosh}
      <div class="szt-jami">
        <div class="yorliq">Jami pulim</div>
        <div class="summa${h.jami < 0 ? " manfiy" : ""}">${h.jami < 0 ? "−" : ""}${fmt(h.jami)}<span>${NB}so‘m</span></div>
        <div class="szt-chiziq">${chiziq}</div>
        <div class="taqsim">
          <span><b style="background:${NAQD_RANG}"></b>Naqd<em>${som(h.naqd)}</em></span>
          <span><b style="background:#8fb3ff"></b>Kartalar<em>${som(h.karta)}</em></span>
        </div>
      </div>
      <div class="sz-bolim szt-bolim">Hamyon<small>${n ? `${n + 1} ta joy` : ""}</small></div>
      <div class="sz-royxat">
        <div class="sz-q szt-q szt-naqd">
          <span class="szt-belgi" style="background:#e3f7ee;color:#1d9d63">${IK.naqd}</span>
          <span class="szt-matn"><b>Naqd</b><small class="${h.naqd < 0 ? "ogoh" : ""}">${naqdIzoh}</small></span>
          <span class="szt-qoldiq${h.naqd < 0 ? " manfiy" : ""}">${som(h.naqd)}</span>
        </div>
        ${h.kartalar.map((k) => { const r = rang(k.id); return `<button class="sz-q szt-q" data-karta="${k.id}">
          <span class="szt-belgi" style="background:${r.fon};color:${r.ik}">${IK.karta}</span>
          <span class="szt-matn"><b>${e(k.nom)}</b><small>Bank kartasi</small></span>
          <span class="szt-qoldiq${k.qoldiq < 0 ? " manfiy" : ""}">${som(k.qoldiq)}</span>${IK.ong}</button>`; }).join("")}
      </div>
      ${n ? "" : `<p class="szt-izoh markaz">Hali karta qo‘shilmagan. Kartangizdagi pulni alohida ko‘rish uchun karta qo‘shing.</p>`}
      <div class="szt-tugmalar${n ? "" : " bitta"}">
        <button class="sz-kok-tugma" data-amal="yangi">${IK.plyus}Karta qo‘shish</button>
        ${n ? `<button class="sz-och-tugma szt-och" data-amal="otkazma">${IK.otkazma}O‘tkazma</button>` : ""}
      </div>
      <p class="szt-izoh">Naqd alohida saqlanmaydi — u jami puldan kartalardagisi ayirilgani. Xarajat yoki kirim yozayotganda «Qayerdan»ni tanlasangiz, karta qoldig‘i o‘zi o‘zgaradi.</p>`;
  }

  function sanaNomi(s) {
    if (s === bugun) return "Bugun";
    const [y, m, d] = s.split("-").map(Number);
    const b = bugun ? bugun.split("-").map(Number) : null;
    if (b) {
      const kecha = new Date(b[0], b[1] - 1, b[2] - 1);
      if (kecha.getFullYear() === y && kecha.getMonth() === m - 1 && kecha.getDate() === d) return "Kecha";
    }
    return `${d}-${OYLAR[m - 1]}${b && b[0] !== y ? ` ${y}` : ""}`;
  }

  function kartaEkran(id) {
    const k = karta(id);
    if (!k) {
      return sarlavha("Karta") + (holatHtml(`<div class="szt-plastik szt-skelet-plastik"></div>`) ||
        `<div class="sz-royxat"><div class="sz-bosh-holat">Karta topilmadi</div></div>`);
    }
    const r = rang(id);
    const tarix = tafsilot.get(id);
    let royxat;
    if (!tarix) royxat = `<div class="sz-royxat">${"<div class=\"sz-skelet\"></div>".repeat(4)}</div>`;
    else if (!tarix.length) royxat = `<div class="sz-royxat"><div class="sz-bosh-holat">Bu kartada hali harakat yo‘q</div></div>`;
    else {
      const guruh = new Map();
      for (const x of tarix) { if (!guruh.has(x.sana)) guruh.set(x.sana, []); guruh.get(x.sana).push(x); }
      royxat = [...guruh].map(([sana, xs]) => `<div class="szt-sana">${sanaNomi(sana)}</div>
        <div class="sz-royxat szt-tarix">${xs.map((x) => harakatHtml(x)).join("")}</div>`).join("");
    }
    return `${sarlavha(k.nom, `<button class="sz-ikon-tugma" data-amal="nom" aria-label="Nomini o‘zgartirish">${IK.qalam}</button>
        <button class="sz-ikon-tugma xavf" data-amal="ochir" aria-label="O‘chirish">${IK.savat}</button>`)}
      <div class="szt-plastik" style="background:linear-gradient(135deg, ${r.a}, ${r.b})">
        <div class="ust">${IK.chip}<span class="tur">${e(k.nom)}</span></div>
        <div class="yorliq">Kartadagi qoldiq</div>
        <div class="summa">${k.qoldiq < 0 ? "−" : ""}${fmt(k.qoldiq)}<span>${NB}so‘m</span></div>
      </div>
      <div class="szt-amallar">
        <button data-amal="otkazma"><span>${IK.otkazma}</span>O‘tkazma</button>
        <button data-amal="togirla"><span>${IK.togirla}</span>Qoldiqni to‘g‘irlash</button>
      </div>
      <div class="sz-bolim">Tarix</div>
      ${royxat}
      ${tarix && tarix.some((x) => x.tur === "otkazma") ? `<p class="szt-izoh">O‘tkazmani bosing — xato yozilgan bo‘lsa o‘chirish mumkin. Kirim va xarajatlar o‘z bo‘limida tahrirlanadi.</p>` : ""}`;
  }
  function harakatHtml(x) {
    const ik = x.tur === "otkazma" ? IK.almash : x.summa >= 0 ? IK.kirim : IK.rasxod;
    const cls = x.tur === "otkazma" ? "otk" : x.summa >= 0 ? "kir" : "ras";
    const tur = { kirim: "Kirim", rasxod: "Xarajat", otkazma: "O‘tkazma" }[x.tur];
    let nima = x.tur === "kirim" ? x.nima.replace(/^Kirim: /, "") : x.nima, izoh = "";
    // «Shu karta → Naqd (bankomatdan yechdim)» → sarlavha + izoh alohida qatorda
    const m = x.tur === "otkazma" && nima.match(/^(.*?) \((.*)\)$/);
    if (m) { nima = m[1]; izoh = m[2]; }
    const ichi = `<span class="szt-h-belgi ${cls}">${ik}</span>
      <span class="szt-matn"><b>${e(nima)}</b><small>${tur}${izoh ? " · " + e(izoh) : ""}</small></span>
      <span class="szt-summa ${x.summa >= 0 ? "musbat" : ""}">${som(x.summa, true)}</span>`;
    return x.tur === "otkazma"
      ? `<button class="sz-q szt-q szt-h" data-otkazma="${x.id}">${ichi}</button>`
      : `<div class="sz-q szt-q szt-h">${ichi}</div>`;
  }

  // ── Oyna (pastdan) ─────────────────────────────────────────────────
  let parda, oyna;
  function oynaElementlari() {
    if (oyna) return;
    parda = document.createElement("div"); parda.className = "sz-parda szt-parda";
    oyna = document.createElement("div"); oyna.className = "sz-oyna szt-oyna"; oyna.setAttribute("role", "dialog");
    document.body.append(parda, oyna);
    parda.onclick = () => oynaYop();
    oyna.addEventListener("click", oynaBosildi);
    oyna.addEventListener("input", oynaKiritildi);
    oyna.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && ev.target.tagName === "INPUT") { ev.preventDefault(); saqla(); }
    });
  }
  function oynaOch(v, fokus) {
    varaq = v; oynaElementlari(); oynaChiz(); tgOrqa();
    if (fokus) setTimeout(() => { const i = document.getElementById(fokus); if (i) { i.focus(); try { i.setSelectionRange(i.value.length, i.value.length); } catch (err) {} } }, 280);
  }
  function oynaYop(jim) {
    varaq = null;
    if (oyna) { parda.classList.remove("ochiq"); oyna.classList.remove("ochiq"); }
    if (!jim) tgOrqa();
  }
  function oynaChiz() {
    if (!varaq) return;
    oyna.innerHTML = oynaHtml(varaq);
    parda.classList.add("ochiq"); oyna.classList.add("ochiq");
  }
  const oynaBosh = (matn) => `<div class="sz-oyna-bosh"><h3>${matn}</h3><button class="sz-yop" data-amal="yop" aria-label="Yopish">${IK.x}</button></div>`;
  const ogoh = (v) => (v.xato ? `<div class="sz-ogoh">${IK.ogoh}<span>${e(v.xato)}</span></div>` : "");
  const pulMaydon = (id, qiymat, ph = "0") => `<label class="szt-pul"><input class="sz-kirit" id="${id}" inputmode="numeric" autocomplete="off" placeholder="${ph}" value="${qiymat === "" || qiymat == null ? "" : fmt(qiymat)}"><span>so‘m</span></label>`;
  const raqam = (s) => { const t = String(s || "").replace(/\D/g, ""); return t ? Number(t) : null; };
  const joyNomi = (id) => (id == null ? "Naqd" : karta(id)?.nom || "?");
  const joyQoldiq = (id) => (id == null ? h.naqd : karta(id)?.qoldiq ?? 0);

  function oynaHtml(v) {
    const tugma = (matn) => `<button class="sz-kok-tugma" data-amal="saqla"${v.band ? " disabled" : ""}>${matn}</button>`;
    if (v.t === "yangi") {
      return `${oynaBosh("Yangi karta")}
        <label class="sz-yorliq" for="sztNom">Karta nomi</label>
        <input class="sz-kirit" id="sztNom" maxlength="40" autocomplete="off" placeholder="Masalan: Humo, Uzcard, Visa" value="${e(v.nom)}">
        <label class="sz-yorliq" for="sztSumma">Hozir kartada</label>
        ${pulMaydon("sztSumma", v.summa)}
        <p class="sz-izoh szt-oyna-izoh">Bu pul allaqachon hisobingizda — u naqddan kartaga ko‘chadi, jami pulingiz o‘zgarmaydi.</p>
        ${ogoh(v)}${tugma("Qo‘shish")}`;
    }
    if (v.t === "otkazma") {
      const joylar = [null, ...h.kartalar.map((k) => k.id)];
      const chip = (tomon, id) => `<button class="sz-chip szt-joy${v[tomon] === id ? " faol" : ""}" data-${tomon}="${id ?? "naqd"}">${id == null ? IK.naqd : IK.karta}${e(joyNomi(id))}</button>`;
      const yetmaydi = v.summa > 0 && v.summa > joyQoldiq(v.dan);
      return `${oynaBosh("O‘tkazma")}
        <div class="sz-yorliq">Qayerdan</div>
        <div class="szt-joylar">${joylar.map((id) => chip("dan", id)).join("")}</div>
        <div class="szt-mavjud">Mavjud: ${som(joyQoldiq(v.dan))}</div>
        <div class="sz-yorliq">Qayerga</div>
        <div class="szt-joylar">${joylar.map((id) => chip("ga", id)).join("")}</div>
        <div class="szt-mavjud">Mavjud: ${som(joyQoldiq(v.ga))}</div>
        <label class="sz-yorliq" for="sztSumma">Summa</label>
        ${pulMaydon("sztSumma", v.summa)}
        <div class="szt-ogoh-kichik" id="sztYetmaydi"${yetmaydi ? "" : " hidden"}>«${e(joyNomi(v.dan))}»da buncha pul ko‘rinmayapti — baribir yoziladi.</div>
        <label class="sz-yorliq" for="sztIzoh">Izoh <span class="ixtiyoriy">(ixtiyoriy)</span></label>
        <input class="sz-kirit" id="sztIzoh" maxlength="120" autocomplete="off" placeholder="Masalan: bankomatdan yechdim" value="${e(v.izoh)}">
        ${ogoh(v)}${tugma("O‘tkazish")}`;
    }
    if (v.t === "togirla") {
      const k = karta(v.id);
      return `${oynaBosh("Qoldiqni to‘g‘irlash")}
        <p class="sz-matn">Bank ilovasida hozir qancha turibdi? Farq naqd bilan o‘tkazma bo‘lib yoziladi — jami pulingiz o‘zgarmaydi.</p>
        <div class="szt-hozir"><span>Hisobdagi qoldiq</span><b>${som(k.qoldiq)}</b></div>
        <label class="sz-yorliq" for="sztSumma">Kartadagi haqiqiy qoldiq</label>
        ${pulMaydon("sztSumma", v.summa)}
        <div class="szt-farq" id="sztFarq">${farqMatn(v)}</div>
        ${ogoh(v)}${tugma("Saqlash")}`;
    }
    if (v.t === "nom") {
      return `${oynaBosh("Nomini o‘zgartirish")}
        <label class="sz-yorliq" for="sztNom">Karta nomi</label>
        <input class="sz-kirit" id="sztNom" maxlength="40" autocomplete="off" value="${e(v.nom)}">
        ${ogoh(v)}${tugma("Saqlash")}`;
    }
    if (v.t === "ochir") {
      const k = karta(v.id);
      return `${oynaBosh("Kartani o‘chirish")}
        <p class="sz-matn"><b>«${e(k.nom)}»</b> o‘chiriladi. Undagi <b>${som(k.qoldiq)}</b> naqdga qaytadi; kirim, xarajat va o‘tkazmalar o‘chmaydi.</p>
        ${ogoh(v)}<div class="sz-ikki"><button class="sz-kulrang-tugma" data-amal="yop">Bekor qilish</button>
        <button class="sz-qizil-tugma" data-amal="saqla"${v.band ? " disabled" : ""}>O‘chirish</button></div>`;
    }
    if (v.t === "otkOchir") {
      return `${oynaBosh("O‘tkazmani o‘chirish")}
        <div class="szt-hozir"><span>${e(v.x.nima)}</span><b>${som(Math.abs(v.x.summa))}</b></div>
        <p class="sz-matn">O‘tkazma ikkala joydan ham olib tashlanadi — pul qayerdan olingan bo‘lsa, o‘sha yerga qaytadi.</p>
        ${ogoh(v)}<div class="sz-ikki"><button class="sz-kulrang-tugma" data-amal="yop">Bekor qilish</button>
        <button class="sz-qizil-tugma" data-amal="saqla"${v.band ? " disabled" : ""}>O‘chirish</button></div>`;
    }
    return "";
  }
  function farqMatn(v) {
    const k = karta(v.id);
    if (v.summa == null) return "&nbsp;";
    const f = v.summa - k.qoldiq;
    if (f === 0) return "Qoldiq to‘g‘ri — hech narsa yozilmaydi.";
    return f > 0
      ? `Farq <b class="musbat">+${fmt(f)}${NB}so‘m</b> — naqddan kartaga o‘tadi`
      : `Farq <b>−${fmt(f)}${NB}so‘m</b> — kartadan naqdga o‘tadi`;
  }

  function oynaKiritildi(ev) {
    const t = ev.target;
    if (!varaq) return;
    if (t.id === "sztSumma") {
      // Raqamni bo‘lib yozish (1 250 000), kursor oxirida
      const r = raqam(t.value);
      varaq.summa = r;
      const yangi = r == null ? "" : fmt(r);
      if (t.value !== yangi) t.value = yangi;
      if (varaq.t === "togirla") document.getElementById("sztFarq").innerHTML = farqMatn(varaq);
      if (varaq.t === "otkazma") document.getElementById("sztYetmaydi").hidden = !(r > 0 && r > joyQoldiq(varaq.dan));
    }
    if (t.id === "sztNom") varaq.nom = t.value;
    if (t.id === "sztIzoh") varaq.izoh = t.value;
  }
  function oynaBosildi(ev) {
    const t = ev.target.closest("button"); if (!t || !varaq) return;
    if (t.dataset.amal === "yop") return oynaYop();
    if (t.dataset.amal === "saqla") return saqla();
    const v = varaq;
    for (const tomon of ["dan", "ga"]) {
      if (t.dataset[tomon] === undefined) continue;
      const id = t.dataset[tomon] === "naqd" ? null : Number(t.dataset[tomon]);
      const boshqa = tomon === "dan" ? "ga" : "dan";
      if (v[boshqa] === id) v[boshqa] = v[tomon]; // bir xil bo‘lmasin — o‘rnini almashtiradi
      v[tomon] = id; v.xato = "";
      tebran("soft"); oynaChiz();
    }
  }

  async function saqla() {
    const v = varaq; if (!v || v.band) return;
    let yol, tana, ok;
    if (v.t === "yangi") {
      if (!v.nom.trim()) { document.getElementById("sztNom")?.focus(); return; }
      yol = "karta"; tana = { nom: v.nom.trim(), qoldiq: v.summa || 0 }; ok = "Karta qo‘shildi";
    } else if (v.t === "otkazma") {
      if (!v.summa) { document.getElementById("sztSumma")?.focus(); return; }
      yol = "otkazma"; tana = { dan: v.dan, ga: v.ga, summa: v.summa, izoh: (v.izoh || "").trim() || null }; ok = "O‘tkazma yozildi";
    } else if (v.t === "togirla") {
      if (v.summa == null) { document.getElementById("sztSumma")?.focus(); return; }
      yol = `karta/${v.id}/togirla`; tana = { qoldiq: v.summa }; ok = "Qoldiq to‘g‘irlandi";
    } else if (v.t === "nom") {
      if (!v.nom.trim()) { document.getElementById("sztNom")?.focus(); return; }
      yol = `karta/${v.id}/nom`; tana = { nom: v.nom.trim() }; ok = "Nomi o‘zgardi";
    } else if (v.t === "ochir") {
      yol = `karta/${v.id}/ochir`; tana = { karta: null }; ok = "Karta o‘chirildi — puli naqdga qaytdi";
    } else if (v.t === "otkOchir") {
      yol = `otkazma/${v.x.id}/ochir`; tana = {}; ok = "O‘tkazma o‘chirildi";
    } else return;
    v.band = true; v.xato = ""; oynaChiz();
    try {
      const j = await yoz(yol, tana);
      if (v.t === "togirla" && j && j.ozgardi === false) ok = "Qoldiq to‘g‘ri edi — hech narsa yozilmadi";
      oynaYop(); tebran("medium");
      if (v.t === "ochir") { stek = [{ t: "bosh" }]; el.scrollTop = 0; }
      if (v.t === "yangi" && j?.id != null && !NAMUNA) tafsilot.delete(j.id);
      chiz();
      xabar(ok);
    } catch (err) {
      v.band = false; v.xato = err.message;
      if (varaq === v) oynaChiz();
    }
  }

  // ── Hodisalar ──────────────────────────────────────────────────────
  function bosildi(ev) {
    const t = ev.target.closest("button"); if (!t) return;
    if (t.dataset.karta) {
      const id = Number(t.dataset.karta);
      stek.push({ t: "karta", id }); chiz(); el.scrollTop = 0; tebran("soft");
      if (!NAMUNA) yukla();
      return;
    }
    if (t.dataset.otkazma) {
      const x = (tafsilot.get(joriy().id) || []).find((y) => y.tur === "otkazma" && y.id === Number(t.dataset.otkazma));
      if (x) oynaOch({ t: "otkOchir", x, xato: "" });
      return;
    }
    const a = t.dataset.amal;
    if (a === "orqa") return orqa();
    if (a === "qayta") { xatoMatn = ""; chiz(); return yukla(); }
    if (!h) return;
    const s = joriy();
    if (a === "yangi") return oynaOch({ t: "yangi", nom: "", summa: null, xato: "" }, "sztNom");
    if (a === "otkazma") {
      if (!h.kartalar.length) return xabar("Avval karta qo‘shing");
      // Birlamchi — bankomatdan yechish: karta → naqd (desktop OtkazmaDialog)
      const dan = s.t === "karta" ? s.id : h.kartalar[0].id;
      return oynaOch({ t: "otkazma", dan, ga: null, summa: null, izoh: "", xato: "" }, "sztSumma");
    }
    if (s.t !== "karta" || !karta(s.id)) return;
    if (a === "togirla") return oynaOch({ t: "togirla", id: s.id, summa: karta(s.id).qoldiq, xato: "" }, "sztSumma");
    if (a === "nom") return oynaOch({ t: "nom", id: s.id, nom: karta(s.id).nom, xato: "" }, "sztNom");
    if (a === "ochir") return oynaOch({ t: "ochir", id: s.id, xato: "" });
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

  function isoSana(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  // ── Ro‘yxatdan o‘tish va havola ────────────────────────────────────
  window.SozlamaBolimi = window.SozlamaBolimi || {};
  window.SozlamaBolimi.tolov = () => och();

  /** «#sozlamalar/tolov[/karta/<id>]» → ochish. */
  function havola(xesh) {
    const m = String(xesh || "").match(/^#sozlamalar\/tolov(?:\/karta\/(\d+))?\/?$/);
    if (!m) return false;
    if (document.getElementById("sahifa-sozlamalar")?.hidden) return false;
    och(m[1] ? Number(m[1]) : null);
    return true;
  }
  // Sozlamalar moduli xeshni o‘zinikiga qaytarib yozadi — shuning uchun boshlang‘ich
  // manzil navigatsiya yozuvidan olinadi (u asl xeshni saqlaydi).
  let boshXesh = location.hash;
  try { const n = performance.getEntriesByType("navigation")[0]; if (n) boshXesh = new URL(n.name).hash || boshXesh; } catch (err) {}
  if (!havola(location.hash)) havola(boshXesh);
  window.addEventListener("hashchange", (ev) => {
    try { const x = new URL(ev.newURL).hash; if (!ochiqmi()) havola(x); } catch (err) {}
  });
  window.addEventListener("sahifa", (ev) => { if (ev.detail?.nom !== "sozlamalar" && ochiqmi()) yop(); });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && ochiqmi() && !NAMUNA && INIT && !varaq) yukla();
  });
})();
