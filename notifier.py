"""Windows masaustu bildirimi (winotify) + uygulama ikonu uretimi."""
from __future__ import annotations

import json
import os
import sys
import winreg

from winotify import Notification, audio

import db

SES_SECENEKLERI = ["Varsayılan", "Sessiz", "Hatırlatma", "Posta", "SMS", "Döngü (alarm)"]

_SES_ESLEME = {
    "Varsayılan": audio.Default,
    "Sessiz": audio.Silent,
    "Hatırlatma": audio.Reminder,
    "Posta": audio.Mail,
    "SMS": audio.SMS,
    "Döngü (alarm)": audio.LoopingAlarm,
}

# Onizleme icin Windows bildirim seslerine karsilik gelen medya dosyalari.
# Dosya adlari Windows surumune gore degisebildigi icin sirali adaylar denenir.
_SES_DOSYA_ADLARI = {
    "Varsayılan": ["Windows Notify System Generic.wav", "Windows Notify.wav", "notify.wav"],
    "Hatırlatma": ["Windows Notify Calendar.wav", "Windows Notify.wav", "notify.wav"],
    "Posta": ["Windows Notify Email.wav", "Windows Notify.wav", "notify.wav"],
    "SMS": ["Windows Notify Messaging.wav", "Windows Notify.wav", "notify.wav"],
    "Döngü (alarm)": ["Alarm01.wav", "Alarm02.wav", "Ring01.wav"],
}

# Bildirim uzerindeki dugmelere tiklaninca Windows bu protokol ile uygulamayi calistirir.
PROTOKOL_ADI = "nothatirlatici"
# Bildirim butonlarindan gelen isteklerin biriktirildigi dosya.
_KOMUT_DOSYASI = os.path.join(db.VERI_DIR, "_bildirim_komutu.json")


