"""Hisobotlar: Excel va HTML.

Dastur bitta kompyuterda turadi, lekin hisob uchta odamniki. Shuning uchun
bu yerdagi eksportlar — Otabek va Abbosxonga yuboriladigan "chek".
HTML fayl bitta o'zi ochiladi (rasm, shrift, internet kerak emas), demak
uni Telegramga tashlab yuborsa ham to'liq ko'rinadi.
"""
from __future__ import annotations

import html
from datetime import date, timedelta
from pathlib import Path

import config
import money
from core import ledger, plan, settle


def _oraliq_nom(boshi: str, oxiri: str) -> str:
    return f"{boshi} — {oxiri}"


# ═══════════════════════════════════════════════════════════════ Excel

def excel(db, boshi: str, oxiri: str, yol: Path | str | None = None) -> Path:
    """Excel hisoboti — eski `Uy moliya.xlsx` ga o'xshash tuzilishda."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    yol = Path(yol) if yol else config.eksport_papkasi() / f"FarvonUy {boshi}_{oxiri}.xlsx"
    wb = openpyxl.Workbook()

    sarlavha = Font(bold=True, color="FFFFFF", size=11)
    fon = PatternFill("solid", fgColor="3D5A80")
    qalin = Font(bold=True)
    pul = '# ##0 "so\'m"'
    chiziq = Border(bottom=Side("thin", color="D0D0D0"))

    def jadval(ws, ustunlar, qatorlar, kengliklar):
        for i, u in enumerate(ustunlar, 1):
            c = ws.cell(1, i, u)
            c.font, c.fill = sarlavha, fon
            c.alignment = Alignment(horizontal="center", vertical="center")
        for r, qator in enumerate(qatorlar, 2):
            for i, v in enumerate(qator, 1):
                c = ws.cell(r, i, v)
                c.border = chiziq
                if isinstance(v, int) and i > 1:
                    c.number_format = pul
        for i, w in enumerate(kengliklar, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
        ws.freeze_panes = "A2"

    # ── Balans ───────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Balans"
    jadval(ws,
           ["Odam", "Kirim", "Shaxsiy", "Umumiy to'lagan", "Umumiy ulushi",
            "Uning uchun olingan", "Real balans", "Sof pozitsiya",
            "Adolatli balans"],
           [[r["nom"], r["kirim"], r["shaxsiy"], r["umumiy_tolagan"],
             r["umumiy_ulush"], r["uchun_ulush"], r["naqd"], r["sof"],
             r["adolat"]]
            for r in ledger.balanslar(db)],
           [18, 14, 14, 17, 15, 19, 15, 15, 17])

    n = len(ledger.balanslar(db)) + 3
    ws.cell(n, 1, "Hisob-kitob taklifi").font = qalin
    for i, k in enumerate(settle.taklif(db), 1):
        ws.cell(n + i, 1, f"{k.kimdan_nom} → {k.kimga_nom}")
        c = ws.cell(n + i, 2, k.summa)
        c.number_format = pul

    a = ledger.audit(db)
    ws.cell(n + 6, 1, "Kitob holati").font = qalin
    ws.cell(n + 6, 2, "TENG ✔" if a.toza else "MUAMMO ✘")

    # ── Umumiy rasxodlar ─────────────────────────────────────────────
    ws = wb.create_sheet("Umumiy rasxodlar")
    odamlar = ledger.balanslar(db)
    ustunlar = ["Sana", "Nomi", "Kategoriya", "Summa", "Kim to'ladi"] + \
               [f"{o['nom']} ulushi" for o in odamlar]
    qatorlar = []
    for r in db.q(
            "SELECT r.*, t.nom turi_nom, o.nom odam_nom FROM rasxod r"
            " LEFT JOIN turi t ON t.id=r.turi_id LEFT JOIN odam o ON o.id=r.kim_toladi"
            " WHERE r.ochirilgan=0 AND r.umumiymi=1 AND r.sana BETWEEN ? AND ?"
            " ORDER BY r.sana, r.id", boshi, oxiri):
        ul = {x["odam_id"]: x["summa"] for x in
              db.q("SELECT odam_id, summa FROM ulush WHERE rasxod_id=?", r["id"])}
        qatorlar.append([r["sana"], r["nom"], r["turi_nom"] or "", r["summa"],
                         r["odam_nom"]] + [ul.get(o["id"], 0) for o in odamlar])
    jadval(ws, ustunlar, qatorlar, [12, 26, 14, 14, 15] + [15] * len(odamlar))

    # ── Har odamning varag'i ─────────────────────────────────────────
    for o in odamlar:
        ws = wb.create_sheet(o["nom"][:28])
        jadval(ws, ["Kun", "Kirim", "Shaxsiy rasxod", "Umumiy ulushi", "Qoldiq"],
               [[k["sana"], k["kirim"], k["shaxsiy"], k["ulush"], k["qoldiq"]]
                for k in ledger.kunlik_qator(db, o["id"], boshi, oxiri)],
               [12, 14, 16, 16, 16])

    # ── Kirim / Qarz ─────────────────────────────────────────────────
    ws = wb.create_sheet("Kirim")
    jadval(ws, ["Sana", "Kim", "Summa", "Sabab"],
           [[r["sana"], r["nom"], r["summa"], r["sabab"] or ""] for r in db.q(
               "SELECT k.*, o.nom FROM kirim k JOIN odam o ON o.id=k.odam_id"
               " WHERE k.ochirilgan=0 AND k.sana BETWEEN ? AND ? ORDER BY k.sana",
               boshi, oxiri)],
           [12, 18, 14, 30])

    ws = wb.create_sheet("Qarz va hisob-kitob")
    qatorlar = [["Qarz", r["sana"], r["a"], r["b"], r["summa"], r["sabab"] or ""]
                for r in db.q(
                    "SELECT q.*, a.nom a, b.nom b FROM qarz q"
                    " JOIN odam a ON a.id=q.kim_berdi JOIN odam b ON b.id=q.kimga"
                    " WHERE q.ochirilgan=0 ORDER BY q.sana")]
    qatorlar += [["To'lov", r["sana"], r["a"], r["b"], r["summa"], r["izoh"] or ""]
                 for r in db.q(
                     "SELECT h.*, a.nom a, b.nom b FROM hisob_kitob h"
                     " JOIN odam a ON a.id=h.kim_toladi JOIN odam b ON b.id=h.kimga"
                     " WHERE h.ochirilgan=0 ORDER BY h.sana")]
    jadval(ws, ["Turi", "Sana", "Kimdan", "Kimga", "Summa", "Izoh"],
           qatorlar, [10, 12, 16, 16, 14, 30])

    yol.parent.mkdir(parents=True, exist_ok=True)
    wb.save(yol)
    return yol


# ════════════════════════════════════════════════════════════════ HTML

_CSS = """
/* Hisobot HAR DOIM oq. Ilgari `prefers-color-scheme` bilan tungi
   rejimga o'tardi va telefonda quyuq chiqib, o'qish qiyin bo'lardi.
   Bu fayl ulashish va chop etish uchun — qog'ozdek oq bo'lgani ma'qul.
   `color-scheme:light` brauzerga ham shuni aytadi, aks holda u
   aylantirgich va maydonlarni o'zicha quyuq qilib qo'yadi. */
