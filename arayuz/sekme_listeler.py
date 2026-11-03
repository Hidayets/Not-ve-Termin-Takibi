"""Liste sekmeleri: Bekleyen, Bugün, Geciken, Tamamlanan, Geri Dönüşüm."""
from __future__ import annotations

import datetime

import customtkinter as ctk

import db
import reminder
from arayuz.aylik_ozet import AylikOzetKarti
from arayuz.widgetlar import NotKarti

SEKME_BILGILERI = {
    "bekleyen": "Henüz yapılmamış, bugün veya gelecekte uyarılacak notlar",
    "bugun": "Bugün uyarılacak veya bugün son günü olan notlar",
    "geciken": "Tarihi geçmiş ve 'Yapıldı' işaretlenmemiş notlar",
    "tamamlanan": "'Yapıldı' işaretlenen notlar (geri alabilirsiniz)",
    "cop": "Silinen notlar - geri yükleyebilir veya kalıcı silebilirsiniz",
}


class ListeSekmesi(ctk.CTkFrame):
    def __init__(self, parent, pencere, mod: str):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere
        self.uygulama = pencere.uygulama
        self.mod = mod

        self.ozet = None
        if mod == "bugun":
            self.ozet = AylikOzetKarti(self, pencere)
            self.ozet.pack(fill="x", padx=8, pady=(8, 0))

        ust = ctk.CTkFrame(self, fg_color="transparent")
        ust.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            ust, text=SEKME_BILGILERI.get(mod, ""), text_color=("#57606f", "#a4b0be")
        ).pack(side="left", padx=(2, 12))

        self.arama = ctk.CTkEntry(ust, placeholder_text="Ara: başlık, açıklama, etiket", width=240)
        self.arama.pack(side="left", padx=4)
        self.arama.bind("<Return>", lambda _: self.yenile())
        ctk.CTkButton(ust, text="Ara", width=60, command=self.yenile).pack(side="left", padx=4)

        self.sayac = ctk.CTkLabel(ust, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.sayac.pack(side="right", padx=6)

        filtre = ctk.CTkFrame(self, fg_color="transparent")
        filtre.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(filtre, text="Kategori:").pack(side="left", padx=(2, 4))
        self.kategori = ctk.CTkOptionMenu(
            filtre,
            values=["Tümü"] + reminder.KATEGORILER,
            width=130,
            command=lambda _: self.yenile(),
        )
        self.kategori.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(filtre, text="Öncelik:").pack(side="left", padx=(0, 4))
        self.oncelik = ctk.CTkOptionMenu(
            filtre,
            values=["Tümü"] + reminder.ONCELIKLER,
            width=120,
            command=lambda _: self.yenile(),
        )
        self.oncelik.pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            filtre,
            text="Filtreleri Temizle",
            width=120,
            fg_color="#7f8c8d",
            hover_color="#5d6d7e",
            command=self._filtreleri_temizle,
        ).pack(side="left", padx=4)
        ctk.CTkButton(filtre, text="Yenile", width=80, command=self.yenile).pack(side="left", padx=4)

        self.liste = ctk.CTkScrollableFrame(self, label_text="")
        self.liste.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    def _filtreleri_temizle(self) -> None:
        self.arama.delete(0, "end")
        self.kategori.set("Tümü")
        self.oncelik.set("Tümü")
        self.yenile()

    # ------------------------------------------------------------- veri secimi
    def _filtre_uygun(self, kayit: dict, arama: str) -> bool:
        if self.kategori.get() != "Tümü" and (kayit.get("kategori") or "") != self.kategori.get():
            return False
        if self.oncelik.get() != "Tümü" and (kayit.get("oncelik") or "") != self.oncelik.get():
            return False
        if arama:
            metin = " ".join(
                [
                    kayit.get("baslik") or "",
                    kayit.get("aciklama") or "",
                    kayit.get("etiketler") or "",
                ]
            ).casefold()
            if arama not in metin:
                return False
        return True

    def kayitlari_sec(self) -> list[dict]:
        simdi = datetime.datetime.now()
        arama = self.arama.get().strip().casefold()

        if self.mod == "cop":
            return [k for k in db.cop_kutusu() if self._filtre_uygun(k, arama)]

        kayitlar = db.tum_notlar()
        secilen: list[dict] = []
        for kayit in kayitlar:
            if not self._filtre_uygun(kayit, arama):
                continue
            tamamlandi = kayit.get("durum") == "tamamlandi"
            if self.mod == "tamamlanan":
                if tamamlandi or kayit.get("tamamlanan_donem"):
                    secilen.append(kayit)
                continue
            if tamamlandi:
                continue
            if self.mod == "bekleyen":
                if reminder.bugunun_olaylari(kayit, simdi) or reminder.sonraki_olay(kayit, simdi):
                    secilen.append(kayit)
            elif self.mod == "bugun":
                if reminder.bugunun_olaylari(kayit, simdi):
                    secilen.append(kayit)
            elif self.mod == "geciken":
                if reminder.geciken_olay(kayit, simdi):
                    secilen.append(kayit)

        return self._sirala(secilen, simdi)

    def _sirala(self, kayitlar: list[dict], simdi: datetime.datetime) -> list[dict]:
        if self.mod == "tamamlanan":
            return sorted(
                kayitlar,
                key=lambda k: reminder.dt_parse(k.get("tamamlanma_zamani"))
                or datetime.datetime.min,
                reverse=True,
            )
        if self.mod == "geciken":
            return sorted(
                kayitlar,
                key=lambda k: (reminder.geciken_olay(k, simdi) or (datetime.datetime.max,))[0],
            )
        if self.mod == "bugun":
            return sorted(
                kayitlar,
                key=lambda k: (reminder.bugunun_olaylari(k, simdi) or [datetime.datetime.max])[0],
            )
        return sorted(
            kayitlar,
            key=lambda k: reminder.sonraki_olay(k, simdi) or datetime.datetime.max,
        )

    # ------------------------------------------------------------- cizim
    def yenile(self) -> None:
        for cocuk in self.liste.winfo_children():
            cocuk.destroy()
        if self.ozet is not None:
            self.ozet.yenile()
        kayitlar = self.kayitlari_sec()
        self.sayac.configure(text=f"{len(kayitlar)} kayıt")
        if not kayitlar:
            ctk.CTkLabel(
                self.liste,
                text="Bu listede gösterilecek not yok.",
                text_color=("#57606f", "#a4b0be"),
            ).pack(pady=20)
            return
        for kayit in kayitlar:
            NotKarti(self.liste, self.pencere, kayit, mod=self.mod).pack(
                fill="x", pady=5, padx=4
            )
