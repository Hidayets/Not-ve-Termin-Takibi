"""GitHub Releases uzerinden otomatik guncelleme.

Akis:
1. Arka planda GitHub Releases API'sinden son surum kontrol edilir.
2. Daha yeni bir surum varsa exe, kullanici profilindeki 'guncelleme'
   klasorune indirilir (uygulama calisirken, arka planda).
3. Uygulama bir sonraki kez baslatildiginda, indirilen exe yardimci bir
   toplu is dosyasi (bat) ile mevcut exe'nin uzerine yazilir ve uygulama
   yeniden baslatilir. Uygulama tepsidе calisiyor olsa bile yeni bir ornek
   acildiginda mevcut ornek guncellemeyi kurup yeniden baslar. Boylece
   guncelleme; uygulama yeniden baslatildiginda (ya da bilgisayar yeniden
   baslatildiginda) devreye girer.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import db

REPO = "Hidayets/Not-ve-Termin-Takibi"
ASSET_UZANTI = ".exe"
GUNCELLEME_KLASORU = os.path.join(db.VERI_DIR, "guncelleme")
INDIRILEN_EXE = os.path.join(GUNCELLEME_KLASORU, "NotlarimVeTerminTakibi.exe")
META_DOSYASI = os.path.join(GUNCELLEME_KLASORU, "surum.json")
DURUM_DOSYASI = os.path.join(GUNCELLEME_KLASORU, "durum.json")
_USER_AGENT = "NotlarimVeTerminTakibi-Updater"

_kontrol_kilidi = threading.Lock()
_kontrol_thread: threading.Thread | None = None


# --------------------------------------------------------------- surum
def _surum_parcalari(surum: str) -> tuple[int, ...]:
    """'v1.2.3' -> (1, 2, 3) seklinde sayisal karsilastirma anahtari uretir."""
    temiz = (surum or "").strip().lstrip("vV")
    parcalar: list[int] = []
    for parca in temiz.split("."):
        sayi = ""
        for karakter in parca:
            if karakter.isdigit():
                sayi += karakter
            else:
                break
        if not sayi:
            break
        parcalar.append(int(sayi))
    return tuple(parcalar) if parcalar else (0,)


def surum_buyuk_mu(yeni: str, mevcut: str) -> bool:
    return _surum_parcalari(yeni) > _surum_parcalari(mevcut)


def repo_adresi() -> str:
    return (db.ayar_al("guncelleme_repo", REPO) or "").strip()


# --------------------------------------------------------------- ag
def _json_istek(url: str, timeout: float = 15.0) -> dict | None:
    istek = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(istek, timeout=timeout) as yanit:
            return json.loads(yanit.read().decode("utf-8"))
    except urllib.error.HTTPError as hata:
        if hata.code == 404:
            return {}
        print("[guncelleme api hatasi]", hata)
    except Exception as hata:  # ag yok, zaman asimi, json hatasi vb.
        print("[guncelleme api hatasi]", hata)
    return None


def son_surum_bilgisi() -> dict | None:
    """Son yayinin surum etiketini ve exe indirme adresini dondurur."""
    repo = repo_adresi()
    if "/" not in repo:
        return None
    veri = _json_istek(f"https://api.github.com/repos/{repo}/releases/latest")
    if veri is None:
        return None  # ag hatasi
    if not veri:
        # Depo ya da yayin bulunamadi (HTTP 404).
        return {"surum": "", "notlar": "", "exe_url": "", "boyut": 0, "tarih": ""}

    exe_url = ""
    boyut = 0
    for varlik in veri.get("assets") or []:
        ad = str(varlik.get("name") or "")
        if ad.lower().endswith(ASSET_UZANTI):
            exe_url = str(varlik.get("browser_download_url") or "")
            boyut = int(varlik.get("size") or 0)
            break
    return {
        "surum": str(veri.get("tag_name") or "").strip(),
        "notlar": str(veri.get("body") or "").strip(),
        "exe_url": exe_url,
        "boyut": boyut,
        "tarih": str(veri.get("published_at") or ""),
    }


def _indir(url: str, hedef: str) -> bool:
    try:
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        gecici = hedef + ".tmp"
        istek = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(istek, timeout=120) as yanit, open(
            gecici, "wb"
        ) as dosya:
            shutil.copyfileobj(yanit, dosya, length=1024 * 256)
        os.replace(gecici, hedef)
        return True
    except Exception as hata:
        print("[guncelleme indirme hatasi]", hata)
        try:
            os.remove(hedef + ".tmp")
        except OSError:
            pass
        return False


# --------------------------------------------------------------- durum dosyalari
def durum_oku() -> dict:
    try:
        with open(DURUM_DOSYASI, "r", encoding="utf-8") as dosya:
            veri = json.load(dosya)
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def _durum_yaz(**alanlar) -> None:
    durum = durum_oku()
    durum.update(alanlar)
    try:
        os.makedirs(GUNCELLEME_KLASORU, exist_ok=True)
        gecici = DURUM_DOSYASI + ".tmp"
        with open(gecici, "w", encoding="utf-8") as dosya:
            json.dump(durum, dosya, ensure_ascii=False)
        os.replace(gecici, DURUM_DOSYASI)
    except OSError:
        pass


def _meta_yaz(meta: dict) -> None:
    try:
        os.makedirs(GUNCELLEME_KLASORU, exist_ok=True)
        with open(META_DOSYASI, "w", encoding="utf-8") as dosya:
            json.dump(meta, dosya, ensure_ascii=False)
    except OSError:
        pass


def _meta_oku() -> dict:
    try:
        with open(META_DOSYASI, "r", encoding="utf-8") as dosya:
            veri = json.load(dosya)
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


# --------------------------------------------------------------- kontrol / indirme
def kontrol_et_ve_indir() -> str:
    """Son surumu kontrol eder, yeniyse arka planda indirir ve durum mesaji doner."""
    zaman = db.zaman_damgasi()
    bilgi = son_surum_bilgisi()
    if bilgi is None:
        mesaj = "Güncelleme sunucusuna ulaşılamadı."
        _durum_yaz(son_kontrol=zaman, son_kontrol_ts=time.time(), mesaj=mesaj)
        return mesaj

    surum = bilgi.get("surum") or ""
    if not surum or not bilgi.get("exe_url"):
        mesaj = "Yayınlanmış güncelleme bulunamadı."
        _durum_yaz(
            son_kontrol=zaman, son_kontrol_ts=time.time(), mesaj=mesaj, son_surum=surum
        )
        return mesaj

    if not surum_buyuk_mu(surum, db.SURUM):
        mesaj = f"Güncel sürümdesiniz ({db.SURUM})."
        _durum_yaz(
            son_kontrol=zaman, son_kontrol_ts=time.time(), mesaj=mesaj, son_surum=surum
        )
        return mesaj

    _durum_yaz(
        son_kontrol=zaman,
        son_kontrol_ts=time.time(),
        mesaj=f"{surum} indiriliyor...",
        son_surum=surum,
    )
    if _indir(bilgi["exe_url"], INDIRILEN_EXE):
        _meta_yaz(
            {
                "surum": surum,
                "boyut": bilgi.get("boyut") or 0,
                "notlar": bilgi.get("notlar") or "",
            }
        )
        mesaj = f"{surum} indirildi; yeniden başlatılınca kurulacak."
    else:
        mesaj = "Güncelleme indirilemedi."
    _durum_yaz(
        son_kontrol=zaman, son_kontrol_ts=time.time(), mesaj=mesaj, son_surum=surum
    )
    return mesaj


def bekleyen_guncelleme() -> dict | None:
    """Indirilmis ve kurulmayi bekleyen guncelleme varsa meta bilgisini doner."""
    if not os.path.exists(INDIRILEN_EXE):
        return None
    meta = _meta_oku()
    surum = str(meta.get("surum") or "")
    if not surum or not surum_buyuk_mu(surum, db.SURUM):
        return None
    boyut = int(meta.get("boyut") or 0)
    if boyut and os.path.getsize(INDIRILEN_EXE) != boyut:
        return None
    return meta


# --------------------------------------------------------------- uygulama
def _yardimci_betik(hedef: str) -> str | None:
    """Mevcut surec kapaninca exe'yi degistirip yeniden baslatan bat dosyasi."""
    betik = os.path.join(GUNCELLEME_KLASORU, "guncelle.bat")
    pid = os.getpid()
    icerik = (
        "@echo off\r\n"
        "setlocal\r\n"
        ":bekle\r\n"
        f'tasklist /FI "PID eq {pid}" /NH 2>nul | find "{pid}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  ping -n 2 127.0.0.1 >nul\r\n"
        "  goto bekle\r\n"
        ")\r\n"
        f'copy /Y "{INDIRILEN_EXE}" "{hedef}" >nul 2>&1\r\n'
        f'if not errorlevel 1 del /Q "{INDIRILEN_EXE}" >nul 2>&1\r\n'
        f'start "" "{hedef}"\r\n'
        '(goto) 2>nul & del "%~f0"\r\n'
    )
    try:
        os.makedirs(GUNCELLEME_KLASORU, exist_ok=True)
        with open(betik, "w", encoding="mbcs", errors="replace") as dosya:
            dosya.write(icerik)
        return betik
    except OSError as hata:
        print("[guncelleme betik hatasi]", hata)
        return None


