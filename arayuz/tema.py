"""Tasarim sistemi, renk paletleri ve tipografi tanimlari.

Modern, kurumsal, temiz ve katmanli Windows 10/11 arayuzu icin renk ve stil sabitleri.
"""
from __future__ import annotations

import customtkinter as ctk

# ------------------------------------------------------------- Font Ailesi
FONT_FAMILY = "Segoe UI"


def font(size: int = 12, weight: str = "normal", slant: str = "roman") -> ctk.CTkFont:
    """Segoe UI tabanli standart font uretici."""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight, slant=slant)


# ------------------------------------------------------------- Renk Paleti
# Koyu Tema Katmanli Yuzeyler (Surface Layers):
# Level 0 (Zemin): #0F172A (Derin Lacivert-Siyah)
# Level 1 (Yan Menü, Kartlar): #1E293B (Koyu Arduvaz)
# Level 2 (İç Kartlar, Vurgulu Alanlar): #334155 (Orta Arduvaz)
# Level 3 (Giriş Kutuları, Hover): #475569 (Açık Arduvaz)

# Açık Tema Yuzeyler:
# Level 0 (Zemin): #F8FAFC
# Level 1 (Yan Menü, Kartlar): #FFFFFF
# Level 2 (İç Alanlar, Hover): #F1F5F9
# Level 3 (Giriş Kutuları, Çerçeveler): #E2E8F0

TEMA_RENKLERI = {
    # Yüzeyler (Açık, Koyu)
    "bg_ana": ("#F8FAFC", "#0F172A"),
    "bg_kart": ("#FFFFFF", "#1E293B"),
    "bg_kart_ic": ("#F1F5F9", "#273549"),
    "bg_sidebar": ("#F1F5F9", "#111827"),
    "bg_sidebar_aktif": ("#E2E8F0", "#1E293B"),
    "bg_hover": ("#E2E8F0", "#334155"),
    
    # Kenarlıklar
    "kenarlik": ("#E2E8F0", "#334155"),
    "kenarlik_ince": ("#CBD5E1", "#475569"),
    
    # Metin Renkleri
    "metin_ana": ("#0F172A", "#F8FAFC"),
    "metin_ikincil": ("#475569", "#94A3B8"),
    "metin_soluk": ("#64748B", "#64748B"),
    
    # Vurgu / Kurumsal Lacivert
    "vurgu": ("#1E3A8A", "#3B82F6"),
    "vurgu_hover": ("#1E40AF", "#60A5FA"),
    "vurgu_metin": ("#FFFFFF", "#FFFFFF"),
    
    # Durum Renkleri
    "durum_bekliyor": ("#2563EB", "#3B82F6"),
    "durum_yaklasiyor": ("#D97706", "#F59E0B"),
    "durum_geciken": ("#DC2626", "#EF4444"),
    "durum_tamamlandi": ("#16A34A", "#10B981"),
    "durum_bilgi_verildi": ("#7C3AED", "#8B5CF6"),
    
    # Nötr Butonlar
    "btn_notr": ("#E2E8F0", "#334155"),
    "btn_notr_hover": ("#CBD5E1", "#475569"),
    "btn_notr_metin": ("#0F172A", "#F8FAFC"),
    
    # Birincil Buton (Yeni Ekle vb.)
    "btn_primary": ("#1E3A8A", "#2563EB"),
    "btn_primary_hover": ("#172554", "#1D4ED8"),
    "btn_primary_metin": ("#FFFFFF", "#FFFFFF"),
}

# Öncelik Renkleri
ONCELIK_RENKLERI = {
    "Düşük": ("#64748B", "#94A3B8"),
    "Normal": ("#2563EB", "#3B82F6"),
    "Önemli": ("#D97706", "#F59E0B"),
    "Acil": ("#DC2626", "#EF4444"),
}

# Evrak ve Termin Durumları
EVRAK_DURUMLARI = [
    "Bekliyor",
    "Hazırlandı",
    "Gönderildi",
    "Onaylandı",
    "Reddedildi",
    "Gecikti",
]

# Evrak Termin Kuralları
TERMIN_KURALLARI = [
    "Belirli tarih",
    "Her ayın 1-5'i",
    "Ayın ilk haftası",
    "Ayın son haftası",
    "Ayın son iş günü",
]

# Görev Durumları
GOREV_DURUMLARI = [
    "Bekliyor",
    "Devam ediyor",
    "Tamamlandı",
    "Gecikti",
]
