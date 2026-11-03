"""Hatirlatma motoru: tekrar hesaplama, aylik gun araligi, erteleme ve durum siniflandirma."""
from __future__ import annotations

import calendar
import datetime

PENCERE_GUN = 30  # gecmis uyarilari yakalama penceresi

TEKRAR_TIPLERI = {
    "Tek seferlik": "tek",
    "Her gün": "gunluk",
    "Haftalık": "haftalik",
    "Aylık": "aylik",
    "Yıllık": "yillik",
}
TEKRAR_TERS = {v: k for k, v in TEKRAR_TIPLERI.items()}

HATIRLATMA_SECENEKLERI = {
    "Zamanında": 0,
    "5 dakika önce": 5,
    "15 dakika önce": 15,
    "1 saat önce": 60,
    "1 gün önce": 1440,
}
HATIRLATMA_TERS = {v: k for k, v in HATIRLATMA_SECENEKLERI.items()}

ERTELEME_SECENEKLERI = {"15 dakika": 15, "1 saat": 60, "1 gün": 1440}

ONCELIKLER = ["Düşük", "Normal", "Önemli", "Acil"]
KATEGORILER = ["Genel", "Okul", "Toplantı", "Ödeme", "Rapor", "Kişisel", "Diğer"]

# Esnek aylik kurallar: gun listesi disindaki hazir secenekler.
AYLIK_KURALLAR = {
    "Gün listesi": "liste",
    "Ayın ilk günü": "ilk_gun",
    "Ayın son günü": "son_gun",
    "İlk iş günü (hafta içi)": "ilk_is_gunu",
    "Son iş günü (hafta içi)": "son_is_gunu",
}
AYLIK_KURAL_TERS = {v: k for k, v in AYLIK_KURALLAR.items()}
# Arayuzde secilebilen aylik modlar: kural kodlari + eski gun araligi secenegi.
AYLIK_SECENEKLER = ["Gün listesi", "Gün aralığı"] + [
    ad for ad in AYLIK_KURALLAR if ad != "Gün listesi"
]
AYLIK_KURAL_METIN = {
    "ilk_gun": "her ayın 1'i",
    "son_gun": "her ayın son günü",
    "ilk_is_gunu": "her ayın ilk iş günü",
    "son_is_gunu": "her ayın son iş günü",
}

ONCELIK_RENK = {
    "Düşük": "#7f8c8d",
    "Normal": "#2980b9",
    "Önemli": "#e67e22",
    "Acil": "#c0392b",
}

GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AY_ADLARI = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]

ZAMAN_BICIMLERI = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def dt_parse(metin) -> datetime.datetime | None:
    if metin is None or metin == "":
        return None
    if isinstance(metin, datetime.datetime):
        return metin
    metin = str(metin).strip()
    for bicim in ZAMAN_BICIMLERI:
        try:
            return datetime.datetime.strptime(metin, bicim)
        except ValueError:
            continue
    try:
        return datetime.datetime.fromisoformat(metin)
    except ValueError:
        return None


def not_zamani(not_kaydi: dict) -> datetime.datetime | None:
    return dt_parse(not_kaydi.get("tarih_saat"))


def tekrarli(not_kaydi: dict) -> bool:
    return (not_kaydi.get("tekrar_tipi") or "tek") != "tek"


def aylik_aralik(not_kaydi: dict) -> tuple[int, int] | None:
    bas = not_kaydi.get("ay_baslangic_gun")
    bit = not_kaydi.get("ay_bitis_gun")
    if bas is None or bit is None:
        return None
    try:
        bas, bit = int(bas), int(bit)
    except (TypeError, ValueError):
        return None
    if bas < 1 or bit < 1 or bit < bas:
        return None
    return bas, bit


def is_gunu(gun: datetime.date) -> bool:
    """Hafta ici (Pazartesi-Cuma) mi?"""
    return gun.weekday() < 5


