"""Ana Pencere: Sol yan menu (sidebar), ust baslik bari ve dinamik sayfa yonetimi."""
from __future__ import annotations

import ctypes
import datetime
import os

import customtkinter as ctk

import db
import notifier
import reminder
import sistem
from arayuz.aylik_ozet import AylikGorevlerEkrani
from arayuz.sayfa_ayarlar import AyarlarEkrani
from arayuz.sayfa_bildirimler import BildirimlerEkrani
from arayuz.sayfa_cop_kutusu import CopKutusuEkrani
from arayuz.sayfa_gorevler import GorevlerEkrani
from arayuz.sayfa_notlar import NotlarEkrani
from arayuz.sayfa_panel import PanelEkrani
from arayuz.sayfa_takvim import TakvimEkrani
from arayuz.sayfa_terminler import TerminlerEkrani
from arayuz.tema import FONT_FAMILY, TEMA_RENKLERI, font
from arayuz.uyari_penceresi import UyariPenceresi
from arayuz.widgetlar import rozet
from arayuz.yeni_ekle_dialog import YeniEkleDialog

BOLUMLER = [
    ("panel", "📊  Panel"),
    ("notlar", "📝  Notlar"),
    ("gorevler", "✅  Görevler"),
    ("aylik", "📆  Aylık Görevler"),
    ("terminler", "📁  Evrak & Termin"),
    ("takvim", "📅  Takvim"),
    ("bildirimler", "🔔  Bildirimler"),
    ("cop", "♻️  Geri Dönüşüm"),
    ("ayarlar", "⚙️  Ayarlar"),
]

BOLUM_KODLARI = {kod for kod, _ in BOLUMLER}

# Ctrl+1..9 klavye kisayollari (gorunum sirasindan bagimsiz sabit eslesme).
KISAYOL_BOLUMLERI = [
    "panel",
    "notlar",
    "gorevler",
    "terminler",
    "takvim",
    "bildirimler",
    "cop",
    "ayarlar",
]


