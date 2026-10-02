// Mini App «Sozlamalar → Kategoriyalar» API (miniapp_sozlama.js) va mahsulot.js /
// kategoriya.js dagi kategoriya funksiyalari — Python `core/mahsulot.py` bilan PARITY:
// daraxt, bo'sh ikonkalar, qo'shish (ichma-ich, tiriltirish), nomlash, ikonka
// almashtirish, o'chirish qoidalari, jurnal (bitta undo guruhi, toq id).
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { yangiBaza, py } from "./fixture.js";
import * as ma from "../src/miniapp.js";
import * as so from "../src/miniapp_sozlama.js";
import * as kat from "../src/kategoriya.js";
import * as mh from "../src/mahsulot.js";

const TOKEN = "123456:SINOV-token";

function imzola(user, { token = TOKEN, auth = Math.floor(Date.now() / 1000) } = {}) {
  const p = new URLSearchParams({ auth_date: String(auth), query_id: "AAE1", user: JSON.stringify(user) });
  const qator = [...p.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join("\n");
  const sir = createHmac("sha256", "WebAppData").update(token).digest();
  p.set("hash", createHmac("sha256", sir).update(qator).digest("hex"));
  return p.toString();
}

// Oziq-ovqat › Meva-sabzavot, Oziq-ovqat › Sut (ichida mahsulot), o'chirilgan
// «Eski» (ikonkali) va «Eski2» (ikonkasiz) — tiriltirish va nom qoidasi uchun.
const SEED = String.raw`
import json
from core import entries as en, xabar as xb, mahsulot as mh
F = en.odam_qosh(db, "Fayzulloxon")
O = en.odam_qosh(db, "Otabek")
db.apply("odam", "UPDATE", {"telegram": "fsultonoov", "tg_chat": 111}, F)
db.apply("odam", "UPDATE", {"tg_chat": 222}, O)
xb.sozlama_qoy(db, token="123456:SINOV-token", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
bz = db.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
db.apply("turi", "UPDATE", {"rasm": "shopping_01.png"}, bz)
oz = mh.kategoriya_qosh(db, "Oziq-ovqat", None, "food_01.png")
ms = mh.kategoriya_qosh(db, "Meva-sabzavot", oz, "food_23.png")
sut = mh.kategoriya_qosh(db, "Sut", oz, "food_08.png")
mh.saqla(db, nom="Qatiq", turi_id=sut)
mh.saqla(db, nom="Kefir", turi_id=sut)
mh.ochir(db, mh.saqla(db, nom="Eski sut", turi_id=sut))
e1 = mh.kategoriya_qosh(db, "Eski", None, "food_05.png")
mh.kategoriya_ochir(db, e1)
e2 = mh.kategoriya_qosh(db, "Eski2")
mh.kategoriya_ochir(db, e2)
`;

function qur() {
  const b = yangiBaza(SEED);
  b.sor = (yol, { user = { id: 111 }, tana, init } = {}) =>
    ma.ishla(new Request(`https://w.example${yol}`, {
      method: tana !== undefined ? "POST" : "GET",
      headers: { authorization: "tma " + (init ?? imzola(user)), "content-type": "application/json" },
      body: tana !== undefined ? JSON.stringify(tana) : undefined,
    }), {}, b.db);
  b.id = async (nom) => (await b.db.q1("SELECT id FROM turi WHERE nom=?", nom))?.id;
  return b;
}
const jsonOl = async (r) => [r.status, await r.json()];
const pyJson = (papka, kod) => {
  const chiq = py(papka, "import json\n" + kod).trim().split("\n");
  return JSON.parse(chiq[chiq.length - 1]);
};

test("ruxsat: imzosiz 401, begona 403, noma'lum yo'l 404", async () => {
  const b = qur();
  assert.equal((await b.sor("/app/api/kategoriya", { init: "hash=abc" })).status, 401);
  assert.equal((await b.sor("/app/api/kategoriya", { user: { id: 999 } })).status, 403);
  assert.equal((await b.sor("/app/api/kategoriya/boshqa")).status, 404);
  assert.equal((await b.sor("/app/api/kategoriya/99999", { tana: { nom: "X" } })).status, 404);
  assert.equal((await b.sor("/app/api/kategoriya/1/ochir/x", { tana: {} })).status, 404);
  // Uyning ikkinchi a'zosi ham boshqaradi
  assert.equal((await b.sor("/app/api/kategoriya", { user: { id: 222 } })).status, 200);
});

test("ikonkalar ro'yxati va guruh nomlari — Python kategoriya.py bilan bir xil (klient katalogi ham)", async () => {
  const b = qur();
  const p = pyJson(b.papka, `from core import kategoriya as k
print(json.dumps({"b": k.belgilar(), "g": k.GURUH_NOMI, "y": sorted(k.YASHIRIN)}))`);
  assert.deepEqual(kat.belgilar(), p.b);
  assert.deepEqual(kat.GURUH_NOMI, p.g);
  assert.deepEqual([...kat.YASHIRIN].sort(), p.y);
  // Klient (app/sozlama.js) dagi katalog: kalitlar va qidiruv so'zlari belgi_xarita.json dan.
  const ilova = readFileSync(resolve(import.meta.dirname, "../app/sozlama.js"), "utf8");
  const m = ilova.match(/const KATALOG = "([^"]+)"/);
  assert.ok(m, "sozlama.js da KATALOG topilmadi");
  const juft = m[1].split(",").map((x) => x.split(":"));
  assert.deepEqual(juft.map(([f]) => f + ".png"), p.b);
  const xarita = JSON.parse(readFileSync(resolve(import.meta.dirname, "../../packaging/belgi_xarita.json"), "utf8"));
  for (const [f, soz] of juft) assert.equal(soz, xarita[f + ".png"]);
  for (const f of p.b) assert.equal(kat.guruh(f), f.slice(0, f.lastIndexOf("_")));
});

