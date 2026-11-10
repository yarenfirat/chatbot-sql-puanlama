import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import streamlit as st

load_dotenv()

# OpenAI API anahtarı
if "openai_key" in st.secrets:
  my_key_openai = st.secrets["openai_key"]
else:
  my_key_openai = os.getenv("openai_key")

llm_gpt = ChatOpenAI(
    api_key=my_key_openai,
    model="gpt-4o-mini",
    temperature=0,  # Tutarlı puanlama için 0
)

SYSTEM_PROMPT_SQL = """
Sen Miuul Data Analytics Bootcamp'inde görevli kıdemli bir SQL Mentorüsün.
Öğrenciler Northwind ve İK (Employee Attrition) veritabanı üzerinde 33 soruluk SQL bitirme ödevini tamamlamaktadır.

GÖREVİN:
Öğrencinin teslim ettiği SQL dosyasını satır satır incelemek; her bir sorunun (Soru 1'den Soru 33'e kadar) doğru yazılıp yazılmadığını kontrol etmek ve aşağıdaki formata tam sadık kalarak bir mentör raporu üretmektir.

DEĞERLENDİRME KURALLARI:
1. Öğrencinin kodunda her soru genellikle yorum satırlarıyla (örn: -- Soru 1, -- Soru 2 vb.) ayrılmıştır. Kodun tamamını tara.
2. Yazılan sorgu doğru mantıkta ve soru amacına uygunsa "Doğru", eksik/hatalıysa "Hatalı: [Kısa açıklama]", o soru için hiçbir sorgu yazılmamışsa "Boş bırakılmış. Bu soru için sorgu yok." olarak belirt.
3. Toplam doğru sayısını say ve tam olarak "TOPLAM PUAN: X/33" formatında en başta yaz.

ÇIKTI FORMATI:
Raporunu tam olarak şu şablonda üret:

TOPLAM PUAN: [Doğru Sayısı]/33

SORU BAZLI DEĞERLENDİRME:
- Soru 1: [Doğru / Hatalı / Boş bırakılmış]
- Soru 2: [Doğru / Hatalı / Boş bırakılmış]
... (Soru 33'e kadar her soruyu tek tek listele)
- Soru 33: [Doğru / Hatalı / Boş bırakılmış]

1. MENTÖRÜN TAVSİYELERİ:
- [Öğrencinin SQL yetkinliğini artıracak 2-3 yapıcı mentör tavsiyesi]
"""


def evaluate_student_sql(sql_kodu: str, schema_path="schemas/odev1_sema.txt"):
  """Öğrencinin SQL kodunu kesmeden, 33 sorunun tamamını inceleyerek değerlendirir."""
  try:
    sema_icerigi = ""
    if os.path.exists(schema_path):
      try:
        with open(schema_path, "r", encoding="utf-8") as f:
          sema_icerigi = f.read()
      except Exception:
        sema_icerigi = "Veritabanı şeması okunamadı."
    else:
      sema_icerigi = "Veritabanı şeması bulunamadı."

    # final_prompt burada doğrudan ve koşulsuz olarak atanır
    final_prompt = f"""
VERİTABANI ŞEMASI / BİLGİ:
{sema_icerigi}

ÖĞRENCİNİN YAZDIĞI SQL KODLARI (33 SORU):
{sql_kodu}

Lütfen yukarıdaki kurallara göre 33 sorunun tamamını incele ve raporu hazırla.
"""

    mesajlar = [
        SystemMessage(content=SYSTEM_PROMPT_SQL),
        HumanMessage(content=final_prompt),
    ]

    cevap = llm_gpt.invoke(mesajlar)
    return cevap.content

  except Exception as e:
    return (
        "⚠️ Değerlendirme Hatası: Bu öğrencinin ödevi işlenirken model"
        f" sınırlarına takıldı veya bir API hatası oluştu.\nDetay: {str(e)}"
    )