def gun_listesi_ayristir(metin) -> list[int]:
    """'1, 5;15' gibi metni sirali, tekil, 1-31 arasi gun listesine cevirir."""
    if not metin:
        return []
    gunler = set()
    for parca in str(metin).replace(";", ",").split(","):
        parca = parca.strip()
        if not parca:
            continue
        try:
            gun = int(parca)
        except ValueError:
            continue
        if 1 <= gun <= 31:
            gunler.add(gun)
    return sorted(gunler)


def aylik_gun_listesi(not_kaydi: dict) -> list[int]:
    return gun_listesi_ayristir(not_kaydi.get("ay_gun_listesi"))


def aylik_hedef_gunler(not_kaydi: dict, yil: int, ay: int) -> set[int]:
    """Ilgili ay icin uyari verilecek gun numaralari.

    Oncelik sirasi: hazir kural -> gun listesi -> gun araligi -> notun kendi gunu.
    Eski kayitlarda yeni alanlar bos oldugundan davranis aynen korunur.
    """
    son = calendar.monthrange(yil, ay)[1]
    kural = (not_kaydi.get("ay_kural") or "").strip()
    if kural == "ilk_gun":
        return {1}
    if kural == "son_gun":
        return {son}
    if kural == "ilk_is_gunu":
        for gun in range(1, son + 1):
            if is_gunu(datetime.date(yil, ay, gun)):
                return {gun}
        return {1}
    if kural == "son_is_gunu":
        for gun in range(son, 0, -1):
            if is_gunu(datetime.date(yil, ay, gun)):
                return {gun}
        return {son}
    liste = aylik_gun_listesi(not_kaydi)
    if liste:
        return {gun for gun in liste if gun <= son}
    aralik = aylik_aralik(not_kaydi)
    if aralik:
        return set(range(aralik[0], min(aralik[1], son) + 1))
    zaman = not_zamani(not_kaydi)
    if zaman is None:
        return set()
    return {zaman.day}


def _gun_uygun(not_kaydi: dict, gun: datetime.date) -> bool:
    zaman = not_zamani(not_kaydi)
    if zaman is None or gun < zaman.date():
        return False
    tip = not_kaydi.get("tekrar_tipi") or "tek"
    if tip == "tek":
        return gun == zaman.date()
    if tip == "gunluk":
        return True
    if tip == "haftalik":
        return gun.weekday() == zaman.weekday()
    if tip == "aylik":
        return gun.day in aylik_hedef_gunler(not_kaydi, gun.year, gun.month)
    if tip == "yillik":
        return gun.month == zaman.month and gun.day == zaman.day
    return False


def olay_zamanlari(
    not_kaydi: dict, baslangic: datetime.datetime, bitis: datetime.datetime
) -> list[datetime.datetime]:
    """[baslangic, bitis] araligindaki planlanan anlari dondurur."""
    zaman = not_zamani(not_kaydi)
    if zaman is None:
        return []
    sonuc = []
    gun = baslangic.date()
    son_gun = bitis.date()
    while gun <= son_gun:
        if _gun_uygun(not_kaydi, gun):
            sonuc.append(datetime.datetime.combine(gun, zaman.time()))
        gun += datetime.timedelta(days=1)
    return sonuc


def aylik_ay_bazli(not_kaydi: dict, olay: datetime.datetime) -> bool:
    """Aylik tekrarda donem ay bazinda mi, gun bazinda mi?

    Eski "gun araligi" notlari geriye donuk uyumluluk icin ay bazli kalir: bir kez
    yapildi isaretlenince o ayin kalan gunleri de susar. Gun listesi / hazir kurallar
    ile tanimlanan aylik gorevler gun bazlidir; her gun ayri isaretlenir.
    """
    return aylik_aralik(not_kaydi) is not None