test("daraxt, sonlar va bo'sh ikonkalar — Python mh.daraxt / bosh_belgilar bilan parity", async () => {
  const b = qur();
  const p = pyJson(b.papka, `from core import mahsulot as mh
def t(x):
    return {"id": x["id"], "nom": x["nom"], "rasm": x["rasm"], "ota_id": x["ota_id"], "bolalar": [t(c) for c in x["bolalar"]]}
mah = {r["turi_id"]: r["n"] for r in db.q("SELECT turi_id, COUNT(*) n FROM item WHERE ochirilgan=0 GROUP BY turi_id")}
print(json.dumps({"d": [t(x) for x in mh.daraxt(db)], "bosh": mh.bosh_belgilar(db), "mah": mah}))`);
  const [s, j] = await jsonOl(await b.sor("/app/api/kategoriya"));
  assert.equal(s, 200);
  assert.equal(j.ok, true);
  const tozala = (x) => ({ id: x.id, nom: x.nom, rasm: x.rasm, ota_id: x.ota_id, bolalar: x.bolalar.map(tozala) });
  assert.deepEqual(j.daraxt.map(tozala), p.d);
  assert.deepEqual(j.bosh, p.bosh);
  assert.deepEqual(await mh.bosh_belgilar(b.db), p.bosh);
  const tekis = [];
  const yur = (x) => { tekis.push(x); x.bolalar.forEach(yur); };
  j.daraxt.forEach(yur);
  for (const x of tekis) assert.equal(x.mahsulot, p.mah[x.id] || 0, x.nom);
  const oz = tekis.find((x) => x.nom === "Oziq-ovqat");
  assert.equal(oz.bolalar.length, 2);
  assert.equal(tekis.find((x) => x.nom === "Sut").mahsulot, 2); // o'chirilgani sanalmaydi
  assert.ok(!tekis.some((x) => x.nom === "Eski"));
  assert.ok(!j.bosh.includes("food_01.png") && j.bosh.includes("food_05.png")); // nofaolniki bo'sh
  assert.ok(!j.bosh.includes("education_08.png") && !j.bosh.includes("health_08.png"));
  for (const f of ["avlodlar"]) {
    const pa = pyJson(b.papka, `from core import mahsulot as mh
print(json.dumps(sorted(mh.${f}(db, ${oz.id}))))`);
    assert.deepEqual((await mh[f](b.db, oz.id)).sort((x, y) => x - y), pa);
  }
});

