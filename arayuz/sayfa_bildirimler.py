"""Bildirimler Ekrani: Bildirim gecmisi, beklemedeki uyarilar ve erteleme/yapildi islemleri."""
from __future__ import annotations

import datetime

import customtkinter as ctk

import db
import notifier
import reminder
from arayuz.tema import TEMA_RENKLERI, font
from arayuz.widgetlar import AcilirButon, kartlari_yerlestir, liste_temizle, rozet


class BildirimlerEkrani(ctk.CTkFrame):
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
            placeholder_text="Bildirim veya işlem ara...",
            width=240,
            height=32,
            font=font(12),
        )
        self.arama.pack(side="left", padx=4, pady=8)
        self.arama.bind("<KeyRelease>", lambda _: self.yenile())

        ctk.CTkLabel(ust, text="Tür:", font=font(11)).pack(side="left", padx=(10, 4))
        self.opt_tur = ctk.CTkOptionMenu(
            ust,
            values=["Tümü", "Not", "Görev", "Termin"],
            width=100,
            height=30,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=lambda _: self.yenile(),
        )
        self.opt_tur.pack(side="left", padx=4)

        ctk.CTkButton(
            ust,
            text="Test Bildirimi Gönder",
            width=140,
            height=30,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=notifier.test_bildirimi,
        ).pack(side="right", padx=(4, 12), pady=8)

        self.sayac = ctk.CTkLabel(
            ust,
            text="",
            font=font(12, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        )
        self.sayac.pack(side="right", padx=10)

        # Liste
        self.liste = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self.liste.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        # Satirlarin gruplar halinde cizilmesi icin nesil takibi.
        self._yukleme: dict = {}
        self.yenile()

    def yenile(self) -> None:
        liste_temizle(self.liste, self._yukleme)

        arama = self.arama.get().strip().casefold()
        secili_tur = self.opt_tur.get()

        gecmis = db.uyari_gecmisi(limit=200)
        tum_notlar_map = {k["id"]: k for k in db.tum_notlar(cop_dahil=True)}

        filtrelenen = []
        for g in gecmis:
            not_id = g.get("not_id")
            not_kaydi = tum_notlar_map.get(not_id) if not_id else None

            tur = not_kaydi.get("tur") if not_kaydi else "not"
            tur_metin = {"not": "Not", "gorev": "Görev", "termin": "Termin"}.get(
                tur, "Not"
            )

            if secili_tur != "Tümü" and tur_metin != secili_tur:
                continue

            if arama:
                metin = " ".join(
                    [
                        g.get("baslik") or "",
                        g.get("islem") or "",
                        g.get("aciklama") or "",
                        g.get("uyari_zamani") or "",
                    ]
                ).casefold()
                if arama not in metin:
                    continue

            filtrelenen.append((g, not_kaydi, tur_metin))

        self.sayac.configure(text=f"{len(filtrelenen)} Bildirim")

        if not filtrelenen:
            ctk.CTkLabel(
                self.liste,
                text="Henüz kaydedilmiş bildirim veya uyarı geçmişi yok.",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(pady=40)
            return

        kartlari_yerlestir(
            self.liste,
            filtrelenen,
            lambda kayit: self._satir_ciz(*kayit),
            self._yukleme,
            fill="x",
            pady=3,
            padx=2,
        )

    def _satir_ciz(self, g: dict, not_kaydi: dict | None, tur_metin: str) -> ctk.CTkFrame:
        kart = ctk.CTkFrame(
            self.liste,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=8,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        kart.grid_columnconfigure(1, weight=1)

        islem = (g.get("islem") or "").lower()
        islem_renk = (
            TEMA_RENKLERI["durum_tamamlandi"]
            if "yapıldı" in islem
            else (
                TEMA_RENKLERI["durum_yaklasiyor"]
                if "ertelendi" in islem
                else TEMA_RENKLERI["durum_bekliyor"]
            )
        )

        serit = ctk.CTkFrame(kart, width=4, corner_radius=2, fg_color=islem_renk)
        serit.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(6, 8), pady=6)

        ust = ctk.CTkFrame(kart, fg_color="transparent")
        ust.grid(row=0, column=1, sticky="ew", pady=(6, 2))

        ctk.CTkLabel(
            ust,
            text=g.get("baslik", ""),
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        ).pack(side="left")

        rozet(ust, tur_metin, TEMA_RENKLERI["btn_notr"], text_color=TEMA_RENKLERI["metin_ana"]).pack(
            side="left", padx=4
        )
        rozet(ust, g.get("islem", ""), islem_renk).pack(side="left", padx=4)

        zaman_str = g.get("uyari_zamani") or ""
        ctk.CTkLabel(
            ust,
            text=f"🕒 {zaman_str}",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
        ).pack(side="right", padx=10)

        aciklama = (g.get("aciklama") or "").strip()
        if aciklama:
            ctk.CTkLabel(
                kart,
                text=aciklama,
                justify="left",
                anchor="w",
                font=font(11),
                text_color=TEMA_RENKLERI["metin_ikincil"],
            ).grid(row=1, column=1, sticky="w", pady=(0, 6))

        # Eger not hala aktif ve yapilmamissa eylemler gosterilebilir
        if not_kaydi and not_kaydi.get("silindi") == 0:
            tamam = not_kaydi.get("durum") == "tamamlandi"
            if not tamam:
                kutu = ctk.CTkFrame(kart, fg_color="transparent")
                kutu.grid(row=0, column=2, rowspan=2, sticky="e", padx=(4, 10))
                nid = not_kaydi["id"]

                ctk.CTkButton(
                    kutu,
                    text="✓ Yapıldı",
                    width=74,
                    height=26,
                    font=font(11, weight="bold"),
                    fg_color=TEMA_RENKLERI["durum_tamamlandi"],
                    command=lambda: self.uygulama.yapildi_isaretle(nid),
                ).pack(side="left", padx=2)

                AcilirButon(
                    kutu,
                    secenekler=["15 dakika", "1 saat", "1 gün"],
                    komut=lambda s: self.uygulama.ertele_uyari(
                        nid, reminder.ERTELEME_SECENEKLERI.get(s, 15)
                    ),
                    metin="⏰ Ertele",
                    width=90,
                    height=26,
                    font=font(11),
                    fg_color=TEMA_RENKLERI["btn_notr"],
                    text_color=TEMA_RENKLERI["btn_notr_metin"],
                    hover_color=TEMA_RENKLERI["btn_notr_hover"],
                ).pack(side="left", padx=2)

        return kart
