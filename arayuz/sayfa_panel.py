"""Panel (Dashboard) ekrani: 4 KPI ozet karti ve 2 sutunlu operasyon gorunumu."""
from __future__ import annotations

import datetime

import customtkinter as ctk

import db
import reminder
import rapor
from arayuz.tema import TEMA_RENKLERI, font
from arayuz.widgetlar import GorevKarti, NotKarti, TerminKarti, rozet


class OzetKarti(ctk.CTkFrame):
    """Buyuk sayi, baslik ve ince renkli vurgu cizgisi iceren KPI karti.

    `komut` verilirse kartin tamami (ve tum alt bilesenleri) tiklanabilir olur;
    uzerine gelindiginde kenarlik vurgulanir ve imlec el isaretine doner.
    """

    def __init__(self, parent, baslik: str, renk: str | tuple, komut=None):
        super().__init__(
            parent,
            corner_radius=8,
            fg_color=TEMA_RENKLERI["bg_kart"],
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
            height=86,
        )
        self.pack_propagate(False)
        self._komut = komut

        # Ust ince vurgu seridi
        serit = ctk.CTkFrame(self, height=4, corner_radius=2, fg_color=renk)
        serit.pack(fill="x", side="top")

        ic = ctk.CTkFrame(self, fg_color="transparent")
        ic.pack(fill="both", expand=True, padx=14, pady=8)

        self.lbl_sayi = ctk.CTkLabel(
            ic,
            text="0",
            font=font(26, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        )
        self.lbl_sayi.pack(side="left")

        sag = ctk.CTkFrame(ic, fg_color="transparent")
        sag.pack(side="left", padx=12)

        self.lbl_baslik = ctk.CTkLabel(
            sag,
            text=baslik,
            font=font(12, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ikincil"],
            anchor="w",
        )
        self.lbl_baslik.pack(anchor="w")

        if komut is not None:
            self._tiklanabilir_yap(self)
            ctk.CTkLabel(
                sag,
                text="Detay ›",
                font=font(10),
                text_color=TEMA_RENKLERI["metin_soluk"],
                anchor="w",
            ).pack(anchor="w", pady=(1, 0))

    # ----------------------------------------------------- tiklama / hover
    def _tiklanabilir_yap(self, bilesen) -> None:
        """Kartin kendisi ve tum alt bilesenlerine tiklama ve hover baglar."""
        for hedef in (bilesen, getattr(bilesen, "_canvas", None)):
            if hedef is None:
                continue
            try:
                hedef.bind("<Button-1>", self._tiklandi)
                hedef.bind("<Enter>", self._hover_gir)
                hedef.bind("<Leave>", self._hover_cik)
                hedef.configure(cursor="hand2")
            except Exception:
                pass
        for cocuk in bilesen.winfo_children():
            self._tiklanabilir_yap(cocuk)

    def _tiklandi(self, _olay=None) -> None:
        if self._komut is not None:
            self._komut()

    def _hover_gir(self, _olay=None) -> None:
        self.configure(border_color=TEMA_RENKLERI["vurgu"], border_width=2)

    def _hover_cik(self, _olay=None) -> None:
        self.after_idle(self._hover_dogrula)

    def _hover_dogrula(self) -> None:
        """Imlec karttan gercekten ciktysa cerceveyi normale dondurur."""
        try:
            altinda = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        except Exception:
            altinda = None
        yol = str(self)
        if altinda is not None and (str(altinda) == yol or str(altinda).startswith(yol + ".")):
            return
        self.configure(border_color=TEMA_RENKLERI["kenarlik"], border_width=1)

    def guncelle(self, sayi: int) -> None:
        self.lbl_sayi.configure(text=str(sayi))


class PanelEkrani(ctk.CTkFrame):
    """Ana karsilama ve gosterge paneli."""

    def __init__(self, parent, pencere):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere
        self.uygulama = pencere.uygulama
        self._kategoriler: dict[str, tuple[str, list[dict]]] = {}
        # Acik KPI detay pencereleri: her biri {"pencere": ..., "tazele": ...}
        self._detaylar: list[dict] = []

        # Ust Buton Bari (Rapor)
        bar_ust = ctk.CTkFrame(self, fg_color="transparent")
        bar_ust.pack(fill="x", padx=14, pady=(6, 0))
        ctk.CTkLabel(
            bar_ust,
            text="Genel Durum ve Göstergeler",
            font=font(12, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        ).pack(side="left")
        ctk.CTkButton(
            bar_ust,
            text="🖨️ Yazdır / Rapor Al",
            width=140,
            height=28,
            font=font(11, weight="bold"),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=rapor.rapor_olustur_ve_ac,
        ).pack(side="right")

        # 1. Ust KPI Kartlari Izgarasi (4 Kart)
        kpi_alani = ctk.CTkFrame(self, fg_color="transparent")
        kpi_alani.pack(fill="x", padx=14, pady=(10, 10))
        for i in range(4):
            kpi_alani.grid_columnconfigure(i, weight=1)

        self.kart_bugun = OzetKarti(
            kpi_alani,
            "Bugünkü İşler",
            TEMA_RENKLERI["durum_bekliyor"],
            komut=lambda: self._kategori_ac("bugun"),
        )
        self.kart_bugun.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.kart_geciken = OzetKarti(
            kpi_alani,
            "Geciken İşler",
            TEMA_RENKLERI["durum_geciken"],
            komut=lambda: self._kategori_ac("geciken"),
        )
        self.kart_geciken.grid(row=0, column=1, sticky="ew", padx=6)

        self.kart_termin = OzetKarti(
            kpi_alani,
            "Yaklaşan Terminler",
            TEMA_RENKLERI["durum_yaklasiyor"],
            komut=lambda: self._kategori_ac("termin"),
        )
        self.kart_termin.grid(row=0, column=2, sticky="ew", padx=6)

        self.kart_tamamlanan = OzetKarti(
            kpi_alani,
            "Bu Ay Tamamlanan",
            TEMA_RENKLERI["durum_tamamlandi"],
            komut=lambda: self._kategori_ac("tamamlanan"),
        )
        self.kart_tamamlanan.grid(row=0, column=3, sticky="ew", padx=(6, 0))

        # 2. Iki Sutunlu Alt Govde
        govde = ctk.CTkFrame(self, fg_color="transparent")
        govde.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        govde.grid_columnconfigure(0, weight=1)
        govde.grid_columnconfigure(1, weight=1)
        govde.grid_rowconfigure(0, weight=1)

        # Sol Sutun: Bugün Yapılacaklar
        sol_kutu = ctk.CTkFrame(
            govde,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=8,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        sol_kutu.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        sol_baslik = ctk.CTkFrame(sol_kutu, fg_color="transparent")
        sol_baslik.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(
            sol_baslik,
            text="📌 Bugün Yapılacaklar",
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        ).pack(side="left")
        self.sol_sayac = ctk.CTkLabel(
            sol_baslik,
            text="0 iş",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        )
        self.sol_sayac.pack(side="right")

        self.sol_liste = ctk.CTkScrollableFrame(sol_kutu, fg_color="transparent", label_text="")
        self.sol_liste.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        # Sag Sutun: Risk Altındaki Terminler
        sag_kutu = ctk.CTkFrame(
            govde,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=8,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        sag_kutu.grid(row=0, column=1, sticky="nsew", padx=(7, 0))

        sag_baslik = ctk.CTkFrame(sag_kutu, fg_color="transparent")
        sag_baslik.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(
            sag_baslik,
            text="⏳ Risk Altındaki Terminler",
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        ).pack(side="left")
        self.sag_sayac = ctk.CTkLabel(
            sag_baslik,
            text="0 termin",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        )
        self.sag_sayac.pack(side="right")

        self.sag_liste = ctk.CTkScrollableFrame(sag_kutu, fg_color="transparent", label_text="")
        self.sag_liste.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        # 3. Hizli Not / Karalama Defteri (Autosave)
        hizli_kutu = ctk.CTkFrame(
            self,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=8,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
            height=70,
        )
        hizli_kutu.pack(fill="x", padx=14, pady=(0, 10))
        hizli_kutu.pack_propagate(False)

        hizli_ust = ctk.CTkFrame(hizli_kutu, fg_color="transparent")
        hizli_ust.pack(fill="x", padx=10, pady=(4, 2))
        ctk.CTkLabel(
            hizli_ust,
            text="📝 Hızlı Karalama Defteri (Otomatik Kaydedilir)",
            font=font(11, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        ).pack(side="left")

        self.txt_hizli_not = ctk.CTkEntry(
            hizli_kutu,
            height=32,
            font=font(12),
            placeholder_text="Anlık telefon notu, hatırlatma veya karalama yazın (otomatik kaydedilir)...",
        )
        self.txt_hizli_not.pack(fill="x", padx=10, pady=(0, 6))
        self.txt_hizli_not.insert(0, db.ayar_al("hizli_karalama_notu", ""))
        self.txt_hizli_not.bind("<KeyRelease>", self._hizli_not_kaydet)

        self.yenile()

    def _hizli_not_kaydet(self, event=None) -> None:
        db.ayar_yaz("hizli_karalama_notu", self.txt_hizli_not.get())

    def yenile(self) -> None:
        """Verileri hesaplar, KPI ve listeleri gunceller."""
        simdi = datetime.datetime.now()
        tum_kayitlar = db.tum_notlar()

        bugunku_isler: list[dict] = []
        geciken_isler: list[dict] = []
        yaklasan_terminler: list[dict] = []
        bu_ay_tamamlanan: list[dict] = []

        bu_ay_basi = datetime.date(simdi.year, simdi.month, 1)

        for k in tum_kayitlar:
            tamamlandi = (
                k.get("durum") == "tamamlandi"
                or int(k.get("ilerleme") or 0) == 100
                or k.get("evrak_durum") == "Onaylandı"
            )

            if tamamlandi:
                tamam_zamani = reminder.dt_parse(k.get("tamamlanma_zamani"))
                if tamam_zamani and tamam_zamani.date() >= bu_ay_basi:
                    bu_ay_tamamlanan.append(k)
                continue

            zaman = reminder.not_zamani(k)
            tur = k.get("tur") or "not"

            # Bugun kontrolu
            if reminder.bugunun_olaylari(k, simdi):
                bugunku_isler.append(k)

            # Geciken kontrolu
            if reminder.geciken_olay(k, simdi) or (zaman and zaman < simdi):
                geciken_isler.append(k)

            # Termin kontrolu
            if tur == "termin":
                if zaman:
                    fark = zaman - simdi
                    if fark.total_seconds() < 0:
                        # Gecikmis termin
                        yaklasan_terminler.append(k)
                    elif fark <= datetime.timedelta(days=db.ayar_sayi("termin_esik_gun", 5)):
                        # 5 gun icinde teslim
                        yaklasan_terminler.append(k)

        # KPI kartlarini guncelle
        self.kart_bugun.guncelle(len(bugunku_isler))
        self.kart_geciken.guncelle(len(geciken_isler))
        self.kart_termin.guncelle(len(yaklasan_terminler))
        self.kart_tamamlanan.guncelle(len(bu_ay_tamamlanan))

        # Karta tiklaninca acilacak icerikler
        self._kategoriler = {
            "bugun": ("Bugünkü İşler", bugunku_isler),
            "geciken": ("Geciken İşler", geciken_isler),
            "termin": ("Yaklaşan Terminler", yaklasan_terminler),
            "tamamlanan": ("Bu Ay Tamamlanan", bu_ay_tamamlanan),
        }

        # Sol Listeyi Ciz (Bugün Yapılacaklar)
        for w in self.sol_liste.winfo_children():
            w.destroy()
        self.sol_sayac.configure(text=f"{len(bugunku_isler)} iş")

        if not bugunku_isler:
            ctk.CTkLabel(
                self.sol_liste,
                text="🎉 Bugün için planlanmış herhangi bir işiniz yok.",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(pady=30)
        else:
            for kayit in bugunku_isler:
                tur = kayit.get("tur") or "not"
                if tur == "gorev":
                    GorevKarti(self.sol_liste, self.pencere, kayit).pack(
                        fill="x", pady=4, padx=4
                    )
                elif tur == "termin":
                    TerminKarti(self.sol_liste, self.pencere, kayit).pack(
                        fill="x", pady=4, padx=4
                    )
                else:
                    NotKarti(self.sol_liste, self.pencere, kayit, mod="bugun").pack(
                        fill="x", pady=4, padx=4
                    )

        # Sag Listeyi Ciz (Risk Altındaki Terminler)
        for w in self.sag_liste.winfo_children():
            w.destroy()
        self.sag_sayac.configure(text=f"{len(yaklasan_terminler)} termin")

        if not yaklasan_terminler:
            ctk.CTkLabel(
                self.sag_liste,
                text="✅ Şu anda geciken veya risk altında olan bir termin yok.",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(pady=30)
        else:
            for kayit in yaklasan_terminler:
                TerminKarti(self.sag_liste, self.pencere, kayit).pack(
                    fill="x", pady=4, padx=4
                )

        # Acik KPI detay pencerelerini guncel veriyle tazele (or. "Geciken
        # Isler" penceresinde bir kayit "Yapildi" isaretlendiginde listeden
        # hemen dusmesi icin).
        self._detaylari_tazele()

    # ----------------------------------------------------- KPI detay penceresi
    def _kategori_ac(self, kod: str) -> None:
        """KPI kartina tiklandiginda o basliga ait kayitlari pencerede acar.

        Pencere acikken yapilan islemlerden (or. "Yapildi" isaretleme) sonra
        panel yenilendiginde icerik otomatik tazelenir; boylece kayit listeden
        hemen duser ve pencere guncel kalir.
        """
        baslik = self._kategoriler.get(kod, ("Kayıtlar", []))[0]

        pencere = ctk.CTkToplevel(self)
        pencere.geometry("620x620")
        pencere.minsize(440, 320)
        pencere.configure(fg_color=TEMA_RENKLERI["bg_ana"])
        try:
            pencere.transient(self.winfo_toplevel())
            pencere.after(80, pencere.lift)
        except Exception:
            pass

        ust = ctk.CTkFrame(
            pencere,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=0,
            height=52,
        )
        ust.pack(fill="x")
        ust.pack_propagate(False)
        ctk.CTkLabel(
            ust,
            text=baslik,
            font=font(15, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        ).pack(side="left", padx=14)
        sayac = ctk.CTkLabel(
            ust,
            text="0 kayıt",
            font=font(12),
            text_color=TEMA_RENKLERI["metin_ikincil"],
        )
        sayac.pack(side="right", padx=14)

        liste = ctk.CTkScrollableFrame(pencere, fg_color="transparent", label_text="")
        liste.pack(fill="both", expand=True, padx=12, pady=10)

        def icerik_ciz() -> None:
            guncel_kayitlar = self._kategoriler.get(kod, (baslik, []))[1]
            pencere.title(f"{baslik} ({len(guncel_kayitlar)})")
            sayac.configure(text=f"{len(guncel_kayitlar)} kayıt")
            for w in liste.winfo_children():
                w.destroy()
            if not guncel_kayitlar:
                ctk.CTkLabel(
                    liste,
                    text="Bu listede kayıt bulunmuyor.",
                    font=font(12),
                    text_color=TEMA_RENKLERI["metin_soluk"],
                ).pack(pady=40)
                return
            for kayit in guncel_kayitlar:
                tur = kayit.get("tur") or "not"
                if tur == "gorev":
                    GorevKarti(liste, self.pencere, kayit).pack(fill="x", pady=4, padx=4)
                elif tur == "termin":
                    TerminKarti(liste, self.pencere, kayit).pack(fill="x", pady=4, padx=4)
                else:
                    NotKarti(
                        liste,
                        self.pencere,
                        kayit,
                        mod="tamamlanan" if kod == "tamamlanan" else "bekleyen",
                    ).pack(fill="x", pady=4, padx=4)

        kayit_bilgi = {"pencere": pencere, "tazele": icerik_ciz}
        self._detaylar.append(kayit_bilgi)

        def _kapat(olay):
            if olay.widget is pencere:
                try:
                    self._detaylar.remove(kayit_bilgi)
                except ValueError:
                    pass

        pencere.bind("<Destroy>", _kapat)
        icerik_ciz()

    def _detaylari_tazele(self) -> None:
        """Acik KPI detay pencerelerinin icerigini guncel veriyle yeniden cizer."""
        for kayit in list(self._detaylar):
            pencere = kayit.get("pencere")
            try:
                mevcut = pencere is not None and pencere.winfo_exists()
            except Exception:
                mevcut = False
            if not mevcut:
                try:
                    self._detaylar.remove(kayit)
                except ValueError:
                    pass
                continue
            try:
                kayit["tazele"]()
            except Exception:
                pass
