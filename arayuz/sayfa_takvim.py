"""Takvim Ekrani: Ay gorunumu, gun hucresi basliklari ve sag gun detay paneli."""
from __future__ import annotations

import calendar
import datetime
import os

import customtkinter as ctk

import db
import reminder
from arayuz.tema import ONCELIK_RENKLERI, TEMA_RENKLERI, font
from arayuz.widgetlar import onay_iste, rozet


class GunKaydiKarti(ctk.CTkFrame):
    """Takvimin sag panelinde bir gune ait kaydi tum ayrintilariyla gosterir.

    Panel dar oldugu icin icerik dikey yerlesir ve metinler kart genisligine
    gore sarilir; boylece baslik, aciklama, kurum, sorumlu ve etiketler
    kisaltilmadan okunabilir.
    """

    ERTELEME = {"15 dakika": 15, "1 saat": 60, "1 gün": 1440}
    EVRAK_DURUMLARI = ["Bekliyor", "Hazırlandı", "Gönderildi", "Onaylandı", "Reddedildi"]

    def __init__(self, parent, pencere, kayit: dict, olay: datetime.datetime):
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
        self.olay = olay
        self.tur = kayit.get("tur") or "not"
        self._sarmali: list[ctk.CTkLabel] = []

        self.grid_columnconfigure(1, weight=1)

        serit = ctk.CTkFrame(self, width=5, corner_radius=3, fg_color=self._serit_rengi())
        serit.grid(row=0, column=0, rowspan=5, sticky="ns", padx=(6, 10), pady=8)

        self._basligi_ciz()
        self._rozetleri_ciz()
        self._aciklamayi_ciz()
        self._detaylari_ciz()
        self._butonlari_ciz()

        self.bind("<Configure>", self._sarmayi_guncelle)
        self.after_idle(self._sarmayi_guncelle)

    # ------------------------------------------------------------- renk
    def _serit_rengi(self):
        """Kaydin turune ve durumuna gore sol vurgu rengini dondurur."""
        if self.tur == "termin":
            return {
                "Bekliyor": TEMA_RENKLERI["durum_bekliyor"],
                "Hazırlandı": ("#0284C7", "#38BDF8"),
                "Gönderildi": ("#4F46E5", "#818CF8"),
                "Onaylandı": TEMA_RENKLERI["durum_tamamlandi"],
                "Reddedildi": TEMA_RENKLERI["durum_geciken"],
                "Gecikti": TEMA_RENKLERI["durum_geciken"],
            }.get(
                self.kayit.get("evrak_durum") or "Bekliyor",
                TEMA_RENKLERI["durum_bekliyor"],
            )
        if self.tur == "gorev":
            ilerleme = int(self.kayit.get("ilerleme") or 0)
            zaman = reminder.not_zamani(self.kayit)
            if ilerleme >= 100 or self.kayit.get("durum") == "tamamlandi":
                return TEMA_RENKLERI["durum_tamamlandi"]
            if zaman and zaman < datetime.datetime.now():
                return TEMA_RENKLERI["durum_geciken"]
            if ilerleme > 0:
                return TEMA_RENKLERI["durum_yaklasiyor"]
            return TEMA_RENKLERI["durum_bekliyor"]
        return ONCELIK_RENKLERI.get(
            self.kayit.get("oncelik", "Normal"), ("#2563EB", "#3B82F6")
        )

    # ------------------------------------------------------------- bolumler
    def _basligi_ciz(self) -> None:
        ust = ctk.CTkFrame(self, fg_color="transparent")
        ust.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(8, 2))
        ust.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            ust,
            text=self.olay.strftime("%H:%M"),
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["vurgu"],
        ).grid(row=0, column=0, sticky="nw", padx=(0, 8))

        baslik = ctk.CTkLabel(
            ust,
            text=(self.kayit.get("baslik") or "(başlıksız)"),
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
            justify="left",
        )
        baslik.grid(row=0, column=1, sticky="ew")
        self._sarmali.append(baslik)

    def _rozetleri_ciz(self) -> None:
        kutu = ctk.CTkFrame(self, fg_color="transparent")
        kutu.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(0, 4))

        tur_metni = {"gorev": "✅ Görev", "termin": "⏳ Termin"}.get(self.tur, "📝 Not")
        rozet(
            kutu, tur_metni, ("#E2E8F0", "#334155"), text_color=("#0F172A", "#F8FAFC")
        ).pack(side="left", padx=(0, 4))

        rozet(
            kutu,
            self.kayit.get("kategori") or "Genel",
            ("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(side="left", padx=4)

        if self.tur == "termin":
            rozet(
                kutu, self.kayit.get("evrak_durum") or "Bekliyor", self._serit_rengi()
            ).pack(side="left", padx=4)
        elif self.tur == "gorev":
            rozet(
                kutu,
                f"%{int(self.kayit.get('ilerleme') or 0)}",
                TEMA_RENKLERI["durum_bekliyor"],
            ).pack(side="left", padx=4)
        else:
            oncelik = self.kayit.get("oncelik") or "Normal"
            rozet(kutu, oncelik, ONCELIK_RENKLERI.get(oncelik, ("#2563EB", "#3B82F6"))).pack(
                side="left", padx=4
            )

    def _aciklamayi_ciz(self) -> None:
        aciklama = (self.kayit.get("aciklama") or "").strip()
        if not aciklama:
            return
        etiket = ctk.CTkLabel(
            self,
            text=aciklama,
            font=font(12),
            text_color=TEMA_RENKLERI["metin_ikincil"],
            anchor="w",
            justify="left",
        )
        etiket.grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=(2, 4))
        self._sarmali.append(etiket)

    def _detaylari_ciz(self) -> None:
        satirlar = self._detay_satirlari()
        if not satirlar:
            return
        kutu = ctk.CTkFrame(self, fg_color="transparent")
        kutu.grid(row=3, column=1, sticky="ew", padx=(0, 12), pady=(0, 4))
        kutu.grid_columnconfigure(0, weight=1)
        for sira, metin in enumerate(satirlar):
            etiket = ctk.CTkLabel(
                kutu,
                text=metin,
                font=font(11),
                text_color=TEMA_RENKLERI["metin_soluk"],
                anchor="w",
                justify="left",
            )
            etiket.grid(row=sira, column=0, sticky="ew", pady=1)
            self._sarmali.append(etiket)

    def _detay_satirlari(self) -> list[str]:
        """Kaydin tum alanlarini satir satir dondurur (bos alanlar atlanir)."""
        kayit = self.kayit
        satirlar = []

        kurum = (kayit.get("kurum_amir") or "").strip()
        if kurum:
            satirlar.append(f"🏛️ Kurum / Amir: {kurum}")

        sorumlu = (kayit.get("sorumlu") or "").strip()
        if sorumlu:
            satirlar.append(f"👤 Sorumlu: {sorumlu}")

        etiketler = (kayit.get("etiketler") or "").strip()
        if etiketler:
            satirlar.append(f"🏷️ Etiketler: {etiketler}")

        once = kayit.get("hatirlatma_once_dk")
        if once:
            satirlar.append(f"🔔 Hatırlatma: {reminder.hatirlatma_metni(once)}")

        tekrar = reminder.tekrar_metni(kayit)
        if tekrar and tekrar != "Tek seferlik":
            satirlar.append(f"🔁 Tekrar: {tekrar}")

        if self.tur == "gorev":
            satirlar.append(f"📊 İlerleme: %{int(kayit.get('ilerleme') or 0)}")

        if self.tur == "termin":
            zaman = reminder.not_zamani(kayit)
            if zaman and zaman < datetime.datetime.now() and kayit.get("evrak_durum") != "Onaylandı":
                satirlar.append("⚠️ Teslim tarihi geçti")
            if kayit.get("amire_bilgi_verildi"):
                satirlar.append("✅ Amire bilgi verildi")

        satirlar.append(f"📅 Planlanan: {reminder.zaman_metni(self.olay)}")

        dosya = (kayit.get("dosya_eki") or "").strip()
        if dosya:
            satirlar.append(f"📎 Dosya: {os.path.basename(dosya)}")

        return satirlar

    def _butonlari_ciz(self) -> None:
        kutu = ctk.CTkFrame(self, fg_color="transparent")
        kutu.grid(row=4, column=1, sticky="ew", padx=(0, 12), pady=(4, 10))
        kimlik = self.kayit["id"]

        if self.tur == "gorev":
            ilerleme = int(self.kayit.get("ilerleme") or 0)
            if ilerleme < 100:
                self._btn(kutu, "+%25", 56, lambda: self._ilerleme(kimlik, ilerleme + 25))
                self._btn(
                    kutu, "Tamamla", 78, lambda: self._ilerleme(kimlik, 100),
                    TEMA_RENKLERI["durum_tamamlandi"],
                )
            else:
                self._btn(kutu, "Geri Al", 70, lambda: self._ilerleme(kimlik, 0))
        elif self.tur == "termin":
            menu = ctk.CTkOptionMenu(
                kutu,
                values=self.EVRAK_DURUMLARI,
                width=100,
                height=28,
                font=font(11),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=lambda s: self._evrak_durum(kimlik, s),
            )
            menu.set(self.kayit.get("evrak_durum") or "Bekliyor")
            menu.pack(side="left", padx=(0, 6))
        else:
            tamamlandi = kayit_tamamlandi_mi(self.kayit, self.olay)
            if tamamlandi:
                self._btn(
                    kutu, "Geri Al", 70, lambda: self.uygulama.tamamlamayi_geri_al(kimlik)
                )
            else:
                self._btn(
                    kutu, "Yapıldı", 70,
                    lambda: self.uygulama.yapildi_isaretle(kimlik, self.olay),
                    TEMA_RENKLERI["durum_tamamlandi"],
                )
                menu = ctk.CTkOptionMenu(
                    kutu,
                    values=list(self.ERTELEME.keys()),
                    width=78,
                    height=28,
                    font=font(11),
                    fg_color=TEMA_RENKLERI["btn_notr"],
                    text_color=TEMA_RENKLERI["btn_notr_metin"],
                    command=lambda s: self.uygulama.ertele_uyari(
                        kimlik, self.ERTELEME[s]
                    ),
                )
                menu.pack(side="left", padx=(0, 6))

        self._btn(kutu, "Düzenle", 62, lambda: self.pencere.duzenlemeye_al(kimlik))
        self._btn(
            kutu, "Sil", 36, self._sil, "transparent",
            metin_renk=TEMA_RENKLERI["durum_geciken"],
        )

    def _btn(self, parent, metin, genislik, komut, renk=None, metin_renk=None):
        ctk.CTkButton(
            parent,
            text=metin,
            width=genislik,
            height=28,
            font=font(11, weight="bold"),
            fg_color=renk or TEMA_RENKLERI["btn_notr"],
            text_color=metin_renk or TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=komut,
        ).pack(side="left", padx=(0, 4))

    # ------------------------------------------------------------- islemler
    def _ilerleme(self, kimlik: int, yeni: int) -> None:
        db.gorev_ilerleme_kaydet(kimlik, max(0, min(100, yeni)))
        self.uygulama.arayuzu_yenile()

    def _evrak_durum(self, kimlik: int, durum: str) -> None:
        db.evrak_durum_kaydet(kimlik, durum)
        if durum == "Onaylandı":
            self.uygulama.yapildi_isaretle(kimlik)
        else:
            self.uygulama.arayuzu_yenile()

    def _sil(self) -> None:
        if onay_iste(
            "Kaydı Sil", "Kayıt geri dönüşüm kutusuna taşınacak. Onaylıyor musunuz?"
        ):
            self.uygulama.cop_kutusuna_at(self.kayit["id"])

    # ------------------------------------------------------------- sarma
    def _sarmayi_guncelle(self, _olay=None) -> None:
        """Kart genisligi degistiginde metinlerin sarma genisligini gunceller."""
        genislik = self.winfo_width()
        if genislik <= 1:
            return
        kaydirma = max(150, genislik - 45)
        for etiket in self._sarmali:
            if etiket.cget("wraplength") != kaydirma:
                etiket.configure(wraplength=kaydirma)


def kayit_tamamlandi_mi(kayit: dict, olay: datetime.datetime) -> bool:
    """Bir kaydin verilen olay/donem icin tamamlanmis sayilip sayilmadigi."""
    return bool(
        kayit.get("durum") == "tamamlandi"
        or kayit.get("tamamlanan_donem") == reminder.periyot_anahtari(kayit, olay)
    )


class TakvimEkrani(ctk.CTkFrame):
    def __init__(self, parent, pencere):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere
        self.uygulama = pencere.uygulama

        bugun = datetime.date.today()
        self.yil = bugun.year
        self.ay = bugun.month
        self.secili = bugun

        # Ust Bar: Navigasyon ve Kontroller
        ust = ctk.CTkFrame(
            self,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=8,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        ust.pack(fill="x", padx=14, pady=(10, 8))

        ctk.CTkButton(
            ust,
            text="<",
            width=36,
            height=32,
            font=font(12, weight="bold"),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=lambda: self._kaydir(-1),
        ).pack(side="left", padx=(10, 4), pady=6)

        self.lbl_ay_yil = ctk.CTkLabel(
            ust,
            text="",
            width=160,
            font=font(15, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        )
        self.lbl_ay_yil.pack(side="left", padx=4)

        ctk.CTkButton(
            ust,
            text=">",
            width=36,
            height=32,
            font=font(12, weight="bold"),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=lambda: self._kaydir(1),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            ust,
            text="Bugün",
            width=70,
            height=32,
            font=font(11, weight="bold"),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=self._bugune_don,
        ).pack(side="left", padx=12)

        ctk.CTkLabel(
            ust,
            text="Gün hücresine tıklayarak sağ panelde o günün planlarını görüntüleyebilirsiniz.",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
        ).pack(side="left", padx=8)

        # Iki Sutunlu Ana Bolum: Sol Takvim Izgarasi, Sag Gun Detayi
        govde = ctk.CTkFrame(self, fg_color="transparent")
        govde.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        govde.grid_columnconfigure(0, weight=3)
        govde.grid_columnconfigure(1, weight=2)
        govde.grid_rowconfigure(0, weight=1)

        # Sol: Takvim Kartı
        sol_kart = ctk.CTkFrame(
            govde,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=8,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        sol_kart.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        self.izgara = ctk.CTkFrame(sol_kart, fg_color="transparent")
        self.izgara.pack(fill="both", expand=True, padx=8, pady=8)
        for s in range(7):
            self.izgara.grid_columnconfigure(s, weight=1)

        # Sag: Detay Paneli
        sag_kart = ctk.CTkFrame(
            govde,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=8,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        sag_kart.grid(row=0, column=1, sticky="nsew", padx=(7, 0))

        # Sag Baslik & Tur Filtresi
        sag_ust = ctk.CTkFrame(sag_kart, fg_color="transparent")
        sag_ust.pack(fill="x", padx=12, pady=(10, 4))

        self.lbl_gun_baslik = ctk.CTkLabel(
            sag_ust,
            text="",
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        )
        self.lbl_gun_baslik.pack(side="left")

        self.opt_tur_filtre = ctk.CTkOptionMenu(
            sag_ust,
            values=["Tümü", "Not", "Görev", "Termin"],
            width=90,
            height=26,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=lambda _: self._gun_listesini_ciz(self._gun_kayitlari_onbellek),
        )
        self.opt_tur_filtre.pack(side="right")

        self.gun_listesi = ctk.CTkScrollableFrame(
            sag_kart, fg_color="transparent", label_text=""
        )
        self.gun_listesi.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        self._gun_kayitlari_onbellek = {}
        self._hucreler: dict[datetime.date, ctk.CTkFrame] = {}
        self.yenile()

    def _kaydir(self, fark: int) -> None:
        ay = self.ay + fark
        yil = self.yil
        if ay < 1:
            ay, yil = 12, yil - 1
        elif ay > 12:
            ay, yil = 1, yil + 1
        self.ay, self.yil = ay, yil
        # Goruntulenen ayda mutlaka gecerli bir secili gun kalsin; aksi halde
        # sag panel bos gorunur. Bu ay bugunu iceriyorsa bugun secilir.
        bugun = datetime.date.today()
        if self.secili.year != yil or self.secili.month != ay:
            self.secili = (
                bugun
                if (bugun.year == yil and bugun.month == ay)
                else datetime.date(yil, ay, 1)
            )
        self.yenile()

    def _bugune_don(self) -> None:
        bugun = datetime.date.today()
        self.yil, self.ay, self.secili = bugun.year, bugun.month, bugun
        self.yenile()

    def _gun_sec(self, gun: datetime.date) -> None:
        """Sadece secimi ve sag paneli gunceller; izgara yeniden cizilmez."""
        if gun == self.secili:
            return
        eski = self.secili
        self.secili = gun
        self._hucre_vurgula(eski)
        self._hucre_vurgula(gun)
        self._gun_listesini_ciz(self._gun_kayitlari_onbellek)

    def _hucre_vurgula(self, gun: datetime.date) -> None:
        """Bir gun hucresinin cercevesini secili/bugun durumuna gore boyar."""
        hucre = self._hucreler.get(gun)
        if hucre is None:
            return
        if gun == self.secili:
            renk, kalinlik = TEMA_RENKLERI["vurgu"], 2
        elif gun == datetime.date.today():
            renk, kalinlik = TEMA_RENKLERI["durum_tamamlandi"], 2
        else:
            renk, kalinlik = TEMA_RENKLERI["kenarlik"], 1
        hucre.configure(border_color=renk, border_width=kalinlik)

    def _ay_kayitlarini_derle(self) -> dict[datetime.date, list[tuple]]:
        """Ay icindeki gunler icin (kayit, olay_zamani) listesi."""
        ilk = datetime.date(self.yil, self.ay, 1)
        son = datetime.date(self.yil, self.ay, calendar.monthrange(self.yil, self.ay)[1])
        baslangic = datetime.datetime.combine(ilk, datetime.time.min)
        bitis = datetime.datetime.combine(son, datetime.time.max)

        sonuc: dict[datetime.date, list[tuple]] = {}
        for kayit in db.tum_notlar():
            for olay in reminder.olay_zamanlari(kayit, baslangic, bitis):
                sonuc.setdefault(olay.date(), []).append((kayit, olay))

        for lst in sonuc.values():
            lst.sort(key=lambda t: t[1])
        return sonuc

    def yenile(self) -> None:
        self.lbl_ay_yil.configure(text=f"{reminder.AY_ADLARI[self.ay - 1]} {self.yil}")

        for w in self.izgara.winfo_children():
            w.destroy()
        self._hucreler = {}

        # Hafta Gunleri Basliklari
        for sutun, g_adi in enumerate(reminder.GUN_ADLARI):
            ctk.CTkLabel(
                self.izgara,
                text=g_adi[:3],
                font=font(11, weight="bold"),
                text_color=TEMA_RENKLERI["metin_ikincil"],
            ).grid(row=0, column=sutun, sticky="ew", pady=(0, 4))

        self._gun_kayitlari_onbellek = self._ay_kayitlarini_derle()
        bugun = datetime.date.today()
        takvim_haftalari = calendar.Calendar(firstweekday=0).monthdatescalendar(
            self.yil, self.ay
        )

        for satir_idx, hafta in enumerate(takvim_haftalari, start=1):
            self.izgara.grid_rowconfigure(satir_idx, weight=1)
            for sutun_idx, gun in enumerate(hafta):
                ayni_ay = gun.month == self.ay
                secili_mi = gun == self.secili
                bugun_mu = gun == bugun

                kayitlar = self._gun_kayitlari_onbellek.get(gun, [])

                # Cerceve
                kenar_renk = (
                    TEMA_RENKLERI["vurgu"]
                    if secili_mi
                    else (
                        TEMA_RENKLERI["durum_tamamlandi"]
                        if bugun_mu
                        else TEMA_RENKLERI["kenarlik"]
                    )
                )
                kenar_w = 2 if (secili_mi or bugun_mu) else 1

                hucre = ctk.CTkFrame(
                    self.izgara,
                    width=10,
                    fg_color=TEMA_RENKLERI["bg_kart_ic"] if ayni_ay else ("#F1F5F9", "#0F172A"),
                    border_width=kenar_w,
                    border_color=kenar_renk,
                    corner_radius=6,
                )
                hucre.grid(
                    row=satir_idx, column=sutun_idx, sticky="nsew", padx=2, pady=2
                )
                self._hucreler[gun] = hucre

                # Tiklama butonu: gun numarasi + kayit basliklari
                btn_metin = self._hucre_metni(gun, kayitlar)

                btn = ctk.CTkButton(
                    hucre,
                    text=btn_metin,
                    width=10,
                    font=font(10, weight="bold" if bugun_mu else "normal"),
                    fg_color="transparent",
                    text_color=TEMA_RENKLERI["metin_ana"]
                    if ayni_ay
                    else TEMA_RENKLERI["metin_soluk"],
                    hover_color=TEMA_RENKLERI["bg_hover"],
                    command=lambda g=gun: self._gun_sec(g),
                )
                btn.pack(fill="both", expand=True)

        self._gun_listesini_ciz(self._gun_kayitlari_onbellek)

    def _hucre_metni(self, gun: datetime.date, kayitlar: list[tuple]) -> str:
        """Gun hucresinde gosterilecek metni uretir: gun numarasi + kayit basliklari."""
        satirlar = [f"{gun.day}"]
        for kayit, _olay in kayitlar[:3]:
            tur = kayit.get("tur") or "not"
            isaret = {"gorev": "✅", "termin": "⏳"}.get(tur, "📝")
            baslik = (kayit.get("baslik") or "").strip() or "(başlıksız)"
            if len(baslik) > 8:
                baslik = baslik[:8] + "…"
            satirlar.append(f"{isaret} {baslik}")

        kalan = len(kayitlar) - 3
        if kalan > 0:
            satirlar.append(f"+{kalan} kayıt")
        return "\n".join(satirlar)

    def _gun_listesini_ciz(self, gun_notlari: dict) -> None:
        for w in self.gun_listesi.winfo_children():
            w.destroy()

        tarih_metni = (
            f"{self.secili.strftime('%d.%m.%Y')} - "
            f"{reminder.GUN_ADLARI[self.secili.weekday()]}"
        )
        self.lbl_gun_baslik.configure(text=tarih_metni)

        kayitlar = gun_notlari.get(self.secili, [])
        secili_tur = self.opt_tur_filtre.get()

        filtrelenen = []
        for kayit, olay in kayitlar:
            tur = kayit.get("tur") or "not"
            if secili_tur == "Not" and tur != "not":
                continue
            if secili_tur == "Görev" and tur != "gorev":
                continue
            if secili_tur == "Termin" and tur != "termin":
                continue
            filtrelenen.append((kayit, olay))

        if not filtrelenen:
            ctk.CTkLabel(
                self.gun_listesi,
                text="Bu güne ait planlanan kayıt bulunmuyor.",
                font=font(12),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(pady=30)
            return

        for kayit, olay in filtrelenen:
            GunKaydiKarti(self.gun_listesi, self.pencere, kayit, olay).pack(
                fill="x", pady=4, padx=2
            )
