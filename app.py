import streamlit as st
from loaders import get_oauth_drive_service, list_student_folders

st.title("Tek Seferlik Harita Çıkarıcı")

# ID'yi tarayıcıdaki orijinal haline göre düzelttim (VIg değil Vlg)
PARENT_FOLDER_ID = "1_E3hv4U032hF7TRQFI129XAoyVlgXpwU"

service = get_oauth_drive_service()

if service:
    st.info("Lütfen asıl hesabınla giriş yap!")
    if st.button("74 Öğrencinin Haritasını Çıkar"):
        with st.spinner("Klasörler taranıyor..."):
            student_folders = list_student_folders(service, PARENT_FOLDER_ID)
            st.success(f"Toplam {len(student_folders)} klasör bulundu!")
            st.code(str(student_folders), language="python")
else:
    st.info("Lütfen giriş yapın.")