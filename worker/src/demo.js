// Demo rejim (taqdimot): yoqilgan odamning Mini App'i soxta ma'lumotli
// alohida D1 dan (`env.DEMO_DB`, `tools/demo_d1.sh`) ishlaydi.
//
// Holat HAQIQIY bazada, har odamga alohida: `sozlama.miniapp_demo:<odam_id>`.
// Bu texnik holat (`tg_rx:<chat>` kabi) — undo/jurnalga tushmaydi, desktop
// bu kalitni yozmaydi. Almashtirish: botda /demo yoki Mini App → Sozlamalar.

export const kalit = (odam_id) => `miniapp_demo:${odam_id}`;

export async function yoqiqmi(db, odam_id) {
  return (await db.sozlama(kalit(odam_id), "0")) === "1";
}

export async function qoy(db, odam_id, yoq) {
  await db.sozlama_qoy(kalit(odam_id), yoq ? "1" : "0");
  return !!yoq;
}

/** Demo bazada «men» — asosiy odam (`plan.asosiy_odam` qoidasi). */
export async function demoOdam(db) {
  const r = await db.q1("SELECT qiymat FROM sozlama WHERE kalit='asosiy_odam'");
  if (r?.qiymat) {
    const o = await db.q1("SELECT id, nom FROM odam WHERE faol=1 AND id=?", Number(r.qiymat));
    if (o) return o;
  }
  return (await db.q1("SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id")) || null;
}

const YOQ = new Set(["on", "yoq", "yoqish", "1", "ha"]);
const OCHIR = new Set(["off", "ochir", "o'chir", "uchir", "0", "yo'q", "yoq emas"]);

/** «/demo», «/demo on», «/demo off» → yangi holat; boshqa matn → null. */
export async function buyruq(db, odam_id, matn) {
  const m = String(matn || "").trim().toLowerCase().replace(/[‘’ʻʼ`]/g, "'");
  const r = m.match(/^\/demo(?:@\w+)?(?:\s+(.+))?$/);
  if (!r) return null;
  const arg = (r[1] || "").trim();
  let yangi;
  if (YOQ.has(arg)) yangi = true;
  else if (OCHIR.has(arg)) yangi = false;
  else yangi = !(await yoqiqmi(db, odam_id));
  return qoy(db, odam_id, yangi);
}

export function javobMatn(yoqiq) {
  return yoqiq
    ? "🎭 <b>Demo rejim YOQILDI</b>\n\nBot menyusi va Mini App endi faqat soxta " +
      "ma'lumot ko'rsatadi (Sardor, Jasur, Bekzod). Haqiqiy pulingiz va vazifalaringiz " +
      "ko'rinmaydi, ularga hech narsa yozilmaydi; shaxsiy eslatmalar demo " +
      "o'chguncha ushlab turiladi.\n\nO'chirish: /demo"
    : "✅ <b>Demo rejim o'chirildi</b>\n\nBot va Mini App yana haqiqiy ma'lumotingizni ko'rsatadi.";
}