def _exe_komutu() -> str:
    """Protokol tiklandiginda calistirilacak komut (paketli exe veya pythonw main.py)."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" "%1"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    calistirici = pythonw if os.path.exists(pythonw) else sys.executable
    betik = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return f'"{calistirici}" "{betik}" "%1"'


def protokol_kaydet() -> None:
    """Windows bildirim butonlarinin uygulamayi tetikleyebilmesi icin URL protokolu kaydeder.

    Bildirimdeki 'Ertele' / 'Yapildi' dugmeleri tiklandiginda Windows uygulamayi
    ``nothatirlatici:...`` adresiyle calistirir; uygulama bu adresi bir komuta cevirip
    calisan pencereye iletir.
    """
    try:
        kok = rf"Software\Classes\{PROTOKOL_ADI}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, kok) as anahtar:
            winreg.SetValueEx(anahtar, "", 0, winreg.REG_SZ, f"URL:{PROTOKOL_ADI}")
            winreg.SetValueEx(anahtar, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, kok + r"\shell\open\command"
        ) as anahtar:
            winreg.SetValueEx(anahtar, "", 0, winreg.REG_SZ, _exe_komutu())
    except Exception as hata:  # kayit yapilamazsa bildirimler dugmesiz gosterilir
        print("[protokol kayit hatasi]", hata)


def protokol_komutu(argv: list[str]) -> str | None:
    """Komut satirinda bildirimden gelen ``nothatirlatici:...`` adresini arar."""
    for arg in argv[1:]:
        if arg.startswith(PROTOKOL_ADI + ":"):
            return arg
    return None


def protokol_isle(uri: str) -> bool:
    """Bildirimden gelen adresi komuta cevirip dosyaya yazar.

    Ayrı bir surec olarak calisan uygulama, komutu calisan pencereye (varsa) birakir.
    """
    parcalar = uri.strip().rstrip("/").split(":")
    if len(parcalar) < 4 or parcalar[0] != PROTOKOL_ADI:
        return False
    try:
        deger = int(parcalar[2])
        not_id = int(parcalar[3])
    except (TypeError, ValueError):
        return False
    komut_yaz({"islem": parcalar[1], "id": not_id, "dakika": deger})
    return True


def komut_yaz(komut: dict) -> None:
    """Komutu atomik olarak diske yazar (kismi okuma olmamasi icin)."""
    try:
        os.makedirs(os.path.dirname(_KOMUT_DOSYASI), exist_ok=True)
        gecici = _KOMUT_DOSYASI + ".tmp"
        with open(gecici, "w", encoding="utf-8") as dosya:
            json.dump(komut, dosya)
        os.replace(gecici, _KOMUT_DOSYASI)
    except OSError as hata:
        print("[komut yazma hatasi]", hata)


def komut_oku() -> dict | None:
    """Bekleyen bildirim komutunu okur ve dosyayi siler. Yoksa None."""
    if not os.path.exists(_KOMUT_DOSYASI):
        return None
    veri = None
    try:
        with open(_KOMUT_DOSYASI, "r", encoding="utf-8") as dosya:
            veri = json.load(dosya)
    except Exception:
        veri = None
    try:
        os.remove(_KOMUT_DOSYASI)
    except OSError:
        pass
    return veri if isinstance(veri, dict) else None


def ikon_olustur(yol: str | None = None) -> str:
    """Basit bir zil ikonu uretir (yoksa). Uygulama, tepsi ve bildirim icin kullanilir."""
    yol = yol or db.IKON_YOLU
    if os.path.exists(yol):
        return yol
    try:
        from PIL import Image, ImageDraw

        boyut = 256
        resim = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
        cizim = ImageDraw.Draw(resim)
        mavi = (41, 128, 185, 255)
        kirmizi = (192, 57, 43, 255)
        cizim.ellipse([104, 18, 152, 66], fill=mavi)          # topuz
        cizim.pieslice([40, 44, 216, 220], 180, 360, fill=mavi)  # kubbe
        cizim.rectangle([40, 132, 216, 190], fill=mavi)         # govde
        cizim.rounded_rectangle([26, 184, 230, 212], radius=14, fill=mavi)  # alt kenar
        cizim.ellipse([110, 214, 146, 250], fill=kirmizi)       # dil
        resim.save(yol, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
    except Exception as hata:  # ikon uretilemezse bildirimler ikonsuz calisir
        print("[ikon] uretilemedi:", hata)
    return yol


def bildirim_goster(
    baslik: str, mesaj: str, ses: str | None = None, kayit_id: int | None = None
) -> bool:
    """Windows bildirim balonu gosterir. Basarisiz olursa plyer ile dener.

    ``kayit_id`` verilirse balona Ertele / Yapildi dugmeleri eklenir; boylece
    kullanici uygulamaya donmeden bildirimden dogrudan erteleyebilir.
    """
    ses = ses or db.ayar_al("bildirim_sesi", "Varsayılan")
    ikon = ikon_olustur()
    try:
        balon = Notification(
            app_id="Not ve Hatırlatma",
            title=baslik,
            msg=mesaj,
            duration="long",
            icon=ikon if os.path.exists(ikon) else "",
        )
        if kayit_id is not None:
            for etiket, dakika in (("⏰ 15 dk", 15), ("⏰ 1 saat", 60), ("⏰ 1 gün", 1440)):
                balon.add_actions(
                    etiket, f"{PROTOKOL_ADI}:ertele:{dakika}:{kayit_id}"
                )
            balon.add_actions("✓ Yapıldı", f"{PROTOKOL_ADI}:yapildi:0:{kayit_id}")
        balon.set_audio(_SES_ESLEME.get(ses, audio.Default), loop=False)
        balon.show()
        return True
    except Exception as hata:
        print("[winotify hatasi]", hata)
    try:
        from plyer import notification

        notification.notify(
            title=baslik,
            message=mesaj,
            app_name="Not ve Hatırlatma",
            timeout=10,
        )
        return True
    except Exception as hata:
        print("[plyer hatasi]", hata)
        return False


def ses_cal(ses_adi: str) -> bool:
    """Secilen bildirim sesini onizleme amaciyla calar (Ayarlar ekrani icin).

    Windows bildirim sesleri belirli .wav dosyalarina karsilik gelir; uygun
    dosya bulunamazsa sistem uyari sesi calinir. 'Sessiz' seceneginde hicbir
    sey calinmaz.
    """
    if ses_adi == "Sessiz":
        return False
    try:
        import winsound
    except Exception:
        return False
    medya = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Media")
    for ad in _SES_DOSYA_ADLARI.get(ses_adi, []):
        yol = os.path.join(medya, ad)
        if os.path.exists(yol):
            try:
                winsound.PlaySound(
                    yol,
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
                return True
            except RuntimeError:
                continue
    try:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        return True
    except Exception:
        return False


def test_bildirimi() -> None:
    bildirim_goster(
        "Test bildirimi",
        "Bildirimler bu şekilde görünecek. İyi çalışıyor!",
    )
