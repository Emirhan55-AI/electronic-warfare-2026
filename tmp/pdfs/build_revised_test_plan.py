from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(r"C:\Users\emirhan55\OneDrive\Documents\ChatGPT\TEKNOFEST")
OUTPUT = ROOT / "output" / "pdf" / "TEKNOFEST_EH_Guncel_Test_Senaryolari_20260914.pdf"

PAGE_W, PAGE_H = A4
MARGIN_X = 15 * mm
MARGIN_TOP = 16 * mm
MARGIN_BOTTOM = 15 * mm

NAVY = colors.HexColor("#123B56")
NAVY_2 = colors.HexColor("#1D5875")
TEAL = colors.HexColor("#008FA1")
PALE_TEAL = colors.HexColor("#E9F5F6")
PALE_BLUE = colors.HexColor("#EFF5F8")
PALE_GRAY = colors.HexColor("#F5F6F7")
MID_GRAY = colors.HexColor("#6B7680")
GRID = colors.HexColor("#9DB0BC")
AMBER = colors.HexColor("#D68A00")
PALE_AMBER = colors.HexColor("#FFF4D7")
RED = colors.HexColor("#A73A3A")
PALE_RED = colors.HexColor("#FBECEC")
GREEN = colors.HexColor("#2F7D57")
INK = colors.HexColor("#202C35")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Italic", r"C:\Windows\Fonts\ariali.ttf"))


register_fonts()

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="BodyTR", fontName="Arial", fontSize=8.4, leading=11.2, textColor=INK, spaceAfter=3))
styles.add(ParagraphStyle(name="SmallTR", fontName="Arial", fontSize=6.7, leading=8.6, textColor=INK))
styles.add(ParagraphStyle(name="TinyTR", fontName="Arial", fontSize=5.9, leading=7.2, textColor=INK))
styles.add(ParagraphStyle(name="H1TR", fontName="Arial-Bold", fontSize=18, leading=21, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name="H1LongTR", fontName="Arial-Bold", fontSize=15.2, leading=18, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name="H2TR", fontName="Arial-Bold", fontSize=11, leading=13, textColor=NAVY, spaceBefore=3, spaceAfter=5))
styles.add(ParagraphStyle(name="H3TR", fontName="Arial-Bold", fontSize=8.7, leading=10.5, textColor=NAVY, spaceBefore=3, spaceAfter=3))
styles.add(ParagraphStyle(name="CenterTR", fontName="Arial", fontSize=8, leading=10, alignment=TA_CENTER, textColor=INK))
styles.add(ParagraphStyle(name="CenterSmall", fontName="Arial", fontSize=6.5, leading=8, alignment=TA_CENTER, textColor=INK))
styles.add(ParagraphStyle(name="TableHead", fontName="Arial-Bold", fontSize=6.5, leading=7.8, alignment=TA_CENTER, textColor=colors.white))
styles.add(ParagraphStyle(name="CoverTitle", fontName="Arial-Bold", fontSize=27, leading=31, alignment=TA_LEFT, textColor=INK))
styles.add(ParagraphStyle(name="CoverSub", fontName="Arial", fontSize=12, leading=16, textColor=NAVY))
styles.add(ParagraphStyle(name="Callout", fontName="Arial-Bold", fontSize=8.1, leading=10, textColor=NAVY))
styles.add(ParagraphStyle(name="Foot", fontName="Arial", fontSize=6.2, leading=7.4, textColor=MID_GRAY))


def P(text: str, style: str = "BodyTR") -> Paragraph:
    return Paragraph(text, styles[style])


def C(text: str) -> Paragraph:
    return P(text, "CenterSmall")


def head(text: str) -> Paragraph:
    return P(text, "TableHead")


def table(data, widths, *, header=True, font=6.5, row_heights=None, repeat_rows=1, aligns=None, padding=4):
    cooked = []
    for r, row in enumerate(data):
        out = []
        for cell in row:
            if isinstance(cell, Paragraph):
                out.append(cell)
            elif r == 0 and header:
                out.append(head(str(cell)))
            else:
                out.append(Paragraph(str(cell), ParagraphStyle(
                    name=f"cell-{r}-{len(out)}-{id(data)}",
                    parent=styles["SmallTR"],
                    fontSize=font,
                    leading=font + 1.7,
                    alignment=TA_LEFT,
                )))
        cooked.append(out)
    t = Table(cooked, colWidths=widths, rowHeights=row_heights, repeatRows=repeat_rows if header else 0, hAlign="LEFT")
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY if header else PALE_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white if header else INK),
        ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold" if header else "Arial"),
        ("GRID", (0, 0), (-1, -1), 0.45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]
    if header:
        for r in range(1, len(cooked)):
            if r % 2 == 0:
                ts.append(("BACKGROUND", (0, r), (-1, r), PALE_GRAY))
    if aligns:
        for col, align in aligns.items():
            ts.append(("ALIGN", (col, 1 if header else 0), (col, -1), align))
    t.setStyle(TableStyle(ts))
    return t


def box(title: str, text: str, tone="blue"):
    bg, border, title_color = {
        "blue": (PALE_BLUE, NAVY_2, NAVY),
        "teal": (PALE_TEAL, TEAL, NAVY),
        "amber": (PALE_AMBER, AMBER, colors.HexColor("#7A5000")),
        "red": (PALE_RED, RED, RED),
    }[tone]
    body = Table([[P(f"<font color='{title_color.hexval()}'><b>{title}</b></font><br/>{text}", "SmallTR")]], colWidths=[PAGE_W - 2 * MARGIN_X])
    body.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return body


def section_title(code: str, title: str, subtitle: str = ""):
    label = f"{code}  {title}"
    items = [P(label, "H1LongTR" if len(label) > 40 else "H1TR")]
    if subtitle:
        items.append(P(subtitle, "CoverSub"))
    items.append(Spacer(1, 3 * mm))
    return items


def result_line():
    return box("SONUÇ", "GEÇTİ □   KALDI □   GEÇERSİZ □   ERTELENDİ □ &nbsp;&nbsp;&nbsp; Karar veren: ____________________ &nbsp;&nbsp; Tarih/UTC: ____________________", "teal")


def blank_rows(count, cols):
    return [[str(i + 1)] + ["________________" for _ in range(cols - 1)] for i in range(count)]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#C9D3D9"))
    canvas.setLineWidth(0.45)
    canvas.line(MARGIN_X, 10.5 * mm, PAGE_W - MARGIN_X, 10.5 * mm)
    canvas.setFont("Arial", 6.5)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(MARGIN_X, 6.7 * mm, "TEKNOFEST Elektronik Harp - Test Senaryoları | Rev. 1 | 14 Eylül 2026")
    canvas.drawRightString(PAGE_W - MARGIN_X, 6.7 * mm, f"Sayfa {doc.page}")
    canvas.restoreState()


class TestPlanDoc(BaseDocTemplate):
    pass


def add_cover(story):
    story.append(Spacer(1, 21 * mm))
    story.append(P("TEKNOFEST", "CoverSub"))
    story.append(Spacer(1, 3 * mm))
    story.append(P("ELEKTRONİK HARP<br/>TEST SENARYOLARI", "CoverTitle"))
    story.append(Spacer(1, 5 * mm))
    story.append(P("Proje durumuna göre gözden geçirilmiş ED kabul paketi ve kontrollü ET eki", "CoverSub"))
    story.append(Spacer(1, 14 * mm))
    story.append(box("GÜNCEL DURUM", "Ürün kapsamı yalnız RX tabanlı Elektronik Destek (ED) işlevleridir. PHASE-08 / ST-06 kabulü açıktır. ET sayfaları tarihsel gereksinim ve kontrollü laboratuvar yeniden açılma taslağı olarak korunmuştur; güncel üründe TX yolu bulunduğunu göstermez.", "teal"))
    story.append(Spacer(1, 6 * mm))
    story.append(box("GÜVENLİK SINIRI", "Fiziksel ET-TX yalnız kapalı Faraday kabininde veya aynı kabin içindeki uygun zayıflatmalı kablolu düzende; tüm interlocklar sağlanırsa ve kapsam yeniden açılırsa yürütülebilir. Açık alan ve denetimsiz antenli TX yasaktır. GNSS RF aldatma mevcut yetkilendirmenin dışındadır.", "amber"))
    story.append(Spacer(1, 20 * mm))
    story.append(table([
        ["Belge", "Değer"],
        ["Sürüm", "Rev. 1 - 14 Eylül 2026"],
        ["Temel kapsam", "KTR-4.1, KTR-4.2, KTR-4.3, KTR-4.4"],
        ["Açık ana kapı", "PHASE-08 / ST-06"],
        ["Belge sahibi", "____________________________"],
        ["Onay", "____________________________"],
    ], [45 * mm, 120 * mm], font=8))
    story.append(Spacer(1, 12 * mm))
    story.append(P("Bu belge test tasarımıdır. Boş form, tek başına donanım başarısı, ürün kabulü veya faz geçişi oluşturmaz.", "Foot"))
    story.append(PageBreak())


