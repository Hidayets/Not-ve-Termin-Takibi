"""Sistem tepsisi (pystray) menusu."""
from __future__ import annotations

import pystray
from PIL import Image

import db
import notifier


class Tepsi:
    def __init__(self, pencere_goster, gunluk_goster, ayarlari_goster, cikis):
        self.pencere_goster = pencere_goster
        self.gunluk_goster = gunluk_goster
        self.ayarlari_goster = ayarlari_goster
        self.cikis = cikis
        self.simge: pystray.Icon | None = None

    def _resim(self) -> Image.Image:
        yol = notifier.ikon_olustur()
        try:
            return Image.open(yol)
        except Exception:
            return Image.new("RGBA", (64, 64), (41, 128, 185, 255))

    def baslat(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Not Ekle", self._not_ekle, default=True),
            pystray.MenuItem("Bugünün Notları", self._bugun),
            pystray.MenuItem("Ayarlar", self._ayarlar),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Tamamen Çık", self._cikis),
        )
        self.simge = pystray.Icon(db.UYGULAMA_ADI, self._resim(), db.UYGULAMA_ADI, menu)
        self.simge.run_detached()

    def durdur(self) -> None:
        if self.simge is not None:
            try:
                self.simge.stop()
            except Exception:
                pass
            self.simge = None

    # pystray geri cagrilari kendi thread'inde calisir
    def _not_ekle(self, ikon=None, oge=None) -> None:
        self.pencere_goster("Yeni Not")

    def _bugun(self, ikon=None, oge=None) -> None:
        self.gunluk_goster()

    def _ayarlar(self, ikon=None, oge=None) -> None:
        self.ayarlari_goster()

    def _cikis(self, ikon=None, oge=None) -> None:
        self.cikis()
