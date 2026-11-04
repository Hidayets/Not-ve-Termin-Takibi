"""Ayarlar Ekrani: Gorunum, bildirimler, varsayilanlar, Windows, yedekleme ve Excel veri aktarimi."""
from __future__ import annotations

import os
import threading
import tkinter.filedialog as dosya_penceresi
import tkinter.messagebox as mesaj_kutusu

import customtkinter as ctk

import db
import guncelleme
import notifier
import reminder
import sistem
import yedek
from arayuz.tema import TEMA_RENKLERI, font
from arayuz.widgetlar import onay_iste

TEMA_ESLEME = {"Koyu": "dark", "Açık": "light", "Sistem": "system"}
TEMA_TERS = {v: k for k, v in TEMA_ESLEME.items()}


def tema_modu(deger: str) -> str:
    """Kayitli tema degerini gecerli bir CustomTkinter moduna cevirir."""
    if deger in TEMA_TERS:
        return deger
    return TEMA_ESLEME.get(deger, "dark")


class AyarlarEkrani(ctk.CTkFrame):
    def __init__(self, parent, pencere):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere
        self.uygulama = pencere.uygulama

        kaydirma = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        kaydirma.pack(fill="both", expand=True, padx=14, pady=(10, 10))
        self.govde = kaydirma

        self._kart_gorunum()
        self._kart_bildirim()
        self._kart_varsayilanlar()
        self._kart_windows()
        self._kart_guncelleme()
        self._kart_yedekleme()
        self._kart_veri()

    def _kart(self, baslik: str, ikon: str = "⚙️") -> ctk.CTkFrame:
        kutu = ctk.CTkFrame(
            self.govde,
            fg_color=TEMA_RENKLERI["bg_kart"],
            corner_radius=8,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        kutu.pack(fill="x", pady=6)

        ust = ctk.CTkFrame(kutu, fg_color="transparent")
        ust.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            ust,
            text=f"{ikon}  {baslik}",
            font=font(14, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        ).pack(side="left")

        ic = ctk.CTkFrame(kutu, fg_color="transparent")
        ic.pack(fill="x", padx=16, pady=(0, 14))
        return ic

    def _satir(self, parent, etiket: str, olustur, aciklama: str = ""):
        """Etiketli ayar satiri olusturur ve ayar bilesenini dondurur.

        `olustur`, satir cercevesini (yani bilesenin dogrudan ebeveyni olacak
        cerceveyi) alip ayar bilesenini ureten bir fonksiyondur. Bilesen satirin
        dogrudan cocugu olmalidir; aksi halde kaydirilabilir alanda satir
        cercevesinin tuvali bilesenin uzerine cizilir ve tiklamalar bilesene
        ulasmaz.
        """
        satir = ctk.CTkFrame(parent, fg_color="transparent")
        satir.pack(fill="x", pady=4)
        ctk.CTkLabel(
            satir,
            text=etiket,
            width=220,
            font=font(12),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        ).pack(side="left")
        bilesen = olustur(satir)
        bilesen.pack(side="left")
        if aciklama:
            ctk.CTkLabel(
                satir,
                text=aciklama,
                font=font(11),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(side="left", padx=12)
        return bilesen

    # ------------------------------------------------------------- Gorunum
    def _kart_gorunum(self) -> None:
        ic = self._kart("Görünüm ve Tema", "🎨")

        def _olustur(satir):
            return ctk.CTkOptionMenu(
                satir,
                values=list(TEMA_ESLEME.keys()),
                width=160,
                height=32,
                font=font(12),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=self._tema_degisti,
            )

        opt_tema = self._satir(
            ic,
            "Arayüz Teması",
            _olustur,
            "Koyu, Açık veya Windows sistem temasını takip et.",
        )
        opt_tema.set(TEMA_TERS.get(db.ayar_al("tema", "dark"), "Koyu"))

    def _tema_degisti(self, secim: str) -> None:
        db.ayar_yaz("tema", TEMA_ESLEME.get(secim, "dark"))
        self.uygulama.tema_uygula()

    def _ses_degisti(self, secim: str) -> None:
        """Secilen bildirim sesini kaydeder ve onizleme olarak calar."""
        db.ayar_yaz("bildirim_sesi", secim)
        notifier.ses_cal(secim)

    # ------------------------------------------------------------- Bildirim
    def _kart_bildirim(self) -> None:
        ic = self._kart("Bildirimler ve Uyarılar", "🔔")

        def _olustur_ses(satir):
            kutu = ctk.CTkFrame(satir, fg_color="transparent")
            self.opt_ses = ctk.CTkOptionMenu(
                kutu,
                values=notifier.SES_SECENEKLERI,
                width=180,
                height=32,
                font=font(12),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=self._ses_degisti,
            )
            self.opt_ses.pack(side="left")
            ctk.CTkButton(
                kutu,
                text="▶ Dinle",
                width=80,
                height=32,
                font=font(11, weight="bold"),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                hover_color=TEMA_RENKLERI["btn_notr_hover"],
                command=lambda: notifier.ses_cal(self.opt_ses.get()),
            ).pack(side="left", padx=(8, 0))
            return kutu

        self._satir(
            ic,
            "Bildirim Sesi",
            _olustur_ses,
            "Seçtiğiniz ses otomatik dinletilir; 'Dinle' ile tekrar çalabilirsiniz.",
        )
        self.opt_ses.set(db.ayar_al("bildirim_sesi", "Varsayılan"))

        def _olustur_aralik(satir):
            return ctk.CTkOptionMenu(
                satir,
                values=["10", "20", "30", "60"],
                width=120,
                height=32,
                font=font(12),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=lambda s: db.ayar_yaz("kontrol_araligi_sn", s),
            )

        aralik = self._satir(
            ic,
            "Kontrol Aralığı (Saniye)",
            _olustur_aralik,
            "Hatırlatıcı döngüsünün kontrol sıklığı.",
        )
        aralik.set(str(db.ayar_sayi("kontrol_araligi_sn", 20)))

    # ------------------------------------------------------------- Varsayilanlar
    def _kart_varsayilanlar(self) -> None:
        ic = self._kart("Varsayılan Değerler", "📝")

        def _olustur_oncelik(satir):
            return ctk.CTkOptionMenu(
                satir,
                values=reminder.ONCELIKLER,
                width=160,
                height=32,
                font=font(12),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=lambda s: db.ayar_yaz("varsayilan_oncelik", s),
            )

        onc = self._satir(ic, "Varsayılan Öncelik", _olustur_oncelik)
        onc.set(db.ayar_al("varsayilan_oncelik", "Normal"))

        def _olustur_kategori(satir):
            return ctk.CTkOptionMenu(
                satir,
                values=reminder.KATEGORILER,
                width=160,
                height=32,
                font=font(12),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=lambda s: db.ayar_yaz("varsayilan_kategori", s),
            )

        kat = self._satir(ic, "Varsayılan Kategori", _olustur_kategori)
        kat.set(db.ayar_al("varsayilan_kategori", "Genel"))

        def _olustur_esik(satir):
            return ctk.CTkOptionMenu(
                satir,
                values=["2", "3", "5", "7", "10", "15"],
                width=160,
                height=32,
                font=font(12),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=lambda s: db.ayar_yaz("termin_esik_gun", s),
            )

        esik = self._satir(
            ic,
            "Termin Yaklaşma Eşiği (Gün)",
            _olustur_esik,
            "Kaç gün kala riskli olarak gösterilsin.",
        )
        esik.set(str(db.ayar_sayi("termin_esik_gun", 5)))

    # ------------------------------------------------------------- Windows
    def _kart_windows(self) -> None:
        ic = self._kart("Windows Entegrasyonu", "💻")

        sw_oto = ctk.CTkSwitch(
            ic,
            text="Bilgisayar açıldığında Notlarım & Termin Takibi uygulamasını başlat",
            font=font(12),
        )
        sw_oto.pack(anchor="w", pady=6)
        if sistem.otomatik_baslat_acik_mi():
            sw_oto.select()

        def _oto_degisti():
            acik = sw_oto.get() == 1
            if sistem.otomatik_baslat_ayarla(acik):
                db.ayar_yaz("otomatik_baslat", "1" if acik else "0")
            else:
                mesaj_kutusu.showerror("Hata", "Windows başlangıç kaydı yazılamadı.")

        sw_oto.configure(command=_oto_degisti)

        sw_tepsi = ctk.CTkSwitch(
            ic,
            text="Pencere kapatıldığında arka planda çalışmaya devam et (Sistem Tepsisi)",
            font=font(12),
        )
        sw_tepsi.pack(anchor="w", pady=6)
        if db.ayar_acik("tepsiye_kucult"):
            sw_tepsi.select()
        sw_tepsi.configure(
            command=lambda: db.ayar_yaz(
                "tepsiye_kucult", "1" if sw_tepsi.get() == 1 else "0"
            )
        )

    # ------------------------------------------------------------- Guncelleme
    def _kart_guncelleme(self) -> None:
        ic = self._kart("Güncellemeler", "⬆️")

        ctk.CTkLabel(
            ic,
            text=f"Mevcut sürüm: {db.SURUM}",
            font=font(12),
            text_color=TEMA_RENKLERI["metin_ana"],
        ).pack(anchor="w", pady=(0, 4))

        def _olustur_repo(satir):
            return ctk.CTkEntry(satir, width=280, height=32, font=font(12))

        ent_repo = self._satir(
            ic, "GitHub Deposu", _olustur_repo, "örn: kullanici/depo"
        )
        ent_repo.insert(0, db.ayar_al("guncelleme_repo", guncelleme.REPO))
        ent_repo.bind("<FocusOut>", lambda _: self._guncelleme_repo_kaydet(ent_repo))

        sw_oto = ctk.CTkSwitch(
            ic,
            text="Güncellemeleri arka planda otomatik kontrol et ve indir",
            font=font(12),
        )
        sw_oto.pack(anchor="w", pady=6)
        if db.ayar_acik("guncelleme_otomatik"):
            sw_oto.select()
        sw_oto.configure(
            command=lambda: db.ayar_yaz(
                "guncelleme_otomatik", "1" if sw_oto.get() == 1 else "0"
            )
        )

        def _olustur_saat(satir):
            return ctk.CTkOptionMenu(
                satir,
                values=["1", "3", "6", "12", "24"],
                width=100,
                height=32,
                font=font(12),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=lambda s: db.ayar_yaz("guncelleme_kontrol_saat", s),
            )

        opt_saat = self._satir(
            ic,
            "Kontrol Sıklığı (Saat)",
            _olustur_saat,
            "Arka plan kontrolünün sıklığı.",
        )
        opt_saat.set(str(db.ayar_sayi("guncelleme_kontrol_saat", 6)))

        self.lbl_guncelleme = ctk.CTkLabel(
            ic,
            text=self._guncelleme_durum_metni(),
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
            justify="left",
            wraplength=620,
        )
        self.lbl_guncelleme.pack(anchor="w", pady=(4, 6))

        bar = ctk.CTkFrame(ic, fg_color="transparent")
        bar.pack(fill="x", pady=(2, 4))

        self.btn_guncelleme = ctk.CTkButton(
            bar,
            text="Şimdi Kontrol Et",
            width=150,
            height=32,
            font=font(11, weight="bold"),
            fg_color=TEMA_RENKLERI["vurgu"],
            command=self._guncelleme_kontrol_et,
        )
        self.btn_guncelleme.pack(side="left", padx=(0, 8))

        if guncelleme.bekleyen_guncelleme() is not None:
            ctk.CTkButton(
                bar,
                text="Yeniden Başlat ve Kur",
                width=170,
                height=32,
                font=font(11),
                fg_color=TEMA_RENKLERI["durum_tamamlandi"],
                command=self._guncellemeyi_kur,
            ).pack(side="left")

    def _guncelleme_repo_kaydet(self, giris: ctk.CTkEntry) -> None:
        deger = (giris.get() or "").strip()
        if deger and deger != db.ayar_al("guncelleme_repo", guncelleme.REPO):
            db.ayar_yaz("guncelleme_repo", deger)

    def _guncelleme_durum_metni(self) -> str:
        bekleyen = guncelleme.bekleyen_guncelleme()
        if bekleyen is not None:
            return (
                f"Sürüm {bekleyen.get('surum')} indirildi. "
                "Uygulama yeniden başlatıldığında kurulacak."
            )
        durum = guncelleme.durum_oku()
        mesaj = durum.get("mesaj")
        son = durum.get("son_kontrol")
        if mesaj:
            return f"{mesaj}  (Son kontrol: {son})" if son else str(mesaj)
        return "Henüz kontrol edilmedi."

    def _guncelleme_kontrol_et(self) -> None:
        self.btn_guncelleme.configure(state="disabled", text="Kontrol ediliyor...")

        def _calis():
            guncelleme.kontrol_et_ve_indir()
            try:
                self.after(0, self._guncelleme_durumu_tazele)
            except Exception:
                pass

        threading.Thread(target=_calis, daemon=True).start()

    def _guncelleme_durumu_tazele(self) -> None:
        try:
            self.lbl_guncelleme.configure(text=self._guncelleme_durum_metni())
            self.btn_guncelleme.configure(state="normal", text="Şimdi Kontrol Et")
        except Exception:
            pass

    def _guncellemeyi_kur(self) -> None:
        if not onay_iste(
            "Güncelleme", "Uygulama kapatılıp yeni sürüm kurulacak. Devam edilsin mi?"
        ):
            return
        if guncelleme.guncellemeyi_uygula():
            self.uygulama.cikis()
        else:
            mesaj_kutusu.showinfo(
                "Bilgi",
                "Güncelleme yalnızca paketlenmiş (exe) sürümde kurulabilir.",
            )

    # ------------------------------------------------------------- Yedekleme
    def _kart_yedekleme(self) -> None:
        ic = self._kart("Veritabanı ve Yedekleme", "💾")

        sw_gunluk = ctk.CTkSwitch(
            ic,
            text="Uygulama her açıldığında otomatik günlük veritabanı yedeği al",
            font=font(12),
        )
        sw_gunluk.pack(anchor="w", pady=6)
        if db.ayar_acik("gunluk_yedek"):
            sw_gunluk.select()
        sw_gunluk.configure(
            command=lambda: db.ayar_yaz("gunluk_yedek", "1" if sw_gunluk.get() == 1 else "0")
        )

        def _olustur_saklama(satir):
            return ctk.CTkEntry(satir, width=100, height=32, font=font(12))

        ent_saklama = self._satir(
            ic,
            "Yedek Saklama Süresi (Gün)",
            _olustur_saklama,
            "Eski yedekler otomatik temizlenir.",
        )
        ent_saklama.insert(0, str(db.ayar_sayi("yedek_saklama_gun", 30)))
        ent_saklama.bind("<FocusOut>", lambda _: self._saklama_kaydet(ent_saklama))

        btn_bar = ctk.CTkFrame(ic, fg_color="transparent")
        btn_bar.pack(fill="x", pady=(10, 4))

        ctk.CTkButton(
            btn_bar,
            text="Şimdi Yedek Al",
            width=130,
            height=32,
            font=font(11, weight="bold"),
            fg_color=TEMA_RENKLERI["durum_tamamlandi"],
            command=self._simdi_yedekle,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_bar,
            text="Yedek Klasörünü Aç",
            width=150,
            height=32,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=self._klasor_ac,
        ).pack(side="left")

    def _saklama_kaydet(self, giris: ctk.CTkEntry) -> None:
        try:
            gun = max(1, int(float(giris.get())))
        except (TypeError, ValueError):
            gun = 30
        db.ayar_yaz("yedek_saklama_gun", gun)

    def _simdi_yedekle(self) -> None:
        etiket = db.simdi().strftime("%Y-%m-%d_%H-%M-%S")
        yol = yedek.yedek_al(etiket=etiket)
        if yol:
            mesaj_kutusu.showinfo("Yedek Alındı", f"Veritabanı yedeği oluşturuldu:\n{yol}")

    def _klasor_ac(self) -> None:
        try:
            os.startfile(yedek.yedek_klasoru())
        except Exception as e:
            mesaj_kutusu.showerror("Hata", f"Klasör açılamadı:\n{e}")

    # ------------------------------------------------------------- Veri Islemleri
    def _kart_veri(self) -> None:
        ic = self._kart("Veri Dışa / İçe Aktar", "📊")

        bar = ctk.CTkFrame(ic, fg_color="transparent")
        bar.pack(fill="x", pady=6)

        ctk.CTkButton(
            bar,
            text="Excel'e Aktar (.xlsx)",
            width=160,
            height=34,
            font=font(11, weight="bold"),
            fg_color=TEMA_RENKLERI["vurgu"],
            command=self._excel_aktar,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            bar,
            text="Excel'den İçe Aktar",
            width=160,
            height=34,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=self._excel_iceri,
        ).pack(side="left")

    def _excel_aktar(self) -> None:
        yol = dosya_penceresi.asksaveasfilename(
            title="Excel olarak kaydet",
            defaultextension=".xlsx",
            initialfile=f"notlar_{db.simdi().strftime('%Y-%m-%d')}.xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")],
        )
        if not yol:
            return
        try:
            adet = yedek.excel_disa_aktar(yol)
            mesaj_kutusu.showinfo("Başarılı", f"{adet} kayıt Excel'e aktarıldı:\n{yol}")
        except Exception as hata:
            mesaj_kutusu.showerror("Hata", f"Dışa aktarılamadı:\n{hata}")

    def _excel_iceri(self) -> None:
        yol = dosya_penceresi.askopenfilename(
            title="Excel Dosyası Seç", filetypes=[("Excel Dosyası", "*.xlsx")]
        )
        if not yol:
            return
        if not onay_iste(
            "İçe Aktar", "Dosyadaki notlar veritabanına eklenecek. Devam edilsin mi?"
        ):
            return
        try:
            eklenen, hatalar = yedek.excel_ice_aktar(yol)
            self.uygulama.yenile()
            msg = f"{eklenen} kayıt içe aktarıldı."
            if hatalar:
                msg += "\n\nHatalar:\n" + "\n".join(hatalar[:5])
            mesaj_kutusu.showinfo("Bilgi", msg)
        except Exception as e:
            mesaj_kutusu.showerror("Hata", f"İçe aktarılamadı:\n{e}")
