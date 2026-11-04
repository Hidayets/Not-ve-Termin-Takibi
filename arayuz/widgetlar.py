"""Tekrar kullanilan modern arayuz bilesenleri: kartlar, rozetler, tarih secici ve dialoglar."""
from __future__ import annotations

import datetime
import os
import tkinter as tk
import tkinter.messagebox as mesaj_kutusu

import customtkinter as ctk

import db
import reminder
from arayuz.tema import FONT_FAMILY, ONCELIK_RENKLERI, TEMA_RENKLERI, font


def rozet(parent, metin: str, bg_renk: str | tuple, text_color: str = "#FFFFFF") -> ctk.CTkLabel:
    """Modern kapsul/rozet bileseni."""
    return ctk.CTkLabel(
        parent,
        text=f" {metin} ",
        fg_color=bg_renk,
        corner_radius=6,
        text_color=text_color,
        font=font(11, weight="bold"),
        height=22,
    )


def onay_iste(baslik: str, mesaj: str) -> bool:
    """Standart Turkce onay penceresi."""
    return mesaj_kutusu.askyesno(baslik, mesaj)


def liste_temizle(liste, durum: dict) -> None:
    """Liste icerigini bosaltir ve bekleyen kart yerlestirmelerini iptal eder."""
    durum["nesil"] = durum.get("nesil", 0) + 1
    for w in liste.winfo_children():
        w.destroy()


def kartlari_yerlestir(container, kayitlar, uretici, durum: dict, adim: int = 4, **pack_ayarlari) -> None:
    """Kartlari artan boyutlu gruplar halinde yerlestirir; arayuz donmaz.

    Kartlar tek seferde degil, kucuk gruplar halinde `after` ile olusturulur.
    Boylece cok kayitli listelerde sekme gecisleri ve yenilemeler aninda
    hissedilir (sayfa yenileme hissi olusmaz). `durum` sozlugu nesil takibi
    icin kullanilir; `liste_temizle` ile nesil artirildiginda onceki bekleyen
    isler guvenle iptal edilir.
    """
    nesil = durum.get("nesil", 0)
    toplam = len(kayitlar)
    if toplam == 0:
        return
    if not pack_ayarlari:
        pack_ayarlari = {"fill": "x", "pady": 4, "padx": 2}

    index = 0
    boyut = adim

    def grup() -> None:
        nonlocal index, boyut
        try:
            if durum.get("nesil") != nesil or not container.winfo_exists():
                return
            son = min(index + boyut, toplam)
            for i in range(index, son):
                uretici(kayitlar[i]).pack(**pack_ayarlari)
            index = son
            if index < toplam:
                boyut = min(boyut * 2, 24)
                container.after(1, grup)
        except Exception:
            return

    grup()


class AcilirButon(ctk.CTkButton):
    """Tiklayinca yerel bir tk.Menu acan hafif secim butonu.

    CTkOptionMenu her olusturuldugunda ek bir dropdown bileseni urettigi icin
    yuzlerce kart iceren listelerde belirgin yavaslamaya yol acar. Bu bilesen
    yalnizca tek bir buton uretir; secenek menusu ilk tiklamada (tembel olarak)
    olusturulur ve boylece liste sayfalari cok daha hizli cizilir.
    """

    def __init__(self, parent, secenekler, komut=None, metin=None, **kwargs):
        if metin is None:
            metin = str(secenekler[0]) if secenekler else ""
        super().__init__(parent, text=str(metin), command=self._ac, **kwargs)
        self._secenekler = [str(s) for s in secenekler]
        self._komut = komut
        self._menu = None

    def _ac(self) -> None:
        if self._menu is None:
            self._menu = tk.Menu(self, tearoff=0)
            for s in self._secenekler:
                self._menu.add_command(label=s, command=lambda sec=s: self._sec(sec))
        try:
            self._menu.tk_popup(
                self.winfo_rootx(), self.winfo_rooty() + self.winfo_height()
            )
        finally:
            self._menu.grab_release()

    def _sec(self, secim: str) -> None:
        self.configure(text=secim)
        if self._komut is not None:
            self._komut(secim)

    def set(self, deger) -> None:
        """Secili degeri buton uzerinde gosterir (CTkOptionMenu uyumlulugu)."""
        self.configure(text=str(deger))

    def get(self) -> str:
        return str(self.cget("text"))


