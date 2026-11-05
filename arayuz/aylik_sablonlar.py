"""Aylik gorev sablonlari: kural tabanli tekrarlayan gorev tanimlari.

db.py'deki `monthly_task_rules` altyapisini (kural_ekle / kurallar /
kural_getir / kural_guncelle / kural_sil) kullanan yonetim arayuzu. Her sablon
bir kural tipi ve parametreleriyle, o ayin hangi gunlerinde gorev olacagini
tanimlar. Sablonlar Ayarlar sayfasindaki karttan eklenip duzenlenir; her ay
icin planlanan gunler otomatik hesaplanip gosterilir.
"""
from __future__ import annotations

import calendar
import datetime
import tkinter.messagebox as mesaj_kutusu

import customtkinter as ctk

import db
import reminder
from arayuz.tema import TEMA_RENKLERI, font
from arayuz.widgetlar import SayiSecici, onay_iste, rozet

# Kural tipi -> (etiket, parametre anahtari, varsayilan deger) listesi.
# Anahtarlar db.AYLIK_KURAL_TIPLERI ile birebir eslesir.
KURAL_PARAMETRELERI: dict[str, tuple[tuple[str, str, int], ...]] = {
    "first_calendar_days": (("İlk kaç gün", "days", 7),),
    "last_calendar_days": (("Son kaç gün", "days", 3),),
    "day_range": (("Başlangıç günü", "start_day", 1), ("Bitiş günü", "end_day", 5)),
    "nth_workday": (("Kaçıncı iş günü", "n", 3),),
    "last_workday": (),
    "last_n_workdays": (("Son kaç iş günü", "n", 2),),
}

# Kural tipi -> arayuzde gosterilecek ad (db.AYLIK_KURAL_TIPLERI degerleri).
KURAL_ADLARI = dict(db.AYLIK_KURAL_TIPLERI)
_AD_TERS = {ad: tip for tip, ad in KURAL_ADLARI.items()}


def _sayi(params: dict, anahtar: str, varsayilan: int) -> int:
    try:
        return int((params or {}).get(anahtar, varsayilan))
    except (TypeError, ValueError):
        return varsayilan


def kural_gunleri(rule_type: str, params: dict, yil: int, ay: int) -> list[int]:
    """Sablonun ilgili ayda planlanan gun numaralarini dondurur."""
    son = calendar.monthrange(yil, ay)[1]
    if rule_type == "first_calendar_days":
        n = max(1, min(31, _sayi(params, "days", 7)))
        return list(range(1, min(n, son) + 1))
    if rule_type == "last_calendar_days":
        n = max(1, min(31, _sayi(params, "days", 3)))
        return list(range(max(1, son - n + 1), son + 1))
    if rule_type == "day_range":
        bas = max(1, min(31, _sayi(params, "start_day", 1)))
        bit = max(bas, min(31, _sayi(params, "end_day", 5)))
        if bas > son:
            return []
        return list(range(bas, min(bit, son) + 1))
    is_gunleri = [
        gun for gun in range(1, son + 1) if datetime.date(yil, ay, gun).weekday() < 5
    ]
    if not is_gunleri:
        return []
    if rule_type == "nth_workday":
        n = max(1, _sayi(params, "n", 3))
        return [is_gunleri[n - 1]] if len(is_gunleri) >= n else []
    if rule_type == "last_workday":
        return [is_gunleri[-1]]
    if rule_type == "last_n_workdays":
        n = max(1, _sayi(params, "n", 2))
        return is_gunleri[-n:]
    return []


def kural_metni(rule_type: str, params: dict) -> str:
    """Sablon kuralini okunabilir Turkce metne cevirir."""
    if rule_type == "first_calendar_days":
        return f"Ayın ilk {_sayi(params, 'days', 7)} takvim günü"
    if rule_type == "last_calendar_days":
        return f"Ayın son {_sayi(params, 'days', 3)} takvim günü"
    if rule_type == "day_range":
        return f"Ayın {_sayi(params, 'start_day', 1)}-{_sayi(params, 'end_day', 5)} günleri"
    if rule_type == "nth_workday":
        return f"Ayın {_sayi(params, 'n', 3)}. iş günü"
    if rule_type == "last_workday":
        return "Ayın son iş günü"
    if rule_type == "last_n_workdays":
        return f"Ayın son {_sayi(params, 'n', 2)} iş günü"
    return KURAL_ADLARI.get(rule_type, rule_type)