test("belgilar: bo'shlari, tahrirda o'z ikonkasi, guruhlar, taklif (ota guruhidan)", async () => {
  const b = qur();
  const ms = await b.id("Meva-sabzavot");
  const [, j] = await jsonOl(await b.sor(`/app/api/kategoriya/belgilar?ota=${ms}`));
  assert.equal(j.ok, true);
  assert.ok(!j.belgilar.includes("food_23.png"));
  assert.equal(j.guruhlar.length, 13);
  assert.deepEqual(j.guruhlar.find((g) => g.kalit === "food"), { kalit: "food", nom: "Oziq-ovqat" });
  assert.equal(j.taklif.length, 10);
  assert.ok(j.taklif.every((f) => f.startsWith("food_") && j.belgilar.includes(f)));
  const [, t] = await jsonOl(await b.sor(`/app/api/kategoriya/belgilar?ozi=${ms}`));
  assert.ok(t.belgilar.includes("food_23.png"));
  assert.equal(t.taklif.length, 16);
  assert.equal(new Set(t.taklif.map(kat.guruh)).size, 13); // katta uchun — har guruhdan
});

// Bir xil amallar ketma-ketligi: JS (API orqali) va Python (desktop funksiyalari)
// ikki nusxa bazada. Natija (ok/xato matni), turi jadvali va jurnal solishtiriladi.
const AMALLAR = [
  ["qosh", { nom: "Uy-joy", ota: null, rasm: "life_14.png" }],
  ["qosh", { nom: "  Mevalar ", ota: "Meva-sabzavot", rasm: "food_13.png" }], // 3-chuqurlik
  ["qosh", { nom: "Olma", ota: "Mevalar", rasm: "food_20.png" }],             // 4-chuqurlik
  ["qosh", { nom: "Nok", ota: "Mevalar", rasm: "food_20.png" }],              // ikonka band
  ["qosh", { nom: "Robot", ota: "Mevalar", rasm: "education_08.png" }],       // yashirin
  ["qosh", { nom: "Nimadir", ota: "Mevalar", rasm: null }],                   // ichkiga rasm shart
  ["qosh", { nom: "Oziq-ovqat", ota: null, rasm: "food_02.png" }],            // nom band
  ["qosh", { nom: "   ", ota: null, rasm: "food_02.png" }],                   // bo'sh nom
  ["qosh", { nom: "Ikonkasiz", ota: null, rasm: null }],                      // katta — desktopda ruxsat
  ["qosh", { nom: "Eski", ota: null, rasm: "food_06.png" }],                  // tiriltirish
  ["tahrir", { kim: "Olma", nom: "Olmalar" }],                                // nomlash
  ["tahrir", { kim: "Olmalar", nom: "Eski2" }],                               // nofaol nom ham band
  ["tahrir", { kim: "Olmalar", nom: "Uy-joy" }],
  ["tahrir", { kim: "Olmalar", rasm: "food_24.png" }],                        // ikonka almashtirish
  ["tahrir", { kim: "Olmalar", rasm: "food_13.png" }],                        // Mevalar niki
  ["tahrir", { kim: "Olmalar", rasm: "health_08.png" }],                      // yashirin
  ["tahrir", { kim: "Olmalar", rasm: "food_24.png", nom: "Olmalar" }],        // o'zgarishsiz
  ["tahrir", { kim: "Mevalar", nom: "Mevalar!", rasm: "food_20.png" }],       // ikkalasi, bitta undo
  ["ochir", { kim: "Mevalar!" }],                                             // ichida Olmalar
  ["ochir", { kim: "Oziq-ovqat" }],                                           // ichida 2 ta
  ["ochir", { kim: "Sut" }],                                                  // ichida mahsulot
  ["ochir", { kim: "Olmalar" }],
  ["ochir", { kim: "Mevalar!" }],                                             // endi bo'sh
  ["qosh", { nom: "Olmalar", ota: "Uy-joy", rasm: "food_20.png" }],           // tiriladi, yangi ota
  ["qosh", { nom: "Yangi", ota: "Uy-joy", rasm: "food_24.png" }],             // Olmalar ikonkasi bo'shagan
];

