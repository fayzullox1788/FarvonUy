// «Sozlamalar» sahifasi va kategoriyalarni boshqarish — index.html dagi umumiy
// yordamchilar ustida: api(), NAMUNA, INIT, tg, xabar(), tebran(), e(), $().
// API: worker/src/miniapp_sozlama.js (/app/api/kategoriya*). Qoidalar desktopniki
// (core/mahsulot.py): ichki kategoriyaga bo'sh ikonka majburiy, bitta ikonka — bitta
// faol kategoriya, ichida faol ichki kategoriya yoki mahsulot bo'lsa o'chmaydi.
// Ekranlar — sahifa ichidagi stek (← va Telegram BackButton), manzil:
//   #sozlamalar · #sozlamalar/kategoriyalar · #sozlamalar/kat/<id> · …/yangi ·
//   …/tahrir · …/ochir · …/iconlar  (skrinshot va to'g'ridan-to'g'ri havola uchun).
(() => {
  const ILOVA = location.protocol === "file:" ? "" : "/app/";
  const S = () => document.getElementById("sahifa-sozlamalar");
  const korinadimi = () => !S().hidden;

  // Ikonkalar katalogi: kalit:Fluent nomi (packaging/belgi_xarita.json) — faqat qidiruv
  // uchun, ekranga chiqmaydi (ikonkalar NOMSIZ). Python kategoriya.belgilar() bilan
  // bir xilligi test/miniapp_sozlama.test.js da tekshiriladi.
  const KATALOG = "education_01:closed_book,education_02:bookmark,education_03:graduation_cap,education_04:identification_card,education_05:compass,education_06:microscope,education_07:ringed_planet,education_09:musical_notes,education_10:artist_palette,education_11:basketball,education_12:open_book,education_13:fork_and_knife,education_14:softball,education_15:chart_increasing,entertainment_01:ghost,entertainment_02:hotel,entertainment_03:mirror_ball,entertainment_04:microphone,entertainment_05:puzzle_piece,entertainment_06:chequered_flag,entertainment_07:radio,entertainment_08:clapper_board,entertainment_09:video_game,entertainment_10:headphone,entertainment_11:airplane,entertainment_12:robot,entertainment_13:chess_pawn,entertainment_14:bowling,entertainment_15:hiking_boot,finance_01:repeat_button,finance_02:bar_chart,finance_03:dollar_banknote,finance_04:bank,finance_05:coin,finance_06:mobile_phone_with_arrow,finance_07:credit_card,finance_08:shield,finance_09:scroll,finance_10:purse,food_01:flatbread,food_02:paw_prints,food_03:rice_ball,food_04:jar,food_05:fish,food_06:hamburger,food_07:egg,food_08:cheese_wedge,food_09:hatching_chick,food_10:hot_pepper,food_11:sheaf_of_rice,food_12:ice_cream,food_13:tangerine,food_14:droplet,food_15:curry_rice,food_16:cocktail_glass,food_17:steaming_bowl,food_18:shrimp,food_19:clinking_glasses,food_20:lemon,food_21:chestnut,food_22:soft_ice_cream,food_23:avocado,food_24:tropical_fish,food_25:beer_mug,food_26:bottle_with_popping_cork,food_27:cooking,food_28:olive,food_29:sandwich,health_01:syringe,health_02:medical_symbol,health_03:manual_wheelchair,health_04:stethoscope,health_05:ambulance,health_06:tooth,health_07:face_with_medical_mask,health_09:adhesive_bandage,health_10:anatomical_heart,health_11:beating_heart,health_12:test_tube,health_13:bone,health_14:hospital,health_15:thermometer,health_16:kitchen_knife,health_17:framed_picture,life_01:hot_beverage,life_02:flashlight,life_03:bathtub,life_04:television,life_05:deciduous_tree,life_06:money_with_wings,life_07:umbrella,life_08:bucket,life_09:camera,life_10:bed,life_11:chair,life_12:door,life_13:candle,life_14:house_with_garden,life_15:pick,life_16:basket,life_17:abacus,life_18:barber_pole,life_19:wind_face,life_20:thread,office_01:globe_with_meridians,office_02:megaphone,office_03:telephone_receiver,office_04:briefcase,office_05:floppy_disk,office_06:inbox_tray,office_07:paperclip,office_08:antenna_bars,office_09:calendar,office_10:printer,office_11:desktop_computer,office_12:pencil,office_13:ticket,others_01:telescope,others_02:lotus,others_03:envelope,others_04:receipt,others_05:computer_disk,others_06:rosette,others_07:military_medal,others_08:balance_scale,others_09:books,others_10:gear,others_11:spiral_notepad,others_12:speech_balloon,others_13:pushpin,others_14:play_button,others_15:butterfly,others_16:baby_bottle,others_17:factory,personal_01:teddy_bear,personal_02:stopwatch,personal_03:fire,personal_04:guitar,personal_05:blossom,personal_06:brain,personal_07:couch_and_lamp,personal_08:womans_clothes,personal_09:kite,personal_10:seedling,shopping_01:shopping_bags,shopping_02:billed_cap,shopping_03:tulip,shopping_04:socks,shopping_05:high-heeled_shoe,shopping_06:dress,shopping_07:mans_shoe,shopping_08:lotion_bottle,shopping_09:necktie,shopping_10:jeans,shopping_11:coat,shopping_12:gem_stone,shopping_13:watch,shopping_14:glasses,shopping_15:lipstick,shopping_16:label,shopping_17:gloves,shopping_18:notebook,shopping_19:handbag,sports_01:goggles,sports_02:bullseye,sports_03:flag_in_hole,sports_04:crossed_swords,sports_05:rescue_workers_helmet,sports_06:running_shoe,sports_07:badminton,sports_08:ping_pong,sports_09:baseball,sports_10:soccer_ball,sports_11:volleyball,sports_12:bicycle,sports_13:person_lifting_weights,sports_14:tennis,sports_15:person_in_lotus_position,sports_16:skis,sports_17:boxing_glove,transportation_01:p_button,transportation_02:train,transportation_03:motorway,transportation_04:sailboat,transportation_05:electric_plug,transportation_06:motorcycle,transportation_07:wheel,transportation_08:delivery_truck,transportation_09:metro,transportation_10:fuel_pump,travel_01:luggage,travel_02:palm_tree,travel_03:balloon,travel_04:aerial_tramway,travel_05:snow-capped_mountain,travel_06:cityscape,travel_07:round_pushpin,travel_08:desert_island";
  // kategoriya.GURUH_NOMI — guruh sarlavhalari (ikonka nomi emas).
  const GURUH_NOMI = {"education": "Ta'lim", "entertainment": "Ko'ngilochar", "finance": "Moliya", "food": "Oziq-ovqat", "health": "Salomatlik", "life": "Turmush", "office": "Ofis", "others": "Boshqalar", "personal": "Shaxsiy", "shopping": "Xarid", "sports": "Sport", "transportation": "Transport", "travel": "Sayohat"};
  // Taklif tartibi — miniapp_sozlama.js dagi GURUH_TARTIB/QOSHNI bilan bir xil.
  const GURUH_TARTIB = ["food", "life", "transportation", "shopping", "health", "education",
    "entertainment", "personal", "finance", "sports", "travel", "office", "others"];
  const QOSHNI = {
    food: ["shopping", "life", "health"], life: ["shopping", "personal", "food"],
    transportation: ["travel", "finance", "life"], shopping: ["life", "food", "personal"],
    health: ["personal", "sports", "food"], education: ["office", "others", "entertainment"],
    entertainment: ["sports", "travel", "personal"], personal: ["life", "health", "shopping"],
    finance: ["office", "shopping", "others"], sports: ["health", "entertainment", "travel"],
    travel: ["transportation", "entertainment", "sports"], office: ["education", "finance", "others"],
    others: ["life", "office", "personal"],
  };
  const PASTEL = {
    food: "#fff0e6", life: "#e8f0ff", transportation: "#e3f5ec", shopping: "#f1ebff", health: "#ffebee",
    education: "#ebe9ff", entertainment: "#f0e9ff", personal: "#ffedf5", finance: "#e5f5ea",
    sports: "#e6f3ff", travel: "#e2f5f3", office: "#edf1f6", others: "#eff1f4",
  };
  const guruh = (f) => f.slice(0, f.lastIndexOf("_"));
  const BELGILAR = KATALOG.split(",").map((x) => {
    const [k, soz] = x.split(":");
    const g = guruh(k);
    return { fayl: k + ".png", kalit: k, guruh: g,
      qidir: `${soz.replace(/_/g, " ")} ${g} ${(GURUH_NOMI[g] || "").toLowerCase()}` };
  });
  const BELGI = new Map(BELGILAR.map((b) => [b.fayl, b]));
  const guruhNomi = (g) => GURUH_NOMI[g] || (g.charAt(0).toUpperCase() + g.slice(1));

  const IK = {
    orqa: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 12h-15M10.5 5.5 4 12l6.5 6.5"/></svg>`,
    ong: `<svg class="ong" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="m9.5 5.5 6.5 6.5-6.5 6.5"/></svg>`,
    plyus: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>`,
    qalam: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/><path d="M14 20h6"/></svg>`,
    savat: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M10 11v6M14 11v6"/><path d="M5.5 7l1 12a2 2 0 0 0 2 1.8h7a2 2 0 0 0 2-1.8l1-12"/><path d="M9 7V4.8a.8.8 0 0 1 .8-.8h4.4a.8.8 0 0 1 .8.8V7"/></svg>`,
    x: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>`,
    qidir: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/></svg>`,
    boshqa: `<svg class="ik" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/><rect x="3.5" y="13.5" width="7" height="7" rx="2"/><path d="M17 13.5v7M13.5 17h7" stroke-linecap="round"/></svg>`,
    yorliq: `<svg width="58%" height="58%" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="M3.5 12.2V4.5a1 1 0 0 1 1-1h7.7a1 1 0 0 1 .7.3l7.8 7.8a1 1 0 0 1 0 1.4l-7.7 7.7a1 1 0 0 1-1.4 0l-7.8-7.8a1 1 0 0 1-.3-.7Z"/><circle cx="8" cy="8" r="1.4"/></svg>`,
    ogoh: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5 2.5 20h19L12 3.5Z"/><path d="M12 10v4.5M12 17.5h.01"/></svg>`,
  };
  const ikon = (d) => `<svg class="ik" width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const MENYU = [
    ["profil", "Profil", ikon(`<circle cx="12" cy="8" r="4"/><path d="M4.5 20.5a7.5 7.5 0 0 1 15 0"/>`)],
    ["azolar", "Uy a’zolari", ikon(`<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20v-.5a5 5 0 0 1 5-5h3a5 5 0 0 1 5 5v.5"/><path d="M15.5 4.7a3.5 3.5 0 0 1 0 6.6M18.5 14.4a5 5 0 0 1 3 4.6v1"/>`)],
    ["kategoriyalar", "Kategoriyalar", ikon(`<rect x="3.5" y="3.5" width="17" height="7" rx="2"/><rect x="3.5" y="13.5" width="7" height="7" rx="2"/><rect x="13.5" y="13.5" width="7" height="7" rx="2"/><path d="M7 7h.01M17 7h-6"/>`)],
    ["vazifalar", "Vazifalar", ikon(`<rect x="4.5" y="4" width="15" height="17" rx="2.5"/><path d="M9 3v2.5h6V3M8.5 12.5l2.3 2.3 4.7-4.8"/>`)],
    ["mahsulotlar", "Mahsulotlar", ikon(`<path d="M3.5 8.5h17v10a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2v-10Z"/><path d="M3.5 8.5 5.5 4h13l2 4.5M12 4v4.5M9.5 12.5h5"/>`)],
    ["tolov", "Hamyon", ikon(`<rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="M2.5 10h19M6.5 15h4"/>`)],
    ["reja", "Reja (budget)", ikon(`<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M8 3v4M16 3v4M3.5 10h17"/><path d="M12 13v2.5l1.6 1"/>`)],
    ["bildirishnoma", "Bildirishnomalar", ikon(`<path d="M6 9a6 6 0 0 1 12 0c0 6 2.5 7.5 2.5 7.5h-17S6 15 6 9"/><path d="M10 20a2.2 2.2 0 0 0 4 0"/>`)],
    ["demo", "Demo rejim", ikon(`<rect x="3" y="4.5" width="18" height="12" rx="2"/><path d="M8.5 20.5h7M12 16.5v4M10 8.5l4 2-4 2Z"/>`)],
    ["ilova", "Ilova sozlamalari", ikon(`<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>`)],
  ];

  /** Kategoriya ikonkasi — doim `turi.rasm` (belgilar/<kalit>.svg), yo'q bo'lsa neytral. */
  function belgi(rasm, katta = false) {
    const b = rasm && BELGI.get(rasm);
    const cls = "sz-belgi" + (katta ? " katta" : "");
    if (!b) return `<span class="${cls}">${IK.yorliq}</span>`;
    return `<span class="${cls}" style="background:${PASTEL[b.guruh] || "#eef1f6"}"><img src="${ILOVA}belgilar/${b.kalit}.svg" alt="" decoding="async"></span>`;
  }

  // ── Namuna (file://) — dizayn namunasidagi daraxt ──────────────────
  function namunaDaraxt() {
    let id = 1;
    const t = (nom, rasm, bolalar = [], mahsulot = 0) => ({ id: id++, nom, rasm, ota_id: null, mahsulot, bolalar });
    const ildiz = [
      t("Oziq-ovqat", "food_17.png", [
        t("Meva-sabzavot", "food_10.png", [
          t("Mevalar", "food_11.png", [
            t("Olma", "food_23.png"), t("Limon", "food_20.png"), t("Mandarin", "food_13.png"),
            t("Zaytun", "food_28.png"), t("Kashtan", "food_21.png")]),
          t("Sabzavotlar", "personal_10.png")]),
        t("Go‘sht mahsulotlari", "food_27.png", [t("Baliq", "food_05.png")]),
        t("Sut va sut mahsulotlari", "food_08.png", [t("Tuxum", "food_07.png")], 3),
        t("Non va un mahsulotlari", "food_01.png", [t("Shirinliklar", "food_12.png")]),
        t("Ichimliklar", "food_26.png", [t("Choy va qahva", "life_01.png")]),
        t("Boshqa oziq-ovqat", "food_04.png")]),
      t("Uy-joy", "life_14.png", [t("Ijara", "life_12.png"), t("Kommunal", "transportation_05.png"),
        t("Ta’mirlash", "life_15.png"), t("Mebel", "life_11.png")]),
      t("Transport", "transportation_09.png", [t("Yoqilg‘i", "transportation_10.png"),
        t("Poyezd", "transportation_02.png"), t("Avtoturargoh", "transportation_01.png")]),
      t("Maishiy tovarlar", "life_08.png", [t("Gigiena", "life_03.png"), t("Tozalash", "life_16.png"),
        t("Oshxona jihozlari", "health_16.png"), t("Chiroqlar", "life_02.png"), t("Shamlar", "life_13.png")]),
      t("Sog‘liq", "health_11.png", [t("Dorilar", "health_01.png"), t("Shifokor", "health_04.png"),
        t("Tish", "health_06.png"), t("Tahlillar", "health_12.png")]),
      t("Ta’lim", "education_03.png", [t("Kitoblar", "education_12.png"), t("Kurslar", "education_15.png"),
        t("Kanselyariya", "office_12.png")]),
      t("Ko‘ngil ochish", "entertainment_09.png", [t("Kino", "entertainment_08.png"), t("Musiqa", "entertainment_10.png")]),
      t("Kiyim-kechak", "shopping_11.png", [t("Poyabzal", "shopping_07.png"), t("Ko‘ylak", "shopping_06.png"),
        t("Shim", "shopping_10.png"), t("Aksessuar", "shopping_13.png")]),
      t("Shaxsiy parvarish", "shopping_08.png", [t("Kosmetika", "shopping_15.png"), t("Sartaroshxona", "life_18.png"),
        t("Atir", "personal_05.png"), t("Soch parvarishi", "life_20.png")]),
      t("Boshqa", "others_13.png", [t("Sovg‘alar", "travel_03.png"), t("Xayriya", "others_06.png")]),
    ];
    id = 1; // oldindan tartib: Oziq-ovqat=1, Meva-sabzavot=2, Mevalar=3
    const ota = (x, o) => { x.id = id++; x.ota_id = o; x.bolalar.forEach((c) => ota(c, x.id)); };
    ildiz.forEach((x) => ota(x, null));
    return ildiz;
  }

  // ── Holat ──────────────────────────────────────────────────────────
  let daraxt = null;           // [{id, nom, rasm, ota_id, mahsulot, bolalar}]
  let bosh = [];               // tanlasa bo'ladigan (hech bir faol kategoriyada yo'q) ikonkalar
  const tugun = new Map();     // id → tugun
  let xatoMatn = "";
  let yuklanmoqda = false;
  let stek = [{ t: "bosh" }];  // ekranlar: bosh | royxat | kat{id}
  let varaq = null;            // oyna: forma{rejim, ota, id, nom, rasm} | icon{forma, guruh, q} | ochir{id}
  let kutilganXesh = null;     // daraxt yuklanmasdan ochilgan havola

  function indeksla() {
    tugun.clear();
    const yur = (x) => { tugun.set(x.id, x); x.bolalar.forEach(yur); };
    (daraxt || []).forEach(yur);
  }
  function qabul(j) {
    daraxt = j.daraxt; bosh = j.bosh; indeksla();
    // O'chgan kategoriya ekranida qolmaslik
    stek = stek.filter((s) => s.t !== "kat" || tugun.has(s.id));
  }

  async function yukla() {
    if (yuklanmoqda) return;
    if (NAMUNA) {
      if (!daraxt) {
        daraxt = namunaDaraxt(); indeksla();
        const band = new Set([...tugun.values()].map((x) => x.rasm).filter(Boolean));
        bosh = BELGILAR.map((b) => b.fayl).filter((f) => !band.has(f));
      }
      return kutilganXesh != null ? xeshniOch() : chiz();
    }
    if (!INIT) { xatoMatn = "Bu sahifani Telegram'dagi Farovon Uy botidan oching."; return chiz(); }
    yuklanmoqda = true;
    try { qabul(await api("kategoriya")); xatoMatn = ""; }
    catch (err) { xatoMatn = err.message; }
    yuklanmoqda = false;
    if (kutilganXesh != null) xeshniOch(); else chiz();
  }

  // ── Manzil (xesh) ──────────────────────────────────────────────────
  const joriy = () => stek[stek.length - 1];
  function xeshYoz() {
    const s = joriy();
    let h = "#sozlamalar";
    if (s.t === "royxat") h += "/kategoriyalar";
    if (s.t === "kat") h += "/kat/" + s.id;
    if (varaq) {
      const f = varaq.t === "icon" ? varaq.forma : varaq;
      if (f.t === "forma" && f.rejim === "yangi") h = (s.t === "kat" ? h : "#sozlamalar") + "/yangi";
      if (f.t === "forma" && f.rejim === "tahrir") h += "/tahrir";
      if (f.t === "ochir") h += "/ochir";
      if (varaq.t === "icon") h += "/iconlar";
    }
    if (location.hash !== h) { try { history.replaceState(null, "", h); } catch (err) {} }
  }
  function zanjir(id) {
    const z = [];
    for (let x = tugun.get(id); x; x = x.ota_id != null ? tugun.get(x.ota_id) : null) z.unshift({ t: "kat", id: x.id });
    return z;
  }
  function xeshniOch() {
    const h = kutilganXesh ?? location.hash;
    kutilganXesh = null;
    const q = h.replace(/^#/, "").split("/");
    if (q[0] !== "sozlamalar") return chiz();
    stek = [{ t: "bosh" }]; varaq = null;
    let qoldiq = q.slice(1).filter(Boolean);
    if (!daraxt && !xatoMatn && qoldiq.length && !(qoldiq.length === 1 && qoldiq[0] === "kategoriyalar")) {
      // Ma'lumot kelguncha — ro'yxat skeleti; kelgach shu havola ochiladi.
      kutilganXesh = h; stek.push({ t: "royxat" }); return chiz();
    }
    if (["kategoriyalar", "yangi", "iconlar"].includes(qoldiq[0])) {
      stek.push({ t: "royxat" });
      if (qoldiq[0] === "kategoriyalar") qoldiq = qoldiq.slice(1);
    } else if (qoldiq[0] === "kat") {
      stek.push({ t: "royxat" });
      const id = Number(qoldiq[1]);
      if (tugun.has(id)) stek.push(...zanjir(id));
      qoldiq = qoldiq.slice(2);
    }
    const s = joriy();
    const ota = s.t === "kat" ? s.id : null;
    if (qoldiq[0] === "yangi" || qoldiq[0] === "iconlar") {
      varaq = yangiForma(ota);
      if (qoldiq[0] === "iconlar" || qoldiq[1] === "iconlar") varaq = { t: "icon", forma: varaq, guruh: "barchasi", q: "" };
    } else if (s.t === "kat" && qoldiq[0] === "tahrir") {
      varaq = tahrirForma(s.id);
      if (qoldiq[1] === "iconlar") varaq = { t: "icon", forma: varaq, guruh: "barchasi", q: "" };
    } else if (s.t === "kat" && qoldiq[0] === "ochir") {
      varaq = { t: "ochir", id: s.id };
    }
    chiz();
  }

  // ── Ikonka takliflari (server bilan bir xil algoritm) ──────────────
  function taklif(royxat, otaRasm, n) {
    const g = new Map(GURUH_TARTIB.map((x) => [x, []]));
    for (const f of royxat) { const k = guruh(f); if (!g.has(k)) g.set(k, []); g.get(k).push(f); }
    if (otaRasm) {
      const k = guruh(otaRasm);
      return [...new Set([k, ...(QOSHNI[k] || []), ...g.keys()])].flatMap((x) => g.get(x) || []).slice(0, n);
    }
    const navbat = [...g.values()], natija = [];
    for (let i = 0; navbat.some((q) => q.length > i); i++) for (const q of navbat) if (q[i]) natija.push(q[i]);
    return natija.slice(0, n);
  }
  /** Shu formada tanlasa bo'ladigan ikonkalar: bo'shlari + (tahrirda) o'z ikonkasi. */
  function tanlanadigan(forma) {
    const o = forma.rejim === "tahrir" ? tugun.get(forma.id)?.rasm : null;
    const r = BELGILAR.map((b) => b.fayl).filter((f) => f === o || bosh.includes(f));
    return r;
  }
  function yangiForma(ota) { return { t: "forma", rejim: "yangi", ota, nom: "", rasm: null, xato: "" }; }
  function tahrirForma(id) {
    const x = tugun.get(id);
    return { t: "forma", rejim: "tahrir", id, ota: x.ota_id, nom: x.nom, rasm: x.rasm, xato: "" };
  }
  const chuqurlik = (id) => zanjir(id).length; // ildiz = 1

  // ── Chizish ────────────────────────────────────────────────────────
  function chiz() {
    if (!korinadimi()) return;
    const s = joriy();
    S().innerHTML = s.t === "bosh" ? boshEkran() : s.t === "royxat" ? royxatEkran() : katEkran(s.id);
    if (s.t === "bosh") hamyonJami();
    xeshYoz();
    oynaChiz();
    tgOrqa();
  }

  function boshEkran() {
    return `<div class="sz-bosh"><h1>Sozlamalar</h1></div>
      <div class="sz-menyu">${MENYU.map(([k, nom, ik]) =>
        `<button class="sz-menyu-q${k === "kategoriyalar" ? " faol" : ""}" data-menyu="${k}">${ik}<span>${nom}</span>${
          k === "tolov" ? `<em class="sz-menyu-qiymat" id="sz-hamyon-jami"></em>` : ""}${
          k === "demo" ? `<i class="sz-switch${window.FarvonDemo && window.FarvonDemo.yoqiq ? " on" : ""}" aria-hidden="true"></i>` : IK.ong}</button>`).join("")}</div>`;
  }
  /** «Hamyon» qatorida jami pul — sz_tolov.js dan (u hali yuklanmagan bo'lsa jim). */
  function hamyonJami() {
    const f = window.SozlamaJami;
    if (!f) return;
    f().then((m) => { const x = document.getElementById("sz-hamyon-jami"); if (x && m) x.textContent = m; }).catch(() => {});
  }

  function qatorlar(royxat) {
    return royxat.map((x) => `<button class="sz-q" data-kat="${x.id}">${belgi(x.rasm)}
      <span class="nom">${e(x.nom)}</span><span class="son">${x.bolalar.length}</span>${IK.ong}</button>`).join("");
  }
  function holatMatni() {
    if (xatoMatn) return `<div class="sz-royxat"><div class="sz-bosh-holat">${e(xatoMatn)}<br><button data-amal="qayta">Qayta urinish</button></div></div>`;
    if (!daraxt) return `<div class="sz-royxat">${"<div class=\"sz-skelet\"></div>".repeat(6)}</div>`;
    return "";
  }

  function royxatEkran() {
    return `<div class="sz-bosh"><button class="sz-orqa" data-amal="orqa" aria-label="Orqaga">${IK.orqa}</button><h1>Kategoriyalar</h1></div>
      <div style="margin-top:14px"><button class="sz-kok-tugma" data-amal="yangi">${IK.plyus}Kategoriya qo‘shish</button></div>
      ${holatMatni() || (daraxt.length
        ? `<div class="sz-royxat">${qatorlar(daraxt)}</div>`
        : `<div class="sz-royxat"><div class="sz-bosh-holat">Hali kategoriya yo‘q</div></div>`)}`;
  }

  function katEkran(id) {
    const x = tugun.get(id);
    if (!x) {
      return `<div class="sz-bosh ichki"><button class="sz-orqa" data-amal="orqa" aria-label="Orqaga">${IK.orqa}</button><h1>Kategoriya</h1></div>
        ${holatMatni() || `<div class="sz-royxat"><div class="sz-bosh-holat">Kategoriya topilmadi</div></div>`}`;
    }
    const n = x.bolalar.length;
    return `<div class="sz-bosh ichki">
        <button class="sz-orqa" data-amal="orqa" aria-label="Orqaga">${IK.orqa}</button>
        <h1>${e(x.nom)}</h1>
        <button class="sz-ikon-tugma" data-amal="tahrir" aria-label="Tahrirlash">${IK.qalam}</button>
        <button class="sz-ikon-tugma xavf" data-amal="ochir" aria-label="O‘chirish">${IK.savat}</button>
      </div>
      <div class="sz-xulosa">${belgi(x.rasm, true)}<div><b>${e(x.nom)}</b><small>${n} ta ichki kategoriya</small></div></div>
      <div class="sz-bolim">Ichki kategoriyalar</div>
      <button class="sz-och-tugma" data-amal="yangi">${IK.plyus}Ichki kategoriya qo‘shish</button>
      ${n ? `<div class="sz-royxat">${qatorlar(x.bolalar)}</div>`
        : `<div class="sz-royxat"><div class="sz-bosh-holat">Hali ichki kategoriya yo‘q</div></div>`}`;
  }

  // ── Oyna (pastdan) ─────────────────────────────────────────────────
  let parda, oyna;
  function oynaElementlari() {
    if (oyna) return;
    parda = document.createElement("div"); parda.className = "sz-parda";
    oyna = document.createElement("div"); oyna.className = "sz-oyna"; oyna.setAttribute("role", "dialog");
    document.body.append(parda, oyna);
    parda.onclick = () => yop();
    oyna.addEventListener("click", oynaBosildi);
    oyna.addEventListener("input", oynaKiritildi);
    oyna.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && ev.target.id === "szNom") { ev.preventDefault(); saqla(); } });
  }
  function yop() { varaq = null; oynaChiz(); xeshYoz(); tgOrqa(); }

  function oynaChiz() {
    oynaElementlari();
    const och = !!varaq && korinadimi();
    parda.classList.toggle("ochiq", och);
    oyna.classList.toggle("ochiq", och);
    if (!och) return;
    oyna.classList.toggle("toliq", varaq.t === "icon");
    if (varaq.t === "forma") oyna.innerHTML = formaHtml(varaq);
    else if (varaq.t === "icon") oyna.innerHTML = iconHtml(varaq);
    else oyna.innerHTML = ochirHtml(varaq);
  }
  const sarlavha = (matn) => `<div class="sz-oyna-bosh"><h3>${matn}</h3><button class="sz-yop" data-amal="yop" aria-label="Yopish">${IK.x}</button></div>`;

  function formaHtml(f) {
    const ichki = f.ota != null;
    const yangi = f.rejim === "yangi";
    const sar = yangi ? (ichki ? "Yangi ichki kategoriya" : "Yangi kategoriya") : "Kategoriyani tahrirlash";
    const placeholder = !ichki ? "Masalan: Uy-joy" : chuqurlik(f.ota) <= 1 ? "Masalan: Meva-sabzavot" : "Masalan: Olma";
    const royxat = tanlanadigan(f);
    const otaRasm = ichki ? tugun.get(f.ota)?.rasm : (f.rejim === "tahrir" ? f.rasm : null);
    const n = ichki ? 10 : 16;
    let taklifR = taklif(royxat.filter((x) => x !== f.rasm), otaRasm, n);
    if (f.rasm) taklifR = [f.rasm, ...taklifR].slice(0, n); // tanlangani doim ko'rinsin
    return `${sarlavha(sar)}
      <label class="sz-yorliq" for="szNom">${ichki ? "Nomi" : "Kategoriya nomi"}</label>
      <input class="sz-kirit" id="szNom" maxlength="60" autocomplete="off" placeholder="${placeholder}" value="${e(f.nom)}">
      <div class="sz-yorliq">Icon tanlang</div>
      ${taklifR.length ? `<div class="sz-panjara${ichki ? " besh" : ""}">${taklifR.map((x) => tanlaHtml(x, x === f.rasm)).join("")}</div>`
        : `<div class="sz-izoh" style="margin:0">Bo‘sh icon qolmadi — boshqa kategoriyaning iconini almashtiring.</div>`}
      <button class="sz-boshqa" data-amal="iconlar">${IK.boshqa}<span>Boshqa iconlar</span>${IK.ong}</button>
      ${f.xato ? `<div class="sz-ogoh">${IK.ogoh}<span>${e(f.xato)}</span></div>` : ""}
      <button class="sz-kok-tugma" data-amal="saqla"${f.band ? " disabled" : ""}>${yangi ? "Qo‘shish" : "Saqlash"}</button>`;
  }
  function tanlaHtml(f, tanlangan) {
    const b = BELGI.get(f);
    if (!b) return "";
    return `<button class="sz-tanla${tanlangan ? " tanlangan" : ""}" data-belgi="${f}" style="background:${PASTEL[b.guruh] || "#eef1f6"}" aria-label="${e(guruhNomi(b.guruh))}"><img src="${ILOVA}belgilar/${b.kalit}.svg" alt="" loading="lazy" decoding="async"></button>`;
  }

  function iconHtml(v) {
    const guruhlar = GURUH_TARTIB.filter((g) => BELGILAR.some((b) => b.guruh === g));
    return `${sarlavha("Icon tanlang")}
      <label class="sz-qidir">${IK.qidir}<input id="szQidir" type="search" placeholder="Icon qidirish..." autocomplete="off" value="${e(v.q)}"></label>
      <div class="sz-chiplar">${[["barchasi", "Barchasi"], ...guruhlar.map((g) => [g, guruhNomi(g)])].map(([k, nom]) =>
        `<button class="sz-chip${k === v.guruh ? " faol" : ""}" data-guruh="${k}">${e(nom)}</button>`).join("")}</div>
      <div class="sz-aylan" id="szIconlar">${iconPanjara(v)}</div>`;
  }
  function iconPanjara(v) {
    const ruxsat = new Set(tanlanadigan(v.forma));
    const q = v.q.trim().toLowerCase();
    const tartib = new Map(GURUH_TARTIB.map((g, i) => [g, i]));
    const royxat = BELGILAR
      .filter((b) => ruxsat.has(b.fayl) && (v.guruh === "barchasi" || b.guruh === v.guruh) && (!q || b.qidir.includes(q)))
      .sort((a, b) => (tartib.get(a.guruh) ?? 99) - (tartib.get(b.guruh) ?? 99) || (a.fayl < b.fayl ? -1 : 1));
    if (!royxat.length) return `<div class="sz-bosh-holat">${q ? "Hech narsa topilmadi" : "Bu guruhda bo‘sh icon qolmadi"}</div>`;
    return `<div class="sz-panjara olti">${royxat.map((b) => tanlaHtml(b.fayl, b.fayl === v.forma.rasm)).join("")}</div>`;
  }

  /** Desktop `kategoriya_ochir` qoidasi — oldindan ko'rsatish uchun (server baribir tekshiradi). */
  function ochirSababi(x) {
    const n = x.bolalar.length;
    if (n) return `«${x.nom}» ichida ${n} ta ichki kategoriya bor — avval ularni o‘chiring.`;
    if (x.mahsulot) return `«${x.nom}» ichida ${x.mahsulot} ta mahsulot bor — avval ularni boshqa kategoriyaga o‘tkazing yoki o‘chiring.`;
    return "";
  }
  function ochirHtml(v) {
    const x = tugun.get(v.id);
    if (!x) return sarlavha("Kategoriya topilmadi");
    const sabab = v.xato || ochirSababi(x);
    if (sabab) {
      return `${sarlavha("O‘chirib bo‘lmaydi")}<div class="sz-ogoh">${IK.ogoh}<span>${e(sabab)}</span></div>
        <button class="sz-kok-tugma" data-amal="yop">Tushunarli</button>`;
    }
    return `${sarlavha("Kategoriyani o‘chirish")}
      <p class="sz-matn"><b>«${e(x.nom)}»</b> o‘chiriladi. Unga yozilgan eski xarajatlar o‘chmaydi — kategoriyasi bilan joyida qoladi.</p>
      <div class="sz-ikki"><button class="sz-kulrang-tugma" data-amal="yop">Bekor qilish</button>
        <button class="sz-qizil-tugma" data-amal="ochirTasdiq"${v.band ? " disabled" : ""}>O‘chirish</button></div>`;
  }

  // ── Hodisalar ──────────────────────────────────────────────────────
  function och(yangi) { varaq = yangi; oynaChiz(); xeshYoz(); tgOrqa(); }
  function orqa() {
    if (varaq) {
      if (varaq.t === "icon") { varaq = varaq.forma; oynaChiz(); xeshYoz(); tgOrqa(); return; }
      return yop();
    }
    if (stek.length > 1) { stek.pop(); chiz(); window.scrollTo(0, 0); }
  }

  S().addEventListener("click", (ev) => {
    const t = ev.target.closest("button"); if (!t) return;
    if (t.dataset.menyu) {
      // Demo rejim — soxta ma'lumot bilan taqdimot (index.html dagi FarvonDemo).
      if (t.dataset.menyu === "demo") {
        tebran("soft");
        const sw = t.querySelector(".sz-switch"); if (sw) sw.classList.toggle("on");
        if (window.FarvonDemo) window.FarvonDemo.almashtir().catch(() => { if (sw) sw.classList.toggle("on"); xabar("Ulanib bo‘lmadi"); });
        return;
      }
      if (t.dataset.menyu === "kategoriyalar") { stek.push({ t: "royxat" }); chiz(); tebran("soft"); if (!daraxt) yukla(); return; }
      // Boshqa bo'limlar o'z faylida: window.SozlamaBolimi[<kalit>] = () => ochish.
      // Kalitlar — MENYU dagi: profil, azolar, vazifalar, mahsulotlar, tolov, reja, bildirishnoma, ilova.
      const bolim = window.SozlamaBolimi && window.SozlamaBolimi[t.dataset.menyu];
      if (typeof bolim === "function") { tebran("soft"); return bolim(); }
      return xabar("Tez orada");
    }
    if (t.dataset.kat) { stek.push({ t: "kat", id: Number(t.dataset.kat) }); chiz(); window.scrollTo(0, 0); tebran("soft"); return; }
    const a = t.dataset.amal;
    if (a === "orqa") return orqa();
    if (a === "qayta") { xatoMatn = ""; chiz(); return yukla(); }
    const s = joriy();
    if (a === "yangi") {
      if (!daraxt) return;
      och(yangiForma(s.t === "kat" ? s.id : null));
      setTimeout(() => document.getElementById("szNom")?.focus(), 260);
    }
    if (a === "tahrir" && tugun.has(s.id)) och(tahrirForma(s.id));
    if (a === "ochir" && tugun.has(s.id)) och({ t: "ochir", id: s.id });
  });

  function formaniOl() {
    const f = varaq?.t === "forma" ? varaq : varaq?.forma;
    const inp = document.getElementById("szNom");
    if (f && inp) f.nom = inp.value;
    return f;
  }
  function oynaBosildi(ev) {
    const t = ev.target.closest("button"); if (!t) return;
    const a = t.dataset.amal;
    if (a === "yop") {
      if (varaq?.t === "icon") { varaq = varaq.forma; oynaChiz(); xeshYoz(); return; }
      return yop();
    }
    if (t.dataset.belgi) {
      if (varaq.t === "icon") { varaq.forma.rasm = t.dataset.belgi; varaq.forma.xato = ""; varaq = varaq.forma; oynaChiz(); xeshYoz(); tebran("soft"); return; }
      const f = formaniOl(); f.rasm = t.dataset.belgi; f.xato = "";
      oyna.querySelectorAll(".sz-tanla").forEach((b) => b.classList.toggle("tanlangan", b === t));
      oyna.querySelector(".sz-ogoh")?.remove();
      tebran("soft");
      return;
    }
    if (a === "iconlar") { const f = formaniOl(); och({ t: "icon", forma: f, guruh: "barchasi", q: "" }); oyna.scrollTop = 0; return; }
    if (t.dataset.guruh) {
      varaq.guruh = t.dataset.guruh;
      oyna.querySelectorAll(".sz-chip").forEach((b) => b.classList.toggle("faol", b === t));
      document.getElementById("szIconlar").innerHTML = iconPanjara(varaq);
      document.getElementById("szIconlar").scrollTop = 0;
      return;
    }
    if (a === "saqla") return saqla();
    if (a === "ochirTasdiq") return ochir();
  }
  function oynaKiritildi(ev) {
    if (ev.target.id === "szQidir" && varaq?.t === "icon") {
      varaq.q = ev.target.value;
      document.getElementById("szIconlar").innerHTML = iconPanjara(varaq);
    }
  }

  // ── Yozish ─────────────────────────────────────────────────────────
  async function saqla() {
    const f = formaniOl(); if (!f || f.band) return;
    const nom = f.nom.trim();
    if (!nom) { document.getElementById("szNom")?.focus(); return; }
    if (!f.rasm) { f.xato = "Icon tanlang — har kategoriya o‘z iconi bilan ko‘rinadi."; oynaChiz(); return; }
    f.band = true; oynaChiz();
    try {
      if (NAMUNA) namunaYoz(f, nom);
      else if (f.rejim === "yangi") qabul(await api("kategoriya", { nom, ota_id: f.ota, rasm: f.rasm }));
      else qabul(await api("kategoriya/" + f.id, { nom, rasm: f.rasm }));
      varaq = null; tebran("medium");
      chiz();
      xabar(f.rejim === "yangi" ? "Kategoriya qo‘shildi" : "Saqlandi");
    } catch (err) {
      f.band = false; f.xato = err.message;
      if (varaq === f) oynaChiz();
    }
  }
  async function ochir() {
    const v = varaq; if (!v || v.band) return;
    v.band = true; oynaChiz();
    try {
      if (NAMUNA) namunaOchir(v.id);
      else qabul(await api(`kategoriya/${v.id}/ochir`, {}));
      varaq = null; tebran("medium");
      stek = stek.filter((s) => !(s.t === "kat" && s.id === v.id));
      chiz(); window.scrollTo(0, 0);
      xabar("Kategoriya o‘chirildi");
    } catch (err) {
      v.band = false; v.xato = err.message;
      if (varaq === v) oynaChiz();
    }
  }

  // Namuna rejimi — desktop qoidalarining soddasi (faqat ko'rish uchun).
  function namunaYoz(f, nom) {
    const bor = [...tugun.values()].find((x) => x.nom === nom && x.id !== f.id);
    if (bor) throw new Error(`«${nom}» nomli kategoriya allaqachon bor`);
    const egasi = [...tugun.values()].find((x) => x.rasm === f.rasm && x.id !== f.id);
    if (egasi) throw new Error(`Bu rasm «${egasi.nom}» kategoriyasida band — boshqasini tanlang.`);
    if (f.rejim === "yangi") {
      const x = { id: Math.max(0, ...tugun.keys()) + 1, nom, rasm: f.rasm, ota_id: f.ota, mahsulot: 0, bolalar: [] };
      (f.ota != null ? tugun.get(f.ota).bolalar : daraxt).push(x);
    } else {
      Object.assign(tugun.get(f.id), { nom, rasm: f.rasm });
    }
    namunaYangila();
  }
  function namunaOchir(id) {
    const x = tugun.get(id); const sabab = ochirSababi(x);
    if (sabab) throw new Error(sabab);
    const r = x.ota_id != null ? tugun.get(x.ota_id).bolalar : daraxt;
    r.splice(r.indexOf(x), 1);
    namunaYangila();
  }
  function namunaYangila() {
    indeksla();
    const band = new Set([...tugun.values()].map((x) => x.rasm).filter(Boolean));
    bosh = BELGILAR.map((b) => b.fayl).filter((f) => !band.has(f));
  }

  // ── Telegram «Orqaga» ──────────────────────────────────────────────
  const TB = window.Telegram && Telegram.WebApp && Telegram.WebApp.BackButton;
  let tbKorinadi = false;
  if (TB) { try { TB.onClick(() => { if (korinadimi() && (stek.length > 1 || varaq)) orqa(); }); } catch (err) {} }
  function tgOrqa() {
    if (!TB) return;
    const kerak = korinadimi() && (stek.length > 1 || !!varaq);
    try {
      if (kerak && !tbKorinadi) TB.show();
      if (!kerak && tbKorinadi) TB.hide();
    } catch (err) {}
    tbKorinadi = kerak;
  }

  // ── Sahifa hodisalari ──────────────────────────────────────────────
  window.addEventListener("sahifa", (ev) => {
    if (ev.detail?.nom !== "sozlamalar") { if (varaq) { varaq = null; oynaChiz(); } tgOrqa(); return; }
    xeshniOch();
    if (!daraxt) yukla();
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && korinadimi() && !NAMUNA && INIT && !varaq) yukla();
  });
  if (korinadimi()) { xeshniOch(); yukla(); }
})();
