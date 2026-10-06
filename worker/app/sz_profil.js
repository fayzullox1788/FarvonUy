// Sozlamalar → «Profil», «Uy a’zolari», «Bildirishnomalar», «Ilova sozlamalari».
// index.html yordamchilari ustida: api(), NAMUNA, INIT, tg, xabar(), tebran(), e().
// API: worker/src/miniapp_sz_profil.js (/app/api/profil*). Har bo'lim — Sozlamalar
// ustidagi to'liq ekran (← va Telegram BackButton), manzil #sozlamalar/<kalit>.
//
// Tahrirlanadi: O'Z ismi va O'Z Telegram nomi (odam qatori — jurnal orqali desktopga
// boradi). Bot, uborka, dars sozlamalari va asosiy odam FAQAT ko'rsatiladi: ular
// desktopniki (src/sinx.py) — desktop har sinxronda o'z qiymatini yuborib, bu
// yerdagi o'zgarishni bosib ketardi.
(() => {
  const BOLIM = {
    profil: "Profil",
    azolar: "Uy a’zolari",
    bildirishnoma: "Bildirishnomalar",
    ilova: "Ilova sozlamalari",
  };
  const XESH = /^#sozlamalar\/(profil|azolar|bildirishnoma|ilova)$/;
  const S = () => document.getElementById("sahifa-sozlamalar");

  const IK = {
    orqa: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 12h-15M10.5 5.5 4 12l6.5 6.5"/></svg>`,
    qalam: `<svg class="qalam" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/></svg>`,
    x: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>`,
    qulf: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="4.5" y="10.5" width="15" height="10" rx="2.2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/></svg>`,
    info: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8h.01"/></svg>`,
    ogoh: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5 2.5 20h19L12 3.5Z"/><path d="M12 10v4.5M12 17.5h.01"/></svg>`,
    qongiroq: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9a6 6 0 0 1 12 0c0 6 2.5 7.5 2.5 7.5h-17S6 15 6 9"/><path d="M10 20a2.2 2.2 0 0 0 4 0"/></svg>`,
    uy: `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"><path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 8.6V20a1 1 0 0 0 1 1H10v-6h4v6h3.5a1 1 0 0 0 1-1V8.6"/></svg>`,
    sinx: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11a8 8 0 0 0-14.3-4.5L4 8.5M4 4v4.5h4.5"/><path d="M4 13a8 8 0 0 0 14.3 4.5l1.7-2M20 20v-4.5h-4.5"/></svg>`,
  };

  // ── Namuna (file://) ───────────────────────────────────────────────
  function namuna() {
    const h = new Date();
    const p = (n) => String(n).padStart(2, "0");
    const st = (d) => `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:00`;
    return {
      ok: true, men_id: 1, tg_username: "fsultonoov",
      azolar: [
        { id: 1, nom: "Fayzulloxon", rang: "#4A40BE", telegram: "fsultonoov", dm: "yoqilgan", faol: true, asosiy: true, men: true },
        { id: 2, nom: "Otabek", rang: "#0D7490", telegram: "Otabek_33", dm: "start_kerak", faol: true, asosiy: false, men: false },
        { id: 3, nom: "Behruz", rang: "#B0421F", telegram: "behruz_o", dm: "yoqilgan", faol: true, asosiy: false, men: false },
        { id: 4, nom: "Sardor", rang: "#9C2C74", telegram: null, dm: "nom_yoq", faol: false, asosiy: false, men: false },
      ],
      bildirishnoma: {
        sozlangan: true, yoqilgan: true, token_bor: true, guruh_bor: true, guruh_nomi: "Farovon oila",
        kunlik_vaqt: "07:30", kechiktirish: [10, 30, 60], dm_yoqmaganlar: ["Otabek"],
      },
      ilova: {
        versiya: "2026.10.02", hozir: st(h),
        desktop_oxirgi: st(new Date(h - 47 * 60000)), desktop_soni: 18420,
        server_oxirgi: st(new Date(h - 6 * 60000)),
        uborka: { kun: 6, kun_nomi: "Yakshanba", vaqt: "10:00", ishlar: ["Oshxonani tozalash", "Sanuzelni tozalash", "Uyni tozalash"] },
        dars: { yoq: true, sinf: "11-A", odam: "Behruz", tekshirildi: st(new Date(h - 25 * 60000)) },
      },
    };
  }

  // ── Holat ──────────────────────────────────────────────────────────
  let ochiq = null;      // joriy bo'lim kaliti
  let M = null;          // serverdan kelgan ma'lumot
  let xatoMatn = "";
  let yuklanmoqda = false;
  let varaq = null;      // pastdan oyna: {t:"nom", xato}
  let band = false;

  const el = document.createElement("div");
  el.className = "szp-ekran"; el.hidden = true; el.setAttribute("role", "dialog");
  document.body.appendChild(el);

  const men = () => M && M.azolar.find((a) => a.men);
  const harf = (nom) => (String(nom || "?").trim()[0] || "?").toUpperCase();
  const tgNom = (t) => t ? "@" + t : "";

  // ── Vaqt ───────────────────────────────────────────────────────────
  const OY = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];
  const sanaOl = (s) => { const m = /^(\d{4})-(\d\d)-(\d\d)[ T](\d\d):(\d\d)/.exec(s || ""); return m ? m.slice(1).map(Number) : null; };
  function qachon(s) {
    const a = sanaOl(s); if (!a) return "—";
    const b = sanaOl(M?.ilova?.hozir) || null;
    const daq = b ? Math.round((Date.UTC(b[0], b[1] - 1, b[2], b[3], b[4]) - Date.UTC(a[0], a[1] - 1, a[2], a[3], a[4])) / 60000) : null;
    const soat = `${String(a[3]).padStart(2, "0")}:${String(a[4]).padStart(2, "0")}`;
    if (daq != null && daq >= 0) {
      if (daq < 1) return "hozirgina";
      if (daq < 60) return `${daq} daqiqa oldin`;
      if (daq < 24 * 60 && a[2] === b[2]) return `bugun, ${soat}`;
      if (daq < 48 * 60) { const k = new Date(Date.UTC(b[0], b[1] - 1, b[2] - 1)); if (k.getUTCDate() === a[2]) return `kecha, ${soat}`; }
    }
    return `${a[2]}-${OY[a[1] - 1]}, ${soat}`;
  }
  const daqMatn = (m) => m < 60 ? `${m} daq` : (m % 60 ? `${Math.floor(m / 60)} soat ${m % 60} daq` : `${m / 60} soat`);

  // ── Kichik bo'laklar ───────────────────────────────────────────────
  const chip = (matn, rang = "", nuqta = true) => `<span class="szp-chip ${rang}">${nuqta ? "<i></i>" : ""}${matn}</span>`;
  const qator = (yor, qiy, { izoh = "", tugma = "", bos = "" } = {}) =>
    `<${bos ? `button data-p="${bos}"` : "div"} class="szp-q"><span class="yor">${yor}${izoh ? `<small>${izoh}</small>` : ""}</span>${qiy}${tugma}</${bos ? "button" : "div"}>`;
  const qiymat = (m) => `<span class="qiy">${m}</span>`;
  const izohQuti = (matn, tur = "") => `<div class="szp-izoh ${tur}">${tur === "sariq" ? IK.ogoh : tur === "qulf" ? IK.qulf : IK.info}<div>${matn}</div></div>`;
  const DESKTOPDA = izohQuti("Bu sozlamalar <b>desktop dasturida o‘zgartiriladi</b>. Desktop har sinxronda o‘z qiymatini yuboradi, shuning uchun bu yerda faqat ko‘rinadi.", "qulf");

  function dmChip(dm) {
    if (dm === "yoqilgan") return chip("Yoqilgan", "yashil");
    if (dm === "start_kerak") return chip("/start kutilmoqda", "sariq");
    return chip("Telegram nomi yo‘q");
  }
  const dmMatn = (dm) => dm === "yoqilgan" ? "Xabar yoqilgan" : dm === "start_kerak" ? "/start bosmagan" : "Telegram yo‘q";
  const dmRang = (dm) => dm === "yoqilgan" ? "#22c27a" : dm === "start_kerak" ? "#f0a020" : "#b8c0cc";

  // ── Ekranlar ───────────────────────────────────────────────────────
  function profilEkran() {
    const o = men();
    if (!o) return `<div class="sz-royxat"><div class="sz-bosh-holat">Profil topilmadi</div></div>`;
    const un = M.tg_username;
    const boglash = un && un !== o.telegram;
    return `<div class="szp-kim">
        <div class="szp-avatar" style="background:${o.rang}">${e(harf(o.nom))}</div>
        <b>${e(o.nom)}</b>
        <span class="tg">${o.telegram ? e(tgNom(o.telegram)) : "Telegram nomi kiritilmagan"}</span>
        <div class="szp-chiplar">${o.asosiy ? chip("Asosiy odam", "binafsha", false) : ""}${chip(o.dm === "yoqilgan" ? "Shaxsiy xabarlar yoqilgan" : "Shaxsiy xabarlar yoqilmagan", o.dm === "yoqilgan" ? "yashil" : "sariq")}</div>
      </div>
      <div class="szp-sar">Ma’lumotlar</div>
      <div class="szp-karta">
        ${qator("Ism", qiymat(e(o.nom)), { bos: "nom", tugma: IK.qalam })}
        ${qator("Telegram", qiymat(o.telegram ? e(tgNom(o.telegram)) : "—"), {
          izoh: boglash ? `Telegram’dagi nomingiz: @${e(un)}` : "",
          tugma: boglash ? `<button class="szp-kichik-tugma" data-p="tg"${band ? " disabled" : ""}>${o.telegram ? "Yangilash" : "Bog‘lash"}</button>` : "" })}
        ${qator("Shaxsiy xabarlar", dmChip(o.dm), { izoh: o.dm === "yoqilgan" ? "Bot sizga shaxsiy vazifalarni yozadi" : "Shaxsiy vazifalar yuborilmaydi" })}
        ${qator("Rang", `<span class="szp-rang" style="background:${o.rang}"></span>`, { izoh: "Desktopdagi rang bilan bir xil" })}
      </div>
      ${o.dm !== "yoqilgan" ? izohQuti(o.telegram
        ? "Bot sizga shaxsiy yoza olishi uchun Telegram’da botni ochib <b>/start</b> bosing — Telegram bot o‘zi birinchi yozishiga ruxsat bermaydi."
        : "Avval Telegram nomingizni bog‘lang, keyin botga <b>/start</b> bosing.", "sariq") : ""}
      ${izohQuti("Yangi ism desktop dasturida ham keyingi sinxronda ko‘rinadi. Hisob, qarz va ulushlar o‘zgarmaydi.")}`;
  }

  function azoQator(a) {
    return `<div class="szp-azo${a.faol ? "" : " nofaol"}">
      <div class="av" style="background:${a.rang}">${e(harf(a.nom))}</div>
      <div class="ich">
        <b><span>${e(a.nom)}</span>${a.men ? `<em class="siz">Siz</em>` : ""}${a.asosiy ? `<em class="siz asos">Asosiy</em>` : ""}</b>
        <small>${a.telegram ? `<span>${e(tgNom(a.telegram))}</span> · ` : ""}${a.faol ? `<span class="nuq" style="background:${dmRang(a.dm)}"></span>${dmMatn(a.dm)}` : "Ro‘yxatdan olingan"}</small>
      </div>
    </div>`;
  }
  function azolarEkran() {
    const faol = M.azolar.filter((a) => a.faol), nofaol = M.azolar.filter((a) => !a.faol);
    return `<div class="szp-holat"><div class="ik navy">${IK.uy}</div><div><b>${faol.length} kishi</b><small>Uy hisobi va vazifalar shu a’zolar orasida bo‘linadi</small></div></div>
      <div class="szp-sar">Faol a’zolar <span>${faol.length}</span></div>
      <div class="szp-karta">${faol.map(azoQator).join("")}</div>
      ${nofaol.length ? `<div class="szp-sar">Nofaol <span>${nofaol.length}</span></div><div class="szp-karta">${nofaol.map(azoQator).join("")}</div>` : ""}
      ${izohQuti("<b>Asosiy odam</b> — yon paneldagi «Qo‘ldagi pul» kimniki va rejaga yetmagan pulni kim qoplashi. Desktop Sozlamalarida tanlanadi.")}
      ${izohQuti("A’zo qo‘shish va ro‘yxatdan olish <b>desktop dasturida</b> — bu balans va ulushlarga ta’sir qiladi, shuning uchun telefondan qilinmaydi.", "qulf")}`;
  }

  function bildirishnomaEkran() {
    const b = M.bildirishnoma;
    const [ik, sar, iz] = b.sozlangan
      ? ["yashil", "Bot ishlayapti", `Har kuni ${e(b.kunlik_vaqt)} da guruhga kunlik ro‘yxat`]
      : !b.token_bor || !b.guruh_bor ? ["kul", "Bot sozlanmagan", "Token va guruh desktop dasturida kiritiladi"]
      : ["sariq", "Bildirishnomalar o‘chirilgan", "Guruhga xabar va eslatmalar yuborilmaydi"];
    return `<div class="szp-holat"><div class="ik ${ik}">${IK.qongiroq}</div><div><b>${sar}</b><small>${iz}</small></div></div>
      <div class="szp-sar">Telegram bot</div>
      <div class="szp-karta">
        ${qator("Bildirishnomalar", b.yoqilgan ? chip("Yoqilgan", "yashil") : chip("O‘chirilgan"))}
        ${qator("Kunlik xabar vaqti", qiymat(e(b.kunlik_vaqt || "—")), { izoh: "Guruhga bugungi vazifalar ro‘yxati" })}
        ${qator("Kechiktirish", `<span class="szp-chiplar">${b.kechiktirish.map((m) => chip(daqMatn(m), "kok", false)).join("")}</span>`, { izoh: "«Hali yo‘q» tugmasi" })}
        ${qator("Guruh", qiymat(b.guruh_bor ? e(b.guruh_nomi || "Ulangan") : "Ulanmagan"))}
      </div>
      ${DESKTOPDA}
      <div class="szp-sar">Shaxsiy xabarlar</div>
      <div class="szp-karta">${M.azolar.filter((a) => a.faol).map((a) =>
        qator(`${e(a.nom)}${a.men ? " <span class=\"szp-sanoq\">(siz)</span>" : ""}`, dmChip(a.dm), { izoh: a.telegram ? e(tgNom(a.telegram)) : "" })).join("")}</div>
      ${b.dm_yoqmaganlar.length
        ? izohQuti(`${b.dm_yoqmaganlar.map(e).join(", ")} botga hali <b>/start</b> bosmagan — shaxsiy vazifalari na shaxsan, na guruhga yuboriladi.`, "sariq")
        : ""}`;
  }

  function ilovaEkran() {
    const i = M.ilova;
    const tgv = window.Telegram && Telegram.WebApp && Telegram.WebApp.version;
    const tgp = window.Telegram && Telegram.WebApp && Telegram.WebApp.platform;
    const u = i.uborka, d = i.dars;
    return `<div class="szp-holat"><div class="ik navy">${IK.uy}</div><div><b>Farovon Hayot</b><small>Versiya ${e(i.versiya)}${tgv && tgp && tgp !== "unknown" ? ` · Telegram ${e(tgv)} (${e(tgp)})` : ""}</small></div></div>
      <div class="szp-sar">Sinxron</div>
      <div class="szp-karta">
        ${qator("Desktop", qiymat(i.desktop_oxirgi ? qachon(i.desktop_oxirgi) : "Hali yo‘q"), { izoh: "Oxirgi kelgan o‘zgarish" })}
        ${qator("Bot va Mini App", qiymat(i.server_oxirgi ? qachon(i.server_oxirgi) : "Hali yo‘q"), { izoh: "Oxirgi o‘zgarish" })}
      </div>
      <div class="szp-izoh">${IK.sinx}<div><b>Desktop bilan sinxron.</b> Asosiy baza serverda. Desktop dasturi o‘z nusxasida ishlaydi va internet bo‘lganda o‘zgarishlarni yuboradi va oladi. Bot va bu ilovadagi o‘zgarishlar desktopga keyingi sinxronda tushadi; desktop yopiq bo‘lsa ham bot ishlayveradi.</div></div>
      <div class="szp-sar">General uborka</div>
      <div class="szp-karta">
        ${qator("Kun", qiymat(e(u.kun_nomi)))}
        ${qator("Vaqt", qiymat(e(u.vaqt)))}
        ${qator("Ishlar", qiymat(u.ishlar.length ? `${u.ishlar.length} ta` : "—"), { izoh: u.ishlar.map(e).join(", ") })}
      </div>
      <div class="szp-sar">Dars jadvali</div>
      <div class="szp-karta">
        ${qator("Holat", d.yoq ? chip("Yoqilgan", "yashil") : chip("O‘chirilgan"))}
        ${d.yoq || d.sinf ? qator("Guruh / sinf", qiymat(e(d.sinf || "—"))) : ""}
        ${d.yoq || d.odam ? qator("Kimning kalendari", qiymat(e(d.odam || "—"))) : ""}
        ${d.tekshirildi ? qator("Oxirgi tekshiruv", qiymat(qachon(d.tekshirildi))) : ""}
      </div>
      ${DESKTOPDA}`;
  }

  function skelet() {
    return `<div class="szp-skelet"><div class="sz-skelet katta"></div><div class="sz-royxat">${"<div class=\"sz-skelet\"></div>".repeat(4)}</div></div>`;
  }

  function chiz() {
    if (!ochiq) return;
    const tana = xatoMatn && !M
      ? `<div class="sz-royxat" style="margin-top:14px"><div class="sz-bosh-holat">${e(xatoMatn)}<br><button data-p="qayta">Qayta urinish</button></div></div>`
      : !M ? skelet()
      : ochiq === "profil" ? profilEkran() : ochiq === "azolar" ? azolarEkran()
      : ochiq === "bildirishnoma" ? bildirishnomaEkran() : ilovaEkran();
    el.innerHTML = `<div class="sz-bosh ichki"><button class="sz-orqa" data-p="orqa" aria-label="Orqaga">${IK.orqa}</button><h1>${BOLIM[ochiq]}</h1></div>${tana}`;
  }

  // ── Ma'lumot ───────────────────────────────────────────────────────
  async function yukla() {
    if (NAMUNA) { if (!M) M = namuna(); chiz(); return; }
    if (!INIT) { xatoMatn = "Bu sahifani Telegram'dagi Farovon Hayot botidan oching."; chiz(); return; }
    if (yuklanmoqda) return;
    yuklanmoqda = true;
    try { M = await api("profil"); xatoMatn = ""; }
    catch (err) { xatoMatn = err.message; if (M) xabar(err.message); }
    yuklanmoqda = false;
    chiz();
  }

  // ── Ochish / yopish, manzil, BackButton ────────────────────────────
  const TB = window.Telegram && Telegram.WebApp && Telegram.WebApp.BackButton;
  function tbKor(k) { if (!TB) return; try { k ? TB.show() : TB.hide(); } catch (err) {} }
  function xeshQoy(h) { if (location.hash !== h) { try { history.replaceState(null, "", h); } catch (err) {} } }

  function och(k) {
    if (!BOLIM[k]) return;
    const yangi = ochiq !== k;
    ochiq = k;
    el.hidden = false;
    if (yangi) { el.classList.remove("kir"); void el.offsetWidth; el.classList.add("kir"); el.scrollTop = 0; }
    chiz();
    xeshQoy("#sozlamalar/" + k);
    tbKor(true);
    yukla();
  }
  function yop({ xesh = true } = {}) {
    if (!ochiq) return;
    varaqYop(true);
    ochiq = null; el.hidden = true; el.innerHTML = "";
    if (xesh && XESH.test(location.hash)) xeshQoy("#sozlamalar");
    tbKor(false);
  }
  function orqa() { if (varaq) return varaqYop(); yop(); }

  window.SozlamaBolimi = window.SozlamaBolimi || {};
  Object.keys(BOLIM).forEach((k) => { window.SozlamaBolimi[k] = () => och(k); });

  if (TB) { try { TB.onClick(() => { if (ochiq) orqa(); }); } catch (err) {} }

  // sozlama.js o'z ekranini qayta chizganda manzil va BackButton'ni o'ziga qaytaradi —
  // bo'lim ochiq tursa ularni tiklaymiz.
  const sz = S();
  if (sz) new MutationObserver(() => { if (ochiq) { xeshQoy("#sozlamalar/" + ochiq); tbKor(true); } }).observe(sz, { childList: true });

  window.addEventListener("sahifa", (ev) => { if (ev.detail?.nom !== "sozlamalar") yop({ xesh: false }); });
  // hashchange'ni sozlama.js darhol qayta yozadi — yangi manzilni hodisaning o'zidan olamiz.
  window.addEventListener("hashchange", (ev) => {
    const h = "#" + String(ev.newURL || "").split("#")[1];
    const m = XESH.exec(h);
    if (m) setTimeout(() => och(m[1]), 0);
    else if (ochiq && !XESH.test(location.hash)) yop({ xesh: false });
  });
  document.addEventListener("visibilitychange", () => { if (!document.hidden && ochiq && !NAMUNA && INIT && !varaq) yukla(); });

  // Boshlang'ich havola: sozlama.js bu fayldan oldin yuklanib, xeshni allaqachon
  // qayta yozgan bo'lishi mumkin — shuning uchun navigatsiyadagi asl manzil ham.
  let boshXesh = location.hash;
  if (!XESH.test(boshXesh)) {
    try { const n = performance.getEntriesByType("navigation")[0]; if (n && n.name.includes("#")) boshXesh = "#" + n.name.split("#")[1]; } catch (err) {}
  }
  const bm = XESH.exec(boshXesh);
  if (bm && sz && !sz.hidden) och(bm[1]);

  // ── Ism o'zgartirish oynasi (pastdan) ──────────────────────────────
  let parda, oyna;
  function oynaEl() {
    if (oyna) return;
    parda = document.createElement("div"); parda.className = "sz-parda";
    oyna = document.createElement("div"); oyna.className = "sz-oyna"; oyna.setAttribute("role", "dialog");
    document.body.append(parda, oyna);
    parda.onclick = () => varaqYop();
    oyna.addEventListener("click", oynaBosildi);
    oyna.addEventListener("submit", (ev) => { ev.preventDefault(); nomSaqla(); });
  }
  function varaqOch(v) {
    oynaEl(); varaq = v;
    const o = men();
    oyna.innerHTML = `<div class="sz-oyna-bosh"><h3>Ismni o‘zgartirish</h3><button class="sz-yop" data-p="yop" aria-label="Yopish">${IK.x}</button></div>
      <form autocomplete="off">
        <label class="sz-yorliq" for="szpNom">Ism</label>
        <input class="sz-kirit" id="szpNom" maxlength="40" value="${e(o ? o.nom : "")}" enterkeyhint="done">
        <p class="sz-izoh" id="szpXato" style="${v.xato ? "color:var(--qizil)" : ""}">${e(v.xato || "Boshqa a’zolar va desktop dasturida ham shu ism ko‘rinadi.")}</p>
        <div class="sz-ikki"><button type="button" class="sz-kulrang-tugma" data-p="yop">Bekor qilish</button>
          <button type="submit" class="sz-kok-tugma" id="szpSaqla">Saqlash</button></div>
      </form>`;
    requestAnimationFrame(() => { parda.classList.add("ochiq"); oyna.classList.add("ochiq"); });
    setTimeout(() => { const i = document.getElementById("szpNom"); if (i) { i.focus(); i.select(); } }, 260);
  }
  function varaqYop(jim = false) {
    if (!varaq) return;
    varaq = null;
    if (oyna) { parda.classList.remove("ochiq"); oyna.classList.remove("ochiq"); }
    if (!jim) tbKor(!!ochiq);
  }
  function oynaBosildi(ev) {
    const t = ev.target.closest("[data-p]"); if (!t) return;
    if (t.dataset.p === "yop") varaqYop();
  }
  function xatoKor(m) {
    const p = document.getElementById("szpXato");
    if (p) { p.textContent = m; p.style.color = "var(--qizil)"; }
  }
  async function nomSaqla() {
    if (band) return;
    const nom = (document.getElementById("szpNom")?.value || "").trim();
    const o = men(); if (!o) return;
    if (!nom) return xatoKor("Ism bo‘sh bo‘lmasin");
    if (nom === o.nom) return varaqYop();
    if (M.azolar.some((a) => a.id !== o.id && a.nom === nom)) return xatoKor(`${nom} allaqachon bor`);
    band = true;
    const tugma = document.getElementById("szpSaqla"); if (tugma) tugma.disabled = true;
    try {
      if (!NAMUNA) await api("profil/nom", { nom });
      o.nom = nom;
      varaqYop(); chiz(); tebran("soft"); xabar("Ism saqlandi");
    } catch (err) {
      xatoKor(err.message);
      if (tugma) tugma.disabled = false;
    }
    band = false;
  }
  async function tgBogla() {
    const o = men(); if (!o || band || !M.tg_username) return;
    band = true; chiz();
    try {
      const j = NAMUNA ? { telegram: M.tg_username } : await api("profil/telegram", {});
      o.telegram = j.telegram;
      tebran("soft"); xabar("Telegram nomi saqlandi");
    } catch (err) { xabar(err.message); }
    band = false; chiz();
  }

  // ── Hodisalar ──────────────────────────────────────────────────────
  el.addEventListener("click", (ev) => {
    const t = ev.target.closest("[data-p]"); if (!t) return;
    const p = t.dataset.p;
    if (p === "orqa") return orqa();
    if (p === "qayta") { xatoMatn = ""; chiz(); return yukla(); }
    if (p === "nom" && men()) { tebran("soft"); return varaqOch({ t: "nom" }); }
    if (p === "tg") return tgBogla();
  });
})();
