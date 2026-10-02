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
    savat: `<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 3.5h2.6l2.3 11.2a1.5 1.5 0 0 0 1.5 1.2h8.7a1.5 1.5 0 0 0 1.5-1.1L21 7.5H6"/><circle cx="9.5" cy="19.5" r="1.4"/><circle cx="17.5" cy="19.5" r="1.4"/></svg>`,
    uy: `<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"><path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 8.6V20a1 1 0 0 0 1 1H10v-6h4v6h3.5a1 1 0 0 0 1-1V8.6"/></svg>`,
    odamlar: `<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20v-1a5 5 0 0 1 5-5h3a5 5 0 0 1 5 5v1"/><path d="M15.5 4.7a3.5 3.5 0 0 1 0 6.6"/><path d="M18.5 14.2a5 5 0 0 1 3 4.6V20"/></svg>`,
    past: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>`,
    ong: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 5 7 7-7 7"/></svg>`,
    plyus: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>`,
    kebab: `<svg width="4" height="16" viewBox="0 0 4 16" fill="currentColor"><circle cx="2" cy="2" r="1.7"/><circle cx="2" cy="8" r="1.7"/><circle cx="2" cy="14" r="1.7"/></svg>`,
  };

  // Namuna (file://) — dizayn namunasi bilan aynan bir xil.
  const NAMUNA_MALUMOT = (oy) => ({
    ok: true, odam: "Fayzulloxon", bugun: "2026-10-04", joriy_oy: "2026-10", otgan_oy: "2026-09",
    kartalar: { balans: 1250000, band: 680000, qarzim: 450000 },
    xarajat: oy === "2026-09"
      ? { oy, reja_bor: true, reja: 2800000, fakt: 2950000, foiz: 105 }
      : { oy: "2026-10", reja_bor: true, reja: 3000000, fakt: 2130000, foiz: 71 },
    yozuvlar: [
      { tur: "rasxod", id: 1, kalit: "rasxod:1", nom: "Oziq-ovqat", belgi: "Xarajat", vaqt: "14:30", ishora: "-", rang: "qizil", summa: 120000, rasm: null, ozimi: true,
        tafsilot: { sabab: "Non, sut, tuxum", kategoriya: "Oziq-ovqat", sana: "2026-10-04", vaqt: "14:30", kim_toladi: "Fayzulloxon", doira: "Umumiy", joy: "Naqd",
          ulushlar: [{ nom: "Fayzulloxon", summa: 40000 }, { nom: "Otabek", summa: 40000 }, { nom: "Behruz", summa: 40000 }], mening_ulushim: 40000 } },
      { tur: "reja", id: 2, kalit: "reja:2", nom: "Uy ijarasi (reja)", belgi: "Reja", vaqt: "10:00", ishora: "-", rang: "navy", summa: 650000, rasm: null, ozimi: false,
        tafsilot: { sabab: "Uy ijarasi", kategoriya: "Uy-joy", sana: "2026-10-04", vaqt: "10:00", doira: "Umumiy reja", tolangan: null } },
      { tur: "qarz", id: 3, kalit: "qarz:3", nom: "Otabekdan qarz", belgi: "Qarz", vaqt: "09:20", ishora: "+", rang: "yashil", summa: 200000, rasm: null, ozimi: false,
        tafsilot: { sabab: "", sana: "2026-10-04", vaqt: "09:20", kim_berdi: "Otabek", kimga: "Fayzulloxon" } },
      { tur: "rasxod", id: 4, kalit: "rasxod:4", nom: "Transport", belgi: "Xarajat", vaqt: "08:10", ishora: "-", rang: "qizil", summa: 15000, rasm: null, ozimi: true,
        tafsilot: { sabab: "Avtobus", kategoriya: "Transport", sana: "2026-10-04", vaqt: "08:10", kim_toladi: "Fayzulloxon", doira: "Shaxsiy", joy: "Naqd", ulushlar: [], mening_ulushim: 15000 } },
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
        <div class="mo-karta mo-k-balans"><span class="ik">${IK.hamyon}</span><span class="yorliq">Joriy balans</span><span class="qiymat" id="moBalans">—</span></div>
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
      $(id).textContent = (s < 0 ? "-" : "") + uzs(s);
    });
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
      const ik = tur === "reja" ? IK.uy : tur === "qarz" ? IK.odamlar
        : y.rasm ? `<img src="${ILOVA}belgilar/${e(y.rasm)}.svg" alt="" loading="lazy" data-zaxira="1">` : IK.savat;
      return `<button class="mo-qator" data-k="${e(y.kalit)}">
        <span class="mo-doira mo-d-${tur}">${ik}</span>
        <span class="ichi"><span class="nom" style="display:block">${e(y.nom)}</span>
          <span class="past"><span class="belgi b-${tur}">${y.belgi}</span>${y.vaqt ? `<span class="soat">${y.vaqt}</span>` : ""}</span></span>
        <span class="pul pul-${y.rang}">${y.ishora}${NB}${uzs(y.summa)}</span>
        <span class="kebab" aria-label="Tafsilot">${IK.kebab}</span>
      </button>`;
    }).join("");
    // Ikonka fayli topilmasa — savatcha.
    $("moRoyxat").querySelectorAll("img[data-zaxira]").forEach((img) => {
      img.onerror = () => { img.outerHTML = IK.savat; };
    });
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
        qator("Sizning ulushingiz", uzs(t.mening_ulushim || 0));
    } else if (y.tur === "reja") {
      ichi = qator("Kategoriya", t.kategoriya) + qator("Nomi", t.sabab) + qator("Doira", t.doira) +
        (t.tolangan != null ? qator("Aslida to‘landi", uzs(t.tolangan)) : "");
    } else {
      ichi = qator("Kimdan", t.kimdan || t.kim_berdi || t.kim_toladi) + qator("Kimga", t.kimga) +
        qator("Kim oldi", t.kim_oldi) + qator("Turi", t.doira) +
        (t.jami && t.jami !== y.summa ? qator("Jami summa", uzs(t.jami)) : "") + qator("Izoh", t.sabab);
    }
    ichi += qator("Sana", sanaMatn(t.sana, t.vaqt));
    oynaOch(`<h3>${e(y.nom)}</h3>
      <div class="mo-tafsilot">
        <p class="katta pul-${y.rang}">${y.ishora}${NB}${uzs(y.summa)}</p>
        <dl>${ichi}</dl>
      </div>
      ${y.tur === "rasxod" && y.ozimi ? `<button class="amal xavf mo-ochir" data-h="ochir"><i>✕</i>O‘chirish</button>` : ""}`);
    $("oyna").onclick = (ev) => {
      const b = ev.target.closest("[data-h]"); if (!b) return;
      if (b.dataset.h === "ochir") tasdiq(y);
    };
  }
  function tasdiq(y) {
    oynaOch(`<h3>Rasxodni o‘chirasizmi?</h3>
      <p class="izoh">${e(y.nom)} · ${uzs(y.summa)}. Ulushlar ham hisobdan chiqadi.</p>
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
