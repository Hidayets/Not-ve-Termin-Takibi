"""Aylik gorevler ozeti: bu ayin tamamlanma durumu ve tamamlanan kayitlar.

Sayfa yalnizca ilerleme cubugunu ve bu ay tamamlanmis kayitlari listeler;
bekleyen kayitlar burada gosterilmez. "Bugun Yapilacaklar" listesinden
yapildi isaretlenen kayitlar bu sayfaya duserek cubugu ilerletir.
"""
from __future__ import annotations

import calendar
import datetime

import customtkinter as ctk

import db
import reminder
from arayuz.tema import TEMA_RENKLERI, font
from arayuz.widgetlar import NotKarti


class AylikOzetKarti(ctk.CTkFrame):
    """Bu ayin tamamlanma durumunu ve tamamlanan kayitlari gosteren ozet karti.

    doldur=True iken govde tum alani kaplayacak sekilde genisler (tam sayfa
    kullanimi icin); varsayilan davranis sabit yukseklikli kompakt karttir.
    """

    def __init__(self, parent, pencere, doldur: bool = False):
        super().__init__(
            parent,
            corner_radius=8,
            fg_color=TEMA_RENKLERI["bg_kart"],
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        self.pencere = pencere
        self.uygulama = pencere.uygulama
        self.doldur = doldur

        bugun = datetime.date.today()
        self.yil = bugun.year
        self.ay = bugun.month

        self.baslik_satiri = ctk.CTkFrame(self, fg_color="transparent")
        self.baslik_satiri.pack(fill="x", padx=12, pady=(10, 4))
        self.baslik = ctk.CTkLabel(
            self.baslik_satiri,
            text="",
            font=font(14, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        )
        self.baslik.pack(side="left")
        self.durum = ctk.CTkLabel(
            self.baslik_satiri,
            text="",
            font=font(12),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        )
        self.durum.pack(side="right")

        self.cubuk = ctk.CTkProgressBar(self, height=10)
        self.cubuk.pack(fill="x", padx=12, pady=(0, 8))
        self.cubuk.set(0)

        if doldur:
            self.govde = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
            self.govde.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        else:
            self.govde = ctk.CTkScrollableFrame(self, height=140, fg_color="transparent", label_text="")
            self.govde.pack(fill="x", padx=8, pady=(0, 10))

        self.yenile()

    # ------------------------------------------------------------------ cizim
    def yenile(self) -> None:
        bugun = datetime.date.today()
        self.yil, self.ay = bugun.year, bugun.month
        self.baslik.configure(
            text=f"Aylık Görevler — {reminder.AY_ADLARI[self.ay - 1]} {self.yil}"
        )

        for cocuk in self.govde.winfo_children():
            cocuk.destroy()

        # Bu ay icinde planlanan her kayit ve o kayda ait olay zamanlari.
        kayit_olaylari: dict[int, tuple[dict, list[datetime.datetime]]] = {}
        for gun_kayitlari in self._ay_kayitlari().values():
            for kayit, olay in gun_kayitlari:
                girdi = kayit_olaylari.setdefault(kayit.get("id"), (kayit, []))
                girdi[1].append(olay)

        toplam = len(kayit_olaylari)
        yapilan = sum(
            1
            for kayit, olaylar in kayit_olaylari.values()
            if self._kayit_tamam_mi(kayit, olaylar)
        )

        if toplam:
            oran = yapilan / toplam
            self.cubuk.set(oran)
            self.cubuk.configure(
                progress_color=TEMA_RENKLERI["durum_tamamlandi"]
                if yapilan == toplam
                else TEMA_RENKLERI["durum_bekliyor"]
            )
            self.durum.configure(
                text=f"{yapilan}/{toplam} kayıt tamamlandı (%{int(round(oran * 100))})"
            )
        else:
            self.cubuk.set(0)
            self.cubuk.configure(progress_color=TEMA_RENKLERI["durum_bekliyor"])
            self.durum.configure(text="Bu ay için kayıt yok")

        # Bekleyen kayitlar bu sayfada listelenmez; yalnizca tamamlananlar gosterilir.
        self._tamamlananlari_ciz(kayit_olaylari)

    # ------------------------------------------------- tamamlanma yardimcilari
    def _kayit_tamam_mi(self, kayit: dict, olaylar: list[datetime.datetime]) -> bool:
        """Kayit bu ay icin tamamlanmis sayilir mi?"""
        if kayit.get("durum") == "tamamlandi":
            return True
        if int(kayit.get("ilerleme") or 0) == 100:
            return True
        if kayit.get("evrak_durum") == "Onaylandı":
            return True
        # Tekrarli / gun listeli kayitlarda bu ayki tum olaylarin donemi isaretli olmali.
        return bool(olaylar) and all(reminder.tamamlandi_mi(kayit, o) for o in olaylar)

    def _bu_ay_tamamlandi_mi(self, kayit: dict) -> bool:
        """Kayit bu ay icinde tamamlanmis mi? (tamamlanma zamani bu aya ait)"""
        zaman = reminder.dt_parse(kayit.get("tamamlanma_zamani"))
        if zaman is None or zaman.year != self.yil or zaman.month != self.ay:
            return False
        return (
            kayit.get("durum") == "tamamlandi"
            or kayit.get("tamamlanan_donem") is not None
            or int(kayit.get("ilerleme") or 0) == 100
            or kayit.get("evrak_durum") == "Onaylandı"
        )

    # ------------------------------------------------- ayin tum kayitlari
    def _ay_kayitlari(self) -> dict[datetime.date, list[tuple[dict, datetime.datetime]]]:
        """Bu ay icinde gerceklesen tum kayitlari gune gore gruplar."""
        ilk = datetime.date(self.yil, self.ay, 1)
        son = datetime.date(self.yil, self.ay, calendar.monthrange(self.yil, self.ay)[1])
        baslangic = datetime.datetime.combine(ilk, datetime.time.min)
        bitis = datetime.datetime.combine(son, datetime.time.max)

        gruplar: dict[datetime.date, list[tuple[dict, datetime.datetime]]] = {}
        for kayit in db.tum_notlar():
            for olay in reminder.olay_zamanlari(kayit, baslangic, bitis):
                gruplar.setdefault(olay.date(), []).append((kayit, olay))
        for kayitlar in gruplar.values():
            kayitlar.sort(key=lambda t: t[1])
        return gruplar

    # ------------------------------------------- tamamlanan kayitlar bolumu
    def _tamamlananlari_ciz(
        self, kayit_olaylari: dict[int, tuple[dict, list[datetime.datetime]]]
    ) -> None:
        """Bu ay tamamlanmis kayitlari en son tamamlanan ustte listeler.

        Kapsam: bu ay planlanmis ve tamamlanmis kayitlar ile bu ay icinde
        tamamlanmis olanlar. Eski "Tamamlananlar" sekmesi kaldirildigi icin
        bu bolum ayni islevi Aylik Gorevler sayfasi icinde surdurur.
        """
        tamamlananlar: list[dict] = [
            kayit
            for kayit, olaylar in kayit_olaylari.values()
            if self._kayit_tamam_mi(kayit, olaylar)
        ]
        bu_ay_idler = {kayit.get("id") for kayit, _ in kayit_olaylari.values()}
        for kayit in db.tum_notlar():
            if kayit.get("id") in bu_ay_idler:
                continue
            if self._bu_ay_tamamlandi_mi(kayit):
                tamamlananlar.append(kayit)

        tamamlananlar.sort(
            key=lambda x: reminder.dt_parse(x.get("tamamlanma_zamani"))
            or datetime.datetime.min,
            reverse=True,
        )

        ctk.CTkFrame(self.govde, height=1, fg_color=TEMA_RENKLERI["kenarlik"]).pack(
            fill="x", padx=4, pady=(14, 6)
        )
        ctk.CTkLabel(
            self.govde,
            text=f"🎯 Bu Ay Tamamlananlar  ({len(tamamlananlar)} kayıt)",
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        ).pack(anchor="w", padx=6, pady=(0, 4))

        if not tamamlananlar:
            ctk.CTkLabel(
                self.govde,
                text=(
                    "Bu ay tamamlanmış bir kayıt bulunmuyor. \"Bugün Yapılacaklar\" "
                    "listesinden bir işi yapıldı olarak işaretlediğinizde burada görünür."
                ),
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
                wraplength=820,
                justify="left",
            ).pack(anchor="w", padx=6, pady=(0, 6))
            return

        for kayit in tamamlananlar:
            NotKarti(self.govde, self.pencere, kayit, mod="tamamlanan").pack(
                fill="x", padx=14, pady=3
            )


class AylikGorevlerEkrani(ctk.CTkFrame):
    """Aylık görevleri gün gün işaretlemek için ayrılmış sayfa."""

    def __init__(self, parent, pencere):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere
        self.uygulama = pencere.uygulama

        bilgi = ctk.CTkFrame(
            self,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=8,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        bilgi.pack(fill="x", padx=14, pady=(10, 8))

        ctk.CTkLabel(
            bilgi,
            text="📆 Aylık Görevler",
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        ).pack(side="left", padx=(12, 10), pady=10)

        ctk.CTkLabel(
            bilgi,
            text="Bu ay içinde tamamlanan kayıtlar aşağıda listelenir; bekleyen "
            "kayıtlar burada gösterilmez. \"Bugün Yapılacaklar\" listesinden bir "
            "işi yapıldı işaretlediğinizde buraya düşer ve çubuk ilerler.",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
        ).pack(side="left", pady=10)

        self.ozet = AylikOzetKarti(self, pencere, doldur=True)
        self.ozet.pack(fill="both", expand=True, padx=14, pady=(0, 10))

    def yenile(self) -> None:
        self.ozet.yenile()
