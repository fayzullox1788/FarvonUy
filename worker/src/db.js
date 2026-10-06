// D1 ustidagi baza qatlami — Python `src/db.py` ning JS egizagi.
//
// Asosiy farq: D1 SQL darajasida BEGIN/COMMIT ni qabul qilmaydi, atomik
// birlik — `batch()`. Shuning uchun `Amal` yozuvlarni NAVBATGA yig'adi va
// `commit()` da bitta batch qilib yuboradi. `ozgarishlar` dagi oldin/keyin
// JSON ham shu batch ichida SQL bilan (`json_object`) olinadi — demak jurnal
// yozuvning o'zi bilan aynan bir lahzada, atomik yoziladi.
//
// ID QOIDASI: desktop faqat JUFT, Worker faqat TOQ id beradi (ikkala tomon
// oflayn yozadi, sinxronda to'qnashmasligi uchun). `toqId()` ga qarang.

const TOMON = 1; // Worker = toq

// Yopiq oyda o'zgartirib bo'lmaydigan jadvallar (db.py `_qulfni_tekshir`).
const QULFLI = new Set(["kirim", "rasxod", "qarz", "hisob_kitob", "tashqi_qarz",
  "tashqi_berilgan", "tashqi_qaytim",
  "tashqi_tolov", "tashqi_ulush", "karta_otkazma"]);

export class Xato extends Error {}
export class DavrYopilgan extends Xato {}

const _ustunlar = new Map(); // jadval -> [ustun, ...]  (izolyat umri davomida)

export class Db {
  /** @param {D1Database} d1 */
  constructor(d1) { this.d1 = d1; }

  // ── o'qish ─────────────────────────────────────────────────────────
  async q(sql, ...args) {
    const r = await this.d1.prepare(sql).bind(...args).all();
    return r.results;
  }
  async q1(sql, ...args) {
    return (await this.d1.prepare(sql).bind(...args).first()) ?? null;
  }
  async skalyar(sql, args = [], birlamchi = 0) {
    const r = await this.d1.prepare(sql).bind(...args).raw();
    if (!r.length || r[0][0] == null) return birlamchi;
    return r[0][0];
  }

  async ustunlar(jadval) {
    if (!_ustunlar.has(jadval)) {
      const r = await this.q(`PRAGMA table_info(${jadval})`);
      _ustunlar.set(jadval, r.map((x) => x.name));
    }
    return _ustunlar.get(jadval);
  }

  // ── sozlama / audit qilinmaydigan texnik yozuvlar ──────────────────
  async sozlama(kalit, birlamchi = null) {
    const r = await this.q1("SELECT qiymat FROM sozlama WHERE kalit=?", kalit);
    return r ? r.qiymat : birlamchi;
  }
  async sozlama_qoy(kalit, qiymat) {
    await this.d1.prepare(
      "INSERT INTO sozlama(kalit,qiymat) VALUES(?,?) " +
      "ON CONFLICT(kalit) DO UPDATE SET qiymat=excluded.qiymat").bind(kalit, qiymat).run();
  }
  /** Bir martalik xom yozuv (yuborilgan, davr kabi audit qilinmaydiganlar). */
  async exec(sql, ...args) { return this.d1.prepare(sql).bind(...args).run(); }

  async davr_yopiqmi(sana) {
    const r = await this.q1("SELECT holat FROM davr WHERE oy=?", String(sana).slice(0, 7));
    return !!(r && r.holat === "yopilgan");
  }

  /** `id%2==TOMON` bo'lgan, `jadval` dagi eng kattasidan katta keyingi id. */
  async toqId(jadval) {
    const m = await this.skalyar(`SELECT MAX(id) FROM ${jadval}`, [], 0);
    let n = m + 1;
    if (n % 2 !== TOMON) n += 1;
    return n;
  }

  amal(tavsif = "") { return new Amal(this, tavsif); }

  /** Bitta yozuv — o'z amalida (Python'dagi mustaqil `apply`). */
  async apply(jadval, amal, data = {}, qatorId = null, tavsif = "") {
    const a = this.amal(tavsif);
    const id = await a.apply(jadval, amal, data, qatorId);
    await a.commit();
    return id;
  }
}

/**
 * Bir nechta yozuv = bitta undo qadami = bitta D1 batch.
 *
 *   const a = db.amal("Rasxod qo'shildi");
 *   const rid = await a.apply("rasxod", "INSERT", {...});   // id darhol ma'lum
 *   await a.apply("ulush", "INSERT", {rasxod_id: rid, ...});
 *   await a.commit();
 *
 * DIQQAT: `apply()` yozuvni NAVBATGA qo'yadi; commit'gacha bazada ko'rinmaydi.
 * O'z yozuvini o'qishi kerak bo'lgan mantiq qiymatni JS'da hisoblasin yoki
 * avval `commit()` qilib, keyin yangi amal ochsin.
 */
