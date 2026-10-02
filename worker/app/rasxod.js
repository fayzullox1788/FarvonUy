// «Yangi rasxod» — pastdan chiqadigan oyna (Mini App).
//
// Ochish: window.rasxodOch()  (pastki menyudagi «+», Moliya sahifasi ham).
// Saqlangach: window ga "rasxod-saqlandi" hodisasi ({detail: {id}}).
// API: GET /app/api/rasxod/forma, POST /app/api/rasxod (worker/src/miniapp_rasxod.js).
// Hamma tekshiruv va yozuv serverda — `rasxod_kirit` (desktop va bot bilan bitta mantiq).
// Kompyuterda fayl sifatida ochilsa (file://) — namunaviy ma'lumot; «#rasxod» darhol ochadi.
(function () {
  "use strict";
  const tg = window.Telegram && Telegram.WebApp;
  const NAMUNA = location.protocol === "file:";
  const ASOS = NAMUNA ? "" : "/app/";
  const INIT = (tg && tg.initData) || "";

  const NAMUNA_FORMA = {
    ok: true, men: 1, bugun: "",
    odamlar: [
      { id: 1, nom: "Fayzulloxon", real_balans: 120000, kartalar: [{ id: 11, nom: "Karta" }, { id: 12, nom: "2-karta" }] },
      { id: 2, nom: "Otabek", real_balans: 85500, kartalar: [{ id: 21, nom: "Humo" }] },
      { id: 3, nom: "Abbosxon", real_balans: -14000, kartalar: [] },
    ],
    qatnashchilar: [1, 2, 3],
    kategoriyalar: [
      { id: 5, nom: "Oziq-ovqat", belgi: "life_16.svg", chuq: 0, ichki: [
        { id: 51, nom: "Meva-sabzavot", belgi: "food_13.svg", chuq: 0 },
        { id: 52, nom: "Non", belgi: "food_01.svg", chuq: 0 },
      ] },
      { id: 6, nom: "Transport", belgi: "transportation_01.svg", chuq: 0, ichki: [] },
      { id: 7, nom: "Kommunal", belgi: null, chuq: 0, ichki: [] },
    ],
  };

  // ── Ikonkalar ────────────────────────────────────────────────────────
  const S = (d, w = 1.8) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const IK = {
    odam: S('<circle cx="12" cy="8" r="3.6"/><path d="M5 20.2c0-3.6 3.1-5.9 7-5.9s7 2.3 7 5.9"/>'),
    guruh: `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="7.4" r="3.2"/><circle cx="5.6" cy="9.2" r="2.4"/><circle cx="18.4" cy="9.2" r="2.4"/><path d="M6.6 19.5c0-3.4 2.4-6 5.4-6s5.4 2.6 5.4 6z"/><path d="M1.8 18.6c0-2.6 1.7-4.6 3.9-4.6.6 0 1.1.1 1.6.4-1 1.2-1.6 2.7-1.7 4.2z"/><path d="M22.2 18.6c0-2.6-1.7-4.6-3.9-4.6-.6 0-1.1.1-1.6.4 1 1.2 1.6 2.7 1.7 4.2z"/></svg>`,
    hamyon: S('<path d="M17.5 7V5.6A1.6 1.6 0 0 0 15.9 4H6a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h12.4a1.6 1.6 0 0 0 1.6-1.6V9.6A1.6 1.6 0 0 0 18.4 8H6A3 3 0 0 1 3 7"/><path d="M16.5 13.6h.6"/>', 2),
    info: S('<circle cx="12" cy="12" r="9.2"/><path d="M12 11v5.5"/><path d="M12 7.6v.1" stroke-width="2.4"/>', 1.7),
    naqd: S('<rect x="2.5" y="6" width="19" height="12" rx="1.8"/><circle cx="12" cy="12" r="2.6"/><path d="M6 9.2v.1M18 14.8v-.1" stroke-width="2.4"/>', 1.7),
    karta: S('<rect x="2.8" y="5" width="18.4" height="14" rx="2.4"/><path d="M2.8 9.6h18.4M6.5 15h4"/>', 1.8),
    pastga: S('<path d="m6 9.5 6 6 6-6"/>', 2),
    yop: S('<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>', 2),
    belgi: S('<path d="m5 12.5 4.5 4.5L19 7.5"/>', 2.4),
    tur: S('<path d="M4 7.5h16M4 12h16M4 16.5h10"/>', 1.8),
  };

  // ── Holat ────────────────────────────────────────────────────────────
  let F = null;            // /forma javobi
  let H = null;            // tanlovlar
  let yaratildi = false;
  const $ = (s, ota = document) => ota.querySelector(s);
  const e = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // money.fmt bilan bir xil: ajratmaydigan probel
  const fmt = (n) => { const s = Math.round(Number(n) || 0); return (s < 0 ? "-" : "") + String(Math.abs(s)).replace(/\B(?=(\d{3})+(?!\d))/g, " "); };
  const odam = (id) => F.odamlar.find((o) => o.id === id);
  const kat = (id) => F.kategoriyalar.find((k) => k.id === id);
  const tebran = (t) => { try { t === "ok" ? tg.HapticFeedback.notificationOccurred("success") : tg.HapticFeedback.impactOccurred(t || "light"); } catch (x) {} };

  function boshHolat() {
    const men = F.odamlar.some((o) => o.id === F.men) ? F.men : (F.odamlar[0] || {}).id;
    H = { kimning: men, tur: "umumiy", toladi: men, karta: null, kat: null, ichki: null, summa: 0, sabab: "" };
    if (NAMUNA) Object.assign(H, { karta: 11, kat: 5, ichki: 51 });
  }

  async function api(yol, tana) {
    const r = await fetch("/app/api/" + yol, {
      method: tana ? "POST" : "GET",
      headers: { authorization: "tma " + INIT, ...(tana ? { "content-type": "application/json" } : {}) },
      body: tana ? JSON.stringify(tana) : undefined,
    });
    let j = {};
    try { j = await r.json(); } catch (x) {}
    if (!r.ok || !j.ok) throw new Error(j.xato || `Server javob bermadi (${r.status})`);
    return j;
  }

  // ── DOM ──────────────────────────────────────────────────────────────
  function yarat() {
    if (yaratildi) return;
    yaratildi = true;
    const d = document.createElement("div");
    d.innerHTML = `
      <div class="rx-parda" id="rxParda"></div>
      <section class="rx-oyna" id="rxOyna" role="dialog" aria-modal="true" aria-labelledby="rxSarlavha">
        <div class="rx-tutqich"></div>
        <div class="rx-bosh"><h2 id="rxSarlavha">Yangi rasxod</h2><button class="rx-yop" id="rxYop" aria-label="Yopish">${IK.yop.replace("<svg", '<svg width="18" height="18"')}</button></div>
        <div class="rx-ichi" id="rxIchi"></div>
        <div class="rx-pas"><button class="rx-saqla" id="rxSaqla">Saqlash</button></div>
      </section>
      <div class="rx-royxat-parda" id="rxRParda"></div>
      <section class="rx-royxat" id="rxRoyxat" role="dialog"></section>
      <div class="rx-xabar" id="rxXabar"></div>`;
    while (d.firstElementChild) document.body.appendChild(d.firstElementChild);
    $("#rxParda").onclick = yop;
    $("#rxYop").onclick = yop;
    $("#rxRParda").onclick = royxatYop;
    $("#rxSaqla").onclick = saqla;
    $("#rxIchi").addEventListener("click", bosildi);
    $("#rxIchi").addEventListener("input", yozildi);
    // Ikonka fayli topilmasa — neytral belgi (yangi ikonka o'ylab topilmaydi)
    document.addEventListener("error", (ev) => {
      const t = ev.target;
      if (t && t.tagName === "IMG" && t.parentNode && t.parentNode.classList.contains("rx-ikon")) t.parentNode.innerHTML = BOSH_IKON;
    }, true);
  }

  const BOSH_IKON = `<span class="rx-yoq">${IK.tur.replace("<svg", '<svg width="16" height="16"')}</span>`;
  const ikon = (fayl) => `<span class="rx-ikon">${fayl ? `<img src="${ASOS}belgilar/${e(fayl)}" alt="">` : BOSH_IKON}</span>`;

  function odamTugmalari(nom, tanlangan) {
    return `<div class="rx-seg uch">${F.odamlar.map((o) =>
      `<button class="rx-t${o.id === tanlangan ? " tanlangan" : ""}" data-${nom}="${o.id}">${IK.odam}<span>${e(o.nom)}</span></button>`).join("")}</div>`;
  }

  function chiz() {
    const ich = $("#rxIchi");
    const fokus = document.activeElement && document.activeElement.id;
    const k = kat(H.kat);
    const ichki = k && k.ichki.length ? k.ichki : [];
    const ik = ichki.find((x) => x.id === H.ichki);
    const toladi = odam(H.toladi);
    const kartalar = toladi ? toladi.kartalar : [];
    const tolovlar = [{ id: null, nom: "Naqt", ikon: IK.naqd }, ...kartalar.map((x) => ({ id: x.id, nom: x.nom, ikon: IK.karta }))];
    const b = odam(H.kimning);
    ich.innerHTML = `
      <div class="rx-kirit">
        <div class="rx-maydon rx-summa" id="rxSummaQ"><label for="rxSumma">Summa</label>
          <input id="rxSumma" inputmode="numeric" autocomplete="off" placeholder="0" value="${H.summa ? fmt(H.summa) : ""}"><span class="rx-val">UZS</span></div>
        <div class="rx-maydon" id="rxSababQ"><label for="rxSabab">Sabab</label>
          <input id="rxSabab" autocomplete="off" maxlength="120" placeholder="Nima uchun?" value="${e(H.sabab)}"></div>
      </div>

      <div class="rx-bolim">Kimning rasxodi?</div>
      ${odamTugmalari("kimning", H.kimning)}
      <div class="rx-balans">
        <div class="rx-hamyon">${IK.hamyon.replace("<svg", '<svg width="24" height="24"')}</div>
        <div>
          <div class="rx-b-l">Real balans</div>
          <div class="rx-b-q${b && b.real_balans < 0 ? " manfiy" : ""}">${b ? fmt(b.real_balans) : "—"} UZS</div>
          <div class="rx-b-i">Qarz va rejalardan keyin</div>
        </div>
      </div>

      <div class="rx-bolim">Rasxod turi</div>
      <div class="rx-seg ikki">
        <button class="rx-t${H.tur === "umumiy" ? " tanlangan" : ""}" data-tur="umumiy">${IK.guruh.replace("<svg", '<svg style="width:22px;height:22px"')}<span>Umumiy</span></button>
        <button class="rx-t${H.tur === "shaxsiy" ? " tanlangan" : ""}" data-tur="shaxsiy">${IK.odam}<span>Shaxsiy</span></button>
      </div>
      <div class="rx-bolinish" id="rxBolinish"${H.tur === "umumiy" ? "" : " hidden"}>
        ${IK.info.replace("<svg", '<svg width="22" height="22"')}
        <div class="rx-n">${F.qatnashchilar.length} kishiga teng bo‘linadi</div>
        <div class="rx-chiziq"></div>
        <div class="rx-har"><small>Har biriga:</small><b id="rxHar">${fmt(harBiri())} UZS</b></div>
      </div>

      <div class="rx-bolim">Kim to‘laydi?</div>
      ${odamTugmalari("toladi", H.toladi)}

      <div class="rx-bolim">Nimadan to‘lov qilindi?</div>
      <div class="rx-seg ${tolovlar.length > 3 ? "kop" : ""}">${tolovlar.map((t) =>
        `<button class="rx-t${t.id === H.karta ? " tanlangan" : ""}" data-karta="${t.id ?? ""}">${t.ikon}<span>${e(t.nom)}</span></button>`).join("")}</div>

      <div class="rx-bolim">Kategoriya</div>
      <button class="rx-tanla" data-ochish="kat">${k ? ikon(k.belgi) : ikon(null)}
        <span class="rx-nom${k ? "" : " bosh"}">${k ? e(k.nom) : "Kategoriyani tanlang"}</span>${IK.pastga.replace("<svg", '<svg width="20" height="20"')}</button>

      ${ichki.length ? `
      <div class="rx-bolim">Pad kategoriya</div>
      <button class="rx-tanla" data-ochish="ichki">${ik ? ikon(ik.belgi) : ikon(k.belgi)}
        <span class="rx-nom${ik ? "" : " bosh"}">${ik ? e(ik.nom) : "— ichki kategoriyasiz —"}</span>${IK.pastga.replace("<svg", '<svg width="20" height="20"')}</button>` : ""}`;
    if (fokus && (fokus === "rxSumma" || fokus === "rxSabab")) {
      const el = $("#" + fokus); el.focus(); const n = el.value.length; try { el.setSelectionRange(n, n); } catch (x) {}
    }
  }

  // Umumiy: `money.bol_teng` dagi eng katta ulush (qoldiq +1 so'm bilan tarqaladi).
  function harBiri() {
    const n = F.qatnashchilar.length || 1;
    return Math.floor(H.summa / n) + (H.summa % n ? 1 : 0);
  }

  function bosildi(ev) {
    const t = ev.target.closest("button"); if (!t) return;
    const d = t.dataset;
    if (d.kimning) { H.kimning = Number(d.kimning); }
    else if (d.tur) { H.tur = d.tur; }
    else if (d.toladi) {
      const yangi = Number(d.toladi);
      if (yangi !== H.toladi) H.karta = null; // karta to'lovchiniki bo'lishi shart
      H.toladi = yangi;
    } else if (d.karta !== undefined) { H.karta = d.karta === "" ? null : Number(d.karta); }
    else if (d.ochish) { return royxatOch(d.ochish); }
    else return;
    tebran("soft");
    chiz();
  }

  function yozildi(ev) {
    const t = ev.target;
    if (t.id === "rxSumma") {
      const raqam = t.value.replace(/\D/g, "").replace(/^0+/, "").slice(0, 13);
      H.summa = raqam ? Number(raqam) : 0;
      t.value = raqam ? fmt(H.summa) : "";
      $("#rxSummaQ").classList.remove("xato");
      const h = $("#rxHar"); if (h) h.textContent = `${fmt(harBiri())} UZS`;
    } else if (t.id === "rxSabab") {
      H.sabab = t.value;
      $("#rxSababQ").classList.remove("xato");
    }
  }

  // ── Kategoriya ro'yxati ──────────────────────────────────────────────
  function royxatOch(qaysi) {
    const k = kat(H.kat);
    let qatorlar, sarlavha;
    if (qaysi === "kat") {
      sarlavha = "Kategoriya";
      qatorlar = F.kategoriyalar.map((x) => ({ id: x.id, nom: x.nom, belgi: x.belgi, chuq: 0, tanlangan: x.id === H.kat }));
    } else {
      sarlavha = "Pad kategoriya";
      qatorlar = [{ id: "", nom: "— ichki kategoriyasiz —", belgi: k.belgi, chuq: 0, tanlangan: H.ichki == null },
        ...k.ichki.map((x) => ({ ...x, tanlangan: x.id === H.ichki }))];
    }
    const r = $("#rxRoyxat");
    r.innerHTML = `<div class="rx-tutqich"></div><h3>${sarlavha}</h3><div class="rx-qatorlar">${qatorlar.length ? qatorlar.map((x) =>
      `<button class="rx-qator${x.tanlangan ? " tanlangan" : ""}" data-id="${x.id}" style="padding-left:${10 + 22 * (x.chuq || 0)}px">${ikon(x.belgi)}<span class="rx-nom">${e(x.nom)}</span>${x.tanlangan ? `<span class="rx-belgi">${IK.belgi.replace("<svg", '<svg width="18" height="18"')}</span>` : ""}</button>`).join("")
      : `<div class="rx-qator">Kategoriya yo‘q</div>`}</div>`;
    r.onclick = (ev) => {
      const b = ev.target.closest(".rx-qator[data-id]"); if (!b) return;
      const id = b.dataset.id === "" ? null : Number(b.dataset.id);
      if (qaysi === "kat") { if (id !== H.kat) { H.kat = id; H.ichki = null; } }
      else H.ichki = id;
      tebran("soft"); royxatYop(); chiz();
    };
    $("#rxRParda").classList.add("ochiq"); r.classList.add("ochiq");
  }
  function royxatYop() { $("#rxRParda").classList.remove("ochiq"); $("#rxRoyxat").classList.remove("ochiq"); }

  // ── Ochish / yopish / saqlash ────────────────────────────────────────
  let xabarVaqt;
  function xabar(m) {
    const x = $("#rxXabar"); x.textContent = m; x.classList.add("kor");
    clearTimeout(xabarVaqt); xabarVaqt = setTimeout(() => x.classList.remove("kor"), 2400);
  }

  async function och() {
    yarat();
    const ichi = $("#rxIchi");
    if (NAMUNA) { if (!F) { F = NAMUNA_FORMA; } }
    else {
      if (!INIT) return xabar("Bu sahifani Telegram'dagi Farovon Uy botidan oching.");
      if (!F) ichi.innerHTML = `<p style="color:#8a94a6">Yuklanmoqda…</p>`;
    }
    $("#rxParda").classList.add("ochiq"); $("#rxOyna").classList.add("ochiq");
    if (!NAMUNA) {
      try { F = await api("rasxod/forma"); }
      catch (err) { if (!F) { ichi.innerHTML = `<p style="color:#8a94a6">${e(err.message)}</p>`; return; } }
    }
    boshHolat();
    chiz();
    ichi.scrollTop = 0;
  }

  function yop() {
    royxatYop();
    $("#rxParda").classList.remove("ochiq"); $("#rxOyna").classList.remove("ochiq");
    if (document.activeElement) document.activeElement.blur();
  }

  async function saqla() {
    if (!F || !H) return;
    if (!H.summa) { $("#rxSummaQ").classList.add("xato"); $("#rxSumma").focus(); return xabar("Summani kiriting"); }
    if (!H.sabab.trim()) { $("#rxSababQ").classList.add("xato"); $("#rxSabab").focus(); return xabar("Sababini yozing — rasxod nima uchun?"); }
    if (H.kat == null) { royxatOch("kat"); return xabar("Kategoriyani tanlang"); }
    const tana = {
      kimning: H.kimning, tur: H.tur, kim_toladi: H.toladi, karta_id: H.karta,
      turi_id: H.ichki ?? H.kat, summa: H.summa, sabab: H.sabab.trim(),
    };
    const t = $("#rxSaqla"); t.disabled = true;
    try {
      const j = NAMUNA ? { id: Date.now() } : await api("rasxod", tana);
      yop(); tebran("ok"); xabar("Rasxod saqlandi ✅");
      window.dispatchEvent(new CustomEvent("rasxod-saqlandi", { detail: { id: j.id } }));
    } catch (err) { xabar(err.message); tebran("rigid"); }
    finally { t.disabled = false; }
  }

  window.rasxodOch = och;
  window.rasxodYop = yop;
  if (location.hash === "#rasxod") (document.readyState === "loading"
    ? document.addEventListener("DOMContentLoaded", och) : och());
})();
