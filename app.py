import os
import pandas as pd
import streamlit as st
from loaders import (
    get_oauth_drive_service,
    get_sql_file_from_student_folder,
    list_student_folders,
)
from raghelper import evaluate_student_sql

st.title("Mentor Cockpit: Öğrenci SQL Ödev Değerlendirme")

# --- SOL MENÜ: TOPLU RAPORLARI İNDİR ---
st.sidebar.subheader("📊 Toplu Raporlar")
output_excel = "tum_ogrenci_sql_puanlari.xlsx"
output_csv = "tum_ogrenci_sql_puanlari.csv"

# Eğer run_batch.py çalıştırılmışsa ve dosyalar klasörde varsa butonları göster
if os.path.exists(output_excel) and os.path.exists(output_csv):
  # Excel dosyasını okumaya hazırla
  with open(output_excel, "rb") as f:
    excel_bytes = f.read()

  st.sidebar.download_button(
      label="📊 Tüm Sınıfı Excel İndir (.xlsx)",
      data=excel_bytes,
      file_name="tum_ogrenci_sql_puanlari.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )

  # CSV dosyasını okumaya hazırla
  with open(output_csv, "rb") as f:
    csv_bytes = f.read()

  st.sidebar.download_button(
      label="📄 Tüm Sınıfı CSV İndir (.csv)",
      data=csv_bytes,
      file_name="tum_ogrenci_sql_puanlari.csv",
      mime="text/csv",
  )
  st.sidebar.success(
      "✅ Toplu raporlar hazır. (Terminalden güncelledikçe buradaki butonlar da"
      " güncellenir)"
  )
else:
  st.sidebar.info(
      "ℹ️ Henüz toplu tarama yapılmamış. Toplu raporları indirmek için terminalde"
      " `python run_batch.py` çalıştırın."
  )

st.sidebar.markdown("---")

# --- ANA EKRAN: TEKLİ ARAMA VE DEĞERLENDİRME ---
service = get_oauth_drive_service()

if service:
  student_folders = list_student_folders()

  search_query = st.text_input(
      "Değerlendirilecek Öğrencinin Adını Yazın (örn: İsim Soyisim):", ""
  )
  matched_students = {
      name: fid
      for name, fid in student_folders.items()
      if search_query.lower() in name.lower()
  }

  if search_query:
    if matched_students:
      selected_student = st.selectbox(
          "Eşleşen Öğrenciler:", list(matched_students.keys())
      )
      student_folder_id = matched_students[selected_student]

      if st.button("Ödevi Değerlendir"):
        with st.spinner(
            f"{selected_student} adlı öğrencinin ödevi Google Drive'dan okunuyor"
            " ve model inceliyor..."
        ):
          sql_kodu, file_name = get_sql_file_from_student_folder(
              service, student_folder_id
          )

          if sql_kodu:
            st.success(f"Başarılı! Bulunan Dosya: {file_name}")
            report = evaluate_student_sql(sql_kodu)
            st.markdown(report)
            with st.expander("Öğrencinin Orijinal SQL Kodunu Gör"):
              st.code(sql_kodu, language="sql")
          else:
            st.warning(file_name)
    else:
      st.info("Aradığınız kritere uygun öğrenci bulunamadı.")
else:
  st.info("Google Drive'da bağlanmak için lütfen yetkilendirmeyi tamamlayın.")