// Menyu — oshpaz tanlaydigan taomlar. Python `src/core/menyu.py` egizagi (bot qismi).

// menyu.py:14
export async function royxat(db) {
  return db.q("SELECT * FROM menyu WHERE ochirilgan=0 ORDER BY tartib, id");
}

// menyu.py:19
export async function bitta(db, menyu_id) {
  return db.q1("SELECT * FROM menyu WHERE id=? AND ochirilgan=0", menyu_id);
}