const PY_AMALLAR = String.raw`
from core import mahsulot as mh
AMALLAR = json.loads(open(r"__FAYL__", encoding="utf8").read())
def idsi(nom):
    return db.skalyar("SELECT id FROM turi WHERE nom=?", nom, birlamchi=None)
def tahrir(tid, ozg):
    # Mini App tahriri = desktop qoidalari: kategoriya_nomla + _rasm_tekshir(ozi), bitta undo
    t = db.q1("SELECT nom, rasm, ota_id FROM turi WHERE id=? AND faol=1", tid)
    if not t:
        raise ValueError("Kategoriya topilmadi")
    yangi = {}
    if "nom" in ozg:
        nom = (ozg["nom"] or "").strip()
        if not nom:
            raise ValueError("Kategoriya nomi bo'sh bo'lmasin")
        if nom != t["nom"]:
            if db.q1("SELECT id FROM turi WHERE nom=? AND id<>?", nom, tid):
                raise ValueError(f"«{nom}» nomli kategoriya allaqachon bor")
            yangi["nom"] = nom
    if "rasm" in ozg and (ozg["rasm"] or None) != (t["rasm"] or None):
        mh._rasm_tekshir(db, ozg["rasm"], tid)
        yangi["rasm"] = ozg["rasm"]
    if list(yangi) == ["nom"]:
        return mh.kategoriya_nomla(db, tid, yangi["nom"])   # desktopning o'zi
    if yangi:
        with db.amal(f"Kategoriya nomi: {yangi['nom']}" if "nom" in yangi else f"Kategoriya rasmi: {t['nom']}"):
            db.apply("turi", "UPDATE", yangi, tid)
bosh = db.skalyar("SELECT COALESCE(MAX(id),0) FROM ozgarishlar")
natija = []
for tur, a in AMALLAR:
    try:
        if tur == "qosh":
            mh.kategoriya_qosh(db, a["nom"], idsi(a["ota"]) if a["ota"] else None, a["rasm"])
        elif tur == "tahrir":
            tahrir(idsi(a["kim"]), {k: v for k, v in a.items() if k != "kim"})
        else:
            mh.kategoriya_ochir(db, idsi(a["kim"]))
        natija.append("ok")
    except ValueError as e:
        natija.append(str(e))
nomi = {r["id"]: r["nom"] for r in db.q("SELECT id, nom FROM turi")}
turi = [dict(r) for r in db.q("SELECT nom, rasm, faol, tartib, belgi, ota_id FROM turi ORDER BY nom")]
for r in turi:
    r["ota_id"] = nomi.get(r["ota_id"])
jurnal = [dict(r) for r in db.q("SELECT id, guruh_id, tavsif, jadval, amal, oldin, keyin FROM ozgarishlar WHERE id>? ORDER BY id", bosh)]
print(json.dumps({"natija": natija, "turi": turi, "jurnal": jurnal, "nomi": {str(k): v for k, v in nomi.items()}}, ensure_ascii=False))
`;

