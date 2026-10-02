"""Ma'lumot qatlami.

Bu modulning butun mazmuni bitta jumlada: **hamma yozuv `Db.apply()` dan
o'tadi**. Shuning uchun Ctrl+Z hamma joyda ishlaydi, hech narsa rostdan
o'chirilmaydi va har o'zgarish kim/qachon bilan yozib qo'yiladi.

UI hech qachon `INSERT`/`UPDATE` yozmaydi — faqat `apply()` chaqiradi.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import config


class DavrYopilgan(Exception):
    """Yopilgan oyga yozuv kiritishga urinish."""


class Xato(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato."""


# ────────────────────────────────────────────────────────────── zaxira

def zaxira_ol(yol: Path = config.DB_YOL) -> Path | None:
    """Bazani nusxalab qo'yadi. Eng oxirgi ZAXIRA_SONI ta nusxa saqlanadi."""
    if not yol.exists():
        return None
    belgi = datetime.now().strftime("%Y%m%d-%H%M%S")
    nishon = config.ZAXIRA / f"farvonuy-{belgi}.db"
    try:
        manba = sqlite3.connect(str(yol))
        nusxa = sqlite3.connect(str(nishon))
        with nusxa:
            manba.backup(nusxa)      # onlayn backup — ochiq baza ham xavfsiz
        nusxa.close()
        manba.close()
    except Exception:
        try:
            shutil.copy2(yol, nishon)
        except Exception:
            return None
    eskilar = sorted(config.ZAXIRA.glob("farvonuy-*.db"))
    for e in eskilar[: max(0, len(eskilar) - config.ZAXIRA_SONI)]:
        try:
            e.unlink()
        except OSError:
            pass
    return nishon


# ────────────────────────────────────────────────────────────────── Db