class SayiSecici(ctk.CTkFrame):
    """Tekerlek benzeri sayi secici (saat/dakika icin).

    Alana dogrudan yazilabilir; yanindaki artir/azalt oklari veya fare
    tekerlegi ile de deger degistirilebilir. Deger her zaman
    0..ust_sinir-1 araliginda tutulur ve iki haneli olarak gosterilir.
    """

    def __init__(self, parent, ust_sinir: int, genislik: int = 66):
        super().__init__(parent, fg_color="transparent")
        self.ust_sinir = ust_sinir

        self.giris = ctk.CTkEntry(
            self,
            width=genislik - 22,
            height=32,
            corner_radius=16,
            font=font(12),
            justify="center",
        )
        self.giris.pack(side="left")

        oklar = ctk.CTkFrame(self, fg_color="transparent")
        oklar.pack(side="left", padx=(2, 0))
        self._ok(oklar, "▲", 1).pack()
        self._ok(oklar, "▼", -1).pack(pady=(2, 0))

        self.giris.bind("<Return>", self._normallestir)
        self.giris.bind("<FocusOut>", self._normallestir)
        self.giris.bind("<MouseWheel>", self._tekerlek)
        self.set(0)

    def _ok(self, parent, metin: str, fark: int) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=metin,
            width=20,
            height=15,
            corner_radius=5,
            font=font(8, weight="bold"),
            fg_color=TEMA_RENKLERI["btn_notr"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=lambda: self._degistir(fark),
        )

    def _tekerlek(self, olay) -> str:
        self._degistir(1 if olay.delta > 0 else -1)
        return "break"

    def _degistir(self, fark: int) -> None:
        self._yaz((self._sayi_oku() + fark) % self.ust_sinir)

    def _sayi_oku(self) -> int:
        try:
            return int(str(self.giris.get()).strip())
        except (TypeError, ValueError):
            return 0

    def _normallestir(self, _olay=None) -> str:
        self._yaz(max(0, min(self.ust_sinir - 1, self._sayi_oku())))
        return "break"

    def _yaz(self, deger: int) -> None:
        deger = max(0, min(self.ust_sinir - 1, int(deger)))
        self.giris.delete(0, "end")
        self.giris.insert(0, f"{deger:02d}")

    def set(self, deger) -> None:
        """Degeri ayarlar (int veya 'HH' metni); aralik disinda sarar."""
        try:
            sayi = int(str(deger).strip())
        except (TypeError, ValueError):
            sayi = 0
        self._yaz(sayi % self.ust_sinir)

    def get(self) -> str:
        return self.giris.get()


