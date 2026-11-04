"""SQLite veri katmani: sema, kayit islemleri, ayarlar, geri donusum kutusu."""
from __future__ import annotations

import datetime
import json
import os
import shutil
import sqlite3
import sys

UYGULAMA_ADI = "Notlarım & Termin Takibi"
SURUM = "1.4"
# Kullanici verisinin tutuldugu klasor adi (kullanici profilinde).
VERI_KLASOR_ADI = "NotlarimVeTerminTakibi"


def uygulama_dizini() -> str:
    """Uygulamanin (exe veya .py) bulundugu klasor."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def veri_dizini() -> str:
    """Kalici kullanici verisi klasoru: konumdan ve guncellemelerden bagimsiz.

    Veriler kullanici profilinde (%APPDATA%) tutulur. Boylece exe hangi klasore
    konursa konsun ayni veritabani kullanilir ve yeni surumler kurulurken
    mevcut kayitlar silinmez; uygulama kendini yeni bir uygulama gibi kurmaz.
    """
    temel = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(temel, VERI_KLASOR_ADI)


BASE_DIR = uygulama_dizini()
VERI_DIR = veri_dizini()
DB_YOLU = os.path.join(VERI_DIR, "notlar.db")
VARSAYILAN_YEDEK_KLASORU = os.path.join(VERI_DIR, "yedekler")
# Eski surumlerde veri exe'nin yaninda tutuluyordu; ilk calistirmada tasinir.
ESKI_DB_YOLU = os.path.join(BASE_DIR, "notlar.db")
ESKI_YEDEK_KLASORU = os.path.join(BASE_DIR, "yedekler")
IKON_YOLU = os.path.join(BASE_DIR, "ikon.ico")

ALANLAR = (
    "baslik",
    "aciklama",
    "kategori",
    "oncelik",
    "etiketler",
    "tarih_saat",
    "tekrar_tipi",
    "ay_baslangic_gun",
    "ay_bitis_gun",
    "ay_gun_listesi",
    "ay_kural",
    "hatirlatma_once_dk",
    "durum",
    "tamamlanma_zamani",
    "tamamlanan_donem",
    "son_uyari_zamani",
    "son_uyari_ocak",
    "ertelenen_zaman",
    "silindi",
    "silinme_zamani",
    "tur",
    "sorumlu",
    "ilerleme",
    "kurum_amir",
    "evrak_durum",
    "dosya_eki",
    "amire_bilgi_verildi",
    "amire_bilgi_zamani",
)

VARSAYILAN_AYARLAR = {
    "tema": "dark",
    "bildirim_sesi": "Varsayılan",
    "varsayilan_hatirlatma": "Zamanında",
    "varsayilan_oncelik": "Normal",
    "varsayilan_kategori": "Genel",
    "kontrol_araligi_sn": "20",
    "otomatik_baslat": "0",
    "tepsiye_kucult": "1",
    "gunluk_yedek": "1",
    "yedek_klasoru": VARSAYILAN_YEDEK_KLASORU,
    "yedek_saklama_gun": "30",
    "termin_esik_gun": "3",
    "guncelleme_otomatik": "1",
    "guncelleme_kontrol_saat": "6",
    "guncelleme_repo": "Hidayets/Not-ve-Termin-Takibi",
}

_ayar_onbellek: dict[str, str] | None = None

# Aylik gorev sablonlarinda kullanilan kural tipleri (monthly_task_rules.rule_type).
# rule_params bu tiplere gore JSON olarak saklanir.
AYLIK_KURAL_TIPLERI = {
    "first_calendar_days": "Ayın ilk N takvim günü",   # {"days": 7}
    "last_calendar_days": "Ayın son N takvim günü",    # {"days": 3}
    "day_range": "Ayın X-Y günleri",                   # {"start_day": 1, "end_day": 5}
    "nth_workday": "Ayın X'inci iş günü",              # {"n": 3}
    "last_workday": "Ayın son iş günü",                # {}
    "last_n_workdays": "Ayın son N iş günü",           # {"n": 2}
}


def simdi() -> datetime.datetime:
    return datetime.datetime.now()


def zaman_damgasi() -> str:
    return simdi().strftime("%Y-%m-%d %H:%M:%S")


def baglan() -> sqlite3.Connection:
    baglanti = sqlite3.connect(DB_YOLU, timeout=15)
    baglanti.row_factory = sqlite3.Row
    return baglanti


def _kolon_ekle(baglanti: sqlite3.Connection, tablo: str, kolon: str, tanim: str) -> None:
    """Eksik kolonu ekler; mevcut tablo ve veriler korunur (geriye donuk uyumlu)."""
    mevcut = {satir["name"] for satir in baglanti.execute(f"PRAGMA table_info({tablo})")}
    if kolon not in mevcut:
        baglanti.execute(f"ALTER TABLE {tablo} ADD COLUMN {kolon} {tanim}")


def _eski_veriyi_tasi() -> None:
    """Onceki surumlerdeki veriyi (exe yani) kullanici profiline tasir.

    Hedef konumda veritabani yoksa ve eski konumda varsa, mevcut kayitlar
    kaybolmasin diye eski veritabani ve yedek klasoru kopyalanir. Boylece
    guncelleme, veriyi sifirlamadan mevcut uygulamanin uzerine yazmis olur.
    """
    if os.path.abspath(ESKI_DB_YOLU) == os.path.abspath(DB_YOLU):
        return
    if os.path.exists(DB_YOLU) or not os.path.exists(ESKI_DB_YOLU):
        return
    os.makedirs(VERI_DIR, exist_ok=True)
    try:
        shutil.copy2(ESKI_DB_YOLU, DB_YOLU)
        if os.path.isdir(ESKI_YEDEK_KLASORU) and not os.path.isdir(
            VARSAYILAN_YEDEK_KLASORU
        ):
            shutil.copytree(ESKI_YEDEK_KLASORU, VARSAYILAN_YEDEK_KLASORU)
    except OSError as hata:
        print("[veri tasima hatasi]", hata)


def _yedek_ayarini_guncelle() -> None:
    """yedek_klasoru ayari eski (exe yani) konumu gosteriyorsa yeni konuma ceker."""
    global _ayar_onbellek
    if os.path.abspath(ESKI_YEDEK_KLASORU) == os.path.abspath(VARSAYILAN_YEDEK_KLASORU):
        return
    with baglan() as baglanti:
        baglanti.execute(
            "UPDATE ayarlar SET deger = ? WHERE anahtar = 'yedek_klasoru' AND deger = ?",
            (VARSAYILAN_YEDEK_KLASORU, ESKI_YEDEK_KLASORU),
        )
    _ayar_onbellek = None


def veritabani_olustur() -> None:
    os.makedirs(VERI_DIR, exist_ok=True)
    _eski_veriyi_tasi()
    with baglan() as baglanti:
        baglanti.executescript(
            """
            CREATE TABLE IF NOT EXISTS notlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                baslik TEXT NOT NULL,
                aciklama TEXT DEFAULT '',
                kategori TEXT DEFAULT 'Genel',
                oncelik TEXT DEFAULT 'Normal',
                etiketler TEXT DEFAULT '',
                tarih_saat TEXT NOT NULL,
                tekrar_tipi TEXT DEFAULT 'tek',
                ay_baslangic_gun INTEGER,
                ay_bitis_gun INTEGER,
                ay_gun_listesi TEXT,
                ay_kural TEXT,
                ay_tamamlanan_gunler TEXT,
                hatirlatma_once_dk INTEGER DEFAULT 0,
                durum TEXT DEFAULT 'bekliyor',
                tamamlanma_zamani TEXT,
                tamamlanan_donem TEXT,
                son_uyari_zamani TEXT,
                son_uyari_ocak TEXT,
                ertelenen_zaman TEXT,
                silindi INTEGER DEFAULT 0,
                silinme_zamani TEXT,
                olusturma_zamani TEXT,
                guncelleme_zamani TEXT
            );

            CREATE TABLE IF NOT EXISTS uyari_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                not_id INTEGER,
                baslik TEXT,
                uyari_zamani TEXT,
                islem TEXT,
                aciklama TEXT
            );

            CREATE TABLE IF NOT EXISTS ayarlar (
                anahtar TEXT PRIMARY KEY,
                deger TEXT
            );

            CREATE TABLE IF NOT EXISTS aylik_gecmis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                not_id INTEGER NOT NULL,
                donem TEXT NOT NULL,
                baslik TEXT,
                planlanan_gunler TEXT,
                durum TEXT DEFAULT 'bekliyor',
                tamamlanma_zamani TEXT,
                olusturma_zamani TEXT,
                UNIQUE(not_id, donem)
            );

            CREATE TABLE IF NOT EXISTS monthly_task_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                rule_type TEXT NOT NULL,
                rule_params TEXT NOT NULL,
                reminder_time TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_notlar_tarih ON notlar(tarih_saat);
            CREATE INDEX IF NOT EXISTS idx_notlar_silindi ON notlar(silindi);
            CREATE INDEX IF NOT EXISTS idx_aylik_gecmis_donem ON aylik_gecmis(donem);
            """
        )
        # Geriye donuk uyumlu migrasyon: eksik kolonlar eklenir, mevcut veri korunur.
        _kolon_ekle(baglanti, "notlar", "ay_gun_listesi", "TEXT")
        _kolon_ekle(baglanti, "notlar", "ay_kural", "TEXT")
        _kolon_ekle(baglanti, "notlar", "ay_tamamlanan_gunler", "TEXT")
        _kolon_ekle(baglanti, "notlar", "tur", "TEXT DEFAULT 'not'")
        _kolon_ekle(baglanti, "notlar", "sorumlu", "TEXT DEFAULT ''")
        _kolon_ekle(baglanti, "notlar", "ilerleme", "INTEGER DEFAULT 0")
        _kolon_ekle(baglanti, "notlar", "kurum_amir", "TEXT DEFAULT ''")
        _kolon_ekle(baglanti, "notlar", "evrak_durum", "TEXT DEFAULT 'Bekliyor'")
        _kolon_ekle(baglanti, "notlar", "dosya_eki", "TEXT DEFAULT ''")
        _kolon_ekle(baglanti, "notlar", "amire_bilgi_verildi", "INTEGER DEFAULT 0")
        _kolon_ekle(baglanti, "notlar", "amire_bilgi_zamani", "TEXT DEFAULT ''")
    for anahtar, deger in VARSAYILAN_AYARLAR.items():
        with baglan() as baglanti:
            baglanti.execute(
                "INSERT OR IGNORE INTO ayarlar (anahtar, deger) VALUES (?, ?)",
                (anahtar, str(deger)),
            )
    # Eski surumde varsayilan 5 gundu; yeni varsayilan 3 gune cekilir.
    # Kullanicinin bilincli olarak 5 secmesi disindaki degerler korunur.
    with baglan() as baglanti:
        baglanti.execute(
            "UPDATE ayarlar SET deger = '3' "
            "WHERE anahtar = 'termin_esik_gun' AND deger = '5'"
        )
    # Eski surumden gelen veri varsa yedek klasoru ayarini yeni konuma tasi.
    _yedek_ayarini_guncelle()


# ---------------------------------------------------------------- ayarlar
def _ayarlari_yukle() -> dict[str, str]:
    global _ayar_onbellek
    if _ayar_onbellek is None:
        _ayar_onbellek = dict(VARSAYILAN_AYARLAR)
        try:
            with baglan() as baglanti:
                for satir in baglanti.execute("SELECT anahtar, deger FROM ayarlar"):
                    _ayar_onbellek[satir["anahtar"]] = satir["deger"]
        except sqlite3.Error:
            pass
    return _ayar_onbellek


def ayar_al(anahtar: str, varsayilan: str | None = None) -> str:
    deger = _ayarlari_yukle().get(anahtar)
    if deger is None:
        return VARSAYILAN_AYARLAR.get(anahtar, varsayilan if varsayilan is not None else "")
    return deger


def ayar_sayi(anahtar: str, varsayilan: int = 0) -> int:
    try:
        return int(float(ayar_al(anahtar)))
    except (TypeError, ValueError):
        return varsayilan


def ayar_acik(anahtar: str) -> bool:
    return str(ayar_al(anahtar)) in ("1", "True", "true", "Evet")


def ayar_yaz(anahtar: str, deger) -> None:
    _ayarlari_yukle()[anahtar] = str(deger)
    with baglan() as baglanti:
        baglanti.execute(
            "INSERT INTO ayarlar (anahtar, deger) VALUES (?, ?) "
            "ON CONFLICT(anahtar) DO UPDATE SET deger = excluded.deger",
            (anahtar, str(deger)),
        )


# ---------------------------------------------------------------- not islemleri
def _temizle(veri: dict) -> dict:
    return {k: v for k, v in veri.items() if k in ALANLAR}


def not_ekle(veri: dict) -> int:
    kayit = {
        "baslik": "",
        "aciklama": "",
        "kategori": "Genel",
        "oncelik": "Normal",
        "etiketler": "",
        "tekrar_tipi": "tek",
        "ay_baslangic_gun": None,
        "ay_bitis_gun": None,
        "hatirlatma_once_dk": 0,
        "durum": "bekliyor",
        "silindi": 0,
        "tur": "not",
        "sorumlu": "",
        "ilerleme": 0,
        "kurum_amir": "",
        "evrak_durum": "Bekliyor",
        "dosya_eki": "",
        "amire_bilgi_verildi": 0,
        "amire_bilgi_zamani": "",
        "olusturma_zamani": zaman_damgasi(),
        "guncelleme_zamani": zaman_damgasi(),
    }
    kayit.update(_temizle(veri))
    sutunlar = ", ".join(kayit.keys())
    yer_tutucu = ", ".join("?" for _ in kayit)
    with baglan() as baglanti:
        imlec = baglanti.execute(
            f"INSERT INTO notlar ({sutunlar}) VALUES ({yer_tutucu})", tuple(kayit.values())
        )
        return int(imlec.lastrowid)


def not_guncelle(not_id: int, veri: dict, zaman_degisti: bool = False) -> None:
    kayit = _temizle(veri)
    kayit["guncelleme_zamani"] = zaman_damgasi()
    if zaman_degisti:
        kayit.update(
            {
                "durum": "bekliyor",
                "tamamlanma_zamani": None,
                "tamamlanan_donem": None,
                "son_uyari_zamani": None,
                "son_uyari_ocak": None,
                "ertelenen_zaman": None,
            }
        )
    atamalar = ", ".join(f"{sutun} = ?" for sutun in kayit)
    with baglan() as baglanti:
        baglanti.execute(
            f"UPDATE notlar SET {atamalar} WHERE id = ?", (*kayit.values(), not_id)
        )


def not_getir(not_id: int) -> dict | None:
    with baglan() as baglanti:
        satir = baglanti.execute("SELECT * FROM notlar WHERE id = ?", (not_id,)).fetchone()
    return dict(satir) if satir else None


def tum_notlar(cop_dahil: bool = False) -> list[dict]:
    sorgu = "SELECT * FROM notlar"
    if not cop_dahil:
        sorgu += " WHERE silindi = 0"
    sorgu += " ORDER BY tarih_saat ASC"
    with baglan() as baglanti:
        return [dict(s) for s in baglanti.execute(sorgu)]


def beklemede_olanlar() -> list[dict]:
    """Uyari kontrolu icin: silinmemis ve tamamlanmamis, tekrarsiz."""
    with baglan() as baglanti:
        satirlar = baglanti.execute(
            "SELECT * FROM notlar WHERE silindi = 0 AND durum != 'tamamlandi' "
            "ORDER BY tarih_saat ASC"
        )
        return [dict(s) for s in satirlar]


def yapildi(not_id: int, donem: str, tekrarlimi: bool) -> None:
    with baglan() as baglanti:
        if tekrarlimi:
            baglanti.execute(
                "UPDATE notlar SET tamamlanan_donem = ?, tamamlanma_zamani = ?, "
                "ertelenen_zaman = NULL, guncelleme_zamani = ? WHERE id = ?",
                (donem, zaman_damgasi(), zaman_damgasi(), not_id),
            )
        else:
            baglanti.execute(
                "UPDATE notlar SET durum = 'tamamlandi', tamamlanma_zamani = ?, "
                "tamamlanan_donem = ?, ertelenen_zaman = NULL, guncelleme_zamani = ? "
                "WHERE id = ?",
                (zaman_damgasi(), donem, zaman_damgasi(), not_id),
            )


def yapildi_geri_al(not_id: int) -> None:
    with baglan() as baglanti:
        baglanti.execute(
            "UPDATE notlar SET durum = 'bekliyor', tamamlanma_zamani = NULL, "
            "tamamlanan_donem = NULL, son_uyari_ocak = NULL, ertelenen_zaman = NULL, "
            "guncelleme_zamani = ? WHERE id = ?",
            (zaman_damgasi(), not_id),
        )


def aylik_gun_isaretle(not_id: int, anahtar: str, yapildi: bool) -> None:
    """Aylik bir gorevin tek bir gununu (YYYY-MM-DD) yapildi/bekliyor olarak isaretler.

    Diger not tipleri ve mevcut alanlar etkilenmez; yalnizca ay_tamamlanan_gunler guncellenir.
    """
    with baglan() as baglanti:
        satir = baglanti.execute(
            "SELECT ay_tamamlanan_gunler FROM notlar WHERE id = ?", (not_id,)
        ).fetchone()
        if satir is None:
            return
        gunler = {
            parca.strip()
            for parca in (satir["ay_tamamlanan_gunler"] or "").split(",")
            if parca.strip()
        }
        if yapildi:
            gunler.add(anahtar)
        else:
            gunler.discard(anahtar)
        if yapildi:
            baglanti.execute(
                "UPDATE notlar SET ay_tamamlanan_gunler = ?, tamamlanma_zamani = ?, "
                "guncelleme_zamani = ? WHERE id = ?",
                (",".join(sorted(gunler)), zaman_damgasi(), zaman_damgasi(), not_id),
            )
        else:
            baglanti.execute(
                "UPDATE notlar SET ay_tamamlanan_gunler = ?, guncelleme_zamani = ? WHERE id = ?",
                (",".join(sorted(gunler)), zaman_damgasi(), not_id),
            )


def ertele(not_id: int, dakika: int) -> str:
    hedef = simdi() + datetime.timedelta(minutes=dakika)
    with baglan() as baglanti:
        baglanti.execute(
            "UPDATE notlar SET ertelenen_zaman = ?, guncelleme_zamani = ? WHERE id = ?",
            (hedef.strftime("%Y-%m-%d %H:%M:%S"), zaman_damgasi(), not_id),
        )
    return hedef.strftime("%d.%m.%Y %H:%M")


def ertelenen_temizle(not_id: int) -> None:
    with baglan() as baglanti:
        baglanti.execute("UPDATE notlar SET ertelenen_zaman = NULL WHERE id = ?", (not_id,))


def uyari_isaretle(not_id: int, ocak: str, zaman: str | None = None) -> None:
    with baglan() as baglanti:
        baglanti.execute(
            "UPDATE notlar SET son_uyari_ocak = ?, son_uyari_zamani = ? WHERE id = ?",
            (ocak, zaman or zaman_damgasi(), not_id),
        )


def uyari_kaydet(not_id: int, baslik: str, islem: str, aciklama: str = "") -> None:
    with baglan() as baglanti:
        baglanti.execute(
            "INSERT INTO uyari_gecmisi (not_id, baslik, uyari_zamani, islem, aciklama) "
            "VALUES (?, ?, ?, ?, ?)",
            (not_id, baslik, zaman_damgasi(), islem, aciklama),
        )


def uyari_gecmisi(not_id: int | None = None, limit: int = 300) -> list[dict]:
    with baglan() as baglanti:
        if not_id is None:
            satirlar = baglanti.execute(
                "SELECT * FROM uyari_gecmisi ORDER BY id DESC LIMIT ?", (limit,)
            )
        else:
            satirlar = baglanti.execute(
                "SELECT * FROM uyari_gecmisi WHERE not_id = ? ORDER BY id DESC LIMIT ?",
                (not_id, limit),
            )
        return [dict(s) for s in satirlar]


# ---------------------------------------------------------------- aylik gecmis
def aylik_gecmis_kaydet(
    not_id: int,
    donem: str,
    baslik: str = "",
    planlanan_gunler: str = "",
    durum: str = "tamamlandi",
    tamamlanma_zamani: str | None = None,
) -> None:
    """Bir notun ilgili ay (YYYY-MM) icin durumunu kaydeder/gunceller."""
    with baglan() as baglanti:
        baglanti.execute(
            "INSERT INTO aylik_gecmis "
            "(not_id, donem, baslik, planlanan_gunler, durum, tamamlanma_zamani, olusturma_zamani) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(not_id, donem) DO UPDATE SET "
            "baslik = excluded.baslik, planlanan_gunler = excluded.planlanan_gunler, "
            "durum = excluded.durum, tamamlanma_zamani = excluded.tamamlanma_zamani",
            (
                not_id,
                donem,
                baslik,
                planlanan_gunler,
                durum,
                tamamlanma_zamani or zaman_damgasi(),
                zaman_damgasi(),
            ),
        )


def aylik_gecmisler(donem: str | None = None, limit: int = 300) -> list[dict]:
    with baglan() as baglanti:
        if donem is None:
            satirlar = baglanti.execute(
                "SELECT * FROM aylik_gecmis ORDER BY donem DESC, not_id ASC LIMIT ?",
                (limit,),
            )
        else:
            satirlar = baglanti.execute(
                "SELECT * FROM aylik_gecmis WHERE donem = ? ORDER BY not_id ASC",
                (donem,),
            )
        return [dict(s) for s in satirlar]


# ---------------------------------------------------------------- aylik gorev sablonlari
def _kural_params_yaz(veri) -> str:
    """rule_params sozlugunu JSON metnine cevirir."""
    return json.dumps(veri if isinstance(veri, dict) else {}, ensure_ascii=False)


def _kural_params_oku(metin) -> dict:
    """Saklanan JSON metnini sozluge cevirir; bozuk/eksik veride {} dondurur."""
    try:
        veri = json.loads(metin or "{}")
    except (TypeError, ValueError):
        return {}
    return veri if isinstance(veri, dict) else {}


def _kural_tipi_dogrula(rule_type: str) -> str:
    if rule_type not in AYLIK_KURAL_TIPLERI:
        raise ValueError(f"Gecersiz rule_type: {rule_type!r}")
    return rule_type


def kural_ekle(
    title: str,
    rule_type: str,
    rule_params: dict,
    reminder_time: str,
    description: str = "",
    active: bool = True,
) -> int:
    """Yeni aylik gorev sablonu ekler ve id'sini dondurur."""
    with baglan() as baglanti:
        imlec = baglanti.execute(
            "INSERT INTO monthly_task_rules "
            "(title, description, rule_type, rule_params, reminder_time, active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                title,
                description,
                _kural_tipi_dogrula(rule_type),
                _kural_params_yaz(rule_params),
                reminder_time,
                1 if active else 0,
                zaman_damgasi(),
            ),
        )
        return int(imlec.lastrowid)


