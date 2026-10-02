// «Moliya» sahifasi — index.html dagi umumiy yordamchilar ustida ishlaydi:
// api(), NAMUNA, INIT, oynaOch(), oynaYop(), xabar(), tebran(), e(), $().
// Ma'lumot: GET /app/api/moliya?oy=YYYY-MM (worker/src/miniapp_moliya.js).
// Sahifa almashtirish — index.html dagi router; bu modul `sahifa` hodisasida yuklanadi.
(() => {
  const ILOVA = location.protocol === "file:" ? "" : "/app/";
  const NB = " ";
  const fmt = (s) => String(Math.abs(Math.round(Number(s) || 0))).replace(/\B(?=(\d{3})+(?!\d))/g, NB);
  const uzs = (s) => `${fmt(s)}${NB}UZS`;
  const OYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];

  const IK = {
    hamyon: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M18 7.5V6a1.5 1.5 0 0 0-1.5-1.5h-11A2.5 2.5 0 0 0 3 7v10.5A2.5 2.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5v-9A1.5 1.5 0 0 0 18.5 8H5.5A2.5 2.5 0 0 1 3 7"/><path d="M15.5 12h4.5v4h-4.5a2 2 0 0 1 0-4Z"/></svg>`,
    taqvim: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 17h.01M12 17h.01" stroke-width="2.4"/></svg>`,
    tanga: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="9" cy="6.5" rx="6" ry="2.5"/><path d="M3 6.5v3.5c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5V6.5"/><path d="M3 10v3.5C3 14.9 5.7 16 9 16c1 0 1.9-.1 2.7-.3"/><ellipse cx="15" cy="14" rx="6" ry="2.5"/><path d="M9 17v.5C9 18.9 11.7 20 15 20s6-1.1 6-2.5V14"/></svg>`,
    past: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>`,
    ong: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 5 7 7-7 7"/></svg>`,
    plyus: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>`,
    kebab: `<svg width="4" height="16" viewBox="0 0 4 16" fill="currentColor"><circle cx="2" cy="2" r="1.7"/><circle cx="2" cy="8" r="1.7"/><circle cx="2" cy="14" r="1.7"/></svg>`,
  };

  // Kategoriya ikonkasi foni — guruh bo'yicha pastel (sozlama.js dagi bilan bir xil).
  const PASTEL = {
    food: "#fff0e6", life: "#e8f0ff", transportation: "#e3f5ec", shopping: "#f1ebff", health: "#ffebee",
    education: "#ebe9ff", entertainment: "#f0e9ff", personal: "#ffedf5", finance: "#e5f5ea",
    sports: "#e6f3ff", travel: "#e2f5f3", office: "#edf1f6", others: "#eff1f4",
  };
  const NEYTRAL = "#eff1f4";
  /** Desktop kategoriya ikonkasi: `rasm` (belgilar/<kalit>.svg) yoki `emoji` (server hal qiladi). */
  function ikonka(y, cls) {
    if (y.rasm) {
      const g = y.rasm.slice(0, y.rasm.lastIndexOf("_"));
      return `<span class="${cls}" style="background:${PASTEL[g] || NEYTRAL}"><img src="${ILOVA}belgilar/${e(y.rasm)}.svg" alt="" decoding="async" data-zaxira="1"></span>`;
    }
    return `<span class="${cls}" style="background:${NEYTRAL}">${y.emoji ? `<span class="emoji">${e(y.emoji)}</span>` : ""}</span>`;
  }
  // Ikonka fayli topilmasa — bo'sh neytral doira (kontur ikonka EMAS).
  const zaxira = (ildiz) => ildiz.querySelectorAll("img[data-zaxira]").forEach((img) => {
    img.onerror = () => { img.parentElement.style.background = NEYTRAL; img.remove(); };
  });

  // Namuna (file://) — dizayn namunasi bilan aynan bir xil.
  const NAMUNA_MALUMOT = (oy) => ({
    ok: true, odam: "Fayzulloxon", bugun: "2026-10-04", joriy_oy: "2026-10", otgan_oy: "2026-09",
    kartalar: { balans: 120000, band: 680000, qarzim: 450000 },
    xarajat: oy === "2026-09"
      ? { oy, reja_bor: true, reja: 933333, fakt: 980000, foiz: 105 }
      : { oy: "2026-10", reja_bor: true, reja: 1050000, fakt: 745000, foiz: 71 },
    yozuvlar: [
      { tur: "rasxod", id: 1, kalit: "rasxod:1", nom: "Oziq-ovqat", belgi: "Xarajat", vaqt: "14:30", ishora: "-", rang: "qizil", summa: 40000, rasm: "food_03", emoji: null, ozimi: true,
        tafsilot: { sabab: "Non, sut, tuxum", kategoriya: "Oziq-ovqat", sana: "2026-10-04", vaqt: "14:30", kim_toladi: "Fayzulloxon", doira: "Umumiy", joy: "Naqd",
          ulushlar: [{ nom: "Fayzulloxon", summa: 40000 }, { nom: "Otabek", summa: 40000 }, { nom: "Behruz", summa: 40000 }], jami: 120000, mening_ulushim: 40000 } },
      { tur: "rasxod", id: 5, kalit: "rasxod:5", nom: "Sneklar", belgi: "Xarajat", vaqt: "12:05", ishora: "-", rang: "qizil", summa: 12000, rasm: null, emoji: "🍿", ozimi: true,
        tafsilot: { sabab: "Chips", kategoriya: "Sneklar", sana: "2026-10-04", vaqt: "12:05", kim_toladi: "Fayzulloxon", doira: "Shaxsiy", joy: "Naqd", ulushlar: [], jami: 12000, mening_ulushim: 12000 } },
      { tur: "reja", id: 2, kalit: "reja:2", nom: "Sartarosh (reja)", belgi: "Reja", vaqt: "10:00", ishora: "-", rang: "navy", summa: 50000, rasm: "life_18", emoji: null, ozimi: false,
        tafsilot: { sabab: "Sartarosh", kategoriya: "Sartarosh", sana: "2026-10-04", vaqt: "10:00", doira: "Fayzulloxon — shaxsiy reja", jami: 50000, mening_ulushim: 50000, tolangan: null } },
      { tur: "qarz", id: 3, kalit: "qarz:3", nom: "Abdurahmon akaga qarz qaytarildi", belgi: "Qarz", vaqt: "09:20", ishora: "-", rang: "navy", summa: 200000, rasm: "finance_03", emoji: null, ozimi: false,
        tafsilot: { sabab: "", sana: "2026-10-04", vaqt: "09:20", kimga: "Abdurahmon aka", doira: "Shaxsiy qarz", jami: 200000 } },
      { tur: "rasxod", id: 4, kalit: "rasxod:4", nom: "Transport", belgi: "Xarajat", vaqt: "08:10", ishora: "-", rang: "qizil", summa: 15000, rasm: "transportation_08", emoji: null, ozimi: true,
        tafsilot: { sabab: "Avtobus", kategoriya: "Transport", sana: "2026-10-04", vaqt: "08:10", kim_toladi: "Fayzulloxon", doira: "Shaxsiy", joy: "Naqd", ulushlar: [], jami: 15000, mening_ulushim: 15000 } },
    ],
  });

  let m = null;          // oxirgi javob
  let oy = null;         // tanlangan oy (null — joriy)
  let xatoMatn = "";
  let yuklanmoqda = false;
  let eskirgan = true;   // sahifa ochilganda qayta yuklansinmi
  let chizildi = false;

  // ── Skelet ──────────────────────────────────────────────────────────
  function skelet() {
    const s = $("sahifa-moliya");
    s.innerHTML = `
      <div class="sarlavha">
        <h1>Moliya</h1>
        <button class="mo-oy" id="moOy" aria-haspopup="true" aria-expanded="false"><span id="moOyNom">Bu oy</span>${IK.past}</button>
        <div class="mo-oy-menyu" id="moOyMenyu" hidden>
          <button data-oy="joriy">Bu oy</button><button data-oy="otgan">O‘tgan oy</button>
        </div>
      </div>
      <div class="mo-kartalar">
        <div class="mo-karta mo-k-balans"><span class="ik">${IK.hamyon}</span><span class="yorliq">Joriy balans</span><span class="qiymat" id="moBalans">—</span><span class="izoh">Qarz va rejalardan keyin</span></div>
        <div class="mo-karta mo-k-band"><span class="ik">${IK.taqvim}</span><span class="yorliq">Rejaga band</span><span class="qiymat" id="moBand">—</span></div>
        <div class="mo-karta mo-k-qarz"><span class="ik">${IK.tanga}</span><span class="yorliq">Qarzim</span><span class="qiymat" id="moQarz">—</span></div>
      </div>
      <div class="mo-xarajat">
        <div class="ust">
          <div class="chap"><div class="yorliq" id="moXYorliq">Bu oy xarajatlari</div><div class="summa" id="moFakt">—</div></div>
          <div class="ong"><div class="reja" id="moReja">Reja: —</div><div class="foiz" id="moFoiz"></div></div>
        </div>
        <div class="mo-chiziq"><i id="moChiziq" style="width:0"></i></div>
      </div>
      <div class="bolim"><h2>Bugun</h2><span id="moSoni"></span></div>
      <div class="mo-royxat" id="moRoyxat"></div>
      <button class="qoshish" id="moQosh">
        <span class="plyus">${IK.plyus}</span>
        <span class="matn">Yangi rasxod qo‘shish</span>
        <span class="strelka">${IK.ong}</span>
      </button>`;
    $("moOy").onclick = (ev) => { ev.stopPropagation(); oyMenyu(!$("moOyMenyu").hidden ? false : true); };
    $("moOyMenyu").onclick = (ev) => {
      const b = ev.target.closest("[data-oy]"); if (!b) return;
      oyMenyu(false);
      const yangi = b.dataset.oy === "otgan" ? (m?.otgan_oy || null) : null;
      if (yangi === oy) return;
      oy = yangi; tebran("soft"); oyNomi(); yukla();
    };
    document.addEventListener("click", () => oyMenyu(false));
    $("moRoyxat").onclick = (ev) => {
      const q = ev.target.closest(".mo-qator"); if (!q) return;
      const y = m?.yozuvlar.find((x) => x.kalit === q.dataset.k); if (y) tafsilot(y);
    };
    $("moQosh").onclick = () => {
      if (typeof window.rasxodOch === "function") window.rasxodOch();
      else xabar("Yangi xarajat — keyingi bosqichda");
    };
    chizildi = true;
  }

  function oyMenyu(och) {
    const menyu = $("moOyMenyu"); if (!menyu) return;
    menyu.hidden = !och;
    $("moOy").setAttribute("aria-expanded", och ? "true" : "false");
    menyu.querySelectorAll("button").forEach((b) =>
      b.classList.toggle("faol", (b.dataset.oy === "otgan") === (oy != null)));
  }
  const oyNomi = () => { $("moOyNom").textContent = oy ? "O‘tgan oy" : "Bu oy"; };

  // Qiymat karta eniga sig'masa — shrift kichrayadi (katta summalar).
  function sigdir(el, bosh) {
    el.style.fontSize = "";
    let f = bosh;
    while (el.scrollWidth > el.clientWidth + 0.5 && f > 10) { f -= 0.5; el.style.fontSize = f + "px"; }
  }

  const sigdirHammasi = () => document.querySelectorAll("#sahifa-moliya .mo-karta .qiymat").forEach((el) => sigdir(el, 14));
  // Shrift (Inter) keyin yuklansa yoki ekran o'zgarsa — qayta o'lchanadi.
  try {
    document.fonts.ready.then(() => chizildi && sigdirHammasi());
    document.fonts.addEventListener("loadingdone", () => chizildi && sigdirHammasi());
  } catch (err) {}
  window.addEventListener("resize", () => chizildi && sigdirHammasi());

  // ── Chizish ─────────────────────────────────────────────────────────
  function chiz() {
    if (!chizildi) skelet();
    if (!m) {
      $("moSoni").textContent = "";
      $("moRoyxat").innerHTML = `<div class="bosh-holat">${e(xatoMatn || "Yuklanmoqda…")}</div>`;
      return;
    }
    const k = m.kartalar;
    [["moBalans", k.balans], ["moBand", k.band], ["moQarz", k.qarzim]].forEach(([id, s]) => {
      $(id).textContent = (s < 0 ? "−" : "") + uzs(s);
    });
    $("moBalans").classList.toggle("manfiy", k.balans < 0);
    sigdirHammasi();

    const x = m.xarajat;
    const joriy = x.oy === m.joriy_oy;
    $("moXYorliq").textContent = joriy ? "Bu oy xarajatlari"
      : (x.oy === m.otgan_oy ? "O‘tgan oy xarajatlari" : `${OYLAR[Number(x.oy.slice(5)) - 1]} xarajatlari`);
    $("moFakt").textContent = uzs(x.fakt);
    $("moReja").textContent = `Reja: ${x.reja_bor ? fmt(x.reja) + NB + "UZS" : "—"}`;
    const oshdi = x.foiz != null && x.foiz > 100;
    $("moFoiz").textContent = x.foiz != null ? `${x.foiz}%` : "";
    $("moFoiz").classList.toggle("oshdi", oshdi);
    $("moChiziq").style.width = `${x.foiz != null ? Math.min(100, x.foiz) : 0}%`;
    $("moChiziq").classList.toggle("oshdi", oshdi);

    const ys = m.yozuvlar;
    $("moSoni").textContent = `${ys.length} ta yozuv`;
    if (!ys.length) {
      $("moRoyxat").innerHTML = `<div class="bosh-holat">Bugun hali yozuv yo‘q</div>`;
      return;
    }
    $("moRoyxat").innerHTML = ys.map((y) => {
      const tur = y.belgi === "Xarajat" ? "xarajat" : y.belgi === "Reja" ? "reja" : "qarz";
      return `<button class="mo-qator" data-k="${e(y.kalit)}">
        ${ikonka(y, "mo-doira")}
        <span class="ichi"><span class="nom">${e(y.nom)}</span>
          <span class="past"><span class="belgi b-${tur}">${y.belgi}</span>${y.vaqt ? `<span class="soat">${y.vaqt}</span>` : ""}</span></span>
        <span class="pul pul-${y.rang}">${y.ishora}${NB}${uzs(y.summa)}</span>
        <span class="kebab" aria-label="Tafsilot">${IK.kebab}</span>
      </button>`;
    }).join("");
    zaxira($("moRoyxat"));
  }

  // ── Tafsilot va o'chirish ───────────────────────────────────────────
  function sanaMatn(s, v) {
    if (!s) return "—";
    const [, mo, d] = s.split("-").map(Number);
    return `${d}-${OYLAR[mo - 1]}${v ? ", " + v : ""}`;
  }
  function tafsilot(y) {
    const t = y.tafsilot || {};
    const qator = (k, v) => (v == null || v === "" ? "" : `<dt>${k}</dt><dd>${e(v)}</dd>`);
    let ichi = "";
    if (y.tur === "rasxod") {
      ichi = qator("Kategoriya", t.kategoriya) + qator("Sabab", t.sabab) + qator("Kim to‘ladi", t.kim_toladi) +
        qator("Turi", t.doira) + qator("Qayerdan", t.joy) +
        (t.ulushlar?.length ? `<div class="ulushlar"><div>Ulushlar</div>${t.ulushlar.map((u) =>
          `<div><span>${e(u.nom)}</span><b>${uzs(u.summa)}</b></div>`).join("")}</div>` : "") +
        qator("Jami chek", t.jami != null ? uzs(t.jami) : null) +
        qator("Sizning ulushingiz", uzs(t.mening_ulushim || 0));
    } else if (y.tur === "reja") {
      ichi = qator("Kategoriya", t.kategoriya) + qator("Nomi", t.sabab) + qator("Doira", t.doira) +
        (t.jami != null && t.jami !== t.mening_ulushim
          ? qator("Jami reja", uzs(t.jami)) + qator("Sizning ulushingiz", uzs(t.mening_ulushim || 0)) : "") +
        (t.tolangan != null ? qator("Aslida to‘landi", uzs(t.tolangan)) : "");
    } else {
      ichi = qator("Kimdan", t.kimdan || t.kim_berdi || t.kim_toladi) + qator("Kimga", t.kimga) +
        qator("Kim oldi", t.kim_oldi) + qator("Turi", t.doira) +
        (t.jami && t.jami !== y.summa ? qator("Jami summa", uzs(t.jami)) : "") + qator("Izoh", t.sabab);
    }
    ichi += qator("Sana", sanaMatn(t.sana, t.vaqt));
    oynaOch(`<div class="mo-t-bosh">${ikonka(y, "mo-doira katta-doira")}<h3>${e(y.nom)}</h3></div>
      <div class="mo-tafsilot">
        <p class="katta pul-${y.rang}">${y.ishora}${NB}${uzs(y.summa)}</p>
        <dl>${ichi}</dl>
      </div>
      ${y.tur === "rasxod" && y.ozimi ? `<button class="amal xavf mo-ochir" data-h="ochir"><i>✕</i>O‘chirish</button>` : ""}`);
    zaxira($("oyna"));
    $("oyna").onclick = (ev) => {
      const b = ev.target.closest("[data-h]"); if (!b) return;
      if (b.dataset.h === "ochir") tasdiq(y);
    };
  }
  function tasdiq(y) {
    oynaOch(`<h3>Rasxodni o‘chirasizmi?</h3>
      <p class="izoh">${e(y.nom)} · ${uzs(y.tafsilot?.jami ?? y.summa)}. Ulushlar ham hisobdan chiqadi.</p>
      <div class="mo-tasdiq"><button data-h="yoq">Yo‘q</button><button class="xavf" data-h="ha">O‘chirish</button></div>`);
    $("oyna").onclick = async (ev) => {
      const b = ev.target.closest("[data-h]"); if (!b) return;
      if (b.dataset.h === "yoq") return oynaYop();
      b.disabled = true;
      try {
        if (NAMUNA) m.yozuvlar = m.yozuvlar.filter((x) => x.kalit !== y.kalit);
        else await api(`moliya/rasxod/${y.id}/ochir`, {});
        oynaYop(); tebran("medium"); xabar("Rasxod o‘chirildi");
        if (NAMUNA) chiz(); else yukla();
      } catch (err) { b.disabled = false; xabar(err.message); }
    };
  }

  // ── Yuklash ─────────────────────────────────────────────────────────
  async function yukla() {
    if (!chizildi) skelet();
    eskirgan = false;
    if (NAMUNA) { m = NAMUNA_MALUMOT(oy); return chiz(); }
    if (!INIT) { xatoMatn = "Bu sahifani Telegram'dagi Farovon Uy botidan oching."; return chiz(); }
    if (yuklanmoqda) return;
    yuklanmoqda = true;
    try {
      m = await api("moliya" + (oy ? `?oy=${oy}` : ""));
      xatoMatn = "";
    } catch (err) {
      xatoMatn = err.message;
      if (m) xabar(err.message);
    }
    yuklanmoqda = false;
    chiz();
  }

  // ── Sahifa ko'rsatilganda (index.html router: `sahifa` hodisasi) ─────
  const korinadimi = () => !$("sahifa-moliya").hidden;
  window.addEventListener("sahifa", (ev) => {
    if (ev.detail?.nom === "moliya" && (eskirgan || !m)) yukla();
  });
  window.addEventListener("rasxod-saqlandi", () => {
    eskirgan = true;
    if (korinadimi()) yukla();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) return;
    eskirgan = true;
    if (korinadimi() && !NAMUNA && INIT) yukla();
  });
  // Kech yuklandi: #moliya bilan ochilgan bo'lsa sahifa allaqachon ko'rinib turibdi.
  if (korinadimi()) yukla();
})();