def periyot_anahtari(not_kaydi: dict, olay: datetime.datetime) -> str:
    """Bir olayin ait oldugu 'donem' anahtari. 'Yapildi' bu donem icin susar."""
    tip = not_kaydi.get("tekrar_tipi") or "tek"
    if tip == "aylik" and aylik_ay_bazli(not_kaydi, olay):
        return olay.strftime("%Y-%m")
    if tip == "yillik":
        return olay.strftime("%Y")
    return olay.strftime("%Y-%m-%d")


def aylik_tamamlanan_gunler(not_kaydi: dict) -> set[str]:
    """Not icin gun bazli isaretlenmis gun anahtarlari (YYYY-MM-DD)."""
    metin = not_kaydi.get("ay_tamamlanan_gunler") or ""
    return {parca.strip() for parca in str(metin).split(",") if parca.strip()}


def aylik_gun_tamamlandi_mi(not_kaydi: dict, anahtar: str) -> bool:
    """Verilen donem anahtari tamamlanmis mi? (tek donem + aylik gun listesini birlestirir)"""
    if (not_kaydi.get("tamamlanan_donem") or "") == anahtar:
        return True
    if (not_kaydi.get("tekrar_tipi") or "tek") != "aylik":
        return False
    return anahtar in aylik_tamamlanan_gunler(not_kaydi)


def tamamlandi_mi(not_kaydi: dict, olay: datetime.datetime) -> bool:
    """Bu olayin donemi tamamlanmis mi? (tum not tiplerinde geriye donuk uyumlu)"""
    return aylik_gun_tamamlandi_mi(not_kaydi, periyot_anahtari(not_kaydi, olay))


def aylik_gorev_mi(not_kaydi: dict) -> bool:
    """Aylik gorev panosunda gun bazli gosterilecek not mu? (eski gun araligi haric)"""
    if (not_kaydi.get("tekrar_tipi") or "tek") != "aylik":
        return False
    if not_kaydi.get("durum") == "tamamlandi" or not_kaydi.get("silindi"):
        return False
    return aylik_aralik(not_kaydi) is None


def aylik_gorev_gunleri(not_kaydi: dict, yil: int, ay: int) -> list[int]:
    """Aylik bir gorevin ilgili ayda planlanan gunleri (notun baslangicindan sonrakiler)."""
    zaman = not_zamani(not_kaydi)
    if zaman is None:
        return []
    return [
        gun
        for gun in sorted(aylik_hedef_gunler(not_kaydi, yil, ay))
        if datetime.date(yil, ay, gun) >= zaman.date()
    ]


def uyari_zamani(not_kaydi: dict, olay: datetime.datetime) -> datetime.datetime:
    once = int(not_kaydi.get("hatirlatma_once_dk") or 0)
    return olay - datetime.timedelta(minutes=once)


def _ocak(not_kaydi: dict, olay: datetime.datetime) -> str:
    return f"{periyot_anahtari(not_kaydi, olay)}|{olay.strftime('%Y-%m-%d %H:%M')}"


def _son_islem_zamani(not_kaydi: dict) -> datetime.datetime | None:
    """En son uyari / tamamlama / olusturma zamani.

    Tekrarli notlarda bundan eski olaylar 'kacirilmis' sayilmaz; boylece
    ornegin bugun 'Yapildi' isaretlenen gunluk not icin dunku olay tekrar uyarmaz.
    """
    adaylar = [
        dt_parse(not_kaydi.get("son_uyari_zamani")),
        dt_parse(not_kaydi.get("tamamlanma_zamani")),
        dt_parse(not_kaydi.get("olusturma_zamani")),
    ]
    adaylar = [aday for aday in adaylar if aday is not None]
    return max(adaylar) if adaylar else None


