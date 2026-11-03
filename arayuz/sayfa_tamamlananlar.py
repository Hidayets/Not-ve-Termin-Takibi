"""Tamamlananlar Ekrani: Tamamlanmis notlar, gorevler ve terminler."""
from __future__ import annotations

import datetime

import customtkinter as ctk

import db
import reminder
from arayuz.tema import TEMA_RENKLERI, font
from arayuz.widgetlar import NotKarti


class TamamlananlarEkrani(ctk.CTkFrame):
    def __init__(self, parent, pencere):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere
        self.uygulama = pencere.uygulama

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
            placeholder_text="Tamamlananlar içinde ara...",
            width=260,
            height=32,
            font=font(12),
        )
        self.arama.pack(side="left", padx=4, pady=8)
        self.arama.bind("<KeyRelease>", lambda _: self.yenile())

        self.sayac = ctk.CTkLabel(
            ust,
            text="",
            font=font(12, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        )
        self.sayac.pack(side="right", padx=14)

        self.liste = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self.liste.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self.yenile()

    def yenile(self) -> None:
        for w in self.liste.winfo_children():
            w.destroy()

        arama = self.arama.get().strip().casefold()
        kayitlar = db.tum_notlar()
        tamamlananlar = []

        for k in kayitlar:
            tamam = (
                k.get("durum") == "tamamlandi"
                or k.get("tamamlanan_donem") is not None
                or int(k.get("ilerleme") or 0) == 100
                or k.get("evrak_durum") == "Onaylandı"
            )
            if not tamam:
                continue

            if arama:
                metin = " ".join(
                    [k.get("baslik") or "", k.get("aciklama") or "", k.get("etiketler") or ""]
                ).casefold()
                if arama not in metin:
                    continue

            tamamlananlar.append(k)

        # En son tamamlanan ustte
        tamamlananlar.sort(
            key=lambda x: reminder.dt_parse(x.get("tamamlanma_zamani"))
            or datetime.datetime.min,
            reverse=True,
        )

        self.sayac.configure(text=f"{len(tamamlananlar)} Tamamlanan Kayıt")

        if not tamamlananlar:
            ctk.CTkLabel(
                self.liste,
                text="Henüz tamamlanmış bir kayıt bulunmuyor.",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(pady=40)
            return

        for k in tamamlananlar:
            NotKarti(self.liste, self.pencere, k, mod="tamamlanan").pack(
                fill="x", pady=4, padx=2
            )
