"""Desktop ↔ Cloudflare (Worker + D1) sinxroni.

D1 — asosiy baza, desktop esa o'z SQLite'ida ishlashda davom etadi.
Ikkalasi `ozgarishlar` jurnali orqali gaplashadi: `db.apply()` har
yozuvda qatorning to'liq oldin/keyin JSON'ini yozadi — shu yetarli.

  * push — mahalliy, hali yuborilmagan (`sinx=0`) JUFT id'li jurnal
    qatorlari, desktopniki bo'lgan sozlamalar, `davr` va server hali
    ko'rmagan mahsulot rasmlari.
  * pull — serverning TOQ id'li jurnal qatorlari (`dan` dan keyingi).
    Ular `apply()` orqali EMAS, xom yoziladi: aks holda har kelgan
    qator qayta log bo'lib, serverga qaytib ketardi.

Sozlanmagan bo'lsa (`sinx_url`/`sinx_kalit` bo'sh) hamma narsa jim
o'tadi. Tarmoq xatosi hech qachon UI'ga ko'tarilmaydi — `sinxla()`
holat lug'atini qaytaradi.

Faqat stdlib: PySide6 yo'q, shuning uchun `tekshir.py` ekransiz sinaydi.
SQLite ulanishi oqimga bog'langan — fon oqimi O'Z `Db` sini ochadi
(`Sinxronchi`), UI ulanishiga tegmaydi.
"""
from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import config

K_URL = "sinx_url"
K_KALIT = "sinx_kalit"
META_OXIRGI = "sinx_server_oxirgi"

# Bitta so'rovga nechta jurnal qatori va nechta rasm.
PUSH_QATOR = 200
PUSH_RASM = 3

# Desktopga tegishli BO'LMAGAN sozlamalar: bot holati va serverniki.
_SERVER_KALITLAR = {"tg_offset", "dars_tekshirildi",
                    "tg_korilgan_guruhlar", "tg_rasxod_dan"}
_SERVER_OLDI = ("tg_rx:", "sinx_")
# Serverdan pull javobida keladigan (server egalik qiladigan) sozlamalar.
SERVER_SOZLAMA = ("tg_korilgan_guruhlar", "tg_rasxod_dan")

# Server qaysi rasmlarga ega — oxirgi pull javobidan. Kalit — url.
# None (yo'q) = hali bilmaymiz: bu holda rasm yuborilmaydi, avval pull.
_SERVER_RASMLAR: dict[str, set[str]] = {}


class Oflayn(Exception):
    """Serverga ulanib bo'lmadi (internet yo'q, DNS, vaqt tugadi)."""


class ServerXato(Exception):
    """Server javob berdi, lekin rad etdi yoki tushunarsiz javob."""


# ─────────────────────────────────────────────────────────── tarmoq

def _sorov(usul: str, url: str, kalit: str, tana: bytes | None = None,
           vaqt: float = 30) -> bytes:
    """Yagona tarmoq chaqiruvi — testlarda almashtiriladi.

    Ulanib bo'lmasa `Oflayn`, server HTTP xato bersa `ServerXato`.
    """
    # User-Agent shart: Cloudflare standart «Python-urllib» ni bot deb
    # 403 (error 1010) bilan qaytaradi.
    sarlavha = {"Authorization": f"Bearer {kalit}",
                "User-Agent": "FarvonUy-desktop/1.0"}
    if tana is not None:
        sarlavha["Content-Type"] = "application/json"
    so = urllib.request.Request(url, data=tana, headers=sarlavha, method=usul)
    try:
        with urllib.request.urlopen(so, timeout=vaqt) as j:
            return j.read()
    except urllib.error.HTTPError as e:
        raise ServerXato(f"server {e.code} qaytardi") from e
    except (urllib.error.URLError, OSError) as e:
        raise Oflayn(str(e)) from e


def _post(sozl: dict, yol: str, malumot: dict) -> dict:
    tana = json.dumps(malumot, ensure_ascii=False).encode("utf-8")
    xom = _sorov("POST", sozl["url"] + yol, sozl["kalit"], tana)
    try:
        javob = json.loads(xom.decode("utf-8"))
    except ValueError as e:
        raise ServerXato("server JSON qaytarmadi") from e
    if not isinstance(javob, dict) or not javob.get("ok"):
        izoh = javob.get("xato") if isinstance(javob, dict) else None
        raise ServerXato(izoh or "server rad etdi")
    return javob


# ─────────────────────────────────────────────────────────── sozlama

def sozlamalar(db) -> dict | None:
    """`{"url", "kalit"}` yoki sozlanmagan bo'lsa None."""
    url = (db.sozlama(K_URL, "") or "").strip().rstrip("/")
    kalit = (db.sozlama(K_KALIT, "") or "").strip()
    if not url or not kalit:
        return None
    return {"url": url, "kalit": kalit}


