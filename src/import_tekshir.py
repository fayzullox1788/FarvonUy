"""Excel importini tekshirish — haqiqiy `Uy moliya.xlsx` ustida.

    py -3.14 src\\import_tekshir.py "C:\\Users\\Acer\\Desktop\\Uy moliya.xlsx"
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
for _o in (sys.stdout, sys.stderr):
    try:
        _o.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_TMP = Path(tempfile.mkdtemp(prefix="farvonuy-imp-"))
os.environ["FARVONUY_DATA"] = str(_TMP)

import money        # noqa: E402
import db as dbm    # noqa: E402
from core import importer, ledger, settle  # noqa: E402

yol = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Acer\Desktop\Uy moliya.xlsx"

d = dbm.Db()
n = importer.import_qil(d, yol)
print(n.hisobot())

print("\n── Balanslar ────────────────────────────────────────────────")
print(f"{'Odam':<14}{'Kirim':>12}{'Shaxsiy':>12}{'Ulush':>12}"
      f"{'Naqd':>13}{'Sof':>13}{'Adolat':>13}")
for r in ledger.balanslar(d):
    print(f"{r['nom']:<14}{money.fmt(r['kirim']):>12}{money.fmt(r['shaxsiy']):>12}"
          f"{money.fmt(r['umumiy_ulush']):>12}{money.fmt(r['naqd']):>13}"
          f"{money.fmt(r['sof'], True):>13}{money.fmt(r['adolat']):>13}")

print("\n── Kim kimga qarzdor ────────────────────────────────────────")
for j in ledger.juft_qarzlar(d):
    print(f"  {j.qarzdor_nom} → {j.kreditor_nom}: {money.fmt_som(j.summa)}")

print("\n── Hisob-kitob taklifi ──────────────────────────────────────")
for k in settle.taklif(d):
    print("  " + str(k))

print("\n── Audit ────────────────────────────────────────────────────")
a = ledger.audit(d)
print(f"  Jami kirim   : {money.fmt_som(ledger.jami_kirim(d))}")
print(f"  Jami rasxod  : {money.fmt_som(ledger.jami_rasxod(d))}")
print(f"  Umumiy rasxod: {money.fmt_som(ledger.jami_umumiy(d))}")
print(f"  SUM(sof)     : {a.sof_yigindi}  (0 bo'lishi shart)")
print(f"  SUM(naqd)    : {money.fmt(a.naqd_yigindi)}  "
      f"kutilgan {money.fmt(a.kutilgan_naqd)}")
print(f"  Yaxlitlash   : " + ", ".join(
    f"{r['nom']} +{r['ortiqcha']}" for r in d.q("SELECT * FROM v_yaxlitlash")))
print(f"\n  HOLAT: {'✔ KITOB TENG' if a.toza else '✘ MUAMMO BOR'}")
for m in a.muammolar:
    print("   -", m)

d.yop()
shutil.rmtree(_TMP, ignore_errors=True)
sys.exit(0 if a.toza else 1)