def aktif_uyari(not_kaydi: dict, simdi: datetime.datetime) -> dict | None:
    """Simdi gosterilmesi gereken uyari var mi? Yoksa None."""
    if not_kaydi.get("durum") == "tamamlandi":
        return None
    zaman = not_zamani(not_kaydi)
    if zaman is None:
        return None

    ertelenen = dt_parse(not_kaydi.get("ertelenen_zaman"))
    if ertelenen is not None:
        if ertelenen > simdi:
            return None  # ertelendi, vakti gelene kadar sus
        return {
            "olay": zaman,
            "uyari": ertelenen,
            "ocak": not_kaydi.get("son_uyari_ocak") or "",
            "kaynak": "erteleme",
        }

    son_islem = _son_islem_zamani(not_kaydi) if tekrarli(not_kaydi) else None
    olaylar = olay_zamanlari(not_kaydi, simdi - datetime.timedelta(days=PENCERE_GUN), simdi)
    for olay in reversed(olaylar):
        if son_islem is not None and olay <= son_islem:
            break
        uyari = uyari_zamani(not_kaydi, olay)
        if uyari > simdi:
            continue
        if tamamlandi_mi(not_kaydi, olay):
            continue
        ocak = _ocak(not_kaydi, olay)
        if not_kaydi.get("son_uyari_ocak") == ocak:
            continue
        return {"olay": olay, "uyari": uyari, "ocak": ocak, "kaynak": "plan"}
    return None


def geciken_olay(not_kaydi: dict, simdi: datetime.datetime) -> tuple | None:
    """Bu donem icin tamamlanmamis, zamani gecmis en yeni olay (olay, uyari)."""
    if not_kaydi.get("durum") == "tamamlandi":
        return None
    zaman = not_zamani(not_kaydi)
    if zaman is None:
        return None

    ertelenen = dt_parse(not_kaydi.get("ertelenen_zaman"))
    if ertelenen is not None and ertelenen > simdi:
        return None  # ertelendi, beklemede

    if not tekrarli(not_kaydi):
        if zaman < simdi:
            return zaman, uyari_zamani(not_kaydi, zaman)
        return None

    tamamlanma = dt_parse(not_kaydi.get("tamamlanma_zamani"))
    for olay in reversed(
        olay_zamanlari(not_kaydi, simdi - datetime.timedelta(days=PENCERE_GUN), simdi)
    ):
        if tamamlanma is not None and olay <= tamamlanma:
            break
        uyari = uyari_zamani(not_kaydi, olay)
        if uyari > simdi:
            continue
        if tamamlandi_mi(not_kaydi, olay):
            continue
        return olay, uyari
    return None


def bugunun_olaylari(not_kaydi: dict, simdi: datetime.datetime) -> list[datetime.datetime]:
    """Bugun uyarilacak olaylar (bugun son gunu olanlar dahil)."""
    if not_kaydi.get("durum") == "tamamlandi":
        return []
    bugun = simdi.date()
    baslangic = datetime.datetime.combine(bugun, datetime.time.min)
    bitis = datetime.datetime.combine(bugun, datetime.time.max)
    sonuc = []
    for olay in olay_zamanlari(not_kaydi, baslangic, bitis):
        if tamamlandi_mi(not_kaydi, olay):
            continue
        sonuc.append(olay)
    return sonuc


def sonraki_olay(
    not_kaydi: dict, simdi: datetime.datetime, arama_gun: int = 800
) -> datetime.datetime | None:
    """Simdiden sonraki ilk planlanan an. Gecmis tek seferlik notlarda None."""
    if not_kaydi.get("durum") == "tamamlandi":
        return None
    zaman = not_zamani(not_kaydi)
    if zaman is None:
        return None
    if not tekrarli(not_kaydi):
        return zaman if zaman >= simdi else None

    gun = simdi.date()
    for fark in range(arama_gun):
        aday_gun = gun + datetime.timedelta(days=fark)
        if not _gun_uygun(not_kaydi, aday_gun):
            continue
        olay = datetime.datetime.combine(aday_gun, zaman.time())
        if olay < simdi:
            continue
        if tamamlandi_mi(not_kaydi, olay):
            continue
        return olay
    return None


