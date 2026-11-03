"""Veritabani yedegi ve Excel ice/disa aktarma."""
from __future__ import annotations

import datetime
import os
import shutil

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

import db
import reminder

BASLIKLAR = [
    "Başlık",
    "Açıklama",
    "Kategori",
    "Öncelik",
    "Etiketler",
    "Tarih",
    "Tekrar",
    "Aylık Başlangıç Günü",
    "Aylık Bitiş Günü",
    "Hatırlatma",
    "Durum",
    "Tamamlanma Zamanı",
    "Son Uyarı",
    "Silindi",
]


def yedek_klasoru() -> str:
    klasor = db.ayar_al("yedek_klasoru", db.VARSAYILAN_YEDEK_KLASORU)
    os.makedirs(klasor, exist_ok=True)
    return klasor


def yedek_al(etiket: str | None = None) -> str | None:
    """notlar.db dosyasini yedekler klasorune kopyalar."""
    if not os.path.exists(db.DB_YOLU):
        return None
    damga = etiket or datetime.datetime.now().strftime("%Y-%m-%d")
    hedef = os.path.join(yedek_klasoru(), f"notlar_{damga}.db")
    if os.path.exists(hedef) and etiket is None:
        return hedef
    shutil.copy2(db.DB_YOLU, hedef)
    eski_yedekleri_temizle()
    return hedef


def gunluk_yedek() -> str | None:
    if not db.ayar_acik("gunluk_yedek"):
        return None
    return yedek_al()


def eski_yedekleri_temizle() -> list[str]:
    sinir = db.ayar_sayi("yedek_saklama_gun", 30)
    if sinir <= 0:
        return []
    esik = datetime.datetime.now() - datetime.timedelta(days=sinir)
    silinenler = []
    for dosya in os.listdir(yedek_klasoru()):
        if not (dosya.startswith("notlar_") and dosya.endswith(".db")):
            continue
        tam_yol = os.path.join(yedek_klasoru(), dosya)
        try:
            degisme = datetime.datetime.fromtimestamp(os.path.getmtime(tam_yol))
        except OSError:
            continue
        if degisme < esik:
            try:
                os.remove(tam_yol)
                silinenler.append(dosya)
            except OSError:
                pass
    return silinenler


def excel_disa_aktar(yol: str, cop_dahil: bool = False) -> int:
    kitap = Workbook()
    sayfa = kitap.active
    sayfa.title = "Notlar"
    sayfa.append(BASLIKLAR)
    for hucre in sayfa[1]:
        hucre.font = Font(bold=True)

    sayilar = 0
    for kayit in db.tum_notlar(cop_dahil=cop_dahil):
        zaman = reminder.dt_parse(kayit.get("tarih_saat"))
        sayfa.append(
            [
                kayit.get("baslik", ""),
                kayit.get("aciklama", ""),
                kayit.get("kategori", ""),
                kayit.get("oncelik", ""),
                kayit.get("etiketler", ""),
                zaman,
                reminder.TEKRAR_TERS.get(kayit.get("tekrar_tipi"), "Tek seferlik"),
                kayit.get("ay_baslangic_gun"),
                kayit.get("ay_bitis_gun"),
                reminder.hatirlatma_metni(kayit.get("hatirlatma_once_dk")),
                "Tamamlandı" if kayit.get("durum") == "tamamlandi" else "Bekliyor",
                reminder.dt_parse(kayit.get("tamamlanma_zamani")),
                reminder.dt_parse(kayit.get("son_uyari_zamani")),
                "Evet" if kayit.get("silindi") else "Hayır",
            ]
        )
        sayilar += 1

    for satir in sayfa.iter_rows(min_row=2, min_col=6, max_col=6):
        for hucre in satir:
            hucre.number_format = "yyyy-mm-dd hh:mm"
    sayfa.column_dimensions["A"].width = 32
    sayfa.column_dimensions["B"].width = 48
    kitap.save(yol)
    return sayilar


def excel_ice_aktar(yol: str) -> tuple[int, list[str]]:
    """Excel'den notlari okur ve veritabanina ekler."""
    kitap = load_workbook(yol, data_only=True)
    sayfa = kitap.active
    baslik_satiri = [str(h.value).strip() if h.value is not None else "" for h in sayfa[1]]
    indeks = {ad: i for i, ad in enumerate(baslik_satiri)}

    def al(satir: tuple, ad: str):
        konum = indeks.get(ad)
        if konum is None or konum >= len(satir):
            return None
        return satir[konum]

    eklenen = 0
    hatalar: list[str] = []
    for numara, satir in enumerate(sayfa.iter_rows(min_row=2, values_only=True), start=2):
        if satir is None or all(deger in (None, "") for deger in satir):
            continue
        baslik = str(al(satir, "Başlık") or "").strip()
        zaman = reminder.dt_parse(al(satir, "Tarih"))
        if not baslik or zaman is None:
            hatalar.append(f"{numara}. satır atlandı (başlık veya tarih eksik).")
            continue

        tekrar_metni = str(al(satir, "Tekrar") or "Tek seferlik").strip()
        tekrar_kodu = reminder.TEKRAR_TIPLERI.get(tekrar_metni, "tek")
        hatirlatma_metni = str(al(satir, "Hatırlatma") or "Zamanında").strip()
        once = reminder.HATIRLATMA_SECENEKLERI.get(hatirlatma_metni)
        if once is None:
            once = 0
            try:
                once = int(float(hatirlatma_metni))
            except (TypeError, ValueError):
                once = 0

        def sayi(deger):
            try:
                return int(deger) if deger not in (None, "") else None
            except (TypeError, ValueError):
                return None

        db.not_ekle(
            {
                "baslik": baslik,
                "aciklama": str(al(satir, "Açıklama") or ""),
                "kategori": str(al(satir, "Kategori") or "Genel"),
                "oncelik": str(al(satir, "Öncelik") or "Normal"),
                "etiketler": str(al(satir, "Etiketler") or ""),
                "tarih_saat": zaman.strftime("%Y-%m-%d %H:%M"),
                "tekrar_tipi": tekrar_kodu,
                "ay_baslangic_gun": sayi(al(satir, "Aylık Başlangıç Günü")),
                "ay_bitis_gun": sayi(al(satir, "Aylık Bitiş Günü")),
                "hatirlatma_once_dk": once,
            }
        )
        eklenen += 1
    return eklenen, hatalar
