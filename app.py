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

output_excel = "tum_ogrenci_sql_puanlari.xlsx"
output_csv = "tum_ogrenci_sql_puanlari.csv"

# --- SOL MENÜ: TOPLU RAPOR YÖNETİMİ VE TARAMA BUTONU ---
st.sidebar.subheader("📊 Toplu Rapor Yönetimi")

# Google servisini almayı dene
service = get_oauth_drive_service()

if service:
  if st.sidebar.button("🚀 Tüm Sınıfı Tara ve Raporu Güncelle"):
    student_folders = list_student_folders()
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    total_students = len(student_folders)

    for idx, (student_name, folder_id) in enumerate(
        student_folders.items(), start=1
    ):
      status_text.text(
          f"[{idx}/{total_students}] {student_name} ödevi inceleniyor..."
      )
      sql_kodu, msg = get_sql_file_from_student_folder(service, folder_id)

      if sql_kodu:
        report = evaluate_student_sql(sql_kodu)
        results.append({
            "Öğrenci Adı": student_name,
            "Dosya Adı": msg,
            "Durum": "Başarılı",
            "Değerlendirme Raporu": report,
        })
      else:
        results.append({
            "Öğrenci Adı": student_name,
            "Dosya Adı": "-",
            "Durum": msg,
            "Değerlendirme Raporu": "Ödev Bulunamadı",
        })

      progress_bar.progress(idx / total_students)

    df_results = pd.DataFrame(results)
    df_results.to_csv(output_csv, index=False, encoding="utf-8-sig")
    df_results.to_excel(output_excel, index=False)

    status_text.empty()
    progress_bar.empty()
    st.sidebar.success("🎉 Tüm sınıf başarıyla tarandı ve rapor kaydedildi!")
    st.rerun()
else:
  st.sidebar.warning(
      "⚠️ Google Drive bağlantısı bekleniyor. Lütfen önce giriş yapın."
  )

st.sidebar.markdown("---")

# Rapor dosyaları diskte var mı kontrol et ve indirme butonlarını göster
if os.path.exists(output_excel) and os.path.exists(output_csv):
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

  with open(output_csv, "rb") as f:
    csv_bytes = f.read()

  st.sidebar.download_button(
      label="📄 Tüm Sınıfı CSV İndir (.csv)",
      data=csv_bytes,
      file_name="tum_ogrenci_sql_puanlari.csv",
      mime="text/csv",
  )
  st.sidebar.success("✅ Toplu raporlar indirilmeye hazır.")
else:
  st.sidebar.info(
      "ℹ️ Henüz toplu tarama dosyası oluşturulmamış. Yukarıdaki butona basarak"
      " tarama yapabilirsiniz."
  )

st.sidebar.markdown("---")

# --- ANA EKRAN: TEKLİ ARAMA VE DEĞERLENDİRME ---
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