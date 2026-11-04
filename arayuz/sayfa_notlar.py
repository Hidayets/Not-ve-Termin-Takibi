"""Notlar Ekrani: Kart tabanli liste, arama, kategori ve oncelik filtreleri."""
from __future__ import annotations

import datetime

import customtkinter as ctk

import db
import reminder
from arayuz.tema import TEMA_RENKLERI, font
from arayuz.widgetlar import NotKarti, kartlari_yerlestir, liste_temizle


class NotlarEkrani(ctk.CTkFrame):
    def __init__(self, parent, pencere):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere
        self.uygulama = pencere.uygulama

        # Ust Filtre Bari
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
            placeholder_text="Notlarda ara (başlık, açıklama, etiket)...",
            width=260,
            height=32,
            font=font(12),
        )
        self.arama.pack(side="left", padx=4, pady=8)
        self.arama.bind("<KeyRelease>", lambda _: self.yenile())

        ctk.CTkLabel(ust, text="Kategori:", font=font(11)).pack(side="left", padx=(10, 4))
        self.kategori = ctk.CTkOptionMenu(
            ust,
            values=["Tümü"] + reminder.KATEGORILER,
            width=120,
            height=30,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=lambda _: self.yenile(),
        )
        self.kategori.pack(side="left", padx=4)

        ctk.CTkLabel(ust, text="Öncelik:", font=font(11)).pack(side="left", padx=(10, 4))
        self.oncelik = ctk.CTkOptionMenu(
            ust,
            values=["Tümü"] + reminder.ONCELIKLER,
            width=110,
            height=30,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=lambda _: self.yenile(),
        )
        self.oncelik.pack(side="left", padx=4)

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
        self.kategori.set("Tümü")
        self.oncelik.set("Tümü")
        self.yenile()

    def yenile(self) -> None:
        liste_temizle(self.liste, self._yukleme)

        arama = self.arama.get().strip().casefold()
        secili_kat = self.kategori.get()
        secili_onc = self.oncelik.get()

        kayitlar = db.tum_notlar()
        filtrelenen = []

        for k in kayitlar:
            # Sadece 'not' turundekiler
            tur = k.get("tur") or "not"
            if tur != "not":
                continue
            if k.get("durum") == "tamamlandi":
                continue

            if secili_kat != "Tümü" and (k.get("kategori") or "") != secili_kat:
                continue
            if secili_onc != "Tümü" and (k.get("oncelik") or "") != secili_onc:
                continue

            if arama:
                bilesik = " ".join(
                    [k.get("baslik") or "", k.get("aciklama") or "", k.get("etiketler") or ""]
                ).casefold()
                if arama not in bilesik:
                    continue

            filtrelenen.append(k)

        self.sayac.configure(text=f"{len(filtrelenen)} Not")

        if not filtrelenen:
            ctk.CTkLabel(
                self.liste,
                text="Görüntülenecek not bulunamadı.",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(pady=40)
            return

        kartlari_yerlestir(
            self.liste,
            filtrelenen,
            lambda k: NotKarti(self.liste, self.pencere, k, mod="bekleyen"),
            self._yukleme,
        )