# ---------------------------------------------------------------- metinler
def kalan_metin(hedef: datetime.datetime | None, simdi: datetime.datetime) -> str:
    if hedef is None:
        return "-"
    fark = hedef - simdi
    saniye = int(abs(fark.total_seconds()))
    gun, kalan = divmod(saniye, 86400)
    saat, kalan = divmod(kalan, 3600)
    dakika = kalan // 60
    parcalar = []
    if gun:
        parcalar.append(f"{gun} gün")
    if saat:
        parcalar.append(f"{saat} saat")
    if dakika and not gun:
        parcalar.append(f"{dakika} dk")
    if not parcalar:
        parcalar.append("1 dk'dan az")
    metin = " ".join(parcalar)
    return f"{metin} kaldı" if fark.total_seconds() >= 0 else f"{metin} gecikti"


def tekrar_metni(not_kaydi: dict) -> str:
    tip = not_kaydi.get("tekrar_tipi") or "tek"
    if tip == "tek":
        return "Tek seferlik"
    if tip == "gunluk":
        return "Her gün"
    if tip == "haftalik":
        zaman = not_zamani(not_kaydi)
        gun = GUN_ADLARI[zaman.weekday()] if zaman else ""
        return f"Haftalık ({gun})"
    if tip == "aylik":
        kural = (not_kaydi.get("ay_kural") or "").strip()
        if kural in AYLIK_KURAL_METIN:
            return f"Aylık ({AYLIK_KURAL_METIN[kural]})"
        liste = aylik_gun_listesi(not_kaydi)
        if liste:
            gunler = ", ".join(str(gun) for gun in liste)
            return f"Aylık (her ayın {gunler}. günü)"
        aralik = aylik_aralik(not_kaydi)
        if aralik:
            return f"Aylık (her ayın {aralik[0]}-{aralik[1]} arası)"
        zaman = not_zamani(not_kaydi)
        return f"Aylık (her ayın {zaman.day}'i)" if zaman else "Aylık"
    if tip == "yillik":
        zaman = not_zamani(not_kaydi)
        if zaman:
            return f"Yıllık ({zaman.day} {AY_ADLARI[zaman.month - 1]})"
        return "Yıllık"
    return "Tek seferlik"


def hatirlatma_metni(dakika: int | None) -> str:
    return HATIRLATMA_TERS.get(int(dakika or 0), f"{dakika} dakika önce")


def zaman_metni(zaman: datetime.datetime | None) -> str:
    if zaman is None:
        return "-"
    return f"{zaman.strftime('%d.%m.%Y %H:%M')} ({GUN_ADLARI[zaman.weekday()]})"


def donem_metni(not_kaydi: dict, simdi: datetime.datetime) -> str:
    """Listeler icin kisa durum aciklamasi."""
    if not_kaydi.get("durum") == "tamamlandi":
        tamam = dt_parse(not_kaydi.get("tamamlanma_zamani"))
        return f"Tamamlandı: {tamam.strftime('%d.%m.%Y %H:%M') if tamam else '-'}"

    ertelenen = dt_parse(not_kaydi.get("ertelenen_zaman"))
    if ertelenen is not None and ertelenen > simdi:
        return f"Ertelendi: {ertelenen.strftime('%d.%m.%Y %H:%M')}"

    bugun = bugunun_olaylari(not_kaydi, simdi)
    if bugun:
        return f"Bugün uyarı: {bugun[-1].strftime('%H:%M')}"

    sonraki = sonraki_olay(not_kaydi, simdi)
    if sonraki is not None:
        return f"Sonraki: {sonraki.strftime('%d.%m.%Y %H:%M')} ({kalan_metin(sonraki, simdi)})"

    geciken = geciken_olay(not_kaydi, simdi)
    if geciken is not None:
        return f"Gecikti: {geciken[0].strftime('%d.%m.%Y %H:%M')}"

    zaman = not_zamani(not_kaydi)
    return zaman.strftime("%d.%m.%Y %H:%M") if zaman else "-"
