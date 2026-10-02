// Ikonkali rasxod kategoriyalari — Python `core/kategoriya.py` ning botga kerak qismi.
//
// Python ikonkalar ro'yxatini `src/belgilar/*.png` papkasidan o'qiydi. Worker'da
// disk yo'q: ro'yxat shu yerda (guruh → fayllar soni, `food_01.png` … `food_29.png`).
// SVG'lari `worker/app/belgilar/<kalit>.svg` (statik). Ro'yxat Python
// `kategoriya.belgilar()` bilan bir xilligi testda tekshiriladi
// (test/miniapp_sozlama.test.js) — ikonka qo'shilsa shu jadvalni yangilang.

// kategoriya.py:27
/** Foydalanuvchi ro'yxatdan olib tashlashni so'ragan ikonkalar (robot, xoch). */
export const YASHIRIN = new Set(["education_08.png", "health_08.png"]);

// Guruh → fayllar soni (raqamlar 01 dan uzluksiz).
const _SONI = {
  education: 15, entertainment: 15, finance: 10, food: 29, health: 17, life: 20,
  office: 13, others: 17, personal: 10, shopping: 19, sports: 17, transportation: 10,
  travel: 8,
};

const _BELGILAR = Object.keys(_SONI).sort()
  .flatMap((g) => Array.from({ length: _SONI[g] }, (_, i) => `${g}_${String(i + 1).padStart(2, "0")}.png`))
  .filter((f) => !YASHIRIN.has(f))
  .sort();

// kategoriya.py:30
/** Hamma ikonka fayllari — guruhlab, tartib bilan (yashirinlarsiz). */
export function belgilar() {
  return _BELGILAR.slice();
}

// kategoriya.py:42
/** Skrinshotlardagi bo'lim nomlari — ikonka nomi EMAS, faqat guruh sarlavhasi. */
export const GURUH_NOMI = {
  education: "Ta'lim",
  entertainment: "Ko'ngilochar",
  finance: "Moliya",
  food: "Oziq-ovqat",
  health: "Salomatlik",
  life: "Turmush",
  office: "Ofis",
  others: "Boshqalar",
  personal: "Shaxsiy",
  shopping: "Xarid",
  sports: "Sport",
  transportation: "Transport",
  travel: "Sayohat",
};

// kategoriya.py:58
/** `food_03.png` → `food`. */
export function guruh(fayl) {
  const i = fayl.lastIndexOf("_");
  return i < 0 ? fayl : fayl.slice(0, i);
}

// kategoriya.py:63
export function guruh_nomi(g) {
  return GURUH_NOMI[g] ?? (g.charAt(0).toUpperCase() + g.slice(1).toLowerCase());
}

// kategoriya.py:74
/** ikonka fayli → faol kategoriya ({id, nom, rasm}). Map — qo'shilish tartibi. */
export async function nomlanganlar(db) {
  const m = new Map();
  for (const r of await db.q("SELECT id, nom, rasm FROM turi WHERE faol=1 AND rasm IS NOT NULL")) {
    m.set(r.rasm, { ...r });
  }
  return m;
}
