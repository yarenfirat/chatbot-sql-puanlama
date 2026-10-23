import streamlit as st
from loaders import get_oauth_drive_service, list_student_folders, get_sql_file_from_student_folder
from raghelper import evaluate_student_sql

st.title("Mentor Cockpit: Öğrenci SQL Ödev Değerlendirme")

service = get_oauth_drive_service()

if service:
    # Artık Drive'da klasör aramıyor, loaders.py içindeki sabit listemizi saniyesinde çekiyor
    student_folders = list_student_folders()
    
    search_query = st.text_input("Değerlendirilecek Öğrencinin Adını Yazın (örn: İsim Soyisim):", "")
    matched_students = {name: fid for name, fid in student_folders.items() if search_query.lower() in name.lower()}
    
    if search_query:
        if matched_students:
            selected_student = st.selectbox("Eşleşen Öğrenciler:", list(matched_students.keys()))
            student_folder_id = matched_students[selected_student]
            
            if st.button("Ödevi Değerlendir"):
                with st.spinner(f"{selected_student} adlı öğrencinin ödevi Google Drive'dan okunuyor ve model inceliyor..."):
                    sql_code, file_name = get_sql_file_from_student_folder(service, student_folder_id)
                    
                    if sql_code:
                        st.success(f"Başarılı! Bulunan Dosya: {file_name}")
                        report = evaluate_student_sql(sql_code)
                        st.markdown(report)
                        with st.expander("Öğrencinin Orijinal SQL Kodunu Gör"):
                            st.code(sql_code, language="sql")
                    else:
                        st.warning(file_name)
        else:
            st.info("Aradığınız kritere uygun öğrenci bulunamadı.")
else:
    st.info("Google Drive'a bağlanmak için lütfen yetkilendirmeyi tamamlayın.")