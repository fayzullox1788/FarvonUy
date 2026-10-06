// «Sozlamalar → Mahsulotlar» — mahsulot katalogi (desktop «Kategoriyalar» varag'idagi
// mahsulot kartalari: sahifa_mahsulot.MahsulotSahifa + MahsulotDialog). index.html dagi
// umumiy yordamchilar ustida: api(), NAMUNA, INIT, xabar(), tebran(), e().
// API: worker/src/miniapp_sz_mahsulot.js (/app/api/mahsulot*). Qoidalar core/mahsulot.py:
// `faol=0` — rasxodda tanlanmaydi (katalogda «Nofaol» bo'lib ko'rinadi), «O'chirish» —
// ochirilgan=1 (eski rasxodlar joyida qoladi). Rasm faqat ko'rsatiladi (botga yuboriladi).
// Sahifa — Sozlamalar ustidagi to'liq ekran; manzil:
//   #sozlamalar/mahsulotlar · …/yangi · …/yangi/kategoriya · …/<id> · …/<id>/kategoriya ·
//   …/<id>/ochir · …/<id>/rasm   (skrinshot va to'g'ridan-to'g'ri havola uchun).
(() => {
  const ILOVA = location.protocol === "file:" ? "" : "/app/";
  const XESH = "#sozlamalar/mahsulotlar";
  const NB = " ";
  const fmt = (s) => String(Math.abs(Math.round(Number(s) || 0))).replace(/\B(?=(\d{3})+(?!\d))/g, NB);
  const OLCHOVLAR_B = ["dona", "kg", "gramm", "litr", "millilitr", "qadoq", "bog'", "metr", "juft"];
  const PASTEL = {
    food: "#fff0e6", life: "#e8f0ff", transportation: "#e3f5ec", shopping: "#f1ebff", health: "#ffebee",
    education: "#ebe9ff", entertainment: "#f0e9ff", personal: "#ffedf5", finance: "#e5f5ea",
    sports: "#e6f3ff", travel: "#e2f5f3", office: "#edf1f6", others: "#eff1f4",
  };
  const IK = {
    orqa: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 12h-15M10.5 5.5 4 12l6.5 6.5"/></svg>`,
    ong: `<svg class="ong" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="m9.5 5.5 6.5 6.5-6.5 6.5"/></svg>`,
    plyus: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>`,
    x: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>`,
    qidir: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/></svg>`,
    savat: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M10 11v6M14 11v6"/><path d="M5.5 7l1 12a2 2 0 0 0 2 1.8h7a2 2 0 0 0 2-1.8l1-12"/><path d="M9 7V4.8a.8.8 0 0 1 .8-.8h4.4a.8.8 0 0 1 .8.8V7"/></svg>`,
    yorliq: `<svg width="58%" height="58%" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="M3.5 12.2V4.5a1 1 0 0 1 1-1h7.7a1 1 0 0 1 .7.3l7.8 7.8a1 1 0 0 1 0 1.4l-7.7 7.7a1 1 0 0 1-1.4 0l-7.8-7.8a1 1 0 0 1-.3-.7Z"/><circle cx="8" cy="8" r="1.4"/></svg>`,
    ogoh: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5 2.5 20h19L12 3.5Z"/><path d="M12 10v4.5M12 17.5h.01"/></svg>`,
    kamera: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8.5a2 2 0 0 1 2-2h1.8l1.4-2h5.6l1.4 2H18a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z"/><circle cx="12" cy="12.6" r="3.4"/></svg>`,
    quti: `<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 8.5h17v10a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2v-10Z"/><path d="M3.5 8.5 5.5 4h13l2 4.5M12 4v4.5M9.5 12.5h5"/></svg>`,
  };

  // ── Holat ──────────────────────────────────────────────────────────
  let ochiq = false;
  let mahsulotlar = null;      // server qatorlari (mh.mahsulotlar tartibida)
  let daraxt = [];             // faol kategoriyalar daraxti
  let olchovlar = OLCHOVLAR_B;
  const tugun = new Map();     // id → {id, nom, rasm, ota_id, bolalar}
  let xatoMatn = "";
  let yuklanmoqda = false;
  let filtr = { ildiz: null, q: "" };
  let varaq = null;            // forma{…} | kat{forma, ildiz} | ochir{id} | rasm{id}
  let kutilgan = null;         // ma'lumot kelguncha ochilgan havola

  const guruh = (f) => (f || "").slice(0, (f || "").lastIndexOf("_"));
  function indeksla() {
    tugun.clear();
    const yur = (x) => { tugun.set(x.id, x); x.bolalar.forEach(yur); };
    daraxt.forEach(yur);
  }
  /** Daraxt tartibida tekis ro'yxat: [tugun, chuqurlik] (mh.tekis). */
  function tekis(royxat = daraxt, chuq = 0, natija = []) {
    for (const t of royxat) { natija.push([t, chuq]); tekis(t.bolalar, chuq + 1, natija); }
    return natija;
  }
  function avlodlar(id) {
    const s = new Set();
    const yur = (x) => { s.add(x.id); x.bolalar.forEach(yur); };
    if (tugun.has(id)) yur(tugun.get(id));
    return s;
  }
  function ildizi(id) {
    let x = tugun.get(id);
    while (x && x.ota_id != null && tugun.has(x.ota_id)) x = tugun.get(x.ota_id);
    return x ? x.id : null;
  }
  function yolNomi(id) {
    const q = [];
    for (let x = tugun.get(id); x; x = x.ota_id != null ? tugun.get(x.ota_id) : null) q.unshift(x.nom);
    return q.join(" › ");
  }

  /** Kategoriya ikonkasi — belgilar/<turi.rasm stem>.svg, yo'q bo'lsa neytral. */
  function belgi(rasm, cls = "sz-belgi") {
    if (!rasm) return `<span class="${cls}">${IK.yorliq}</span>`;
    const kalit = rasm.replace(/\.[a-z]+$/i, "");
    return `<span class="${cls}" style="background:${PASTEL[guruh(rasm)] || "#eef1f6"}"><img src="${ILOVA}belgilar/${e(kalit)}.svg" alt="" decoding="async" onerror="this.remove()"></span>`;
  }

  // ── Namuna (file://) ───────────────────────────────────────────────
  function namunaRasm(a, b, shakl) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80"><defs><radialGradient id="g" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></radialGradient><linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f6efe4"/><stop offset="1" stop-color="#e4d6c1"/></linearGradient></defs><rect width="80" height="80" fill="url(#f)"/>${shakl.replace(/F/g, "url(#g)")}</svg>`;
    return "data:image/svg+xml," + encodeURIComponent(svg);
  }
  const NAMUNA_RASM = {
    "k.jpg": namunaRasm("#ffffff", "#cfd9e6", `<rect x="27" y="14" width="26" height="54" rx="7" fill="F"/><rect x="30" y="8" width="20" height="9" rx="3" fill="#2f6ff5"/><rect x="27" y="34" width="26" height="16" fill="#2f6ff5" opacity=".85"/>`),
    "b.jpg": namunaRasm("#ffe680", "#e7b416", `<path d="M14 30c10 30 42 38 56 18-6 4-30 4-46-22Z" fill="F"/><path d="M18 34c12 22 36 26 48 14" stroke="#b88a0a" stroke-width="2" fill="none"/>`),
    "o.jpg": namunaRasm("#ff8a7a", "#c81e1e", `<circle cx="40" cy="45" r="22" fill="F"/><path d="M40 24c0-6 3-10 7-12" stroke="#6b4b1f" stroke-width="3" fill="none" stroke-linecap="round"/><ellipse cx="50" cy="16" rx="7" ry="3.5" fill="#3fa34d" transform="rotate(-25 50 16)"/>`),
    "n.jpg": namunaRasm("#f3c27b", "#b9762a", `<ellipse cx="40" cy="46" rx="28" ry="17" fill="F"/><path d="M24 40l6 6M34 37l6 6M44 37l6 6M54 40l-4 5" stroke="#8a5418" stroke-width="2.2" stroke-linecap="round"/>`),
  };
  function namunaMa() {
    let id = 1;
    const t = (nom, rasm, bolalar = []) => ({ id: 0, nom, rasm, ota_id: null, bolalar });
    const d = [
      t("Oziq-ovqat", "food_17.png", [
        t("Meva-sabzavot", "food_10.png", [t("Mevalar", "food_11.png"), t("Sabzavotlar", "personal_10.png")]),
        t("Sut va sut mahsulotlari", "food_08.png"),
        t("Go‘sht mahsulotlari", "food_27.png"),
        t("Non va un mahsulotlari", "food_01.png")]),
      t("Maishiy tovarlar", "life_08.png", [t("Gigiena", "life_03.png"), t("Tozalash", "life_16.png")]),
      t("Sog‘liq", "health_11.png", [t("Dorilar", "health_01.png")]),
    ];
    const ota = (x, o) => { x.id = id++; x.ota_id = o; x.bolalar.forEach((c) => ota(c, x.id)); };
    d.forEach((x) => ota(x, null));
    daraxt = d; indeksla();
    const kat = (nom) => [...tugun.values()].find((x) => x.nom === nom).id;
    let iid = 100;
    const m = (nom, k, narx, o = {}) => {
      const r = { id: iid++, nom, turi_id: kat(k), narx, miqdor: null, olchov: null, ogirlik: null, litr: null,
        izoh: null, faol: 1, rasm: null, ...o };
      r.kategoriya = yolNomi(r.turi_id);
      return r;
    };
    const qatorlar = [
      m("Banan", "Mevalar", 24000, { miqdor: 1, olchov: "kg", rasm: "b.jpg" }),
      m("Olma", "Mevalar", 18000, { miqdor: 1, olchov: "kg", rasm: "o.jpg", izoh: "Qizil, Namangan" }),
      m("Kartoshka", "Sabzavotlar", 6000, { miqdor: 1, olchov: "kg" }),
      m("Kefir", "Sut va sut mahsulotlari", 11000, { litr: 1, rasm: "k.jpg", izoh: "Nestle" }),
      m("Qatiq", "Sut va sut mahsulotlari", 9000, { miqdor: 0.5, olchov: "litr" }),
      m("Tvorog", "Sut va sut mahsulotlari", 32000, { ogirlik: 0.5, faol: 0 }),
      m("Mol go‘shti", "Go‘sht mahsulotlari", 110000, { miqdor: 1, olchov: "kg" }),
      m("Non", "Non va un mahsulotlari", 4000, { miqdor: 1, olchov: "dona", rasm: "n.jpg" }),
      m("Sovun", "Gigiena", 6500, { ogirlik: 0.15, izoh: "Dove" }),
      m("Tish pastasi", "Gigiena", 15000, { miqdor: 1, olchov: "dona" }),
      m("Kir yuvish kukuni", "Tozalash", 42000, { ogirlik: 3, faol: 0 }),
      m("Paratsetamol", "Dorilar", 8000, { miqdor: 1, olchov: "qadoq" }),
    ];
    return qatorlar.map(tavsifla).sort(tartib);
  }
  const tartib = (a, b) => (b.faol - a.faol) || a.nom.toLowerCase().localeCompare(b.nom.toLowerCase());
  /** Namuna/oldindan ko'rish uchun mh.tavsif (server o'zi hisoblaydi). */
  function tavsifla(r) {
    const son = (x) => String(Number(x)).replace(".", ",");
    const q = [];
    if (r.miqdor != null) q.push(`${son(r.miqdor)} ${r.olchov || ""}`.trim());
    else if (r.olchov) q.push(r.olchov);
    if (r.ogirlik != null) q.push(`${son(r.ogirlik)} kg`);
    if (r.litr != null) q.push(`${son(r.litr)} l`);
    r.olcham = q.join(" · ");
    return r;
  }

  // ── Ma'lumot ───────────────────────────────────────────────────────
  function qabul(j) {
    mahsulotlar = j.mahsulotlar; daraxt = j.daraxt || []; olchovlar = j.olchovlar || OLCHOVLAR_B;
    indeksla();
    if (filtr.ildiz != null && !tugun.has(filtr.ildiz)) filtr.ildiz = null;
  }
  async function yukla() {
    if (yuklanmoqda) return;
    if (NAMUNA) { if (!mahsulotlar) mahsulotlar = namunaMa(); return tayyor(); }
    if (!INIT) { xatoMatn = "Bu sahifani Telegram'dagi Farovon Hayot botidan oching."; return tayyor(); }
    yuklanmoqda = true;
    try { qabul(await api("mahsulot")); xatoMatn = ""; } catch (err) { xatoMatn = err.message; }
    yuklanmoqda = false;
    tayyor();
  }
  function tayyor() {
    if (kutilgan != null && mahsulotlar) { const h = kutilgan; kutilgan = null; return xeshniOch(h); }
    chiz();
  }

  // ── Rasm: Authorization bilan fetch → blob URL (img sarlavha yubora olmaydi) ──
  const rasmKesh = new Map();  // item.rasm (mazmun xeshi nomi) → blob URL | null
  const navbat = [];
  let faol = 0;
  function rasmOl(r) {
    if (!r.rasm) return Promise.resolve(null);
    if (NAMUNA) return Promise.resolve(NAMUNA_RASM[r.rasm] || null);
    const k = rasmKesh.get(r.rasm);
    if (k !== undefined) return Promise.resolve(k);
    return new Promise((ok) => { navbat.push([r, ok]); ishlat(); });
  }
  function ishlat() {
    while (faol < 4 && navbat.length) {
      const [r, ok] = navbat.shift();
      if (rasmKesh.has(r.rasm)) { ok(rasmKesh.get(r.rasm)); continue; }
      faol++;
      fetch(`/app/api/mahsulot/${r.id}/rasm`, { headers: { authorization: "tma " + INIT } })
        .then((j) => (j.ok ? j.blob() : null))
        .then((b) => { const u = b && b.size ? URL.createObjectURL(b) : null; rasmKesh.set(r.rasm, u); ok(u); })
        .catch(() => ok(null))
        .finally(() => { faol--; ishlat(); });
    }
  }
  let kuzatuvchi = null;
  function rasmlarniKuzat() {
    const imgs = P().querySelectorAll(".szm-rasm[data-id]:not(.tayyor)");
    if (!imgs.length) return;
    if (!kuzatuvchi && "IntersectionObserver" in window) {
      kuzatuvchi = new IntersectionObserver((ent) => ent.forEach((x) => {
        if (x.isIntersecting) { kuzatuvchi.unobserve(x.target); rasmQoy(x.target); }
      }), { root: P(), rootMargin: "200px" });
    }
    imgs.forEach((el) => (kuzatuvchi ? kuzatuvchi.observe(el) : rasmQoy(el)));
  }
  function rasmQoy(el) {
    const r = mahsulotlar && mahsulotlar.find((x) => x.id === Number(el.dataset.id));
    if (!r) return;
    rasmOl(r).then((u) => {
      if (!u || !el.isConnected) return;
      const img = new Image();
      img.alt = ""; img.decoding = "async";
      img.onload = () => el.classList.add("tayyor");
      img.src = u;
      el.appendChild(img);
    });
  }
  /** Mahsulot kichik rasmi: rasm kelguncha (yoki rasmsiz) — kategoriya ikonkasi. */
  function kichikRasm(r, cls = "szm-kichik") {
    const kat = tugun.get(r.turi_id);
    return `<span class="${cls}">${belgi(kat && kat.rasm, "sz-belgi")}${r.rasm ? `<span class="szm-rasm" data-id="${r.id}"></span>` : ""}</span>`;
  }

  // ── Sahifa elementi ────────────────────────────────────────────────
  let sahifa = null;
  const P = () => sahifa;
  function sahifaEl() {
    if (sahifa) return;
    sahifa = document.createElement("div");
    sahifa.className = "szm-sahifa";
    sahifa.hidden = true;
    const bosh = document.querySelector(".ilova > header.bosh");
    sahifa.innerHTML = `${bosh ? bosh.outerHTML : ""}<div class="varaq szm-varaq" id="szmVaraq"></div>`;
    (document.querySelector(".ilova") || document.body).appendChild(sahifa);
    sahifa.addEventListener("click", bosildi);
    sahifa.addEventListener("input", (ev) => {
      if (ev.target.id !== "szmQidir") return;
      filtr.q = ev.target.value;
      const ro = document.getElementById("szmRoyxat");
      if (ro) { ro.innerHTML = royxatHtml(); rasmlarniKuzat(); }
    });
  }

  // ── Chizish ────────────────────────────────────────────────────────
  function chiz() {
    if (!ochiq) return;
    sahifaEl();
    const v = document.getElementById("szmVaraq");
    const q = filtr.q;
    v.innerHTML = `<div class="sz-bosh ichki"><button class="sz-orqa" data-amal="orqa" aria-label="Orqaga">${IK.orqa}</button><h1>Mahsulotlar</h1></div>
      <div style="margin-top:14px"><button class="sz-kok-tugma" data-amal="yangi">${IK.plyus}Mahsulot qo‘shish</button></div>
      <label class="sz-qidir szm-qidir">${IK.qidir}<input id="szmQidir" type="search" placeholder="Mahsulot qidirish…" autocomplete="off" value="${e(q)}"></label>
      ${mahsulotlar && daraxt.length ? `<div class="sz-chiplar szm-chiplar">${[[null, "Hammasi"], ...daraxt.map((x) => [x.id, x.nom])].map(([id, nom]) =>
        `<button class="sz-chip${id === filtr.ildiz ? " faol" : ""}" data-ildiz="${id ?? ""}">${e(nom)}</button>`).join("")}</div>` : ""}
      <div id="szmRoyxat">${royxatHtml()}</div>`;
    rasmlarniKuzat();
    oynaChiz();
    xeshYoz();
    tgOrqa();
  }

  function korinadiganlar() {
    const q = filtr.q.trim().toLowerCase();
    const ichida = filtr.ildiz != null ? avlodlar(filtr.ildiz) : null;
    return mahsulotlar.filter((r) => (!ichida || ichida.has(r.turi_id)) &&
      (!q || (r.nom || "").toLowerCase().includes(q) || (r.izoh || "").toLowerCase().includes(q)));
  }

  function royxatHtml() {
    if (xatoMatn) return `<div class="sz-royxat"><div class="sz-bosh-holat">${e(xatoMatn)}<br><button data-amal="qayta">Qayta urinish</button></div></div>`;
    if (!mahsulotlar) return `<div class="szm-joy szm-skelet-joy"></div><div class="sz-royxat">${"<div class=\"sz-skelet szm-skelet\"></div>".repeat(6)}</div>`;
    const royxat = korinadiganlar();
    const kat = filtr.ildiz != null ? yolNomi(filtr.ildiz) : "Hammasi";
    const joy = `<div class="szm-joy">${e(kat)} · ${royxat.length} ta mahsulot</div>`;
    if (!royxat.length) {
      const q = filtr.q.trim();
      return `${joy}<div class="sz-royxat"><div class="sz-bosh-holat szm-bosh">${IK.quti}<div>${q
        ? `«${e(q)}» bo‘yicha mahsulot topilmadi.`
        : "Bu kategoriyada hali mahsulot yo‘q."}</div>${q ? "" : `<button data-amal="yangi">+ Mahsulot qo‘shish</button>`}</div></div>`;
    }
    // Guruhlar — kategoriya daraxti tartibida; nofaol/yo'q kategoriyalilar oxirida.
    const tartibi = new Map(tekis().map(([t], i) => [t.id, i]));
    const guruhlar = new Map();
    for (const r of royxat) {
      const k = tugun.has(r.turi_id) ? r.turi_id : "x:" + (r.kategoriya || "");
      if (!guruhlar.has(k)) guruhlar.set(k, []);
      guruhlar.get(k).push(r);
    }
    const kalitlar = [...guruhlar.keys()].sort((a, b) =>
      (tartibi.get(a) ?? 1e9) - (tartibi.get(b) ?? 1e9) || String(a).localeCompare(String(b)));
    return joy + kalitlar.map((k) => {
      const qat = guruhlar.get(k);
      const t = tugun.get(k);
      const yol = t ? yolNomi(t.id) : (qat[0].kategoriya || "Kategoriyasiz");
      const bolak = yol.split(" › ");
      const oxiri = bolak.pop();
      return `<div class="szm-guruh">${belgi(t && t.rasm, "sz-belgi szm-gb")}<span class="nom"><b>${e(oxiri)}</b>${bolak.length ? `<span class="ota"> · ${e(bolak.join(" › "))}</span>` : ""}</span><span class="son">${qat.length}</span></div>
        <div class="sz-royxat szm-royxat">${qat.map(qatorHtml).join("")}</div>`;
    }).join("");
  }

  function qatorHtml(r) {
    const narx = r.narx ? `${fmt(r.narx)}${NB}UZS` : "—";
    return `<button class="szm-q${r.faol ? "" : " nofaol"}" data-id="${r.id}">${kichikRasm(r)}
      <span class="szm-matn"><span class="szm-nom"><span class="t">${e(r.nom)}</span>${r.faol ? "" : `<span class="szm-nishon">Nofaol</span>`}</span>
        ${r.olcham || r.izoh ? `<span class="szm-ost">${e([r.olcham, r.izoh].filter(Boolean).join(" · "))}</span>` : ""}</span>
      <span class="szm-narx${r.narx ? "" : " yoq"}">${narx}</span></button>`;
  }

  // ── Pastdan chiqadigan oyna ────────────────────────────────────────
  let parda, oyna;
  function oynaEl() {
    if (oyna) return;
    parda = document.createElement("div"); parda.className = "sz-parda";
    oyna = document.createElement("div"); oyna.className = "sz-oyna szm-oyna"; oyna.setAttribute("role", "dialog");
    document.body.append(parda, oyna);
    parda.onclick = () => yop();
    oyna.addEventListener("click", oynaBosildi);
    oyna.addEventListener("input", oynaKiritildi);
    oyna.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && ev.target.matches("input.sz-kirit")) { ev.preventDefault(); saqla(); }
    });
  }
  const sarlavha = (matn, orqa = false) => `<div class="sz-oyna-bosh">${orqa
    ? `<button class="sz-orqa szm-oyna-orqa" data-amal="formaga" aria-label="Orqaga">${IK.orqa}</button>` : ""}<h3>${matn}</h3><button class="sz-yop" data-amal="yop" aria-label="Yopish">${IK.x}</button></div>`;

  function oynaChiz() {
    oynaEl();
    const och = !!varaq && ochiq;
    parda.classList.toggle("ochiq", och);
    oyna.classList.toggle("ochiq", och);
    oyna.classList.toggle("szm-rasm-oyna", och && varaq.t === "rasm");
    if (!och) return;
    const t = varaq.t;
    const html = t === "forma" ? formaHtml(varaq) : t === "kat" ? katHtml(varaq) : t === "ochir" ? ochirHtml(varaq) : rasmHtml(varaq);
    oyna.innerHTML = html;
    oyna.querySelectorAll(".szm-rasm[data-id]").forEach(rasmQoy);
  }

  const sonMatn = (x) => (x == null || x === "" ? "" : String(x).replace(".", ","));
  function yangiForma() {
    const ildiz = filtr.ildiz;
    return { t: "forma", id: null, nom: "", turi_id: ildiz, narx: "", miqdor: "", olchov: "", ogirlik: "", litr: "",
      izoh: "", faol: true, xato: "", band: false };
  }
  function tahrirForma(id) {
    const r = mahsulotlar.find((x) => x.id === id);
    if (!r) return null;
    const f = { t: "forma", id, nom: r.nom, turi_id: r.turi_id, narx: r.narx ? fmt(r.narx) : "", miqdor: sonMatn(r.miqdor),
      olchov: r.olchov || "", ogirlik: sonMatn(r.ogirlik), litr: sonMatn(r.litr), izoh: r.izoh || "", faol: !!r.faol,
      xato: "", band: false };
    f.asl = JSON.stringify(formaQiymat(f));
    return f;
  }

  function formaHtml(f) {
    const r = f.id != null ? mahsulotlar.find((x) => x.id === f.id) : null;
    const kat = tugun.get(f.turi_id);
    const yolsiz = f.turi_id != null && !kat; // kategoriyasi nofaol bo'lib qolgan
    const ol = (f.olchov || "").trim();
    return `${sarlavha(r ? "Mahsulotni tahrirlash" : "Yangi mahsulot")}
      ${r ? `<div class="szm-rasm-qator">${r.rasm
        ? `<button class="szm-katta" data-amal="rasmKor" aria-label="Rasmni ko‘rish">${kichikRasm(r, "szm-katta-ich")}</button>`
        : `<span class="szm-katta bosh">${IK.kamera}<small>Rasm yo‘q</small></span>`}
        <span class="szm-tel">Rasm qo‘shish uchun uni Telegram botga shaxsiy yuboring, izohiga mahsulot nomini aynan yozing — bir daqiqada shu yerda paydo bo‘ladi.</span></div>` : ""}
      <label class="sz-yorliq" for="szmNom">Nomi *</label>
      <input class="sz-kirit" id="szmNom" data-m="nom" maxlength="80" autocomplete="off" placeholder="masalan: Olma" value="${e(f.nom)}">
      <div class="sz-yorliq">Kategoriya *</div>
      <button class="sz-boshqa szm-kat-tanla${kat ? "" : " bosh"}" data-amal="katTanla">${kat ? belgi(kat.rasm) : `<span class="sz-belgi">${IK.yorliq}</span>`}
        <span>${kat ? `${ildizi(kat.id) !== kat.id ? `<small>${e(yolNomi(kat.ota_id))} ›</small>` : ""}${e(kat.nom)}` : yolsiz ? "Kategoriya endi yo‘q — boshqasini tanlang" : "Kategoriyani tanlang"}</span>${IK.ong}</button>
      <label class="sz-yorliq" for="szmNarx">Narxi</label>
      <label class="szm-pul"><input id="szmNarx" data-m="narx" class="sz-kirit" inputmode="numeric" autocomplete="off" placeholder="0" value="${e(f.narx)}"><span>UZS</span></label>
      <div class="sz-yorliq">Miqdori / hajmi</div>
      <div class="szm-ikki">
        <input class="sz-kirit" id="szmMiqdor" data-m="miqdor" inputmode="decimal" autocomplete="off" placeholder="masalan: 1" value="${e(f.miqdor)}">
        <input class="sz-kirit" id="szmOlchov" data-m="olchov" maxlength="30" autocomplete="off" placeholder="o‘lchov" value="${e(f.olchov)}">
      </div>
      <div class="sz-chiplar szm-olchovlar">${olchovlar.map((o) =>
        `<button class="sz-chip${o === ol ? " faol" : ""}" data-olchov="${e(o)}">${e(o)}</button>`).join("")}</div>
      <div class="szm-ikki szm-ikki-yorliq">
        <label class="sz-yorliq" for="szmOgirlik">Og‘irligi (kg)</label><label class="sz-yorliq" for="szmLitr">Litri</label>
      </div>
      <div class="szm-ikki">
        <input class="sz-kirit" id="szmOgirlik" data-m="ogirlik" inputmode="decimal" autocomplete="off" placeholder="masalan: 0,5" value="${e(f.ogirlik)}">
        <input class="sz-kirit" id="szmLitr" data-m="litr" inputmode="decimal" autocomplete="off" placeholder="masalan: 1,5" value="${e(f.litr)}">
      </div>
      <label class="sz-yorliq" for="szmIzoh">Izoh</label>
      <input class="sz-kirit" id="szmIzoh" data-m="izoh" maxlength="200" autocomplete="off" value="${e(f.izoh)}">
      <button class="szm-faol" data-amal="faol" role="switch" aria-checked="${f.faol}">
        <span><b>Faol</b><small>${f.faol ? "Rasxod yozishda tanlanadi" : "Rasxod yozishda tanlanmaydi — katalogda qoladi"}</small></span>
        <span class="szm-tugmacha${f.faol ? " yoq" : ""}"></span></button>
      ${f.xato ? `<div class="sz-ogoh">${IK.ogoh}<span>${e(f.xato)}</span></div>` : ""}
      <button class="sz-kok-tugma" data-amal="saqla"${f.band ? " disabled" : ""}>${r ? "Saqlash" : "Qo‘shish"}</button>
      ${r ? `<button class="szm-ochir" data-amal="ochir">${IK.savat}Mahsulotni o‘chirish</button>` : ""}`;
  }

  /** Kategoriya tanlash — ikki bosqich (desktop KategoriyaTanla): katta, keyin ichkisi. */
  function katHtml(v) {
    const f = v.forma;
    if (v.ildiz == null) {
      const joriyIldiz = ildizi(f.turi_id);
      return `${sarlavha("Kategoriya", true)}
        <div class="sz-royxat szm-tanla">${daraxt.map((x) => `<button class="sz-q${x.id === joriyIldiz ? " tanlangan" : ""}" data-ildiz-tanla="${x.id}">${belgi(x.rasm)}
          <span class="nom">${e(x.nom)}</span>${x.bolalar.length ? `<span class="son">${tekis(x.bolalar).length}</span>${IK.ong}` : (x.id === f.turi_id ? TANLANDI : "")}</button>`).join("")}</div>`;
    }
    const x = tugun.get(v.ildiz);
    if (!x) return sarlavha("Kategoriya topilmadi", true);
    return `${sarlavha(e(x.nom), true)}
      <div class="sz-royxat szm-tanla">
        <button class="sz-q" data-kat-tanla="${x.id}">${belgi(x.rasm)}<span class="nom szm-ozi">— ichki kategoriyasiz —</span>${x.id === f.turi_id ? TANLANDI : ""}</button>
        ${tekis(x.bolalar, 1).map(([t, c]) => `<button class="sz-q" data-kat-tanla="${t.id}" style="padding-left:${10 + (c - 1) * 22}px">${belgi(t.rasm)}
          <span class="nom">${e(t.nom)}</span>${t.id === f.turi_id ? TANLANDI : ""}</button>`).join("")}
      </div>`;
  }
  const TANLANDI = `<svg class="szm-belgilandi" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>`;

  function ochirHtml(v) {
    const r = mahsulotlar.find((x) => x.id === v.id);
    if (!r) return sarlavha("Mahsulot topilmadi");
    return `${sarlavha("Mahsulotni o‘chirish")}
      <p class="sz-matn"><b>«${e(r.nom)}»</b> o‘chirilsinmi? Unga bog‘langan eski rasxodlar o‘zgarmaydi.</p>
      ${v.xato ? `<div class="sz-ogoh">${IK.ogoh}<span>${e(v.xato)}</span></div>` : ""}
      <div class="sz-ikki"><button class="sz-kulrang-tugma" data-amal="formaga">Bekor qilish</button>
        <button class="sz-qizil-tugma" data-amal="ochirTasdiq"${v.band ? " disabled" : ""}>O‘chirish</button></div>`;
  }

  function rasmHtml(v) {
    const r = mahsulotlar.find((x) => x.id === v.id);
    if (!r || !r.rasm) return sarlavha("Rasm yo‘q");
    return `${sarlavha(e(r.nom), true)}<div class="szm-rasm-katta">${kichikRasm(r, "szm-rasm-ich")}</div>
      ${r.kategoriya || r.olcham ? `<p class="szm-rasm-izoh">${e([r.kategoriya, tavsifMatn(r)].filter(Boolean).join(" · "))}</p>` : ""}`;
  }
  const tavsifMatn = (r) => [r.olcham, r.narx ? `${fmt(r.narx)}${NB}UZS` : ""].filter(Boolean).join(" · ");

  // ── Forma qiymatlari ───────────────────────────────────────────────
  function formaniOl() {
    const f = varaq && (varaq.t === "forma" ? varaq : varaq.forma);
    if (!f || varaq.t !== "forma") return f;
    oyna.querySelectorAll("[data-m]").forEach((el) => { f[el.dataset.m] = el.value; });
    return f;
  }
  function formaQiymat(f) {
    const narx = String(f.narx || "").replace(/[\s ]/g, "");
    return { nom: f.nom, turi_id: f.turi_id, narx: narx === "" ? 0 : narx, miqdor: f.miqdor, olchov: f.olchov,
      ogirlik: f.ogirlik, litr: f.litr, izoh: f.izoh, faol: !!f.faol };
  }

  // ── Hodisalar ──────────────────────────────────────────────────────
  function och(yangi) { varaq = yangi; oynaChiz(); xeshYoz(); tgOrqa(); }
  function yop() { varaq = null; oynaChiz(); xeshYoz(); tgOrqa(); }
  function orqa() {
    if (varaq) {
      if (varaq.t === "kat" && varaq.ildiz != null) { varaq.ildiz = null; return och(varaq); }
      if (varaq.t === "kat" || ((varaq.t === "ochir" || varaq.t === "rasm") && varaq.forma)) return och(varaq.forma);
      return yop();
    }
    sahifaniYop();
  }

  function bosildi(ev) {
    const t = ev.target.closest("button"); if (!t) return;
    if (t.dataset.id && t.classList.contains("szm-q")) {
      const f = tahrirForma(Number(t.dataset.id));
      if (f) { tebran("soft"); och(f); }
      return;
    }
    if (t.dataset.ildiz !== undefined) {
      filtr.ildiz = t.dataset.ildiz === "" ? null : Number(t.dataset.ildiz);
      tebran("soft");
      document.querySelectorAll(".szm-chiplar .sz-chip").forEach((c) => c.classList.toggle("faol", c === t));
      const ro = document.getElementById("szmRoyxat");
      if (ro) { ro.innerHTML = royxatHtml(); rasmlarniKuzat(); }
      return;
    }
    const a = t.dataset.amal;
    if (a === "orqa") return orqa();
    if (a === "qayta") { xatoMatn = ""; chiz(); return yukla(); }
    if (a === "yangi") {
      if (!mahsulotlar) return;
      och(yangiForma());
      setTimeout(() => document.getElementById("szmNom")?.focus(), 260);
    }
  }

  function oynaBosildi(ev) {
    const t = ev.target.closest("button"); if (!t) return;
    if (t.dataset.olchov !== undefined) {
      const f = formaniOl();
      f.olchov = (f.olchov || "").trim() === t.dataset.olchov ? "" : t.dataset.olchov;
      const inp = document.getElementById("szmOlchov"); if (inp) inp.value = f.olchov;
      oyna.querySelectorAll(".szm-olchovlar .sz-chip").forEach((c) => c.classList.toggle("faol", c.dataset.olchov === f.olchov));
      return;
    }
    if (t.dataset.ildizTanla) {
      const x = tugun.get(Number(t.dataset.ildizTanla));
      if (!x) return;
      if (!x.bolalar.length) { varaq.forma.turi_id = x.id; varaq.forma.xato = ""; tebran("soft"); return och(varaq.forma); }
      varaq.ildiz = x.id; return och(varaq);
    }
    if (t.dataset.katTanla) {
      varaq.forma.turi_id = Number(t.dataset.katTanla); varaq.forma.xato = ""; tebran("soft");
      return och(varaq.forma);
    }
    const a = t.dataset.amal;
    if (a === "yop") return yop();
    if (a === "formaga") return orqa();
    if (a === "katTanla") { const f = formaniOl(); return och({ t: "kat", forma: f, ildiz: null }); }
    if (a === "faol") {
      const f = formaniOl(); f.faol = !f.faol;
      t.setAttribute("aria-checked", String(f.faol));
      t.querySelector(".szm-tugmacha").classList.toggle("yoq", f.faol);
      t.querySelector("small").textContent = f.faol ? "Rasxod yozishda tanlanadi" : "Rasxod yozishda tanlanmaydi — katalogda qoladi";
      return tebran("soft");
    }
    if (a === "saqla") return saqla();
    if (a === "ochir") { const f = formaniOl(); return och({ t: "ochir", id: f.id, forma: f }); }
    if (a === "ochirTasdiq") return ochir();
    if (a === "rasmKor") { const f = formaniOl(); return och({ t: "rasm", id: f.id, forma: f }); }
  }

  function oynaKiritildi(ev) {
    const el = ev.target;
    if (el.id === "szmNarx") {
      // PulEdit kabi: faqat raqam, minglik bo'lak bilan
      const raqam = el.value.replace(/\D/g, "").replace(/^0+(?=\d)/, "").slice(0, 13);
      const yangi = raqam ? fmt(raqam) : "";
      if (el.value !== yangi) {
        const oxirdan = el.value.length - (el.selectionEnd ?? el.value.length);
        el.value = yangi;
        const joy = Math.max(0, yangi.length - oxirdan);
        try { el.setSelectionRange(joy, joy); } catch (err) {}
      }
    }
    if (el.id === "szmOlchov") {
      const v = el.value.trim();
      oyna.querySelectorAll(".szm-olchovlar .sz-chip").forEach((c) => c.classList.toggle("faol", c.dataset.olchov === v));
    }
    const f = varaq && varaq.t === "forma" ? varaq : null;
    if (f && f.xato) { f.xato = ""; oyna.querySelector(".sz-ogoh")?.remove(); }
  }

  async function saqla() {
    const f = formaniOl();
    if (!f || f.band || varaq.t !== "forma") return;
    const q = formaQiymat(f);
    // Oldindan tekshiruv (server baribir mh.saqla qoidasi bilan tekshiradi)
    if (!q.nom.trim()) return xatoQoy(f, "Mahsulot nomi yozilmagan");
    if (q.turi_id == null || !tugun.has(q.turi_id)) {
      return xatoQoy(f, q.turi_id == null ? "Kategoriya tanlanmagan" : "Bu kategoriya endi yo'q — boshqasini tanlang");
    }
    if (f.id != null && f.asl === JSON.stringify(q)) { yop(); return xabar("O‘zgarish yo‘q"); }
    if (NAMUNA) return namunaYoz(f, q);
    f.band = true; oynaChiz();
    try {
      const j = await api(f.id != null ? `mahsulot/${f.id}` : "mahsulot", q);
      qabul(j);
      tebran("medium");
      varaq = null; chiz();
      xabar(f.id != null ? "✔ O‘zgarishlar saqlandi" : `✔ «${q.nom.trim()}» qo‘shildi`);
    } catch (err) {
      f.band = false; xatoQoy(f, err.message);
    }
  }
  function xatoQoy(f, m) {
    f.xato = m; f.band = false;
    try { tg && tg.HapticFeedback.notificationOccurred("error"); } catch (err) {}
    oynaChiz();
  }
  async function ochir() {
    const v = varaq;
    if (!v || v.t !== "ochir" || v.band) return;
    const r = mahsulotlar.find((x) => x.id === v.id);
    if (NAMUNA) {
      mahsulotlar = mahsulotlar.filter((x) => x.id !== v.id);
      varaq = null; chiz(); return xabar(`✔ «${r ? r.nom : ""}» o‘chirildi`);
    }
    v.band = true; oynaChiz();
    try {
      qabul(await api(`mahsulot/${v.id}/ochir`, {}));
      tebran("medium");
      varaq = null; chiz();
      xabar(`✔ «${r ? r.nom : ""}» o‘chirildi`);
    } catch (err) {
      v.band = false; v.xato = err.message; oynaChiz();
    }
  }
  function namunaYoz(f, q) {
    const son = (x) => { const s = String(x ?? "").trim().replace(",", ".").replace(/ /g, ""); return s === "" ? null : Number(s); };
    for (const [k, nom] of [["miqdor", "Miqdor"], ["ogirlik", "Og'irlik"], ["litr", "Litr"]]) {
      const v = son(q[k]);
      if (v != null && Number.isNaN(v)) return xatoQoy(f, `${nom} son bo'lishi kerak`);
      if (v != null && v < 0) return xatoQoy(f, `${nom} manfiy bo'lmasin`);
    }
    const r = { id: f.id ?? Math.max(0, ...mahsulotlar.map((x) => x.id)) + 1, nom: q.nom.trim(), turi_id: q.turi_id,
      narx: Number(q.narx) || 0, miqdor: son(q.miqdor), olchov: q.olchov.trim() || null, ogirlik: son(q.ogirlik),
      litr: son(q.litr), izoh: q.izoh.trim() || null, faol: q.faol ? 1 : 0,
      rasm: f.id != null ? (mahsulotlar.find((x) => x.id === f.id) || {}).rasm || null : null };
    r.kategoriya = yolNomi(r.turi_id);
    mahsulotlar = [...mahsulotlar.filter((x) => x.id !== r.id), tavsifla(r)].sort(tartib);
    varaq = null; chiz();
    xabar(f.id != null ? "✔ O‘zgarishlar saqlandi" : `✔ «${r.nom}» qo‘shildi`);
  }

  // ── Ochish / yopish va manzil ──────────────────────────────────────
  function sahifaniOch() {
    sahifaEl();
    ochiq = true;
    sahifa.hidden = false;
    sahifa.scrollTop = 0;
    document.documentElement.classList.add("szm-ochiq");
    chiz();
    if (!mahsulotlar || !NAMUNA) yukla();
  }
  function sahifaniYop({ xesh = true } = {}) {
    if (!ochiq) return;
    ochiq = false; varaq = null;
    oynaChiz();
    if (sahifa) sahifa.hidden = true;
    document.documentElement.classList.remove("szm-ochiq");
    if (xesh && location.hash.startsWith(XESH)) { try { history.replaceState(null, "", "#sozlamalar"); } catch (err) {} }
    tgOrqa();
  }

  function joriyXesh() {
    let h = XESH;
    if (varaq) {
      const f = varaq.t === "forma" ? varaq : varaq.forma;
      if (f) h += "/" + (f.id != null ? f.id : "yangi");
      if (varaq.t === "kat") h += "/kategoriya";
      if (varaq.t === "ochir") h += (varaq.forma ? "" : "/" + varaq.id) + "/ochir";
      if (varaq.t === "rasm") h += (varaq.forma ? "" : "/" + varaq.id) + "/rasm";
    }
    return h;
  }
  function xeshYoz() {
    if (!ochiq) return;
    const h = joriyXesh();
    if (location.hash !== h) { try { history.replaceState(null, "", h); } catch (err) {} }
  }
  function xeshniOch(h) {
    const q = String(h || "").replace(/^#/, "").split("/").filter(Boolean);
    if (q[0] !== "sozlamalar" || q[1] !== "mahsulotlar") return false;
    if (!ochiq) sahifaniOch();
    if (!mahsulotlar) { kutilgan = h; return true; }
    varaq = null;
    const qism = q.slice(2);
    if (qism[0] === "yangi") varaq = yangiForma();
    else if (/^\d+$/.test(qism[0] || "")) varaq = tahrirForma(Number(qism[0]));
    if (varaq && qism[1] === "kategoriya") {
      const ild = ildizi(varaq.turi_id);
      varaq = { t: "kat", forma: varaq, ildiz: qism[2] === "ichki" && ild != null && tugun.get(ild).bolalar.length ? ild : null };
    } else if (varaq && varaq.id != null && qism[1] === "ochir") varaq = { t: "ochir", id: varaq.id, forma: varaq };
    else if (varaq && varaq.id != null && qism[1] === "rasm") varaq = { t: "rasm", id: varaq.id, forma: varaq };
    chiz();
    return true;
  }

  // ── Telegram «Orqaga» ──────────────────────────────────────────────
  const TB = window.Telegram && Telegram.WebApp && Telegram.WebApp.BackButton;
  if (TB) { try { TB.onClick(() => { if (ochiq) orqa(); }); } catch (err) {} }
  function tgOrqa() {
    if (!TB) return;
    try { if (ochiq) TB.show(); else TB.hide(); } catch (err) {}
  }

  // ── Ulanish ────────────────────────────────────────────────────────
  window.SozlamaBolimi = window.SozlamaBolimi || {};
  window.SozlamaBolimi.mahsulotlar = () => { sahifaniOch(); };

  // Boshqa sahifaga o'tilsa yopiladi; manzil orqali ochilsa — ochiladi.
  window.addEventListener("sahifa", (ev) => {
    if (ev.detail?.nom !== "sozlamalar") return sahifaniYop({ xesh: false });
  });
  // sozlama.js o'z manzilini yozadi (#sozlamalar) — shuning uchun yangi manzilni
  // hodisaning o'zidan (newURL) o'qiymiz.
  window.addEventListener("hashchange", (ev) => {
    const h = new URL(ev.newURL || location.href).hash;
    if (h.startsWith(XESH)) xeshniOch(h);
    else if (ochiq && !h.startsWith("#sozlamalar")) sahifaniYop({ xesh: false });
  });
  // Sozlamalar sahifasi qayta chizilsa (sozlama.js) — bizning manzil joyida qolsin.
  const S = document.getElementById("sahifa-sozlamalar");
  if (S && "MutationObserver" in window) new MutationObserver(() => { if (ochiq) setTimeout(xeshYoz, 0); }).observe(S, { childList: true });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && ochiq && !NAMUNA && INIT && !varaq) yukla();
  });

  // Birinchi ochilish: manzil (sozlama.js uni allaqachon #sozlamalar ga almashtirgan
  // bo'lishi mumkin — navigatsiya yozuvidagi asl URL'dan ham qaraymiz).
  let boshXesh = location.hash;
  if (!boshXesh.startsWith(XESH)) {
    try {
      const n = performance.getEntriesByType("navigation")[0];
      if (n && n.name) boshXesh = new URL(n.name).hash;
    } catch (err) {}
  }
  if (boshXesh.startsWith(XESH) && document.getElementById("sahifa-sozlamalar") && !document.getElementById("sahifa-sozlamalar").hidden) {
    xeshniOch(boshXesh);
  }
})();