async function jsAmallar(b) {
  const bosh = await b.db.skalyar("SELECT COALESCE(MAX(id),0) FROM ozgarishlar");
  const natija = [];
  for (const [tur, a] of AMALLAR) {
    let r;
    if (tur === "qosh") {
      r = await b.sor("/app/api/kategoriya", { tana: { nom: a.nom, ota_id: a.ota ? await b.id(a.ota) : null, rasm: a.rasm } });
    } else if (tur === "tahrir") {
      const { kim, ...ozg } = a;
      r = await b.sor(`/app/api/kategoriya/${await b.id(kim)}`, { tana: ozg });
    } else {
      r = await b.sor(`/app/api/kategoriya/${await b.id(a.kim)}/ochir`, { tana: {} });
    }
    const j = await r.json();
    assert.equal(r.status, j.ok ? 200 : 400, `${tur} ${JSON.stringify(a)} ${JSON.stringify(natija)} ${JSON.stringify(j)}`);
    natija.push(j.ok ? "ok" : j.xato);
  }
  const nomi = Object.fromEntries((await b.db.q("SELECT id, nom FROM turi")).map((r) => [r.id, r.nom]));
  const turi = (await b.db.q("SELECT nom, rasm, faol, tartib, belgi, ota_id FROM turi ORDER BY nom"))
    .map((r) => ({ ...r, ota_id: nomi[r.ota_id] ?? null }));
  const jurnal = await b.db.q(
    "SELECT id, guruh_id, tavsif, jadval, amal, oldin, keyin FROM ozgarishlar WHERE id>? ORDER BY id", bosh);
  return { natija, turi, jurnal, nomi };
}

/** Jurnal qatori — id'larsiz (Python juft, Worker toq id beradi), ota nomi bilan. */
const jurnalTekis = (rows, nomi) => {
  const guruhlar = [...new Set(rows.map((r) => r.guruh_id))];
  const qator = (s) => {
    if (s == null) return null;
    const o = JSON.parse(s);
    delete o.id;
    o.ota_id = o.ota_id == null ? null : nomi[o.ota_id];
    return o;
  };
  return rows.map((r) => ({ guruh: guruhlar.indexOf(r.guruh_id), tavsif: r.tavsif, jadval: r.jadval,
    amal: r.amal, oldin: qator(r.oldin), keyin: qator(r.keyin) }));
};

test("qo'shish/tahrir/o'chirish ketma-ketligi — Python desktop funksiyalari bilan parity", async () => {
  const b = qur();
  const { writeFileSync } = await import("node:fs");
  const pb = yangiBaza(SEED); // Python — alohida nusxa bazada
  const fayl = resolve(pb.papka, "amallar.json");
  writeFileSync(fayl, JSON.stringify(AMALLAR));
  const p = pyJson(pb.papka, PY_AMALLAR.replace("__FAYL__", fayl));
  const j = await jsAmallar(b);

  assert.deepEqual(j.natija, p.natija);
  // Kutilgan xatolar desktop matni bilan
  assert.equal(j.natija[3], "Bu rasm «Olma» kategoriyasida band — boshqasini tanlang.");
  assert.equal(j.natija[4], "Bunday rasm yo'q — ro'yxatdan tanlang.");
  assert.equal(j.natija[5], "Ichki kategoriya uchun rasm tanlang.");
  assert.equal(j.natija[6], "«Oziq-ovqat» nomli kategoriya allaqachon bor");
  assert.equal(j.natija[11], "«Eski2» nomli kategoriya allaqachon bor"); // nomlash tiriltirmaydi
  assert.match(j.natija[18], /ichida 1 ta ichki kategoriya bor/);
  assert.match(j.natija[20], /«Sut» ichida 2 ta mahsulot bor/);
  assert.equal(j.natija.filter((x) => x === "ok").length, 13); // bittasi — o'zgarishsiz tahrir

  assert.deepEqual(j.turi, p.turi);
  const t = Object.fromEntries(j.turi.map((r) => [r.nom, r]));
  assert.equal(t.Eski.faol, 1);                       // tirildi
  assert.equal(t.Eski.rasm, "food_06.png");
  assert.equal(t.Olmalar.ota_id, "Uy-joy");           // qayta qo'shilganda yangi ota
  assert.equal(t["Mevalar!"].faol, 0);                // o'chirildi — qator joyida
  assert.equal(t.Sut.faol, 1);

  assert.deepEqual(jurnalTekis(j.jurnal, j.nomi), jurnalTekis(p.jurnal, p.nomi));
  // Har muvaffaqiyatli amal — bitta undo guruhi, bitta jurnal qatori, toq id (Worker)
  assert.equal(new Set(j.jurnal.map((r) => r.guruh_id)).size, 12); // o'zgarishsiz tahrir yozmaydi
  assert.equal(j.jurnal.length, 12);
  assert.ok(j.jurnal.every((r) => r.id % 2 === 1));
  const yangi = await b.db.q("SELECT id FROM turi WHERE nom IN ('Uy-joy','Mevalar!','Olma','Ikonkasiz','Yangi')");
  // «Olma» endi «Olmalar» — id lar toq (Worker yaratgan)
  assert.ok(yangi.every((r) => r.id % 2 === 1));
});