:root{color-scheme:light;
      --fon:#f6f7f9;--karta:#fff;--matn:#1a1d21;--kul:#6b7280;
      --chiziq:#e5e7eb;--kok:#3d5a80;--yashil:#0f7b3f;--qizil:#b91c1c}
*{box-sizing:border-box}
body{margin:0;padding:28px 20px;background:var(--fon);color:var(--matn);
     font:15px/1.55 -apple-system,Segoe UI,Roboto,sans-serif}
.o{max-width:940px;margin:0 auto}
h1{font-size:24px;margin:0 0 4px}
.davr{color:var(--kul);margin-bottom:24px;font-size:14px}
.karta{background:var(--karta);border:1px solid var(--chiziq);border-radius:12px;
       padding:18px 20px;margin-bottom:18px}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.06em;
   color:var(--kul);margin:0 0 14px;font-weight:600}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.04em;
   color:var(--kul);padding:0 10px 8px;font-weight:600;border-bottom:1px solid var(--chiziq)}
td{padding:9px 10px;border-bottom:1px solid var(--chiziq)}
tr:last-child td{border-bottom:none}
.r{text-align:right}
.musbat{color:var(--yashil);font-weight:600}
.manfiy{color:var(--qizil);font-weight:600}
.katta{font-size:26px;font-weight:700;letter-spacing:-.02em}
.setka{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(215px,1fr))}
.quti{background:var(--karta);border:1px solid var(--chiziq);border-radius:12px;padding:16px 18px}
.yorliq{font-size:12px;color:var(--kul);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
.izoh{font-size:13px;color:var(--kul);margin-top:6px}
.tolov{background:var(--karta);border-left:3px solid var(--kok);padding:11px 15px;
       border-radius:0 8px 8px 0;margin-bottom:9px}
.oyoq{color:var(--kul);font-size:12px;text-align:center;margin-top:28px}
.nishon{display:inline-block;padding:3px 9px;border-radius:20px;font-size:12px;font-weight:600}
.ok{background:rgba(15,123,63,.13);color:var(--yashil)}
.xato{background:rgba(185,28,28,.13);color:var(--qizil)}
"""

# Kalendar uchun qo'shimcha. Grid `auto-fit` bilan: kompyuterda yetti
# ustun, telefonda o'zi bir-ikkitaga tushadi — hech narsa kesilmaydi.
_VAZIFA_CSS = """
.kunlar{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(165px,1fr))}
.kun{background:var(--karta);border:1px solid var(--chiziq);border-radius:12px;
     padding:12px 12px 10px}
