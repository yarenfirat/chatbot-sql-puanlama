import os
from openai import OpenAI
import streamlit as st


def get_openai_client():
  api_key = st.secrets.get("openai_key") or os.getenv("OPENAI_API_KEY")
  if not api_key:
    raise ValueError(
        "OpenAI API Key bulunamadı! Lütfen secrets.toml dosyasını kontrol edin."
    )
  return OpenAI(api_key=api_key)


SYSTEM_PROMPT_CRM = """
Sen Miuul Data Analytics Bootcamp'inde görevli kıdemli bir CRM ve Müşteri Analitiği Mentorüsün.
Sana bir öğrencinin Excel (.xlsx) üzerinde tamamladığı RFM Analizi ve Müşteri Segmentasyonu ödevinin yapısal veri özeti (sayfalar, kolonlar, hesaplanan metrikler, segment dağılımları ve tablo örnekleri) verilmektedir.

GÖREVİN:
Öğrencinin çalışmasını Miuul standartlarında titizlikle incelemek, aşağıdaki 4 ana adıma göre 100 üzerinden puanlamak ve yapıcı bir mentör değerlendirmesi sunmaktır.

DEĞERLENDİRME RUBRİK VE KRİTERLERİ (100 PUAN):

1. Veri Hazırlığı ve Temel RFM Metrikleri (25 Puan):
   - Recency (Yenilik): Doğru analiz tarihi baz alınarak son satın alma tarihinden gün farkı hesaplanmış mı?
   - Frequency (Sıklık): Müşteri bazında tekil fatura/sipariş sayısı doğru bulunmuş mu?
   - Monetary (Parasal Değer): Müşteri bazlı toplam harcama/ciro tutarları doğru hesaplanmış mı?

2. RFM Skorlaması (1-5 Puan Skalası) (25 Puan):
   - Recency Skoru: Ters orantı kuralı doğru uygulanmış mı? (Recency değeri en küçük/en yeni olan aktif müşteriye 5, en eski müşteriye 1 verilmeli).
   - Frequency ve Monetary Skorları: Küçükten büyüğe 1'den 5'e doğru dilimlenmiş mi?
   - RF Skoru: Recency ve Frequency skorları doğru formatta birleştirilmiş mi? (Örn: 55, 11).

3. Segment Haritalaması (Segment Mapping) (25 Puan):
   - Miuul RFM segment haritası (Champions, Loyal Customers, Potential Loyalists, At Risk, Can't Lose Them, Hibernating, About to Sleep, New Customers vb.) doğru regex/aralıklarla eşleştirilmiş mi?
   - Segment sütununda tanımsız (NaN / #N/A) veya açıkta kalan kayıt kalmış mı?

4. Yönetsel Aksiyon ve İletişim Stratejisi (25 Puan):
   - Kritik segmentler (özellikle "Champions", "At Risk" ve "Can't Lose Them") için somut, veri odaklı pazarlama veya retention önerileri geliştirilmiş mi?

ÇIKTI FORMATI:
Yanıtını tam olarak aşağıdaki şablonu koruyarak ver:

TOPLAM PUAN: [Puan]/100

1. ADIM ADIM DEĞERLENDİRME:
- Adım 1 (Veri & RFM Metrikleri): [Detaylı yorum ve doğruluk analizi]
- Adım 2 (Skorlama & Ters Orantı Kuralı): [Detaylı yorum ve dilimleme analizi]
- Adım 3 (Segmentasyon Dağılımı): [Segment haritası doğruluğu ve eşleşme analizi]
- Adım 4 (Yönetsel Aksiyon Planı): [Strateji ve pazarlama aksiyonlarının değerlendirmesi]

2. MENTÖR TAVSİYELERİ:
- [Öğrencinin CRM bakış açısını geliştirecek 2-3 teknik mentör önerisi]
"""


def evaluate_student_crm(excel_summary_text):
  """Öğrencinin Excel özet metnini OpenAI'a göndererek yapılandırılmış mentör raporunu üretir."""
  client = get_openai_client()

  response = client.chat.completions.create(
      model="gpt-4o-mini",
      temperature=0.0,
      messages=[
          {"role": "system", "content": SYSTEM_PROMPT_CRM},
          {
              "role": "user",
              "content": (
                  "Aşağıda öğrencinin teslim ettiği Excel RFM ödevinin detaylı"
                  " özeti yer almaktadır:\n\n"
                  f"{excel_summary_text}\n\nLütfen değerlendirme kriterlerine"
                  " göre raporu hazırla."
              ),
          },
      ],
  )
  return response.choices[0].message.content