def kurallar(sadece_aktif: bool = False) -> list[dict]:
    """Aylik gorev sablonlarini dondurur; rule_params cozulmus sozluk olarak gelir."""
    sorgu = "SELECT * FROM monthly_task_rules"
    if sadece_aktif:
        sorgu += " WHERE active = 1"
    sorgu += " ORDER BY id ASC"
    with baglan() as baglanti:
        kayitlar = [dict(s) for s in baglanti.execute(sorgu)]
    for kayit in kayitlar:
        kayit["rule_params"] = _kural_params_oku(kayit.get("rule_params"))
    return kayitlar


def kural_getir(kural_id: int) -> dict | None:
    with baglan() as baglanti:
        satir = baglanti.execute(
            "SELECT * FROM monthly_task_rules WHERE id = ?", (kural_id,)
        ).fetchone()
    if satir is None:
        return None
    kayit = dict(satir)
    kayit["rule_params"] = _kural_params_oku(kayit.get("rule_params"))
    return kayit


def kural_guncelle(kural_id: int, **alanlar) -> None:
    """Verilen alanlari gunceller ve updated_at'i yeniler."""
    izinli = {"title", "description", "rule_type", "rule_params", "reminder_time", "active"}
    veri = {anahtar: deger for anahtar, deger in alanlar.items() if anahtar in izinli}
    if not veri:
        return
    if "rule_type" in veri:
        _kural_tipi_dogrula(veri["rule_type"])
    if "rule_params" in veri:
        veri["rule_params"] = _kural_params_yaz(veri["rule_params"])
    if "active" in veri:
        veri["active"] = 1 if veri["active"] else 0
    atamalar = ", ".join(f"{anahtar} = ?" for anahtar in veri)
    with baglan() as baglanti:
        baglanti.execute(
            f"UPDATE monthly_task_rules SET {atamalar}, updated_at = ? WHERE id = ?",
            (*veri.values(), zaman_damgasi(), kural_id),
        )


