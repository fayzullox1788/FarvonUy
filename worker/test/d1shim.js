// D1Database API'sining node:sqlite ustidagi taqlidi — testlar uchun.
// Worker kodi aynan shu metodlarni ishlatadi: prepare().bind().all/first/raw/run,
// batch(). Prod'da haqiqiy D1, testda bu — kod bir xil.
import { DatabaseSync } from "node:sqlite";

class Stmt {
  constructor(db, sql) { this.db = db; this.sql = sql; this.args = []; }
  bind(...args) {
    const s = new Stmt(this.db, this.sql);
    s.args = args.map((a) => (a === undefined ? null : typeof a === "boolean" ? Number(a) : a));
    return s;
  }
  _p() { return this.db.prepare(this.sql); }
  async all() { return { results: this._p().all(...this.args).map(oddiy), success: true, meta: {} }; }
  async first(col) {
    const r = this._p().get(...this.args);
    if (!r) return null;
    return col ? r[col] : oddiy(r);
  }
  async raw() {
    const p = this._p();
    p.setReturnArrays?.(true);
    const rows = p.all(...this.args);
    return rows.map((r) => (Array.isArray(r) ? r : Object.values(r)));
  }
  async run() { return this._run(); }
  _run() {
    const r = this._p().run(...this.args);
    return { success: true, meta: { last_row_id: Number(r.lastInsertRowid), changes: Number(r.changes) } };
  }
}

// node:sqlite null-prototype obyekt qaytaradi; D1 oddiy obyekt beradi.
const oddiy = (r) => ({ ...r });

export class D1Shim {
  /** @param {string} yol — ":memory:" yoki fayl yo'li */
  constructor(yol = ":memory:") {
    this.db = new DatabaseSync(yol);
    this.db.exec("PRAGMA foreign_keys=ON");
  }
  prepare(sql) { return new Stmt(this.db, sql); }
  async batch(stmts) {
    this.db.exec("BEGIN");
    try {
      const out = stmts.map((s) => s._run());
      this.db.exec("COMMIT");
      return out;
    } catch (e) {
      this.db.exec("ROLLBACK");
      throw e;
    }
  }
  async exec(sql) { this.db.exec(sql); return { count: 1 }; }
}
