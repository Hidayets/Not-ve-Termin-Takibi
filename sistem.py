"""Windows ile ilgili yardimci islemler: otomatik baslatma, tek ornek kilidi."""
from __future__ import annotations

import ctypes
import os
import sys
import winreg

KAYIT_YOLU = r"Software\Microsoft\Windows\CurrentVersion\Run"
KAYIT_ADI = "NotHatirlatici"

# Tek ornek (single instance) icin adlandirilmis mutex adi.
KILIT_ADI = "NotlarimVeTerminTakibi.TekOranek"
_ERROR_ALREADY_EXISTS = 183
_tutamac = None  # mutex tutamaci; surec boyunca canli kalmali


def uygulama_komutu() -> str:
    """Acilista calistirilacak komut (konsol penceresi gorunmez)."""
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}"'
    python_w = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(python_w):
        python_w = sys.executable
    betik = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return f'"{python_w}" "{betik}"'


def otomatik_baslat_acik_mi() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KAYIT_YOLU, 0, winreg.KEY_READ) as anahtar:
            deger, _ = winreg.QueryValueEx(anahtar, KAYIT_ADI)
            return bool(deger)
    except OSError:
        return False


def otomatik_baslat_ayarla(acik: bool) -> bool:
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, KAYIT_YOLU, 0, winreg.KEY_SET_VALUE
        ) as anahtar:
            if acik:
                winreg.SetValueEx(anahtar, KAYIT_ADI, 0, winreg.REG_SZ, uygulama_komutu())
            else:
                try:
                    winreg.DeleteValue(anahtar, KAYIT_ADI)
                except FileNotFoundError:
                    pass
        return True
    except OSError as hata:
        print("[otomatik baslatma hatasi]", hata)
        return False


# --------------------------------------------------------------- tek ornek
def _goster_dosyasi() -> str:
    """Ikinci ornegin 'pencereyi goster' istegini biraktigi dosya yolu."""
    import db  # dongusel ice aktarmayi onlemek icin tembel yuklenir

    return os.path.join(db.VERI_DIR, "_pencere_goster.json")


def kilit_al() -> bool:
    """Uygulamanin tek ornegi oldugunu garanti eder.

    Adlandirilmis bir mutex olusturur. Mutex zaten varsa (baska bir ornek
    calisiyorsa) False doner; bu durumda cagiran taraf mevcut pencereyi one
    getirip kendini kapatmalidir. True donerse kilit bu surece aittir.
    """
    global _tutamac
    try:
        cekirdek = ctypes.WinDLL("kernel32", use_last_error=True)
        cekirdek.CreateMutexW.argtypes = (
            ctypes.c_void_p,
            ctypes.c_bool,
            ctypes.c_wchar_p,
        )
        cekirdek.CreateMutexW.restype = ctypes.c_void_p
        cekirdek.CloseHandle.argtypes = (ctypes.c_void_p,)
        tutamac = cekirdek.CreateMutexW(None, False, KILIT_ADI)
        if not tutamac:
            return True  # API basarisizsa kilidi zorlamayalim
        if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
            cekirdek.CloseHandle(tutamac)
            return False
        _tutamac = tutamac  # surec boyunca canli kalsin (cop toplamayi engelle)
        return True
    except Exception as hata:
        print("[kilit hatasi]", hata)
        return True


def goster_sinyali_gonder() -> None:
    """Calisan ornege 'pencereni one getir' istegi birakir."""
    try:
        yol = _goster_dosyasi()
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write("1")
    except OSError as hata:
        print("[goster sinyali hatasi]", hata)


def goster_sinyali_oku() -> bool:
    """Bekleyen 'pencereyi goster' istegini okur ve temizler."""
    yol = _goster_dosyasi()
    if not os.path.exists(yol):
        return False
    try:
        os.remove(yol)
    except OSError:
        pass
    return True


# --------------------------------------------------- guncelleme sinyali
def _guncelleme_dosyasi() -> str:
    """Ikinci ornegin 'guncellemeyi kur ve yeniden baslat' istegi dosyasi."""
    import db

    return os.path.join(db.VERI_DIR, "_guncelle.json")


def guncelleme_sinyali_gonder() -> None:
    """Calisan ornege 'indirilen guncellemeyi kur ve yeniden baslat' istegi birakir."""
    try:
        yol = _guncelleme_dosyasi()
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write("1")
    except OSError as hata:
        print("[guncelleme sinyali hatasi]", hata)


def guncelleme_sinyali_oku() -> bool:
    """Bekleyen 'guncellemeyi kur' istegini okur ve temizler."""
    yol = _guncelleme_dosyasi()
    if not os.path.exists(yol):
        return False
    try:
        os.remove(yol)
    except OSError:
        pass
    return True