def _gun_metni(gunler: list[int]) -> str:
    return ", ".join(str(gun) for gun in gunler) if gunler else "—"


def bu_ayki_gunler(rule_type: str, params: dict) -> list[int]:
    bugun = datetime.date.today()
    return kural_gunleri(rule_type, params, bugun.year, bugun.month)


class SablonDialog(ctk.CTkToplevel):
    """Aylik gorev sablonu ekleme / duzenleme penceresi."""

    def __init__(self, pencere, kural_id: int | None = None, kaydedildi=None):
        super().__init__(pencere)
        self.pencere = pencere
        self.kural_id = kural_id
        self.kaydedildi = kaydedildi
        self.param_girisleri: dict[str, ctk.CTkEntry] = {}

        self.title("Şablon Düzenle" if kural_id else "Yeni Aylık Görev Şablonu")
        self.geometry("600x620")
        self.minsize(540, 560)
        self.transient(pencere)
        self.grab_set()
        self.configure(fg_color=TEMA_RENKLERI["bg_ana"])

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self._bilesenleri_olustur()
        self._yukle()
        self.after_idle(self._onizleme_guncelle)

    # ------------------------------------------------------------- arayuz
    def _etiket(self, satir: int, metin: str) -> None:
        ctk.CTkLabel(
            self,
            text=metin,
            font=font(12, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        ).grid(row=satir, column=0, sticky="nw", padx=(20, 10), pady=(10, 0))

    def _bilesenleri_olustur(self) -> None:
        self._etiket(0, "Başlık *")
        self.ent_baslik = ctk.CTkEntry(
            self, height=36, font=font(12), placeholder_text="Örn. Aylık Ek Ders Puantajı"
        )
        self.ent_baslik.grid(row=0, column=1, sticky="ew", padx=(0, 20), pady=(10, 0))

        self._etiket(1, "Açıklama")
        self.txt_aciklama = ctk.CTkTextbox(self, height=72, font=font(12))
        self.txt_aciklama.grid(row=1, column=1, sticky="ew", padx=(0, 20), pady=(10, 0))

        self._etiket(2, "Kural Tipi")
        self.opt_kural = ctk.CTkOptionMenu(
            self,
            values=list(KURAL_ADLARI.values()),
            height=34,
            font=font(12),
            command=lambda _: self._parametreleri_ciz(),
        )
        self.opt_kural.grid(row=2, column=1, sticky="w", padx=(0, 20), pady=(10, 0))
        self.opt_kural.set(list(KURAL_ADLARI.values())[0])

        self._etiket(3, "Kural Değerleri")
        self.frm_parametre = ctk.CTkFrame(
            self, fg_color=TEMA_RENKLERI["bg_kart_ic"], corner_radius=6
        )
        self.frm_parametre.grid(row=3, column=1, sticky="ew", padx=(0, 20), pady=(10, 0))

        self._etiket(4, "Hatırlatma Saati")
        saat_kutu = ctk.CTkFrame(self, fg_color="transparent")
        saat_kutu.grid(row=4, column=1, sticky="w", padx=(0, 20), pady=(10, 0))
        self.saat = SayiSecici(saat_kutu, 24)
        self.saat.pack(side="left")
        ctk.CTkLabel(
            saat_kutu, text=":", font=font(14, weight="bold"), text_color=TEMA_RENKLERI["metin_ana"]
        ).pack(side="left", padx=4)
        self.dakika = SayiSecici(saat_kutu, 60)
        self.dakika.pack(side="left")
        self.saat.set(9)
        self.dakika.set(0)

        self.sw_aktif = ctk.CTkSwitch(
            self, text="Şablon aktif (her ay hatırlatılır)", font=font(12)
        )
        self.sw_aktif.grid(row=5, column=1, sticky="w", padx=(0, 20), pady=(14, 0))
        self.sw_aktif.select()

        self.lbl_onizleme = ctk.CTkLabel(
            self,
            text="",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
            justify="left",
            wraplength=380,
        )
        self.lbl_onizleme.grid(row=6, column=1, sticky="nw", padx=(0, 20), pady=(10, 0))

        alt = ctk.CTkFrame(self, fg_color=TEMA_RENKLERI["bg_kart"], height=60)
        alt.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        alt.grid_propagate(False)

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
        ).pack(side="right", padx=(6, 20), pady=12)

        ctk.CTkButton(
            alt,
            text="Güncelle" if self.kural_id else "Kaydet",
            width=120,
            height=36,
            font=font(12, weight="bold"),
            fg_color=TEMA_RENKLERI["btn_primary"],
            hover_color=TEMA_RENKLERI["btn_primary_hover"],
            command=self._kaydet,
        ).pack(side="right", padx=6, pady=12)

        self._parametreleri_ciz()

    def _parametreleri_ciz(self) -> None:
        """Secili kural tipine gore parametre giris alanlarini uretir."""
        for cocuk in self.frm_parametre.winfo_children():
            cocuk.destroy()
        self.param_girisleri = {}

        tip = _AD_TERS.get(self.opt_kural.get(), "first_calendar_days")
        tanimlar = KURAL_PARAMETRELERI.get(tip, ())
        if not tanimlar:
            ctk.CTkLabel(
                self.frm_parametre,
                text="Bu kural için ek değer gerekmez.",
                font=font(11),
                text_color=TEMA_RENKLERI["metin_soluk"],
            ).pack(side="left", padx=12, pady=10)
            self._onizleme_guncelle()
            return

        for etiket, anahtar, varsayilan in tanimlar:
            kutu = ctk.CTkFrame(self.frm_parametre, fg_color="transparent")
            kutu.pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(
                kutu,
                text=etiket,
                font=font(11),
                text_color=TEMA_RENKLERI["metin_ikincil"],
            ).pack(anchor="w")
            giris = ctk.CTkEntry(kutu, width=90, height=30, font=font(12), justify="center")
            giris.insert(0, str(varsayilan))
            giris.pack()
            giris.bind("<KeyRelease>", lambda _e: self._onizleme_guncelle())
            self.param_girisleri[anahtar] = giris

        self._onizleme_guncelle()

    def _params_oku(self) -> dict:
        sonuc: dict[str, int] = {}
        for anahtar, giris in self.param_girisleri.items():
            try:
                sonuc[anahtar] = int(str(giris.get()).strip())
            except (TypeError, ValueError):
                continue
        return sonuc

    def _onizleme_guncelle(self, _olay=None) -> None:
        try:
            tip = _AD_TERS.get(self.opt_kural.get(), "first_calendar_days")
            gunler = bu_ayki_gunler(tip, self._params_oku())
            bugun = datetime.date.today()
            self.lbl_onizleme.configure(
                text=(
                    f"{reminder.AY_ADLARI[bugun.month - 1]} {bugun.year} için planlanan günler: "
                    f"{_gun_metni(gunler)}"
                )
            )
        except Exception:
            pass

    # ------------------------------------------------------------- veri
    def _yukle(self) -> None:
        if not self.kural_id:
            return
        kural = db.kural_getir(self.kural_id)
        if not kural:
            return
        self.ent_baslik.delete(0, "end")
        self.ent_baslik.insert(0, kural.get("title") or "")
        self.txt_aciklama.delete("1.0", "end")
        self.txt_aciklama.insert("1.0", kural.get("description") or "")

        ad = KURAL_ADLARI.get(kural.get("rule_type"))
        if ad:
            self.opt_kural.set(ad)
            self._parametreleri_ciz()
        params = kural.get("rule_params") or {}
        for anahtar, giris in self.param_girisleri.items():
            if anahtar in params:
                giris.delete(0, "end")
                giris.insert(0, str(params[anahtar]))

        saat, dakika = self._zaman_ayristir(kural.get("reminder_time"))
        self.saat.set(saat)
        self.dakika.set(dakika)
        if kural.get("active"):
            self.sw_aktif.select()
        else:
            self.sw_aktif.deselect()
        self._onizleme_guncelle()

    @staticmethod
    def _zaman_ayristir(metin) -> tuple[int, int]:
        parcalar = str(metin or "09:00").split(":")
        try:
            saat = int(parcalar[0])
        except (ValueError, IndexError):
            saat = 9
        try:
            dakika = int(parcalar[1])
        except (ValueError, IndexError):
            dakika = 0
        return max(0, min(23, saat)), max(0, min(59, dakika))

    def _kaydet(self) -> None:
        baslik = self.ent_baslik.get().strip()
        if not baslik:
            mesaj_kutusu.showwarning("Eksik Bilgi", "Lütfen şablon başlığını girin.")
            return

        tip = _AD_TERS.get(self.opt_kural.get(), "first_calendar_days")
        params = self._params_oku()
        hatirlatma = f"{int(self.saat.get()):02d}:{int(self.dakika.get()):02d}"
        aciklama = self.txt_aciklama.get("1.0", "end").strip()
        aktif = self.sw_aktif.get() == 1

        if self.kural_id:
            db.kural_guncelle(
                self.kural_id,
                title=baslik,
                description=aciklama,
                rule_type=tip,
                rule_params=params,
                reminder_time=hatirlatma,
                active=aktif,
            )
        else:
            db.kural_ekle(
                baslik, tip, params, hatirlatma, description=aciklama, active=aktif
            )

        if self.kaydedildi is not None:
            self.kaydedildi()
        self.destroy()