def sozlama_qoy(db, url: str, kalit: str) -> None:
    db.sozlama_qoy(K_URL, (url or "").strip())
    db.sozlama_qoy(K_KALIT, (kalit or "").strip())


def desktop_kalitimi(kalit: str) -> bool:
    """Bu sozlamani desktop egalik qiladimi (push qilinadimi)."""
    if kalit in _SERVER_KALITLAR:
        return False
    return not kalit.startswith(_SERVER_OLDI)


def _desktop_sozlamalari(db) -> dict:
    return {r["kalit"]: r["qiymat"]
            for r in db.q("SELECT kalit, qiymat FROM sozlama ORDER BY kalit")
            if desktop_kalitimi(r["kalit"])}


def _meta(db, kalit: str, birlamchi: str = "") -> str:
    r = db.q1("SELECT qiymat FROM meta WHERE kalit=?", kalit)
    return r["qiymat"] if r and r["qiymat"] is not None else birlamchi


def _meta_qoy(db, kalit: str, qiymat) -> None:
    db.con.execute("INSERT OR REPLACE INTO meta(kalit,qiymat) VALUES(?,?)",
                   (kalit, str(qiymat)))


def _ustunlar(db, jadval: str) -> list[str]:
    return [r["name"] for r in db.q(f"PRAGMA table_info({jadval})")]


# ─────────────────────────────────────────────────────────── push

def yuborilmaganlar(db, soni: int = PUSH_QATOR) -> list[dict]:
    """Hali serverga ketmagan mahalliy (JUFT id) jurnal qatorlari."""
    ustun = [c for c in _ustunlar(db, "ozgarishlar") if c != "sinx"]
    return [dict(r) for r in db.q(
        f"SELECT {','.join(ustun)} FROM ozgarishlar"
        " WHERE sinx=0 AND id%2=0 ORDER BY id LIMIT ?", soni)]


def _rasm_nomi_toza(nom) -> bool:
    return (isinstance(nom, str) and nom not in ("", ".", "..")
            and Path(nom).name == nom and "/" not in nom and "\\" not in nom)


def _kerakli_rasmlar(db) -> list[str]:
    """Mahsulotlar ishlatadigan va diskda bor rasm fayllari."""
    nomlar = []
    for r in db.q("SELECT DISTINCT rasm FROM item"
                  " WHERE rasm IS NOT NULL AND rasm<>'' ORDER BY rasm"):
        nom = r["rasm"]
        if _rasm_nomi_toza(nom) and (config.MAHSULOT_RASM / nom).is_file():
            nomlar.append(nom)
    return nomlar


def _push_tanasi(db, qatorlar: list[dict], rasmlar: list[str]) -> dict:
    return {
        "ozgarishlar": qatorlar,
        "sozlama": _desktop_sozlamalari(db),
        "davr": [dict(r) for r in db.q("SELECT * FROM davr ORDER BY oy")],
        "rasmlar": [{"nom": n, "data": base64.b64encode(
            (config.MAHSULOT_RASM / n).read_bytes()).decode("ascii")}
            for n in rasmlar],
    }


def push(db, sozl: dict) -> int:
    """Jurnal qatorlarini yuboradi. Qabul qilingan qatorlar soni."""
    jami = 0
    birinchi = True
    while True:
        qatorlar = yuborilmaganlar(db)
        if not qatorlar and not birinchi:
            break
        birinchi = False
        javob = _post(sozl, "/sinx/push", _push_tanasi(db, qatorlar, []))
        qabul = [int(i) for i in (javob.get("qabul") or [])]
        if qabul:
            db.con.execute("BEGIN")
            try:
                db.con.executemany(
                    "UPDATE ozgarishlar SET sinx=1 WHERE id=?",
                    [(i,) for i in qabul])
                db.con.execute("COMMIT")
            except Exception:
                db.con.execute("ROLLBACK")
                raise
        jami += len(qabul)
        yuborilgan = {q["id"] for q in qatorlar}
        # Server hech birini qabul qilmagan bo'lsa — cheksiz aylanmaymiz.
        if not qatorlar or not (yuborilgan & set(qabul)):
            break
    return jami


def rasmlarni_yubor(db, sozl: dict) -> int:
    """Server hali ko'rmagan mahsulot rasmlari. Server ro'yxati
    noma'lum bo'lsa (pull bo'lmagan) — hech narsa yuborilmaydi."""
    bor = _SERVER_RASMLAR.get(sozl["url"])
    if bor is None:
        return 0
    kerak = [n for n in _kerakli_rasmlar(db) if n not in bor]
    soni = 0
    for i in range(0, len(kerak), PUSH_RASM):
        bolak = kerak[i:i + PUSH_RASM]
        _post(sozl, "/sinx/push", _push_tanasi(db, [], bolak))
        bor.update(bolak)
        soni += len(bolak)
    return soni