def kural_sil(kural_id: int) -> None:
    with baglan() as baglanti:
        baglanti.execute("DELETE FROM monthly_task_rules WHERE id = ?", (kural_id,))


# ---------------------------------------------------------------- geri donusum kutusu
def cop_kutusuna_at(not_id: int) -> None:
    with baglan() as baglanti:
        baglanti.execute(
            "UPDATE notlar SET silindi = 1, silinme_zamani = ?, guncelleme_zamani = ? "
            "WHERE id = ?",
            (zaman_damgasi(), zaman_damgasi(), not_id),
        )


def cop_kutusu() -> list[dict]:
    with baglan() as baglanti:
        satirlar = baglanti.execute(
            "SELECT * FROM notlar WHERE silindi = 1 ORDER BY silinme_zamani DESC"
        )
        return [dict(s) for s in satirlar]


def geri_yukle(not_id: int) -> None:
    with baglan() as baglanti:
        baglanti.execute(
            "UPDATE notlar SET silindi = 0, silinme_zamani = NULL, guncelleme_zamani = ? "
            "WHERE id = ?",
            (zaman_damgasi(), not_id),
        )


def kalici_sil(not_id: int) -> None:
    with baglan() as baglanti:
        baglanti.execute("DELETE FROM notlar WHERE id = ?", (not_id,))
        baglanti.execute("DELETE FROM uyari_gecmisi WHERE not_id = ?", (not_id,))


