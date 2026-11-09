import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

if "openai_key" in st.secrets:
  my_key_openai = st.secrets["openai_key"]
else:
  my_key_openai = os.getenv("openai_key")

# gpt-4o yerine gpt-4o-mini kullanarak token sınırları ve 400 Bad Request hatalarını kökten önlüyoruz
llm_gpt = ChatOpenAI(api_key=my_key_openai, model="gpt-4o-mini", temperature=0)


def evaluate_student_sql(sql_kodu: str, schema_path="schemas/odev1_sema.txt"):
  if os.path.exists(schema_path):
    with open(schema_path, "r", encoding="utf-8") as f:
      sema_icerigi = f.read()
  else:
    sema_icerigi = "Veritabanı şeması bulunamadı."

  # Güvenlik önlemi: Kod aşırı uzunsa modelin token sınırını aşmaması için kırpıyoruz
  if len(sql_kodu) > 12000:
    sql_kodu = (
        sql_kodu[:12000]
        + "\n\n[... Kod çok uzun olduğu için son kısım kırpıldı ...]"
    )

  final_prompt = f"""
    Sen kıdemli ve titiz bir veri analitiği mentörüsün. 
    Aşağıda veritabanı şeması ve bu şemaya göre öğrencinin yazdığı SQL sorguları veriliyor. 
    
    Lütfen bu kodu dikkatle incele ve yanıtını kesinlikle şu formatta ver:

    1. **TOPLAM PUAN:** [Ödev toplam 33 sorudan oluşmaktadır. Puanlama 100 üzerinden DEĞİLDİR. 
    Her doğru soru 1 puandır. Kesinlikle "Doğru Sayısı / 33" formatında (Örn: 33/33, 28/33 gibi) net bir skor yaz.]
    2. **SORU BAZLI DEĞERLENDİRME:** (Öğrencinin yazdığı sorguları sırayla ele al; hangileri doğru, hangilerinde hata var tek tek açıkla)

    3. **MENTÖRÜN TAVSİYELERİ:** (Öğrencinin kendini geliştirmesi için kısa öneriler) 
    
    
    ---
    VERİTABANI ŞEMASI:
    {sema_icerigi}

    ---
    ÖĞRENCİNİN SQL KODLARI:
    {sql_kodu}
    """

  try:
    AI_Response = llm_gpt.invoke(final_prompt)
    return AI_Response.content
  except Exception as e:
    return (
        "⚠️ **Değerlendirme Hatası:** Bu öğrencinin ödevi işlenirken model"
        f" sınırlarına takıldı veya bir API hatası oluştu.\n\nDetay: {str(e)}"
    )
