"""Pul va bo'lish.

Ikkita qat'iy qoida:

1. **Pul har doim butun son (so'm).** Hech qanday float yo'q. Excel'dagi
   519,666.6666... kabi qiymatlar bu yerda umuman paydo bo'lmaydi.

2. **Bo'lishdagi qoldiq yo'qolmaydi.** 1,559,000 ni 3 ga bo'lsak
   519,666 + 519,667 + 519,667 chiqadi — yig'indisi aynan 1,559,000.
   Ortiqcha so'mni kim olishi tasodifiy emas: shu paytgacha eng kam
   ortiqcha so'm olgan odam oladi. Shuning uchun vaqt o'tishi bilan
   yaxlitlash hech kimga zarar qilmaydi va har doim isbotlanadi.
"""
from __future__ import annotations

from dataclasses import dataclass

VERGUL = " "  # ajratmaydigan probel — 1 559 000


# ──────────────────────────────────────────────────────────── formatlash

def fmt(summa: int | float | None, belgi: bool = False) -> str:
    """1559000 -> '1 559 000'.  belgi=True bo'lsa musbat oldiga '+' qo'yadi."""
    if summa is None:
        return "—"
    s = int(round(summa))
    ishora = "-" if s < 0 else ("+" if (belgi and s > 0) else "")
    return ishora + f"{abs(s):,}".replace(",", VERGUL)


def fmt_som(summa: int | float | None, belgi: bool = False) -> str:
    if summa is None:
        return "—"
    return f"{fmt(summa, belgi)} so'm"


def parse(matn: str) -> int:
    """'1 559 000', '1559000', '1.559.000', '1559k', '1,5 mln' -> butun so'm.

    Bo'sh yoki tushunarsiz matn uchun ValueError.
    """
    if matn is None:
        raise ValueError("bo'sh")
    t = str(matn).strip().lower()
    t = t.replace("so'm", "").replace("som", "").replace("sum", "").strip()
    if not t:
        raise ValueError("bo'sh")

    kopaytir = 1
    for qoshimcha, k in (("mln", 1_000_000), ("million", 1_000_000),
                         ("ming", 1_000), ("k", 1_000), ("m", 1_000_000)):
        if t.endswith(qoshimcha):
            kopaytir = k
            t = t[: -len(qoshimcha)].strip()
            break

    # ajratgichlarni tozalash
    t = t.replace(VERGUL, "").replace(" ", "").replace(" ", "")
    if kopaytir > 1:
        t = t.replace(",", ".")            # 1,5 mln -> 1.5
        qiymat = float(t) * kopaytir
    else:
        t = t.replace(",", "").replace(".", "")
        if not t or not (t.lstrip("-").isdigit()):
            raise ValueError(f"pul emas: {matn!r}")
        qiymat = float(t)

    return int(round(qiymat))


# ────────────────────────────────────────────────────────────── bo'lish

@dataclass(frozen=True)
class Ulush:
    odam_id: int
    summa: int
    yaxlitlash: int = 0    # shu odamga tushgan ortiqcha so'm (0 yoki 1)


def bol_tortli(jami: int, ogirliklar: dict[int, float],
               qarz_tarixi: dict[int, int] | None = None) -> list[Ulush]:
    """`jami` ni og'irliklar bo'yicha bo'ladi. Yig'indi ANIQ `jami` ga teng.

    ogirliklar  : {odam_id: og'irlik}. Teng bo'lish uchun hammasi 1.
    qarz_tarixi : {odam_id: shu paytgacha olgan ortiqcha so'm}. Ortiqcha
                  so'm eng kam olganga beriladi — adolat vaqt bo'yicha
                  tenglashadi.

    Eng katta qoldiq usuli (largest remainder), determinlashtirilgan
    tie-break bilan: bir xil kirish har doim bir xil natija beradi.
    """
    ids = [i for i, w in ogirliklar.items() if w > 0]
    if not ids:
        raise ValueError("bo'linadigan odam yo'q")
    if jami == 0:
        return [Ulush(i, 0, 0) for i in ids]

    manfiy = jami < 0
    j = abs(jami)

    W = sum(ogirliklar[i] for i in ids)
    xom = {i: j * ogirliklar[i] / W for i in ids}
    asos = {i: int(xom[i] // 1) for i in ids}
    qoldiq = j - sum(asos.values())

    tarix = qarz_tarixi or {}
    # kasr qismi katta bo'lgan oldin; teng bo'lsa — kam ortiqcha olgan oldin;
    # u ham teng bo'lsa — id bo'yicha (barqaror)
    navbat = sorted(ids, key=lambda i: (-(xom[i] - asos[i]), tarix.get(i, 0), i))

    extra = {i: 0 for i in ids}
    for i in navbat[:qoldiq]:
        asos[i] += 1
        extra[i] = 1

    ishora = -1 if manfiy else 1
    natija = [Ulush(i, ishora * asos[i], extra[i]) for i in ids]
    assert sum(u.summa for u in natija) == jami, "bo'lish yig'indisi buzildi"
    return natija


def bol_teng(jami: int, odamlar: list[int],
             qarz_tarixi: dict[int, int] | None = None) -> list[Ulush]:
    return bol_tortli(jami, {i: 1.0 for i in odamlar}, qarz_tarixi)


def bol_foiz(jami: int, foizlar: dict[int, float],
             qarz_tarixi: dict[int, int] | None = None) -> list[Ulush]:
    """Foizlar 100 ga teng bo'lishi shart emas — nisbat sifatida olinadi."""
    return bol_tortli(jami, foizlar, qarz_tarixi)


def bol_aniq(jami: int, summalar: dict[int, int]) -> list[Ulush]:
    """Har kimning ulushi qo'lda kiritilgan. Yig'indi `jami` ga teng bo'lishi shart."""
    s = sum(summalar.values())
    if s != jami:
        raise ValueError(
            f"aniq ulushlar yig'indisi {fmt(s)} — rasxod {fmt(jami)} ga teng emas "
            f"(farq {fmt(jami - s, belgi=True)})"
        )
    return [Ulush(i, v, 0) for i, v in summalar.items()]


USUL_TENG = "teng"
USUL_FOIZ = "foiz"
USUL_OGIRLIK = "ogirlik"
USUL_ANIQ = "aniq"

USUL_NOM = {
    USUL_TENG: "Teng bo'linadi",
    USUL_FOIZ: "Foiz bo'yicha",
    USUL_OGIRLIK: "Og'irlik bo'yicha",
    USUL_ANIQ: "Aniq summa",
}


def bol(jami: int, usul: str, parametrlar: dict[int, float],
        qarz_tarixi: dict[int, int] | None = None) -> list[Ulush]:
    """Yagona kirish nuqtasi — UI shuni chaqiradi."""
    if usul == USUL_TENG:
        return bol_teng(jami, list(parametrlar.keys()), qarz_tarixi)
    if usul == USUL_FOIZ:
        return bol_foiz(jami, parametrlar, qarz_tarixi)
    if usul == USUL_OGIRLIK:
        return bol_tortli(jami, parametrlar, qarz_tarixi)
    if usul == USUL_ANIQ:
        return bol_aniq(jami, {i: int(v) for i, v in parametrlar.items()})
    raise ValueError(f"noma'lum bo'lish usuli: {usul!r}")
