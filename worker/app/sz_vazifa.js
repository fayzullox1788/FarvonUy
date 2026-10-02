// Sozlamalar → «Vazifalar» — vazifalarni boshqarish: yaqin kunlar ro‘yxati, yangi vazifa
// (takror / ovqat navbati bilan), tahrirlash va ish turlari (qadamlari bilan).
// index.html yordamchilari ustida: api(), NAMUNA, INIT, xabar(), tebran(), e().
// API: worker/src/miniapp_sz_vazifa.js (/app/api/vazifa-boshqaruv*), yozuv — vazifa.js
// (Python core/vazifa.py egizagi). Qaysi maydon o‘zgarishini SERVER aytadi (`ruxsat`):
// dars — faqat o‘qish, ovqat navbati — kim «Almashtirish/Faqat shu kunni berish» bilan,
// idish — oshpazga ergashadi, takror — bitta kun yoki qoidani to‘xtatish.
// Ekranlar — Sozlamalar ustidagi to‘liq sahifa (← va Telegram BackButton), manzil:
//   #sozlamalar/vazifalar · …/vazifalar/yangi · …/vazifalar/v/<id> · …/vazifalar/turlar
//   · …/vazifalar/turlar/yangi · …/vazifalar/tur/<id>  (skrinshot va havola uchun).
(() => {
  const svg = (d, o = 20, w = 1.8) => `<svg width="${o}" height="${o}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const IK = {
    orqa: svg(`<path d="M19.5 12h-15M10.5 5.5 4 12l6.5 6.5"/>`, 22, 2.1),
    ong: `<svg class="ong" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="m9.5 5.5 6.5 6.5-6.5 6.5"/></svg>`,
    chap: svg(`<path d="m14.5 5.5-6.5 6.5 6.5 6.5"/>`, 18, 2.2),
    ongK: svg(`<path d="m9.5 5.5 6.5 6.5-6.5 6.5"/>`, 18, 2.2),
    plyus: svg(`<path d="M12 5v14M5 12h14"/>`, 18, 2.2),
    x: svg(`<path d="M6 6l12 12M18 6 6 18"/>`, 15, 2.4),
    ogoh: svg(`<path d="M12 3.5 2.5 20h19L12 3.5Z"/><path d="M12 10v4.5M12 17.5v.01"/>`, 18, 2),
    info: svg(`<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.8v.01"/>`, 18, 2),
    turlar: svg(`<path d="M8.5 6.5h11M8.5 12h11M8.5 17.5h11"/><circle cx="4.6" cy="6.5" r="1.1"/><circle cx="4.6" cy="12" r="1.1"/><circle cx="4.6" cy="17.5" r="1.1"/>`, 21, 1.9),
    takror: svg(`<path d="M17 2.5 20.5 6 17 9.5"/><path d="M3.5 11.5V10a4 4 0 0 1 4-4h13M7 21.5 3.5 18 7 14.5"/><path d="M20.5 12.5V14a4 4 0 0 1-4 4h-13"/>`, 13, 2.2),
    qulf: svg(`<rect x="5" y="10.5" width="14" height="10" rx="2.2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>`, 13, 2.1),
    savat: svg(`<path d="M4 7h16M10 11v6M14 11v6"/><path d="M5.5 7l1 12a2 2 0 0 0 2 2h7a2 2 0 0 0 2-2l1-12M9 7V4.5h6V7"/>`, 18, 1.9),
    ok: svg(`<path d="m5 12.5 4.5 4.5L19 7.5"/>`, 12, 3.2),
    almash: svg(`<path d="M5 9h13l-3.5-3.5M19 15H6l3.5 3.5"/>`, 17, 2.1),
  };
  const OYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];
  const KUNLAR = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"];
  const KUN_QISQA = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
  const TOIFA = { shaxsiy: "Shaxsiy", uy: "Uy", darslar: "Dars", boshqa: "Boshqa" };
  const NAQSH = [["kunlik", "Har kuni"], ["kunlar", "Kunlar"], ["oraliq", "Har N kunda"]];
  const DAVOM = [15, 30, 45, 60, 90];
  const KUN_SONI = 8; // bugun + 7 kun
  const UFQ = 30;     // vazifa.TAKROR_UFQ

  // ── Sana yordamchilari (UTC — vaqt mintaqasidan qat'i nazar) ───────
  const sD = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(Date.UTC(y, m - 1, d)); };
  const dS = (d) => d.toISOString().slice(0, 10);
  const kunQosh = (s, n) => { const d = sD(s); d.setUTCDate(d.getUTCDate() + n); return dS(d); };
  const hk = (s) => (sD(s).getUTCDay() + 6) % 7; // Du = 0
  const kunFarq = (a, b) => Math.round((sD(b) - sD(a)) / 864e5);
  const dm = (s) => `${Number(s.slice(8, 10))}-${OYLAR[Number(s.slice(5, 7)) - 1]}`;
  const dmQ = (s) => `${s.slice(8, 10)}.${s.slice(5, 7)}`;
  const davMatn = (m) => (m >= 60 && m % 30 === 0 ? `${String(m / 60).replace(".", ",")} soat` : `${m} daq`);

  // ── Holat ──────────────────────────────────────────────────────────
  let el = null;           // sahifa elementi (yopiq bo‘lsa null)
  let stek = [];           // [{t:"bosh"}] | [..., {t:"turlar"}]
  let d = null;            // API javobi: {men, bugun, dan, gacha, odamlar, turlar, vazifalar, navbat}
  let dan = null;          // ko‘rinayotgan birinchi kun (null — bugun)
  let kim = "men";         // filtr: "men" | "hammasi" | odam id
  let xatoMatn = "";
  let yuklanmoqda = false;
  let varaq = null;        // pastdan oyna
  let kutilgan = null;     // havola: ma'lumot kelgach ochiladigan oyna

  const ochiqmi = () => !!el;
  const joriy = () => stek[stek.length - 1];
  const odam = (id) => d?.odamlar.find((o) => o.id === id) || null;
  const tur = (id) => d?.turlar.find((t) => t.id === id) || null;
  const turNom = (nom) => d?.turlar.find((t) => t.nom === nom) || null;
  const vazifa = (id) => d?.vazifalar.find((v) => v.id === id) || null;

  // ── Namuna (file://) — API'siz, xotirada ───────────────────────────
  function namuna() {
    const b = dS(new Date(Date.now() - new Date().getTimezoneOffset() * 6e4));
    const odamlar = [{ id: 1, nom: "Fayzulloxon", rang: "#2f6ff5" }, { id: 3, nom: "Otabek", rang: "#f08a24" }, { id: 5, nom: "Abbosxon", rang: "#22c27a" }];
    const turlar = [
      { id: 1, nom: "Ovqat qilish", davomiylik: 60, shaxsiy: false, navbat: true, haftalik: false, ergash: false, dars: false, qadamlar: [] },
      { id: 2, nom: "Idish yuvish", davomiylik: 30, shaxsiy: false, navbat: false, haftalik: false, ergash: true, dars: false, qadamlar: [] },
      { id: 3, nom: "Musorlarni tashlash", davomiylik: 15, shaxsiy: false, navbat: false, haftalik: false, ergash: false, dars: false, qadamlar: [] },
      { id: 4, nom: "Sanuzelni tozalash", davomiylik: 90, shaxsiy: false, navbat: false, haftalik: true, ergash: false, dars: false,
        qadamlar: [{ id: 1, nom: "Unitaz" }, { id: 2, nom: "Vanna" }, { id: 3, nom: "Pol" }] },
      { id: 5, nom: "Kitob o‘qish", davomiylik: 30, shaxsiy: true, navbat: false, haftalik: false, ergash: false, dars: false, qadamlar: [] },
      { id: 6, nom: "Matematika", davomiylik: 80, shaxsiy: true, navbat: false, haftalik: false, ergash: false, dars: true, qadamlar: [] },
    ];
    const R = {
      oddiy: { maydon: { nom: true, sana: true, kim: true, vaqt: true, davomiylik: true, izoh: true }, ochir: true, navbat: false, shaxsiy: true, izoh: "" },
      dars: { maydon: { nom: false, sana: false, kim: false, vaqt: false, davomiylik: false, izoh: false }, ochir: false, navbat: false, shaxsiy: false,
        izoh: "Dars jadvalidan (EduPage) keladi — sinxron har soatda qaytadan yozadi, shuning uchun bu yerda o‘zgartirilmaydi." },
      navbat: { maydon: { nom: false, sana: false, kim: false, vaqt: true, davomiylik: true, izoh: true }, ochir: true, navbat: true, shaxsiy: true,
        izoh: "Ovqat navbati: kimligi «Almashtirish» yoki «Faqat shu kunni berish» bilan o‘zgaradi — idish yuvuvchi ham o‘zi to‘g‘rilanadi." },
      ergash: { maydon: { nom: false, sana: false, kim: false, vaqt: true, davomiylik: true, izoh: true }, ochir: true, navbat: false, shaxsiy: true,
        izoh: "Idishni ovqat qilgan odamning o‘zi yuvadi — kimligi ovqat navbati bilan birga o‘zgaradi." },
      takror: { maydon: { nom: true, sana: true, kim: true, vaqt: true, davomiylik: true, izoh: true }, ochir: true, navbat: false, shaxsiy: true, takror: true,
        izoh: "Takroriy vazifaning bitta kuni — o‘zgartirish faqat shu kunga tegadi, qoidaga emas." },
    };
    let id = 100;
    const v = [];
    const q = (nom, odam_id, kun, vaqt, dav, t = "oddiy", qosh = {}) => v.push({
      id: id++, nom, odam_id, sana: kunQosh(b, kun), vaqt, davomiylik: dav, izoh: null, holat: "ochiq", menyu: null,
      toifa: t === "dars" ? "darslar" : turlar.find((x) => x.nom === nom)?.shaxsiy ? "shaxsiy" : turlar.find((x) => x.nom === nom) ? "uy" : "boshqa",
      tur: t, tur_id: turlar.find((x) => x.nom === nom)?.id ?? null, shaxsiy: !!turlar.find((x) => x.nom === nom)?.shaxsiy,
      takror: t === "takror" ? { id: 7, tavsif: "Du, Ch, Ju 07:00" } : null, ruxsat: R[t], ...qosh });
    for (let k = 0; k < KUN_SONI; k++) {
      const oshpaz = odamlar[k % 3].id;
      q("Ovqat qilish", oshpaz, k, "19:00", 60, "navbat");
      q("Idish yuvish", oshpaz, k, "20:00", 30, "ergash");
      if ([0, 2, 4].includes(hk(kunQosh(b, k)))) q("Sport", 1, k, "07:00", 45, "takror", { izoh: "Zal" });
      if (k % 2 === 0) q("Kitob o‘qish", 1, k, "21:30", 30);
      if (hk(kunQosh(b, k)) < 5) q("Matematika", 1, k, "09:00", 80, "dars");
    }
    q("Musorlarni tashlash", 3, 0, "08:30", 15, "oddiy", { holat: "bajarildi" });
    q("Do‘kon uchun ma’lumot tayyorlash", 1, 0, null, 60);
    q("Sanuzelni tozalash", 5, 1, "10:00", 90);
    q("Kir yuvish", 1, 3, "11:00", 90, "oddiy", { izoh: "Oq kiyimlar alohida" });
    d = { ok: true, men: 1, bugun: b, dan: dan || b, gacha: kunQosh(dan || b, KUN_SONI - 1), odamlar, turlar, vazifalar: v,
      navbat: { tur_id: 1, nom: "Ovqat qilish", ergash: "Idish yuvish" } };
  }

  async function yukla() {
    if (NAMUNA) { if (!d) namuna(); return chiz(); }
    if (!INIT) { xatoMatn = "Bu sahifani Telegram'dagi Farovon Uy botidan oching."; return chiz(); }
    if (yuklanmoqda) return;
    yuklanmoqda = true;
    try {
      d = await api(`vazifa-boshqaruv?kun=${KUN_SONI}${dan ? "&dan=" + dan : ""}`);
      xatoMatn = "";
    } catch (err) { xatoMatn = err.message; }
    yuklanmoqda = false;
    chiz();
  }

  // ── Ochish / yopish ────────────────────────────────────────────────
  function och(ekran = null, keyin = null) {
    if (!el) {
      el = document.createElement("section");
      el.className = "szv-sahifa";
      el.setAttribute("role", "dialog");
      el.setAttribute("aria-label", "Vazifalar");
      el.addEventListener("click", bosildi);
      document.body.appendChild(el);
    }
    stek = [{ t: "bosh" }];
    if (ekran) stek.push(ekran);
    kutilgan = keyin;
    chiz();
    yukla();
  }
  function yop() {
    oynaYop(true);
    if (el) { el.remove(); el = null; }
    stek = [];
    try { if (location.hash.startsWith("#sozlamalar/vazifalar")) history.replaceState(null, "", "#sozlamalar"); } catch (err) {}
    tgOrqa();
  }
  function orqa() {
    if (varaq) return oynaYop();
    if (stek.length > 1) { stek.pop(); chiz(); el.scrollTop = 0; tebran("soft"); return; }
    yop();
  }
  function xeshYoz() {
    let x = "#sozlamalar/vazifalar";
    if (joriy()?.t === "turlar") x += "/turlar";
    if (varaq) {
      if (varaq.t === "yangi") x = "#sozlamalar/vazifalar/yangi";
      if (varaq.t === "vazifa") x = "#sozlamalar/vazifalar/v/" + varaq.id;
      if (varaq.t === "tur" && varaq.id == null) x = "#sozlamalar/vazifalar/turlar/yangi";
      if (varaq.t === "tur" && varaq.id != null) x = "#sozlamalar/vazifalar/tur/" + varaq.id;
    }
    if (location.hash !== x) { try { history.replaceState(null, "", x); } catch (err) {} }
  }

  // ── Chizish ────────────────────────────────────────────────────────
  function chiz() {
    if (!el) return;
    el.innerHTML = joriy().t === "turlar" ? turlarEkran() : boshEkran();
    if (d && kutilgan) { const k = kutilgan; kutilgan = null; k(); return; }
    xeshYoz();
    tgOrqa();
  }
  const sarlavha = (nom, ong = "") => `<div class="sz-bosh ichki szv-bosh">
      <button class="sz-orqa" data-amal="orqa" aria-label="Orqaga">${IK.orqa}</button><h1>${e(nom)}</h1>${ong}</div>`;
  function holatHtml(skelet) {
    if (xatoMatn) return `<div class="sz-royxat"><div class="sz-bosh-holat">${e(xatoMatn)}<br><button data-amal="qayta">Qayta urinish</button></div></div>`;
    if (!d) return skelet;
    return "";
  }
  const skelet = (n) => `<div class="sz-royxat">${"<div class=\"sz-skelet szv-skelet\"></div>".repeat(n)}</div>`;

  function kimFiltri(v) {
    if (kim === "hammasi") return true;
    return v.odam_id === (kim === "men" ? d.men : kim);
  }
  function kunSarlavha(s) {
    const n = kunFarq(d.bugun, s);
    const nom = n === 0 ? "Bugun" : n === 1 ? "Ertaga" : n === -1 ? "Kecha" : KUNLAR[hk(s)][0].toUpperCase() + KUNLAR[hk(s)].slice(1);
    return `<b>${nom}</b><span>${n === 0 || n === 1 || n === -1 ? KUNLAR[hk(s)] + ", " : ""}${dm(s)}</span>`;
  }

  function boshEkran() {
    const bosh = sarlavha("Vazifalar", `<button class="sz-ikon-tugma" data-amal="turlar" aria-label="Vazifa turlari">${IK.turlar}</button>`);
    const hol = holatHtml(`<div class="szv-chiplar">${"<span class=\"szv-chip-sk\"></span>".repeat(4)}</div>${skelet(5)}`);
    if (hol) return bosh + hol;
    const chiplar = [["men", "Men", odam(d.men)?.rang], ...d.odamlar.filter((o) => o.id !== d.men).map((o) => [o.id, o.nom, o.rang]), ["hammasi", "Hammasi", null]];
    const korinadi = d.vazifalar.filter(kimFiltri);
    const kunlar = [];
    for (let s = d.dan; s <= d.gacha; s = kunQosh(s, 1)) kunlar.push(s);
    const bitta = kim !== "hammasi";
    const royxat = kunlar.map((s) => {
      const xs = korinadi.filter((v) => v.sana === s)
        .sort((a, b) => (a.vaqt || "99:99").localeCompare(b.vaqt || "99:99") || a.id - b.id);
      return `<div class="szv-kun${s === d.bugun ? " bugun" : ""}">${kunSarlavha(s)}<em>${xs.length ? xs.length + " ta" : ""}</em></div>
        ${xs.length ? `<div class="sz-royxat szv-royxat">${xs.map((v) => qatorHtml(v, bitta)).join("")}</div>`
          : `<div class="szv-bosh-kun">Vazifa yo‘q</div>`}`;
    }).join("");
    const oraliq = `${dm(d.dan)} – ${dm(d.gacha)}`;
    return `${bosh}
      <div class="szv-chiplar">${chiplar.map(([k, nom, r]) => `<button class="sz-chip szv-chip${String(kim) === String(k) ? " faol" : ""}" data-kim="${k}">${r ? `<i style="background:${e(r)}"></i>` : ""}${e(nom)}</button>`).join("")}</div>
      <div class="szv-hafta">
        <button class="szv-hafta-t" data-amal="oldin" aria-label="Oldingi hafta"${d.dan <= d.bugun ? " disabled" : ""}>${IK.chap}</button>
        <span>${oraliq}${d.dan !== d.bugun ? `<button data-amal="bugunga">Bugunga</button>` : ""}</span>
        <button class="szv-hafta-t" data-amal="keyin" aria-label="Keyingi hafta">${IK.ongK}</button>
      </div>
      <button class="sz-kok-tugma" data-amal="yangi">${IK.plyus}Yangi vazifa</button>
      ${royxat}
      <button class="sz-q szv-turlar-q" data-amal="turlar"><span class="szv-belgi">${IK.turlar}</span>
        <span class="szv-matn"><b>Vazifa turlari</b><small>${d.turlar.length} ta tur · nomi, davomiyligi, shaxsiy yoki umumiy</small></span>${IK.ong}</button>`;
  }

  function nishonlar(v) {
    const n = [];
    if (v.tur === "dars") n.push(`<span class="szv-n dars">${IK.qulf}Dars</span>`);
    else n.push(`<span class="szv-n t-${v.toifa}">${TOIFA[v.toifa] || "Boshqa"}</span>`);
    if (v.tur === "navbat") n.push(`<span class="szv-n navbat">Navbat</span>`);
    if (v.takror) n.push(`<span class="szv-n takror">${IK.takror}Takror</span>`);
    return n.join("");
  }
  function qatorHtml(v, bitta) {
    const o = odam(v.odam_id);
    const tayyor = v.holat !== "ochiq";
    return `<button class="sz-q szv-q${tayyor ? " tayyor" : ""}" data-vazifa="${v.id}" style="--r:${e(o?.rang || "#8a94a6")}">
      <span class="szv-vaqt"><b>${v.vaqt || "—"}</b><small>${davMatn(v.davomiylik)}</small></span>
      <span class="szv-matn"><b>${tayyor ? `<span class="szv-ok">${IK.ok}</span>` : ""}${e(v.nom)}</b>
        <small>${bitta ? "" : `<span class="szv-kim">${e(o?.nom || "?")}</span>`}${nishonlar(v)}</small></span>${IK.ong}</button>`;
  }

  function turlarEkran() {
    const bosh = sarlavha("Vazifa turlari");
    const hol = holatHtml(skelet(6));
    if (hol) return bosh + hol;
    return `${bosh}
      <p class="szv-izoh">Tur — tayyor ish nomi va odatdagi davomiyligi. <b>Shaxsiy</b> ish guruhga chiqmaydi, bot uni faqat egasiga yozadi.</p>
      <button class="sz-kok-tugma" data-amal="yangiTur">${IK.plyus}Yangi tur</button>
      <div class="sz-royxat szv-turlar">${d.turlar.map((t) => `<button class="sz-q szv-tq" data-tur="${t.id}">
        <span class="szv-matn"><b>${e(t.nom)}</b><small>${davMatn(t.davomiylik)}${t.qadamlar.length ? ` · ${t.qadamlar.length} ta qadam` : ""}</small>
        <span class="szv-nlar">${turNishon(t)}</span></span>${IK.ong}</button>`).join("") || `<div class="sz-bosh-holat">Hali tur yo‘q</div>`}</div>`;
  }
  function turNishon(t) {
    const n = [t.shaxsiy ? `<span class="szv-n t-shaxsiy">${IK.qulf}Shaxsiy</span>` : `<span class="szv-n t-uy">Umumiy</span>`];
    if (t.navbat) n.push(`<span class="szv-n navbat">Ovqat navbati</span>`);
    if (t.ergash) n.push(`<span class="szv-n navbat">Ovqatdan keyin</span>`);
    if (t.haftalik) n.push(`<span class="szv-n haftalik">General uborka</span>`);
    if (t.dars) n.push(`<span class="szv-n dars">Dars</span>`);
    return n.join("");
  }

  // ── Oyna (pastdan) ─────────────────────────────────────────────────
  let parda, oyna;
  function oynaElementlari() {
    if (oyna) return;
    parda = document.createElement("div"); parda.className = "sz-parda szv-parda";
    oyna = document.createElement("div"); oyna.className = "sz-oyna szv-oyna"; oyna.setAttribute("role", "dialog");
    document.body.append(parda, oyna);
    parda.onclick = () => oynaYop();
    oyna.addEventListener("click", oynaBosildi);
    oyna.addEventListener("input", oynaKiritildi);
    oyna.addEventListener("change", oynaKiritildi);
  }
  function oynaOch(v) {
    varaq = v; oynaElementlari(); oynaChiz(); xeshYoz(); tgOrqa();
    oyna.scrollTop = 0;
    if (v.t === "vazifa" && v.r.navbat) navbatOldin();
  }
  function oynaYop(jim) {
    varaq = null;
    if (oyna) { parda.classList.remove("ochiq"); oyna.classList.remove("ochiq"); }
    if (!jim) { xeshYoz(); tgOrqa(); }
  }
  function oynaChiz() {
    if (!varaq) return;
    const y = oyna.scrollTop;
    oyna.innerHTML = oynaHtml(varaq);
    oyna.scrollTop = y;
    parda.classList.add("ochiq"); oyna.classList.add("ochiq");
  }
  const oynaBosh = (matn) => `<div class="sz-oyna-bosh"><h3>${matn}</h3><button class="sz-yop" data-amal="yop" aria-label="Yopish">${IK.x}</button></div>`;
  const ogoh = (v) => (v.xato ? `<div class="sz-ogoh">${IK.ogoh}<span>${e(v.xato)}</span></div>` : "");
  const qoida = (m) => (m ? `<div class="szv-qoida">${IK.info}<span>${e(m)}</span></div>` : "");
  const qulf = (ok) => (ok ? "" : ` <span class="szv-qulf">${IK.qulf}</span>`);
  const dis = (ok) => (ok ? "" : " disabled");

  /** Yangi vazifa formasi (VazifaDialog birlamchi qiymatlari). */
  function yangiForma(tur_id = null) {
    const t = tur_id != null ? tur(tur_id) : null;
    const sana = d.dan > d.bugun ? d.dan : d.bugun;
    const v = { t: "yangi", nom: t ? t.nom : "", tur_id: t ? t.id : null, odam_id: kim === "men" || kim === "hammasi" ? d.men : kim,
      sana, vaqtsiz: false, vaqt: "09:00", davomiylik: t ? t.davomiylik : 60, izoh: "",
      takror: false, naqsh: "kunlik", kunlar: [hk(sana)], oraliq: 2, navbat: false, navbatKun: 7, xato: "" };
    turQoy(v, t);
    return v;
  }
  function turQoy(v, t) {
    v.tur_id = t ? t.id : null;
    if (!t) return;
    v.nom = t.nom; v.davomiylik = t.davomiylik;
    if (v.t === "yangi") {
      v.navbat = !!t.navbat;
      if (t.navbat) { v.takror = false; v.vaqt = "19:00"; v.vaqtsiz = false; }
    }
  }
  function vazifaForma(x) {
    return { t: "vazifa", id: x.id, r: x.ruxsat, asl: x, nom: x.nom, tur_id: x.tur_id, odam_id: x.odam_id, sana: x.sana,
      vaqtsiz: !x.vaqt, vaqt: x.vaqt || "09:00", davomiylik: x.davomiylik, izoh: x.izoh || "", xato: "",
      yangiOdam: null, navbatReja: null, tasdiq: null };
  }

  function oynaHtml(v) {
    if (v.t === "yangi" || v.t === "vazifa") return vazifaHtml(v);
    if (v.t === "tur") return turHtml(v);
    return "";
  }

  function odamChiplar(tanlangan, ok, data = "odam") {
    return `<div class="szv-odamlar">${d.odamlar.map((o) => `<button class="sz-chip szv-chip${o.id === tanlangan ? " faol" : ""}" data-${data}="${o.id}"${dis(ok)}>
      <i style="background:${e(o.rang)}"></i>${e(o.nom)}</button>`).join("")}</div>`;
  }

  function vazifaHtml(v) {
    const yangi = v.t === "yangi";
    const r = yangi ? null : v.r;
    const m = r ? r.maydon : { nom: true, sana: true, kim: true, vaqt: true, davomiylik: true, izoh: true };
    const x = yangi ? null : v.asl;
    if (v.tasdiq) return tasdiqHtml(v);
    const tanlanganTur = v.tur_id != null ? tur(v.tur_id) : turNom(v.nom);
    const turlarHtml = m.nom && d.turlar.length ? `<div class="sz-yorliq">Qanday vazifa</div>
      <div class="szv-turchip">${d.turlar.filter((t) => !t.dars).map((t) => `<button class="sz-chip${tanlanganTur && tanlanganTur.id === t.id ? " faol" : ""}" data-turtanla="${t.id}">${e(t.nom)}</button>`).join("")}</div>` : "";
    const sarl = yangi ? "Yangi vazifa" : x.tur === "dars" ? "Dars" : "Vazifa";
    const holat = !yangi && x.holat !== "ochiq" ? `<div class="szv-holat">${IK.ok}${x.holat === "qazo" ? "Qazo bo‘ldi" : "Bajarildi"}</div>` : "";
    const takrorHtml = yangi && !v.navbat ? `
      <label class="szv-almash"><input type="checkbox" id="szvTakror"${v.takror ? " checked" : ""}><span><b>Takrorlansin</b><small>Bitta qoida — kalendar ${UFQ} kunga oldindan o‘zi to‘ladi</small></span></label>
      ${v.takror ? `<div class="szv-seg">${NAQSH.map(([k, n]) => `<button class="${v.naqsh === k ? "faol" : ""}" data-naqsh="${k}">${n}</button>`).join("")}</div>
        ${v.naqsh === "kunlar" ? `<div class="szv-hk">${KUN_QISQA.map((n, i) => `<button class="${v.kunlar.includes(i) ? "faol" : ""}" data-hk="${i}">${n}</button>`).join("")}</div>` : ""}
        ${v.naqsh === "oraliq" ? `<label class="szv-oraliq">Har <input class="sz-kirit" id="szvOraliq" type="number" inputmode="numeric" min="1" max="90" value="${e(v.oraliq)}"> kunda</label>` : ""}
        <div class="szv-oldin" id="szvOldin">${takrorOldin(v)}</div>` : ""}` : "";
    const navbatHtml = yangi && v.navbat !== undefined && tanlanganTur?.navbat ? `
      <label class="szv-almash"><input type="checkbox" id="szvNavbat"${v.navbat ? " checked" : ""}><span><b>Navbat bilan davom etsin</b><small>Har kuni keyingi odam pishiradi, idishni o‘sha odamning o‘zi yuvadi</small></span></label>
      ${v.navbat ? `<label class="szv-oraliq">Necha kun: <input class="sz-kirit" id="szvNavbatKun" type="number" inputmode="numeric" min="1" max="28" value="${e(v.navbatKun)}"></label>
        <div class="szv-oldin">${navbatOldinMatn(v)}</div>` : ""}` : "";
    const korinish = !yangi && r.shaxsiy ? `
      <div class="sz-yorliq szv-ajrat">Kimga ko‘rinadi</div>
      <div class="szv-seg">
        <button class="${x.shaxsiy ? "" : "faol"}" data-shaxsiy="0">Umumiy — guruhga</button>
        <button class="${x.shaxsiy ? "faol" : ""}" data-shaxsiy="1">${IK.qulf}Shaxsiy — faqat egasiga</button>
      </div>
      <p class="szv-kichik">«${e(x.nom)}» turiga yoziladi — shu nomli hamma vazifaga tegadi.</p>` : "";
    const navbatBlok = !yangi && r.navbat ? `
      <div class="szv-navbat">
        <div class="szv-odamlar">${d.odamlar.map((o) => `<button class="sz-chip szv-chip${o.id === v.odam_id ? " joriy" : ""}${o.id === v.yangiOdam ? " faol" : ""}" data-yangiodam="${o.id}"${o.id === v.odam_id ? " disabled" : ""}><i style="background:${e(o.rang)}"></i>${e(o.nom)}${o.id === v.odam_id ? " · hozir" : ""}</button>`).join("")}</div>
        <div class="szv-oldin">${v.yangiOdam == null ? "Navbatni kimga o‘tkazish kerak — o‘sha odamni tanlang." : v.navbatReja == null ? "…" : v.navbatReja.mumkin
          ? `Almashtirilsa: <b>${dmQ(v.navbatReja.sana)}</b> — ${e(v.navbatReja.yangi)}, <b>${dmQ(v.navbatReja.juft_sana)}</b> — ${e(v.navbatReja.eski)}. Qolgan kunlarga tegilmaydi.`
          : e(v.navbatReja.sabab)}</div>
        <div class="sz-ikki">
          <button class="sz-och-tugma" data-amal="almashtir"${v.yangiOdam == null || !v.navbatReja?.mumkin || v.band ? " disabled" : ""}>${IK.almash}Almashtirish</button>
          <button class="sz-och-tugma" data-amal="bersin"${v.yangiOdam == null || v.band ? " disabled" : ""}>Faqat shu kunni berish</button>
        </div>
      </div>` : "";
    const biror = Object.values(m).some(Boolean);
    const ochirHtml = !yangi && r.ochir ? `<div class="szv-ochirlar">
        <button class="szv-qizil" data-amal="ochirKun">${IK.savat}${x.takror ? "Faqat shu kunni o‘chirish" : "Vazifani o‘chirish"}</button>
        ${x.takror ? `<button class="szv-qizil" data-amal="ochirQoida">${IK.takror}Takrorni to‘xtatish</button>` : ""}
      </div>` : "";
    return `${oynaBosh(sarl)}
      ${holat}${r ? qoida(r.izoh) : ""}${!yangi && x.takror ? `<div class="szv-takror">${IK.takror}<span>${e(x.takror.tavsif)}</span></div>` : ""}
      ${turlarHtml}
      <label class="sz-yorliq" for="szvNom">Nomi${qulf(m.nom)}</label>
      <input class="sz-kirit" id="szvNom" maxlength="120" autocomplete="off" placeholder="Masalan: Kir yuvish" value="${e(v.nom)}"${dis(m.nom)}>
      <div class="sz-yorliq">Kim bajaradi${r?.navbat ? "" : qulf(m.kim)}</div>
      ${r?.navbat ? navbatBlok : odamChiplar(v.odam_id, m.kim)}
      <div class="szv-ikki">
        <div><label class="sz-yorliq" for="szvSana">Kun${qulf(m.sana)}</label>
          <input class="sz-kirit" id="szvSana" type="date" value="${e(v.sana)}"${dis(m.sana)}></div>
        <div><label class="sz-yorliq" for="szvVaqt">Vaqt${qulf(m.vaqt)}</label>
          <input class="sz-kirit" id="szvVaqt" type="time" value="${v.vaqtsiz ? "" : e(v.vaqt)}"${dis(m.vaqt && !v.vaqtsiz)}></div>
      </div>
      <label class="szv-almash kichik"><input type="checkbox" id="szvVaqtsiz"${v.vaqtsiz ? " checked" : ""}${dis(m.vaqt)}><span>Aniq vaqtsiz (kun davomida)</span></label>
      <div class="sz-yorliq">Davomiyligi${qulf(m.davomiylik)}</div>
      <div class="szv-davom">${DAVOM.map((n) => `<button class="sz-chip${v.davomiylik === n ? " faol" : ""}" data-davom="${n}"${dis(m.davomiylik)}>${davMatn(n)}</button>`).join("")}
        <input class="sz-kirit" id="szvDavom" type="number" inputmode="numeric" min="1" max="720" value="${e(v.davomiylik)}" aria-label="Daqiqa"${dis(m.davomiylik)}><span>daq</span></div>
      <label class="sz-yorliq" for="szvIzoh">Izoh <span class="ixtiyoriy">(ixtiyoriy)</span>${qulf(m.izoh)}</label>
      <input class="sz-kirit" id="szvIzoh" maxlength="200" autocomplete="off" placeholder="Ixtiyoriy" value="${e(v.izoh)}"${dis(m.izoh)}>
      ${takrorHtml}${navbatHtml}
      ${ogoh(v)}
      ${biror ? `<button class="sz-kok-tugma" data-amal="saqla"${v.band ? " disabled" : ""}>${yangi ? "Qo‘shish" : "Saqlash"}</button>` : ""}
      ${korinish}${ochirHtml}`;
  }

  function takrorSanalari(v) {
    const b = v.sana, natija = [];
    for (let k = b, i = 0; i <= UFQ && natija.length < 6; k = kunQosh(k, 1), i++) {
      const mos = v.naqsh === "kunlar" ? v.kunlar.includes(hk(k)) : v.naqsh === "oraliq" ? kunFarq(b, k) % Math.max(1, Number(v.oraliq) || 1) === 0 : true;
      if (mos) natija.push(k);
    }
    return natija;
  }
  function takrorOldin(v) {
    if (v.naqsh === "kunlar" && !v.kunlar.length) return "Kamida bitta hafta kuni tanlanishi kerak.";
    const s = takrorSanalari(v);
    return `${s.map(dmQ).join(" · ")}${s.length >= 6 ? " …" : ""}<br>Kalendar ${UFQ} kunga oldindan to‘ldiriladi va o‘zi davom etadi.`;
  }
  function navbatOldinMatn(v) {
    const idlar = d.odamlar.map((o) => o.id);
    const n = Math.max(1, Math.min(28, Number(v.navbatKun) || 7));
    const b = idlar.indexOf(v.odam_id);
    if (idlar.length < 2) return "Navbat uchun kamida ikkita faol odam kerak.";
    const qator = [];
    for (let i = 0; i < Math.min(n, 4); i++) qator.push(`${dmQ(kunQosh(v.sana, i))} — ${e(odam(idlar[(b + i) % idlar.length]).nom)}`);
    const erg = d.navbat?.ergash;
    return `${qator.join(" · ")}${n > 4 ? " …" : ""}<br>${erg ? `Jami ${n * 2} ta vazifa (ovqat + idish).` : "⚠ Ovqatdan keyingi ish tanlanmagan — faqat pishirish yoziladi."}`;
  }

  function tasdiqHtml(v) {
    const x = v.asl;
    if (v.tasdiq === "kun") {
      return `${oynaBosh(x.takror ? "Shu kunni o‘chirish" : "Vazifani o‘chirish")}
        <p class="sz-matn"><b>«${e(x.nom)}»</b> (${dmQ(x.sana)}) kalendardan olib tashlanadi, tarixda qoladi.${x.takror ? " Takror qoidasi davom etadi — bu kun qayta tirilmaydi." : ""}</p>
        ${ogoh(v)}<div class="sz-ikki"><button class="sz-kulrang-tugma" data-amal="bekor">Bekor qilish</button>
        <button class="sz-qizil-tugma" data-amal="ochirHa"${v.band ? " disabled" : ""}>O‘chirish</button></div>`;
    }
    if (v.tasdiq === "qoida") {
      return `${oynaBosh("Takrorni to‘xtatish")}
        <p class="sz-matn"><b>«${e(x.nom)}»</b> takrori to‘xtatiladi. Bugundan boshlab hali bajarilmagan kunlar kalendardan olib tashlanadi; o‘tgan va bajarilgan kunlar joyida qoladi.</p>
        ${ogoh(v)}<div class="sz-ikki"><button class="sz-kulrang-tugma" data-amal="bekor">Bekor qilish</button>
        <button class="sz-qizil-tugma" data-amal="ochirHa"${v.band ? " disabled" : ""}>To‘xtatish</button></div>`;
    }
    const o = odam(v.yangiOdam)?.nom || "?";
    const p = v.navbatReja;
    const matn = v.tasdiq === "almashtir"
      ? `Ikki navbat almashadi:<br>• <b>${dmQ(p.sana)}</b> — ${e(p.eski)} o‘rniga ${e(p.yangi)}<br>• <b>${dmQ(p.juft_sana)}</b> — ${e(p.yangi)} o‘rniga ${e(p.eski)}<br>Qolgan kunlarga tegilmaydi, navbat soni ikkalasida ham o‘zgarmaydi.`
      : `<b>«${e(x.nom)}»</b> (${dmQ(x.sana)}) ${e(o)}ga o‘tadi. Almashuv yo‘q — boshqa kunlarga tegilmaydi.`;
    return `${oynaBosh(v.tasdiq === "almashtir" ? "Navbatni almashtirish" : "Faqat shu kunni berish")}
      <p class="sz-matn">${matn}</p><p class="szv-kichik">Kim pishirsa, idishni ham o‘sha yuvadi — o‘sha kunning yuvuvchisi ham o‘zi to‘g‘rilanadi.</p>
      ${ogoh(v)}<div class="sz-ikki"><button class="sz-kulrang-tugma" data-amal="bekor">Bekor qilish</button>
      <button class="sz-kok-tugma" data-amal="navbatHa"${v.band ? " disabled" : ""}>Tasdiqlash</button></div>`;
  }

  function turHtml(v) {
    const t = v.id != null ? tur(v.id) : null;
    if (v.tasdiq) {
      const ogohMatn = t.navbat ? " Bu ovqat navbatining ishi — navbat endi tuzilmaydi." : t.ergash ? " Ovqat navbati endi idish yuvishni yozmaydi." : t.haftalik ? " U general uborkadan ham chiqadi." : "";
      return `${oynaBosh("Turni o‘chirish")}
        <p class="sz-matn"><b>«${e(t.nom)}»</b> ro‘yxatdan olib tashlanadi. Allaqachon biriktirilgan vazifalar kalendarda qoladi.${ogohMatn}</p>
        ${ogoh(v)}<div class="sz-ikki"><button class="sz-kulrang-tugma" data-amal="bekor">Bekor qilish</button>
        <button class="sz-qizil-tugma" data-amal="turOchirHa"${v.band ? " disabled" : ""}>O‘chirish</button></div>`;
    }
    const davom = `<div class="sz-yorliq">Odatdagi davomiyligi</div>
      <div class="szv-davom">${DAVOM.map((n) => `<button class="sz-chip${v.davomiylik === n ? " faol" : ""}" data-davom="${n}">${davMatn(n)}</button>`).join("")}
        <input class="sz-kirit" id="szvDavom" type="number" inputmode="numeric" min="1" max="720" value="${e(v.davomiylik)}" aria-label="Daqiqa"><span>daq</span></div>`;
    const kimga = `<div class="sz-yorliq">Kimga</div>
      <div class="szv-seg ustun">
        <button class="${v.shaxsiy ? "" : "faol"}" data-turshaxsiy="0"${t?.dars ? " disabled" : ""}><b>Umumiy</b><small>Uy guruhiga e’lon qilinadi</small></button>
        <button class="${v.shaxsiy ? "faol" : ""}" data-turshaxsiy="1"><b>${IK.qulf}Shaxsiy</b><small>Faqat egasiga, bot bilan shaxsiy suhbatda</small></button>
      </div>`;
    if (!t) {
      return `${oynaBosh("Yangi vazifa turi")}
        <label class="sz-yorliq" for="szvNom">Nomi</label>
        <input class="sz-kirit" id="szvNom" maxlength="80" autocomplete="off" placeholder="Masalan: Kir yuvish" value="${e(v.nom)}">
        ${davom}${kimga}${ogoh(v)}
        <button class="sz-kok-tugma" data-amal="turSaqla"${v.band ? " disabled" : ""}>Qo‘shish</button>`;
    }
    return `${oynaBosh(e(t.nom))}
      <div class="szv-nlar keng">${turNishon(t)}</div>
      ${t.dars ? qoida("Dars fani — EduPage jadvalidan. Shaxsiy bo‘lib qolishi shart, aks holda dars guruhga chiqib ketadi.") : ""}
      <p class="szv-kichik">Nomi o‘zgartirilmaydi: vazifalar turga nomi orqali bog‘langan (shaxsiy filtr, qadamlar, navbat).</p>
      ${davom}${kimga}${ogoh(v)}
      <button class="sz-kok-tugma" data-amal="turSaqla"${v.band ? " disabled" : ""}>Saqlash</button>
      <div class="szv-blok">
        <div class="sz-yorliq">Qadamlar <span class="ixtiyoriy">— guruh xabarida ro‘yxat bo‘lib chiqadi</span></div>
        ${t.qadamlar.length ? `<div class="szv-qadamlar">${t.qadamlar.map((q, i) => `<div class="szv-qadam"><em>${i + 1}</em><span>${e(q.nom)}</span>
          <button data-qadamochir="${q.id}" aria-label="Olib tashlash"${v.band ? " disabled" : ""}>${IK.x}</button></div>`).join("")}</div>` : `<p class="szv-kichik">Hali qadam yo‘q.</p>`}
        <div class="szv-qadam-qosh"><input class="sz-kirit" id="szvQadam" maxlength="80" autocomplete="off" placeholder="Masalan: Pol" value="${e(v.qadam || "")}">
          <button class="sz-och-tugma" data-amal="qadamQosh"${v.band ? " disabled" : ""}>${IK.plyus}</button></div>
      </div>
      ${t.dars ? "" : `<div class="szv-ochirlar"><button class="szv-qizil" data-amal="turOchir">${IK.savat}Turni o‘chirish</button></div>`}`;
  }

  // ── Kiritish ───────────────────────────────────────────────────────
  function oynaKiritildi(ev) {
    const t = ev.target, v = varaq;
    if (!v) return;
    if (t.id === "szvNom") { v.nom = t.value; if (v.tur_id != null && tur(v.tur_id)?.nom !== t.value.trim()) v.tur_id = null; }
    if (t.id === "szvSana" && t.value) { v.sana = t.value; if (ev.type === "change") oynaChiz(); }
    if (t.id === "szvVaqt") v.vaqt = t.value || v.vaqt;
    if (t.id === "szvIzoh") v.izoh = t.value;
    if (t.id === "szvQadam") v.qadam = t.value;
    if (t.id === "szvDavom") {
      v.davomiylik = Number(t.value) || 0;
      oyna.querySelectorAll("[data-davom]").forEach((b) => b.classList.toggle("faol", Number(b.dataset.davom) === v.davomiylik));
    }
    if (t.id === "szvOraliq") { v.oraliq = t.value; const o = document.getElementById("szvOldin"); if (o) o.innerHTML = takrorOldin(v); }
    if (t.id === "szvNavbatKun" && ev.type === "change") { v.navbatKun = t.value; oynaChiz(); }
    if (ev.type !== "change") return;
    if (t.id === "szvVaqtsiz") { v.vaqtsiz = t.checked; oynaChiz(); }
    if (t.id === "szvTakror") { v.takror = t.checked; oynaChiz(); }
    if (t.id === "szvNavbat") { v.navbat = t.checked; oynaChiz(); }
  }

  function oynaBosildi(ev) {
    const t = ev.target.closest("button"); if (!t || !varaq || t.disabled) return;
    const v = varaq, a = t.dataset.amal;
    if (a === "yop") return oynaYop();
    if (a === "bekor") { v.tasdiq = null; v.xato = ""; return oynaChiz(); }
    if (t.dataset.odam) { v.odam_id = Number(t.dataset.odam); v.xato = ""; tebran("soft"); return oynaChiz(); }
    if (t.dataset.turtanla) { turQoy(v, tur(Number(t.dataset.turtanla))); v.xato = ""; tebran("soft"); return oynaChiz(); }
    if (t.dataset.davom) { v.davomiylik = Number(t.dataset.davom); tebran("soft"); return oynaChiz(); }
    if (t.dataset.naqsh) { v.naqsh = t.dataset.naqsh; v.xato = ""; return oynaChiz(); }
    if (t.dataset.hk) {
      const k = Number(t.dataset.hk);
      v.kunlar = v.kunlar.includes(k) ? v.kunlar.filter((x) => x !== k) : [...v.kunlar, k].sort();
      return oynaChiz();
    }
    if (t.dataset.yangiodam) {
      v.yangiOdam = Number(t.dataset.yangiodam); v.navbatReja = null; v.xato = "";
      oynaChiz(); return navbatOldin();
    }
    if (t.dataset.shaxsiy) return shaxsiyQoy(t.dataset.shaxsiy === "1");
    if (t.dataset.turshaxsiy) { v.shaxsiy = t.dataset.turshaxsiy === "1"; return oynaChiz(); }
    if (t.dataset.qadamochir) return turAmal(`tur-qadam-ochir`, Number(t.dataset.qadamochir));
    if (a === "saqla") return vazifaSaqla();
    if (a === "almashtir" || a === "bersin") { v.tasdiq = a; return oynaChiz(); }
    if (a === "navbatHa") return navbatYoz();
    if (a === "ochirKun") { v.tasdiq = "kun"; return oynaChiz(); }
    if (a === "ochirQoida") { v.tasdiq = "qoida"; return oynaChiz(); }
    if (a === "ochirHa") return vazifaOchir();
    if (a === "turSaqla") return turSaqla();
    if (a === "turOchir") { v.tasdiq = "tur"; return oynaChiz(); }
    if (a === "turOchirHa") return turAmal("tur-ochir");
    if (a === "qadamQosh") return turAmal("qadam-qosh");
  }

  // ── Yozish ─────────────────────────────────────────────────────────
  /** Bitta yozuv: namunada xotirada, aks holda API; keyin ro‘yxat qayta olinadi. */
  async function yoz(v, yol, tana, ok, keyin) {
    if (v.band) return;
    v.band = true; v.xato = ""; oynaChiz();
    try {
      if (NAMUNA) namunaYoz(yol, tana);
      else { await api("vazifa-boshqaruv/" + yol, tana); await yukla(); }
      v.band = false;
      tebran("medium");
      if (keyin) keyin(); else oynaYop();
      chiz();
      if (ok) xabar(ok);
    } catch (err) {
      v.band = false; v.xato = err.message;
      if (varaq === v) oynaChiz();
    }
  }

  function vazifaSaqla() {
    const v = varaq;
    const nom = v.nom.trim();
    if (!nom) { v.xato = "Vazifa nomini yozing"; return oynaChiz(); }
    const vaqt = v.vaqtsiz ? null : v.vaqt || null;
    if (v.t === "yangi") {
      const tana = { nom, odam_id: v.odam_id, sana: v.sana, vaqt, davomiylik: v.davomiylik, izoh: v.izoh };
      const t = v.tur_id != null ? tur(v.tur_id) : null;
      if (t?.navbat && v.navbat) tana.navbat = { tur_id: t.id, kunlar: Number(v.navbatKun) || 7 };
      else if (v.takror) tana.takror = { naqsh: v.naqsh, kunlar: v.kunlar, oraliq: Number(v.oraliq) };
      const ok = tana.navbat ? "Ovqat navbati tuzildi" : tana.takror ? "Takroriy vazifa qo‘shildi" : "Vazifa qo‘shildi";
      return yoz(v, "vazifa", tana, ok);
    }
    // Faqat o‘zgargan va ruxsat etilgan maydonlar
    const x = v.asl, m = v.r.maydon, tana = {};
    if (m.nom && nom !== x.nom) tana.nom = nom;
    if (m.kim && v.odam_id !== x.odam_id) tana.odam_id = v.odam_id;
    if (m.sana && v.sana !== x.sana) tana.sana = v.sana;
    if (m.vaqt && vaqt !== (x.vaqt || null)) tana.vaqt = vaqt;
    if (m.davomiylik && v.davomiylik !== x.davomiylik) tana.davomiylik = v.davomiylik;
    if (m.izoh && v.izoh.trim() !== (x.izoh || "")) tana.izoh = v.izoh;
    if (!Object.keys(tana).length) { oynaYop(); return xabar("O‘zgarish yo‘q"); }
    return yoz(v, `vazifa/${v.id}`, tana, "Saqlandi");
  }
  function vazifaOchir() {
    const v = varaq;
    if (v.tasdiq === "qoida") return yoz(v, `vazifa/${v.id}/takror-ochir`, {}, "Takror to‘xtatildi");
    return yoz(v, `vazifa/${v.id}/ochir`, {}, "Vazifa o‘chirildi");
  }
  function navbatYoz() {
    const v = varaq;
    return yoz(v, `vazifa/${v.id}/navbat`, { odam_id: v.yangiOdam, usul: v.tasdiq },
      v.tasdiq === "almashtir" ? "Navbat almashdi" : "Shu kun berildi");
  }
  function shaxsiyQoy(shaxsiy) {
    const v = varaq;
    if (Boolean(v.asl.shaxsiy) === shaxsiy) return;
    return yoz(v, `vazifa/${v.id}/shaxsiy`, { shaxsiy }, shaxsiy ? "Endi shaxsiy — guruhga chiqmaydi" : "Endi umumiy — guruhga chiqadi", () => {
      const x = vazifa(v.id);
      if (x) { v.asl = x; oynaChiz(); } else oynaYop();
    });
  }
  async function navbatOldin() {
    const v = varaq;
    if (!v || v.t !== "vazifa" || v.yangiOdam == null) return;
    const kimga = v.yangiOdam;
    let r;
    if (NAMUNA) {
      const x = v.asl;
      const juft = d.vazifalar.filter((y) => y.nom === x.nom && y.odam_id === kimga && y.sana > x.sana).sort((a, b) => a.sana.localeCompare(b.sana))[0];
      r = kimga === x.odam_id ? { mumkin: false, sabab: "Bu vazifa allaqachon o'shanikida" }
        : juft ? { mumkin: true, sana: x.sana, juft_sana: juft.sana, eski: odam(x.odam_id).nom, yangi: odam(kimga).nom }
          : { mumkin: false, sabab: `${odam(kimga).nom}ning bundan keyin «${x.nom}» navbati yo'q — almashtirib bo'lmaydi. «Faqat shu kunni berish» dan foydalaning.` };
    } else {
      try { r = await api(`vazifa-boshqaruv/vazifa/${v.id}/navbat?odam=${kimga}`); } catch (err) { r = { mumkin: false, sabab: err.message }; }
    }
    if (varaq === v && v.yangiOdam === kimga) { v.navbatReja = r; if (!v.tasdiq) oynaChiz(); }
  }

  function turSaqla() {
    const v = varaq;
    const dav = Number(v.davomiylik);
    if (v.id == null) {
      if (!v.nom.trim()) { v.xato = "Tur nomini yozing"; return oynaChiz(); }
      return yoz(v, "tur", { nom: v.nom.trim(), davomiylik: dav, shaxsiy: v.shaxsiy }, "Tur qo‘shildi");
    }
    const t = tur(v.id), tana = {};
    if (dav !== t.davomiylik) tana.davomiylik = dav;
    if (v.shaxsiy !== t.shaxsiy) tana.shaxsiy = v.shaxsiy;
    if (!Object.keys(tana).length) { oynaYop(); return xabar("O‘zgarish yo‘q"); }
    return yoz(v, `tur/${v.id}`, tana, "Saqlandi");
  }
  function turAmal(nima, qid) {
    const v = varaq;
    if (nima === "tur-ochir") return yoz(v, `tur/${v.id}/ochir`, {}, "Tur o‘chirildi");
    const qayta = () => { if (tur(v.id)) { v.qadam = ""; oynaChiz(); } else oynaYop(); };
    if (nima === "qadam-qosh") {
      const nom = (v.qadam || "").trim();
      if (!nom) return document.getElementById("szvQadam")?.focus();
      return yoz(v, `tur/${v.id}/qadam`, { nom }, null, () => { qayta(); setTimeout(() => document.getElementById("szvQadam")?.focus(), 30); });
    }
    if (nima === "tur-qadam-ochir") return yoz(v, `qadam/${qid}/ochir`, {}, null, qayta);
  }

  // Namuna rejimi — server qoidalarining soddasi (faqat ko‘rish uchun).
  function namunaYoz(yol, tana) {
    const q = yol.split("/");
    const yangiId = () => Math.max(0, ...d.vazifalar.map((x) => x.id)) + 1;
    if (yol === "vazifa") {
      if (!tana.nom.trim()) throw new Error("Vazifa nomi bo'sh bo'lishi mumkin emas");
      const t = turNom(tana.nom);
      const asos = { nom: tana.nom, odam_id: tana.odam_id, vaqt: tana.vaqt, davomiylik: tana.davomiylik, izoh: tana.izoh || null, holat: "ochiq",
        toifa: t ? (t.shaxsiy ? "shaxsiy" : "uy") : "boshqa", tur: "oddiy", tur_id: t?.id ?? null, shaxsiy: !!t?.shaxsiy, takror: null,
        ruxsat: { maydon: { nom: true, sana: true, kim: true, vaqt: true, davomiylik: true, izoh: true }, ochir: true, navbat: false, shaxsiy: true, izoh: "" } };
      const sanalar = tana.takror ? takrorSanalari({ sana: tana.sana, ...tana.takror }) : [tana.sana];
      for (const s of sanalar) d.vazifalar.push({ ...asos, id: yangiId(), sana: s, ...(tana.takror ? { tur: "takror", takror: { id: 99, tavsif: "Takroriy" } } : {}) });
      return;
    }
    if (q[0] === "vazifa") {
      const x = vazifa(Number(q[1]));
      if (!q[2]) return Object.assign(x, tana);
      if (q[2] === "ochir") { d.vazifalar = d.vazifalar.filter((y) => y !== x); return; }
      if (q[2] === "takror-ochir") { d.vazifalar = d.vazifalar.filter((y) => !(y.nom === x.nom && y.takror && y.sana >= d.bugun)); return; }
      if (q[2] === "navbat") {
        const eski = x.odam_id;
        const juft = tana.usul === "almashtir" && d.vazifalar.filter((y) => y.nom === x.nom && y.odam_id === tana.odam_id && y.sana > x.sana).sort((a, b) => a.sana.localeCompare(b.sana))[0];
        x.odam_id = tana.odam_id;
        if (juft) juft.odam_id = eski;
        for (const y of d.vazifalar) {
          if (y.tur !== "ergash") continue;
          const o = d.vazifalar.find((z) => z.tur === "navbat" && z.sana === y.sana);
          if (o) y.odam_id = o.odam_id;
        }
        return;
      }
      if (q[2] === "shaxsiy") {
        let t = turNom(x.nom);
        if (!t) { t = { id: Math.max(...d.turlar.map((z) => z.id)) + 1, nom: x.nom, davomiylik: x.davomiylik, shaxsiy: false, navbat: false, haftalik: false, ergash: false, dars: false, qadamlar: [] }; d.turlar.push(t); }
        t.shaxsiy = tana.shaxsiy;
        for (const y of d.vazifalar) if (y.nom === t.nom) { y.shaxsiy = t.shaxsiy; y.tur_id = t.id; if (y.tur !== "dars") y.toifa = t.shaxsiy ? "shaxsiy" : "uy"; }
        return;
      }
    }
    if (yol === "tur") {
      if (d.turlar.some((t) => t.nom === tana.nom)) throw new Error(`«${tana.nom}» ro'yxatda bor`);
      d.turlar.push({ id: Math.max(...d.turlar.map((z) => z.id)) + 1, nom: tana.nom, davomiylik: tana.davomiylik, shaxsiy: tana.shaxsiy,
        navbat: false, haftalik: false, ergash: false, dars: false, qadamlar: [] });
      return;
    }
    if (q[0] === "tur") {
      const t = tur(Number(q[1]));
      if (!q[2]) return Object.assign(t, tana);
      if (q[2] === "ochir") { d.turlar = d.turlar.filter((z) => z !== t); return; }
      if (q[2] === "qadam") {
        if (t.qadamlar.some((z) => z.nom.toLowerCase() === tana.nom.toLowerCase())) throw new Error(`«${tana.nom}» bu ishda allaqachon bor`);
        t.qadamlar.push({ id: Date.now(), nom: tana.nom });
        return;
      }
    }
    if (q[0] === "qadam") for (const t of d.turlar) t.qadamlar = t.qadamlar.filter((z) => z.id !== Number(q[1]));
  }

  // ── Hodisalar ──────────────────────────────────────────────────────
  function bosildi(ev) {
    const t = ev.target.closest("button"); if (!t || t.disabled) return;
    const a = t.dataset.amal;
    if (a === "orqa") return orqa();
    if (a === "qayta") { xatoMatn = ""; chiz(); return yukla(); }
    if (!d) return;
    if (t.dataset.kim) { kim = /^\d+$/.test(t.dataset.kim) ? Number(t.dataset.kim) : t.dataset.kim; tebran("soft"); return chiz(); }
    if (t.dataset.vazifa) { const x = vazifa(Number(t.dataset.vazifa)); if (x) { tebran("soft"); oynaOch(vazifaForma(x)); } return; }
    if (t.dataset.tur) { const x = tur(Number(t.dataset.tur)); if (x) { tebran("soft"); oynaOch({ t: "tur", id: x.id, davomiylik: x.davomiylik, shaxsiy: x.shaxsiy, qadam: "", xato: "" }); } return; }
    if (a === "yangi") return oynaOch(yangiForma());
    if (a === "yangiTur") return oynaOch({ t: "tur", id: null, nom: "", davomiylik: 60, shaxsiy: false, xato: "" });
    if (a === "turlar") { stek.push({ t: "turlar" }); chiz(); el.scrollTop = 0; tebran("soft"); return; }
    if (a === "oldin" || a === "keyin" || a === "bugunga") {
      dan = a === "bugunga" ? null : kunQosh(d.dan, a === "keyin" ? KUN_SONI : -KUN_SONI);
      if (dan && dan <= d.bugun) dan = null;
      tebran("soft");
      if (NAMUNA) { d.dan = dan || d.bugun; d.gacha = kunQosh(d.dan, KUN_SONI - 1); return chiz(); }
      return yukla();
    }
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
  window.SozlamaBolimi.vazifalar = () => och();

  /** «#sozlamalar/vazifalar[/yangi|/v/<id>|/turlar[/yangi]|/tur/<id>]» → ochish. */
  function havola(xesh) {
    const m = String(xesh || "").match(/^#sozlamalar\/vazifalar(?:\/(yangi|turlar(?:\/yangi)?|v\/\d+|tur\/\d+))?\/?$/);
    if (!m) return false;
    if (document.getElementById("sahifa-sozlamalar")?.hidden) return false;
    const q = (m[1] || "").split("/");
    const turlarda = q[0] === "turlar" || q[0] === "tur";
    och(turlarda ? { t: "turlar" } : null, () => {
      if (q[0] === "yangi") oynaOch(yangiForma());
      else if (q[0] === "v") { const x = vazifa(Number(q[1])); if (x) oynaOch(vazifaForma(x)); else chiz(); }
      else if (q[1] === "yangi") oynaOch({ t: "tur", id: null, nom: "", davomiylik: 60, shaxsiy: false, xato: "" });
      else if (q[0] === "tur") { const x = tur(Number(q[1])); if (x) oynaOch({ t: "tur", id: x.id, davomiylik: x.davomiylik, shaxsiy: x.shaxsiy, qadam: "", xato: "" }); else chiz(); }
      else chiz();
    });
    return true;
  }
  // Sozlamalar moduli xeshni o‘zinikiga qaytarib yozadi — boshlang‘ich manzil
  // navigatsiya yozuvidan olinadi (u asl xeshni saqlaydi).
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