def add_review(story):
    story += section_title("01", "KAYNAK FORM İNCELEMESİ VE PUANLAMA")
    story.append(P("Kaynak 21 sayfalık form seti, sahada elle doldurmaya elverişli ve görsel olarak tutarlıdır. Ancak güncel depo durumu, kabul bilimi ve kanıt zinciri açısından önemli revizyon gerektirir."))
    scores = [
        ["Boyut", "Ağırlık", "Kaynak", "Revize", "Temel gerekçe"],
        ["Kapsam ve KTR uyumu", "1,5", "0,5", "1,4", "ET güncel üründe yok; ED açık kapıları ayrılaştırıldı."],
        ["Kabul ölçütleri", "1,5", "0,5", "1,4", "PASS/FAIL eşikleri ve geçersiz koşu kuralları eklendi."],
        ["Tekrarlanabilirlik", "1,5", "0,6", "1,4", "Seri, sürüm, hash, UTC, ayar ve kanıt yolu zorunlu."],
        ["Pozitif/negatif kontroller", "1,5", "0,5", "1,4", "TX açık/kapalı, yanlış kanal, kör tekrar ve payda kaydı eklendi."],
        ["Ölçüm doğruluğu", "1,0", "0,5", "0,9", "dBi, dBFS, dBm ve JSR ayrıldı; kalibrasyon kapısı kondu."],
        ["RF güvenliği", "1,5", "0,8", "1,5", "Faraday, interlock, acil stop ve GNSS yürütmeme kapısı eklendi."],
        ["Saha kullanılabilirliği", "1,0", "0,9", "0,9", "Form sadeliği korunurken karar alanları netleştirildi."],
        ["Kanıt ve hata yönetimi", "0,5", "0,2", "0,5", "Ham kayıt, sapma, kusur ve imza zinciri eklendi."],
        ["TOPLAM", "10,0", "4,5", "9,4", "Revize puanı belge tasarım kalitesidir; test sonucu değildir."],
    ]
    story.append(table(scores, [35 * mm, 14 * mm, 15 * mm, 15 * mm, 86 * mm], font=6.2))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Başlıca düzeltmeler", "H2TR"))
    fixes = [
        ["Kaynakta görülen sorun", "Revizyondaki karar"],
        ["Toplam GAIN için 0/10/20/30/47 adımları belirsiz.", "Toplam GAIN kaldırıldı; RF AMP, LNA ve VGA ayrı ve cihazdan geri okunan gerçek değerlerle kaydedilir."],
        ["Tek ölçümle anten 'kapsıyor/kapsamıyor' sonucu.", "Anten uygunluğu referans antene göreli fark, tekrar, yönelim ve belirsizlikle değerlendirilir; nominal bant garanti değildir."],
        ["dBFS, dBm ve dBi aynı sonuç alanında karışıyor.", "Her birinin referans düzlemi ayrıldı. Geçerli kalibrasyon yoksa dBm alanı zorunlu olarak 'Kalibre değil' olur."],
        ["CFAR kutusu ölçüm tanımı vermiyor.", "Olay durumu, frekans hatası, gözlem oranı, yanlış alarm paydası ve ham sayaçlar ayrı alanlardır."],
        ["BPSK/QPSK protokol çözümü zorunlu gibi.", "Sayısal dinleme ilave kapsam olarak ayrıldı; mevcut üründe protokol çözümü uygulanmış sayılmaz."],
        ["ET testleri güncel ürün yeteneği gibi duruyor.", "ET eki korundu fakat 'yeniden açılma onayı bekler' ve fail-closed laboratuvar kapılarıyla sınırlandı."],
        ["GNSS aldatma yürütülebilir test gibi.", "Mevcut yetkilendirme dışında olduğu için yalnız NO-GO karar kaydı olarak tutuldu."],
    ]
    story.append(table(fixes, [65 * mm, 100 * mm], font=6.6))
    story.append(PageBreak())


def add_rules(story):
    story += section_title("02", "YÜRÜTME KURALLARI VE KARAR SÖZLEŞMESİ")
    story.append(box("FAZ KAPISI", "Bu form setinin hazırlanması sonraki fazı açmaz. PHASE-08 / ST-06 kapanış kararı kanıtla verilir. Sonraki geliştirme veya ET yeniden açılması için ayrıca açık kullanıcı onayı gerekir.", "amber"))
    story.append(Spacer(1, 4 * mm))
    rules = [
        ["Kural", "Zorunlu uygulama"],
        ["Önceden dondurma", "Frekanslar, tekrar sayısı, eşikler, rastgele sıra ve hariç tutma koşulları testten önce yazılır; sonuç görüldükten sonra değiştirilmez."],
        ["Koşu kimliği", "Her fiziksel koşuya benzersiz kimlik verilir. Ham kayıt, özet ve ekran görüntüsü aynı kimliği taşır."],
        ["Kimlik bağı", "Kaynak commit/çalışma ağacı özeti, uygulama/hizmet/köprü/FPGA/imaj SHA-256 ve cihaz seri numarası yazılır."],
        ["Geçersiz koşu", "Kırpılma, USB overrun, CRC/sıra/kuyruk hatası, yanlış cihaz, eksik referans veya interlock ihlali başarı sayılmaz; GEÇERSİZ olarak paydada raporlanır."],
        ["Negatif kontrol", "TX-kapalı veya kaynaksız koşu, pozitif koşulla aynı RX ayarı ve geometriyle eşleştirilir. 'Verici kapalı' ortam sessizliği demek değildir."],
        ["Körlük", "Kör değerlendirmede operatör hedef frekansını sonuç dondurulana kadar bilmez. Kaynak sorumlusu ve gözlemci ayrılır."],
        ["Mutlak güç", "Kalibrasyon profili cihaz/frekans/örnekleme/LNA/VGA/ölçek/süre ile tam eşleşmiyorsa yalnız dBFS raporlanır; dBm yazılmaz."],
        ["Frekans sınırı", "HackRF sistem zarfı 1 MHz - 6 GHz'dir. 10 MS/s yolu kısa algılama burst'üdür; sürekli gerçek zaman iddiası değildir. 20 MS/s bu host/USB düzeninde kabul edilmemiştir."],
        ["Arşiv", "Başarısız ve belirsiz sonuçlar silinmez. Eski kanıt yeni ikiliye hash eşleşmeden aktarılmaz."],
    ]
    story.append(table(rules, [38 * mm, 127 * mm], font=6.7))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Standart sonuç kodu", "H2TR"))
    story.append(table([
        ["Kod", "Anlam"],
        ["GEÇTİ", "Önceden dondurulmuş ölçütlerin tamamı sağlandı ve kanıt paketi eksiksiz."],
        ["KALDI", "Geçerli koşuda en az bir zorunlu ölçüt sağlanmadı."],
        ["GEÇERSİZ", "Koşu bütünlüğü bozuldu; ölçüm başarı/başarısızlık paydasından ayrı raporlanır."],
        ["ERTELENDİ", "Önkoşul, faz onayı, donanım veya güvenlik yetkisi yok."],
    ], [28 * mm, 137 * mm], font=7))
    story.append(PageBreak())


