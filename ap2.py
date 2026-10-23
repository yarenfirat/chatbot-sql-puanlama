import streamlit as st
from loaders import get_oauth_drive_service, list_student_folders

st.title("Tek Seferlik Klasör Haritalama (Extractor)")

# BURAYA 2_SQL ANA KLASÖRÜNÜN GERÇEK ID'SİNİ YAZ
PARENT_FOLDER_ID = "BURAYA_DOGRU_KLASOR_IDSINI_YAZ"

service = get_oauth_drive_service()

if service:
    st.info("Lütfen dosyaların asıl sahibi olan hesabınla (yrnfrt7@gmail.com) giriş yap!")
    if st.button("74 Öğrencinin Haritasını Çıkar"):
        with st.spinner("Klasörler taranıyor..."):
            student_folders = list_student_folders(service, PARENT_FOLDER_ID)
            
            st.success(f"Toplam {len(student_folders)} klasör bulundu!")
            st.write("Aşağıdaki kopyala butonuna basarak tüm listeyi al:")
            st.code(str(student_folders), language="python")
else:
    st.info("Google Drive'a bağlanmak için lütfen yetkilendirmeyi tamamlayın.")