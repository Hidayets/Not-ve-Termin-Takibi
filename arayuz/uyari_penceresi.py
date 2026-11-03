"""Zamaninda cikan modern hatirlatma penceresi: Yapildi / Ertele secenekleri."""
from __future__ import annotations

import datetime

import customtkinter as ctk

import reminder
from arayuz.tema import ONCELIK_RENKLERI, TEMA_RENKLERI, font


class UyariPenceresi(ctk.CTkToplevel):
    def __init__(self, pencere, kayit: dict, olay: datetime.datetime, sira: int = 0):
        super().__init__(pencere)
        self.pencere = pencere
        self.uygulama = pencere.uygulama
        self.kayit = kayit
        self.olay = olay

        oncelik = kayit.get("oncelik", "Normal")
        renk = ONCELIK_RENKLERI.get(oncelik, TEMA_RENKLERI["durum_bekliyor"])

        self.title(f"Hatırlatma - {kayit.get('baslik', '')[:40]}")
        self.resizable(False, False)
        genislik, yukseklik = 480, 310
        ekran_g = self.winfo_screenwidth()
        ekran_y = self.winfo_screenheight()
        x = ekran_g - genislik - 24
        y = ekran_y - yukseklik - 70 - (sira * (yukseklik + 12))
        if y < 20:
            y = 20
        self.geometry(f"{genislik}x{yukseklik}+{x}+{y}")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.kapat)
        self.configure(fg_color=TEMA_RENKLERI["bg_ana"])

        ust = ctk.CTkFrame(self, fg_color=renk, corner_radius=0)
        ust.pack(fill="x")

        ctk.CTkLabel(
            ust,
            text="🔔 HATIRLATMA",
            font=font(11, weight="bold"),
            text_color="#FFFFFF",
        ).pack(anchor="w", padx=16, pady=(10, 0))

        ctk.CTkLabel(
            ust,
            text=kayit.get("baslik", ""),
            font=font(16, weight="bold"),
            text_color="#FFFFFF",
            wraplength=440,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        govde = ctk.CTkFrame(self, fg_color="transparent")
        govde.pack(fill="both", expand=True, padx=16, pady=10)

        aciklama = (kayit.get("aciklama") or "").strip()
        if aciklama:
            ctk.CTkLabel(
                govde,
                text=aciklama,
                wraplength=440,
                justify="left",
                anchor="w",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_ana"],
            ).pack(anchor="w")

        detaylar = [
            f"📅 Planlanan: {reminder.zaman_metni(self.olay)}",
            f"🏷️ Kategori: {kayit.get('kategori', 'Genel')}",
            f"⚡ Öncelik: {oncelik}",
        ]
        tekrar = reminder.tekrar_metni(kayit)
        if tekrar and tekrar != "Tek seferlik":
            detaylar.append(f"🔁 Tekrar: {tekrar}")

        ctk.CTkLabel(
            govde,
            text="\n".join(detaylar),
            justify="left",
            anchor="w",
            text_color=TEMA_RENKLERI["metin_soluk"],
            font=font(11),
        ).pack(anchor="w", pady=(8, 0))

        alt = ctk.CTkFrame(self, fg_color="transparent")
        alt.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkButton(
            alt,
            text="✓ Yapıldı",
            width=100,
            height=34,
            font=font(12, weight="bold"),
            fg_color=TEMA_RENKLERI["durum_tamamlandi"],
            command=self.yapildi,
        ).pack(side="left")

        self.erteleme = ctk.CTkOptionMenu(
            alt,
            values=list(reminder.ERTELEME_SECENEKLERI.keys()),
            width=110,
            height=34,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
        )
        self.erteleme.set("15 dakika")
        self.erteleme.pack(side="left", padx=8)

        ctk.CTkButton(
            alt,
            text="Ertele",
            width=80,
            height=34,
            font=font(11),
            fg_color=TEMA_RENKLERI["durum_yaklasiyor"],
            command=self.ertele,
        ).pack(side="left")

        ctk.CTkButton(
            alt,
            text="Kapat",
            width=70,
            height=34,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=self.kapat,
        ).pack(side="right")

        self.after(150, self._one_cikar)

    def _one_cikar(self) -> None:
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def yapildi(self) -> None:
        self.uygulama.yapildi_isaretle(self.kayit["id"], olay=self.olay)
        self.kapat()

    def ertele(self) -> None:
        dakika = reminder.ERTELEME_SECENEKLERI.get(self.erteleme.get(), 15)
        self.uygulama.ertele_uyari(self.kayit["id"], dakika, kaynak="erteleme")
        self.kapat()

    def kapat(self) -> None:
        self.pencere.uyari_kapandi(self)
        try:
            self.destroy()
        except Exception:
            pass
