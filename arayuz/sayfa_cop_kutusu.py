"""Geri Donusum Kutusu: Silinen kayitlar, geri yukleme ve kalici temizleme."""
from __future__ import annotations

import customtkinter as ctk

import db
from arayuz.tema import TEMA_RENKLERI, font
from arayuz.widgetlar import NotKarti, onay_iste


class CopKutusuEkrani(ctk.CTkFrame):
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

        ctk.CTkLabel(
            ust,
            text="🗑️ Geri Dönüşüm Kutusu",
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        ).pack(side="left", padx=(12, 10), pady=10)

        ctk.CTkButton(
            ust,
            text="Çöp Kutusunu Boşalt",
            width=160,
            height=32,
            font=font(11, weight="bold"),
            fg_color=TEMA_RENKLERI["durum_geciken"],
            hover_color=("#991B1B", "#7F1D1D"),
            command=self._cop_bosalt,
        ).pack(side="right", padx=(4, 14), pady=8)

        self.sayac = ctk.CTkLabel(
            ust,
            text="",
            font=font(12, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        )
        self.sayac.pack(side="right", padx=10)

        self.liste = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self.liste.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self.yenile()

    def _cop_bosalt(self) -> None:
        if onay_iste(
            "Çöpü Boşalt",
            "Geri dönüşüm kutusundaki TÜM kayıtlar kalıcı olarak silinecek.\n"
            "Bu işlem geri alınamaz! Onaylıyor musunuz?",
        ):
            sayi = db.cop_bosalt()
            self.uygulama.yenile()
            self.yenile()

    def yenile(self) -> None:
        for w in self.liste.winfo_children():
            w.destroy()

        cop = db.cop_kutusu()
        self.sayac.configure(text=f"{len(cop)} Silinmiş Kayıt")

        if not cop:
            ctk.CTkLabel(
                self.liste,
                text="Geri dönüşüm kutusu boş.",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(pady=40)
            return

        for k in cop:
            NotKarti(self.liste, self.pencere, k, mod="cop").pack(
                fill="x", pady=4, padx=2
            )
