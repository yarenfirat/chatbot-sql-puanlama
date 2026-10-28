import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

if "openai_key" in st.secrets:
    my_key_openai = st.secrets["openai_key"]
else:
    my_key_openai = os.getenv("openai_key")

llm_gpt = ChatOpenAI(
    api_key=my_key_openai,
    model="gpt-4o"
)

# Parametre adını 'sql_kodu' yaptık ki app.py ile uyuşsun
def evaluate_student_sql(sql_kodu: str, schema_path="schemas/odev1_sema.txt"):
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            sema_icerigi = f.read()
    else:
        sema_icerigi = "Veritabanı şeması bulunamadı."

    final_prompt = f"""
    Sen kıdemli ve titiz bir veri analitiği mentörüsün. 
    Aşağıda veritabanı şeması ve bu şemaya göre öğrencinin yazdığı SQL sorguları veriliyor. 
    
    Lütfen bu kodu dikkatle incele ve yanıtını kesinlikle şu formatta ver:

    1. **TOPLAM PUAN:** [Her soru için puan 1 ya da 0 olacak şekilde değerlendir. Çıktıyı doğru veren her sorguya tam puan (1) ver; 
    ekonomik/optimal olmayan ama doğru sonuç veren sorgulara da tam puan (1) ver ancak alternatif/daha performanslı bir çözüm için yapıcı uyarıda bulun. 
    Toplam skoru X/100 veya soru başı özet şeklinde belirt]
    2. **SORU BAZLI DEĞERLENDİRME:** (Öğrencinin yazdığı sorguları sırayla ele al; hangileri doğru, hangilerinde hata var tek tek açıkla)
    3. **MENTÖRÜN TAVSİYELERİ:** (Öğrencinin kendini geliştirmesi için kısa öneriler)

    ---
    VERİTABANI ŞEMASI:
    {sema_icerigi}

    ---
    ÖĞRENCİNİN SQL KODLARI:
    {sql_kodu}
    """

    AI_Response = llm_gpt.invoke(final_prompt)
    return AI_Response.content