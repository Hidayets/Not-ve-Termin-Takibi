"""Takvim sekmesi: ay gorunumu ve gun bazli not listesi."""
from __future__ import annotations

import calendar
import datetime

import customtkinter as ctk

import db
import reminder
from arayuz.widgetlar import NotKarti


class TakvimSekmesi(ctk.CTkFrame):
    def __init__(self, parent, pencere):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere
        self.uygulama = pencere.uygulama
        bugun = datetime.date.today()
        self.yil = bugun.year
        self.ay = bugun.month
        self.secili = bugun

        ust = ctk.CTkFrame(self, fg_color="transparent")
        ust.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkButton(ust, text="<", width=40, command=lambda: self._kaydir(-1)).pack(side="left")
        self.baslik = ctk.CTkLabel(ust, text="", font=ctk.CTkFont(size=17, weight="bold"))
        self.baslik.pack(side="left", padx=14)
        ctk.CTkButton(ust, text=">", width=40, command=lambda: self._kaydir(1)).pack(side="left")
        ctk.CTkButton(
            ust, text="Bugün", width=80, fg_color="#7f8c8d", hover_color="#5d6d7e",
            command=self._bugune_don,
        ).pack(side="left", padx=14)
        ctk.CTkLabel(
            ust,
            text="Not içeren günler vurgulanır. Bir güne tıklayarak o günün notlarını görün.",
            text_color=("#57606f", "#a4b0be"),
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=10)

        self.izgara = ctk.CTkFrame(self, fg_color="transparent")
        self.izgara.pack(fill="x", padx=10)
        for sutun in range(7):
            self.izgara.grid_columnconfigure(sutun, weight=1)

        self.gun_basligi = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        )
        self.gun_basligi.pack(fill="x", padx=12, pady=(12, 4))
        self.gun_listesi = ctk.CTkScrollableFrame(self, label_text="")
        self.gun_listesi.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ------------------------------------------------------------- gezinme
    def _kaydir(self, fark: int) -> None:
        ay = self.ay + fark
        yil = self.yil
        if ay < 1:
            ay, yil = 12, yil - 1
        elif ay > 12:
            ay, yil = 1, yil + 1
        self.ay, self.yil = ay, yil
        self.yenile()

    def _bugune_don(self) -> None:
        bugun = datetime.date.today()
        self.yil, self.ay, self.secili = bugun.year, bugun.month, bugun
        self.yenile()

    def _gun_sec(self, gun: datetime.date) -> None:
        self.secili = gun
        self.yenile()

    # ------------------------------------------------------------- yardimcilar
    def _gun_notlari(self) -> dict[datetime.date, list[tuple]]:
        """Ay icindeki her gun icin (not, olaylar) listesi."""
        ilk = datetime.date(self.yil, self.ay, 1)
        son = datetime.date(self.yil, self.ay, calendar.monthrange(self.yil, self.ay)[1])
        baslangic = datetime.datetime.combine(ilk, datetime.time.min)
        bitis = datetime.datetime.combine(son, datetime.time.max)
        sonuc: dict[datetime.date, list[tuple]] = {}
        for kayit in db.tum_notlar():
            for olay in reminder.olay_zamanlari(kayit, baslangic, bitis):
                sonuc.setdefault(olay.date(), []).append((kayit, olay))
        for deger in sonuc.values():
            deger.sort(key=lambda ikili: ikili[1])
        return sonuc

    # ------------------------------------------------------------- cizim
    def yenile(self) -> None:
        self.baslik.configure(text=f"{reminder.AY_ADLARI[self.ay - 1]} {self.yil}")
        for cocuk in self.izgara.winfo_children():
            cocuk.destroy()

        for sutun, gun_adi in enumerate(reminder.GUN_ADLARI):
            ctk.CTkLabel(
                self.izgara,
                text=gun_adi,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#57606f", "#a4b0be"),
            ).grid(row=0, column=sutun, sticky="ew", padx=2, pady=(0, 4))

        gun_notlari = self._gun_notlari()
        bugun = datetime.date.today()
        takvim = calendar.Calendar(firstweekday=0).monthdatescalendar(self.yil, self.ay)

        for satir, hafta in enumerate(takvim, start=1):
            for sutun, gun in enumerate(hafta):
                kayitlar = gun_notlari.get(gun, [])
                if kayitlar:
                    tamamlanmis = all(
                        kayit.get("durum") == "tamamlandi"
                        or kayit.get("tamamlanan_donem")
                        == reminder.periyot_anahtari(kayit, olay)
                        for kayit, olay in kayitlar
                    )
                    renk = ("#d5dbdb", "#3b4a5a") if tamamlanmis else ("#d4e6f1", "#1f3b57")
                else:
                    renk = "transparent"

                ayni_ay = gun.month == self.ay
                etiketler = []
                for kayit, _ in kayitlar[:2]:
                    baslik = (kayit.get("baslik") or "")[:16]
                    etiketler.append(f"• {baslik}")
                if len(kayitlar) > 2:
                    etiketler.append(f"• +{len(kayitlar) - 2} not")
                metin = f"{gun.day}"
                if etiketler:
                    metin += "\n" + "\n".join(etiketler)

                kenar = 2 if gun == self.secili else 0
                cerceve = ctk.CTkFrame(
                    self.izgara,
                    border_width=kenar,
                    border_color="#2980b9",
                    fg_color=renk,
                    corner_radius=8,
                )
                cerceve.grid(row=satir, column=sutun, sticky="nsew", padx=2, pady=2)
                cerceve.grid_propagate(False)
                cerceve.configure(width=130, height=86)
                duzen = {
                    "text": metin,
                    "anchor": "nw",
                    "font": ctk.CTkFont(size=11, weight="bold" if gun == bugun else "normal"),
                    "fg_color": "transparent",
                    "hover_color": ("#eaf2f8", "#2c4258"),
                    "text_color": ("#2c3e50", "#ecf0f1") if ayni_ay else ("#95a5a6", "#6b7c8c"),
                    "width": 126,
                    "height": 82,
                    "corner_radius": 8,
                    "command": lambda g=gun: self._gun_sec(g),
                }
                ctk.CTkButton(cerceve, **duzen).pack(fill="both", expand=True)

        self._gun_listesini_ciz(gun_notlari)

    def _gun_listesini_ciz(self, gun_notlari: dict) -> None:
        for cocuk in self.gun_listesi.winfo_children():
            cocuk.destroy()
        self.gun_basligi.configure(
            text=(
                f"{self.secili.strftime('%d.%m.%Y')} - "
                f"{reminder.GUN_ADLARI[self.secili.weekday()]} günü planlanan notlar"
            )
        )
        kayitlar = gun_notlari.get(self.secili, [])
        if not kayitlar:
            ctk.CTkLabel(
                self.gun_listesi,
                text="Bu gün için planlanmış not yok.",
                text_color=("#57606f", "#a4b0be"),
            ).pack(pady=16)
            return
        for kayit, olay in kayitlar:
            tamamlandi = kayit.get("durum") == "tamamlandi" or kayit.get(
                "tamamlanan_donem"
            ) == reminder.periyot_anahtari(kayit, olay)
            NotKarti(
                self.gun_listesi,
                self.pencere,
                kayit,
                mod="tamamlanan" if tamamlandi else "bekleyen",
            ).pack(fill="x", pady=5, padx=4)
