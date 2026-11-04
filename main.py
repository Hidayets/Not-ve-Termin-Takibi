"""Notlarım & Termin Takibi - giriş noktası.

Python + CustomTkinter ile yazilmis, Turkce arayuzlu masaustu not/hatirlatma uygulamasi.
Calistirmak icin: pythonw main.py
"""
from __future__ import annotations

import datetime
import sys
import threading
import time

import customtkinter as ctk

import db
import guncelleme
import notifier
import reminder
import sistem
import yedek
from arayuz.ana_pencere import AnaPencere
from arayuz.sekme_ayarlar import tema_modu
from tray import Tepsi


class NotHatirlatici:
    def __init__(self):
        db.veritabani_olustur()
        yedek.gunluk_yedek()
        notifier.ikon_olustur()
        notifier.protokol_kaydet()

        ctk.set_appearance_mode(tema_modu(db.ayar_al("tema", "dark")))
        ctk.set_default_color_theme("blue")

        self.pencere = AnaPencere(self)
        self.calisiyor = True

        self.tepsi = Tepsi(
            pencere_goster=self._tepsi_pencere,
            gunluk_goster=self._tepsi_bugun,
            ayarlari_goster=self._tepsi_ayarlar,
            cikis=self._tepsi_cikis,
        )
        self.tepsi.baslat()

        self.kontrol_thread = threading.Thread(target=self.kontrol_dongusu, daemon=True)
        self.kontrol_thread.start()

    # ------------------------------------------------------------- tepsi
    def _tepsi_pencere(self, sekme: str | None = None) -> None:
        self.pencere.after(0, lambda: self.pencere.pencereyi_goster(sekme))

    def _tepsi_bugun(self) -> None:
        self.pencere.after(0, lambda: self.pencere.pencereyi_goster("Bugün"))

    def _tepsi_ayarlar(self) -> None:
        self.pencere.after(0, lambda: self.pencere.pencereyi_goster("Ayarlar"))

    def _tepsi_cikis(self) -> None:
        self.pencere.after(0, self.cikis)

    # ------------------------------------------------------------- tema
    def tema_uygula(self) -> None:
        ctk.set_appearance_mode(tema_modu(db.ayar_al("tema", "dark")))

    # ------------------------------------------------------------- zamanlayici
    def kontrol_dongusu(self) -> None:
        while self.calisiyor:
            try:
                self.kontrol_et()
            except Exception as hata:  # dongu asla olmemeli
                print("[kontrol hatasi]", hata)
            # Arka planda guncelleme kontrolu/indirmesi (ayarliysa).
            guncelleme.periyodik_kontrol_baslat()
            aralik = max(5, db.ayar_sayi("kontrol_araligi_sn", 20))
            for _ in range(aralik):
                if not self.calisiyor:
                    return
                try:
                    self.bildirim_komutlarini_isle()
                    if sistem.guncelleme_sinyali_oku():
                        # Yeniden baslatan ornek guncellemeyi kurmamizi istedi.
                        self.guncellemeyi_uygula_ve_cik()
                        return
                    if sistem.goster_sinyali_oku():
                        self.pencere.after(0, lambda: self.pencere.pencereyi_goster())
                except Exception as hata:
                    print("[komut hatasi]", hata)
                time.sleep(1)

    def bildirim_komutlarini_isle(self) -> None:
        """Windows bildirim dugmelerinden gelen ertele/yapildi isteklerini uygular."""
        komut = notifier.komut_oku()
        if not komut:
            return
        try:
            not_id = int(komut.get("id"))
        except (TypeError, ValueError):
            return
        if komut.get("islem") == "ertele":
            dakika = int(komut.get("dakika") or 15)
            self.ertele_uyari(not_id, dakika, kaynak="bildirim")
        elif komut.get("islem") == "yapildi":
            self.yapildi_isaretle(not_id)
        else:
            return
        # Bildirimden isaretlenen kaydin hala acik olan penceresi varsa kapat.
        try:
            self.pencere.after(0, lambda: self.pencere.uyari_kapat_id(not_id))
        except Exception:
            pass

    def kontrol_et(self) -> None:
        """Bekleyen notlari tarar; zamani gelen uyarilari gosterir."""
        simdi = datetime.datetime.now()
        for kayit in db.beklemede_olanlar():
            uyari = reminder.aktif_uyari(kayit, simdi)
            if uyari is None:
                continue
            self.uyari_gonder(kayit, uyari)

    def uyari_gonder(self, kayit: dict, uyari: dict) -> None:
        olay = uyari["olay"]
        aciklama = (kayit.get("aciklama") or "").strip()
        mesaj = aciklama if aciklama else "Hatırlatma zamanı geldi."
        mesaj += f"  (Planlanan: {olay.strftime('%d.%m.%Y %H:%M')})"

        notifier.bildirim_goster(
            kayit.get("baslik") or "Hatırlatma", mesaj, kayit_id=kayit.get("id")
        )
        db.uyari_isaretle(kayit["id"], uyari["ocak"])
        if uyari["kaynak"] == "erteleme":
            db.erteleme_temizle(kayit["id"])
        db.uyari_kaydet(
            kayit["id"],
            kayit.get("baslik") or "",
            "gösterildi",
            f"Kaynak: {'erteleme' if uyari['kaynak'] == 'erteleme' else 'plan'}",
        )
        self.pencere.uyari_ekle(kayit, olay)
        self.arayuzu_yenile()

    # ------------------------------------------------------------- islemler
    def arayuzu_yenile(self) -> None:
        try:
            self.pencere.after(0, self.pencere.yenile)
        except Exception:
            pass

    def yenile(self) -> None:
        self.pencere.yenile()

    def _uygun_olay(self, kayit: dict, olay: datetime.datetime | None) -> datetime.datetime:
        if olay is not None:
            return olay
        simdi = datetime.datetime.now()
        bugun = reminder.bugunun_olaylari(kayit, simdi)
        if bugun:
            return bugun[-1]
        return reminder.not_zamani(kayit) or simdi

    def yapildi_isaretle(self, not_id: int, olay: datetime.datetime | None = None) -> None:
        kayit = db.not_getir(not_id)
        if kayit is None:
            return
        olay = self._uygun_olay(kayit, olay)
        donem = reminder.periyot_anahtari(kayit, olay)
        db.yapildi(not_id, donem, reminder.tekrarli(kayit))
        db.uyari_kaydet(
            not_id,
            kayit.get("baslik") or "",
            "yapıldı",
            f"Dönem: {donem}"
            + (" (tekrarlı not, sonraki dönemde yeniden uyarır)" if reminder.tekrarli(kayit) else ""),
        )
        self.arayuzu_yenile()

    def aylik_gun_degistir(self, not_id: int, anahtar: str, yapildi: bool) -> None:
        """Aylik bir gorevin tek bir gununu isaretler/geri alir (gun bazli takip)."""
        kayit = db.not_getir(not_id)
        if kayit is None:
            return
        db.aylik_gun_isaretle(not_id, anahtar, yapildi)
        db.uyari_kaydet(
            not_id,
            kayit.get("baslik") or "",
            "aylık gün yapıldı" if yapildi else "aylık gün geri alındı",
            f"Gün: {anahtar}",
        )
        self.arayuzu_yenile()

    def tamamlamayi_geri_al(self, not_id: int) -> None:
        kayit = db.not_getir(not_id)
        if kayit is None:
            return
        db.yapildi_geri_al(not_id)
        db.uyari_kaydet(not_id, kayit.get("baslik") or "", "geri alındı", "")
        self.arayuzu_yenile()

    def ertele_uyari(self, not_id: int, dakika: int, kaynak: str = "liste") -> None:
        kayit = db.not_getir(not_id)
        if kayit is None:
            return
        hedef = db.ertele(not_id, dakika)
        db.uyari_kaydet(
            not_id,
            kayit.get("baslik") or "",
            "ertelendi",
            f"{dakika} dakika sonra ({hedef}) - kaynak: {kaynak}",
        )
        self.arayuzu_yenile()

    def cop_kutusuna_at(self, not_id: int) -> None:
        kayit = db.not_getir(not_id)
        db.cop_kutusuna_at(not_id)
        if kayit:
            db.uyari_kaydet(not_id, kayit.get("baslik") or "", "geri dönüşüm kutusuna taşındı", "")
        self.arayuzu_yenile()

    def cop_kutusundan_geri_al(self, not_id: int) -> None:
        db.geri_yukle(not_id)
        self.arayuzu_yenile()

    def kalici_sil(self, not_id: int) -> None:
        db.kalici_sil(not_id)
        self.arayuzu_yenile()

    # ------------------------------------------------------------- yasam dongusu
    def guncellemeyi_uygula_ve_cik(self) -> None:
        """Indirilen guncellemeyi kurar ve uygulamayi kapatir.

        Yardimci toplu is dosyasi bu surec kapandiktan sonra exe'yi degistirip
        yeni surumu otomatik baslatir. Boylece uygulama yeniden acildiginda
        guncelleme devreye girmis olur.
        """
        if guncelleme.guncellemeyi_uygula():
            self.pencere.after(0, self.cikis)
        else:
            # Kurulamadiysa (or. gelistirme modu) pencereyi one getirmekle yetin.
            self.pencere.after(0, lambda: self.pencere.pencereyi_goster())

    def cikis(self) -> None:
        if not self.calisiyor:
            return
        self.calisiyor = False
        try:
            self.tepsi.durdur()
        except Exception:
            pass
        try:
            self.pencere.destroy()
        except Exception:
            pass

    def calistir(self) -> None:
        self.pencere.mainloop()


def main() -> None:
    # Windows bildirimindeki bir dugmeye tiklandiysa arayuzu acmadan istegi ilet.
    komut_uri = notifier.protokol_komutu(sys.argv)
    if komut_uri is not None:
        notifier.protokol_isle(komut_uri)
        return
    # Indirilmis ve kurulmayi bekleyen guncelleme var mi?
    bekleyen = guncelleme.bekleyen_guncelleme()
    # Ayni anda yalnizca bir ornek calisabilir.
    if not sistem.kilit_al():
        # Baska bir ornek (or. tepsidе) calisiyor. Guncelleme bekliyorsa ondan
        # guncellemeyi kurup yeniden baslatmasini iste; yoksa pencereyi one getir.
        if bekleyen is not None:
            sistem.guncelleme_sinyali_gonder()
        else:
            sistem.goster_sinyali_gonder()
        return
    # Uygulama yeniden acildi ve guncelleme hazir: kur ve yeni surumle basla.
    if bekleyen is not None and guncelleme.guncellemeyi_uygula():
        return
    uygulama = NotHatirlatici()
    uygulama.calistir()


if __name__ == "__main__":
    main()
