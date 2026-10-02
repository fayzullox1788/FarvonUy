// Reja — botga kerak bo'lgan qism (Python `core/plan.py`).

// plan.py:1019
/** Shu kategoriya (va ichki kategoriyalari) mahsulotlari — narxi bilan. */
export async function turi_itemlari(db, turi_id) {
  if (turi_id == null) {
    return db.q("SELECT * FROM item WHERE faol=1 AND ochirilgan=0" +
      " AND turi_id IS NULL ORDER BY nom");
  }
  return db.q(
    "WITH RECURSIVE a(id) AS (SELECT ?" +
    " UNION SELECT t.id FROM turi t JOIN a ON t.ota_id=a.id)" +
    " SELECT i.*, t.nom turi_nom, (i.turi_id<>?) ichkida FROM item i" +
    " JOIN turi t ON t.id=i.turi_id" +
    " WHERE i.faol=1 AND i.ochirilgan=0 AND i.turi_id IN (SELECT id FROM a)" +
    " ORDER BY ichkida, t.tartib, i.nom COLLATE NOCASE", turi_id, turi_id);
}
