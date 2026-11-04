"""Evrak & Termin Ekrani: Okul ve resmi surecler, amir onayi, teslim takibi."""
from __future__ import annotations

import datetime

import customtkinter as ctk

import db
import reminder
import rapor
from arayuz.tema import EVRAK_DURUMLARI, TEMA_RENKLERI, font
from arayuz.widgetlar import TerminKarti, kartlari_yerlestir, liste_temizle


class TerminlerEkrani(ctk.CTkFrame):
    def __init__(self, parent, pencere):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere
        self.uygulama = pencere.uygulama

        # Ust Filtre ve Kontrol Bari
        ust = ctk.CTkFrame(
            self,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=8,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        ust.pack(fill="x", padx=14, pady=(10, 8))

        ctk.CTkLabel(ust, text="🔍", font=font(13)).pack(side="left", padx=(10, 4))
        self.arama = ctk.CTkEntry(
            ust,
            placeholder_text="Evrak adı, kurum veya amir ara...",
            width=260,
            height=32,
            font=font(12),
        )
        self.arama.pack(side="left", padx=4, pady=8)
        self.arama.bind("<KeyRelease>", lambda _: self.yenile())

        ctk.CTkLabel(ust, text="Durum:", font=font(11)).pack(side="left", padx=(10, 4))
        self.opt_durum = ctk.CTkOptionMenu(
            ust,
            values=["Tümü"] + EVRAK_DURUMLARI,
            width=130,
            height=30,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=lambda _: self.yenile(),
        )
        self.opt_durum.pack(side="left", padx=4)

        ctk.CTkButton(
            ust,
            text="Temizle",
            width=70,
            height=30,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=self._filtre_temizle,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            ust,
            text="🖨️ Rapor Al",
            width=100,
            height=30,
            font=font(11, weight="bold"),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=rapor.rapor_olustur_ve_ac,
        ).pack(side="right", padx=(4, 12), pady=8)

        self.sayac = ctk.CTkLabel(
            ust,
            text="",
            font=font(12, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        )
        self.sayac.pack(side="right", padx=14)

        # Liste Alani
        self.liste = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self.liste.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        # Kartlarin gruplar halinde cizilmesi icin nesil takibi.
        self._yukleme: dict = {}
        self.yenile()

    def _filtre_temizle(self) -> None:
        self.arama.delete(0, "end")
        self.opt_durum.set("Tümü")
        self.yenile()

    def yenile(self) -> None:
        liste_temizle(self.liste, self._yukleme)

        arama = self.arama.get().strip().casefold()
        secili_durum = self.opt_durum.get()

        simdi = datetime.datetime.now()
        kayitlar = db.tum_notlar()
        filtrelenen = []

        for k in kayitlar:
            # Yalnizca tur='termin' kayitlari bu sekmede gosterilir.
            if (k.get("tur") or "not") != "termin":
                continue

            zaman = reminder.not_zamani(k)
            durum = k.get("evrak_durum") or "Bekliyor"

            # Gecikme kontrolu
            if zaman and zaman < simdi and durum not in ("Onaylandı", "Tamamlandı"):
                durum_gosterim = "Gecikti"
            else:
                durum_gosterim = durum

            if secili_durum != "Tümü":
                if secili_durum == "Gecikti" and durum_gosterim != "Gecikti":
                    continue
                elif secili_durum != "Gecikti" and durum != secili_durum:
                    continue

            if arama:
                metin = " ".join(
                    [
                        k.get("baslik") or "",
                        k.get("kurum_amir") or "",
                        k.get("aciklama") or "",
                        k.get("etiketler") or "",
                    ]
                ).casefold()
                if arama not in metin:
                    continue

            filtrelenen.append(k)

        self.sayac.configure(text=f"{len(filtrelenen)} Evrak/Termin")

        if not filtrelenen:
            ctk.CTkLabel(
                self.liste,
                text="Takip edilen evrak veya termin bulunamadı.",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(pady=40)
            return

        kartlari_yerlestir(
            self.liste,
            filtrelenen,
            lambda k: TerminKarti(self.liste, self.pencere, k),
            self._yukleme,
        )