export class Amal {
  constructor(db, tavsif) {
    this.db = db;
    this.tavsif = tavsif;
    this.guruh = crypto.randomUUID().replaceAll("-", "");
    this.stmts = [];
    this._idlar = new Map(); // jadval -> shu amalda berilgan oxirgi id
    this.yozildi = false;
  }

  async _keyingiId(jadval) {
    let n = this._idlar.has(jadval) ? this._idlar.get(jadval) + 2 : await this.db.toqId(jadval);
    this._idlar.set(jadval, n);
    return n;
  }

  async _jsonSql(jadval) {
    const u = await this.db.ustunlar(jadval);
    return `json_object(${u.map((c) => `'${c}',${c}`).join(",")})`;
  }

  async apply(jadval, amal, data = {}, qatorId = null, tavsif = "") {
    data = { ...(data || {}) };
    const d1 = this.db.d1;
    const t = tavsif || this.tavsif || `${amal} ${jadval}`;
    let eski = null;
    if (qatorId != null) eski = await this.db.q1(`SELECT * FROM ${jadval} WHERE id=?`, qatorId);

    if (QULFLI.has(jadval)) {
      for (const m of [data, eski || {}]) {
        if (m.sana && await this.db.davr_yopiqmi(m.sana)) {
          throw new DavrYopilgan(`${String(m.sana).slice(0, 7)} oyi yopilgan — yozuvni o'zgartirib bo'lmaydi.`);
        }
      }
    }

    const js = await this._jsonSql(jadval);
    const oldinSql = `(SELECT ${js} FROM ${jadval} WHERE id=?)`;
    let keyinNull = false;

    if (amal === "INSERT") {
      if (data.id == null) data.id = await this._keyingiId(jadval);
      qatorId = data.id;
      const u = Object.keys(data);
      this.stmts.push(d1.prepare(
        `INSERT INTO ${jadval}(${u.join(",")}) VALUES(${u.map(() => "?").join(",")})`)
        .bind(...u.map((c) => data[c])));
    } else if (amal === "UPDATE") {
      if (qatorId == null) throw new Xato("UPDATE uchun qator_id kerak");
      const u = Object.keys(data);
      if (u.length) {
        this.stmts.push(d1.prepare(`UPDATE ${jadval} SET ${u.map((c) => `${c}=?`).join(",")} WHERE id=?`)
          .bind(...u.map((c) => data[c]), qatorId));
      }
    } else if (amal === "DELETE") {
      if (qatorId == null) throw new Xato("DELETE uchun qator_id kerak");
      if ((await this.db.ustunlar(jadval)).includes("ochirilgan")) {
        this.stmts.push(d1.prepare(`UPDATE ${jadval} SET ochirilgan=1 WHERE id=?`).bind(qatorId));
      } else {
        this.stmts.push(d1.prepare(`DELETE FROM ${jadval} WHERE id=?`).bind(qatorId));
        keyinNull = true;
      }
    } else {
      throw new Xato(`noma'lum amal: ${amal}`);
    }

    // Jurnal: oldin — yozuvdan OLDINGI holat (JS'da o'qilgan), keyin — batch
    // ichida, yozuvdan keyin SQL bilan olinadi (default ustunlar ham kiradi).
    const ozId = await this._keyingiId("ozgarishlar");
    this.stmts.push(d1.prepare(
      "INSERT INTO ozgarishlar(id,guruh_id,tavsif,jadval,qator_id,amal,oldin,keyin) " +
      `VALUES(?,?,?,?,?,?,?,${keyinNull ? "NULL" : oldinSql})`)
      .bind(ozId, this.guruh, t, jadval, qatorId, amal,
        eski ? JSON.stringify(eski) : null, ...(keyinNull ? [] : [qatorId])));
    return qatorId;
  }

  async commit() {
    if (!this.stmts.length || this.yozildi) return;
    // Yangi yozuv guruhi — redo yo'li yopiladi (db.py `_redo_yolini_yop`).
    this.stmts.unshift(this.db.d1.prepare(
      "UPDATE ozgarishlar SET bekor=1 WHERE qaytarilgan=1 AND bekor=0"));
    await this.db.d1.batch(this.stmts);
    this.yozildi = true;
  }
}