class AnaPencere(ctk.CTk):
    def __init__(self, uygulama):
        super().__init__()
        self.uygulama = uygulama
        # Tema degisiminde CustomTkinter, baslik cubugu rengini guncellemek icin
        # pencereyi gizleyip yeniden gosterir; bu da tum ekranin kaybolup geri
        # gelmesine (titremeye) yol acar. Baslik cubugu rengini biz dogrudan
        # DwmSetWindowAttribute ile uyguladigimiz icin bu davranis kapatilir.
        self._deactivate_windows_window_header_manipulation = True
        self.title("Notlarım & Termin Takibi")
        self.geometry("1200x780")
        self.minsize(1040, 680)
        self.protocol("WM_DELETE_WINDOW", self.kapat_talebi)
        self.configure(fg_color=TEMA_RENKLERI["bg_ana"])
        self._ikonu_ayarla()

        self.uyarilar: list[UyariPenceresi] = []
        self._tepsi_uyarisi_gosterildi = False
        self.aktif_bolum: str = "panel"
        self.sayfalar: dict[str, ctk.CTkFrame] = {}
        self.nav_butonlari: dict[str, ctk.CTkButton] = {}
        # Veri degistiginde yeniden cizilmesi gereken sayfalar. Gecis hizini
        # korumak icin sayfa yalnizca ilk gosterimde ve kirliyse yenilenir.
        self._kirli: set[str] = set()
        # Yan menu ozet rozetleri yalnizca veri degistiginde yeniden hesaplanir.
        self._ozet_kirli = True

        # Ana Izgara: Sol Yan Menu (240px) + Sag Ana Bolge
        self.grid_columnconfigure(0, weight=0, minsize=240)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Navigasyon butonlarinda tekrar tekrar font uretmemek icin onbellek
        self._nav_font = font(12, weight="normal")
        self._nav_font_aktif = font(12, weight="bold")

        self._yan_menuyu_olustur()
        self._sag_bolgeyi_olustur()

        # Sayfalar ilk gosterimde tembel olarak olusturulur (acilis hizli kalir)
        self.bolum_goster("panel")
        self.ozet_sayaclari_guncelle()
        self._kisayollari_bagla()
        # Pencere olustuktan sonra baslik cubugu rengini (koyu/acik) uygula.
        self.after(80, self.baslik_cubugu_rengini_ayarla)

    def baslik_cubugu_rengini_ayarla(self) -> None:
        """Baslik cubugu rengini pencereyi gizlemeden (titremesiz) uygular."""
        try:
            koyu = ctk.get_appearance_mode() == "Dark"
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            deger = ctypes.c_int(1 if koyu else 0)
            # DWMWA_USE_IMMERSIVE_DARK_MODE: 20 (yeni) / 19 (eski Windows surumleri)
            for nitelik in (20, 19):
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, nitelik, ctypes.byref(deger), ctypes.sizeof(deger)
                ) == 0:
                    break
        except Exception:
            pass

    def _kisayollari_bagla(self) -> None:
        """Klavye hizlandiricilari: Ctrl+N, F5, Ctrl+P, Ctrl+1..9"""
        self.bind("<Control-n>", lambda e: self._yeni_ekle_dialog_ac())
        self.bind("<Control-N>", lambda e: self._yeni_ekle_dialog_ac())
        self.bind("<F5>", lambda e: self.yenile())
        self.bind("<Control-p>", lambda e: self._hizli_rapor_al())
        self.bind("<Control-P>", lambda e: self._hizli_rapor_al())

        for idx, kod in enumerate(KISAYOL_BOLUMLERI, start=1):
            self.bind(f"<Control-Key-{idx}>", lambda e, k=kod: self.bolum_goster(k))

    def _hizli_rapor_al(self) -> None:
        try:
            import rapor
            rapor.rapor_olustur_ve_ac()
        except Exception as e:
            print("[rapor hatasi]", e)

    def _ikonu_ayarla(self) -> None:
        """Pencere ve gorev cubugu simgesini uygulama ikonuna ayarlar.

        Aksi halde uygulama pythonw/main.py ile acildiginda gorev cubugunda
        Python simgesi gorunur. Gorev cubugu gruplamasi icin gereken
        AppUserModelID ise pencereler olusmadan once main.py'de ayarlanir.
        """
        try:
            if os.path.exists(db.IKON_YOLU):
                self.iconbitmap(db.IKON_YOLU)
        except Exception:
            pass

    # ------------------------------------------------------------- Sol Yan Menu
    def _yan_menuyu_olustur(self) -> None:
        self.sidebar = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0,
            fg_color=TEMA_RENKLERI["bg_sidebar"],
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # 1. Logo ve Baslik
        logo_kutusu = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_kutusu.pack(fill="x", padx=16, pady=(18, 14))

        ctk.CTkLabel(
            logo_kutusu,
            text="📌 Notlarım & Termin",
            font=font(16, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            logo_kutusu,
            text="Okul & Kurum Yönetimi",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        # Ince ayirici cizgi
        ctk.CTkFrame(
            self.sidebar, height=1, fg_color=TEMA_RENKLERI["kenarlik"]
        ).pack(fill="x", padx=14, pady=(0, 10))

        # 2. Navigasyon Butonlari
        nav_alani = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_alani.pack(fill="both", expand=True, padx=10)

        for kod, etiket in BOLUMLER:
            btn = ctk.CTkButton(
                nav_alani,
                text=etiket,
                anchor="w",
                height=38,
                corner_radius=6,
                font=self._nav_font,
                fg_color="transparent",
                text_color=TEMA_RENKLERI["metin_ikincil"],
                hover_color=TEMA_RENKLERI["bg_hover"],
                command=lambda k=kod: self.bolum_goster(k),
            )
            btn.pack(fill="x", pady=2)
            self.nav_butonlari[kod] = btn

        # Ince ayirici cizgi
        ctk.CTkFrame(
            self.sidebar, height=1, fg_color=TEMA_RENKLERI["kenarlik"]
        ).pack(fill="x", padx=14, pady=(6, 8))

        # 3. Alt Kullanici Ozet Rozetleri
        self.ozet_kutusu = ctk.CTkFrame(
            self.sidebar,
            fg_color=TEMA_RENKLERI["bg_kart_ic"],
            corner_radius=6,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        self.ozet_kutusu.pack(fill="x", padx=12, pady=(0, 14))

        self.lbl_ozet_bugun = ctk.CTkLabel(
            self.ozet_kutusu,
            text="📌 Bugün: 0 iş",
            font=font(11),
            text_color=TEMA_RENKLERI["durum_bekliyor"],
            anchor="w",
        )
        self.lbl_ozet_bugun.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_ozet_geciken = ctk.CTkLabel(
            self.ozet_kutusu,
            text="⚠️ 0 geciken",
            font=font(11),
            text_color=TEMA_RENKLERI["durum_geciken"],
            anchor="w",
        )
        self.lbl_ozet_geciken.pack(fill="x", padx=10, pady=2)

        self.lbl_ozet_termin = ctk.CTkLabel(
            self.ozet_kutusu,
            text="⏳ 0 termin yaklaşıyor",
            font=font(11),
            text_color=TEMA_RENKLERI["durum_yaklasiyor"],
            anchor="w",
        )
        self.lbl_ozet_termin.pack(fill="x", padx=10, pady=(2, 6))

    # ------------------------------------------------------------- Sag Ana Bolge
    def _sag_bolgeyi_olustur(self) -> None:
        self.sag_alan = ctk.CTkFrame(self, fg_color="transparent")
        self.sag_alan.grid(row=0, column=1, sticky="nsew")
        self.sag_alan.grid_columnconfigure(0, weight=1)
        self.sag_alan.grid_rowconfigure(1, weight=1)

        # 1. Ust Bar (Header)
        self.ust_bar = ctk.CTkFrame(
            self.sag_alan,
            height=60,
            corner_radius=0,
            fg_color=TEMA_RENKLERI["bg_ana"],
            border_width=0,
        )
        self.ust_bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        self.ust_bar.grid_propagate(False)

        self.lbl_sayfa_baslik = ctk.CTkLabel(
            self.ust_bar,
            text="Panel",
            font=font(20, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        )
        self.lbl_sayfa_baslik.pack(side="left", padx=6, pady=10)

        # Sag Ust: Belirgin ama Abartisiz "Yeni Ekle" Butonu
        self.btn_yeni = ctk.CTkButton(
            self.ust_bar,
            text="+ Yeni Ekle (Ctrl+N)",
            width=150,
            height=36,
            font=font(12, weight="bold"),
            fg_color=TEMA_RENKLERI["btn_primary"],
            hover_color=TEMA_RENKLERI["btn_primary_hover"],
            command=self._yeni_ekle_dialog_ac,
        )
        self.btn_yeni.pack(side="right", padx=6, pady=10)

        # Ince ayrac cizgisi
        ayrac = ctk.CTkFrame(self.sag_alan, height=1, fg_color=TEMA_RENKLERI["kenarlik"])
        ayrac.grid(row=0, column=0, sticky="sew", padx=14)

        # 2. Sayfa Icerik Konteyneri
        self.icerik_alani = ctk.CTkFrame(self.sag_alan, fg_color="transparent")
        self.icerik_alani.grid(row=1, column=0, sticky="nsew")
        self.icerik_alani.grid_columnconfigure(0, weight=1)
        self.icerik_alani.grid_rowconfigure(0, weight=1)

    def _sayfa_olustur(self, kod: str) -> ctk.CTkFrame:
        """Bir sayfayi ilk gosteriminde olusturur ve onbellege alir."""
        olusturucular = {
            "panel": lambda: PanelEkrani(self.icerik_alani, self),
            "notlar": lambda: NotlarEkrani(self.icerik_alani, self),
            "gorevler": lambda: GorevlerEkrani(self.icerik_alani, self),
            "aylik": lambda: AylikGorevlerEkrani(self.icerik_alani, self),
            "terminler": lambda: TerminlerEkrani(self.icerik_alani, self),
            "takvim": lambda: TakvimEkrani(self.icerik_alani, self),
            "bildirimler": lambda: BildirimlerEkrani(self.icerik_alani, self),
            "cop": lambda: CopKutusuEkrani(self.icerik_alani, self),
            "ayarlar": lambda: AyarlarEkrani(self.icerik_alani, self),
        }
        sayfa = olusturucular[kod]()
        self.sayfalar[kod] = sayfa
        return sayfa

    def bolum_goster(self, kod: str) -> None:
        """Secilen bolumu on plana cikarir, sidebar butonunu aktifler."""
        if kod not in BOLUM_KODLARI:
            return

        self.aktif_bolum = kod

        # Buton stillerini guncelle (fontlar onbellekten kullanilir)
        for k, btn in self.nav_butonlari.items():
            if k == kod:
                # Aktif sekme icin dolgun mavi blok yerine sade bir arka plan ve
                # vurgu renkli metin kullanilir; boylece sekme yazisi "secili
                # metin" gibi gorunmez.
                btn.configure(
                    fg_color=TEMA_RENKLERI["bg_sidebar_aktif"],
                    text_color=TEMA_RENKLERI["vurgu"],
                    font=self._nav_font_aktif,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=TEMA_RENKLERI["metin_ikincil"],
                    font=self._nav_font,
                )

        # Baslik metnini guncelle
        baslik_haritasi = {
            "panel": "Panel & Genel Durum",
            "notlar": "Notlarım",
            "gorevler": "Görev Takibi",
            "aylik": "Aylık Görevler",
            "terminler": "Evrak & Termin Yönetimi",
            "takvim": "Takvim Planı",
            "bildirimler": "Bildirim Merkezi",
            "cop": "Geri Dönüşüm Kutusu",
            "ayarlar": "Uygulama Ayarları",
        }
        self.lbl_sayfa_baslik.configure(text=baslik_haritasi.get(kod, "Panel"))

        # Sayfa yalnizca ilk gosterimde olusturulur; boylece acilis hizli kalir.
        yeni = kod not in self.sayfalar
        if yeni:
            self._sayfa_olustur(kod)
            self._kirli.discard(kod)

        for k, sayfa in self.sayfalar.items():
            if k == kod:
                sayfa.grid(row=0, column=0, sticky="nsew")
            else:
                sayfa.grid_remove()

        # Veri degismedikce sayfa yeniden cizilmez; sekmeler arasi gecis
        # aninda gerceklesir. Yalnizca kirli sayfalar bir sonraki dongu adiminda
        # (tiklar tiklamaz hissi icin) yenilenir.
        if not yeni and kod in self._kirli:
            self._kirli.discard(kod)
            hedef = self.sayfalar[kod]
            self.after_idle(lambda s=hedef, k=kod: self._sayfayi_yenile(s, k))
        # Rozetler yalnizca veri degistiginde yeniden hesaplanir; boylece sekme
        # gecisleri veritabani okumasi nedeniyle yavaslamaz.
        if self._ozet_kirli:
            self.after_idle(self.ozet_sayaclari_guncelle)

    def _sayfayi_yenile(self, sayfa, kod: str) -> None:
        """Erteleme sirasinda bolum degistiyse yenilemeyi iptal eder."""
        if self.aktif_bolum != kod:
            return
        yenile = getattr(sayfa, "yenile", None)
        if callable(yenile):
            yenile()

    def ozet_sayaclari_guncelle(self) -> None:
        """Yan menunun altindaki ozet rozetlerini yeniler."""
        simdi = datetime.datetime.now()
        tum_kayitlar = db.tum_notlar()

        bugun_sayisi = 0
        geciken_sayisi = 0
        termin_sayisi = 0

        for k in tum_kayitlar:
            tamamlandi = (
                k.get("durum") == "tamamlandi"
                or int(k.get("ilerleme") or 0) == 100
                or k.get("evrak_durum") == "Onaylandı"
            )
            if tamamlandi:
                continue

            zaman = reminder.not_zamani(k)
            tur = k.get("tur") or "not"

            if reminder.bugunun_olaylari(k, simdi):
                bugun_sayisi += 1

            if reminder.geciken_olay(k, simdi) or (zaman and zaman < simdi):
                geciken_sayisi += 1

            if tur == "termin":
                if zaman:
                    fark = zaman - simdi
                    if fark <= datetime.timedelta(days=db.ayar_sayi("termin_esik_gun", 3)):
                        termin_sayisi += 1

        self.lbl_ozet_bugun.configure(text=f"📌 Bugün: {bugun_sayisi} iş")
        self.lbl_ozet_geciken.configure(text=f"⚠️ {geciken_sayisi} geciken")
        self.lbl_ozet_termin.configure(text=f"⏳ {termin_sayisi} termin yaklaşıyor")
        self._ozet_kirli = False

    # ------------------------------------------------------------- Islemler
    def yenile(self) -> None:
        """Veri degisti: olusturulmus tum sayfalari kirli isaretle.

        Yalnizca aktif sayfa hemen yeniden cizilir; digerleri kullanici o
        bolume gectiginde tazelenir. Bu sayede gecisler hizli kalir.
        """
        self._kirli = set(self.sayfalar)
        aktif = self.sayfalar.get(self.aktif_bolum)
        if aktif is not None and hasattr(aktif, "yenile"):
            aktif.yenile()
            self._kirli.discard(self.aktif_bolum)
        self.ozet_sayaclari_guncelle()

    def sekme_goster(self, ad: str) -> None:
        """Eski metotla geriye donuk uyumluluk."""
        eslesme = {
            "Bugün": "panel",
            "Yeni Not": "notlar",
            "Bekleyen Notlar": "notlar",
            "Geciken Notlar": "panel",
            "Tamamlananlar": "aylik",
            "Takvim": "takvim",
            "Ayarlar": "ayarlar",
            "Geri Dönüşüm": "cop",
        }
        hedef = eslesme.get(ad, "panel")
        self.bolum_goster(hedef)

    def duzenlemeye_al(self, not_id: int) -> None:
        """Kayıt düzenleme dialogunu açar."""
        YeniEkleDialog(self, self, duzenlenen_id=not_id)

    def _yeni_ekle_dialog_ac(self) -> None:
        """Aktif sayfaya gore varsayilan turle yeni ekleme dialogu acar."""
        varsayilan_tur = "not"
        if self.aktif_bolum == "gorevler":
            varsayilan_tur = "gorev"
        elif self.aktif_bolum == "terminler":
            varsayilan_tur = "termin"
        YeniEkleDialog(self, self, varsayilan_tur=varsayilan_tur)

    def pencereyi_goster(self, ad: str | None = None) -> None:
        """Pencereyi on plana getirir (tepsi ve sabitlenmis kisayol istekleri).

        Yalnizca deiconify/lift yetmez: Windows arka plandaki bir surecin
        penceresini dogrudan one getirmesini engeller. Bu yuzden pencere
        Win32 tarafinda (giris kuyruguna gecici olarak baglanarak) one alinir;
        ardindan kisa sureli 'en ustte' davranisiyla odagin gercekten
        uygulamaya gecmesi garanti edilir.
        """
        try:
            self.deiconify()
        except Exception:
            pass
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            self.update_idletasks()
            sistem.pencereyi_one_getir(hwnd)
        except Exception:
            pass
        try:
            self.lift()
            self.focus_force()
            # Kalici bir "her zaman ustte" davranisi istemiyoruz; yalnizca
            # odagi garantilemek icin kisa bir sure en ustte tutulur.
            if not getattr(self, "_ustte_gecici", False):
                self._ustte_gecici = True
                self.attributes("-topmost", True)
                self.after(300, self._gecici_ustte_birak)
        except Exception:
            pass
        if ad:
            self.sekme_goster(ad)

    def _gecici_ustte_birak(self) -> None:
        self._ustte_gecici = False
        try:
            self.attributes("-topmost", False)
        except Exception:
            pass

    def kapat_talebi(self) -> None:
        if db.ayar_acik("tepsiye_kucult"):
            self.withdraw()
            if not self._tepsi_uyarisi_gosterildi:
                self._tepsi_uyarisi_gosterildi = True
                notifier.bildirim_goster(
                    "Uygulama arka planda çalışıyor",
                    "Notlarım & Termin Takibi sistem tepsisinde çalışmaya devam ediyor.",
                )
        else:
            self.uygulama.cikis()

    def uyari_ekle(self, kayit: dict, olay: datetime.datetime) -> None:
        def pencere_olustur() -> None:
            try:
                pencere = UyariPenceresi(self, kayit, olay, sira=len(self.uyarilar))
                self.uyarilar.append(pencere)
            except Exception as hata:
                print("[uyari penceresi hatasi]", hata)

        self.after(0, pencere_olustur)

    def uyari_kapandi(self, pencere) -> None:
        if pencere in self.uyarilar:
            self.uyarilar.remove(pencere)

    def uyari_kapat_id(self, not_id: int) -> None:
        """Verilen kayda ait acik hatirlatma penceresini kapatir (or. bildirimden erteleme)."""
        for pencere in list(self.uyarilar):
            try:
                if pencere.kayit.get("id") == not_id:
                    pencere.kapat()
            except Exception:
                pass