test("javob yangi daraxtni qaytaradi; o'chirish zanjir bo'lib ketmaydi", async () => {
  const b = qur();
  const oz = await b.id("Oziq-ovqat");
  const [s, j] = await jsonOl(await b.sor(`/app/api/kategoriya/${oz}/ochir`, { tana: {} }));
  assert.equal(s, 400);
  assert.equal(j.xato, "«Oziq-ovqat» ichida 2 ta ichki kategoriya bor — avval ularni o'chiring.");
  const faol = await b.db.skalyar("SELECT COUNT(*) FROM turi WHERE faol=1 AND (id=? OR ota_id=?)", [oz, oz]);
  assert.equal(faol, 3);
  const [, q] = await jsonOl(await b.sor("/app/api/kategoriya", {
    tana: { nom: "Mevalar", ota_id: await b.id("Meva-sabzavot"), rasm: "food_13.png" } }));
  assert.equal(q.ok, true);
  assert.ok(Number.isInteger(q.id) && q.id % 2 === 1);
  const ms = q.daraxt.find((x) => x.nom === "Oziq-ovqat").bolalar.find((x) => x.nom === "Meva-sabzavot");
  assert.deepEqual(ms.bolalar.map((x) => x.nom), ["Mevalar"]);
  assert.ok(!q.bosh.includes("food_13.png"));
  // Tahrir: bo'sh nom rad, noto'g'ri ota rad
  assert.equal((await jsonOl(await b.sor(`/app/api/kategoriya/${q.id}`, { tana: { nom: " " } })))[1].xato,
    "Kategoriya nomi bo'sh bo'lmasin");
  assert.equal((await jsonOl(await b.sor("/app/api/kategoriya", { tana: { nom: "X", ota_id: 99999, rasm: "food_02.png" } })))[1].xato,
    "Asosiy kategoriya topilmadi");
  // Ichki kategoriya ikonkasini olib tashlab bo'lmaydi
  assert.equal((await jsonOl(await b.sor(`/app/api/kategoriya/${q.id}`, { tana: { rasm: null } })))[1].xato,
    "Ichki kategoriya uchun rasm tanlang.");
});

test("taklif: sof funksiya — ota guruhi, keyin qo'shnilari; katta uchun navbat bilan", () => {
  const bosh = kat.belgilar().filter((f) => f !== "food_01.png");
  const t = so.taklif(bosh, "food_99.png", 40);
  assert.ok(t.slice(0, 28).every((f) => f.startsWith("food_")));
  assert.ok(t.slice(28).every((f) => f.startsWith("shopping_")));
  const k = so.taklif(bosh);
  assert.deepEqual(k.slice(0, 3), ["food_02.png", "life_01.png", "transportation_01.png"]);
});
