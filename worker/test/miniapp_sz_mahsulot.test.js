// Mini App «Sozlamalar → Mahsulotlar» API (miniapp_sz_mahsulot.js) va mahsulot.js dagi
// katalog funksiyalari — Python `core/mahsulot.py` bilan PARITY: mahsulotlar (filtr,
// qidiruv, tartib, kategoriya yo'li), tavsif, saqla/ochir/faol_almashtir qoidalari va
// xato matnlari, item jadvali va jurnal (bitta undo guruhi, toq id), rasm (faqat a'zoga).
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { yangiBaza, py } from "./fixture.js";
import * as ma from "../src/miniapp.js";
import * as mh from "../src/mahsulot.js";

const TOKEN = "123456:SINOV-token";

function imzola(user, { token = TOKEN, auth = Math.floor(Date.now() / 1000) } = {}) {
  const p = new URLSearchParams({ auth_date: String(auth), query_id: "AAE1", user: JSON.stringify(user) });
  const qator = [...p.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join("\n");
  const sir = createHmac("sha256", "WebAppData").update(token).digest();
  p.set("hash", createHmac("sha256", sir).update(qator).digest("hex"));
  return p.toString();
}

// Oziq-ovqat › Sut › Qatiq/Kefir; Oziq-ovqat › Meva-sabzavot › Olma (nofaol); Bozorlik
// ichida turli o'lchovli mahsulotlar; o'chirilgan mahsulot; nofaol kategoriyadagi mahsulot.
const SEED = String.raw`
from core import entries as en, xabar as xb, mahsulot as mh
F = en.odam_qosh(db, "Fayzulloxon")
O = en.odam_qosh(db, "Otabek")
db.apply("odam", "UPDATE", {"telegram": "fsultonoov", "tg_chat": 111}, F)
db.apply("odam", "UPDATE", {"tg_chat": 222}, O)
xb.sozlama_qoy(db, token="123456:SINOV-token", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
bz = db.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
oz = mh.kategoriya_qosh(db, "Oziq-ovqat", None, "food_01.png")
ms = mh.kategoriya_qosh(db, "Meva-sabzavot", oz, "food_23.png")
sut = mh.kategoriya_qosh(db, "Sut", oz, "food_08.png")
mh.saqla(db, nom="Qatiq", turi_id=sut, narx=9000, miqdor="0,5", olchov="litr")
mh.saqla(db, nom="kefir", turi_id=sut, narx=11000, litr="1", izoh="Nestle, yog'li")
mh.saqla(db, nom="Olma", turi_id=ms, narx=18000, miqdor=1, olchov="kg", faol=False)
mh.saqla(db, nom="Sovun", turi_id=bz, narx=6500, ogirlik="0,15", izoh="Dove")
mh.saqla(db, nom="Guruch", turi_id=bz, narx=0, miqdor="5", olchov="kg", ogirlik="5")
mh.ochir(db, mh.saqla(db, nom="Eski sut", turi_id=sut, narx=1))
es = mh.kategoriya_qosh(db, "Eski kat")
mh.saqla(db, nom="Yetim", turi_id=es, narx=500)
db.apply("turi", "UPDATE", {"faol": 0}, es)
db.apply("item", "INSERT", {"nom": "Eski tuz", "narx": 3000, "birlik": "4 dona"})
`;

function qur() {
  const b = yangiBaza(SEED);
  b.sor = (yol, { user = { id: 111 }, tana, init } = {}) =>
    ma.ishla(new Request(`https://w.example${yol}`, {
      method: tana !== undefined ? "POST" : "GET",
      headers: { authorization: "tma " + (init ?? imzola(user)), "content-type": "application/json" },
      body: tana !== undefined ? JSON.stringify(tana) : undefined,
    }), {}, b.db);
  b.tid = async (nom) => (await b.db.q1("SELECT id FROM turi WHERE nom=?", nom))?.id;
  b.iid = async (nom) => (await b.db.q1("SELECT id FROM item WHERE nom=? ORDER BY ochirilgan, id", nom))?.id;
  return b;
}
const jsonOl = async (r) => [r.status, await r.json()];
const pyJson = (papka, kod) => {
  const chiq = py(papka, "import json\n" + kod).trim().split("\n");
  return JSON.parse(chiq[chiq.length - 1]);
};

test("ruxsat: imzosiz 401, begona 403, noma'lum yo'l 404, ikkinchi a'zo ham", async () => {
  const b = qur();
  const sut = await b.iid("Qatiq");
  assert.equal((await b.sor("/app/api/mahsulot", { init: "hash=abc" })).status, 401);
  assert.equal((await b.sor("/app/api/mahsulot", { user: { id: 999 } })).status, 403);
  // Rasm ham faqat imzo bilan
  assert.equal((await b.sor(`/app/api/mahsulot/${sut}/rasm`, { init: "" })).status, 401);
  assert.equal((await b.sor(`/app/api/mahsulot/${sut}/rasm`, { user: { id: 999 } })).status, 403);
  assert.equal((await b.sor("/app/api/mahsulot/boshqa")).status, 404);
  assert.equal((await b.sor("/app/api/mahsulot/99999", { tana: { nom: "X" } })).status, 404);
  assert.equal((await b.sor(`/app/api/mahsulot/${sut}/ochir/x`, { tana: {} })).status, 404);
  const eski = (await b.db.q1("SELECT id FROM item WHERE nom='Eski sut'")).id;
  const [s, j] = await jsonOl(await b.sor(`/app/api/mahsulot/${eski}`, { tana: { nom: "Tirildi" } }));
  assert.equal(s, 404); // o'chirilgan mahsulot tahrirlanmaydi
  assert.equal(j.xato, "Mahsulot topilmadi");
  assert.equal((await b.sor("/app/api/mahsulot", { user: { id: 222 } })).status, 200);
});

const PY_ROYXAT = String.raw`
from core import mahsulot as mh
def q(rows):
    return [{"id": r["id"], "nom": r["nom"], "turi_id": r["turi_id"], "kategoriya": r["kategoriya"],
             "narx": r["narx"], "miqdor": r["miqdor"], "olchov": r["olchov"], "ogirlik": r["ogirlik"],
             "litr": r["litr"], "izoh": r["izoh"], "faol": r["faol"], "turi_nom": r["turi_nom"],
             "tavsif": mh.tavsif(r)} for r in rows]
tid = lambda n: db.skalyar("SELECT id FROM turi WHERE nom=?", n)
print(json.dumps({
  "hamma": q(mh.mahsulotlar(db)),
  "oziq": q(mh.mahsulotlar(db, tid("Oziq-ovqat"))),
  "sut": q(mh.mahsulotlar(db, tid("Sut"))),
  "qidir": q(mh.mahsulotlar(db, None, "  YOG'")),
  "qidir2": q(mh.mahsulotlar(db, tid("Oziq-ovqat"), "ol")),
  "faol": q(mh.mahsulotlar(db, None, "", True)),
  "tekis": [[t["id"], t["nom"], c] for t, c in mh.tekis(db)],
  "olchov": mh.OLCHOVLAR,
}, ensure_ascii=False))`;

test("katalog: mahsulotlar/tavsif/tekis — Python mh bilan parity (filtr, qidiruv, tartib, yo'l)", async () => {
  const b = qur();
  const p = pyJson(b.papka, PY_ROYXAT);
  const q = (rows) => rows.map((r) => ({ id: r.id, nom: r.nom, turi_id: r.turi_id, kategoriya: r.kategoriya,
    narx: r.narx, miqdor: r.miqdor, olchov: r.olchov, ogirlik: r.ogirlik, litr: r.litr, izoh: r.izoh,
    faol: r.faol, turi_nom: r.turi_nom, tavsif: mh.tavsif(r) }));
  const oz = await b.tid("Oziq-ovqat");
  assert.deepEqual(q(await mh.mahsulotlar(b.db)), p.hamma);
  assert.deepEqual(q(await mh.mahsulotlar(b.db, oz)), p.oziq);
  assert.deepEqual(q(await mh.mahsulotlar(b.db, await b.tid("Sut"))), p.sut);
  assert.deepEqual(q(await mh.mahsulotlar(b.db, null, "  YOG'")), p.qidir);
  assert.deepEqual(q(await mh.mahsulotlar(b.db, oz, "ol")), p.qidir2);
  assert.deepEqual(q(await mh.mahsulotlar(b.db, null, "", true)), p.faol);
  assert.deepEqual((await mh.tekis(b.db)).map(([t, c]) => [t.id, t.nom, c]), p.tekis);
  assert.deepEqual(mh.OLCHOVLAR, p.olchov);
  // Kutilganlar (desktop qoidasi): o'chirilgani yo'q, nofaol oxirida, ichkilari ham kiradi
  assert.ok(!p.hamma.some((r) => r.nom === "Eski sut"));
  assert.equal(p.hamma.at(-1).nom, "Olma");
  assert.deepEqual(p.oziq.map((r) => r.nom), ["kefir", "Qatiq", "Olma"]);
  assert.equal(p.qidir.map((r) => r.nom).join(), "kefir"); // izohdan
  assert.equal(p.hamma.find((r) => r.nom === "Qatiq").kategoriya, "Oziq-ovqat › Sut");
  assert.equal(p.hamma.find((r) => r.nom === "Qatiq").tavsif.replace(/ /g, " "), "0,5 litr · 9 000 so'm");
  assert.equal(p.hamma.find((r) => r.nom === "Eski tuz").tavsif.replace(/ /g, " "), "4 dona · 3 000 so'm");

  // API: o'sha tartib, qator maydonlari, filtrlar va daraxt
  const [s, j] = await jsonOl(await b.sor("/app/api/mahsulot"));
  assert.equal(s, 200);
  assert.deepEqual(j.mahsulotlar.map((r) => [r.id, r.kategoriya, r.tavsif]), p.hamma.map((r) => [r.id, r.kategoriya, r.tavsif]));
  const qatiq = j.mahsulotlar.find((r) => r.nom === "Qatiq");
  assert.equal(qatiq.olcham, "0,5 litr");
  assert.equal(qatiq.narx, 9000);
  assert.equal(j.mahsulotlar.find((r) => r.nom === "Guruch").olcham, "5 kg · 5 kg");
  assert.equal(j.mahsulotlar.find((r) => r.nom === "Olma").faol, 0);
  assert.equal(j.mahsulotlar.find((r) => r.nom === "Eski tuz").turi_id, null);
  assert.deepEqual(j.olchovlar, p.olchov);
  const tekis = [];
  const yur = (x, c) => { tekis.push([x.id, x.nom, c]); x.bolalar.forEach((y) => yur(y, c + 1)); };
  j.daraxt.forEach((x) => yur(x, 0));
  assert.deepEqual(tekis, p.tekis);
  const [, f] = await jsonOl(await b.sor(`/app/api/mahsulot?turi=${oz}&q=ol`));
  assert.deepEqual(f.mahsulotlar.map((r) => r.id), p.qidir2.map((r) => r.id));
  const [, g] = await jsonOl(await b.sor("/app/api/mahsulot?faollar=1"));
  assert.deepEqual(g.mahsulotlar.map((r) => r.id), p.faol.map((r) => r.id));
});

const SONLAR = ["", "  ", "0,5", "1 000,25", "1_000", "1e3", ".5", "5.", "+2", "-1", "-0", "abc",
  "1,2,3", "inf", "-inf", "1__0", "_1", "0x10", 3, 2.5, -4, true, null];

test("_son va narx (int) — Python bilan bir xil natija/xato", async () => {
  const b = qur();
  const fayl = resolve(b.papka, "sonlar.json");
  writeFileSync(fayl, JSON.stringify(SONLAR));
  const p = pyJson(b.papka, String.raw`
from core import mahsulot as mh
X = json.loads(open(r"${fayl}", encoding="utf8").read())
def bir(f):
    try:
        v = f()
        return ["ok", "Infinity" if v == float("inf") else v]
    except (ValueError, TypeError) as e:
        return ["xato", str(e)]
def narx(x):
    try:
        n = int(x or 0)
    except (TypeError, ValueError):
        raise ValueError("Narx butun son bo'lishi kerak") from None
    if n < 0:
        raise ValueError("Narx manfiy bo'lmasin")
    return n
print(json.dumps({"son": [bir(lambda x=x: mh._son(x, "Miqdor")) for x in X],
                  "narx": [bir(lambda x=x: narx(x)) for x in X if not isinstance(x, float) and x not in ("inf", "-inf", "nan")]}))`);
  const bir = (f) => { try { return ["ok", f()]; } catch (e) { return ["xato", e.message]; } };
  const js = SONLAR.map((x) => bir(() => mh._son(x, "Miqdor"))).map(([k, v]) =>
    [k, v === Infinity ? "Infinity" : v]);
  const pyS = p.son.map(([k, v]) => [k, v]);
  // json.dumps(inf) → Infinity (JSON.parse ham Infinity'ni qabul qilmaydi — matn bilan solishtiramiz)
  assert.deepEqual(js.map(([k, v]) => [k, typeof v === "number" ? v : String(v)]),
    pyS.map(([k, v]) => [k, typeof v === "number" ? v : String(v)]));
  assert.deepEqual(js[11], ["xato", "Miqdor son bo'lishi kerak"]);
  assert.deepEqual(js[9], ["xato", "Miqdor manfiy bo'lmasin"]);
  // Narx: API orqali (saqla) — Python int() bilan bir xil
  const sut = await b.tid("Sut");
  const nar = SONLAR.filter((x) => typeof x !== "number" || Number.isInteger(x)).filter((x) => !["inf", "-inf", "nan"].includes(x));
  const natija = [];
  for (const x of nar) {
    const [, j] = await jsonOl(await b.sor("/app/api/mahsulot", { tana: { nom: "N", turi_id: sut, narx: x } }));
    natija.push(j.ok ? ["ok", (await b.db.q1("SELECT narx FROM item WHERE id=?", j.id)).narx] : ["xato", j.xato]);
  }
  assert.deepEqual(natija, p.narx);
});

// Bir xil amallar ketma-ketligi: JS (API orqali) va Python (desktop funksiyalari)
// ikki nusxa bazada. Natija (ok/xato matni), item jadvali va jurnal solishtiriladi.
const AMALLAR = [
  ["yangi", { nom: "  Pishloq ", turi: "Sut", narx: 45000, miqdor: "0,3", olchov: " kg ", ogirlik: "", litr: "", izoh: " Golland ", faol: true }],
  ["yangi", { nom: "Tuxum", turi: "Oziq-ovqat", narx: 1500, miqdor: "10", olchov: "dona", ogirlik: null, litr: null, izoh: null, faol: false }],
  ["yangi", { nom: "   ", turi: "Sut", narx: 1 }],                          // nom bo'sh
  ["yangi", { nom: "Hech", turi: null, narx: 1 }],                          // kategoriya yo'q
  ["yangi", { nom: "Yetim2", turi: "Eski kat", narx: 1 }],                  // nofaol kategoriya
  ["yangi", { nom: "Manfiy", turi: "Sut", narx: -5 }],
  ["yangi", { nom: "Kasr", turi: "Sut", narx: "12.5" }],                    // narx butun emas
  ["yangi", { nom: "Litr", turi: "Sut", narx: 0, litr: "-1" }],
  ["yangi", { nom: "Og'ir", turi: "Sut", narx: 0, ogirlik: "bir" }],
  ["yangi", { nom: "Qatiq", turi: "Sut", narx: 9000 }],                     // bir xil nom — desktopda ruxsat
  ["tahrir", { kim: "Olma", nom: "Olma qizil", turi: "Meva-sabzavot", narx: 20000, miqdor: "1", olchov: "kg", ogirlik: "", litr: "", izoh: "", faol: true }],
  ["tahrir", { kim: "Sovun", nom: "Sovun", turi: "Oziq-ovqat", narx: 6500, miqdor: "", olchov: "", ogirlik: "0,15", litr: "", izoh: "Dove", faol: false }],
  ["tahrir", { kim: "Guruch", nom: "", turi: "Bozorlik", narx: 0 }],        // nom bo'sh
  ["tahrir", { kim: "Guruch", nom: "Guruch", turi: "Eski kat", narx: 0 }],  // nofaol kategoriya
  ["tahrir", { kim: "kefir", nom: "kefir", turi: "Sut", narx: 11000, miqdor: "", olchov: "", ogirlik: "", litr: "1", izoh: "Nestle, yog'li", faol: true }], // o'zgarishsiz — baribir yoziladi
  ["ochir", { kim: "Qatiq" }],
  ["ochir", { kim: "Tuxum" }],
  ["faol", { kim: "Pishloq" }],
  ["faol", { kim: "Pishloq" }],
];
const MAYDON = ["narx", "miqdor", "olchov", "ogirlik", "litr", "izoh"];

const PY_AMALLAR = String.raw`
from core import mahsulot as mh
AMALLAR = json.loads(open(r"__FAYL__", encoding="utf8").read())
MAYDON = ["narx", "miqdor", "olchov", "ogirlik", "litr", "izoh"]
tid = lambda n: db.skalyar("SELECT id FROM turi WHERE nom=?", n, birlamchi=None) if n else None
iid = lambda n: db.skalyar("SELECT id FROM item WHERE nom=? ORDER BY ochirilgan, id", n, birlamchi=None)
bosh = db.skalyar("SELECT COALESCE(MAX(id),0) FROM ozgarishlar")
natija = []
for tur, a in AMALLAR:
    try:
        if tur == "yangi":
            mh.saqla(db, None, nom=a["nom"], turi_id=tid(a["turi"]), faol=a.get("faol", True),
                     **{k: a.get(k) for k in MAYDON})
        elif tur == "tahrir":
            mh.saqla(db, iid(a["kim"]), nom=a["nom"], turi_id=tid(a["turi"]), faol=a.get("faol", False),
                     **{k: a.get(k) for k in MAYDON})
        elif tur == "ochir":
            mh.ochir(db, iid(a["kim"]))
        else:
            mh.faol_almashtir(db, iid(a["kim"]))
        natija.append("ok")
    except ValueError as e:
        natija.append(str(e))
tn = {r["id"]: r["nom"] for r in db.q("SELECT id, nom FROM turi")}
item = [dict(r) for r in db.q("SELECT nom, turi_id, narx, miqdor, olchov, ogirlik, litr, izoh, faol, ochirilgan, rasm, birlik FROM item ORDER BY nom, ochirilgan, narx")]
for r in item:
    r["turi_id"] = tn.get(r["turi_id"])
jurnal = [dict(r) for r in db.q("SELECT id, guruh_id, tavsif, jadval, amal, oldin, keyin FROM ozgarishlar WHERE id>? ORDER BY id", bosh)]
print(json.dumps({"natija": natija, "item": item, "jurnal": jurnal, "tn": {str(k): v for k, v in tn.items()}}, ensure_ascii=False))
`;

async function jsAmallar(b) {
  const bosh = await b.db.skalyar("SELECT COALESCE(MAX(id),0) FROM ozgarishlar");
  const natija = [];
  for (const [tur, a] of AMALLAR) {
    let r;
    if (tur === "yangi" || tur === "tahrir") {
      const tana = { nom: a.nom, turi_id: a.turi ? await b.tid(a.turi) : null, faol: a.faol ?? (tur === "yangi") };
      for (const k of MAYDON) tana[k] = a[k] ?? null;
      r = await b.sor(tur === "yangi" ? "/app/api/mahsulot" : `/app/api/mahsulot/${await b.iid(a.kim)}`, { tana });
    } else if (tur === "ochir") {
      r = await b.sor(`/app/api/mahsulot/${await b.iid(a.kim)}/ochir`, { tana: {} });
    } else {
      // Mini App'da alohida tugma yo'q (forma «Faol» belgisi bilan) — funksiya parity uchun
      try { await mh.faol_almashtir(b.db, await b.iid(a.kim)); natija.push("ok"); } catch (e) { natija.push(e.message); }
      continue;
    }
    const j = await r.json();
    assert.equal(r.status, j.ok ? 200 : 400, `${tur} ${JSON.stringify(a)} ${JSON.stringify(j)}`);
    natija.push(j.ok ? "ok" : j.xato);
  }
  const tn = Object.fromEntries((await b.db.q("SELECT id, nom FROM turi")).map((r) => [r.id, r.nom]));
  const item = (await b.db.q("SELECT nom, turi_id, narx, miqdor, olchov, ogirlik, litr, izoh, faol, ochirilgan, rasm, birlik FROM item ORDER BY nom, ochirilgan, narx"))
    .map((r) => ({ ...r, turi_id: tn[r.turi_id] ?? null }));
  const jurnal = await b.db.q(
    "SELECT id, guruh_id, tavsif, jadval, amal, oldin, keyin FROM ozgarishlar WHERE id>? ORDER BY id", bosh);
  return { natija, item, jurnal, tn };
}

/** Jurnal qatori — id'larsiz (Python juft, Worker toq id beradi), kategoriya nomi bilan. */
const jurnalTekis = (rows, tn) => {
  const guruhlar = [...new Set(rows.map((r) => r.guruh_id))];
  const qator = (s) => {
    if (s == null) return null;
    const o = JSON.parse(s);
    delete o.id;
    o.turi_id = o.turi_id == null ? null : tn[o.turi_id];
    return o;
  };
  return rows.map((r) => ({ guruh: guruhlar.indexOf(r.guruh_id), tavsif: r.tavsif, jadval: r.jadval,
    amal: r.amal, oldin: qator(r.oldin), keyin: qator(r.keyin) }));
};

test("qo'shish/tahrir/o'chirish/faol ketma-ketligi — Python desktop funksiyalari bilan parity", async () => {
  const b = qur();
  const pb = yangiBaza(SEED);
  const fayl = resolve(pb.papka, "amallar.json");
  writeFileSync(fayl, JSON.stringify(AMALLAR));
  const p = pyJson(pb.papka, PY_AMALLAR.replace("__FAYL__", fayl));
  const j = await jsAmallar(b);

  assert.deepEqual(j.natija, p.natija);
  assert.equal(j.natija[2], "Mahsulot nomi yozilmagan");
  assert.equal(j.natija[3], "Kategoriya tanlanmagan");
  assert.equal(j.natija[4], "Bu kategoriya endi yo'q — boshqasini tanlang");
  assert.equal(j.natija[5], "Narx manfiy bo'lmasin");
  assert.equal(j.natija[6], "Narx butun son bo'lishi kerak");
  assert.equal(j.natija[7], "Litr manfiy bo'lmasin");
  assert.equal(j.natija[8], "Og'irlik son bo'lishi kerak");
  assert.equal(j.natija.filter((x) => x === "ok").length, 10, JSON.stringify(j.natija));

  assert.deepEqual(j.item, p.item);
  const it = (nom) => j.item.find((r) => r.nom === nom && !r.ochirilgan);
  assert.deepEqual([it("Pishloq").miqdor, it("Pishloq").olchov, it("Pishloq").izoh, it("Pishloq").ogirlik], [0.3, "kg", "Golland", null]);
  assert.equal(it("Pishloq").faol, 1);                     // ikki marta almashtirildi
  assert.equal(it("Olma qizil").faol, 1);
  assert.equal(it("Sovun").turi_id, "Oziq-ovqat");
  assert.equal(j.item.filter((r) => r.nom === "Qatiq").map((r) => r.ochirilgan).join(), "0,1"); // eskisi o'chdi, qatori joyida
  assert.equal(j.item.find((r) => r.nom === "Tuxum").ochirilgan, 1);

  assert.deepEqual(jurnalTekis(j.jurnal, j.tn), jurnalTekis(p.jurnal, p.tn));
  assert.equal(new Set(j.jurnal.map((r) => r.guruh_id)).size, 10);
  assert.equal(j.jurnal.length, 10);
  assert.ok(j.jurnal.every((r) => r.id % 2 === 1));
  assert.ok(j.jurnal.some((r) => r.tavsif === "Mahsulot o'chirildi: Qatiq" && r.amal === "DELETE"));
});

test("tahrir: yuborilmagan maydon joyida qoladi; javobda yangi katalog", async () => {
  const b = qur();
  const id = await b.iid("Qatiq");
  const [s, j] = await jsonOl(await b.sor(`/app/api/mahsulot/${id}`, { tana: { narx: 9500 } }));
  assert.equal(s, 200);
  const r = await b.db.q1("SELECT * FROM item WHERE id=?", id);
  assert.deepEqual([r.nom, r.narx, r.miqdor, r.olchov, r.faol], ["Qatiq", 9500, 0.5, "litr", 1]);
  assert.equal(j.mahsulotlar.find((x) => x.id === id).tavsif.replace(/ /g, " "), "0,5 litr · 9 500 so'm");
  const [, k] = await jsonOl(await b.sor(`/app/api/mahsulot/${id}/ochir`, { tana: {} }));
  assert.ok(!k.mahsulotlar.some((x) => x.id === id));
  assert.equal((await b.db.q1("SELECT ochirilgan FROM item WHERE id=?", id)).ochirilgan, 1);
});

test("rasm: faqat o'chirilmagan mahsulotniki, tur sarlavhasi bilan; bo'lmasa 404", async () => {
  const b = qur();
  b.d1.db.exec("CREATE TABLE IF NOT EXISTS rasm(nom TEXT PRIMARY KEY, data BLOB)");
  const id = await b.iid("Qatiq");
  const fayl = await mh.rasm_baytdan(b.db, id, new Uint8Array([0xff, 0xd8, 0xff, 1, 2, 3]), ".JPG");
  const [, j] = await jsonOl(await b.sor("/app/api/mahsulot"));
  assert.equal(j.mahsulotlar.find((x) => x.id === id).rasm, fayl);
  const r = await b.sor(`/app/api/mahsulot/${id}/rasm`);
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("content-type"), "image/jpeg");
  assert.match(r.headers.get("cache-control"), /private/);
  assert.deepEqual([...new Uint8Array(await r.arrayBuffer())], [0xff, 0xd8, 0xff, 1, 2, 3]);
  assert.equal((await b.sor(`/app/api/mahsulot/${await b.iid("kefir")}/rasm`)).status, 404); // rasmsiz
  await mh.ochir(b.db, id);
  assert.equal((await b.sor(`/app/api/mahsulot/${id}/rasm`)).status, 404);                 // o'chirilgan
});