class Db:
    """SQLite ustidagi yagona yozuv nuqtasi."""

    def __init__(self, yol: Path | str = config.DB_YOL, zaxirasiz: bool = False):
        self.yol = Path(yol)
        yangi = not self.yol.exists() or self.yol.stat().st_size == 0
        if not yangi and not zaxirasiz:
            zaxira_ol(self.yol)

        self.con = sqlite3.connect(str(self.yol), isolation_level=None)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA foreign_keys=ON")
        self.con.execute("PRAGMA synchronous=FULL")
        # Baza band bo'lsa darhol yiqilmasin, 5 soniya kutsin. Dastur
        # to'satdan yopilgan bo'lsa WAL tiklanishi bir necha yuz millisekund
        # oladi — o'sha paytda ochilsa, kutmasa jimgina o'lib qolardi.
        self.con.execute("PRAGMA busy_timeout=5000")
        # COMMIT dan keyin chaqiriladigan funksiyalar (sinxron shu bilan
        # uyg'otiladi). Xatosi yozuvni buzmaydi — `_commitdan_keyin()`.
        self.commitdan_keyin: list = []
        self._migratsiya()
        if yangi:
            self._boshlangich()

    # ── sxema ────────────────────────────────────────────────────────

    # Keyin qo'shilgan ustunlar. `CREATE TABLE IF NOT EXISTS` mavjud
    # jadvalga ustun qo'shmaydi, shuning uchun ularni qo'lda tekshiramiz.
    YANGI_USTUNLAR = [
        ("rasxod", "kim_uchun", "INTEGER REFERENCES odam(id)"),
        ("ulush", "tolandi", "INTEGER NOT NULL DEFAULT 0"),
        ("ulush", "tolangan_sana", "TEXT"),
        ("hisob_kitob", "ulush_id", "INTEGER REFERENCES ulush(id)"),
        ("ozgarishlar", "bekor", "INTEGER NOT NULL DEFAULT 0"),
        ("vazifa_turi", "navbat", "INTEGER NOT NULL DEFAULT 0"),
        ("vazifa_turi", "haftalik", "INTEGER NOT NULL DEFAULT 0"),
        ("vazifa_turi", "shaxsiy", "INTEGER NOT NULL DEFAULT 0"),
        ("vazifa_turi", "ergash_turi_id", "INTEGER REFERENCES vazifa_turi(id)"),
        ("odam", "telegram", "TEXT"),
        ("odam", "tg_chat", "INTEGER"),
        ("vazifa", "menyu", "TEXT"),
        ("vazifa", "kechiktirildi", "TEXT"),
        ("vazifa", "manba", "TEXT"),
        ("yuborilgan", "xabar_id", "INTEGER"),
        ("turi", "rasm", "TEXT"),
        ("turi", "ota_id", "INTEGER REFERENCES turi(id)"),
        ("item", "rasm", "TEXT"),
        ("item", "miqdor", "REAL"),
        ("item", "ogirlik", "REAL"),
        ("item", "litr", "REAL"),
        ("item", "olchov", "TEXT"),
        ("item", "ochirilgan", "INTEGER NOT NULL DEFAULT 0"),
        ("tashqi_qarz", "umumiy", "INTEGER NOT NULL DEFAULT 0"),
        # Oylik reja yozuvi — rasxod kabi sanasi bilan (2026-10-01).
        ("reja_qator", "sana", "TEXT"),
        # Umumiy yoki kimningdir shaxsiy rejasi (2026-10-01).
        ("reja_qator", "umumiymi", "INTEGER NOT NULL DEFAULT 1"),
        ("reja_qator", "odam_id", "INTEGER REFERENCES odam(id)"),
        # «Aslida to'landi»: rejadan yozilgan haqiqiy rasxod va summalar.
        ("reja_qator", "rasxod_id", "INTEGER REFERENCES rasxod(id)"),
        ("reja_qator", "tolangan", "INTEGER"),
        ("reja_mahsulot", "tolangan", "INTEGER"),
        # Pul qayerdan chiqdi / qayerga tushdi: NULL — naqd (2026-10-01).
        ("rasxod", "karta_id", "INTEGER REFERENCES karta(id)"),
        ("kirim", "karta_id", "INTEGER REFERENCES karta(id)"),
        # Serverga (Cloudflare D1) yuborildimi: 1 — yuborilgan (`sinx.py`).
        ("ozgarishlar", "sinx", "INTEGER NOT NULL DEFAULT 0"),
    ]

    def _migratsiya(self) -> None:
        matn = config.resurs("schema.sql")
        if not matn.exists():
            matn = Path(__file__).resolve().parent / "schema.sql"
        self.con.executescript(matn.read_text(encoding="utf-8"))

        for jadval, ustun, tur in self.YANGI_USTUNLAR:
            if not self._ustun_bormi(jadval, ustun):
                self.con.execute(f"ALTER TABLE {jadval} ADD COLUMN {ustun} {tur}")
                if (jadval, ustun) == ("ozgarishlar", "sinx"):
                    # Ustungacha bo'lgan butun tarix D1 ga boshlang'ich
                    # eksport bilan (`tools/d1_eksport.py`) tushadi — uni
                    # qayta yuborish serverdagi yangi holatni eski
                    # qiymat bilan bosib ketardi.
                    self.con.execute("UPDATE ozgarishlar SET sinx=1")
                    # Pull ham shu nuqtadan boshlansin: eksportdagi eski
                    # toq id'li qatorlar qayta qo'yilsa, keyingi juft
                    # yozuvlar eski holatga qaytib qolardi.
                    self.con.execute(
                        "INSERT OR REPLACE INTO meta(kalit,qiymat) VALUES("
                        "'sinx_server_oxirgi',"
                        " (SELECT COALESCE(MAX(id),0) FROM ozgarishlar"
                        "  WHERE id%2=1))")

        self._vazifa_turlarini_ek()
        self._navbatni_ek()
        self._uborkani_ek()
        self._menyuni_ek()

        self.con.execute(
            "INSERT OR REPLACE INTO meta(kalit,qiymat) VALUES('sxema_versiya','21')")

    # Excel «Vazifalar» varag'idagi tayyor uy ishlari (C17:C21).
    VAZIFA_TURLARI = [
        "Ovqat qilish",
        "Ovqat qilib turgan vaqtda chiqqan idishlarni yuvish",
        "Dasturxon yozish, narsalarni qo'yish",
        "Gaz plitasini ovqatdan keyin yog'laridan artib tozalash",
        "Musorlarni tashlash",
    ]

    def _vazifa_turlarini_ek(self) -> None:
        """Tayyor vazifa turlarini BIR MARTA ekadi.

        `_boshlangich()` da emas: u faqat yangi bazaga ishlaydi, bu
        jadval esa mavjud bazalarga keyin qo'shildi. Bayroq `meta` da —
        aks holda foydalanuvchi o'chirgan tur har ochilganda tirilardi.
        """
        if self.q1("SELECT 1 FROM meta WHERE kalit='vazifa_turi_ekildi'"):
            return
        for i, nom in enumerate(self.VAZIFA_TURLARI):
            self.con.execute(
                "INSERT OR IGNORE INTO vazifa_turi(nom,tartib) VALUES(?,?)",
                (nom, i))
        self.con.execute(
            "INSERT OR REPLACE INTO meta(kalit,qiymat)"
            " VALUES('vazifa_turi_ekildi','1')")

    def _navbatni_ek(self) -> None:
        """Ovqat qilish → navbatli, ergashi → idish yuvish.

        Alohida bayroq: turlar allaqachon ekilgan bazalarga ham shu
        bog'lanish tushishi kerak. Foydalanuvchi keyin o'zgartirsa,
        qayta yozilmaydi.
        """
        if self.q1("SELECT 1 FROM meta WHERE kalit='vazifa_navbat_ekildi'"):
            return
        ovqat = self.q1("SELECT id FROM vazifa_turi WHERE nom=?",
                        self.VAZIFA_TURLARI[0])
        idish = self.q1("SELECT id FROM vazifa_turi WHERE nom=?",
                        self.VAZIFA_TURLARI[1])
        if ovqat and idish:
            self.con.execute(
                "UPDATE vazifa_turi SET navbat=1, ergash_turi_id=?"
                " WHERE id=?", (idish["id"], ovqat["id"]))
        self.con.execute(
            "INSERT OR REPLACE INTO meta(kalit,qiymat)"
            " VALUES('vazifa_navbat_ekildi','1')")

    # ── general uborka ───────────────────────────────────────────────
    #
    # Haftada bir marta (birlamchi — yakshanba) qilinadigan uchta katta
    # ish. Har biri bitta odamga tushadi va HAR HAFTA keyingisiga
    # o'tadi — `core/vazifa.uborka_rejasi()` shuni hisoblaydi.
    #
    # Qadamlar shu yerda, chunki «Sanuzelni tozalash» degan nomning
    # o'zi nima qilish kerakligini aytmaydi: guruhga ketadigan xabarda
    # ro'yxat turgani ma'qul. Foydalanuvchi keyin xohlaganini qo'shadi
    # yoki olib tashlaydi — bular faqat BOSHLANG'ICH qiymat.
    UBORKA = [
        ("Oshxonani tozalash", [
            "Gaz plitasini yog'idan tozalash",
            "Rakovina va kranni tozalash",
            "Stol va javon ustini artish",
            "Muzlatkichni ichidan ko'rib chiqish",
            "Polni yuvish",
        ]),
        ("Sanuzelni tozalash", [
            "Unitazni tozalash",
            "Vanna va dushni yuvish",
            "Rakovina va oynani artish",
            "Polni yuvish",
            "Sochiqlarni almashtirish",
        ]),
        ("Umumiy uyni tozalash", [
            "Changlarni artish",
            "Pollarni artish",
            "Pilesos qilish",
        ]),
    ]

    # Uborka kuni: 0 = dushanba … 6 = yakshanba.
    UBORKA_KUNI = 6

    def _uborkani_ek(self) -> None:
        """General uborka ishlarini va ularning qadamlarini BIR MARTA ekadi.

        Uchtasining nomi mavjud bazalarda allaqachon bo'lishi mumkin
        (foydalanuvchi o'zi qo'shgan) — shuning uchun avval nomi
        bo'yicha qidiriladi va faqat `haftalik=1` qo'yiladi. Yangi tur
        yaratish o'sha ishni ikki marta ko'rsatib qo'yardi.

        Bayroq `meta` da: `vazifa_turi` va `menyu` bilan bir xil sabab —
        foydalanuvchi o'chirgan ish har ochilganda tirilmasin.
        """
        if self.q1("SELECT 1 FROM meta WHERE kalit='uborka_ekildi'"):
            return
        tartib = self.skalyar(
            "SELECT COALESCE(MAX(tartib),0)+1 FROM vazifa_turi")
        for i, (nom, qadamlar) in enumerate(self.UBORKA):
            self.con.execute(
                "INSERT OR IGNORE INTO vazifa_turi(nom,tartib) VALUES(?,?)",
                (nom, tartib + i))
            self.con.execute(
                "UPDATE vazifa_turi SET haftalik=1, ochirilgan=0 WHERE nom=?",
                (nom,))
            r = self.q1("SELECT id FROM vazifa_turi WHERE nom=?", nom)
            if not r:
                continue
            for j, qadam in enumerate(qadamlar):
                self.con.execute(
                    "INSERT INTO ish_qadam(turi_id,nom,tartib) VALUES(?,?,?)",
                    (r["id"], qadam, j))
        self.con.execute(
            "INSERT INTO sozlama(kalit,qiymat) VALUES('uborka_kuni',?)"
            " ON CONFLICT(kalit) DO NOTHING", (str(self.UBORKA_KUNI),))
        self.con.execute(
            "INSERT OR REPLACE INTO meta(kalit,qiymat)"
            " VALUES('uborka_ekildi','1')")

    # Guruhda oshpaz tanlaydigan taomlar. Ro'yxat jadvalda yashaydi —
    # bular shunchaki BOSHLANG'ICH qiymat.
    MENYU = [
        "Spagetti",
        "Makaron",
        "Mastava",
        "Garox sho'rva",
        "Chuchvara",
    ]

    def _menyuni_ek(self) -> None:
        """Boshlang'ich menyuni BIR MARTA ekadi.

        `vazifa_turi` bilan bir xil sabab: bayroq bo'lmasa
        foydalanuvchi o'chirgan taom har ochilganda tirilardi.
        """
        if self.q1("SELECT 1 FROM meta WHERE kalit='menyu_ekildi'"):
            return
        for i, nom in enumerate(self.MENYU):
            self.con.execute(
                "INSERT OR IGNORE INTO menyu(nom,tartib) VALUES(?,?)",
                (nom, i))
        self.con.execute(
            "INSERT OR REPLACE INTO meta(kalit,qiymat)"
            " VALUES('menyu_ekildi','1')")

    def _boshlangich(self) -> None:
        """Bo'sh bazaga standart kategoriyalar."""
        turlar = [
            ("Ovqat", "🍲"), ("Bozorlik", "🛒"), ("Ro'zg'or", "🏠"),
            ("Gigiena", "🧼"), ("Transport", "🚕"), ("Kommunal", "💡"),
            ("Kiyim", "👕"), ("Sog'liq", "💊"), ("Boshqa", "📦"),
        ]
        for i, (nom, belgi) in enumerate(turlar):
            self.con.execute(
                "INSERT OR IGNORE INTO turi(nom,belgi,tartib) VALUES(?,?,?)",
                (nom, belgi, i))

    # ── o'qish ───────────────────────────────────────────────────────

    def q(self, sql: str, *args) -> list[sqlite3.Row]:
        return self.con.execute(sql, args).fetchall()

    def q1(self, sql: str, *args) -> sqlite3.Row | None:
        return self.con.execute(sql, args).fetchone()

    def skalyar(self, sql: str, *args, birlamchi=0):
        r = self.con.execute(sql, args).fetchone()
        if r is None or r[0] is None:
            return birlamchi
        return r[0]

    # ── davr qulfi ───────────────────────────────────────────────────

    def davr_yopiqmi(self, sana: str) -> bool:
        oy = str(sana)[:7]
        r = self.q1("SELECT holat FROM davr WHERE oy=?", oy)
        return bool(r and r["holat"] == "yopilgan")

    def juft_id(self, jadval: str) -> int:
        """Keyingi JUFT id: `MAX(id)` dan katta eng kichik juft son.

        Desktop faqat juft, Cloudflare Worker faqat toq id beradi —
        ikkalasi oflayn yozadi va sinxronda birlamchi kalit
        to'qnashmaydi. Bitta tranzaksiyada ketma-ket INSERT ham to'g'ri:
        SQLite yozuvni darhol qo'yadi, keyingi `MAX(id)` uni ko'radi.
        """
        m = self.skalyar(f"SELECT MAX(id) FROM {jadval}", birlamchi=0)
        n = int(m) + 1
        return n + 1 if n % 2 else n

    def _commitdan_keyin(self) -> None:
        for f in list(self.commitdan_keyin):
            try:
                f()
            except Exception:
                pass

    def _qulfni_tekshir(self, jadval: str, data: dict, eski: dict | None) -> None:
        if jadval not in ("kirim", "rasxod", "qarz", "hisob_kitob",
                          "tashqi_qarz", "tashqi_tolov", "tashqi_ulush",
                          "karta_otkazma"):
            return
        for manba in (data, eski or {}):
            s = manba.get("sana")
            if s and self.davr_yopiqmi(s):
                raise DavrYopilgan(
                    f"{str(s)[:7]} oyi yopilgan — yozuvni o'zgartirib bo'lmaydi.\n"
                    f"Avval Sozlamalar → Davrlar bo'limida oyni oching.")

    # ── yozish ───────────────────────────────────────────────────────

    @contextmanager
    def amal(self, tavsif: str = ""):
        """Bir nechta yozuvni BITTA undo qadamiga bog'laydi.

            with db.amal("Rasxod qo'shildi"):
                rid = db.apply("rasxod", "INSERT", {...})
                for u in ulushlar:
                    db.apply("ulush", "INSERT", {...})
        """
        # Ichma-ich chaqirilishi mumkin: `entries.*` funksiyalarining o'zi
        # `amal()` ishlatadi, ularni bitta katta amalga o'rash tabiiy.
        # SQLite ichma-ich BEGIN ni ko'tarmaydi, shuning uchun ichkaridagi
        # chaqiruv tashqi guruhga QO'SHILADI — hammasi bitta undo qadami.
        ichkarida = getattr(self, "_guruh", None) is not None
        if ichkarida:
            yield self._guruh
            return

        guruh = uuid.uuid4().hex
        self._guruh = guruh
        self._tavsif = tavsif
        self.con.execute("BEGIN")
        try:
            self._redo_yolini_yop()
            yield guruh
        except Exception:
            self.con.execute("ROLLBACK")
            raise
        else:
            self.con.execute("COMMIT")
            self._guruh = None
            self._commitdan_keyin()
        finally:
            self._guruh = None

    def apply(self, jadval: str, amal: str, data: dict | None = None,
              qator_id: int | None = None, tavsif: str = "") -> int:
        """Yagona yozuv nuqtasi. `ozgarishlar` ga log yozadi.

        amal:  INSERT | UPDATE | DELETE
        DELETE haqiqiy o'chirish emas — `ochirilgan=1` qo'yadi (agar ustun bo'lsa).
        """
        data = dict(data or {})
        guruh = getattr(self, "_guruh", None)
        mustaqil = guruh is None
        if mustaqil:
            guruh = uuid.uuid4().hex
            self.con.execute("BEGIN")
        tavsif = tavsif or getattr(self, "_tavsif", "") or f"{amal} {jadval}"

        try:
            if mustaqil:
                self._redo_yolini_yop()
            eski = None
            if qator_id is not None:
                r = self.q1(f"SELECT * FROM {jadval} WHERE id=?", qator_id)
                eski = dict(r) if r else None

            self._qulfni_tekshir(jadval, data, eski)

            if amal == "INSERT":
                if data.get("id") is None:
                    data["id"] = self.juft_id(jadval)
                ustunlar = list(data)
                sql = (f"INSERT INTO {jadval}({','.join(ustunlar)}) "
                       f"VALUES({','.join('?' * len(ustunlar))})")
                cur = self.con.execute(sql, [data[c] for c in ustunlar])
                qator_id = cur.lastrowid
                keyin = dict(self.q1(f"SELECT * FROM {jadval} WHERE id=?", qator_id))

            elif amal == "UPDATE":
                if qator_id is None:
                    raise Xato("UPDATE uchun qator_id kerak")
                if not data:
                    keyin = eski
                else:
                    setlar = ",".join(f"{c}=?" for c in data)
                    self.con.execute(f"UPDATE {jadval} SET {setlar} WHERE id=?",
                                     [*data.values(), qator_id])
                    keyin = dict(self.q1(f"SELECT * FROM {jadval} WHERE id=?", qator_id))

            elif amal == "DELETE":
                if qator_id is None:
                    raise Xato("DELETE uchun qator_id kerak")
                if self._ustun_bormi(jadval, "ochirilgan"):
                    self.con.execute(f"UPDATE {jadval} SET ochirilgan=1 WHERE id=?",
                                     (qator_id,))
                    keyin = dict(self.q1(f"SELECT * FROM {jadval} WHERE id=?", qator_id))
                else:
                    self.con.execute(f"DELETE FROM {jadval} WHERE id=?", (qator_id,))
                    keyin = None
            else:
                raise Xato(f"noma'lum amal: {amal}")

            self.con.execute(
                "INSERT INTO ozgarishlar(id,guruh_id,tavsif,jadval,qator_id,amal,"
                "oldin,keyin) VALUES(?,?,?,?,?,?,?,?)",
                (self.juft_id("ozgarishlar"), guruh, tavsif, jadval, qator_id, amal,
                 json.dumps(eski, ensure_ascii=False) if eski else None,
                 json.dumps(keyin, ensure_ascii=False) if keyin else None))
        except Exception:
            if mustaqil:
                self.con.execute("ROLLBACK")
            raise
        else:
            if mustaqil:
                self.con.execute("COMMIT")
                self._commitdan_keyin()
        return qator_id

    def _ustun_bormi(self, jadval: str, ustun: str) -> bool:
        return any(r["name"] == ustun
                   for r in self.q(f"PRAGMA table_info({jadval})"))

    # ── undo / redo ──────────────────────────────────────────────────

    def oxirgi_guruh(self) -> tuple[str, str] | None:
        """Keyingi Ctrl+Z nimani qaytaradi — eng oxirgi amaldagi guruh."""
        r = self.q1(
            "SELECT guruh_id, tavsif FROM ozgarishlar WHERE qaytarilgan=0"
            " ORDER BY id DESC LIMIT 1")
        return (r["guruh_id"], r["tavsif"]) if r else None

    def keyingi_guruh(self) -> tuple[str, str] | None:
        """Keyingi Ctrl+Y nimani qayta bajaradi — eng ESKI qaytarilgan guruh.

        DIQQAT — bu yerda `ASC`, `DESC` emas. Undo orqaga qarab yuradi,
        demak redo uni teskari yo'nalishda YECHISHI kerak: oxirgi undo
        qaysi guruhni olib tashlagan bo'lsa, birinchi redo o'shani
        qaytaradi. `DESC` bo'lsa redo stekning narigi uchiga sakraydi va
        log aralashib ketadi: bir qism guruh qaytarilgan holda qolib,
        undan keyingilari amalda bo'lib turadi.

        Aynan shu xato 2026-09-02 da ma'lumotni buzgan — 45 ta yozuv
        qaytarilgan holda qolib, eng yangi 4 tasi qayta qo'llangan.
        """
        r = self.q1(
            "SELECT guruh_id, tavsif FROM ozgarishlar"
            " WHERE qaytarilgan=1 AND bekor=0"
            " ORDER BY id ASC LIMIT 1")
        return (r["guruh_id"], r["tavsif"]) if r else None

    def _redo_yolini_yop(self) -> None:
        """Undo'dan keyin YANGI yozuv kiritildi — redo yo'li yopiladi.

        Klassik undo/redo qoidasi: tarix shoxlanmaydi. Qaytarilgan
        guruhlar endi qayta bajarilmaydi, aks holda yangi yozuvdan keyin
        Ctrl+Y eski guruhni tiklab, `ozgarishlar` tartibini buzadi.

        Ular O'CHIRILMAYDI (3-qoida: hech narsa o'chirilmaydi) — faqat
        `bekor=1` bo'ladi va «O'zgarishlar tarixi» da ko'rinib turadi.
        Chaqiruv har doim ochiq tranzaksiya ichida bo'ladi.
        """
        self.con.execute(
            "UPDATE ozgarishlar SET bekor=1 WHERE qaytarilgan=1 AND bekor=0")

    def undo(self) -> str | None:
        g = self.oxirgi_guruh()
        if not g:
            return None
        guruh, tavsif = g
        qatorlar = self.q(
            "SELECT * FROM ozgarishlar WHERE guruh_id=? AND qaytarilgan=0"
            " ORDER BY id DESC", guruh)
        self.con.execute("BEGIN")
        try:
            for z in qatorlar:
                self._teskari(z, qaytar=True)
            self.con.execute(
                "UPDATE ozgarishlar SET qaytarilgan=1 WHERE guruh_id=?", (guruh,))
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise
        return tavsif

    def redo(self) -> str | None:
        g = self.keyingi_guruh()
        if not g:
            return None
        guruh, tavsif = g
        qatorlar = self.q(
            "SELECT * FROM ozgarishlar WHERE guruh_id=? AND qaytarilgan=1"
            " ORDER BY id ASC", guruh)
        self.con.execute("BEGIN")
        try:
            for z in qatorlar:
                self._teskari(z, qaytar=False)
            self.con.execute(
                "UPDATE ozgarishlar SET qaytarilgan=0 WHERE guruh_id=?", (guruh,))
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise
        return tavsif

    def _teskari(self, z: sqlite3.Row, qaytar: bool) -> None:
        """qaytar=True → undo (keyin'dan oldin'ga). False → redo."""
        jadval, qid, amal = z["jadval"], z["qator_id"], z["amal"]
        oldin = json.loads(z["oldin"]) if z["oldin"] else None
        keyin = json.loads(z["keyin"]) if z["keyin"] else None
        nishon = oldin if qaytar else keyin

        if nishon is None:
            self.con.execute(f"DELETE FROM {jadval} WHERE id=?", (qid,))
            return
        bor = self.q1(f"SELECT 1 FROM {jadval} WHERE id=?", qid)
        if bor:
            ustunlar = [c for c in nishon if c != "id"]
            self.con.execute(
                f"UPDATE {jadval} SET {','.join(f'{c}=?' for c in ustunlar)} WHERE id=?",
                [*[nishon[c] for c in ustunlar], qid])
        else:
            ustunlar = list(nishon)
            self.con.execute(
                f"INSERT INTO {jadval}({','.join(ustunlar)}) "
                f"VALUES({','.join('?' * len(ustunlar))})",
                [nishon[c] for c in ustunlar])

    # ── sozlamalar ───────────────────────────────────────────────────

    def sozlama(self, kalit: str, birlamchi: str = "") -> str:
        r = self.q1("SELECT qiymat FROM sozlama WHERE kalit=?", kalit)
        return r["qiymat"] if r else birlamchi

    def sozlama_qoy(self, kalit: str, qiymat: str) -> None:
        self.con.execute(
            "INSERT INTO sozlama(kalit,qiymat) VALUES(?,?)"
            " ON CONFLICT(kalit) DO UPDATE SET qiymat=excluded.qiymat",
            (kalit, str(qiymat)))

    def yop(self) -> None:
        try:
            self.con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        self.con.close()


def bugun() -> str:
    return date.today().isoformat()
