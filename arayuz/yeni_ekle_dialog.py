"""Yeni Ekle / Duzenle Modal Form Penceresi.

Not, Gorev ve Evrak/Termin kayitlarini dinamik form alanlariyla olusturur ve gunceller.
"""
from __future__ import annotations

import datetime
import os
import tkinter.filedialog as dosya_penceresi
import tkinter.messagebox as mesaj_kutusu

import customtkinter as ctk

import db
import reminder
from arayuz.tema import (
    EVRAK_DURUMLARI,
    FONT_FAMILY,
    ONCELIK_RENKLERI,
    TERMIN_KURALLARI,
    TEMA_RENKLERI,
    font,
)
from arayuz.widgetlar import TarihSaatSecici

OKUL_SABLONLARI = [
    {
        "etiket": "📋 Hızlı Şablon Seçin...",
        "tur": "Not",
        "baslik": "",
        "kurum": "",
        "sorumlu": "",
        "aciklama": "",
    },
    {
        "etiket": "Aylık Ek Ders Puantajı",
        "tur": "Evrak & Termin",
        "baslik": "Aylık Ek Ders Puantajı ve Çizelgesi",
        "kurum": "İlçe Milli Eğitim Müdürlüğü",
        "sorumlu": "",
        "aciklama": "Öğretmenlerin aylık ek ders puantaj cetvellerinin kontrol edilip DYS üzerinden gönderilmesi.",
    },
    {
        "etiket": "Maaş & SGK Bildirgeleri",
        "tur": "Evrak & Termin",
        "baslik": "Maaş Değişiklikleri ve SGK Bildirgeleri",
        "kurum": "İlçe Malmüdürlüğü / Muhasebe",
        "sorumlu": "",
        "aciklama": "Rapor, terfi ve kesintilerin KBS sistemine girilerek onaylanması.",
    },
    {
        "etiket": "Zümre Öğretmenler Kurulu Tutanakları",
        "tur": "Görev",
        "baslik": "Zümre Öğretmenler Kurulu Tutanaklarının Teslimi",
        "kurum": "",
        "sorumlu": "Zümre Başkanları",
        "aciklama": "Dönem zümre toplantı tutanaklarının idareye teslim edilmesi ve onaylatılması.",
    },
    {
        "etiket": "Şube Öğretmenler Kurulu (ŞÖK)",
        "tur": "Görev",
        "baslik": "Şube Öğretmenler Kurulu (ŞÖK) Toplantısı",
        "kurum": "",
        "sorumlu": "Sınıf Rehber Öğretmenleri",
        "aciklama": "Risk altındaki öğrencilerin değerlendirilmesi ve ŞÖK kararlarının dosyalanması.",
    },
    {
        "etiket": "TEFBİS Gelir-Gider Kayıtları",
        "tur": "Evrak & Termin",
        "baslik": "Okul Aile Birliği TEFBİS Gelir-Gider Girişi",
        "kurum": "Okul Aile Birliği / MEM",
        "sorumlu": "",
        "aciklama": "Aylık fatura ve bağış makbuzlarının TEFBİS modülüne zamanında işlenmesi.",
    },
    {
        "etiket": "e-Okul Sınav Not Girişleri",
        "tur": "Görev",
        "baslik": "e-Okul Yazılı Sınav Notlarının Girişi",
        "kurum": "",
        "sorumlu": "Ders Öğretmenleri",
        "aciklama": "Yazılı sınav notlarının ve performans değerlendirmelerinin e-Okul sistemine girilmesi.",
    },
    {
        "etiket": "İSG Aylık Okul Denetimi",
        "tur": "Görev",
        "baslik": "İSG Aylık Okul Bina ve Yangın Tüpü Kontrolü",
        "kurum": "",
        "sorumlu": "İSG Koordinatörü / Müdür Yrd.",
        "aciklama": "Okul acil çıkış, yangın tüpleri ve ilk yardım dolaplarının periyodik kontrolü.",
    },
    {
        "etiket": "Rehberlik Faaliyet Raporu",
        "tur": "Evrak & Termin",
        "baslik": "Rehberlik Servisi Dönem Sonu Çalışma Raporu",
        "kurum": "RAM / İlçe MEM",
        "sorumlu": "",
        "aciklama": "Dönemlik rehberlik ve psikolojik danışma hizmetleri faaliyet raporunun iletilmesi.",
    },
]