.kun.bugun{border-color:var(--kok);box-shadow:0 0 0 2px rgba(61,90,128,.16)}
.kunbosh{font-size:13px;font-weight:700;margin-bottom:10px;
         display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.kunbosh .sana{color:var(--kul);font-weight:500;font-size:12px}
.ish{border-left:3px solid var(--kok);background:rgba(61,90,128,.07);
     border-radius:0 8px 8px 0;padding:7px 10px;margin-bottom:7px}
.ish:last-child{margin-bottom:0}
.ish .vaqt{font-size:11px;color:var(--kul);font-variant-numeric:tabular-nums}
.ish .nomi{font-size:13px;font-weight:600;margin:1px 0 2px}
.ish .kim{font-size:12px;color:var(--kul)}
.ish.bajarildi{border-left-color:var(--yashil);background:rgba(15,123,63,.07)}
.ish.bajarildi .nomi{color:var(--kul);text-decoration:line-through}
.ish.kechikkan{border-left-color:var(--qizil);background:rgba(185,28,28,.07)}
.bosh{color:var(--kul);font-size:13px;padding:4px 2px}
@media print{body{padding:0}.kun{break-inside:avoid}}
"""


def _pul(v: int, rangli: bool = False) -> str:
    s = html.escape(money.fmt(v, belgi=rangli))
    if rangli and v:
        return f'<span class="{"musbat" if v > 0 else "manfiy"}">{s}</span>'
    return s


def html_hisobot(db, boshi: str, oxiri: str,
                 yol: Path | str | None = None) -> Path:
    """Bitta o'zi ochiladigan HTML — Telegramga tashlash uchun."""
    yol = Path(yol) if yol else config.eksport_papkasi() / f"FarvonUy {boshi}_{oxiri}.html"
    qatorlar = ledger.balanslar(db)
    a = ledger.audit(db)
    p = plan.prognoz(db)

    q = []
    q.append(f"<!doctype html><html lang='uz'><head><meta charset='utf-8'>"
             f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>Farvon Uy — {html.escape(_oraliq_nom(boshi, oxiri))}</title>"
             f"<style>{_CSS}</style></head><body><div class='o'>")
    q.append(f"<h1>Farvon Uy</h1><div class='davr'>Hisobot davri: "
             f"{html.escape(_oraliq_nom(boshi, oxiri))} &nbsp;·&nbsp; "
             f"tuzildi {date.today().isoformat()}</div>")

    # umumiy raqamlar
    kirim = ledger.jami_kirim(db)
    rasxod = ledger.jami_rasxod(db)
    q.append("<div class='setka'>")
    for yorliq, qiymat, izoh in (
            ("Jami kirim", kirim, ""),
            ("Jami rasxod", rasxod, ""),
            ("Umumiy rasxod", ledger.jami_umumiy(db), "3 kishiga bo'lingan"),
            ("Qo'ldagi pul", kirim - rasxod,
             f"shu tempda {p['yetadi_kun']} kunga yetadi" if p["yetadi_kun"] else "")):
        q.append(f"<div class='quti'><div class='yorliq'>{yorliq}</div>"
                 f"<div class='katta'>{_pul(qiymat)}</div>"
                 + (f"<div class='izoh'>{html.escape(izoh)}</div>" if izoh else "")
                 + "</div>")
    q.append("</div>")

    # balanslar
    q.append("<div class='karta'><h2>Har kimning hisobi</h2><table><tr>"
             "<th>Odam</th><th class='r'>Kirim</th><th class='r'>Shaxsiy</th>"
             "<th class='r'>Umumiy ulushi</th><th class='r'>Uning uchun olingan</th>"
             "<th class='r'>Real balans</th>"
             "<th class='r'>Sof pozitsiya</th><th class='r'>Adolatli balans</th></tr>")
    for r in qatorlar:
        q.append(f"<tr><td><b>{html.escape(r['nom'])}</b></td>"
                 f"<td class='r'>{_pul(r['kirim'])}</td>"
                 f"<td class='r'>{_pul(r['shaxsiy'])}</td>"
                 f"<td class='r'>{_pul(r['umumiy_ulush'])}</td>"
                 f"<td class='r'>{_pul(r['uchun_ulush'])}</td>"
                 f"<td class='r'>{_pul(r['naqd'])}</td>"
                 f"<td class='r'>{_pul(r['sof'], True)}</td>"
                 f"<td class='r'>{_pul(r['adolat'])}</td></tr>")
    q.append("</table><div class='izoh'>"
             "<b>Uning uchun olingan</b> — boshqa odam uning o'rniga to'lagan "
             "xarid. Bu kirim emas: pul qo'liga tegmagan, faqat qarz bo'lib "
             "yozilgan.<br>"
             "<b>Real balans</b> — hozir qo'lida turgan pul. "
             "<b>Sof pozitsiya</b> — musbat bo'lsa unga qarzdorlar, manfiy bo'lsa u qarzdor. "
             "<b>Adolatli balans</b> — hamma hisoblashgandan keyin qoladigan pul "
             "(real balans + sof pozitsiya).</div></div>")

    # hisob-kitob
    kochirmalar = settle.taklif(db)
    q.append("<div class='karta'><h2>Hisob-kitob</h2>")
    if kochirmalar:
        q.append("<div class='izoh' style='margin-bottom:12px'>"
                 "Hammani tenglashtirish uchun shu to'lovlar yetarli:</div>")
        for k in kochirmalar:
            q.append(f"<div class='tolov'><b>{html.escape(k.kimdan_nom)}</b> → "
                     f"<b>{html.escape(k.kimga_nom)}</b>: "
                     f"{html.escape(money.fmt_som(k.summa))}</div>")
    else:
        q.append("<div class='izoh'>Hamma tinch — hech kim hech kimga qarzdor emas.</div>")
    q.append("</div>")

    # kategoriya
    turlar = ledger.turi_boyicha(db, boshi, oxiri)
    if turlar:
        jami = sum(t["summa"] for t in turlar) or 1
        q.append("<div class='karta'><h2>Nimaga ketdi</h2><table>"
                 "<tr><th>Kategoriya</th><th class='r'>Soni</th>"
                 "<th class='r'>Summa</th><th class='r'>Ulushi</th></tr>")
        for t in turlar:
            q.append(f"<tr><td>{html.escape(t['belgi'])} {html.escape(t['nom'])}</td>"
                     f"<td class='r'>{t['soni']}</td>"
                     f"<td class='r'>{_pul(t['summa'])}</td>"
                     f"<td class='r'>{t['summa'] / jami * 100:.0f}%</td></tr>")
        q.append("</table></div>")

    # audit
    nishon = ("<span class='nishon ok'>KITOB TENG ✔</span>" if a.toza
              else "<span class='nishon xato'>MUAMMO BOR ✘</span>")
    q.append(f"<div class='karta'><h2>Tekshiruv</h2>{nishon}"
             f"<div class='izoh'>Qarzlar yig'indisi: {a.sof_yigindi} "
             f"(nolga teng bo'lishi shart) &nbsp;·&nbsp; "
             f"Naqd pul: {_pul(a.naqd_yigindi)} = kirim − rasxod + tashqi qarz "
             f"({_pul(a.kutilgan_naqd)})</div>")
    for m in a.muammolar:
        q.append(f"<div class='izoh manfiy'>{html.escape(m)}</div>")
    q.append("</div>")

    q.append(f"<div class='oyoq'>Farvon Uy {config.VERSIYA} — "
             f"uy moliyasi hisobi</div></div></body></html>")

    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text("".join(q), encoding="utf-8")
    return yol


def odam_hisoboti(db, odam_id: int, boshi: str, oxiri: str,
                  yol: Path | str | None = None) -> Path:
    """Bitta odam uchun shaxsiy HTML — "sen shu oyda nima qilding"."""
    o = ledger.balans(db, odam_id)
    if not o:
        raise ValueError("Odam topilmadi")
    yol = Path(yol) if yol else config.eksport_papkasi() / f"{o['nom']} {boshi}_{oxiri}.html"

    q = [f"<!doctype html><html lang='uz'><head><meta charset='utf-8'>"
         f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>{html.escape(o['nom'])} — {html.escape(_oraliq_nom(boshi, oxiri))}</title>"
         f"<style>{_CSS}</style></head><body><div class='o'>",
         f"<h1>{html.escape(o['nom'])}</h1><div class='davr'>"
         f"{html.escape(_oraliq_nom(boshi, oxiri))}</div>",
         "<div class='setka'>"]
    for yorliq, qiymat, izoh in (
            ("Real balans", o["naqd"], "hozir qo'lingdagi pul"),
            ("Sof pozitsiya", o["sof"],
             "senga qarzdorlar" if o["sof"] > 0 else
             ("sen qarzdorsan" if o["sof"] < 0 else "hamma tinch")),
            ("Adolatli balans", o["adolat"], "hisoblashgandan keyin"),
            ("Sen uchun olingan", o["uchun_ulush"],
             "boshqa to'lagan — qarz" if o["uchun_ulush"] else "yo'q")):
        q.append(f"<div class='quti'><div class='yorliq'>{yorliq}</div>"
                 f"<div class='katta'>{_pul(qiymat, yorliq == 'Sof pozitsiya')}</div>"
                 f"<div class='izoh'>{html.escape(izoh)}</div></div>")
    q.append("</div>")

    q.append("<div class='karta'><h2>Kunlik harakat</h2><table><tr><th>Kun</th>"
             "<th class='r'>Kirim</th><th class='r'>Shaxsiy rasxod</th>"
             "<th class='r'>Umumiy ulushi</th><th class='r'>Qoldiq</th></tr>")
    for k in ledger.kunlik_qator(db, odam_id, boshi, oxiri):
        q.append(f"<tr><td>{k['sana']}</td><td class='r'>{_pul(k['kirim'])}</td>"
                 f"<td class='r'>{_pul(k['shaxsiy'])}</td>"
                 f"<td class='r'>{_pul(k['ulush'])}</td>"
                 f"<td class='r'>{_pul(k['qoldiq'])}</td></tr>")
    q.append("</table></div>")

    juftlar = [j for j in ledger.juft_qarzlar(db)
               if odam_id in (j.qarzdor_id, j.kreditor_id)]
    if juftlar:
        q.append("<div class='karta'><h2>Qarz holati</h2>")
        for j in juftlar:
            if j.qarzdor_id == odam_id:
                q.append(f"<div class='tolov'>Sen <b>{html.escape(j.kreditor_nom)}</b>ga "
                         f"{html.escape(money.fmt_som(j.summa))} qarzdorsan</div>")
            else:
                q.append(f"<div class='tolov'><b>{html.escape(j.qarzdor_nom)}</b> senga "
                         f"{html.escape(money.fmt_som(j.summa))} qarzdor</div>")
        q.append("</div>")

    q.append("</div></body></html>")
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text("".join(q), encoding="utf-8")
    return yol


# ═══════════════════════════════════════════════════════════ vazifalar
#
# Kalendarni ham ulashish kerak: "shu hafta kim nima qiladi" degan
# savolga javob Telegramda ham ko'rinishi kerak. HTML — o'qish uchun,
# Excel — saralash va chop etish uchun.


def _vazifa_fayl_nomi(db, dan: str, oxiri: str, odam_id, kengaytma: str) -> Path:
    if odam_id:
        o = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
        kim = (o["nom"] if o else str(odam_id))
    else:
        kim = "Umumiy"
    return config.eksport_papkasi() / f"Vazifalar {kim} {dan}_{oxiri}.{kengaytma}"


def _vazifa_qatorlari(db, dan: str, oxiri: str, odam_id=None):
    from core import vazifa as vz
    return vz.oraliq(db, dan, oxiri, odam_id)


def vazifa_html(db, dan: str, oxiri: str, odam_id=None,
                yol: Path | str | None = None) -> Path:
    """Kalendar — bitta o'zi ochiladigan HTML.

    Ustunlar kun, ichida vazifalar vaqt bo'yicha. Vaqt to'ri chizilmaydi:
    telefonda 18 soatlik to'r o'qilmaydi, ro'yxat esa o'qiladi.
    """
    from core import vazifa as vz

    yol = Path(yol) if yol else _vazifa_fayl_nomi(db, dan, oxiri, odam_id, "html")
    qatorlar = _vazifa_qatorlari(db, dan, oxiri, odam_id)
    s = vz.sanoq(db, dan, oxiri, odam_id)
    if odam_id:
        o = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
        kim = o["nom"] if o else "—"
        bosh = f"{kim} — vazifalar"
    else:
        bosh = "Uy vazifalari"

    kun_boshi, kun_oxiri = vz._sana(dan), vz._sana(oxiri)
    kunlar = []
    k = kun_boshi
    while k <= kun_oxiri:
        kunlar.append(k)
        k += timedelta(days=1)

    kun_vazifa: dict[str, list] = {}
    for r in qatorlar:
        kun_vazifa.setdefault(r["sana"], []).append(r)

    q = [f"<!doctype html><html lang='uz'><head><meta charset='utf-8'>"
         f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>{html.escape(bosh)} — {html.escape(_oraliq_nom(dan, oxiri))}"
         f"</title><style>{_CSS}{_VAZIFA_CSS}</style></head>"
         f"<body><div class='o'>"]
    q.append(f"<h1>{html.escape(bosh)}</h1><div class='davr'>"
             f"{html.escape(_oraliq_nom(dan, oxiri))} &nbsp;·&nbsp; "
             f"tuzildi {date.today().isoformat()}</div>")

    q.append("<div class='setka'>")
    for yorliq_matn, qiymat in (("Jami", s["jami"]), ("Bajarildi", s["bajarildi"]),
                                ("Qoldi", s["ochiq"]), ("Kechikkan", s["kechikkan"])):
        q.append(f"<div class='quti'><div class='yorliq'>{yorliq_matn}</div>"
                 f"<div class='katta'>{qiymat}</div></div>")
    q.append("</div>")

    bugun = date.today()
    q.append("<div class='kunlar'>")
    for kun in kunlar:
        bugunmi = " bugun" if kun == bugun else ""
        q.append(f"<div class='kun{bugunmi}'>"
                 f"<div class='kunbosh'>{html.escape(vz.KUNLAR[kun.weekday()])}"
                 f"<span class='sana'>{kun.strftime('%d.%m')}</span></div>")
        bugungi = kun_vazifa.get(kun.isoformat(), [])
        if not bugungi:
            q.append("<div class='bosh'>—</div>")
        for r in bugungi:
            bajarildi = r["holat"] == vz.BAJARILDI
            kechikkan = not bajarildi and vz._sana(r["sana"]) < bugun
            sinf = "bajarildi" if bajarildi else ("kechikkan" if kechikkan else "")
            belgi = "✓ " if bajarildi else ("⏳ " if kechikkan else "")
            q.append(
                f"<div class='ish {sinf}'>"
                f"<div class='vaqt'>{html.escape(r['vaqt'] or 'kun bo‘yi')}</div>"
                f"<div class='nomi'>{belgi}{html.escape(r['nom'])}</div>"
                f"<div class='kim'>{html.escape(r['odam'])}</div></div>")
        q.append("</div>")
    q.append("</div>")

    q.append("<div class='oyoq'>Farvon Uy · vazifalar kalendari</div>")
    q.append("</div></body></html>")
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text("".join(q), encoding="utf-8")
    return yol


def vazifa_excel(db, dan: str, oxiri: str, odam_id=None,
                 yol: Path | str | None = None) -> Path:
    """Kalendar — Excel. Ikkita varaq: ro'yxat va odamlar bo'yicha xulosa."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    from core import vazifa as vz

    yol = Path(yol) if yol else _vazifa_fayl_nomi(db, dan, oxiri, odam_id, "xlsx")
    qatorlar = _vazifa_qatorlari(db, dan, oxiri, odam_id)

    wb = openpyxl.Workbook()
    sarlavha = Font(bold=True, color="FFFFFF", size=11)
    fon = PatternFill("solid", fgColor="3D5A80")
    chiziq = Border(bottom=Side("thin", color="D0D0D0"))

    ws = wb.active
    ws.title = "Vazifalar"
    ustunlar = ["Kun", "Sana", "Vaqt", "Vazifa", "Kim bajaradi", "Holati",
                "Davomiyligi"]
    for i, u in enumerate(ustunlar, 1):
        c = ws.cell(1, i, u)
        c.font, c.fill = sarlavha, fon
        c.alignment = Alignment(horizontal="center", vertical="center")

    bugun = date.today()
    for r_i, r in enumerate(qatorlar, 2):
        kun = vz._sana(r["sana"])
        bajarildi = r["holat"] == vz.BAJARILDI
        holat = ("Bajarildi" if bajarildi
                 else "Qazo" if r["holat"] == vz.QAZO
                 else ("Kechikkan" if kun < bugun else "Kutilmoqda"))
        qiymatlar = [vz.KUNLAR[kun.weekday()], kun.strftime("%d.%m.%Y"),
                     r["vaqt"] or "kun bo'yi", r["nom"], r["odam"], holat,
                     f"{r['davomiylik']} daqiqa"]
        for i, v in enumerate(qiymatlar, 1):
            ws.cell(r_i, i, v).border = chiziq
    for i, w in enumerate([14, 13, 11, 46, 16, 14, 14], 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:G{max(2, len(qatorlar) + 1)}"

    # ── xulosa
    ws2 = wb.create_sheet("Xulosa")
    for i, u in enumerate(["Odam", "Jami", "Bajarildi", "Qoldi", "Kechikkan"], 1):
        c = ws2.cell(1, i, u)
        c.font, c.fill = sarlavha, fon
        c.alignment = Alignment(horizontal="center", vertical="center")
    odamlar = ([db.q1("SELECT id, nom FROM odam WHERE id=?", odam_id)]
               if odam_id else vz.navbat_odamlari(db))
    for r_i, o in enumerate([x for x in odamlar if x], 2):
        s = vz.sanoq(db, dan, oxiri, o["id"])
        for i, v in enumerate([o["nom"], s["jami"], s["bajarildi"],
                               s["ochiq"], s["kechikkan"]], 1):
            ws2.cell(r_i, i, v).border = chiziq
    for i, w in enumerate([18, 10, 12, 10, 12], 1):
        ws2.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws2.freeze_panes = "A2"

    yol.parent.mkdir(parents=True, exist_ok=True)
    wb.save(yol)
    return yol


# ═════════════════════════════════════════ umumiy rasxod hisobotlari
#
# Ikkita hisobot, ikkalasi ham FAQAT umumiy rasxodni ko'radi
# (`umumiymi=1`). Shaxsiy rasxod bu yerga umuman kirmaydi: u
# odamning o'z puli va uni jamoaga ko'rsatishning ma'nosi yo'q.
#
#   umumiy_rasxod_*  — uy nimaga qancha sarfladi;
#   shaxsiy_ulush_*  — o'sha umumiy rasxoddan har kimga qancha tushdi.
#
# Ikkinchisi «mening rasxodim» EMAS: bu umumiy xaridning shu odamga
# to'g'ri keladigan qismi (`ulush` jadvali). Shuning uchun ustunlar
# to'lovchi bilan ulushdorni ajratib ko'rsatadi — «men to'ladim» va
# «bu menga tushdi» ikki xil narsa.


def _umumiy_rasxodlar(db, dan: str, oxiri: str) -> list:
    return db.q(
        "SELECT r.id, r.sana, r.nom, r.summa, r.bolish_usul,"
        "       COALESCE(t.nom,'—') turi_nom, COALESCE(t.belgi,'') belgi,"
        "       o.nom tolagan"
        " FROM rasxod r"
        " LEFT JOIN turi t ON t.id = r.turi_id"
        " JOIN odam o ON o.id = r.kim_toladi"
        " WHERE r.ochirilgan=0 AND r.umumiymi=1 AND r.sana BETWEEN ? AND ?"
        " ORDER BY r.sana, r.id", dan, oxiri)


def _ulush_qatorlari(db, dan: str, oxiri: str, odam_id=None) -> list:
    p = [dan, oxiri]
    shart = ""
    if odam_id:
        shart = " AND u.odam_id=?"
        p.append(odam_id)
    return db.q(
        "SELECT u.odam_id, u.summa, u.tolandi, o.nom odam,"
        "       r.id rasxod_id, r.sana, r.nom, COALESCE(t.nom,'—') turi_nom,"
        "       r.summa jami, tol.nom tolagan"
        " FROM ulush u"
        " JOIN rasxod r ON r.id = u.rasxod_id"
        " JOIN odam o ON o.id = u.odam_id"
        " JOIN odam tol ON tol.id = r.kim_toladi"
        " LEFT JOIN turi t ON t.id = r.turi_id"
        " WHERE r.ochirilgan=0 AND r.umumiymi=1"
        "   AND r.sana BETWEEN ? AND ?" + shart +
        " ORDER BY o.tartib, o.id, r.sana, r.id", *p)


def _rasxod_fayl_nomi(db, tur: str, dan: str, oxiri: str, odam_id,
                      kengaytma: str) -> Path:
    if odam_id:
        o = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
        kim = " " + (o["nom"] if o else str(odam_id))
    else:
        kim = ""
    return (config.eksport_papkasi()
            / f"{tur}{kim} {dan}_{oxiri}.{kengaytma}")


def umumiy_rasxod_html(db, dan: str, oxiri: str,
                       yol: Path | str | None = None) -> Path:
    """Uy nimaga qancha sarfladi — faqat UMUMIY rasxod."""
    yol = Path(yol) if yol else _rasxod_fayl_nomi(
        db, "Umumiy rasxodlar", dan, oxiri, None, "html")
    qatorlar = _umumiy_rasxodlar(db, dan, oxiri)
    jami = sum(r["summa"] for r in qatorlar)

    turlar: dict[str, int] = {}
    for r in qatorlar:
        turlar[r["turi_nom"]] = turlar.get(r["turi_nom"], 0) + r["summa"]

    q = [f"<!doctype html><html lang='uz'><head><meta charset='utf-8'>"
         f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>Umumiy rasxodlar — {html.escape(_oraliq_nom(dan, oxiri))}"
         f"</title><style>{_CSS}</style></head><body><div class='o'>"]
    q.append(f"<h1>Umumiy rasxodlar</h1><div class='davr'>"
             f"{html.escape(_oraliq_nom(dan, oxiri))} &nbsp;·&nbsp; "
             f"tuzildi {date.today().isoformat()}</div>")

    q.append("<div class='setka'>")
    q.append(f"<div class='quti'><div class='yorliq'>Jami</div>"
             f"<div class='katta'>{_pul(jami)}</div></div>")
    q.append(f"<div class='quti'><div class='yorliq'>Yozuvlar</div>"
             f"<div class='katta'>{len(qatorlar)}</div></div>")
    q.append("</div>")

    if turlar:
        q.append("<div class='karta'><h2>Turlar bo'yicha</h2><table><tr><th>Turi</th>"
                 "<th class='r'>Summa</th><th class='r'>Ulushi</th></tr>")
        for nom, summa in sorted(turlar.items(), key=lambda x: -x[1]):
            ulush = (summa * 100 // jami) if jami else 0
            q.append(f"<tr><td>{html.escape(nom)}</td>"
                     f"<td class='r'>{_pul(summa)}</td>"
                     f"<td class='r'>{ulush}%</td></tr>")
        q.append("</table></div>")

    q.append("<div class='karta'><h2>Yozuvlar</h2><table><tr><th>Sana</th><th>Nomi</th>"
             "<th>Turi</th><th>To'ladi</th><th class='r'>Summa</th></tr>")
    if not qatorlar:
        q.append("<tr><td colspan='5'>Bu oraliqda umumiy rasxod yo'q.</td></tr>")
    for r in qatorlar:
        q.append(f"<tr><td>{html.escape(str(r['sana']))}</td>"
                 f"<td>{html.escape(r['nom'] or '—')}</td>"
                 f"<td>{html.escape(r['belgi'])} "
                 f"{html.escape(r['turi_nom'])}</td>"
                 f"<td>{html.escape(r['tolagan'])}</td>"
                 f"<td class='r'>{_pul(r['summa'])}</td></tr>")
    q.append(f"<tr><td colspan='4'><b>Jami</b></td>"
             f"<td class='r'><b>{_pul(jami)}</b></td></tr>")
    q.append("</table></div>")
    q.append("<div class='izoh'>Farvon Uy · umumiy rasxodlar</div>")
    q.append("</div></body></html>")

    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text("".join(q), encoding="utf-8")
    return yol


def shaxsiy_ulush_html(db, dan: str, oxiri: str, odam_id=None,
                       yol: Path | str | None = None) -> Path:
    """Umumiy rasxoddan har kimga qancha tushgani.

    «Mening rasxodim» EMAS: umumiy xaridning shu odamga to'g'ri
    keladigan qismi. To'lagan odam ham o'z ulushini ko'radi — u pulni
    chiqargan bo'lsa ham, ulush baribir uniki.
    """
    yol = Path(yol) if yol else _rasxod_fayl_nomi(
        db, "Shaxsiy ulush", dan, oxiri, odam_id, "html")
    qatorlar = _ulush_qatorlari(db, dan, oxiri, odam_id)

    odamlar: dict[int, dict] = {}
    for r in qatorlar:
        d = odamlar.setdefault(r["odam_id"], {
            "nom": r["odam"], "jami": 0, "tolangan": 0, "qatorlar": []})
        d["jami"] += r["summa"]
        if r["tolandi"]:
            d["tolangan"] += r["summa"]
        d["qatorlar"].append(r)

    bosh = "Shaxsiy ulush"
    if odam_id:
        o = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
        bosh = f"{o['nom'] if o else '—'} — umumiy rasxoddan ulushi"

    q = [f"<!doctype html><html lang='uz'><head><meta charset='utf-8'>"
         f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>{html.escape(bosh)} — "
         f"{html.escape(_oraliq_nom(dan, oxiri))}"
         f"</title><style>{_CSS}</style></head><body><div class='o'>"]
    q.append(f"<h1>{html.escape(bosh)}</h1><div class='davr'>"
             f"{html.escape(_oraliq_nom(dan, oxiri))} &nbsp;·&nbsp; "
             f"faqat umumiy rasxod &nbsp;·&nbsp; "
             f"tuzildi {date.today().isoformat()}</div>")

    if not odamlar:
        q.append("<p>Bu oraliqda umumiy rasxod yo'q.</p>")

    q.append("<div class='setka'>")
    for d in odamlar.values():
        q.append(f"<div class='quti'><div class='yorliq'>"
                 f"{html.escape(d['nom'])}</div>"
                 f"<div class='katta'>{_pul(d['jami'])}</div></div>")
    q.append("</div>")

    for d in odamlar.values():
        q.append(f"<div class='karta'><h2>{html.escape(d['nom'])}</h2>")
        q.append("<table><tr><th>Sana</th><th>Nomi</th><th>Turi</th>"
                 "<th>To'ladi</th><th class='r'>Xarid</th>"
                 "<th class='r'>Ulushi</th></tr>")
        for r in d["qatorlar"]:
            q.append(f"<tr><td>{html.escape(str(r['sana']))}</td>"
                     f"<td>{html.escape(r['nom'] or '—')}</td>"
                     f"<td>{html.escape(r['turi_nom'])}</td>"
                     f"<td>{html.escape(r['tolagan'])}</td>"
                     f"<td class='r'>{_pul(r['jami'])}</td>"
                     f"<td class='r'>{_pul(r['summa'])}</td></tr>")
        q.append(f"<tr><td colspan='5'><b>Jami ulushi</b></td>"
                 f"<td class='r'><b>{_pul(d['jami'])}</b></td></tr>")
        q.append("</table></div>")

    q.append("<div class='izoh'>Farvon Uy · umumiy rasxoddan ulushlar</div>")
    q.append("</div></body></html>")

    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text("".join(q), encoding="utf-8")
    return yol


def _varaqni_bezash(varaq, sarlavhalar, kengliklar):
    """Excel varag'ining sarlavha qatori — hamma hisobotda bir xil."""
    from openpyxl.styles import Alignment, Font, PatternFill
    varaq.append(sarlavhalar)
    for i, (nom, en) in enumerate(zip(sarlavhalar, kengliklar), start=1):
        katak = varaq.cell(row=1, column=i)
        katak.font = Font(bold=True, color="FFFFFF")
        katak.fill = PatternFill("solid", fgColor="4A40BE")
        katak.alignment = Alignment(horizontal="center")
        varaq.column_dimensions[katak.column_letter].width = en
    varaq.freeze_panes = "A2"


def umumiy_rasxod_excel(db, dan: str, oxiri: str,
                        yol: Path | str | None = None) -> Path:
    import openpyxl
    from openpyxl.styles import Font

    yol = Path(yol) if yol else _rasxod_fayl_nomi(
        db, "Umumiy rasxodlar", dan, oxiri, None, "xlsx")
    qatorlar = _umumiy_rasxodlar(db, dan, oxiri)

    kitob = openpyxl.Workbook()
    v = kitob.active
    v.title = "Umumiy rasxod"
    _varaqni_bezash(v, ["Sana", "Nomi", "Turi", "To'ladi", "Summa"],
                    [12, 34, 16, 16, 16])
    for r in qatorlar:
        v.append([str(r["sana"]), r["nom"] or "—", r["turi_nom"],
                  r["tolagan"], r["summa"]])
    jami = sum(r["summa"] for r in qatorlar)
    v.append(["", "", "", "JAMI", jami])
    for katak in v[v.max_row]:
        katak.font = Font(bold=True)
    for qator in v.iter_rows(min_row=2, min_col=5, max_col=5):
        for katak in qator:
            katak.number_format = "#,##0"

    x = kitob.create_sheet("Turlar")
    _varaqni_bezash(x, ["Turi", "Summa", "Ulushi"], [22, 16, 10])
    turlar: dict[str, int] = {}
    for r in qatorlar:
        turlar[r["turi_nom"]] = turlar.get(r["turi_nom"], 0) + r["summa"]
    for nom, summa in sorted(turlar.items(), key=lambda t: -t[1]):
        x.append([nom, summa, (summa / jami if jami else 0)])
    for qator in x.iter_rows(min_row=2, min_col=2, max_col=3):
        qator[0].number_format = "#,##0"
        qator[1].number_format = "0.0%"

    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    kitob.save(yol)
    return yol


def shaxsiy_ulush_excel(db, dan: str, oxiri: str, odam_id=None,
                        yol: Path | str | None = None) -> Path:
    import openpyxl
    from openpyxl.styles import Font

    yol = Path(yol) if yol else _rasxod_fayl_nomi(
        db, "Shaxsiy ulush", dan, oxiri, odam_id, "xlsx")
    qatorlar = _ulush_qatorlari(db, dan, oxiri, odam_id)

    kitob = openpyxl.Workbook()
    v = kitob.active
    v.title = "Ulushlar"
    _varaqni_bezash(v, ["Odam", "Sana", "Nomi", "Turi", "To'ladi",
                        "Xarid", "Ulushi", "To'landi"],
                    [16, 12, 30, 16, 16, 14, 14, 10])
    for r in qatorlar:
        v.append([r["odam"], str(r["sana"]), r["nom"] or "—", r["turi_nom"],
                  r["tolagan"], r["jami"], r["summa"],
                  "Ha" if r["tolandi"] else ""])
    for qator in v.iter_rows(min_row=2, min_col=6, max_col=7):
        for katak in qator:
            katak.number_format = "#,##0"

    x = kitob.create_sheet("Xulosa")
    _varaqni_bezash(x, ["Odam", "Ulushi jami", "To'langan"], [18, 16, 16])
    xulosa: dict[str, list] = {}
    for r in qatorlar:
        d = xulosa.setdefault(r["odam"], [0, 0])
        d[0] += r["summa"]
        if r["tolandi"]:
            d[1] += r["summa"]
    for nom, (jami, tolangan) in xulosa.items():
        x.append([nom, jami, tolangan])
    for qator in x.iter_rows(min_row=2, min_col=2, max_col=3):
        for katak in qator:
            katak.number_format = "#,##0"
    if x.max_row > 1:
        for katak in x[x.max_row]:
            katak.font = Font(bold=False)

    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    kitob.save(yol)
    return yol