def cop_bosalt() -> int:
    with baglan() as baglanti:
        kimlikler = [
            s["id"] for s in baglanti.execute("SELECT id FROM notlar WHERE silindi = 1")
        ]
        for kimlik in kimlikler:
            baglanti.execute("DELETE FROM notlar WHERE id = ?", (kimlik,))
            baglanti.execute("DELETE FROM uyari_gecmisi WHERE not_id = ?", (kimlik,))
    return len(kimlikler)


# ---------------------------------------------------------------- termin ve gorev ek islemleri
def amire_bilgi_kaydet(not_id: int, bilgi_verildi: bool) -> None:
    damga = zaman_damgasi() if bilgi_verildi else ""
    with baglan() as baglanti:
        baglanti.execute(
            "UPDATE notlar SET amire_bilgi_verildi = ?, amire_bilgi_zamani = ?, guncelleme_zamani = ? "
            "WHERE id = ?",
            (1 if bilgi_verildi else 0, damga, zaman_damgasi(), not_id),
        )


def gorev_ilerleme_kaydet(not_id: int, ilerleme: int) -> None:
    yuzde = max(0, min(100, int(ilerleme)))
    yeni_durum = "tamamlandi" if yuzde == 100 else ("devam" if yuzde > 0 else "bekliyor")
    with baglan() as baglanti:
        baglanti.execute(
            "UPDATE notlar SET ilerleme = ?, durum = ?, guncelleme_zamani = ? WHERE id = ?",
            (yuzde, yeni_durum, zaman_damgasi(), not_id),
        )


def evrak_durum_kaydet(not_id: int, durum: str) -> None:
    with baglan() as baglanti:
        baglanti.execute(
            "UPDATE notlar SET evrak_durum = ?, guncelleme_zamani = ? WHERE id = ?",
            (durum, zaman_damgasi(), not_id),
        )
