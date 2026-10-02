// Hamyon — faqat botga kerak bo'lgan qism (Python `core/hamyon.py`).

// hamyon.py:90
/** Karta shu odamniki va o'chirilmagan bo'lishi SHART (null — naqd). */
export async function tekshir_karta(db, karta_id, odam_id) {
  if (karta_id == null) return;
  if (!await db.q1("SELECT 1 FROM karta WHERE id=? AND odam_id IS ? AND ochirilgan=0",
    karta_id, odam_id ?? null)) {
    throw new Error("Bu karta to'lovchiniki emas yoki o'chirilgan — " +
      "«Qayerdan» ni qayta tanlang.");
  }
}
