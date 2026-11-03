"""Yeni Not / not ekleme ve duzenleme sekmesi."""
from __future__ import annotations

import datetime
import tkinter.messagebox as mesaj_kutusu

import customtkinter as ctk

import db
import reminder
from arayuz.widgetlar import TarihSaatSecici


class YeniNotSekmesi(ctk.CTkFrame):
    def __init__(self, parent, pencere):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere
        self.uygulama = pencere.uygulama
        self.duzenlenen_id: int | None = None

        self.grid_columnconfigure(1, weight=1)

        satir = 0

        self.baslik = self._satir(
            satir, "Not başlığı", ctk.CTkEntry(self, placeholder_text="Örn. Matematik ödevi")
        )
        satir += 1

        ctk.CTkLabel(self, text="Not açıklaması").grid(
            row=satir, column=0, sticky="nw", padx=10, pady=6
        )
        self.aciklama = ctk.CTkTextbox(self, height=90)
        self.aciklama.grid(row=satir, column=1, sticky="ew", padx=10, pady=6)
        satir += 1

        ctk.CTkLabel(self, text="Tarih ve saat").grid(
            row=satir, column=0, sticky="nw", padx=10, pady=6
        )
        self.secici = TarihSaatSecici(self)
        self.secici.grid(row=satir, column=1, sticky="w", padx=10, pady=6)
        satir += 1

        ctk.CTkLabel(self, text="Öncelik").grid(row=satir, column=0, sticky="w", padx=10, pady=6)
        self.oncelik = ctk.CTkOptionMenu(
            self,
            values=reminder.ONCELIKLER,
            width=180,
            fg_color=reminder.ONCELIK_RENK["Normal"],
        )
        self.oncelik.grid(row=satir, column=1, sticky="w", padx=10, pady=6)
        self.oncelik.configure(command=lambda secim: self.oncelik.configure(
            fg_color=reminder.ONCELIK_RENK.get(secim, "#2980b9")
        ))
        satir += 1

        ctk.CTkLabel(self, text="Kategori").grid(row=satir, column=0, sticky="w", padx=10, pady=6)
        self.kategori = ctk.CTkOptionMenu(self, values=reminder.KATEGORILER, width=180)
        self.kategori.grid(row=satir, column=1, sticky="w", padx=10, pady=6)
        satir += 1

        self.etiketler = self._satir(
            satir,
            "Etiketler (virgülle ayırın)",
            ctk.CTkEntry(self, placeholder_text="Örn. ödev, matematik"),
        )
        satir += 1

        ctk.CTkLabel(self, text="Tekrar").grid(row=satir, column=0, sticky="w", padx=10, pady=6)
        self.tekrar = ctk.CTkOptionMenu(
            self,
            values=list(reminder.TEKRAR_TIPLERI.keys()),
            width=180,
            command=lambda _: self._tekrar_degisti(),
        )
        self.tekrar.grid(row=satir, column=1, sticky="w", padx=10, pady=6)
        satir += 1

        self.aylik_cercevesi = ctk.CTkFrame(self)
        self.aylik_cercevesi.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.aylik_cercevesi, text="Aylık kural").grid(
            row=0, column=0, sticky="w", padx=10, pady=(8, 4)
        )
        self.aylik_secim = ctk.CTkOptionMenu(
            self.aylik_cercevesi,
            values=reminder.AYLIK_SECENEKLER,
            width=240,
            command=lambda _: self._aylik_kural_degisti(),
        )
        self.aylik_secim.grid(row=0, column=1, sticky="w", padx=10, pady=(8, 4))

        self.liste_kutusu = ctk.CTkFrame(self.aylik_cercevesi, fg_color="transparent")
        self.liste_kutusu.grid(row=1, column=0, columnspan=3, sticky="ew")
        ctk.CTkLabel(
            self.liste_kutusu, text="Günler (virgülle ayırın)", width=200, anchor="w"
        ).pack(side="left", padx=10, pady=4)
        self.ay_gunleri = ctk.CTkEntry(
            self.liste_kutusu, placeholder_text="Örn. 1, 5, 15", width=240
        )
        self.ay_gunleri.pack(side="left", padx=10, pady=4)

        self.aralik_kutusu = ctk.CTkFrame(self.aylik_cercevesi, fg_color="transparent")
        self.aralik_kutusu.grid(row=2, column=0, columnspan=3, sticky="ew")
        ctk.CTkLabel(self.aralik_kutusu, text="Başlangıç günü", width=140, anchor="w").pack(
            side="left", padx=10, pady=4
        )
        self.bas_gun = ctk.CTkOptionMenu(
            self.aralik_kutusu, values=[str(i) for i in range(1, 32)], width=80
        )
        self.bas_gun.pack(side="left", padx=(0, 24), pady=4)
        ctk.CTkLabel(self.aralik_kutusu, text="Bitiş günü", width=100, anchor="w").pack(
            side="left", padx=(0, 4), pady=4
        )
        self.bit_gun = ctk.CTkOptionMenu(
            self.aralik_kutusu, values=[str(i) for i in range(1, 32)], width=80
        )
        self.bit_gun.pack(side="left", pady=4)

        ctk.CTkLabel(
            self.aylik_cercevesi,
            text=(
                "Aylık görev her ay tekrarlanır. Gün listesi boş bırakılırsa notun tarihindeki "
                "gün kullanılır. 'Yapıldı' işaretlediğiniz ay susar, ertesi ay yeniden başlar."
            ),
            wraplength=620,
            justify="left",
            text_color=("#57606f", "#a4b0be"),
            font=ctk.CTkFont(size=11),
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 8))
        self.bas_gun.set("1")
        self.bit_gun.set("5")
        self.aylik_secim.set("Gün listesi")
        self._aylik_kural_degisti()
        satir += 1

        ctk.CTkLabel(self, text="Bildirim öncesi hatırlatma").grid(
            row=satir, column=0, sticky="w", padx=10, pady=6
        )
        self.hatirlatma = ctk.CTkOptionMenu(
            self, values=list(reminder.HATIRLATMA_SECENEKLERI.keys()), width=180
        )
        self.hatirlatma.grid(row=satir, column=1, sticky="w", padx=10, pady=6)
        satir += 1

        dugmeler = ctk.CTkFrame(self, fg_color="transparent")
        dugmeler.grid(row=satir, column=0, columnspan=2, sticky="w", padx=10, pady=(14, 4))
        self.kaydet_dugmesi = ctk.CTkButton(
            dugmeler, text="Not Ekle", width=140, height=36, command=self.kaydet
        )
        self.kaydet_dugmesi.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            dugmeler,
            text="Formu Temizle",
            width=130,
            height=36,
            fg_color="#7f8c8d",
            hover_color="#5d6d7e",
            command=self.temizle,
        ).pack(side="left", padx=8)
        self.sil_dugmesi = ctk.CTkButton(
            dugmeler,
            text="Notu Sil",
            width=110,
            height=36,
            fg_color="#c0392b",
            hover_color="#96281b",
            command=self.sil,
            state="disabled",
        )
        self.sil_dugmesi.pack(side="left", padx=8)
        satir += 1

        self.durum = ctk.CTkLabel(
            self,
            text="",
            anchor="w",
            justify="left",
            text_color="#27ae60",
            wraplength=760,
        )
        self.durum.grid(row=satir, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 12))

        self._tekrar_degisti()
        self.varsayilanlari_uygula()

    # ------------------------------------------------------------- yardimcilar
    def _satir(self, satir: int, etiket: str, bilesen):
        ctk.CTkLabel(self, text=etiket).grid(row=satir, column=0, sticky="w", padx=10, pady=6)
        bilesen.grid(row=satir, column=1, sticky="ew", padx=10, pady=6)
        return bilesen

    def varsayilanlari_uygula(self) -> None:
        self.oncelik.set(db.ayar_al("varsayilan_oncelik", "Normal"))
        self.oncelik.configure(fg_color=reminder.ONCELIK_RENK.get(self.oncelik.get(), "#2980b9"))
        self.kategori.set(db.ayar_al("varsayilan_kategori", "Genel"))
        self.hatirlatma.set(db.ayar_al("varsayilan_hatirlatma", "Zamanında"))
        self.secici.ayarla(datetime.datetime.now() + datetime.timedelta(minutes=30))

    def _tekrar_degisti(self) -> None:
        if self.tekrar.get() == "Aylık":
            self.aylik_cercevesi.grid(
                row=7, column=0, columnspan=2, sticky="ew", padx=10, pady=6
            )
        else:
            self.aylik_cercevesi.grid_remove()

    def _aylik_kural_degisti(self) -> None:
        secim = self.aylik_secim.get()
        if secim == "Gün listesi":
            self.liste_kutusu.grid()
            self.aralik_kutusu.grid_remove()
        elif secim == "Gün aralığı":
            self.liste_kutusu.grid_remove()
            self.aralik_kutusu.grid()
        else:
            self.liste_kutusu.grid_remove()
            self.aralik_kutusu.grid_remove()

    # ------------------------------------------------------------- islemler
    def duzenlemeye_al(self, not_id: int) -> None:
        kayit = db.not_getir(not_id)
        if kayit is None:
            return
        self.duzenlenen_id = not_id
        self.baslik.delete(0, "end")
        self.baslik.insert(0, kayit.get("baslik", ""))
        self.aciklama.delete("1.0", "end")
        self.aciklama.insert("1.0", kayit.get("aciklama") or "")
        zaman = reminder.not_zamani(kayit)
        if zaman:
            self.secici.ayarla(zaman)
        self.oncelik.set(kayit.get("oncelik") or "Normal")
        self.oncelik.configure(fg_color=reminder.ONCELIK_RENK.get(self.oncelik.get(), "#2980b9"))
        self.kategori.set(kayit.get("kategori") or "Genel")
        self.etiketler.delete(0, "end")
        self.etiketler.insert(0, kayit.get("etiketler") or "")
        self.tekrar.set(reminder.TEKRAR_TERS.get(kayit.get("tekrar_tipi"), "Tek seferlik"))
        kural = (kayit.get("ay_kural") or "").strip()
        liste = reminder.aylik_gun_listesi(kayit)
        aralik = reminder.aylik_aralik(kayit)
        if kural and kural != "liste" and kural in reminder.AYLIK_KURAL_TERS:
            self.aylik_secim.set(reminder.AYLIK_KURAL_TERS[kural])
        elif aralik and not liste:
            self.aylik_secim.set("Gün aralığı")
        else:
            self.aylik_secim.set("Gün listesi")
        self.ay_gunleri.delete(0, "end")
        if liste:
            self.ay_gunleri.insert(0, ", ".join(str(gun) for gun in liste))
        if aralik:
            self.bas_gun.set(str(aralik[0]))
            self.bit_gun.set(str(aralik[1]))
        self._aylik_kural_degisti()
        self.hatirlatma.set(reminder.hatirlatma_metni(kayit.get("hatirlatma_once_dk")))
        self._tekrar_degisti()
        self.kaydet_dugmesi.configure(text="Güncelle")
        self.sil_dugmesi.configure(state="normal")
        self.durum.configure(text=f"Düzenleniyor: #{not_id} - {kayit.get('baslik', '')}")

    def temizle(self) -> None:
        self.duzenlenen_id = None
        self.baslik.delete(0, "end")
        self.aciklama.delete("1.0", "end")
        self.etiketler.delete(0, "end")
        self.tekrar.set("Tek seferlik")
        self.aylik_secim.set("Gün listesi")
        self.ay_gunleri.delete(0, "end")
        self._tekrar_degisti()
        self.kaydet_dugmesi.configure(text="Not Ekle")
        self.sil_dugmesi.configure(state="disabled")
        self.durum.configure(text="")
        self.varsayilanlari_uygula()

    def sil(self) -> None:
        if self.duzenlenen_id is None:
            return
        if mesaj_kutusu.askyesno(
            "Notu sil", "Not geri dönüşüm kutusuna taşınacak. Onaylıyor musunuz?"
        ):
            kimlik = self.duzenlenen_id
            self.temizle()
            self.uygulama.cop_kutusuna_at(kimlik)

    def kaydet(self) -> None:
        baslik = self.baslik.get().strip()
        if not baslik:
            mesaj_kutusu.showwarning("Eksik bilgi", "Lütfen not başlığı girin.")
            self.baslik.focus_set()
            return

        zaman = self.secici.deger()
        if zaman is None:
            mesaj_kutusu.showwarning(
                "Geçersiz tarih",
                "Seçilen tarih ve saat geçerli değil. Gün/ay/yıl değerlerini kontrol edin.",
            )
            return

        tekrar_kodu = reminder.TEKRAR_TIPLERI.get(self.tekrar.get(), "tek")
        bas_gun = bit_gun = None
        ay_gun_listesi = None
        ay_kural = None
        if tekrar_kodu == "aylik":
            secim = self.aylik_secim.get()
            if secim == "Gün listesi":
                gunler = reminder.gun_listesi_ayristir(self.ay_gunleri.get())
                if gunler:
                    ay_gun_listesi = ",".join(str(gun) for gun in gunler)
                ay_kural = "liste"
            elif secim == "Gün aralığı":
                bas_gun = int(self.bas_gun.get())
                bit_gun = int(self.bit_gun.get())
                if bit_gun < bas_gun:
                    mesaj_kutusu.showwarning(
                        "Geçersiz aralık",
                        "Aylık aralıkta bitiş günü, başlangıç gününden küçük olamaz.",
                    )
                    return
            else:
                ay_kural = reminder.AYLIK_KURALLAR.get(secim)

        veri = {
            "baslik": baslik,
            "aciklama": self.aciklama.get("1.0", "end").strip(),
            "kategori": self.kategori.get(),
            "oncelik": self.oncelik.get(),
            "etiketler": self.etiketler.get().strip(),
            "tarih_saat": zaman.strftime("%Y-%m-%d %H:%M"),
            "tekrar_tipi": tekrar_kodu,
            "ay_baslangic_gun": bas_gun,
            "ay_bitis_gun": bit_gun,
            "ay_gun_listesi": ay_gun_listesi,
            "ay_kural": ay_kural,
            "hatirlatma_once_dk": reminder.HATIRLATMA_SECENEKLERI.get(self.hatirlatma.get(), 0),
        }

        if self.duzenlenen_id is None:
            yeni_kimlik = db.not_ekle(veri)
            mesaj = f"Not eklendi (#{yeni_kimlik}). Uyarı zamanı: {reminder.zaman_metni(zaman)}"
        else:
            db.not_guncelle(self.duzenlenen_id, veri, zaman_degisti=True)
            mesaj = f"Not güncellendi (#{self.duzenlenen_id}). Uyarı zamanı: {reminder.zaman_metni(zaman)}"

        self.temizle()
        self.durum.configure(text=mesaj)
        self.uygulama.yenile()