class TarihSaatSecici(ctk.CTkFrame):
    """Gun / ay / yil / saat / dakika secimi + hizli secenekler."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        simdi = datetime.datetime.now()
        self.gun = ctk.CTkComboBox(
            self,
            values=[f"{i:02d}" for i in range(1, 32)],
            width=68,
            state="readonly",
            font=font(12),
        )
        self.ay = ctk.CTkComboBox(
            self,
            values=[f"{i:02d} - {reminder.AY_ADLARI[i - 1]}" for i in range(1, 13)],
            width=140,
            state="readonly",
            font=font(12),
        )
        self.yil = ctk.CTkComboBox(
            self,
            values=[str(y) for y in range(simdi.year - 1, simdi.year + 7)],
            width=86,
            state="readonly",
            font=font(12),
        )
        self.saat = SayiSecici(self, 24)
        self.dakika = SayiSecici(self, 60)

        parcalar = [
            ("Gün", self.gun),
            ("Ay", self.ay),
            ("Yıl", self.yil),
            ("Saat", self.saat),
            ("Dakika", self.dakika),
        ]
        for sutun, (baslik, bilesen) in enumerate(parcalar):
            ctk.CTkLabel(
                self,
                text=baslik,
                font=font(11),
                text_color=TEMA_RENKLERI["metin_ikincil"],
            ).grid(row=0, column=sutun, padx=(0, 8), sticky="w")
            bilesen.grid(row=1, column=sutun, padx=(0, 8), sticky="w")

        hizli = ctk.CTkFrame(self, fg_color="transparent")
        hizli.grid(row=1, column=5, padx=(6, 0), sticky="w")
        for metin, komut in (
            ("Şimdi", lambda: self.ayarla(simdi)),
            ("1 saat", lambda: self.ayarla(simdi + datetime.timedelta(hours=1))),
            (
                "Yarın 09:00",
                lambda: self.ayarla(
                    datetime.datetime.combine(
                        simdi.date() + datetime.timedelta(days=1), datetime.time(9, 0)
                    )
                ),
            ),
            ("1 hafta", lambda: self.ayarla(simdi + datetime.timedelta(days=7))),
        ):
            ctk.CTkButton(
                hizli,
                text=metin,
                width=80,
                height=28,
                command=komut,
                font=font(11),
                fg_color=TEMA_RENKLERI["btn_notr"],
                hover_color=TEMA_RENKLERI["btn_notr_hover"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
            ).pack(side="left", padx=2)

        self.ayarla(simdi)

    def ayarla(self, zaman: datetime.datetime) -> None:
        mevcut_yillar = list(self.yil.cget("values"))
        if str(zaman.year) not in mevcut_yillar:
            mevcut_yillar = sorted(set(mevcut_yillar + [str(zaman.year)]))
            self.yil.configure(values=mevcut_yillar)
        self.gun.set(f"{zaman.day:02d}")
        self.ay.set(f"{zaman.month:02d} - {reminder.AY_ADLARI[zaman.month - 1]}")
        self.yil.set(str(zaman.year))
        self.saat.set(f"{zaman.hour:02d}")
        self.dakika.set(f"{zaman.minute:02d}")

    def deger(self) -> datetime.datetime | None:
        try:
            return datetime.datetime(
                int(self.yil.get()),
                int(self.ay.get().split(" - ")[0]),
                int(self.gun.get()),
                int(self.saat.get()),
                int(self.dakika.get()),
            )
        except (TypeError, ValueError):
            return None


class NotKarti(ctk.CTkFrame):
    """Tek bir not kaydini gosteren modern kart."""

    def __init__(self, parent, pencere, kayit: dict, mod: str = "bekleyen"):
        super().__init__(
            parent,
            corner_radius=8,
            fg_color=TEMA_RENKLERI["bg_kart"],
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        self.pencere = pencere
        self.uygulama = pencere.uygulama
        self.kayit = kayit
        self.mod = mod
        self.simdi = datetime.datetime.now()

        self.grid_columnconfigure(1, weight=1)

        oncelik_deger = kayit.get("oncelik", "Normal")
        renk = ONCELIK_RENKLERI.get(oncelik_deger, ("#2563EB", "#3B82F6"))

        # Ince vurgu cizgisi
        serit = ctk.CTkFrame(self, width=5, corner_radius=3, fg_color=renk)
        serit.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(6, 10), pady=8)

        # Ust bolum: Baslik ve rozetler
        ust = ctk.CTkFrame(self, fg_color="transparent")
        ust.grid(row=0, column=1, sticky="ew", pady=(8, 2))

        ctk.CTkLabel(
            ust,
            text=kayit.get("baslik", ""),
            font=font(14, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        ).pack(side="left")

        kat = kayit.get("kategori", "Genel")
        rozet(ust, kat, ("#E2E8F0", "#334155"), text_color=("#0F172A", "#F8FAFC")).pack(
            side="left", padx=5
        )
        rozet(ust, oncelik_deger, renk).pack(side="left", padx=3)

        tekrar = reminder.tekrar_metni(kayit)
        if tekrar and tekrar != "Tek seferlik":
            rozet(ust, tekrar, ("#0D9488", "#14B8A6")).pack(side="left", padx=3)

        if reminder.tekrarli(kayit) and kayit.get("tamamlanan_donem"):
            rozet(ust, "Bu dönem yapıldı", ("#64748B", "#475569")).pack(side="left", padx=3)
        if kayit.get("silindi"):
            rozet(ust, "Geri dönüşümde", ("#9333EA", "#A855F7")).pack(side="left", padx=3)

        # Aciklama
        aciklama = (kayit.get("aciklama") or "").strip()
        if aciklama:
            ctk.CTkLabel(
                self,
                text=aciklama,
                justify="left",
                anchor="w",
                wraplength=600,
                font=font(12),
                text_color=TEMA_RENKLERI["metin_ikincil"],
            ).grid(row=1, column=1, sticky="w", pady=(2, 4))

        # Alt detaylar
        detaylar = []
        zaman = reminder.not_zamani(kayit)
        if zaman:
            detaylar.append(f"📅 {reminder.zaman_metni(zaman)}")
        if kayit.get("hatirlatma_once_dk"):
            detaylar.append(f"🔔 {reminder.hatirlatma_metni(kayit.get('hatirlatma_once_dk'))}")
        if kayit.get("etiketler"):
            detaylar.append(f"🏷️ {kayit['etiketler']}")

        ctk.CTkLabel(
            self,
            text="   •   ".join(detaylar),
            justify="left",
            anchor="w",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
        ).grid(row=2, column=1, sticky="w", pady=(0, 8))

        # Butonlar
        self._butonlar()

    def _butonlar(self) -> None:
        kutu = ctk.CTkFrame(self, fg_color="transparent")
        kutu.grid(row=0, column=2, rowspan=3, sticky="e", padx=(6, 12))
        kimlik = self.kayit["id"]

        if self.mod == "cop":
            ctk.CTkButton(
                kutu,
                text="Geri Yükle",
                width=90,
                height=30,
                font=font(11, weight="bold"),
                fg_color=TEMA_RENKLERI["durum_bekliyor"],
                command=lambda: self.geri_yukle(kimlik),
            ).pack(side="left", padx=3)
            ctk.CTkButton(
                kutu,
                text="Kalıcı Sil",
                width=90,
                height=30,
                font=font(11, weight="bold"),
                fg_color=TEMA_RENKLERI["durum_geciken"],
                command=lambda: self.kalici_sil(kimlik),
            ).pack(side="left", padx=3)
            return

        if self.mod == "tamamlanan":
            ctk.CTkButton(
                kutu,
                text="Geri Al",
                width=80,
                height=30,
                font=font(11),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                hover_color=TEMA_RENKLERI["btn_notr_hover"],
                command=lambda: self.geri_al(kimlik),
            ).pack(side="left", padx=3)
        else:
            ctk.CTkButton(
                kutu,
                text="✓ Yapıldı",
                width=86,
                height=30,
                font=font(11, weight="bold"),
                fg_color=TEMA_RENKLERI["durum_tamamlandi"],
                command=lambda: self.yapildi(kimlik),
            ).pack(side="left", padx=3)

            AcilirButon(
                kutu,
                secenekler=list(reminder.ERTELEME_SECENEKLERI.keys()),
                komut=lambda s: self.ertele(kimlik, s),
                metin="⏰ Ertele",
                width=90,
                height=30,
                font=font(11),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                hover_color=TEMA_RENKLERI["btn_notr_hover"],
            ).pack(side="left", padx=3)

        ctk.CTkButton(
            kutu,
            text="Düzenle",
            width=76,
            height=30,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=lambda: self.pencere.duzenlemeye_al(kimlik),
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            kutu,
            text="Sil",
            width=54,
            height=30,
            font=font(11),
            fg_color="transparent",
            text_color=TEMA_RENKLERI["durum_geciken"],
            hover_color=("#FEE2E2", "#450A0A"),
            command=lambda: self.sil(kimlik),
        ).pack(side="left", padx=2)

    def yapildi(self, kimlik: int) -> None:
        self.uygulama.yapildi_isaretle(kimlik)

    def geri_al(self, kimlik: int) -> None:
        self.uygulama.tamamlamayi_geri_al(kimlik)

    def ertele(self, kimlik: int, secim: str) -> None:
        dakika = reminder.ERTELEME_SECENEKLERI.get(secim, 15)
        self.uygulama.ertele_uyari(kimlik, dakika)

    def sil(self, kimlik: int) -> None:
        if onay_iste("Notu Sil", "Not geri dönüşüm kutusuna taşınacak. Onaylıyor musunuz?"):
            self.uygulama.cop_kutusuna_at(kimlik)

    def geri_yukle(self, kimlik: int) -> None:
        self.uygulama.cop_kutusundan_geri_al(kimlik)

    def kalici_sil(self, kimlik: int) -> None:
        if onay_iste(
            "Kalıcı Sil", "Bu not kalıcı olarak silinecektir. Bu işlem geri alınamaz!"
        ):
            self.uygulama.kalici_sil(kimlik)


class GorevKarti(ctk.CTkFrame):
    """Gorevler icin sorumlu, ilerleme yuzdesi ve durum iceren modern kart."""

    def __init__(self, parent, pencere, kayit: dict):
        super().__init__(
            parent,
            corner_radius=8,
            fg_color=TEMA_RENKLERI["bg_kart"],
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        self.pencere = pencere
        self.uygulama = pencere.uygulama
        self.kayit = kayit
        self.simdi = datetime.datetime.now()

        self.grid_columnconfigure(1, weight=1)

        ilerleme = int(kayit.get("ilerleme") or 0)
        durum = kayit.get("durum") or "bekliyor"
        zaman = reminder.not_zamani(kayit)

        # Durum renklendirmesi
        if durum == "tamamlandi" or ilerleme == 100:
            durum_metni = "Tamamlandı"
            renk = TEMA_RENKLERI["durum_tamamlandi"]
        elif zaman and zaman < self.simdi and durum != "tamamlandi":
            durum_metni = "Gecikti"
            renk = TEMA_RENKLERI["durum_geciken"]
        elif ilerleme > 0:
            durum_metni = "Devam ediyor"
            renk = TEMA_RENKLERI["durum_yaklasiyor"]
        else:
            durum_metni = "Bekliyor"
            renk = TEMA_RENKLERI["durum_bekliyor"]

        # Sol renk seridi
        serit = ctk.CTkFrame(self, width=5, corner_radius=3, fg_color=renk)
        serit.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(6, 10), pady=8)

        # Ust baslik
        ust = ctk.CTkFrame(self, fg_color="transparent")
        ust.grid(row=0, column=1, sticky="ew", pady=(8, 2))

        ctk.CTkLabel(
            ust,
            text=kayit.get("baslik", ""),
            font=font(14, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        ).pack(side="left")

        rozet(ust, durum_metni, renk).pack(side="left", padx=6)

        sorumlu = (kayit.get("sorumlu") or "").strip()
        if sorumlu:
            rozet(
                ust, f"👤 {sorumlu}", ("#E0E7FF", "#1E1B4B"), text_color=("#3730A3", "#818CF8")
            ).pack(side="left", padx=4)

        tekrar = reminder.tekrar_metni(kayit)
        if tekrar and tekrar != "Tek seferlik":
            rozet(ust, tekrar, ("#0D9488", "#14B8A6")).pack(side="left", padx=3)

        # Aciklama
        aciklama = (kayit.get("aciklama") or "").strip()
        if aciklama:
            ctk.CTkLabel(
                self,
                text=aciklama,
                justify="left",
                anchor="w",
                wraplength=600,
                font=font(12),
                text_color=TEMA_RENKLERI["metin_ikincil"],
            ).grid(row=1, column=1, sticky="w", pady=(2, 4))

        # Ilerleme ve Tarih
        alt = ctk.CTkFrame(self, fg_color="transparent")
        alt.grid(row=2, column=1, sticky="ew", pady=(2, 8))

        ctk.CTkLabel(
            alt,
            text=f"Son Tarih: {reminder.zaman_metni(zaman) if zaman else '-'}",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
        ).pack(side="left", padx=(0, 14))

        ctk.CTkLabel(
            alt,
            text=f"İlerleme: %{ilerleme}",
            font=font(11, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        ).pack(side="left", padx=(0, 6))

        bar = ctk.CTkProgressBar(alt, width=140, height=8)
        bar.pack(side="left", padx=(0, 10))
        bar.set(ilerleme / 100.0)
        bar.configure(
            progress_color=TEMA_RENKLERI["durum_tamamlandi"]
            if ilerleme == 100
            else TEMA_RENKLERI["durum_bekliyor"]
        )

        # Sag islemler
        kutu = ctk.CTkFrame(self, fg_color="transparent")
        kutu.grid(row=0, column=2, rowspan=3, sticky="e", padx=(6, 12))
        kimlik = kayit["id"]

        # Hızlı ilerleme butonları (+25%, 100%)
        if ilerleme < 100:
            ctk.CTkButton(
                kutu,
                text="+%25",
                width=50,
                height=28,
                font=font(11),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=lambda: self._ilerleme_arttir(kimlik, ilerleme + 25),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                kutu,
                text="✓ Tamamla",
                width=80,
                height=28,
                font=font(11, weight="bold"),
                fg_color=TEMA_RENKLERI["durum_tamamlandi"],
                command=lambda: self._ilerleme_arttir(kimlik, 100),
            ).pack(side="left", padx=2)
        else:
            ctk.CTkButton(
                kutu,
                text="Geri Al",
                width=76,
                height=28,
                font=font(11),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=lambda: self._ilerleme_arttir(kimlik, 0),
            ).pack(side="left", padx=2)

        ctk.CTkButton(
            kutu,
            text="Düzenle",
            width=70,
            height=28,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=lambda: self.pencere.duzenlemeye_al(kimlik),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            kutu,
            text="Sil",
            width=48,
            height=28,
            font=font(11),
            fg_color="transparent",
            text_color=TEMA_RENKLERI["durum_geciken"],
            command=lambda: self._sil(kimlik),
        ).pack(side="left", padx=2)

    def _ilerleme_arttir(self, kimlik: int, yeni: int) -> None:
        db.gorev_ilerleme_kaydet(kimlik, min(100, yeni))
        self.uygulama.arayuzu_yenile()

    def _sil(self, kimlik: int) -> None:
        if onay_iste("Görevi Sil", "Görev geri dönüşüm kutusuna taşınacak. Onaylıyor musunuz?"):
            self.uygulama.cop_kutusuna_at(kimlik)


class TerminKarti(ctk.CTkFrame):
    """Evrak ve termin takibi icin kurumsal kart."""

    def __init__(self, parent, pencere, kayit: dict):
        zaman = reminder.not_zamani(kayit)
        simdi = datetime.datetime.now()
        gecikti = bool(zaman and zaman < simdi and kayit.get("durum") != "tamamlandi")
        yaklasiyor = bool(
            zaman
            and not gecikti
            and (zaman - simdi) <= datetime.timedelta(days=db.ayar_sayi("termin_esik_gun", 3))
            and kayit.get("durum") != "tamamlandi"
        )

        kenar_renk = (
            TEMA_RENKLERI["durum_geciken"]
            if gecikti
            else (
                TEMA_RENKLERI["durum_yaklasiyor"]
                if yaklasiyor
                else TEMA_RENKLERI["kenarlik"]
            )
        )
        kenar_kalinlik = 2 if (gecikti or yaklasiyor) else 1

        super().__init__(
            parent,
            corner_radius=8,
            fg_color=TEMA_RENKLERI["bg_kart"],
            border_width=kenar_kalinlik,
            border_color=kenar_renk,
        )
        self.pencere = pencere
        self.uygulama = pencere.uygulama
        self.kayit = kayit

        self.grid_columnconfigure(1, weight=1)

        # Durum belirleme
        durum = kayit.get("evrak_durum") or "Bekliyor"
        durum_renk = {
            "Bekliyor": TEMA_RENKLERI["durum_bekliyor"],
            "Hazırlandı": ("#0284C7", "#38BDF8"),
            "Gönderildi": ("#4F46E5", "#818CF8"),
            "Onaylandı": TEMA_RENKLERI["durum_tamamlandi"],
            "Reddedildi": TEMA_RENKLERI["durum_geciken"],
            "Gecikti": TEMA_RENKLERI["durum_geciken"],
        }.get(durum, TEMA_RENKLERI["durum_bekliyor"])

        serit = ctk.CTkFrame(self, width=5, corner_radius=3, fg_color=durum_renk)
        serit.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(6, 10), pady=8)

        # Ust Baslik
        ust = ctk.CTkFrame(self, fg_color="transparent")
        ust.grid(row=0, column=1, sticky="ew", pady=(8, 2))

        ctk.CTkLabel(
            ust,
            text=kayit.get("baslik", ""),
            font=font(14, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        ).pack(side="left")

        rozet(ust, durum, durum_renk).pack(side="left", padx=6)

        kurum = (kayit.get("kurum_amir") or "").strip()
        if kurum:
            rozet(
                ust, f"🏛️ {kurum}", ("#FEF3C7", "#78350F"), text_color=("#92400E", "#FDE68A")
            ).pack(side="left", padx=4)

        if gecikti:
            rozet(ust, "GECİKTİ", TEMA_RENKLERI["durum_geciken"]).pack(side="left", padx=4)
        elif yaklasiyor:
            rozet(ust, "YAKLAŞIYOR", TEMA_RENKLERI["durum_yaklasiyor"]).pack(side="left", padx=4)

        # Aciklama
        aciklama = (kayit.get("aciklama") or "").strip()
        if aciklama:
            ctk.CTkLabel(
                self,
                text=aciklama,
                justify="left",
                anchor="w",
                wraplength=600,
                font=font(12),
                text_color=TEMA_RENKLERI["metin_ikincil"],
            ).grid(row=1, column=1, sticky="w", pady=(2, 4))

        # Detaylar
        alt = ctk.CTkFrame(self, fg_color="transparent")
        alt.grid(row=2, column=1, sticky="ew", pady=(2, 8))

        if zaman:
            ctk.CTkLabel(
                alt,
                text=f"📅 Teslim: {zaman.strftime('%d.%m.%Y %H:%M')}",
                font=font(11, weight="bold"),
                text_color=TEMA_RENKLERI["metin_ana"] if not gecikti else TEMA_RENKLERI["durum_geciken"],
            ).pack(side="left", padx=(0, 12))

        # Amire Bilgi Verildi Onay Kutusu
        bilgi_var = bool(kayit.get("amire_bilgi_verildi"))
        bilgi_cb = ctk.CTkCheckBox(
            alt,
            text="Amire bilgi verildi",
            font=font(11),
            command=lambda: self._bilgi_degisti(kayit["id"], bilgi_cb.get() == 1),
        )
        bilgi_cb.pack(side="left", padx=(0, 6))
        if bilgi_var:
            bilgi_cb.select()
            zamani = (kayit.get("amire_bilgi_zamani") or "")[:16]
            if zamani:
                ctk.CTkLabel(
                    alt,
                    text=f"({zamani})",
                    font=font(10),
                    text_color=TEMA_RENKLERI["durum_bilgi_verildi"],
                ).pack(side="left", padx=(0, 10))

        # Dosya eki varsa
        dosya = (kayit.get("dosya_eki") or "").strip()
        if dosya:
            ctk.CTkButton(
                alt,
                text=f"📎 {os.path.basename(dosya)[:18]}",
                height=22,
                font=font(10),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=lambda: self._dosya_ac(dosya),
            ).pack(side="left", padx=4)

        # Sag Butonlar
        kutu = ctk.CTkFrame(self, fg_color="transparent")
        kutu.grid(row=0, column=2, rowspan=3, sticky="e", padx=(6, 12))
        kimlik = kayit["id"]

        durum_menu = AcilirButon(
            kutu,
            secenekler=["Bekliyor", "Hazırlandı", "Gönderildi", "Onaylandı", "Reddedildi"],
            komut=lambda s: self._durum_degistir(kimlik, s),
            metin=durum,
            width=110,
            height=28,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
        )
        durum_menu.pack(side="left", padx=3)

        ctk.CTkButton(
            kutu,
            text="Düzenle",
            width=70,
            height=28,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=lambda: self.pencere.duzenlemeye_al(kimlik),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            kutu,
            text="Sil",
            width=48,
            height=28,
            font=font(11),
            fg_color="transparent",
            text_color=TEMA_RENKLERI["durum_geciken"],
            command=lambda: self._sil(kimlik),
        ).pack(side="left", padx=2)

    def _bilgi_degisti(self, kimlik: int, durum: bool) -> None:
        db.amire_bilgi_kaydet(kimlik, durum)
        self.uygulama.arayuzu_yenile()

    def _durum_degistir(self, kimlik: int, durum: str) -> None:
        db.evrak_durum_kaydet(kimlik, durum)
        if durum == "Onaylandı":
            self.uygulama.yapildi_isaretle(kimlik)
        else:
            self.uygulama.arayuzu_yenile()

    def _dosya_ac(self, dosya: str) -> None:
        try:
            if os.path.exists(dosya):
                os.startfile(dosya)
            else:
                mesaj_kutusu.showerror("Hata", f"Dosya bulunamadı:\n{dosya}")
        except Exception as e:
            mesaj_kutusu.showerror("Hata", f"Dosya açılamadı:\n{e}")

    def _sil(self, kimlik: int) -> None:
        if onay_iste("Evrak/Termini Sil", "Kayıt geri dönüşüm kutusuna taşınacak. Onaylıyor musunuz?"):
            self.uygulama.cop_kutusuna_at(kimlik)
