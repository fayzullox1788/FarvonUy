// Mini App «Sozlamalar → Vazifalar» (miniapp_sz_vazifa.js + vazifa.js portlari).
// Bir xil amallar ketma-ketligi Python `core/vazifa.py` da (to'g'ridan-to'g'ri) va
// Worker API orqali — natija, jadval qatorlari va `ozgarishlar` guruhlari AYNAN teng.
// Ruxsatlar (dars / navbat / idish / takror) va xato javoblari alohida.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { usta, nusxa, jsDb, pyIshla, muzlat, qatorlar, jurnal, jurnalNorm, maxOz } from "./_parity.js";
import * as ma from "../src/miniapp.js";
import * as vz from "../src/vazifa.js";
import { ruxsat, qatorTuri } from "../src/miniapp_sz_vazifa.js";

const TOKEN = "123456:SINOV-token";
const SOAT = "2026-10-04 06:00:00"; // yakshanba

function imzola(user) {
  const p = new URLSearchParams({ auth_date: String(Math.floor(Date.now() / 1000)), query_id: "AAE1", user: JSON.stringify(user) });
  const qator = [...p.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join("\n");
  const sir = createHmac("sha256", "WebAppData").update(TOKEN).digest();
  p.set("hash", createHmac("sha256", sir).update(qator).digest("hex"));
  return p.toString();
}

const SEED = String.raw`
muzlat("${SOAT}")
F = entries.odam_qosh(db, "Fayzulloxon")
O = entries.odam_qosh(db, "Otabek")
A = entries.odam_qosh(db, "Abbosxon")
db.apply("odam", "UPDATE", {"tg_chat": 111}, F)
db.apply("odam", "UPDATE", {"tg_chat": 222}, O)
db.apply("odam", "UPDATE", {"tg_chat": 333}, A)
xb.sozlama_qoy(db, token="${TOKEN}", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
mat = vz.tur_qosh(db, "Matematika", 80, shaxsiy=True)
db.apply("vazifa", "INSERT", {"nom": "Matematika", "odam_id": F, "sana": "2026-10-05", "vaqt": "09:00",
         "davomiylik": 80, "holat": "ochiq", "manba": "dars:2026-10-05:1"})
# Hali to'ldirilmagan qoida: takror_qosh uni ham o'sha amalda to'ldirishi kerak
db.apply("vazifa_takror", "INSERT", {"nom": "Bomdod namozi", "odam_id": A, "vaqt": "05:30", "davomiylik": 20,
         "naqsh": "kunlik", "oraliq": 1, "boshlanish": "2026-10-01"})
musor = vz.qosh(db, "Musorlarni tashlash", O, "2026-10-04", "09:00", 30)
ovq = vz.navbat_turi(db)["id"]
chiq({"F": F, "O": O, "A": A, "mat": mat, "ovq": ovq, "musor": musor})
`;
const U = usta(SEED);
const ID = U.id;

// Python haqiqati. `vid(nom, sana)` — id'lar ikki tomonda farq qiladi (Worker toq id beradi).
const PY_AMALLAR = String.raw`
muzlat("${SOAT}")
F, O, A, ovq = ${ID.F}, ${ID.O}, ${ID.A}, ${ID.ovq}
def vid(nom, sana):
    return db.skalyar("SELECT id FROM vazifa WHERE ochirilgan=0 AND nom=? AND sana=? ORDER BY id", nom, sana)
def tid(nom):
    return db.skalyar("SELECT id FROM vazifa_turi WHERE nom=?", nom)
N = []
def q(f, idmi=False):
    try:
        r = f()
        N.append("id" if idmi else r)
    except ValueError as e:
        N.append("XATO " + str(e))
qi = lambda f: q(f, True)
qi(lambda: vz.qosh(db, "Kir yuvish", O, "2026-10-05", "10:00", 90, "  oq kiyimlar "))
qi(lambda: vz.qosh(db, "   ", O, "2026-10-05", "10:00", 90))
qi(lambda: vz.qosh(db, "X", O, "2026-10-05", "25:00", 90))
qi(lambda: vz.qosh(db, "X", O, "2026-10-05", None, 0))
qi(lambda: vz.takror_qosh(db, "Sport", F, "07:00", 45, naqsh="kunlar", kunlar=[4, 0, 2, 2], izoh=" zal ", boshlanish="2026-10-04"))
qi(lambda: vz.takror_qosh(db, "Gul", F, None, 15, naqsh="oraliq", kunlar=[], oraliq=0, boshlanish="2026-10-04"))
qi(lambda: vz.takror_qosh(db, "Gul", F, None, 15, naqsh="kunlar", kunlar=[], oraliq=1, boshlanish="2026-10-04"))
qi(lambda: vz.takror_qosh(db, "Gul", F, None, 15, naqsh="oraliq", kunlar=[], oraliq=3, boshlanish="2026-10-06"))
q(lambda: vz.navbat_biriktir(db, ovq, O, "2026-10-06", "19:00", 3))
q(lambda: vz.tahrir(db, vid("Kir yuvish", "2026-10-05"), nom="  Kir yuvish (oq) ", vaqt=None, davomiylik=30, izoh=""))
q(lambda: vz.tahrir(db, vid("Kir yuvish (oq)", "2026-10-05"), davomiylik=0))
q(lambda: vz.tahrir(db, vid("Kir yuvish (oq)", "2026-10-05"), odam_id=A, sana="2026-10-07", vaqt="7:5"))
q(lambda: vz.tahrir(db, vid("Sport", "2026-10-07"), vaqt="08:00", izoh="bugun hovlida"))
q(lambda: vz.bersin(db, vid("Ovqat qilish", "2026-10-06"), F))
q(lambda: vz.almashtir(db, vid("Ovqat qilish", "2026-10-07"), O))
q(lambda: vz.almashtir(db, vid("Ovqat qilish", "2026-10-07"), F))
q(lambda: vz.bersin(db, vid("Ovqat qilish", "2026-10-07"), A))
q(lambda: vz.ochir(db, vid("Kir yuvish (oq)", "2026-10-07")))
q(lambda: vz.ochir(db, vid("Sport", "2026-10-09")))
q(lambda: vz.takror_ochir(db, vz.takror_egasi(db, vz.bitta(db, vid("Sport", "2026-10-07")))["id"]))
qi(lambda: vz.tur_qosh(db, "Gul sug'orish", 15, True))
qi(lambda: vz.tur_qosh(db, " Gul sug'orish ", 15, False))
qi(lambda: vz.tur_qosh(db, "Y", 0, False))
q(lambda: vz.tur_davomiylik_qoy(db, tid("Gul sug'orish"), 20))
q(lambda: vz.tur_shaxsiy_qoy(db, tid("Gul sug'orish"), False))
qi(lambda: vz.qadam_qosh(db, tid("Gul sug'orish"), " Balkon "))
qi(lambda: vz.qadam_qosh(db, tid("Gul sug'orish"), "BALKON"))
qi(lambda: vz.qadam_qosh(db, tid("Gul sug'orish"), "Oshxona"))
q(lambda: vz.qadam_ochir(db, db.skalyar("SELECT id FROM ish_qadam WHERE nom='Balkon'")))
q(lambda: vz.tur_ochir(db, tid("Gul sug'orish")))
qi(lambda: vz.tur_qosh(db, "Gul sug'orish", 25, False))
qi(lambda: vz.qosh(db, "Kitob o'qish", F, "2026-10-05", "21:00", 40))
q(lambda: vz.tur_qosh(db, "Kitob o'qish", 40, True) and None)  # API «shaxsiy» → tur yo'q edi
q(lambda: vz.tur_shaxsiy_qoy(db, tid("Kitob o'qish"), False))
chiq(N)
`;

const VAZIFA_SQL = "SELECT nom, odam_id, sana, vaqt, davomiylik, holat, bajarilgan, izoh, kechiktirildi," +
  " CASE WHEN manba LIKE 'takror:%' THEN 'takror:' || (SELECT nom FROM vazifa_takror t WHERE t.id=CAST(substr(manba, 8, instr(substr(manba, 8), ':')-1) AS INTEGER)) || substr(manba, 8 + instr(substr(manba, 8), ':') - 1) ELSE manba END manba," +
  " ochirilgan FROM vazifa ORDER BY sana, nom, odam_id, COALESCE(vaqt,''), manba";
const TUR_SQL = "SELECT nom, davomiylik, tartib, navbat, haftalik, shaxsiy, ergash_turi_id, ochirilgan FROM vazifa_turi ORDER BY nom";
const QADAM_SQL = "SELECT t.nom tur, q.nom, q.tartib, q.ochirilgan FROM ish_qadam q JOIN vazifa_turi t ON t.id=q.turi_id ORDER BY t.nom, q.nom";
const TAKROR_SQL = "SELECT nom, odam_id, vaqt, davomiylik, izoh, naqsh, kunlar, oraliq, boshlanish, tugash, faol, ochirilgan FROM vazifa_takror ORDER BY nom";
const SQLLAR = [VAZIFA_SQL, TUR_SQL, QADAM_SQL, TAKROR_SQL];

/** Worker tomoni: xuddi shu amallar — API orqali (faqat API'da yo'qlari to'g'ridan-to'g'ri). */
async function jsAmallar(db) {
  const sor = async (yol, tana, user = { id: 111 }) => {
    const r = await ma.ishla(new Request(`https://w.example/app/api/vazifa-boshqaruv${yol}`, {
      method: tana ? "POST" : "GET",
      headers: { authorization: "tma " + imzola(user), ...(tana ? { "content-type": "application/json" } : {}) },
      body: tana ? JSON.stringify(tana) : undefined,
    }), {}, db);
    const j = await r.json();
    assert.equal(r.status, j.ok ? 200 : 400, `${yol} ${JSON.stringify(tana)} → ${JSON.stringify(j)}`);
    return j;
  };
  const vid = (nom, sana) => db.skalyar("SELECT id FROM vazifa WHERE ochirilgan=0 AND nom=? AND sana=? ORDER BY id", [nom, sana], null);
  const tid = (nom) => db.skalyar("SELECT id FROM vazifa_turi WHERE nom=?", [nom], null);
  const N = [];
  const q = async (p) => {
    const j = await p;
    N.push(j.ok ? ("id" in j || "takror_id" in j ? "id" : j.soni ?? j.natija ?? null) : "XATO " + j.xato);
  };
  const { F, O, A, ovq } = ID;
  await q(sor("/vazifa", { nom: "Kir yuvish", odam_id: O, sana: "2026-10-05", vaqt: "10:00", davomiylik: 90, izoh: "  oq kiyimlar " }));
  await q(sor("/vazifa", { nom: "   ", odam_id: O, sana: "2026-10-05", vaqt: "10:00", davomiylik: 90 }));
  await q(sor("/vazifa", { nom: "X", odam_id: O, sana: "2026-10-05", vaqt: "25:00", davomiylik: 90 }));
  await q(sor("/vazifa", { nom: "X", odam_id: O, sana: "2026-10-05", vaqt: null, davomiylik: 0 }));
  await q(sor("/vazifa", { nom: "Sport", odam_id: F, sana: "2026-10-04", vaqt: "07:00", davomiylik: 45, izoh: " zal ", takror: { naqsh: "kunlar", kunlar: [4, 0, 2, 2] } }));
  await q(sor("/vazifa", { nom: "Gul", odam_id: F, sana: "2026-10-04", vaqt: null, davomiylik: 15, takror: { naqsh: "oraliq", kunlar: [], oraliq: 0 } }));
  await q(sor("/vazifa", { nom: "Gul", odam_id: F, sana: "2026-10-04", vaqt: null, davomiylik: 15, takror: { naqsh: "kunlar", kunlar: [], oraliq: 1 } }));
  await q(sor("/vazifa", { nom: "Gul", odam_id: F, sana: "2026-10-06", vaqt: null, davomiylik: 15, takror: { naqsh: "oraliq", kunlar: [], oraliq: 3 } }));
  await q(sor("/vazifa", { nom: "Ovqat qilish", odam_id: O, sana: "2026-10-06", vaqt: "19:00", davomiylik: 60, navbat: { tur_id: ovq, kunlar: 3 } }));
  await q(sor(`/vazifa/${await vid("Kir yuvish", "2026-10-05")}`, { nom: "  Kir yuvish (oq) ", vaqt: null, davomiylik: 30, izoh: "" }));
  await q(sor(`/vazifa/${await vid("Kir yuvish (oq)", "2026-10-05")}`, { davomiylik: 0 }));
  await q(sor(`/vazifa/${await vid("Kir yuvish (oq)", "2026-10-05")}`, { odam_id: A, sana: "2026-10-07", vaqt: "7:5" }));
  await q(sor(`/vazifa/${await vid("Sport", "2026-10-07")}`, { vaqt: "08:00", izoh: "bugun hovlida" }));
  const nv = (j) => (j.ok ? { vazifa_id: "id", yuvuvchi_tuzatildi: j.yuvuvchi_tuzatildi, eski_nom: j.eski_nom, yangi_nom: j.yangi_nom, ...(j.juft_id ? { juft_id: "id", juft_sana: j.juft_sana } : {}) } : "XATO " + j.xato);
  N.push(nv(await sor(`/vazifa/${await vid("Ovqat qilish", "2026-10-06")}/navbat`, { odam_id: F, usul: "bersin" })));
  N.push(nv(await sor(`/vazifa/${await vid("Ovqat qilish", "2026-10-07")}/navbat`, { odam_id: O, usul: "almashtir" })));
  N.push(nv(await sor(`/vazifa/${await vid("Ovqat qilish", "2026-10-07")}/navbat`, { odam_id: F, usul: "almashtir" })));
  N.push(nv(await sor(`/vazifa/${await vid("Ovqat qilish", "2026-10-07")}/navbat`, { odam_id: A, usul: "bersin" })));
  await q(sor(`/vazifa/${await vid("Kir yuvish (oq)", "2026-10-07")}/ochir`, {}));
  await q(sor(`/vazifa/${await vid("Sport", "2026-10-09")}/ochir`, {}));
  await q(sor(`/vazifa/${await vid("Sport", "2026-10-07")}/takror-ochir`, {}));
  await q(sor("/tur", { nom: "Gul sug'orish", davomiylik: 15, shaxsiy: true }));
  await q(sor("/tur", { nom: " Gul sug'orish ", davomiylik: 15, shaxsiy: false }));
  await q(sor("/tur", { nom: "Y", davomiylik: 0, shaxsiy: false }));
  await q(sor(`/tur/${await tid("Gul sug'orish")}`, { davomiylik: 20 }));
  await q(sor(`/tur/${await tid("Gul sug'orish")}`, { shaxsiy: false }));
  await q(sor(`/tur/${await tid("Gul sug'orish")}/qadam`, { nom: " Balkon " }));
  await q(sor(`/tur/${await tid("Gul sug'orish")}/qadam`, { nom: "BALKON" }));
  await q(sor(`/tur/${await tid("Gul sug'orish")}/qadam`, { nom: "Oshxona" }));
  await q(sor(`/qadam/${await db.skalyar("SELECT id FROM ish_qadam WHERE nom='Balkon'", [], null)}/ochir`, {}));
  await q(sor(`/tur/${await tid("Gul sug'orish")}/ochir`, {}));
  await q(sor("/tur", { nom: "Gul sug'orish", davomiylik: 25, shaxsiy: false }));
  await q(sor("/vazifa", { nom: "Kitob o'qish", odam_id: F, sana: "2026-10-05", vaqt: "21:00", davomiylik: 40 }));
  await q(sor(`/vazifa/${await vid("Kitob o'qish", "2026-10-05")}/shaxsiy`, { shaxsiy: true }));
  await q(sor(`/vazifa/${await vid("Kitob o'qish", "2026-10-05")}/shaxsiy`, { shaxsiy: false }));
  return N;
}

/** Python natijasini API natijasi ko'rinishiga keltiradi. */
function pyNorm(N) {
  return N.map((x) => {
    if (x && typeof x === "object") {
      const o = { vazifa_id: "id", yuvuvchi_tuzatildi: x.yuvuvchi_tuzatildi, eski_nom: x.eski_nom, yangi_nom: x.yangi_nom };
      if ("juft_id" in x) Object.assign(o, { juft_id: "id", juft_sana: x.juft_sana });
      return o;
    }
    return x;
  });
}

test("amallar ketma-ketligi: natija, jadvallar va jurnal Python bilan AYNAN teng", async () => {
  const pp = nusxa(U.papka), jp = nusxa(U.papka);
  const oz = maxOz(pp);
  const pr = pyIshla(pp, PY_AMALLAR);
  muzlat(SOAT);
  const db = jsDb(jp);
  const jr = await jsAmallar(db);
  // API takror_qosh/navbat_biriktir/tahrir... natijalari: id yoki son, xatolar matni bilan
  assert.deepEqual(jr, pyNorm(pr));
  assert.ok(jr.filter((x) => String(x).startsWith("XATO")).length >= 10, "xato holatlari ham sinalsin");
  for (const s of SQLLAR) assert.deepEqual(qatorlar(jp, s), qatorlar(pp, s), s);
  assert.deepEqual(jurnalNorm(jurnal(jp, oz)), jurnalNorm(jurnal(pp, oz)), "ozgarishlar");
  // Worker yozgan yangi qatorlar — toq id
  const yangi = qatorlar(jp, "SELECT id FROM vazifa WHERE manba LIKE 'takror:%' OR nom='Kitob o''qish'", []);
  assert.ok(yangi.length && yangi.every((r) => r.id % 2 === 1));
});

test("o'qish portlari: navbat_rejasi, takror_tavsif, _kunlar_matn, turlar — Python bilan teng", async () => {
  const pp = nusxa(U.papka);
  const pr = pyIshla(pp, String.raw`
muzlat("${SOAT}")
r = vz.navbat_rejasi(db, ${ID.ovq}, ${ID.A}, "2026-10-30", "22:45", 4)
t = [vz.takror_tavsif(x) for x in [
  {"naqsh": "kunlar", "kunlar": "0,3,6", "oraliq": 1, "vaqt": "07:00"},
  {"naqsh": "oraliq", "kunlar": None, "oraliq": 1, "vaqt": None},
  {"naqsh": "oraliq", "kunlar": None, "oraliq": 5, "vaqt": "06:10"},
  {"naqsh": "kunlik", "kunlar": None, "oraliq": 1, "vaqt": "05:30"}]]
k = [vz._kunlar_matn(x) for x in ([3, 1, 1], "6, 0", [], None)]
xatolar = []
for f in (lambda: vz._kunlar_matn([7]), lambda: vz.navbat_rejasi(db, ${ID.mat}, ${ID.F}, "2026-10-04"),
          lambda: vz.navbat_rejasi(db, ${ID.ovq}, ${ID.F}, "2026-10-04", None, 0)):
    try: f()
    except ValueError as e: xatolar.append(str(e))
chiq({"r": r, "t": t, "k": k, "x": xatolar, "turlar": vz.tur_nomlari(db),
      "nl": vz.navbatlimi(db, ${ID.musor}), "yid": vz.yuvuvchi_id(db, ${ID.O})})
`);
  const db = jsDb(nusxa(U.papka));
  const xatolar = [];
  for (const f of [() => vz._kunlar_matn([7]), () => vz.navbat_rejasi(db, ID.mat, ID.F, "2026-10-04"),
    () => vz.navbat_rejasi(db, ID.ovq, ID.F, "2026-10-04", null, 0)]) {
    try { await f(); } catch (e) { xatolar.push(e.message); }
  }
  const jr = {
    r: await vz.navbat_rejasi(db, ID.ovq, ID.A, "2026-10-30", "22:45", 4),
    t: [{ naqsh: "kunlar", kunlar: "0,3,6", oraliq: 1, vaqt: "07:00" }, { naqsh: "oraliq", kunlar: null, oraliq: 1, vaqt: null },
      { naqsh: "oraliq", kunlar: null, oraliq: 5, vaqt: "06:10" }, { naqsh: "kunlik", kunlar: null, oraliq: 1, vaqt: "05:30" }].map(vz.takror_tavsif),
    k: [[3, 1, 1], "6, 0", [], null].map(vz._kunlar_matn),
    x: xatolar,
    turlar: await vz.tur_nomlari(db),
    nl: await vz.navbatlimi(db, ID.musor),
    yid: await vz.yuvuvchi_id(db, ID.O),
  };
  assert.deepEqual(JSON.parse(JSON.stringify(jr)), pr);
});

// ─────────────────────────────────────────────── API: ruxsatlar va ko'rinish

async function apiDb() {
  muzlat(SOAT);
  const db = jsDb(nusxa(U.papka));
  await vz.navbat_biriktir(db, ID.ovq, ID.O, "2026-10-05", "19:00", 2);
  await vz.takror_qosh(db, "Sport", ID.F, { vaqt: "07:00", naqsh: "kunlik", boshlanish: "2026-10-04" });
  const sor = async (yol, tana, user = { id: 222 }) => {
    const r = await ma.ishla(new Request(`https://w.example/app/api/vazifa-boshqaruv${yol}`, {
      method: tana ? "POST" : "GET",
      headers: { authorization: "tma " + imzola(user), ...(tana ? { "content-type": "application/json" } : {}) },
      body: tana ? JSON.stringify(tana) : undefined,
    }), {}, db);
    return [r.status, await r.json()];
  };
  return { db, sor };
}

test("GET: hamma odamning vazifalari, qator turi va ruxsati, turlar", async () => {
  const { sor } = await apiDb();
  const [st, j] = await sor("?dan=2026-10-04");
  assert.equal(st, 200);
  assert.equal(j.men, ID.O);
  assert.equal(j.bugun, "2026-10-04");
  assert.equal(j.gacha, "2026-10-11");
  assert.deepEqual(j.odamlar.map((o) => o.nom), ["Fayzulloxon", "Otabek", "Abbosxon"]);
  const tur = (nom, sana) => j.vazifalar.find((v) => v.nom === nom && v.sana === sana);
  const dars = tur("Matematika", "2026-10-05");
  assert.equal(dars.tur, "dars");
  assert.equal(dars.toifa, "darslar");
  assert.deepEqual(Object.values(dars.ruxsat.maydon), [false, false, false, false, false, false]);
  assert.equal(dars.ruxsat.ochir, false);
  const ovq = tur("Ovqat qilish", "2026-10-05");
  assert.equal(ovq.tur, "navbat");
  assert.equal(ovq.ruxsat.navbat, true);
  assert.equal(ovq.ruxsat.maydon.kim, false);
  assert.equal(ovq.ruxsat.maydon.vaqt, true);
  const idish = j.vazifalar.find((v) => v.tur === "ergash" && v.sana === "2026-10-05");
  assert.equal(idish.odam_id, ovq.odam_id);
  assert.equal(idish.ruxsat.maydon.kim, false);
  const sport = tur("Sport", "2026-10-06");
  assert.equal(sport.tur, "takror");
  assert.equal(sport.takror.tavsif, "Har kuni 07:00");
  assert.equal(sport.ruxsat.takror, true);
  assert.equal(tur("Musorlarni tashlash", "2026-10-04").tur, "oddiy");
  // Sport 8 kun, bomdod 8 kun (takror_qosh boshqa qoidani ham to'ldirdi)
  assert.equal(j.vazifalar.filter((v) => v.nom === "Bomdod namozi").length, 8);
  const mat = j.turlar.find((t) => t.nom === "Matematika");
  assert.equal(mat.dars, true);
  assert.equal(mat.shaxsiy, true);
  assert.equal(j.turlar.find((t) => t.navbat).nom, "Ovqat qilish");
  assert.equal(j.turlar.find((t) => t.ergash).nom, "Ovqat qilib turgan vaqtda chiqqan idishlarni yuvish");
  assert.deepEqual(j.navbat, { tur_id: ID.ovq, nom: "Ovqat qilish", ergash: "Ovqat qilib turgan vaqtda chiqqan idishlarni yuvish" });
});

test("ruxsat: dars, navbat va idish qatorlari server tomonida ham himoyalangan", async () => {
  const { db, sor } = await apiDb();
  const vid = (nom, sana) => db.skalyar("SELECT id FROM vazifa WHERE ochirilgan=0 AND nom=? AND sana=?", [nom, sana], null);
  const dars = await vid("Matematika", "2026-10-05");
  const ovq = await vid("Ovqat qilish", "2026-10-05");
  const idish = await vid("Ovqat qilib turgan vaqtda chiqqan idishlarni yuvish", "2026-10-05");
  for (const [yol, tana, bolak] of [
    [`/vazifa/${dars}`, { vaqt: "10:00" }, "vaqti"],
    [`/vazifa/${dars}/ochir`, {}, "Dars jadvalidan"],
    [`/vazifa/${dars}/shaxsiy`, { shaxsiy: false }, "Dars jadvalidan"],
    [`/vazifa/${ovq}`, { odam_id: ID.A }, "kim bajarishi"],
    [`/vazifa/${ovq}`, { nom: "Palov" }, "nomi"],
    [`/vazifa/${ovq}`, { sana: "2026-10-09" }, "kuni"],
    [`/vazifa/${idish}`, { odam_id: ID.A }, "Idishni ovqat qilgan"],
    [`/vazifa/${idish}/navbat`, { odam_id: ID.A, usul: "bersin" }, "navbatli emas"],
    [`/tur/${ID.mat}`, { shaxsiy: false }, "Dars fani"],
    [`/tur/${ID.mat}/ochir`, {}, "Dars fani"],
    [`/vazifa/${ovq}/navbat`, { odam_id: ID.A, usul: "boshqa" }, "Noma'lum"],
    ["/vazifa", { nom: "X", odam_id: 0, sana: "2026-10-05" }, "Kim bajarishini"],
    ["/vazifa", { nom: "X", odam_id: ID.F, sana: "5-10-2026" }, "Sana"],
  ]) {
    const [st, j] = await sor(yol, tana);
    assert.equal(st, 400, `${yol} ${JSON.stringify(tana)}`);
    assert.ok(j.xato.includes(bolak), `${yol}: ${j.xato}`);
  }
  const oz = await db.skalyar("SELECT COUNT(*) FROM ozgarishlar", [], 0);
  // Ruxsat etilgani o'tadi: navbat qatorining vaqti, idishning izohi
  assert.equal((await sor(`/vazifa/${ovq}`, { vaqt: "19:30", davomiylik: 75 }))[0], 200);
  assert.equal((await sor(`/vazifa/${idish}`, { izoh: "Tez" }))[0], 200);
  assert.equal(await db.skalyar("SELECT COUNT(*) FROM ozgarishlar", [], 0), oz + 2, "har amal — bitta jurnal yozuvi");
  const v = await vz.bitta(db, ovq);
  assert.equal(v.vaqt, "19:30");
  assert.equal(v.davomiylik, 75);
  // Navbat oldindan ko'rish
  let [st, j] = await sor(`/vazifa/${ovq}/navbat?odam=${ID.A}`);
  assert.equal(st, 200);
  assert.equal(j.mumkin, true);
  assert.equal(j.juft_sana, "2026-10-06");
  [st, j] = await sor(`/vazifa/${ovq}/navbat?odam=${ID.F}`);
  assert.equal(j.mumkin, false);
  assert.match(j.sabab, /Fayzulloxonning bundan keyin/);
  // Yo'l to'qnashmaydi: eski /app/api/vazifa marshruti joyida
  const eski = await ma.ishla(new Request("https://w.example/app/api/vazifalar?sana=2026-10-05", {
    headers: { authorization: "tma " + imzola({ id: 222 }) } }), {}, db);
  assert.equal(eski.status, 200);
  assert.ok((await eski.json()).vazifalar.some((x) => x.nom === "Ovqat qilish"));
});

test("ruxsat: begona foydalanuvchi va noto'g'ri so'rovlar", async () => {
  const { sor } = await apiDb();
  assert.equal((await sor("", null, { id: 999 }))[0], 403);
  assert.equal((await sor("?dan=bugun"))[0], 400);
  assert.equal((await sor("/vazifa/999999", { vaqt: "10:00" }))[0], 404);
  assert.equal((await sor("/nomalum", {}))[0], 404);
  assert.equal((await sor("/tur/999999", { davomiylik: 5 }))[0], 404);
});

test("qatorTuri va ruxsat jadvali", () => {
  assert.equal(qatorTuri({ nom: "Ovqat qilish", manba: "dars:2026-10-05:1" }, "Ovqat qilish", "Idish"), "dars");
  assert.equal(qatorTuri({ nom: "Ovqat qilish", manba: null }, "Ovqat qilish", "Idish"), "navbat");
  assert.equal(qatorTuri({ nom: "Idish", manba: null }, "Ovqat qilish", "Idish"), "ergash");
  assert.equal(qatorTuri({ nom: "Sport", manba: "takror:3:2026-10-05" }, null, null), "takror");
  assert.equal(qatorTuri({ nom: "Sport", manba: "qazo:3" }, null, null), "oddiy");
  assert.equal(ruxsat("takror", false).takror, false);
  assert.equal(ruxsat("oddiy").maydon.kim, true);
});
