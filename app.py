import json
import os
import re
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
CACHE_JSON = "rapor_cache.json"

# --- SOL MENÜ: TOPLU RAPOR YÖNETİMİ & YETKİ ---
st.sidebar.subheader("📊 Toplu Rapor Yönetimi")

admin_password_input = st.sidebar.text_input(
    "🔑 Yönetici Şifresi", type="password", placeholder="Şifreyi giriniz..."
)
correct_password = st.secrets.get("admin_password", "miuul2026")

service = get_oauth_drive_service()

if service and admin_password_input == correct_password:
  st.sidebar.success("🔓 Yönetici Yetkisi Aktif")

  if st.sidebar.button(
      "🚀 Eksikleri Tara ve Raporu Güncelle (Akıllı Mod: Varolanı Atlar)"
  ):
    student_folders = list_student_folders()

    # Önceden kaydedilmiş detaylı rapor cache'ini yükleyelim
    cache_data = {}
    if os.path.exists(CACHE_JSON):
      try:
        with open(CACHE_JSON, "r", encoding="utf-8") as f:
          cache_data = json.load(f)
      except Exception:
        pass

    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    total_students = len(student_folders)

    for idx, (student_name, folder_id) in enumerate(
        student_folders.items(), start=1
    ):
      # AKILLI KONTROL: Öğrencinin cache'te zaten geçerli raporu varsa atla!
      if (
          student_name in cache_data
          and cache_data[student_name].get("puan")
          not in ["Bulunamadı", "Hata", "Ödev Yok"]
          and not str(cache_data[student_name].get("puan")).startswith("Hata")
      ):
        # Sadece Ad ve Puan (CSV/Excel için)
        results.append({
            "Öğrenci Adı": student_name,
            "Puan": cache_data[student_name]["puan"],
        })
        progress_bar.progress(idx / total_students)
        continue

      status_text.text(
          f"[{idx}/{total_students}] {student_name} ödevi inceleniyor..."
      )
      sql_kodu, msg = get_sql_file_from_student_folder(service, folder_id)

      puan = "Bulunamadı"
      report = "Ödev Bulunamadı veya İncelenemedi."

      if sql_kodu:
        try:
          report = evaluate_student_sql(sql_kodu)
          match = re.search(r"TOPLAM PUAN:\s*([^\n]+)", report, re.IGNORECASE)
          if match:
            puan = match.group(1).strip()
          else:
            puan = "Değerlendirildi"
        except Exception as api_err:
          report = f"Hata Detayı: {str(api_err)}"
          puan = "Hata"
      else:
        report = f"Dosya durumu: {msg}"
        puan = "Ödev Yok"

      # Cache'e detaylı raporu kaydediyoruz (Tekil arama için)
      cache_data[student_name] = {
          "puan": puan,
          "dosya_adi": msg,
          "detayli_rapor": report,
      }

      # CSV ve Excel için SADECE İsim ve Puan ekliyoruz
      results.append({"Öğrenci Adı": student_name, "Puan": puan})
      progress_bar.progress(idx / total_students)

    # Cache dosyasını güncelle
    with open(CACHE_JSON, "w", encoding="utf-8") as f:
      json.dump(cache_data, f, ensure_ascii=False, indent=4)

    # CSV ve Excel dosyalarını SADECE İsim ve Puan içerecek şekilde kaydet
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_csv, index=False, encoding="utf-8-sig")
    df_results.to_excel(output_excel, index=False)

    status_text.empty()
    progress_bar.empty()
    st.sidebar.success("🎉 Raporlar güncellendi! CSV ve Excel tertemiz kaydedildi.")
    st.rerun()
elif admin_password_input and admin_password_input != correct_password:
  st.sidebar.error("❌ Hatalı şifre!")
else:
  st.sidebar.info(
      "🔒 Toplu tarama yapmak için yönetici şifresini girin (Sadece eksikler"
      " taranır)."
  )

st.sidebar.markdown("---")

# İndirme Butonları (İndirilen dosyalarda sadece İsim ve Puan yazar)
if os.path.exists(output_excel) and os.path.exists(output_csv):
  with open(output_excel, "rb") as f:
    excel_bytes = f.read()

  st.sidebar.download_button(
      label="📊 Tüm Sınıfı Excel İndir (İsim ve Puan)",
      data=excel_bytes,
      file_name="tum_ogrenci_sql_puanlari.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )

  with open(output_csv, "rb") as f:
    csv_bytes = f.read()

  st.sidebar.download_button(
      label="📄 Tüm Sınıfı CSV İndir (İsim ve Puan)",
      data=csv_bytes,
      file_name="tum_ogrenci_sql_puanlari.csv",
      mime="text/csv",
  )
  st.sidebar.success("✅ İndirme dosyaları hazır.")
else:
  st.sidebar.info("ℹ️ Henüz toplu tarama yapılmamış.")

st.sidebar.markdown("---")

# --- ANA EKRAN: TEKLİ ARAMA (DETAYLI RAPORLAR CACHE'TEN GELİR, TOKEN YAKMAZ) ---
st.subheader("🔍 Öğrenci Detaylı Rapor Sorgulama")

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

    # Gizli cache'ten (veya CSV'den bağımsız arka plan verisinden) detaylı raporu çekelim
    cache_data = {}
    if os.path.exists(CACHE_JSON):
      try:
        with open(CACHE_JSON, "r", encoding="utf-8") as f:
          cache_data = json.load(f)
      except Exception:
        pass

    if selected_student in cache_data:
      student_info = cache_data[selected_student]
      st.success(f"✅ Öğrenci Raporu Yüklendi (Dosya: {student_info.get('dosya_adi', '-')})")
      st.info(f"**Öğrenci Adı:** {selected_student}")
      st.info(f"**Puan:** {student_info.get('puan', '-')}")

      st.markdown("---")
      st.markdown("### 📝 Detaylı Değerlendirme Raporu")
      st.markdown(student_info.get("detayli_rapor", "Rapor bulunamadı."))
    else:
      st.warning(
          "⚠️ Bu öğrenci henüz taranmamış. Toplu tarama yapıldığında detayları buraya gelecektir."
      )
      if service and st.button("Anlık Olarak Tekrar Değerlendir (Token Harcar)"):
        student_folder_id = matched_students[selected_student]
        with st.spinner(f"{selected_student} ödevi Drive'dan inceleniyor..."):
          sql_kodu, file_name = get_sql_file_from_student_folder(
              service, student_folder_id
          )
          if sql_kodu:
            st.success(f"Başarılı! Bulunan Dosya: {file_name}")
            report = evaluate_student_sql(sql_kodu)
            st.markdown(report)
            with st.expander("Orijinal SQL Kodunu Gör"):
              st.code(sql_kodu, language="sql")
          else:
            st.warning(file_name)
      elif not service:
        st.info("Tekli anlık tarama için lütfen Google ile giriş yapın.")
  else:
    st.info("Aradığınız kritere uygun öğrenci bulunamadı.")