# ─────────────────────────────────────────────────────────── pull

def _json(qiymat):
    if qiymat is None or isinstance(qiymat, dict):
        return qiymat
    return json.loads(qiymat)


def qatorlarni_qoy(db, qatorlar: list[dict]) -> int:
    """Serverdan kelgan jurnal qatorlarini BITTA tranzaksiyada qo'yadi.

    `apply()` ishlatilmaydi — qayta log bo'lmasin. Allaqachon bor
    jurnal qatori (shu id) qayta qo'llanmaydi: shuning uchun qayta
    chaqiruv xavfsiz va keyingi mahalliy o'zgarishni eski qiymat
    bosib ketmaydi. Yangi qo'yilgan qatorlar sonini qaytaradi.

    Server — asosiy baza: davr qulfi va tashqi kalitlar tekshirilmaydi
    (bitta qator tufayli butun sinxron to'xtab qolmasin).
    """
    if not qatorlar:
        return 0
    ozg_ustun = set(_ustunlar(db, "ozgarishlar"))
    ustun_kesh: dict[str, list[str]] = {}
    yangi = 0
    db.con.execute("PRAGMA foreign_keys=OFF")
    db.con.execute("BEGIN")
    try:
        for z in sorted(qatorlar, key=lambda x: int(x["id"])):
            zid = int(z["id"])
            if db.q1("SELECT 1 FROM ozgarishlar WHERE id=?", zid):
                continue
            jadval = z.get("jadval")
            if jadval not in ustun_kesh:
                ustun_kesh[jadval] = (_ustunlar(db, jadval)
                                      if isinstance(jadval, str)
                                      and jadval.isidentifier() else [])
            bor_ustun = ustun_kesh[jadval]
            if bor_ustun:
                keyin = _json(z.get("keyin"))
                try:
                    if keyin is not None:
                        c = [k for k in keyin if k in bor_ustun]
                        if "id" not in c:
                            c.insert(0, "id")
                            keyin = {**keyin, "id": z["qator_id"]}
                        yangila = ",".join(f"{k}=excluded.{k}"
                                           for k in c if k != "id")
                        db.con.execute(
                            f"INSERT INTO {jadval}({','.join(c)})"
                            f" VALUES({','.join('?' * len(c))})"
                            f" ON CONFLICT(id) DO "
                            + (f"UPDATE SET {yangila}" if yangila
                               else "NOTHING"),
                            [keyin[k] for k in c])
                    else:
                        db.con.execute(f"DELETE FROM {jadval} WHERE id=?",
                                       (z["qator_id"],))
                except Exception as e:
                    # Bitta buzuq qator (masalan, UNIQUE to'qnashuvi)
                    # butun sinxronni to'xtatmasin — iz qoldiramiz.
                    _iz(f"sinx: {jadval}#{z.get('qator_id')} qo'yilmadi: {e}")
            qiymat = {k: v for k, v in z.items() if k in ozg_ustun}
            for k in ("oldin", "keyin"):
                if isinstance(qiymat.get(k), dict):
                    qiymat[k] = json.dumps(qiymat[k], ensure_ascii=False)
            qiymat["sinx"] = 1
            c = list(qiymat)
            cur = db.con.execute(
                f"INSERT OR IGNORE INTO ozgarishlar({','.join(c)})"
                f" VALUES({','.join('?' * len(c))})",
                [qiymat[k] for k in c])
            yangi += cur.rowcount if cur.rowcount > 0 else 0
        db.con.execute("COMMIT")
    except Exception:
        db.con.execute("ROLLBACK")
        raise
    finally:
        db.con.execute("PRAGMA foreign_keys=ON")
    return yangi


def _kursor(db) -> int:
    """Serverdan qaysi id dan keyingisini olish kerak.

    Kursor hali yo'q bo'lsa — mahalliy eng katta TOQ id: undan oldingi
    toq qatorlar D1 ga eksport bilan tushgan tarix (ular qayta qo'yilsa,
    keyingi juft yozuvlar eski holatga qaytib qoladi), eksportdan keyin
    esa desktop faqat juft id yozadi.
    """
    m = _meta(db, META_OXIRGI, "")
    if m:
        return int(m)
    return int(db.skalyar(
        "SELECT COALESCE(MAX(id),0) FROM ozgarishlar WHERE id%2=1",
        birlamchi=0) or 0)


