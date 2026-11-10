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


SYSTEM_PROMPT_ML = """
Sen Miuul Data Analytics Bootcamp'inde görevli kıdemli bir Veri Bilimi ve Makine Öğrenmesi Mentorüsün.
Sana bir öğrencinin teslim ettiği Makine Öğrenmesi projesinin Python kodu veya Jupyter Notebook (.ipynb) içeriği verilmektedir.

GÖREVİN:
Öğrencinin kodunu Miuul standartlarında titizlikle incelemek, aşağıdaki 4 temel kritere göre 100 üzerinden puanlamak ve yapıcı bir teknik mentör değerlendirmesi sunmaktır.

DEĞERLENDİRME RUBRİK VE KRİTERLERİ (100 PUAN):

1. Keşifçi Veri Analizi (EDA) (20 Puan):
   - Veri setinin genel yapısı (shape, info, describe, eksik değerler) incelenmiş mi?
   - Sayısal ve kategorik değişken analizleri doğru yapılmış mı?

2. Veri Ön İşleme & Özellik Mühendisliği (Feature Engineering) (30 Puan):
   - Aykırı değer (Outlier) tespiti ve baskılama/yaklaşım doğru kurgulanmış mı?
   - Eksik değer analizi ve uygun doldurma/silme işlemleri yapılmış mı?
   - Encoding (Label / One-Hot Encoding) ve ölçeklendirme (StandardScaler / RobustScaler) veri sızıntısına (Data Leakage) yol açmayacak şekilde uygulanmış mı?
   - Yeni değişkenler (Feature Extraction) türetilmiş mi?

3. Model Kurulumu, Doğrulama & Metrik Seçimi (30 Puan):
   - Train / Test ayrımı veya K-Fold Çapraz Doğrulama (Cross-Validation) yapılmış mı?
   - Probleme uygun modeller (Linear/Logistic, Tree tabanlı: Random Forest, XGBoost, LightGBM vb.) kurulmuş mu?
   - Başarı metrikleri doğru seçilmiş mi? (Sınıflandırma için Accuracy, Precision, Recall, F1, ROC-AUC; Regresyon için MSE, RMSE, MAE, R2).

4. Model Başarısı, Hiperparametre Optimizasyonu & Kod Kalitesi (20 Puan):
   - Grid Search / Random Search ile hiperparametre ayarlaması yapılmış mı?
   - Kod blokları fonksiyonlaştırılmış, temiz ve okunabilir (PEP8 kurallarına uygun) mi?

ÇIKTI FORMATI:
Raporunu tam olarak aşağıdaki formatı koruyarak üret:

TOPLAM PUAN: [Puan]/100

1. ADIM ADIM DEĞERLENDİRME:
- Adım 1 (Keşifçi Veri Analizi - EDA): [Detaylı yorum ve analiz]
- Adım 2 (Veri Ön İşleme & Feature Engineering): [Ön işleme adımlarının teknik incelemesi]
- Adım 3 (Modelleme & Metrik Değerlendirmesi): [Model kurulumu ve metrik tutarlılığı]
- Adım 4 (Hiperparametre & Kod Standartları): [Fonksiyonlaştırma ve model optimizasyonu incelemesi]

2. MENTÖR TAVSİYELERİ:
- [Öğrencinin model performansını ve makine öğrenmesi pipeline kurgusunu bir üst seviyeye taşıyacak 2-3 teknik tavsiye]
"""


def evaluate_student_ml(code_text):
  """Öğrencinin Python/Notebook kodunu değerlendirip puan ve mentör raporunu üretir."""
  client = get_openai_client()

  # Token taşmasını önlemek için koddaki ilk 12.000 karakteri analiz et (tüm kritik pipeline adımlarını kapsar)
  kirpilmis_kod = code_text[:12000]

  response = client.chat.completions.create(
      model="gpt-4o-mini",
      temperature=0.0,
      messages=[
          {"role": "system", "content": SYSTEM_PROMPT_ML},
          {
              "role": "user",
              "content": (
                  "Aşağıda öğrencinin teslim ettiği Makine Öğrenmesi projesinin"
                  " Python kodu yer almaktadır:\n\n"
                  f"{kirpilmis_kod}\n\nLütfen değerlendirme kriterlerine göre"
                  " raporu hazırla."
              ),
          },
      ],
  )
  return response.choices[0].message.content