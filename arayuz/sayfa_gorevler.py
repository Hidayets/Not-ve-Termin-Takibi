"""Gorevler Ekrani: Kart ve Tablo gorunumu, ilerleme yuzdesi, durum takibi."""
from __future__ import annotations

import datetime

import customtkinter as ctk

import db
import reminder
from arayuz.tema import TEMA_RENKLERI, font
from arayuz.widgetlar import GorevKarti, kartlari_yerlestir, liste_temizle, onay_iste, rozet


class GorevlerEkrani(ctk.CTkFrame):
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
            placeholder_text="Görev veya sorumlu ara...",
            width=240,
            height=32,
            font=font(12),
        )
        self.arama.pack(side="left", padx=4, pady=8)
        self.arama.bind("<KeyRelease>", lambda _: self.yenile())

        ctk.CTkLabel(ust, text="Durum:", font=font(11)).pack(side="left", padx=(10, 4))
        self.opt_durum = ctk.CTkOptionMenu(
            ust,
            values=["Tümü", "Bekliyor", "Devam ediyor", "Tamamlandı", "Gecikti"],
            width=130,
            height=30,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=lambda _: self.yenile(),
        )
        self.opt_durum.pack(side="left", padx=4)

        # Kart / Tablo Gorunumu Gecisi
        self.gorunum_secici = ctk.CTkSegmentedButton(
            ust,
            values=["Kart", "Tablo"],
            height=30,
            font=font(11, weight="bold"),
            command=lambda _: self.yenile(),
            selected_color=TEMA_RENKLERI["vurgu"],
        )
        self.gorunum_secici.set("Kart")
        self.gorunum_secici.pack(side="right", padx=(6, 12), pady=8)

        self.sayac = ctk.CTkLabel(
            ust,
            text="",
            font=font(12, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        )
        self.sayac.pack(side="right", padx=10)

        # Liste / Tablo Alani
        self.liste = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self.liste.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        # Kartlarin gruplar halinde cizilmesi icin nesil takibi.
        self._yukleme: dict = {}
        self.yenile()

    def yenile(self) -> None:
        liste_temizle(self.liste, self._yukleme)

        arama = self.arama.get().strip().casefold()
        secili_durum = self.opt_durum.get()
        gorunum = self.gorunum_secici.get()

        simdi = datetime.datetime.now()
        kayitlar = db.tum_notlar()
        filtrelenen = []

        for k in kayitlar:
            # Yalnizca tur='gorev' kayitlari bu sekmede gosterilir.
            if (k.get("tur") or "not") != "gorev":
                continue

            ilerleme = int(k.get("ilerleme") or 0)
            zaman = reminder.not_zamani(k)
            durum_ham = k.get("durum") or "bekliyor"

            if durum_ham == "tamamlandi" or ilerleme == 100:
                hesaplanan = "Tamamlandı"
            elif zaman and zaman < simdi and durum_ham != "tamamlandi":
                hesaplanan = "Gecikti"
            elif ilerleme > 0:
                hesaplanan = "Devam ediyor"
            else:
                hesaplanan = "Bekliyor"

            if secili_durum != "Tümü" and hesaplanan != secili_durum:
                continue

            if arama:
                metin = " ".join(
                    [k.get("baslik") or "", k.get("aciklama") or "", k.get("sorumlu") or ""]
                ).casefold()
                if arama not in metin:
                    continue

            k["_hesaplanan_durum"] = hesaplanan
            filtrelenen.append(k)

        self.sayac.configure(text=f"{len(filtrelenen)} Görev")

        if not filtrelenen:
            ctk.CTkLabel(
                self.liste,
                text="Kayıtlı görev bulunamadı.",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(pady=40)
            return

        if gorunum == "Kart":
            kartlari_yerlestir(
                self.liste,
                filtrelenen,
                lambda k: GorevKarti(self.liste, self.pencere, k),
                self._yukleme,
            )
        else:
            self._tablo_ciz(filtrelenen)

    def _tablo_ciz(self, kayitlar: list[dict]) -> None:
        """Yatay kaydirma gerektirmeyen sik tablo gorunumu."""
        # Tablo Baslik Satiri
        baslik_satiri = ctk.CTkFrame(
            self.liste,
            fg_color=TEMA_RENKLERI["bg_kart_ic"],
            corner_radius=6,
            height=34,
        )
        baslik_satiri.pack(fill="x", pady=(0, 4), padx=2)

        sutunlar = [
            ("Görev Adı", 240),
            ("Sorumlu", 130),
            ("Son Tarih", 120),
            ("Tekrar", 90),
            ("İlerleme", 130),
            ("Durum", 110),
            ("İşlemler", 140),
        ]

        for ad, genislik in sutunlar:
            ctk.CTkLabel(
                baslik_satiri,
                text=ad,
                width=genislik,
                font=font(11, weight="bold"),
                text_color=TEMA_RENKLERI["metin_ikincil"],
                anchor="w",
            ).pack(side="left", padx=4)

        # Tablo Satirlari
        for k in kayitlar:
            satir = ctk.CTkFrame(
                self.liste,
                fg_color=TEMA_RENKLERI["bg_kart"],
                corner_radius=6,
                border_width=1,
                border_color=TEMA_RENKLERI["kenarlik"],
                height=40,
            )
            satir.pack(fill="x", pady=2, padx=2)

            durum = k.get("_hesaplanan_durum", "Bekliyor")
            durum_renk = {
                "Tamamlandı": TEMA_RENKLERI["durum_tamamlandi"],
                "Gecikti": TEMA_RENKLERI["durum_geciken"],
                "Devam ediyor": TEMA_RENKLERI["durum_yaklasiyor"],
                "Bekliyor": TEMA_RENKLERI["durum_bekliyor"],
            }.get(durum, TEMA_RENKLERI["durum_bekliyor"])

            # Görev Adı
            ctk.CTkLabel(
                satir,
                text=k.get("baslik", "")[:28],
                width=240,
                font=font(12, weight="bold"),
                anchor="w",
                text_color=TEMA_RENKLERI["metin_ana"],
            ).pack(side="left", padx=4)

            # Sorumlu
            sorumlu = k.get("sorumlu") or "-"
            ctk.CTkLabel(
                satir,
                text=sorumlu[:16],
                width=130,
                font=font(11),
                anchor="w",
                text_color=TEMA_RENKLERI["metin_ikincil"],
            ).pack(side="left", padx=4)

            # Son Tarih
            zaman = reminder.not_zamani(k)
            tarih_metin = zaman.strftime("%d.%m.%Y") if zaman else "-"
            ctk.CTkLabel(
                satir,
                text=tarih_metin,
                width=120,
                font=font(11),
                anchor="w",
                text_color=TEMA_RENKLERI["metin_ikincil"],
            ).pack(side="left", padx=4)

            # Tekrar
            tekrar = reminder.tekrar_metni(k) or "Tek"
            ctk.CTkLabel(
                satir,
                text=tekrar[:12],
                width=90,
                font=font(11),
                anchor="w",
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(side="left", padx=4)

            # İlerleme Barı
            ilerleme = int(k.get("ilerleme") or 0)
            frm_bar = ctk.CTkFrame(satir, width=130, fg_color="transparent")
            frm_bar.pack(side="left", padx=4)
            bar = ctk.CTkProgressBar(frm_bar, width=80, height=8)
            bar.pack(side="left", padx=(0, 6))
            bar.set(ilerleme / 100.0)
            bar.configure(
                progress_color=TEMA_RENKLERI["durum_tamamlandi"]
                if ilerleme == 100
                else TEMA_RENKLERI["durum_bekliyor"]
            )
            ctk.CTkLabel(
                frm_bar,
                text=f"%{ilerleme}",
                font=font(10, weight="bold"),
                text_color=TEMA_RENKLERI["metin_ikincil"],
            ).pack(side="left")

            # Durum Rozeti
            frm_durum = ctk.CTkFrame(satir, width=110, fg_color="transparent")
            frm_durum.pack(side="left", padx=4)
            rozet(frm_durum, durum, durum_renk).pack(side="left")

            # İşlem Butonları
            frm_islem = ctk.CTkFrame(satir, width=140, fg_color="transparent")
            frm_islem.pack(side="left", padx=4)
            kimlik = k["id"]

            if ilerleme < 100:
                ctk.CTkButton(
                    frm_islem,
                    text="✓",
                    width=28,
                    height=24,
                    font=font(11, weight="bold"),
                    fg_color=TEMA_RENKLERI["durum_tamamlandi"],
                    command=lambda i=kimlik: self._tamamla(i),
                ).pack(side="left", padx=2)
            else:
                ctk.CTkButton(
                    frm_islem,
                    text="↩",
                    width=28,
                    height=24,
                    font=font(11),
                    fg_color=TEMA_RENKLERI["btn_notr"],
                    command=lambda i=kimlik: self._geri_al(i),
                ).pack(side="left", padx=2)

            ctk.CTkButton(
                frm_islem,
                text="Düzenle",
                width=56,
                height=24,
                font=font(10),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=lambda i=kimlik: self.pencere.duzenlemeye_al(i),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                frm_islem,
                text="✕",
                width=26,
                height=24,
                font=font(10),
                fg_color="transparent",
                text_color=TEMA_RENKLERI["durum_geciken"],
                command=lambda i=kimlik: self._sil(i),
            ).pack(side="left", padx=2)

    def _tamamla(self, kimlik: int) -> None:
        db.gorev_ilerleme_kaydet(kimlik, 100)
        self.uygulama.arayuzu_yenile()

    def _geri_al(self, kimlik: int) -> None:
        db.gorev_ilerleme_kaydet(kimlik, 0)
        self.uygulama.arayuzu_yenile()

    def _sil(self, kimlik: int) -> None:
        if onay_iste("Görevi Sil", "Görev geri dönüşüm kutusuna taşınacak. Onaylıyor musunuz?"):
            self.uygulama.cop_kutusuna_at(kimlik)