def add_traceability(story):
    story += section_title("03", "ANA TEST MATRİSİ VE UYGULAMA SIRASI")
    data = [
        ["Kimlik", "KTR/Faz", "Senaryo", "Durum", "Çıkış kanıtı"],
        ["ED-00", "Ortak", "Sürüm, donanım ve laboratuvar ön kontrolü", "Şimdi", "Kimlik ve hazır oluş formu"],
        ["ED-01", "KTR-4.1 / ST-06", "Soğuk açılış ve fail-closed başlangıç", "Açık kapı", "İmaj/hizmet/FPGA/rol kanıtı"],
        ["ED-02", "KTR-4.1 / ST-06", "1 MHz - 6 GHz tam bant ve kör hedef arama", "Açık kapı", "Tam pencere, kapsama ve süre kaydı"],
        ["ED-03", "KTR-4.1 / ST-06", "Eşleştirilmiş RF Pd/Pfa ve yerleşim", "Açık kapı", "Pozitif/negatif paydalar"],
        ["ED-04", "KTR-4.1 / APP-F", "GUI + RX dayanıklılık, iptal ve yeniden başlatma", "Açık kapı", "Süre, hız, hata, heartbeat"],
        ["ED-05", "KTR-4.2", "Taşıyıcı, OBW99, güç, Analog/Sayısal", "Kısmi", "Referanslı alan bazlı doğruluk"],
        ["ED-06", "KTR-4.3", "Analog izleme ve AM/NFM dinleme", "Kısmi", "Süreklilik, WAV, anlaşılabilirlik"],
        ["ED-07", "KTR-4.3 ilave", "Sayısal sinyal dinleme/protokol", "İsteğe bağlı", "Uygulandıysa ayrı protokol kanıtı"],
        ["ED-08", "KTR-4.4 / PHASE-09", "24 açılı bağıl genlik yön bulma", "Fiziksel RMS açık", "Açı tablosu ve dairesel RMS"],
        ["ED-09", "Destekleyici", "RX anten uygunluğu ve bant karşılaştırması", "Destekleyici", "Referans antene göreli fark"],
        ["ET-00", "ADR-0043/0044", "Kapsam ve güvenlik yeniden açılma kapısı", "ERTELENDİ", "Tüm interlocklar + yeni onay"],
        ["ET-01", "KTR-5.1 tarihsel", "Tekli / sürekli / ara-bakışlı kontrollü etki", "ERTELENDİ", "Kapalı kabin etki ve sonlanma kaydı"],
        ["ET-02", "KTR-5.2/5.3 tarihsel", "Çoklu / baraj / analog aldatma", "ERTELENDİ", "Yalnız ayrıca kapsam açılırsa"],
        ["ET-03", "GNSS", "GNSS RF aldatma", "YÜRÜTÜLMEZ", "NO-GO kaydı"],
    ]
    story.append(table(data, [18 * mm, 29 * mm, 60 * mm, 22 * mm, 36 * mm], font=5.9))
    story.append(Spacer(1, 4 * mm))
    story.append(box("ÖNCELİK", "Önce ED-00 -> ED-01 -> ED-02/ED-03 -> ED-04 ile PHASE-08 / ST-06 kanıtı tamamlanır. ED-05, ED-06 ve ED-08 mevcut işlevlerin ayrı fiziksel kabulidir. ET sayfaları, ED sonucunu bekletmeden yalnız kontrol listesi olarak saklanır; kendiliğinden yürütülmez.", "blue"))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Her koşuda zorunlu üst bilgi", "H2TR"))
    story.append(table([
        ["Alan", "Kayıt"],
        ["Koşu kimliği / UTC", "____________________________ / ____________________________"],
        ["Operatör / gözlemci", "____________________________ / ____________________________"],
        ["Kaynak sürümü", "Commit: ____________________  Çalışma ağacı: TEMİZ □  DEĞİŞİK □"],
        ["Uygulama / hizmet / köprü", "__________________ / __________________ / __________________"],
        ["FPGA / image.ub SHA-256", "________________________________ / ________________________________"],
        ["RX seri / anten / kablo", "__________________ / __________________ / __________________"],
        ["Ham kanıt dizini", "____________________________________________________________"],
    ], [47 * mm, 118 * mm], font=7))
    story.append(PageBreak())