def guncellemeyi_uygula() -> bool:
    """Indirilen guncellemeyi kurar. True donerse cagiran uygulama kapanmalidir."""
    if not getattr(sys, "frozen", False):
        return False  # gelistirme (.py) modunda calisan exe degistirilemez
    if bekleyen_guncelleme() is None:
        return False
    hedef = os.path.abspath(sys.executable)
    betik = _yardimci_betik(hedef)
    if betik is None:
        return False
    try:
        subprocess.Popen(
            ["cmd", "/c", betik],
            cwd=GUNCELLEME_KLASORU,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
            close_fds=True,
        )
        return True
    except OSError as hata:
        print("[guncelleme uygulama hatasi]", hata)
        return False


# --------------------------------------------------------------- periyodik
def _zaman_geldi() -> bool:
    saat = max(1, db.ayar_sayi("guncelleme_kontrol_saat", 6))
    son = durum_oku().get("son_kontrol_ts") or 0
    try:
        return (time.time() - float(son)) >= saat * 3600
    except (TypeError, ValueError):
        return True


def _arka_planda_kontrol() -> None:
    if not _kontrol_kilidi.acquire(blocking=False):
        return
    try:
        kontrol_et_ve_indir()
    except Exception as hata:
        print("[guncelleme kontrol hatasi]", hata)
    finally:
        _kontrol_kilidi.release()


def periyodik_kontrol_baslat() -> None:
    """Arka planda surum kontrolu/indirmesi baslatir; zaten calisiyorsa tekrarlamaz."""
    global _kontrol_thread
    if not db.ayar_acik("guncelleme_otomatik"):
        return
    if _kontrol_thread is not None and _kontrol_thread.is_alive():
        return
    if not _zaman_geldi():
        return
    _kontrol_thread = threading.Thread(target=_arka_planda_kontrol, daemon=True)
    _kontrol_thread.start()
