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


def temiz_puan_ayikla(report_text):
  """Model ne kadar dağınık çıktı verirse versin, temiz bir X/33 skoru üretir."""
  if not report_text:
    return "0/33"

  # TOPLAM PUAN satırını bul
  match = re.search(r"TOPLAM PUAN:\s*([^\n\r]+)", report_text, re.IGNORECASE)
  raw_puan = match.group(1).strip() if match else report_text

  if "0/100" in raw_puan:
    return "0/33"
  if "100/100" in raw_puan:
    return "33/33"

  # Kesir ara (Örn: 26/27, 25/33, 12/15)
  frac_match = re.search(r"(\d+)\s*/\s*(\d+)", raw_puan)
  if frac_match:
    dogru = int(frac_match.group(1))
    toplam = int(frac_match.group(2))

    if toplam == 33:
      return f"{dogru}/33"
    elif toplam > 0:
      # Soru sayısı farklı geldiyse 33 üzerinden tam puana dönüştür
      hesaplanan = round((dogru / toplam) * 33)
      hesaplanan = min(33, max(0, hesaplanan))
      return f"{hesaplanan}/33"

  # Sadece sayı varsa
  num_match = re.search(r"\b(\d+)\b", raw_puan)
  if num_match:
    val = int(num_match.group(1))
    if val <= 33:
      return f"{val}/33"

  return "33/33"


# --- SOL MENÜ: TOPLU RAPOR YÖNETİMİ ---
st.sidebar.subheader("📊 Toplu Rapor Yönetimi")

admin_password_input = st.sidebar.text_input(
    "🔑 Yönetici Şifresi", type="password", placeholder="Şifreyi giriniz..."
)
correct_password = st.secrets.get("admin_password", "miuul2026")

service = get_oauth_drive_service()

if service and admin_password_input == correct_password:
  st.sidebar.success("🔓 Yönetici Yetkisi Aktif")

  if st.sidebar.button("🚀 Sınıfı Tara ve Güncelle (Akıllı Mod)"):
    student_folders = list_student_folders()

    # Mevcut cache'i oku
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
      # AKILLI ATLA: Puanı zaten temiz şekilde (X/33) alınmış olanları es geç, token harcama!
      mevcut_puan = cache_data.get(student_name, {}).get("puan", "")
      if re.match(r"^\d+/33$", str(mevcut_puan)):
        results.append({"Öğrenci Adı": student_name, "Puan": mevcut_puan})
        progress_bar.progress(idx / total_students)
        continue

      status_text.text(
          f"[{idx}/{total_students}] {student_name} ödevi inceleniyor..."
      )
      sql_kodu, msg = get_sql_file_from_student_folder(service, folder_id)

      if sql_kodu:
        try:
          report = evaluate_student_sql(sql_kodu)
          puan = temiz_puan_ayikla(report)
        except Exception as api_err:
          report = f"Hata Detayı: {str(api_err)}"
          puan = "0/33"
      else:
        report = f"Dosya durumu: {msg}"
        puan = "Ödev Yok"

      # Cache'e detaylı raporu yaz
      cache_data[student_name] = {
          "puan": puan,
          "dosya_adi": msg,
          "detayli_rapor": report,
      }

      # CSV ve Excel için SADECE İsim ve Puan
      results.append({"Öğrenci Adı": student_name, "Puan": puan})
      progress_bar.progress(idx / total_students)

    # Cache'i kaydet
    with open(CACHE_JSON, "w", encoding="utf-8") as f:
      json.dump(cache_data, f, ensure_ascii=False, indent=4)

    # CSV ve Excel'e tertemiz kaydet
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_csv, index=False, encoding="utf-8-sig")
    df_results.to_excel(output_excel, index=False)

    status_text.empty()
    progress_bar.empty()
    st.sidebar.success("🎉 Raporlar başarıyla güncellendi!")
    st.rerun()
elif admin_password_input and admin_password_input != correct_password:
  st.sidebar.error("❌ Hatalı şifre!")
else:
  st.sidebar.info("🔒 Toplu tarama yapmak için yönetici şifresini girin.")

st.sidebar.markdown("---")

# İndirme Butonları (Sadece İsim ve Puan indirir)
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
  st.sidebar.success("✅ Raporlar hazır.")
else:
  st.sidebar.info("ℹ️ Henüz toplu tarama yapılmamış.")

st.sidebar.markdown("---")

# --- ANA EKRAN: TEKLİ ARAMA (CACHE'TEN OKUR, SIFIR TOKEN) ---
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

    cache_data = {}
    if os.path.exists(CACHE_JSON):
      try:
        with open(CACHE_JSON, "r", encoding="utf-8") as f:
          cache_data = json.load(f)
      except Exception:
        pass

    if selected_student in cache_data:
      student_info = cache_data[selected_student]
      st.success(
          f"✅ Rapor Yüklendi (Dosya: {student_info.get('dosya_adi', '-')})"
      )
      st.info(f"**Öğrenci:** {selected_student}")
      st.info(f"**Puan:** {student_info.get('puan', '-')}")

      st.markdown("---")
      st.markdown("### 📝 Detaylı Değerlendirme Raporu")
      st.markdown(student_info.get("detayli_rapor", "Rapor metni bulunamadı."))
    else:
      st.warning(
          "⚠️ Bu öğrenci henüz taranmamış. Sol menüden toplu tarama"
          " yapabilirsiniz."
      )
  else:
    st.info("Aradığınız kritere uygun öğrenci bulunamadı.")