def add_preflight(story):
    story += section_title("ED-00", "ORTAK ÖN KONTROL VE KANIT BAŞLIĞI", "Her fiziksel ED koşusundan önce doldurulur")
    checks = [
        ["No", "Kontrol", "Beklenen", "Sonuç / kanıt", "Durum"],
        ["1", "KTR ve faz kapsamı", "Koşu kimliği ilgili KTR/fazla eşleşir", "________________", "G □ K □"],
        ["2", "Kaynak ve ikili kimliği", "Tüm hash ve sürümler okunur", "________________", "G □ K □"],
        ["3", "ED_RX_PRIMARY", "Tam seri eşleşir; TX argümanı yok", "________________", "G □ K □"],
        ["4", "ZedBoard / FPGA", "Beklenen imaj, hizmet ve 'operating' durumu", "________________", "G □ K □"],
        ["5", "Saat ve günlük", "PC/kart UTC veya ofset kaydı mevcut", "________________", "G □ K □"],
        ["6", "Kablo / anten", "Bant uyumu, konektör ve fiziksel durum kayıtlı", "________________", "G □ K □"],
        ["7", "Referans kaynak", "Açık/kapalı durumu bağımsız kişi/ölçerle kayıtlı", "________________", "G □ K □"],
        ["8", "Disk / kanıt yolu", "Yeni ve yazılabilir çıktı dizini, yeterli alan", "________________", "G □ K □"],
        ["9", "Kırpılma ön kontrolü", "Kısa ön alımda kırpılma yok", "________________", "G □ K □"],
        ["10", "Durdurma", "Operatör iptali ve güvenli kapanış çalışır", "________________", "G □ K □"],
    ]
    story.append(table(checks, [10 * mm, 46 * mm, 51 * mm, 39 * mm, 19 * mm], font=6.1))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Koşu yapılandırması", "H2TR"))
    story.append(table([
        ["Alan", "Değer", "Alan", "Değer"],
        ["Test frekansı/aralığı", "________________", "RX örnekleme", "8 □  10 □  20 □ MS/s"],
        ["FPGA işleme", "2 MS/s □  10 MS/s burst □", "FFT", "4096 □ 8192 □ 16384 □"],
        ["RF AMP", "Kapalı □ Açık □", "LNA / VGA", "______ dB / ______ dB"],
        ["Kare / burst", "______ / ______", "Süre", "______ s / dk"],
        ["Anten / yön / mesafe", "________________", "Kablo / zayıflatma", "________________"],
    ], [35 * mm, 47.5 * mm, 35 * mm, 47.5 * mm], font=7))
    story.append(Spacer(1, 5 * mm))
    story.append(box("DURDURMA KURALI", "Yanlış seri, beklenmeyen TX süreci, kırpılma, USB overrun, CRC/sıra/kuyruk hatası, imaj/hash uyuşmazlığı veya referans kaybında koşu durdurulur ve GEÇERSİZ olarak saklanır.", "red"))
    story.append(Spacer(1, 5 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_cold_boot(story):
    story += section_title("ED-01", "SOĞUK AÇILIŞ VE FAIL-CLOSED BAŞLANGIÇ", "KTR-4.1 / PHASE-08 / ST-06")
    story.append(P("Amaç: Elektrik kesip açılan başlangıçtan sonra kart, hizmet, köprü, FPGA ve RX rolünün güncel hashlerle kendiliğinden ve doğru sırada hazır olduğunu; eksik bileşende ürünün sahte başarı üretmediğini doğrulamak."))
    story.append(P("Önkoşul ve yöntem", "H2TR"))
    story.append(table([
        ["Adım", "İşlem", "Kabul"],
        ["1", "PC, ZedBoard ve RX'i güvenli şekilde kapat; başlangıç zamanını kaydet.", "Kapanışta askıda RX/TX süreci yok."],
        ["2", "Gücü fiziksel olarak kes, en az 30 s bekle ve yeniden ver.", "Koşu gerçek soğuk açılış olarak kaydedilir."],
        ["3", "FPGA durumu, image.ub, hizmet ve köprü özetlerini oku.", "Beklenen kimliklerin tamamı eşleşir; FPGA operating."],
        ["4", "Uygulamayı aç; kart veya alıcı yokken ayrı negatifleri uygula.", "Arayüz yalnız 'Alıcı algılanmadı' / 'FPGA algılanmadı' gösterir; sonuç üretmez."],
        ["5", "Bileşenleri doğru durumda bağla ve 2 MS/s kısa RX çalıştır.", "İlk geçerli olay/boş sonuç yalnız gerçek kart yanıtından gelir."],
        ["6", "Üç bağımsız soğuk açılış tekrarını tamamla.", "3/3 kimlik ve başlangıç geçişi; hata sayacı sıfır."],
    ], [12 * mm, 88 * mm, 65 * mm], font=6.8))
    story.append(Spacer(1, 4 * mm))
    rows = [["Tekrar", "Açılış süresi", "FPGA", "Hizmet/köprü hash", "RX rolü", "Hata", "Sonuç"]] + [
        [str(i), "______ s", "______", "________________", "______", "______", "G □ K □"] for i in range(1, 4)
    ]
    story.append(table(rows, [14 * mm, 25 * mm, 20 * mm, 43 * mm, 20 * mm, 20 * mm, 23 * mm], font=6.3))
    story.append(Spacer(1, 5 * mm))
    story.append(box("GEÇİŞ ÖLÇÜTÜ", "3/3 tekrar doğru kimliklerle açılmalı; yanlış/eksik bileşen negatiflerinin tamamı fail-closed olmalı; USB/CRC/sıra/kuyruk ve kırpılma sayaçları sıfır olmalıdır.", "teal"))
    story.append(Spacer(1, 5 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_detection_fullband(story):
    story += section_title("ED-02", "TAM BANT VE KÖR HEDEF ARAMA", "KTR-4.1 / PHASE-08 / ST-06")
    story.append(P("Amaç: Güncel ürün yolunun 1 MHz - 6 GHz aralığını boşluksuz planladığını, her pencereyi işlediğini ve frekansı operatöre açıklanmayan kontrollü hedefleri bağımsız 2 MS/s doğrulamada doğru bağladığını göstermek."))
    story.append(box("PROFİL SINIRI", "8 veya 10 MS/s fiziksel giriş kullanılabilir. 10 MS/s yolu en çok 256 karelik kısa algılama burst'üdür; sürekli gerçek zaman veya otomatik parametre yolu değildir. 20 MS/s bu bilgisayar/USB düzeninde kabul profili değildir.", "amber"))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Önceden dondurulacak deney tasarımı", "H2TR"))
    story.append(table([
        ["Alan", "Plan"],
        ["Kör hedefler", "En az 6 hedef; dar ve yaklaşık 1 MHz geniş aile; alt/orta/üst bant; kenar ve merkezden uzak yerleşimler."],
        ["Negatifler", "Her hedef ailesi için aynı ayarlı TX-kapalı eş; ayrıca boş bant pencereleri."],
        ["Yerleşim", "Mümkünse alıcı merkezine göre +1, -1, +3,25 ve -3,25 MHz; her nokta ayrı koşu."],
        ["Tekrar", "Her pozitif/negatif koşul için en az 10 bağımsız kayıt; sıra rastgeleleştirilir."],
        ["Körlük", "Kaynak sorumlusu frekansı ve açık/kapalı durumunu kilitli listeye yazar; operatör sonuç dondurulana kadar görmez."],
        ["Tam bant", "Planlanan her pencere işlendi/atlandı sayacı; boşluk, tekrar ve toplam duvar süresi kaydı."],
    ], [39 * mm, 126 * mm], font=6.8))
    story.append(Spacer(1, 4 * mm))
    data = [["Koşu", "Gizli kaynak", "Gerçek frekans", "Bulunan", "Hata Hz", "Pencere", "USB/taşıma", "Sonuç"]]
    for i in range(1, 9):
        data.append([str(i), "AÇIK □ KAPALI □", "________", "________", "________", "____/____", "________", "G □ K □ X □"])
    story.append(table(data, [11 * mm, 25 * mm, 24 * mm, 23 * mm, 19 * mm, 20 * mm, 23 * mm, 20 * mm], font=5.6))
    story.append(Spacer(1, 4 * mm))
    story.append(box("GEÇİŞ ÖLÇÜTÜ", "Tam bantta planlanan pencere sayısı eksiksiz; beklenmeyen kapsama boşluğu yok; geçerli koşulda taşıma/kırpılma hatası sıfır; kör hedefler önceden dondurulan frekans ve gözlem ölçütleriyle bulunur. Pd/Pfa sonucu ED-03 tablosundan ayrı raporlanır.", "teal"))
    story.append(Spacer(1, 4 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_pdpfa(story):
    story += section_title("ED-03", "EŞLEŞTİRİLMİŞ RF Pd/Pfa VE NEGATİF KONTROL", "KTR-4.1 / ST-06")
    story.append(P("Amaç: Aynı geometri, anten, kablo ve RX ayarında yalnız kaynak durumunu değiştirerek doğru tespit ve yanlış alarm oranlarını ölçmek. 'Confirmed' olay, frekans toleransı içinde ve koşunun gerçek gözlem karelerinde bulunmalıdır."))
    story.append(P("Ölçüt dondurma", "H2TR"))
    story.append(table([
        ["Ölçüt", "Testten önce yazılacak değer"],
        ["Eşleşme toleransı", "± __________ Hz veya ± __________ FFT hücresi"],
        ["Pozitif başarı", "En az ______ confirmed gözlem ve gözlem oranı en az ______ %"],
        ["Pd hedefi", "Alt sınır / hedef: ______ / ______ %; güven aralığı yöntemi: __________________"],
        ["Pfa hedefi", "Üst sınır: ______ olay/pencere veya ______ / değerlendirilen CUT"],
        ["Tekrar", "Her aile, SNR/seviye ve açık/kapalı hücresi için en az 10 bağımsız koşu"],
        ["Hariç tutma", "Yalnız önceden yazılmış bütünlük koşulları; Belirsiz ve kaçırmalar paydadan çıkarılmaz"],
    ], [46 * mm, 119 * mm], font=6.8))
    story.append(Spacer(1, 4 * mm))
    data = [["Aile/seviye", "N açık", "Doğru", "Kaçırma", "Pd", "N kapalı", "Yanlış olay", "Pfa", "%95 GA"]]
    families = ["Dar / yüksek", "Dar / sınır", "Geniş / yüksek", "Geniş / sınır", "Merkez/kenar", "Genel"]
    for f in families:
        data.append([f, "____", "____", "____", "____%", "____", "____", "____", "________"])
    story.append(table(data, [29 * mm, 16 * mm, 16 * mm, 18 * mm, 16 * mm, 18 * mm, 23 * mm, 16 * mm, 13 * mm], font=5.8))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Bütünlük sayaçları", "H2TR"))
    story.append(table([
        ["Kare", "USB overrun", "CRC", "Sıra", "Kuyruk", "Kırpılma", "Geçersiz koşu"],
        ["________", "________", "________", "________", "________", "________", "________"],
    ], [28 * mm, 24 * mm, 20 * mm, 20 * mm, 22 * mm, 23 * mm, 28 * mm], font=6.4))
    story.append(Spacer(1, 5 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_endurance(story):
    story += section_title("ED-04", "GUI + RX DAYANIKLILIK VE YAŞAM DÖNGÜSÜ", "KTR-4.1 / APP-F")
    story.append(P("Amaç: Güncel QML, gerçek HackRF -> PC -> ZedBoard -> FPGA/ARM yolunda uzun süre çalışırken veri bütünlüğünü, arayüz canlılığını, durdurma/yeniden başlatmayı ve kapanışı kanıtlamak."))
    story.append(table([
        ["Senaryo", "Uygulama", "Ölçüm", "Kabul"],
        ["Uzun görünür koşu", "En az 15 dk; ekran görünür; gerçek FPGA yanıtı", "Kare/s, USB/CRC/sıra/kuyruk, kırpılma, görüntü yaşı", "Hata sıfır; önceden dondurulan hız/yaş sınırı geçer"],
        ["Masaüstü geçişi", "Pencere gizle/göster ve zaman damgası", "Son çizim aralığı ve dönüş gecikmesi", "Donma/çökme yok; olay nesli karışmaz"],
        ["İptal", "Devam eden taramada operatör durdurur", "Durdurma gecikmesi ve son sayaç", "Durum 'Durduruldu'; sınırlı sürede kapanır"],
        ["Yeniden başlat", "Aynı süreçte yeni oturum", "Nesil, sıra, sayaç ve sonuç kimliği", "Eski kare/olay yeni oturuma sızmaz"],
        ["Kapanış", "RX sürerken pencereyi kapat", "Süreç ve port kapanışı", "Askıda süreç/port yok; kontrollü kapanış"],
        ["Hata enjeksiyonu", "Kart veya RX bağlantısını kontrollü kes", "UI mesajı ve log", "Sahte sonuç yok; Türkçe kullanıcı durumu"],
    ], [31 * mm, 48 * mm, 48 * mm, 38 * mm], font=6.3))
    story.append(Spacer(1, 4 * mm))
    rows = [["Tekrar", "Süre", "Kare", "Kare/s", "USB", "CRC/sıra", "Kuyruk", "p95 yaş", "Max heartbeat", "Sonuç"]]
    for i in range(1, 6):
        rows.append([str(i), "____", "____", "____", "____", "____", "____", "____ ms", "____ ms", "G □ K □"])
    story.append(table(rows, [11 * mm, 16 * mm, 17 * mm, 18 * mm, 15 * mm, 20 * mm, 18 * mm, 19 * mm, 21 * mm, 19 * mm], font=5.3))
    story.append(Spacer(1, 4 * mm))
    story.append(box("NOT", "Geçmiş 15 dakikalık sonuç yalnız kendi kaynak/hash bağında geçerlidir. Güncel QML ve ikili için yeni uzun koşu gerekir; kısa 8 saniyelik tarama uzun süreli kabul yerine geçmez.", "amber"))
    story.append(Spacer(1, 5 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_parameters(story):
    story += section_title("ED-05", "PARAMETRE ÇIKARIMI DOĞRULAMASI", "KTR-4.2 - taşıyıcı, OBW99, güç ve Analog/Sayısal")
    story.append(box("DOĞRULUK SINIRI", "İlk üç sayısal parametre PL/ARM yolundadır; Analog/Sayısal ayrımı PC'dedir. dBm yalnız ölçülmüş ve bağlamı tam eşleşen kalibrasyonla geçerlidir. 'Belirsiz' yanlış sınıf değildir ve paydadan çıkarılmaz.", "blue"))
    story.append(Spacer(1, 4 * mm))
    story.append(table([
        ["Parametre", "Bağımsız referans", "Zorunlu kayıt", "Kabul yaklaşımı"],
        ["Taşıyıcı", "Frekans referanslı üreteç/ölçer", "Hz hatası, ppm, valid oranı", "Çoklu frekans ve SNR; TX/RX saat belirsizliği raporlanır"],
        ["OBW99", "Spektrum analizörü OBW99 veya bağımsız uzun temiz I/Q", "Alt/üst kenar, toplam hata, valid/belirsiz", "AM/NFM/FSK/PSK, komşu ve pencere kenarı"],
        ["Güç", "RX SMA düzleminde bilinen dBm", "dBFS, kalibrasyon C, dBm, hata", "Kalibrasyon ve bağımsız kontrol noktaları ayrıdır"],
        ["Sınıf", "Kaynağı bilinen AM/NFM ve OOK/FSK/PSK/QAM", "Doğru/yanlış/Belirsiz, model/source hash", "Aile bazlı; test verisiyle eşik ayarlanmaz; CW ayrı kontrol"],
    ], [28 * mm, 46 * mm, 47 * mm, 44 * mm], font=6.1))
    story.append(Spacer(1, 4 * mm))
    data = [["No", "Aile", "Gerçek f / OBW", "FPGA/ARM f / OBW", "dBFS", "Ref dBm", "Hata", "Sınıf", "Durum"]]
    for i in range(1, 9):
        data.append([str(i), "______", "________ / ________", "________ / ________", "______", "______", "______", "______", "G/K/B"])
    story.append(table(data, [9 * mm, 20 * mm, 30 * mm, 34 * mm, 17 * mm, 18 * mm, 16 * mm, 16 * mm, 10 * mm], font=5.4))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Zorunlu test ailesi", "H2TR"))
    story.append(P("CW kontrolü; AM ve NFM; FSK/OOK; BPSK/QPSK; farklı içerik/sembol hızı; 0/6/12 dB dahil SNR basamakları; güç basamakları; komşu sinyal; analiz aralığı kenarı; noise-only; kırpılma. Her koşul için en az 10 bağımsız kayıt. Kalibrasyon yoksa mutlak güç satırı ERTELENDİ olur, diğer göreli ölçümler devam eder."))
    story.append(Spacer(1, 4 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_analog_listening(story):
    story += section_title("ED-06", "ANALOG İZLEME VE DİNLEME", "KTR-4.3 - zorunlu AM/NFM ürün akışı")
    story.append(P("Amaç: Tespit -> parametre -> yeniden doğrulama -> dinleme zincirinde gerçek analog telsiz konuşmasını süreklilik ve anlaşılabilirlik ölçütleriyle doğrulamak."))
    story.append(table([
        ["Adım", "İşlem", "Kabul / ölçüm"],
        ["1", "Kaynağı kör taramada bul ve confirmed kanalı seç.", "Frekans/olay/kare kimliği ve kart yanıtı kayıtlı."],
        ["2", "Parametreleri çıkar; emisyon merkezi ve OBW99'u dinlemeye aktar.", "Alan durumları geçerli veya ret nedeni açık; eski olay kimliğine güvenilmez."],
        ["3", "Yeni canlı oturumda aynı RF kanalını FPGA ile yeniden doğrula.", "5,001216 s tampon; en az %95 gözlenen kare; en uzun boşluk en çok 8 kare."],
        ["4", "AM veya NFM'i açıkça seç; 48 kHz mono PCM16/WAV üret.", "Süre, örnek sayısı, kırpılma, WAV bütünlüğü ve oynat/durdur."],
        ["5", "En az iki bağımsız dinleyici, kör cümle listesini değerlendirir.", "Önceden belirlenmiş kelime/cümle doğruluk eşiği; dinleyiciler ayrı kayıt."],
        ["6", "Yanlış kanal ve TX-kapalı negatiflerini uygula.", "Anlamlı ses/yanlış kabul yok; sonuç başarıya çevrilmez."],
    ], [12 * mm, 86 * mm, 67 * mm], font=6.5))
    story.append(Spacer(1, 4 * mm))
    data = [["Koşu", "AM/NFM", "Gözlenen", "Max boşluk", "Güç aralığı dBFS", "Artık f", "WAV", "Anlaşılırlık", "Sonuç"]]
    for i in range(1, 7):
        data.append([str(i), "______", "____%", "____ kare", "________", "________ Hz", "G □ K □", "____%", "G/K/X"])
    story.append(table(data, [12 * mm, 21 * mm, 20 * mm, 20 * mm, 29 * mm, 21 * mm, 17 * mm, 23 * mm, 12 * mm], font=5.7))
    story.append(Spacer(1, 4 * mm))
    story.append(box("GEÇİŞ ÖLÇÜTÜ", "AM ve NFM için ayrı pozitif/negatif tekrarlar; gerçek konuşmanın önceden dondurulmuş anlaşılabilirlik eşiği; veri bütünlüğü hatası ve kırpılma sıfır; dosya ve kart olay bağı eksiksiz. Sentetik 1 kHz ton tek başına konuşma kabulü değildir.", "teal"))
    story.append(Spacer(1, 4 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_digital_listening(story):
    story += section_title("ED-07", "SAYISAL SİNYAL İZLEME / DİNLEME", "KTR-4.3 ilave kapsam - bugün zorunlu ürün kabulü değildir")
    story.append(box("DURUM", "Mevcut ürün için sayısal amatör telsiz protokol/kod çözümü uygulanmış kabul edilmez. Bu form yalnız ilgili protokol ve hukuk/izin kapsamı ayrıca tanımlanırsa kullanılır. Analog ED-06 tamamlanmadan sayısal başarı varsayılmaz.", "amber"))
    story.append(Spacer(1, 5 * mm))
    story.append(table([
        ["Kontrol", "Kayıt", "Durum"],
        ["Protokol ve sürüm açıkça tanımlı", "____________________________", "G □ K □ E □"],
        ["Kaynak bit dizisi / ses referansı hash bağlı", "____________________________", "G □ K □ E □"],
        ["FEC, çerçeveleme ve senkron oracle'ı bağımsız", "____________________________", "G □ K □ E □"],
        ["Şifreli içeriği çözme iddiası yok", "____________________________", "G □ K □ E □"],
        ["BPSK/QPSK/FSK etiketi protokol çözümü yerine geçmez", "____________________________", "G □ K □ E □"],
        ["BER/PER paydası ve SNR noktaları önceden donduruldu", "____________________________", "G □ K □ E □"],
    ], [88 * mm, 50 * mm, 27 * mm], font=6.8))
    story.append(Spacer(1, 5 * mm))
    data = [["No", "Protokol", "Modülasyon", "SNR", "Bit/çerçeve", "BER", "PER", "Ses/veri", "Sonuç"]]
    for i in range(1, 7):
        data.append([str(i), "______", "______", "____ dB", "________", "______", "______", "______", "G/K/E"])
    story.append(table(data, [10 * mm, 25 * mm, 25 * mm, 18 * mm, 28 * mm, 17 * mm, 17 * mm, 17 * mm, 8 * mm], font=5.8))
    story.append(Spacer(1, 5 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_df(story):
    story += section_title("ED-08A", "YÖN BULMA KURULUMU VE 24 AÇILI ÖLÇÜM", "KTR-4.4 / PHASE-09 - bağıl genlik yöntemi")
    story.append(box("SUNUM SINIRI", "İlk başarılı fiziksel yön 0° kabul edilir; ölçümler saat yönünde 15° adımla 345°'ye ilerler. Sonuç bağıl ham maksimum LOB'dur. Enkoder/IMU ve coğrafi referans yokken gerçek kuzey, harita yönü veya hedef konumu üretilmez.", "blue"))
    story.append(Spacer(1, 4 * mm))
    story.append(table([
        ["Alan", "Değer"],
        ["Hedef frekans / kanal", "________________ MHz / ________________"],
        ["Gerçek bağıl yön", "________________ ° (operatörden gizli referans)"],
        ["Anten / polarizasyon / yükseklik", "________________ / ________________ / ______ m"],
        ["Mesafe / ortam", "________ m / ________________________________________"],
        ["RX seri / AMP / LNA / VGA", "________________ / ______ / ______ dB / ______ dB"],
        ["Dönüş sehpası / açı belirsizliği", "________________ / ± ______ °"],
    ], [55 * mm, 110 * mm], font=7))
    story.append(Spacer(1, 4 * mm))
    data = [["Adım", "Açı", "Kanal dBFS", "4 kare kimliği", "Confirmed", "Ayar aynı", "Not"]]
    for i, angle in enumerate(range(0, 180, 15), 1):
        data.append([str(i), f"{angle}°", "________", "________________", "E □ H □", "E □ H □", "________"])
    story.append(table(data, [12 * mm, 17 * mm, 25 * mm, 45 * mm, 22 * mm, 22 * mm, 22 * mm], font=5.9))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Her başarılı açı yeni dört ardışık gerçek kare kullanır. Başarısız/iptal edilmiş ölçüm açı sayacını ilerletmez. Frekans, kanal, seri ve kazanç değişirse tur geçersizdir.", "Foot"))
    story.append(PageBreak())

    story += section_title("ED-08B", "YÖN BULMA TAMAMLAMA VE RMS KARARI", "180° - 345° ölçümleri ve bağımsız yön karşılaştırması")
    data2 = [["Adım", "Açı", "Kanal dBFS", "4 kare kimliği", "Confirmed", "Ayar aynı", "Not"]]
    for i, angle in enumerate(range(180, 360, 15), 13):
        data2.append([str(i), f"{angle}°", "________", "________________", "E □ H □", "E □ H □", "________"])
    story.append(table(data2, [12 * mm, 17 * mm, 25 * mm, 45 * mm, 22 * mm, 22 * mm, 22 * mm], font=5.9))
    story.append(Spacer(1, 4 * mm))
    story.append(table([
        ["Metrik", "Sonuç", "Önceden dondurulmuş kabul"],
        ["Ölçülen ham maksimum LOB", "________ °", "________________"],
        ["Gerçek bağıl yön", "________ °", "Referans düzeninden"],
        ["Dairesel hata", "________ °", "wrap-safe"],
        ["Tepe / rakip farkı", "________ dB", "En az 3 dB"],
        ["Ön / arka farkı", "________ dB", "En az 3 dB"],
        ["Tekrar sayısı", "________", "En az 10 bağımsız yön koşusu"],
        ["Dairesel RMS / p95 / max", "____ / ____ / ____ °", "Testten önce: ____ / ____ / ____ °"],
    ], [53 * mm, 48 * mm, 64 * mm], font=6.7))
    story.append(Spacer(1, 4 * mm))
    story.append(box("GEÇİŞ ÖLÇÜTÜ", "Her turda 24/24 geçerli açı; aynı hedef ve ayar bağı; 3 dB tepe/rakip ve ön/arka kapıları; en az 10 bağımsız gerçek yön; önceden dondurulmuş dairesel RMS/p95/max sınırları.", "teal"))
    story.append(Spacer(1, 4 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_antenna(story):
    story += section_title("ED-09", "RX ANTEN UYGUNLUĞU VE BANT KARŞILAŞTIRMASI", "Tek ölçüm 'kapsama' veya anten kazancı kanıtı değildir")
    story.append(P("Kaynak formdaki nominal bantlar planlama girdisi olarak korunmuştur. Üretici veri sayfası ve anten örneği doğrulanmadan nominal kazanç doğrulanmış gerçek sayılmaz."))
    antennas = [
        ["Anten", "Kaynak formdaki nominal bant", "Rol / not"],
        ["Diamond SRH-789", "95 - 1100 MHz", "Geniş alıcı referansı adayı"],
        ["Quectel YE0003AA", "699 - 5000 MHz", "Alıcı; kurulum geometrisi etkisi yüksek"],
        ["MRTK-Q7060F06X2", "698 - 960 / 1710 - 6000 MHz", "Alıcı; bant boşluğu ayrıca sınanır"],
        ["FOX-727", "144 - 146 / 430 - 440 MHz", "Yönlü; DF için bant uyumu kontrol edilir"],
        ["MRTK-D7038P11", "698 - 960 / 1710 - 3800 MHz", "Yönlü; nominal boşluklar vardır"],
        ["Motorobit yönlü 800M-6G", "800 MHz - 6 GHz", "Yönlü; veri sayfası/seri doğrulaması eklenir"],
        ["Motorobit UWB TEM", "2,4 - 10,5 GHz", "HackRF ile yalnız 6 GHz'e kadar değerlendirilebilir"],
    ]
    story.append(table(antennas, [43 * mm, 55 * mm, 67 * mm], font=6.5))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Eşleştirilmiş karşılaştırma", "H2TR"))
    data = [["No", "Frekans", "Test anteni", "Referans", "Açı/pol.", "dBFS test", "dBFS ref", "Fark", "Tekrar", "Sonuç"]]
    for i in range(1, 9):
        data.append([str(i), "______", "______", "______", "______", "______", "______", "______", "____", "G/K/X"])
    story.append(table(data, [9 * mm, 18 * mm, 25 * mm, 24 * mm, 19 * mm, 19 * mm, 19 * mm, 15 * mm, 13 * mm, 9 * mm], font=5.4))
    story.append(Spacer(1, 4 * mm))
    story.append(box("YORUM KURALI", "dBi üretici/anten kazancıdır; HackRF dBFS alıcı zincirinin göreli sayısal seviyesidir; dBm kalibrasyonlu referans düzlemidir. Aynı tabloda birbirinin yerine kullanılmaz. Bant dışı tek olumlu tespit nominal performans veya 'kapsıyor' kararı değildir.", "amber"))
    story.append(Spacer(1, 4 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_et_gate(story):
    story += section_title("ET-00", "ET KAPSAM VE GÜVENLİK YENİDEN AÇILMA KAPISI", "ADR-0043 laboratuvar sınırı + ADR-0044 güncel ED-only kararı")
    story.append(box("BUGÜNKÜ KARAR", "Güncel üründe ET arayüzü, TX kaynakları, yapılandırma ve özel doğrulayıcılar kaldırılmıştır. Bu ek, kullanıcı isteğiyle test bilgisini korur; TX yetkisi veya çalışan özellik iddiası değildir. ET fiziksel testi başlamadan kapsamın yeniden açıldığı açıkça kaydedilmelidir.", "red"))
    story.append(Spacer(1, 4 * mm))
    gates = [
        ["No", "Zorunlu kapı", "Kanıt", "Durum"],
        ["1", "ET fazı ve test türü için yeni açık kullanıcı onayı", "____________________________", "G □ K □"],
        ["2", "Kapalı Faraday kabini veya aynı kabinde zayıflatmalı kablolu düzen", "____________________________", "G □ K □"],
        ["3", "Kabin izolasyon/kaçak ölçümü ve tarihli kayıt", "____________________________", "G □ K □"],
        ["4", "TX ve bağımsız RX tam seri numarasıyla ayrılmış", "____________________________", "G □ K □"],
        ["5", "Resmî HackRF araçları ve allowlist doğrulanmış", "____________________________", "G □ K □"],
        ["6", "Frekans, örnekleme, kazanç ve süre üst sınırları dondurulmuş", "____________________________", "G □ K □"],
        ["7", "En yüksek kaynak çıkışı + kablo/zayıflatma ile RX giriş güvenliği", "____________________________", "G □ K □"],
        ["8", "Operatör başlatması, otomatik durma ve acil durdurma", "____________________________", "G □ K □"],
        ["9", "Bağımsız ölçüm alıcısı / spektrum ölçümü ve ham kayıt", "____________________________", "G □ K □"],
        ["10", "PA yok veya PA fiziksel güvenlik/ölçüm planında açıkça onaylı", "____________________________", "G □ K □"],
        ["11", "İlk koşu en düşük TX kazancı ve kısa doğrulama tonu", "____________________________", "G □ K □"],
        ["12", "Komut, config, hash, başlangıç/bitiş ve stop günlüğü", "____________________________", "G □ K □"],
    ]
    story.append(table(gates, [10 * mm, 88 * mm, 48 * mm, 19 * mm], font=6.2))
    story.append(Spacer(1, 4 * mm))
    story.append(box("FAIL-CLOSED", "Herhangi bir kapı KALDI veya boş ise fiziksel TX başlatılmaz. Form sonucu ERTELENDİ olur; yazılım veya komutla interlock atlanmaz.", "red"))
    story.append(Spacer(1, 4 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_et_scenarios(story):
    story += section_title("ET-01", "TEKLİ, SÜREKLİ VE ARA-BAKIŞLI ET DOĞRULAMASI", "Yalnız ET-00 tamamen geçer ve kapsam yeniden açılırsa")
    story.append(P("Bu sayfa işlevsel etki ve güvenli sonlanmayı ölçer; dalga şekli üretim talimatı değildir. Frekans ve sinyal türü yalnız izinli, kapalı laboratuvar planından seçilir."))
    story.append(table([
        ["Senaryo", "Girdi", "Ölçüm", "Kabul"],
        ["Tekli", "Tek izinli hedef kanal, sınırlı süre/kazanç", "Hedef seviye, test seviyesi, JSR, hedef hizmet metriği", "Etki eşiği testten önce; zaman sonunda otomatik durma"],
        ["Sürekli", "Tek kanal, önceden dondurulmuş kısa pencere", "Başlangıç gecikmesi, süreklilik, stop gecikmesi", "Kesinti yok; stop sonrası RF tabanına dönüş"],
        ["Ara-bakışlı", "BEKLE -> DİNLE -> TEST -> DİNLE", "Yanlış tetik, geçiş zamanı, duty cycle, kanal geri kazanımı", "Sinyal yokken TX yok; her döngüde doğru sonlanma"],
    ], [28 * mm, 47 * mm, 47 * mm, 43 * mm], font=6.3))
    story.append(Spacer(1, 4 * mm))
    data = [["Koşu", "Tür", "Hedef f", "Süre", "TX/RX seri", "Hedef dB", "Test dB", "JSR", "Stop", "Sonuç"]]
    for i in range(1, 7):
        data.append([str(i), "______", "______", "____ s", "________", "______", "______", "______", "____ ms", "G/K/X"])
    story.append(table(data, [9 * mm, 19 * mm, 18 * mm, 15 * mm, 27 * mm, 18 * mm, 18 * mm, 15 * mm, 16 * mm, 10 * mm], font=5.4))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Ara-bakış döngü kaydı", "H2TR"))
    loop = [["Döngü", "Dinlemede hedef", "TX başladı", "Etki", "TX durdu", "RX geri döndü", "Yanlış tetik", "Sonuç"]]
    for i in range(1, 6):
        loop.append([str(i), "E □ H □", "E □ H □", "E □ H □", "E □ H □", "E □ H □", "E □ H □", "G/K/X"])
    story.append(table(loop, [14 * mm, 25 * mm, 23 * mm, 20 * mm, 23 * mm, 26 * mm, 22 * mm, 12 * mm], font=5.8))
    story.append(Spacer(1, 4 * mm))
    story.append(box("GÜVENLİ SONLANDIRMA", "Hedef etki gözlenmese bile otomatik durma ve acil stop zorunlu kabul kapısıdır. Test bitince bağımsız ölçüm alıcısında yayın taban seviyesine dönmelidir.", "amber"))
    story.append(Spacer(1, 4 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_et_multi(story):
    story += section_title("ET-02", "ÇOKLU, BARAJ VE ANALOG ALDATMA TEST TASLAĞI", "Tarihsel KTR-5.2/5.3 - güncel üründe uygulanmıyor")
    story.append(box("YENİDEN AÇILMA ŞARTI", "ET-00 geçmeden ve her alt senaryo için ayrı kapsam kararı verilmeden yürütülmez. PA, açık alan, denetimsiz anten ve izinsiz hedef kullanımı bu formun dışında ve yasaktır.", "red"))
    story.append(Spacer(1, 4 * mm))
    story.append(table([
        ["Alt senaryo", "Gerekli ek tanım", "Ölçüm", "Karar"],
        ["Çoklu", "Hedef sayısı, izinli kanallar, toplam süre ve kaynak üst sınırı", "Her kanal için etki, çapraz etki, spektral maske, stop", "Tüm hedefler ve hedef dışı koruma ayrı"],
        ["Baraj", "İzinli kapalı bant, bant genişliği ve bağımsız ölçüm planı", "Bant içi düzlüğü, bant dışı sızıntı, toplam güç, stop", "Spektral maske ve güvenlik sınırı önceden"],
        ["Analog aldatma", "Kapalı laboratuvar hedef alıcısı ve bilinen test içeriği", "Doğru/yanlış içerik kabulü, geri dönüş, kayıt", "Hedefin test yayınını alması tek başına başarı değildir"],
    ], [28 * mm, 57 * mm, 47 * mm, 33 * mm], font=6.2))
    story.append(Spacer(1, 4 * mm))
    data = [["No", "Senaryo", "İzinli bant/kanal", "Hedef sayısı", "Etki metriği", "Hedef dışı etki", "Stop", "Kanıt", "Sonuç"]]
    for i in range(1, 7):
        data.append([str(i), "______", "____________", "____", "________", "________", "____ ms", "______", "G/K/E"])
    story.append(table(data, [9 * mm, 22 * mm, 32 * mm, 19 * mm, 25 * mm, 26 * mm, 17 * mm, 15 * mm, 10 * mm], font=5.6))
    story.append(Spacer(1, 5 * mm))
    story.append(P("Anten/PA bilgi kaydı", "H2TR"))
    story.append(table([
        ["TX anteni", "Nominal bant", "PA", "Kablo", "Ölçülen kayıp", "Referans düzlemi"],
        ["________________", "________________", "YOK □ / model: ______", "________________", "______ dB", "________________"],
    ], [30 * mm, 32 * mm, 31 * mm, 27 * mm, 22 * mm, 23 * mm], font=6.2))
    story.append(Spacer(1, 5 * mm))
    story.append(result_line())
    story.append(PageBreak())


def add_gnss(story):
    story += section_title("ET-03", "GNSS RF ALDATMA - NO-GO KAYDI", "Mevcut yetkilendirmenin ve güncel ürün kapsamının dışında")
    story.append(box("YÜRÜTÜLMEZ", "GPS L1/L2 veya başka GNSS RF dalga şekli ADR-0043 laboratuvar onayına dahil değildir. Güncel kaynakta ET/TX yolu da yoktur. Bu nedenle fiziksel GNSS aldatma testi başlatılmaz; PASS/FAIL ölçümü alınmaz.", "red"))
    story.append(Spacer(1, 8 * mm))
    story.append(P("Kaynak formdaki teknik sorunlar", "H2TR"))
    story.append(table([
        ["Bulgu", "Düzeltme"],
        ["MRTK-D7038P11 nominal bantları GPS L1 1575,42 MHz ve L2 1227,60 MHz'i kapsamıyor.", "Bu antenle sonuç üretmek yerine uygun bant, filtre, izolasyon ve ölçüm zinciri yeni faz planında doğrulanmalıdır."],
        ["Aldatma oldu mu? EVET/HAYIR tek başına yeterli değil.", "Gelecekteki izinli plan; gerçek GNSS simülatörü/oracle, konum-zaman hata metriği, emniyetli alıcı, sızıntı ölçümü ve geri kazanım kriteri gerektirir."],
        ["Faraday kabini genel onayı GNSS yetkisi gibi okunabilir.", "GNSS için ayrıca açık kapsam, yasal/kurumsal yetki ve özel risk değerlendirmesi zorunludur."],
    ], [64 * mm, 101 * mm], font=6.8))
    story.append(Spacer(1, 8 * mm))
    story.append(table([
        ["NO-GO kontrolü", "Kayıt"],
        ["Fiziksel TX başlatılmadı", "EVET □  HAYIR □"],
        ["Kapsam dışı karar operatöre bildirildi", "EVET □  HAYIR □"],
        ["Yeniden açılma talebi varsa karar/ADR referansı", "____________________________________________"],
        ["Sorumlu imzası / UTC", "____________________________________________"],
    ], [80 * mm, 85 * mm], font=7))
    story.append(Spacer(1, 8 * mm))
    story.append(box("SONUÇ", "ERTELENDİ □   YÜRÜTÜLMEDİ □   Güvenlik ihlali şüphesi varsa olay kaydı: ______________________________", "amber"))
    story.append(PageBreak())


def add_evidence(story):
    story += section_title("04", "KANIT, SAPMA VE NİHAİ KABUL ÖZETİ")
    story.append(P("Kanıt paketi kontrolü", "H2TR"))
    story.append(table([
        ["Zorunlu öğe", "Mevcut", "Yol / SHA-256"],
        ["Test planı ve dondurulmuş eşikler", "E □ H □", "________________________________________"],
        ["Ham I/Q veya özgün cihaz çıktısı", "E □ H □", "________________________________________"],
        ["JSON/JSONL/CSV özet", "E □ H □", "________________________________________"],
        ["Uygulama/hizmet/köprü/FPGA/imaj kimliği", "E □ H □", "________________________________________"],
        ["Cihaz seri, anten, kablo, geometri, kazanç", "E □ H □", "________________________________________"],
        ["Referans ölçüm ve belirsizlik", "E □ H □", "________________________________________"],
        ["Başarısız/belirsiz/geçersiz koşular", "E □ H □", "________________________________________"],
        ["Yeniden üretim komutu/doğrulayıcı", "E □ H □", "________________________________________"],
    ], [65 * mm, 22 * mm, 78 * mm], font=6.7))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Sapma ve kusur kaydı", "H2TR"))
    data = [["ID", "Test", "Beklenen", "Gözlenen", "Etkisi", "Karar / takip", "Sorumlu"]]
    for i in range(1, 6):
        data.append([f"D-{i:02d}", "______", "________", "________", "______", "________", "______"])
    story.append(table(data, [16 * mm, 20 * mm, 31 * mm, 31 * mm, 20 * mm, 31 * mm, 16 * mm], font=5.8))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Nihai test özeti", "H2TR"))
    summary = [["Test", "Durum", "Kanıt paketi", "Açık kapı / not"]]
    for code in ["ED-00", "ED-01", "ED-02", "ED-03", "ED-04", "ED-05", "ED-06", "ED-07", "ED-08", "ED-09", "ET-00", "ET-01", "ET-02", "ET-03"]:
        summary.append([code, "G □ K □ X □ E □", "________________", "____________________________"])
    story.append(table(summary, [20 * mm, 31 * mm, 45 * mm, 69 * mm], font=5.7, padding=2.4))
    story.append(Spacer(1, 5 * mm))
    story.append(box("BELGE PUANI", "Kaynak form: 4,5 / 10. Revize test tasarımı: 9,4 / 10. Revize puan, senaryoların kapsam, izlenebilirlik, güvenlik ve ölçülebilirlik kalitesidir; projenin testlerden geçtiği anlamına gelmez.", "teal"))
    story.append(Spacer(1, 4 * mm))
    story.append(table([
        ["Karar", "İmza / tarih"],
        ["PHASE-08 / ST-06: GEÇTİ □  KALDI □  AÇIK □", "________________________________________"],
        ["ED saha hazırlığı: HAZIR □  HAZIR DEĞİL □", "________________________________________"],
        ["ET kapsamı: KAPALI □  YENİ ONAY BEKLİYOR □", "________________________________________"],
    ], [92 * mm, 73 * mm], font=7))
    story.append(Spacer(1, 5 * mm))
    story.append(P("Dayanak belgeler: SIGNAL_DETECTION_STATUS.md; IMPLEMENTATION_ROADMAP.md; KTR_TRACEABILITY.md; P0_SYSTEM_ARCHITECTURE.md; SIGNAL_MONITORING_LISTENING_STATUS.md; SIGNAL_DIRECTION_FINDING_STATUS.md; PARAMETER_VALIDATION_BENCH.md; RF_TEST_BOUNDARIES.md; ADR-0043; ADR-0044.", "Foot"))


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame = Frame(MARGIN_X, MARGIN_BOTTOM, PAGE_W - 2 * MARGIN_X, PAGE_H - MARGIN_TOP - MARGIN_BOTTOM, id="main")
    doc = TestPlanDoc(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="TEKNOFEST Elektronik Harp - Güncel Test Senaryoları",
        author="TEKNOFEST Proje Ekibi",
        subject="ED kabul paketi ve kontrollü ET test eki",
    )
    doc.addPageTemplates([PageTemplate(id="standard", frames=[frame], onPage=footer)])
    story = []
    add_cover(story)
    add_review(story)
    add_rules(story)
    add_traceability(story)
    add_preflight(story)
    add_cold_boot(story)
    add_detection_fullband(story)
    add_pdpfa(story)
    add_endurance(story)
    add_parameters(story)
    add_analog_listening(story)
    add_digital_listening(story)
    add_df(story)
    add_antenna(story)
    add_et_gate(story)
    add_et_scenarios(story)
    add_et_multi(story)
    add_gnss(story)
    add_evidence(story)
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()