class YeniEkleDialog(ctk.CTkToplevel):
    def __init__(self, parent, pencere, duzenlenen_id: int | None = None, varsayilan_tur: str = "not"):
        super().__init__(parent)
        self.pencere = pencere
        self.uygulama = pencere.uygulama
        self.duzenlenen_id = duzenlenen_id

        self.title("Kayıt Düzenle" if duzenlenen_id else "Yeni Ekle")
        self.geometry("640x720")
        self.minsize(580, 620)
        self.transient(parent)
        self.grab_set()

        # Ana konteyner
        self.configure(fg_color=TEMA_RENKLERI["bg_ana"])

        # Ust Baslik
        ust = ctk.CTkFrame(self, fg_color="transparent")
        ust.pack(fill="x", padx=20, pady=(16, 8))

        ctk.CTkLabel(
            ust,
            text="Kayıt Düzenle" if duzenlenen_id else "Yeni Kayıt Oluştur",
            font=font(18, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
        ).pack(side="left")

        if not duzenlenen_id:
            self.opt_sablon = ctk.CTkOptionMenu(
                ust,
                values=[s["etiket"] for s in OKUL_SABLONLARI],
                width=220,
                height=30,
                font=font(11),
                fg_color=TEMA_RENKLERI["btn_notr"],
                text_color=TEMA_RENKLERI["btn_notr_metin"],
                command=self._sablon_secildi,
            )
            self.opt_sablon.pack(side="right")

        # Tur Secici (SegmentedButton)
        self.tur_secici = ctk.CTkSegmentedButton(
            self,
            values=["Not", "Görev", "Evrak & Termin"],
            font=font(12, weight="bold"),
            command=self._tur_degisti,
            height=34,
            selected_color=TEMA_RENKLERI["vurgu"],
            selected_hover_color=TEMA_RENKLERI["vurgu_hover"],
        )
        self.tur_secici.pack(fill="x", padx=20, pady=(4, 12))

        # Kaydirilabilir Form Alani
        self.form = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self.form.pack(fill="both", expand=True, padx=16, pady=4)
        self.form.grid_columnconfigure(0, weight=1)
        self.form.grid_columnconfigure(1, weight=1)

        self._bilesenleri_olustur()

        # Alt Butonlar Bar
        alt = ctk.CTkFrame(self, fg_color=TEMA_RENKLERI["bg_kart"], height=64)
        alt.pack(fill="x", side="bottom")

        ctk.CTkButton(
            alt,
            text="İptal",
            width=90,
            height=36,
            font=font(12),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=self.destroy,
        ).pack(side="right", padx=(6, 20), pady=14)

        self.btn_kaydet = ctk.CTkButton(
            alt,
            text="Güncelle" if duzenlenen_id else "Kaydet",
            width=120,
            height=36,
            font=font(12, weight="bold"),
            fg_color=TEMA_RENKLERI["btn_primary"],
            hover_color=TEMA_RENKLERI["btn_primary_hover"],
            command=self._kaydet,
        )
        self.btn_kaydet.pack(side="right", padx=6, pady=14)

        # Varsayilan veya duzenlenen veriyi yukle
        if duzenlenen_id:
            self._duzenle_yukle(duzenlenen_id)
        else:
            eslesme = {"not": "Not", "gorev": "Görev", "termin": "Evrak & Termin"}
            self.tur_secici.set(eslesme.get(varsayilan_tur, "Not"))
            self._tur_degisti(self.tur_secici.get())

    def _bilesenleri_olustur(self) -> None:
        """Formdaki tum alanlari tanimlar."""
        # 1. Baslik / Evrak Adi
        self.lbl_baslik = ctk.CTkLabel(
            self.form, text="Başlık *", font=font(12, weight="bold"), anchor="w"
        )
        self.ent_baslik = ctk.CTkEntry(self.form, height=36, font=font(12))

        # 2. Aciklama / Not Alani
        self.lbl_aciklama = ctk.CTkLabel(
            self.form, text="Açıklama / Notlar", font=font(12), anchor="w"
        )
        self.txt_aciklama = ctk.CTkTextbox(self.form, height=76, font=font(12))

        # 3. Tarih ve Saat Secici
        self.lbl_tarih = ctk.CTkLabel(
            self.form, text="Tarih ve Saat *", font=font(12, weight="bold"), anchor="w"
        )
        self.secici = TarihSaatSecici(self.form)

        # 4. Oncelik ve Kategori (Not icin)
        self.lbl_oncelik = ctk.CTkLabel(self.form, text="Öncelik", font=font(12), anchor="w")
        self.opt_oncelik = ctk.CTkOptionMenu(
            self.form, values=reminder.ONCELIKLER, height=32, font=font(12)
        )
        self.opt_oncelik.set(db.ayar_al("varsayilan_oncelik", "Normal"))

        self.lbl_kategori = ctk.CTkLabel(self.form, text="Kategori", font=font(12), anchor="w")
        self.opt_kategori = ctk.CTkOptionMenu(
            self.form, values=reminder.KATEGORILER, height=32, font=font(12)
        )
        self.opt_kategori.set(db.ayar_al("varsayilan_kategori", "Genel"))

        # 5. Etiketler (Not icin)
        self.lbl_etiketler = ctk.CTkLabel(
            self.form, text="Etiketler (virgülle ayırın)", font=font(12), anchor="w"
        )
        self.ent_etiketler = ctk.CTkEntry(
            self.form, height=34, font=font(12), placeholder_text="Örn. sınav, veli, toplantı"
        )

        # 6. Tekrar Kurali (Not ve Gorev icin)
        self.lbl_tekrar = ctk.CTkLabel(self.form, text="Tekrar", font=font(12), anchor="w")
        self.opt_tekrar = ctk.CTkOptionMenu(
            self.form,
            values=list(reminder.TEKRAR_TIPLERI.keys()),
            height=32,
            font=font(12),
            command=lambda _: self._tekrar_degisti(),
        )

        # Aylik Kural Kutusu
        self.frm_aylik = ctk.CTkFrame(
            self.form, fg_color=TEMA_RENKLERI["bg_kart_ic"], corner_radius=6
        )
        ctk.CTkLabel(
            self.frm_aylik, text="Aylık Kural:", font=font(11, weight="bold")
        ).pack(side="left", padx=8, pady=6)
        self.opt_aylik = ctk.CTkOptionMenu(
            self.frm_aylik,
            values=reminder.AYLIK_SECENEKLER,
            height=28,
            font=font(11),
        )
        self.opt_aylik.pack(side="left", padx=6, pady=6)
        self.ent_ay_gunleri = ctk.CTkEntry(
            self.frm_aylik,
            placeholder_text="Günler (Örn. 1, 5, 15)",
            height=28,
            width=140,
            font=font(11),
        )
        self.ent_ay_gunleri.pack(side="left", padx=6, pady=6)

        # 7. Sorumlu Kisi ve Ilerleme (Gorev icin)
        self.lbl_sorumlu = ctk.CTkLabel(
            self.form, text="Sorumlu Kişi", font=font(12), anchor="w"
        )
        self.ent_sorumlu = ctk.CTkEntry(
            self.form, height=34, font=font(12), placeholder_text="Örn. Müdür Yrd., Ahmet Öğretmen"
        )

        self.lbl_ilerleme = ctk.CTkLabel(
            self.form, text="İlerleme Durumu (%)", font=font(12), anchor="w"
        )
        self.frm_ilerleme = ctk.CTkFrame(self.form, fg_color="transparent")
        self.slider_ilerleme = ctk.CTkSlider(
            self.frm_ilerleme,
            from_=0,
            to=100,
            number_of_steps=20,
            command=self._slider_guncelle,
        )
        self.slider_ilerleme.set(0)
        self.slider_ilerleme.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.lbl_ilerleme_yuzde = ctk.CTkLabel(
            self.frm_ilerleme, text="%0", width=44, font=font(12, weight="bold")
        )
        self.lbl_ilerleme_yuzde.pack(side="right")

        # 8. Evrak / Kurum ve Dosya Eki (Evrak & Termin icin)
        self.lbl_kurum = ctk.CTkLabel(
            self.form, text="İlgili Kurum / Amir *", font=font(12, weight="bold"), anchor="w"
        )
        self.ent_kurum = ctk.CTkEntry(
            self.form, height=34, font=font(12), placeholder_text="Örn. İlçe Milli Eğitim Md., Okul Müdürü"
        )

        self.lbl_evrak_durum = ctk.CTkLabel(
            self.form, text="Evrak Durumu", font=font(12), anchor="w"
        )
        self.opt_evrak_durum = ctk.CTkOptionMenu(
            self.form, values=EVRAK_DURUMLARI, height=32, font=font(12)
        )

        self.lbl_dosya = ctk.CTkLabel(self.form, text="Dosya Eki", font=font(12), anchor="w")
        self.frm_dosya = ctk.CTkFrame(self.form, fg_color="transparent")
        self.ent_dosya = ctk.CTkEntry(
            self.frm_dosya, height=34, font=font(11), placeholder_text="Dosya seçilmedi"
        )
        self.ent_dosya.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(
            self.frm_dosya,
            text="Gözat...",
            width=70,
            height=34,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            command=self._dosya_sec,
        ).pack(side="right")

        # Amire Bilgi Verildi Checkbox
        self.cb_amire_bilgi = ctk.CTkCheckBox(
            self.form,
            text="Amire sözlü/yazılı bilgi verildi",
            font=font(12),
        )

    def _sablon_secildi(self, etiket: str) -> None:
        for s in OKUL_SABLONLARI:
            if s["etiket"] == etiket and s["baslik"]:
                self.tur_secici.set(s["tur"])
                self._tur_degisti(s["tur"])
                self.ent_baslik.delete(0, "end")
                self.ent_baslik.insert(0, s["baslik"])
                if s.get("kurum"):
                    self.ent_kurum.delete(0, "end")
                    self.ent_kurum.insert(0, s["kurum"])
                if s.get("sorumlu"):
                    self.ent_sorumlu.delete(0, "end")
                    self.ent_sorumlu.insert(0, s["sorumlu"])
                if s.get("aciklama"):
                    self.txt_aciklama.delete("1.0", "end")
                    self.txt_aciklama.insert("1.0", s["aciklama"])
                break

    def _slider_guncelle(self, val) -> None:
        self.lbl_ilerleme_yuzde.configure(text=f"%{int(val)}")

    def _dosya_sec(self) -> None:
        yol = dosya_penceresi.askopenfilename(title="Ek Dosyayı Seçin")
        if yol:
            self.ent_dosya.delete(0, "end")
            self.ent_dosya.insert(0, yol)

    def _tekrar_degisti(self) -> None:
        if self.opt_tekrar.get() == "Aylık":
            self.frm_aylik.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(2, 6))
        else:
            self.frm_aylik.grid_remove()

    def _tur_degisti(self, tur_adi: str) -> None:
        """Secilen ture gore dinamik form gridini temizler ve yeniden yerlestirir."""
        # Tum elemanlari grid'den kaldir
        for w in self.form.winfo_children():
            w.grid_remove()

        satir = 0

        if tur_adi == "Not":
            self.lbl_baslik.configure(text="Not Başlığı *")
            self.lbl_baslik.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.ent_baslik.grid(row=satir, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            satir += 1

            self.lbl_aciklama.configure(text="Not Açıklaması")
            self.lbl_aciklama.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.txt_aciklama.grid(row=satir, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            satir += 1

            self.lbl_tarih.configure(text="Tarih ve Saat *")
            self.lbl_tarih.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.secici.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(0, 8))
            satir += 1

            self.lbl_oncelik.grid(row=satir, column=0, sticky="w", pady=(2, 2), padx=(0, 6))
            self.lbl_kategori.grid(row=satir, column=1, sticky="w", pady=(2, 2), padx=(6, 0))
            satir += 1
            self.opt_oncelik.grid(row=satir, column=0, sticky="ew", pady=(0, 8), padx=(0, 6))
            self.opt_kategori.grid(row=satir, column=1, sticky="ew", pady=(0, 8), padx=(6, 0))
            satir += 1

            self.lbl_etiketler.grid(row=satir, column=0, sticky="w", pady=(2, 2), padx=(0, 6))
            self.lbl_tekrar.grid(row=satir, column=1, sticky="w", pady=(2, 2), padx=(6, 0))
            satir += 1
            self.ent_etiketler.grid(row=satir, column=0, sticky="ew", pady=(0, 8), padx=(0, 6))
            self.opt_tekrar.grid(row=satir, column=1, sticky="ew", pady=(0, 8), padx=(6, 0))
            satir += 1

            self._tekrar_degisti()

        elif tur_adi == "Görev":
            self.lbl_baslik.configure(text="Görev Adı *")
            self.lbl_baslik.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.ent_baslik.grid(row=satir, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            satir += 1

            self.lbl_aciklama.configure(text="Görev Detayı")
            self.lbl_aciklama.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.txt_aciklama.grid(row=satir, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            satir += 1

            self.lbl_tarih.configure(text="Son Tarih ve Saat *")
            self.lbl_tarih.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.secici.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(0, 8))
            satir += 1

            self.lbl_sorumlu.grid(row=satir, column=0, sticky="w", pady=(2, 2), padx=(0, 6))
            self.lbl_tekrar.grid(row=satir, column=1, sticky="w", pady=(2, 2), padx=(6, 0))
            satir += 1
            self.ent_sorumlu.grid(row=satir, column=0, sticky="ew", pady=(0, 8), padx=(0, 6))
            self.opt_tekrar.grid(row=satir, column=1, sticky="ew", pady=(0, 8), padx=(6, 0))
            satir += 1

            self.lbl_ilerleme.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.frm_ilerleme.grid(row=satir, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            satir += 1

            self._tekrar_degisti()

        elif tur_adi == "Evrak & Termin":
            self.lbl_baslik.configure(text="Evrak Adı / Konusu *")
            self.lbl_baslik.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.ent_baslik.grid(row=satir, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            satir += 1

            self.lbl_kurum.grid(row=satir, column=0, sticky="w", pady=(2, 2), padx=(0, 6))
            self.lbl_evrak_durum.grid(row=satir, column=1, sticky="w", pady=(2, 2), padx=(6, 0))
            satir += 1
            self.ent_kurum.grid(row=satir, column=0, sticky="ew", pady=(0, 8), padx=(0, 6))
            self.opt_evrak_durum.grid(row=satir, column=1, sticky="ew", pady=(0, 8), padx=(6, 0))
            satir += 1

            self.lbl_tarih.configure(text="Termin / Teslim Tarihi *")
            self.lbl_tarih.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.secici.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(0, 8))
            satir += 1

            self.lbl_dosya.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.frm_dosya.grid(row=satir, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            satir += 1

            self.lbl_aciklama.configure(text="Evrak Notu")
            self.lbl_aciklama.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(2, 2))
            satir += 1
            self.txt_aciklama.grid(row=satir, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            satir += 1

            self.cb_amire_bilgi.grid(
                row=satir, column=0, columnspan=2, sticky="w", pady=(6, 8)
            )

    def _duzenle_yukle(self, not_id: int) -> None:
        kayit = db.not_getir(not_id)
        if not kayit:
            return

        tur = kayit.get("tur") or "not"
        tur_etiket = {"not": "Not", "gorev": "Görev", "termin": "Evrak & Termin"}.get(
            tur, "Not"
        )
        self.tur_secici.set(tur_etiket)
        self._tur_degisti(tur_etiket)

        self.ent_baslik.delete(0, "end")
        self.ent_baslik.insert(0, kayit.get("baslik") or "")

        self.txt_aciklama.delete("1.0", "end")
        self.txt_aciklama.insert("1.0", kayit.get("aciklama") or "")

        zaman = reminder.not_zamani(kayit)
        if zaman:
            self.secici.ayarla(zaman)

        self.opt_oncelik.set(kayit.get("oncelik") or "Normal")
        self.opt_kategori.set(kayit.get("kategori") or "Genel")
        self.ent_etiketler.delete(0, "end")
        self.ent_etiketler.insert(0, kayit.get("etiketler") or "")

        self.opt_tekrar.set(
            reminder.TEKRAR_TERS.get(kayit.get("tekrar_tipi"), "Tek seferlik")
        )
        self._tekrar_degisti()

        # Gorev alanlari
        self.ent_sorumlu.delete(0, "end")
        self.ent_sorumlu.insert(0, kayit.get("sorumlu") or "")
        ilerleme = int(kayit.get("ilerleme") or 0)
        self.slider_ilerleme.set(ilerleme)
        self.lbl_ilerleme_yuzde.configure(text=f"%{ilerleme}")

        # Evrak alanlari
        self.ent_kurum.delete(0, "end")
        self.ent_kurum.insert(0, kayit.get("kurum_amir") or "")
        self.opt_evrak_durum.set(kayit.get("evrak_durum") or "Bekliyor")
        self.ent_dosya.delete(0, "end")
        self.ent_dosya.insert(0, kayit.get("dosya_eki") or "")
        if kayit.get("amire_bilgi_verildi"):
            self.cb_amire_bilgi.select()
        else:
            self.cb_amire_bilgi.deselect()

    def _kaydet(self) -> None:
        baslik = self.ent_baslik.get().strip()
        if not baslik:
            mesaj_kutusu.showwarning("Eksik Bilgi", "Lütfen bir başlık/evrak adı girin.")
            self.ent_baslik.focus_set()
            return

        zaman = self.secici.deger()
        if not zaman:
            mesaj_kutusu.showwarning("Eksik Bilgi", "Lütfen geçerli bir tarih ve saat seçin.")
            return

        tur_secim = self.tur_secici.get()
        tur_kod = {"Not": "not", "Görev": "gorev", "Evrak & Termin": "termin"}.get(
            tur_secim, "not"
        )

        aciklama = self.txt_aciklama.get("1.0", "end").strip()
        tarih_metni = zaman.strftime("%Y-%m-%d %H:%M:%S")

        veri = {
            "baslik": baslik,
            "aciklama": aciklama,
            "tarih_saat": tarih_metni,
            "tur": tur_kod,
        }

        if tur_kod == "not":
            veri["oncelik"] = self.opt_oncelik.get()
            veri["kategori"] = self.opt_kategori.get()
            veri["etiketler"] = self.ent_etiketler.get().strip()
            veri["tekrar_tipi"] = reminder.TEKRAR_TIPLERI.get(
                self.opt_tekrar.get(), "tek"
            )
            if veri["tekrar_tipi"] == "aylik":
                sec = self.opt_aylik.get()
                veri["ay_kural"] = reminder.AYLIK_KURALLAR.get(sec, "liste")
                veri["ay_gun_listesi"] = self.ent_ay_gunleri.get().strip()

        elif tur_kod == "gorev":
            veri["sorumlu"] = self.ent_sorumlu.get().strip()
            ilerleme = int(self.slider_ilerleme.get())
            veri["ilerleme"] = ilerleme
            veri["durum"] = (
                "tamamlandi"
                if ilerleme == 100
                else ("devam" if ilerleme > 0 else "bekliyor")
            )
            veri["tekrar_tipi"] = reminder.TEKRAR_TIPLERI.get(
                self.opt_tekrar.get(), "tek"
            )

        elif tur_kod == "termin":
            kurum = self.ent_kurum.get().strip()
            if not kurum:
                mesaj_kutusu.showwarning(
                    "Eksik Bilgi", "Lütfen ilgili kurum veya amir bilgisini girin."
                )
                self.ent_kurum.focus_set()
                return
            veri["kurum_amir"] = kurum
            veri["evrak_durum"] = self.opt_evrak_durum.get()
            veri["dosya_eki"] = self.ent_dosya.get().strip()
            veri["amire_bilgi_verildi"] = 1 if self.cb_amire_bilgi.get() == 1 else 0
            if veri["amire_bilgi_verildi"]:
                veri["amire_bilgi_zamani"] = db.zaman_damgasi()
            veri["kategori"] = "Okul"
            veri["oncelik"] = "Önemli"

        try:
            if self.duzenlenen_id:
                db.not_guncelle(self.duzenlenen_id, veri, zaman_degisti=True)
                db.uyari_kaydet(
                    self.duzenlenen_id, baslik, "güncellendi", f"Tür: {tur_secim}"
                )
            else:
                yeni_id = db.not_ekle(veri)
                db.uyari_kaydet(yeni_id, baslik, "oluşturuldu", f"Tür: {tur_secim}")

            self.uygulama.arayuzu_yenile()
            self.destroy()
        except Exception as hata:
            mesaj_kutusu.showerror("Hata", f"Kayıt işlemi başarısız:\n{hata}")
