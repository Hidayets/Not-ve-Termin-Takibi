"""Yazdirilabilir Kurumsal Rapor Modulu.

Okul yoneticileri ve ogretmenler icin riskli terminleri, bugunku isleri ve
gorev durumlarini baskiya hazir (A4 uyumlu) kurumsal HTML raporu olarak uretir.
"""
from __future__ import annotations

import datetime
import os
import tempfile

import db
import reminder


def rapor_olustur_ve_ac() -> str:
    """Kurumsal termin ve is takip raporu uretir ve varsayilan tarayicida acar."""
    simdi = datetime.datetime.now()
    tum_kayitlar = db.tum_notlar()

    bugunku_isler = []
    riskli_terminler = []
    bekleyen_gorevler = []

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
            bugunku_isler.append(k)

        if tur == "termin":
            if zaman:
                fark = zaman - simdi
                if fark.total_seconds() < 0 or fark <= datetime.timedelta(days=7):
                    riskli_terminler.append(k)
        elif tur == "gorev":
            bekleyen_gorevler.append(k)

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Termin ve İş Takip Raporu - {simdi.strftime('%d.%m.%Y')}</title>
    <style>
        @page {{ size: A4 portrait; margin: 15mm; }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #1e293b;
            background: #ffffff;
            margin: 0;
            padding: 20px;
            font-size: 13px;
            line-height: 1.4;
        }}
        .header {{
            border-bottom: 2px solid #1e3a8a;
            padding-bottom: 12px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .header h1 {{
            margin: 0;
            font-size: 20px;
            color: #1e3a8a;
            letter-spacing: -0.5px;
        }}
        .header p {{
            margin: 4px 0 0 0;
            color: #64748b;
            font-size: 12px;
        }}
        .badge-bar {{
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
        }}
        .badge-box {{
            flex: 1;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 8px 12px;
            background: #f8fafc;
        }}
        .badge-box .num {{
            font-size: 18px;
            font-weight: bold;
            color: #1e3a8a;
        }}
        .badge-box .title {{
            font-size: 11px;
            color: #64748b;
            text-transform: uppercase;
        }}
        h2 {{
            font-size: 14px;
            color: #0f172a;
            border-left: 4px solid #1e3a8a;
            padding-left: 8px;
            margin: 20px 0 10px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 16px;
        }}
        th, td {{
            border: 1px solid #e2e8f0;
            padding: 8px 10px;
            text-align: left;
        }}
        th {{
            background: #f1f5f9;
            color: #334155;
            font-weight: 600;
            font-size: 12px;
        }}
        tr:nth-child(even) {{
            background: #f8fafc;
        }}
        .status-danger {{
            color: #dc2626;
            font-weight: bold;
        }}
        .status-warn {{
            color: #d97706;
            font-weight: bold;
        }}
        .status-ok {{
            color: #16a34a;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 30px;
            border-top: 1px solid #e2e8f0;
            padding-top: 10px;
            font-size: 11px;
            color: #94a3b8;
            display: flex;
            justify-content: space-between;
        }}
        @media print {{
            .no-print {{ display: none; }}
            body {{ padding: 0; }}
        }}
        .print-btn {{
            background: #1e3a8a;
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>NOTLARIM & TERMİN TAKİP RAPORU</h1>
            <p>Okul & Kurum Yönetimi Çalışma ve Teslim Çizelgesi</p>
        </div>
        <div style="text-align: right;">
            <p><strong>Rapor Tarihi:</strong> {simdi.strftime('%d.%m.%Y %H:%M')}</p>
            <button class="print-btn no-print" onclick="window.print()">🖨️ Yazdır / PDF Kaydet</button>
        </div>
    </div>

    <div class="badge-bar">
        <div class="badge-box">
            <div class="num">{len(bugunku_isler)}</div>
            <div class="title">Bugünkü İşler</div>
        </div>
        <div class="badge-box">
            <div class="num" style="color: #dc2626;">{len(riskli_terminler)}</div>
            <div class="title">Riskli / Yaklaşan Terminler</div>
        </div>
        <div class="badge-box">
            <div class="num" style="color: #2563eb;">{len(bekleyen_gorevler)}</div>
            <div class="title">Bekleyen Görevler</div>
        </div>
    </div>

    <h2>1. Risk Altındaki Evrak ve Terminler</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 30%;">Evrak / Konu</th>
                <th style="width: 25%;">İlgili Kurum / Amir</th>
                <th style="width: 18%;">Teslim Tarihi</th>
                <th style="width: 15%;">Durum</th>
                <th style="width: 12%;">Amir Bilgisi</th>
            </tr>
        </thead>
        <tbody>
    """

    if not riskli_terminler:
        html += """<tr><td colspan="5" style="text-align: center; color: #64748b; padding: 12px;">Risk altında veya geciken termin kaydı bulunmamaktadır.</td></tr>"""
    else:
        for k in riskli_terminler:
            zaman = reminder.not_zamani(k)
            gecikti = bool(zaman and zaman < simdi)
            durum_cls = "status-danger" if gecikti else "status-warn"
            durum_txt = "Gecikti" if gecikti else (k.get("evrak_durum") or "Bekliyor")
            bilgi = "✓ Verildi" if k.get("amire_bilgi_verildi") else "Verilmedi"
            zaman_txt = zaman.strftime("%d.%m.%Y %H:%M") if zaman else "-"

            html += f"""
            <tr>
                <td><strong>{k.get('baslik', '')}</strong></td>
                <td>{k.get('kurum_amir', '-') or '-'}</td>
                <td>{zaman_txt}</td>
                <td class="{durum_cls}">{durum_txt}</td>
                <td>{bilgi}</td>
            </tr>
            """

    html += """
        </tbody>
    </table>

    <h2>2. Bugün Yapılacak İşler ve Notlar</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 35%;">Başlık</th>
                <th style="width: 20%;">Tür / Kategori</th>
                <th style="width: 20%;">Saat / Plan</th>
                <th style="width: 25%;">Açıklama</th>
            </tr>
        </thead>
        <tbody>
    """

    if not bugunku_isler:
        html += """<tr><td colspan="4" style="text-align: center; color: #64748b; padding: 12px;">Bugün için planlanmış herhangi bir iş bulunmamaktadır.</td></tr>"""
    else:
        for k in bugunku_isler:
            zaman = reminder.not_zamani(k)
            zaman_txt = zaman.strftime("%H:%M") if zaman else "-"
            tur_txt = (k.get("tur") or "not").capitalize()
            kat_txt = k.get("kategori") or "Genel"

            html += f"""
            <tr>
                <td><strong>{k.get('baslik', '')}</strong></td>
                <td>{tur_txt} ({kat_txt})</td>
                <td>{zaman_txt}</td>
                <td>{(k.get('aciklama') or '')[:60]}</td>
            </tr>
            """

    html += f"""
        </tbody>
    </table>

    <div class="footer">
        <span>Notlarım & Termin Takibi Masaüstü Uygulaması Tarafından Üretilmiştir.</span>
        <span>Sayfa 1 / 1</span>
    </div>
</body>
</html>
    """

    gecici_dosya = os.path.join(
        tempfile.gettempdir(), f"Termin_Raporu_{simdi.strftime('%Y%m%d_%H%M%S')}.html"
    )
    with open(gecici_dosya, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        os.startfile(gecici_dosya)
    except Exception:
        pass

    return gecici_dosya