def pull(db, sozl: dict) -> int:
    """Serverdagi yangi (toq id) qatorlarni oladi. Qo'yilganlar soni."""
    jami = 0
    while True:
        dan = _kursor(db)
        javob = _post(sozl, "/sinx/pull", {"dan": dan})
        jami += qatorlarni_qoy(db, javob.get("ozgarishlar") or [])
        oxirgi = int(javob.get("oxirgi") or dan)
        if oxirgi > dan:
            _meta_qoy(db, META_OXIRGI, oxirgi)
        for k in SERVER_SOZLAMA:
            v = (javob.get("sozlama") or {}).get(k)
            if v is not None:
                db.sozlama_qoy(k, v)
        if isinstance(javob.get("rasmlar"), list):
            _SERVER_RASMLAR[sozl["url"]] = {
                n for n in javob["rasmlar"] if isinstance(n, str)}
        if not javob.get("kop") or oxirgi <= dan:
            break
    return jami


def rasmlarni_ol(sozl: dict) -> int:
    """Serverda bor, lekin diskda yo'q rasmlarni yuklab oladi."""
    soni = 0
    for nom in sorted(_SERVER_RASMLAR.get(sozl["url"]) or ()):
        if not _rasm_nomi_toza(nom):
            continue
        yol = config.MAHSULOT_RASM / nom
        if yol.exists():
            continue
        try:
            baytlar = _sorov(
                "GET", sozl["url"] + "/sinx/rasm?nom="
                + urllib.parse.quote(nom), sozl["kalit"])
        except ServerXato as e:
            _iz(f"sinx: rasm {nom} olinmadi: {e}")
            continue
        if not baytlar:
            continue
        vaqtincha = yol.with_name(yol.name + ".yuk")
        vaqtincha.write_bytes(baytlar)
        vaqtincha.replace(yol)
        soni += 1
    return soni


# ─────────────────────────────────────────────────────────── umumiy

def _iz(matn: str) -> None:
    try:
        import crashlog
        crashlog.yoz(matn)
    except Exception:
        pass


def sinxla(db) -> dict:
    """push → pull → rasmlar. Hech qachon xato ko'tarmaydi.

    Qaytaradi: `{"holat": ok|oflayn|xato|sozlanmagan, "xabar": str,
    "ozgardi": serverdan kelib qo'yilgan qatorlar soni, "vaqt": "HH:MM"}`.
    """
    natija = {"holat": "sozlanmagan", "xabar": "", "ozgardi": 0,
              "vaqt": datetime.now().strftime("%H:%M")}
    try:
        sozl = sozlamalar(db)
        if sozl is None:
            return natija
        push(db, sozl)
        natija["ozgardi"] = pull(db, sozl)
        rasmlarni_yubor(db, sozl)
        rasmlarni_ol(sozl)
        natija["holat"] = "ok"
    except Oflayn as e:
        natija.update(holat="oflayn", xabar=str(e))
    except Exception as e:      # noqa: BLE001 — UI'ga hech narsa ko'tarilmaydi
        natija.update(holat="xato", xabar=str(e) or type(e).__name__)
        _iz(f"sinx xatosi: {e!r}")
    return natija


class Sinxronchi:
    """Fon oqimi: `tetikla()` chaqirilganda (bir oz kutib) sinxronlaydi.

    Bir vaqtda faqat BITTA sinxron: oqim bitta. Ketma-ket tetiklar
    birlashadi (`kechikish` soniya jimlikdan keyin bitta sinxron).
    `natija_fn(dict)` FON OQIMIDAN chaqiriladi — Qt'da signal orqali
    bosh oqimga o'tkazing.
    """

    def __init__(self, yol, natija_fn=None, kechikish: float = 1.0):
        self.yol = Path(yol)
        self.natija_fn = natija_fn
        self.kechikish = kechikish
        self._tetik = threading.Event()
        self._toxta = threading.Event()
        self._oqim = threading.Thread(target=self._ishla, daemon=True,
                                      name="sinxron")
        self._oqim.start()

    def tetikla(self) -> None:
        self._tetik.set()

    def toxtat(self) -> None:
        self._toxta.set()
        self._tetik.set()

    def _ishla(self) -> None:
        import db as dbm
        baza = None
        while not self._toxta.is_set():
            self._tetik.wait()
            if self._toxta.is_set():
                break
            # Debounce: tetiklar to'xtagach bir marta.
            while self._tetik.is_set() and not self._toxta.is_set():
                self._tetik.clear()
                self._toxta.wait(self.kechikish)
            if self._toxta.is_set():
                break
            try:
                if baza is None:
                    baza = dbm.Db(self.yol, zaxirasiz=True)
                natija = sinxla(baza)
            except Exception as e:      # noqa: BLE001
                natija = {"holat": "xato", "xabar": str(e), "ozgardi": 0,
                          "vaqt": datetime.now().strftime("%H:%M")}
            if self.natija_fn is not None:
                try:
                    self.natija_fn(natija)
                except Exception:
                    pass
        if baza is not None:
            try:
                baza.con.close()
            except Exception:
                pass
