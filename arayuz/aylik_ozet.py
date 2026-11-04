"""Aylik gorevlerin gun bazli takibi.

Bu ayin gun bazli aylik gorevlerini ilerleme cubugu ile ozetler; her gun
tiklanabilir bir cip olarak gosterilir ve tek tek isaretlenir.
"""
from __future__ import annotations

import calendar
import datetime

import customtkinter as ctk

import db
import reminder
from arayuz.tema import ONCELIK_RENKLERI, TEMA_RENKLERI, font
from arayuz.widgetlar import rozet


class AylikOzetKarti(ctk.CTkFrame):
    """Bu ayin gun bazli aylik gorevlerini gosteren ozet karti.

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
    def _anahtar(self, gun: int) -> str:
        return f"{self.yil:04d}-{self.ay:02d}-{gun:02d}"

    def yenile(self) -> None:
        bugun = datetime.date.today()
        self.yil, self.ay = bugun.year, bugun.month
        self.baslik.configure(
            text=f"Aylık Görevler — {reminder.AY_ADLARI[self.ay - 1]} {self.yil}"
        )

        for cocuk in self.govde.winfo_children():
            cocuk.destroy()

        satirlar = []
        toplam = 0
        yapilan = 0
        for kayit in db.tum_notlar():
            if not reminder.aylik_gorev_mi(kayit):
                continue
            gunler = reminder.aylik_gorev_gunleri(kayit, self.yil, self.ay)
            if not gunler:
                continue
            durumlar = [
                (gun, reminder.aylik_gun_tamamlandi_mi(kayit, self._anahtar(gun)))
                for gun in gunler
            ]
            toplam += len(durumlar)
            yapilan += sum(1 for _, tamam in durumlar if tamam)
            satirlar.append((kayit, durumlar))

        if toplam:
            oran = yapilan / toplam
            self.cubuk.set(oran)
            self.cubuk.configure(
                progress_color=TEMA_RENKLERI["durum_tamamlandi"]
                if yapilan == toplam
                else TEMA_RENKLERI["durum_bekliyor"]
            )
            self.durum.configure(
                text=f"{yapilan}/{toplam} gün tamamlandı (%{int(round(oran * 100))})"
            )
        else:
            self.cubuk.set(0)
            self.cubuk.configure(progress_color=TEMA_RENKLERI["durum_bekliyor"])
            self.durum.configure(text="Bu ay için aylık görev yok")

        if not satirlar:
            ctk.CTkLabel(
                self.govde,
                text=(
                    "Bu ay için tanımlı aylık görev yok. \"+ Yeni Ekle\" ile bir görev "
                    "oluşturup Tekrar olarak \"Aylık\" ve kural olarak \"Gün listesi\" seçin."
                ),
                text_color=TEMA_RENKLERI["metin_soluk"],
                wraplength=820,
                justify="left",
                font=font(12),
            ).pack(anchor="w", padx=6, pady=6)
        else:
            for kayit, durumlar in satirlar:
                self._satir_ciz(kayit, durumlar)

        # Tam sayfa kullaniminda ayin tum kayitlari (Not / Gorev / Termin) listelenir.
        if self.doldur:
            self._ay_kayitlarini_ciz()

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

    def _ay_kayitlarini_ciz(self) -> None:
        gruplar = self._ay_kayitlari()

        ctk.CTkFrame(self.govde, height=1, fg_color=TEMA_RENKLERI["kenarlik"]).pack(
            fill="x", padx=4, pady=(12, 6)
        )
        ctk.CTkLabel(
            self.govde,
            text=f"📋 Bu Ayın Tüm Kayıtları — Not • Görev • Evrak Termin  ({len(gruplar)} gün)",
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        ).pack(anchor="w", padx=6, pady=(0, 4))

        if not gruplar:
            ctk.CTkLabel(
                self.govde,
                text="Bu ay içinde planlanmış kayıt bulunmuyor.",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(anchor="w", padx=6, pady=(0, 6))
            return

        for gun in sorted(gruplar):
            self._gun_basligi_ciz(gun, len(gruplar[gun]))
            for kayit, olay in gruplar[gun]:
                self._kayit_satiri_ciz(kayit, olay)

    def _gun_basligi_ciz(self, gun: datetime.date, adet: int) -> None:
        satir = ctk.CTkFrame(self.govde, fg_color="transparent")
        satir.pack(fill="x", padx=6, pady=(8, 2))
        ctk.CTkLabel(
            satir,
            text=f"{gun.day:02d} {reminder.AY_ADLARI[gun.month - 1]} — "
            f"{reminder.GUN_ADLARI[gun.weekday()]}",
            font=font(12, weight="bold"),
            text_color=TEMA_RENKLERI["vurgu"],
        ).pack(side="left")
        ctk.CTkLabel(
            satir,
            text=f"  ({adet} kayıt)",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
        ).pack(side="left")

    def _kayit_satiri_ciz(self, kayit: dict, olay: datetime.datetime) -> None:
        tur = kayit.get("tur") or "not"
        isaret = {"gorev": "✅", "termin": "⏳"}.get(tur, "📝")

        satir = ctk.CTkFrame(
            self.govde, fg_color=TEMA_RENKLERI["bg_kart_ic"], corner_radius=6
        )
        satir.pack(fill="x", padx=14, pady=1)

        ic = ctk.CTkFrame(satir, fg_color="transparent")
        ic.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(
            ic,
            text=olay.strftime("%H:%M"),
            width=44,
            font=font(11, weight="bold"),
            text_color=TEMA_RENKLERI["metin_soluk"],
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            ic,
            text=f"{isaret} {kayit.get('baslik') or '(başlıksız)'}",
            font=font(12),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        ).pack(side="left")

        durum_metni, durum_renk = self._kayit_durumu(kayit)
        if durum_metni:
            rozet(ic, durum_metni, durum_renk).pack(side="right", padx=(6, 0))

    def _kayit_durumu(self, kayit: dict) -> tuple[str, tuple]:
        """Kaydin turune gore kisa durum metni ve rozet rengi."""
        tur = kayit.get("tur") or "not"
        if tur == "gorev":
            ilerleme = int(kayit.get("ilerleme") or 0)
            if ilerleme >= 100 or kayit.get("durum") == "tamamlandi":
                return "Tamamlandı", TEMA_RENKLERI["durum_tamamlandi"]
            zaman = reminder.not_zamani(kayit)
            if zaman and zaman < datetime.datetime.now():
                return f"Gecikti · %{ilerleme}", TEMA_RENKLERI["durum_geciken"]
            return f"Devam · %{ilerleme}", TEMA_RENKLERI["durum_yaklasiyor"]
        if tur == "termin":
            durum = kayit.get("evrak_durum") or "Bekliyor"
            renk = {
                "Onaylandı": TEMA_RENKLERI["durum_tamamlandi"],
                "Reddedildi": TEMA_RENKLERI["durum_geciken"],
                "Gönderildi": ("#4F46E5", "#818CF8"),
                "Hazırlandı": ("#0284C7", "#38BDF8"),
            }.get(durum, TEMA_RENKLERI["durum_bekliyor"])
            return durum, renk
        oncelik = kayit.get("oncelik") or "Normal"
        return kayit.get("kategori") or "Genel", ONCELIK_RENKLERI.get(
            oncelik, TEMA_RENKLERI["durum_bekliyor"]
        )

    def _satir_ciz(self, kayit: dict, durumlar: list[tuple[int, bool]]) -> None:
        satir = ctk.CTkFrame(
            self.govde,
            fg_color=TEMA_RENKLERI["bg_kart_ic"],
            corner_radius=8,
        )
        satir.pack(fill="x", padx=4, pady=3)

        ust = ctk.CTkFrame(satir, fg_color="transparent")
        ust.pack(fill="x", padx=10, pady=(6, 2))
        renk = ONCELIK_RENKLERI.get(
            kayit.get("oncelik"), TEMA_RENKLERI["durum_bekliyor"]
        )
        ctk.CTkLabel(
            ust,
            text=kayit.get("baslik", ""),
            font=font(13, weight="bold"),
            text_color=renk,
        ).pack(side="left")
        ctk.CTkLabel(
            ust,
            text=f"  {reminder.tekrar_metni(kayit)}",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
        ).pack(side="left")

        cip_satiri = ctk.CTkFrame(satir, fg_color="transparent")
        cip_satiri.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(
            cip_satiri,
            text="Günler:",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
        ).pack(side="left", padx=(0, 6))
        for gun, tamam in durumlar:
            ctk.CTkButton(
                cip_satiri,
                text=str(gun),
                width=44,
                height=26,
                corner_radius=13,
                font=font(11, weight="bold"),
                fg_color=TEMA_RENKLERI["durum_tamamlandi"]
                if tamam
                else TEMA_RENKLERI["btn_notr"],
                hover_color=("#15803D", "#059669")
                if tamam
                else TEMA_RENKLERI["btn_notr_hover"],
                text_color="#FFFFFF" if tamam else TEMA_RENKLERI["btn_notr_metin"],
                command=lambda k=kayit["id"], g=gun, t=tamam: self._degistir(k, g, not t),
            ).pack(side="left", padx=3)

    def _degistir(self, not_id: int, gun: int, yapildi: bool) -> None:
        self.uygulama.aylik_gun_degistir(not_id, self._anahtar(gun), yapildi)


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
            text="Aylık yinelenen görevleri gün gün işaretleyin; ayrıca bu ay içindeki "
            "tüm Not, Görev ve Evrak Termin kayıtları gün gün listelenir.",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
        ).pack(side="left", pady=10)

        self.ozet = AylikOzetKarti(self, pencere, doldur=True)
        self.ozet.pack(fill="both", expand=True, padx=14, pady=(0, 10))

    def yenile(self) -> None:
        self.ozet.yenile()