class AylikSablonKarti(ctk.CTkFrame):
    """Ayarlar sayfasinda aylik gorev sablonlarini listeleyen ve yoneten kart."""

    def __init__(self, parent, pencere):
        super().__init__(parent, fg_color="transparent")
        self.pencere = pencere

        ust = ctk.CTkFrame(self, fg_color="transparent")
        ust.pack(fill="x", pady=(0, 6))

        ctk.CTkButton(
            ust,
            text="+ Yeni Şablon",
            width=130,
            height=32,
            font=font(11, weight="bold"),
            fg_color=TEMA_RENKLERI["btn_primary"],
            hover_color=TEMA_RENKLERI["btn_primary_hover"],
            command=self._yeni,
        ).pack(side="right")

        self.lbl_sayac = ctk.CTkLabel(
            ust,
            text="",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
            anchor="w",
        )
        self.lbl_sayac.pack(side="left")

        self.liste = ctk.CTkFrame(self, fg_color="transparent")
        self.liste.pack(fill="x")

        self.yenile()

    # ------------------------------------------------------------- cizim
    def yenile(self) -> None:
        for cocuk in self.liste.winfo_children():
            cocuk.destroy()

        sablonlar = db.kurallar()
        aktif_sayi = sum(1 for s in sablonlar if s.get("active"))
        self.lbl_sayac.configure(
            text=(
                f"{len(sablonlar)} şablon tanımlı ({aktif_sayi} aktif). "
                "Her ay için planlanan günler otomatik hesaplanır."
            )
        )

        if not sablonlar:
            ctk.CTkLabel(
                self.liste,
                text=(
                    'Henüz şablon eklenmemiş. "+ Yeni Şablon" ile aylık tekrarlayan '
                    "görevler tanımlayabilirsiniz."
                ),
                font=font(11),
                text_color=TEMA_RENKLERI["metin_soluk"],
                justify="left",
                wraplength=760,
            ).pack(anchor="w", pady=8)
            return

        for sablon in sablonlar:
            self._satir_ciz(sablon)

    def _satir_ciz(self, sablon: dict) -> None:
        aktif = bool(sablon.get("active"))
        kayit = ctk.CTkFrame(
            self.liste,
            fg_color=TEMA_RENKLERI["bg_kart_ic"],
            corner_radius=6,
            border_width=1,
            border_color=TEMA_RENKLERI["kenarlik"],
        )
        kayit.pack(fill="x", pady=3)
        kayit.grid_columnconfigure(1, weight=1)

        ctk.CTkFrame(
            kayit,
            width=5,
            corner_radius=3,
            fg_color=TEMA_RENKLERI["durum_tamamlandi"]
            if aktif
            else TEMA_RENKLERI["metin_soluk"],
        ).grid(row=0, column=0, rowspan=2, sticky="ns", padx=(6, 10), pady=8)

        ust = ctk.CTkFrame(kayit, fg_color="transparent")
        ust.grid(row=0, column=1, sticky="ew", pady=(8, 0))
        ctk.CTkLabel(
            ust,
            text=sablon.get("title") or "(başlıksız)",
            font=font(13, weight="bold"),
            text_color=TEMA_RENKLERI["metin_ana"],
            anchor="w",
        ).pack(side="left")
        if not aktif:
            rozet(ust, "Pasif", TEMA_RENKLERI["metin_soluk"]).pack(side="left", padx=6)

        alt = ctk.CTkFrame(kayit, fg_color="transparent")
        alt.grid(row=1, column=1, sticky="ew", pady=(2, 8))

        kural = kural_metni(sablon.get("rule_type"), sablon.get("rule_params") or {})
        gunler = bu_ayki_gunler(sablon.get("rule_type"), sablon.get("rule_params") or {})
        ctk.CTkLabel(
            alt,
            text=f"🔁 {kural}   •   🔔 {sablon.get('reminder_time') or '09:00'}",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_ikincil"],
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            alt,
            text=f"Bu ay planlanan günler: {_gun_metni(gunler)}",
            font=font(11),
            text_color=TEMA_RENKLERI["metin_soluk"],
            anchor="w",
            wraplength=620,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        aciklama = (sablon.get("description") or "").strip()
        if aciklama:
            ctk.CTkLabel(
                alt,
                text=aciklama,
                font=font(11),
                text_color=TEMA_RENKLERI["metin_soluk"],
                anchor="w",
                wraplength=620,
                justify="left",
            ).pack(anchor="w", pady=(2, 0))

        kutu = ctk.CTkFrame(kayit, fg_color="transparent")
        kutu.grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 12), pady=8)

        sw = ctk.CTkSwitch(
            kutu,
            text="Aktif",
            font=font(11),
            command=lambda: self._aktif_degistir(sablon["id"], sw.get() == 1),
        )
        sw.pack(side="left", padx=(0, 8))
        if aktif:
            sw.select()

        ctk.CTkButton(
            kutu,
            text="Düzenle",
            width=76,
            height=30,
            font=font(11),
            fg_color=TEMA_RENKLERI["btn_notr"],
            text_color=TEMA_RENKLERI["btn_notr_metin"],
            hover_color=TEMA_RENKLERI["btn_notr_hover"],
            command=lambda: self._duzenle(sablon["id"]),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            kutu,
            text="Sil",
            width=54,
            height=30,
            font=font(11),
            fg_color="transparent",
            text_color=TEMA_RENKLERI["durum_geciken"],
            hover_color=("#FEE2E2", "#450A0A"),
            command=lambda: self._sil(sablon),
        ).pack(side="left", padx=2)

    # ------------------------------------------------------------- islemler
    def _yeni(self) -> None:
        SablonDialog(self.pencere, kaydedildi=self.yenile)

    def _duzenle(self, kural_id: int) -> None:
        SablonDialog(self.pencere, kural_id=kural_id, kaydedildi=self.yenile)

    def _aktif_degistir(self, kural_id: int, aktif: bool) -> None:
        db.kural_guncelle(kural_id, active=aktif)
        self.yenile()

    def _sil(self, sablon: dict) -> None:
        baslik = sablon.get("title") or "şablon"
        if onay_iste("Şablonu Sil", f'"{baslik}" şablonu silinecek. Onaylıyor musunuz?'):
            db.kural_sil(sablon["id"])
            self.yenile()
