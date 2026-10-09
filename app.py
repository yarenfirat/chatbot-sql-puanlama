import streamlit as st
from loaders import find_and_load_student_sql
from raghelper import evaluate_student_sql as evaluate_student_code

st.set_page_config(page_title="Mentor Cockpit - SQL Değerlendirme", layout="wide")
st.title("Mentor Cockpit: Öğrenci SQL Ödev Değerlendirme")
st.divider()

# Ekranı iki sütuna bölelim: Sol taraf giriş alanı, sağ taraf sonuç raporu
col_input, col_result = st.columns([1, 2])

with col_input:
    st.subheader("Öğrenci Arama")
    student_name_input = st.text_input(label="Öğrencinin Adını ve Soyadını Giriniz:")
    st.divider()
    submit_btn = st.button(label="Ödevi Değerlendir", key="eval_button")

if submit_btn:
    if not student_name_input:
        st.warning("Lütfen değerlendirmek istediğiniz öğrencinin adını girin.")
    else:
        with st.spinner("Öğrenci dosyası aranıyor ve o1 modeliyle değerlendiriliyor..."):
            
            # 1. Aşama: loaders.py ile dosyayı bul ve oku
            load_result = find_and_load_student_sql(student_name=student_name_input)
            
            if "error" in load_result:
                st.error(load_result["error"])
            else:
                dosya_adi = load_result["dosya_adi"]
                sql_kodu = load_result["sql_kodu"]
                
                # 2. Aşama: rag.py (değerlendirme fonksiyonu) ile modeli çalıştır
                ai_evaluation = evaluate_student_code(sql_kodu=sql_kodu)
                
                # 3. Aşama: Sonuçları ekrana yazdır
                # Sonuçları ekrana yazdırırken
                with col_result:
                    st.success(f"Başarılı! Bulunan Dosya: {dosya_adi}")
                    
                    # Puan ve Rapor
                    st.markdown("### 🤖 Yapay Zeka Değerlendirme ve Puanlama Raporu")
                    st.markdown(ai_evaluation)
                    st.divider()
                    
                    with st.expander("Öğrencinin Orijinal SQL Kodunu Gör"):
                        st.code(sql_kodu, language="sql")