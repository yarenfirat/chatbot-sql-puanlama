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
  if not report_text:
    return "0/33"
  match = re.search(r"TOPLAM PUAN:\s*([^\n\r]+)", report_text, re.IGNORECASE)
  raw_puan = match.group(1).strip() if match else report_text

  if "0/100" in raw_puan:
    return "0/33"
  if "100/100" in raw_puan:
    return "33/33"

  frac_match = re.search(r"(\d+)\s*/\s*(\d+)", raw_puan)
  if frac_match:
    dogru = int(frac_match.group(1))
    toplam = int(frac_match.group(2))
    if toplam == 33:
      return f"{dogru}/33"
    elif toplam > 0:
      hesaplanan = round((dogru / toplam) * 33)
      return f"{min(33, max(0, hesaplanan))}/33"

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

  if st.sidebar.button(
      "🚀 Eksikleri Tara ve Güncelle (Notu Olanlar Doğrudan Atlanır)"
  ):
    student_folders = list_student_folders()

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

    atlanansayisi = 0
    taranansayisi = 0

    for idx, (student_name, folder_id) in enumerate(
        student_folders.items(), start=1
    ):
      mevcut_puan = cache_data.get(student_name, {}).get("puan", "")

      # 1. AKILLI ATLA: Notu zaten X/33 olanları tek kuruş harcamadan doğrudan hafızadan al
      if re.match(r"^\d+/33$", str(mevcut_puan)):
        atlanansayisi += 1
        status_text.text(
            f"[{idx}/{total_students}] {student_name} hafızadan alındı"
            " (Atlandı ✅)"
        )
        results.append({"Öğrenci Adı": student_name, "Puan": mevcut_puan})
        progress_bar.progress(idx / total_students)
        continue

      # 2. SADECE ÖDEVİ OLMAYANLARI/EKSİKLERİ KONTROL ET
      taranansayisi += 1
      status_text.text(
          f"[{idx}/{total_students}] {student_name} Drive kontrol ediliyor"
          " (Ödev Yok idi)..."
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

      cache_data[student_name] = {
          "puan": puan,
          "dosya_adi": msg,
          "detayli_rapor": report,
          "sql_kodu": sql_kodu if sql_kodu else "",
      }

      results.append({"Öğrenci Adı": student_name, "Puan": puan})
      progress_bar.progress(idx / total_students)

    with open(CACHE_JSON, "w", encoding="utf-8") as f:
      json.dump(cache_data, f, ensure_ascii=False, indent=4)

    df_results = pd.DataFrame(results)
    df_results.to_csv(output_csv, index=False, encoding="utf-8-sig")
    df_results.to_excel(output_excel, index=False)

    status_text.empty()
    progress_bar.empty()
    st.sidebar.success(
        f"🎉 Tamamlandı! {atlanansayisi} öğrenci hafızadan alındı, sadece"
        f" {taranansayisi} eksik kontrol edildi."
    )
    st.rerun()

elif admin_password_input and admin_password_input != correct_password:
  st.sidebar.error("❌ Hatalı şifre!")
else:
  st.sidebar.info("🔒 Toplu tarama yapmak için yönetici şifresini girin.")

st.sidebar.markdown("---")

# İndirme Butonları
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

# --- ANA EKRAN: TEKLİ ARAMA ---
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

    student_info = cache_data.get(selected_student)

    if student_info:
      puan = student_info.get("puan", "-")

      st.success(
          f"✅ Rapor Yüklendi (Dosya: {student_info.get('dosya_adi', '-')})"
      )
      st.info(f"**Öğrenci:** {selected_student}")
      st.info(f"**Puan:** {puan}")

      # Eğer ödev yoksa Drive'ı anlık kontrol etme seçeneği sun
      if puan == "Ödev Yok" and service:
        st.warning(
            "⚠️ Bu öğrenci daha önce ödev yüklememişti. Yeni ödev yüklediyse"
            " kontrol edebilirsiniz:"
        )
        if st.button("🔄 Drive'ı Kontrol Et ve Notlandır"):
          folder_id = matched_students[selected_student]
          with st.spinner("Drive taranıyor..."):
            cekilen_sql, cekilen_msg = get_sql_file_from_student_folder(
                service, folder_id
            )
            if cekilen_sql:
              yeni_rapor = evaluate_student_sql(cekilen_sql)
              yeni_puan = temiz_puan_ayikla(yeni_rapor)

              cache_data[selected_student] = {
                  "puan": yeni_puan,
                  "dosya_adi": cekilen_msg,
                  "detayli_rapor": yeni_rapor,
                  "sql_kodu": cekilen_sql,
              }
              with open(CACHE_JSON, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=4)

              st.success("Ödev bulundu ve notlandırıldı!")
              st.rerun()
            else:
              st.error(f"Hala dosya bulunamadı: {cekilen_msg}")

      st.markdown("---")
      st.markdown("### 📝 Detaylı Değerlendirme Raporu")
      ham_rapor = student_info.get("detayli_rapor", "Rapor metni bulunamadı.")
      duzeltilmis_rapor = re.sub(
          r"(TOPLAM PUAN:\s*)([^\n\r]+)",
          rf"\g<1>{puan}",
          ham_rapor,
          count=1,
          flags=re.IGNORECASE,
      )
      st.markdown(duzeltilmis_rapor)

      ogrenci_sql = student_info.get("sql_kodu")
      if ogrenci_sql:
        with st.expander("📄 Öğrencinin Yüklediği Orijinal SQL Kodunu Gör"):
          st.code(ogrenci_sql, language="sql")
    else:
      st.warning("⚠️ Bu öğrenci henüz taranmamış.")
  else:
    st.info("Aradığınız kritere uygun öğrenci bulunamadı.")