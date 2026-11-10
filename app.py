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

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Miuul Mentor & AI Değerlendirme Portalı",
    layout="wide",
    page_icon="🎓",
)

# ==========================================
# 1. EN ÜST KATMAN: PORTAL GEZİNME PANELİ
# ==========================================
st.sidebar.title("🧭 Gezinme Paneli")
ana_alan = st.sidebar.radio(
    "Geçiş Yapılacak Alan:",
    ["🤖 AI Değerlendirme Hub'ı", "📊 Mentor Cockpit"],
    index=0,
)

st.sidebar.markdown("---")

# ==========================================
# ALAN 1: MENTOR COCKPIT
# ==========================================
if ana_alan == "📊 Mentor Cockpit":
  st.title("📊 Miuul Mentor Cockpit")
  st.caption(
      "Öğrenci genel ilerleme durumu, katılım takip metrikleri ve haftalık özet"
      " paneli."
  )

  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Toplam Öğrenci", "73")
  col2.metric("Aktif Takip Edilen", "DA11")
  col3.metric("Tamamlanan Modüller", "1_CRM, 2_SQL")
  col4.metric("Devam Eden Modül", "3_PowerBI")

  st.info(
      "💡 Mentor Cockpit göstergeleri ve Google Sheets / RFM takip tabloları"
      " bu ekrana bağlanacaktır."
  )


# ==========================================
# ALAN 2: AI DEĞERLENDİRME HUB'I
# ==========================================
elif ana_alan == "🤖 AI Değerlendirme Hub'ı":
  secilen_modul = st.sidebar.selectbox(
      "📚 Değerlendirilecek Modülü Seçin:",
      [
          "SQL",
          "CRM Analytics (Excel)",
          "Power BI",
          "Machine Learning (Python)",
      ],
      index=0,
  )

  # ----------------------------------------------------
  # MODÜL: 2_SQL ★
  # ----------------------------------------------------
  if secilen_modul == "SQL":
    st.title("⚡ SQL Ödev Değerlendirme (33 Soru)")
    st.caption(
        "Northwind & CRM veri tabanı üzerinden hazırlanan 33 soruluk SQL"
        " bitirme projelerinin AI destekli analizi."
    )

    output_excel = "tum_ogrenci_sql_puanlari.xlsx"
    output_csv = "tum_ogrenci_sql_puanlari.csv"
    CACHE_JSON = "rapor_cache.json"

    def temiz_puan_ayikla(report_text):
      if not report_text:
        return "0/33"
      match = re.search(
          r"TOPLAM PUAN:\s*([^\n\r]+)", report_text, re.IGNORECASE
      )
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

    # Sol Menü: Yönetici & Toplu Rapor
    st.sidebar.subheader("📊 SQL Toplu Rapor Yönetimi")
    admin_password_input = st.sidebar.text_input(
        "🔑 Yönetici Şifresi",
        type="password",
        placeholder="Şifreyi giriniz...",
        key="sql_admin_pass",
    )
    correct_password = st.secrets.get("admin_password", "miuul2026")
    service = None

    if admin_password_input == correct_password:
      st.sidebar.success("🔓 Yönetici Girişi Yapıldı")
      with st.sidebar:
        service = get_oauth_drive_service()

      if service:
        # BUTON 1: TOPLU TARAMA
        if st.sidebar.button(
            "🚀 Eksikleri Tara ve Güncelle (0 Puan ve Boşlar Taranır)"
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
          progress_bar = st.sidebar.progress(0)
          status_text = st.sidebar.empty()
          total_students = len(student_folders)

          atlanansayisi = 0
          taranansayisi = 0

          for idx, (student_name, folder_id) in enumerate(
              student_folders.items(), start=1
          ):
            mevcut_puan = cache_data.get(student_name, {}).get("puan", "")

            # 0/33 VE 'Ödev Yok' OLANLARI ATLAMAZ, TEKRAR OKUR
            if (
                re.match(r"^\d+/33$", str(mevcut_puan))
                and mevcut_puan != "0/33"
            ):
              atlanansayisi += 1
              results.append(
                  {"Öğrenci Adı": student_name, "Puan": mevcut_puan}
              )
              progress_bar.progress(idx / total_students)
              continue

            taranansayisi += 1
            status_text.text(
                f"[{idx}/{total_students}] {student_name} taranıyor..."
            )
            sql_kodu, msg = get_sql_file_from_student_folder(service, folder_id)

            if sql_kodu:
              try:
                report = evaluate_student_sql(sql_kodu)
                puan = temiz_puan_ayikla(report)
              except Exception as api_err:
                report = f"Hata: {str(api_err)}"
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
              f"🎉 Bitti! ({atlanansayisi} hafızadan korundu, {taranansayisi}"
              " yeniden tarandı)"
          )
          st.rerun()

        # BUTON 2: SIFIR TOKEN İLE SQL KODLARINI HAFIZAYA ÇEKME
        if st.sidebar.button(
            "📥 Eksik SQL Kodlarını Drive'dan Çek (0 Token - Bedava)"
        ):
          student_folders = list_student_folders()
          cache_data = {}
          if os.path.exists(CACHE_JSON):
            try:
              with open(CACHE_JSON, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            except Exception:
              pass

          progress_bar = st.sidebar.progress(0)
          status_text = st.sidebar.empty()
          total_students = len(student_folders)
          guncellenen = 0

          for idx, (student_name, folder_id) in enumerate(
              student_folders.items(), start=1
          ):
            if student_name in cache_data and not cache_data[student_name].get(
                "sql_kodu"
            ):
              status_text.text(
                  f"[{idx}/{total_students}] {student_name} SQL kodu"
                  " alınıyor..."
              )
              sql_kodu, _ = get_sql_file_from_student_folder(service, folder_id)
              if sql_kodu:
                cache_data[student_name]["sql_kodu"] = sql_kodu
                guncellenen += 1
            progress_bar.progress(idx / total_students)

          with open(CACHE_JSON, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)

          status_text.empty()
          progress_bar.empty()
          st.sidebar.success(
              f"✅ {guncellenen} öğrencinin SQL kodu hafızaya kaydedildi!"
          )
          st.rerun()

    elif admin_password_input and admin_password_input != correct_password:
      st.sidebar.error("❌ Hatalı şifre!")
    else:
      st.sidebar.info("🔒 SQL toplu tarama için yönetici şifresini girin.")

    st.sidebar.markdown("---")

    # İNDİRME BUTONLARI: EXCEL, CSV VE BULUTTAN JSON ÇEKME
    st.sidebar.subheader("📥 Rapor ve Veri Çıktıları")

    if os.path.exists(output_excel):
      with open(output_excel, "rb") as f:
        st.sidebar.download_button(
            label="📊 SQL Sınıf Notları (.xlsx)",
            data=f.read(),
            file_name="tum_ogrenci_sql_puanlari.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

    if os.path.exists(output_csv):
      with open(output_csv, "rb") as f:
        st.sidebar.download_button(
            label="📄 SQL Sınıf Notları (.csv)",
            data=f.read(),
            file_name="tum_ogrenci_sql_puanlari.csv",
            mime="text/csv",
        )

    # CANLIDAN BİLGİSAYARINA TEK TIKLA ÇEKEBİLECEĞİN JSON BUTONU
    if os.path.exists(CACHE_JSON):
      with open(CACHE_JSON, "rb") as f:
        st.sidebar.download_button(
            label="📦 Cache Dosyasını İndir (.json)",
            data=f.read(),
            file_name="rapor_cache.json",
            mime="application/json",
        )

    # SQL Arama ve Gösterim Ekranı
    st.subheader("🔍 Öğrenci Detaylı SQL Raporu Sorgula")
    student_folders = list_student_folders()
    search_query = st.text_input(
        "Öğrencinin Adını Yazın (örn: İsim Soyisim):", "", key="sql_search"
    )

    matched_students = {
        name: fid
        for name, fid in student_folders.items()
        if search_query.lower() in name.lower()
    }

    if search_query:
      if matched_students:
        selected_student = st.selectbox(
            "Eşleşen Öğrenciler:",
            list(matched_students.keys()),
            key="sql_select",
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
          col_a, col_b = st.columns(2)
          col_a.info(f"**Öğrenci:** {selected_student}")
          col_b.info(f"**Puan:** {puan}")

          st.markdown("---")
          st.markdown("### 📝 Detaylı Değerlendirme Raporu")
          ham_rapor = student_info.get(
              "detayli_rapor", "Rapor metni bulunamadı."
          )
          duzeltilmis_rapor = re.sub(
              r"(TOPLAM PUAN:\s*)([^\n\r]+)",
              rf"\g<1>{puan}",
              ham_rapor,
              count=1,
              flags=re.IGNORECASE,
          )
          st.markdown(duzeltilmis_rapor)

          ogrenci_sql = student_info.get("sql_kodu")

          # Eğer hafızada yoksa ve anlık olarak şifre girildiyse Drive'dan tamamla
          if not ogrenci_sql and service:
            fid = matched_students.get(selected_student)
            if fid:
              cekilen_sql, _ = get_sql_file_from_student_folder(service, fid)
              if cekilen_sql:
                ogrenci_sql = cekilen_sql
                student_info["sql_kodu"] = ogrenci_sql
                with open(CACHE_JSON, "w", encoding="utf-8") as f:
                  json.dump(cache_data, f, ensure_ascii=False, indent=4)

          st.markdown("---")
          if ogrenci_sql:
            with st.expander(
                "📄 Öğrencinin Yüklediği Orijinal SQL Kodunu Gör", expanded=True
            ):
              st.code(ogrenci_sql, language="sql")
          else:
            st.warning(
                "ℹ️ Bu öğrencinin SQL kodu henüz önbelleğe alınmamış. Sol"
                " menüden 'Eksik SQL Kodlarını Drive'dan Çek' butonuna"
                " basabilirsiniz."
            )
        else:
          st.warning("⚠️ Bu öğrenci henüz taranmamış.")
      else:
        st.info("Aradığınız kritere uygun öğrenci bulunamadı.")

  # ----------------------------------------------------
  # MODÜL: 1_CRM_Analytics (Excel / RFM)
  # ----------------------------------------------------
  elif secilen_modul == "CRM Analytics (Excel)":
    st.title("📑 CRM Analytics & Müşteri Segmentasyonu")
    st.caption(
        "Öğrencilerin teslim ettiği Excel (.xlsx) dosyalarından RFM metrikleri"
        " ve müşteri segmentasyon analizi."
    )
    st.info(
        "🚧 Bu modülün Excel okuyucusu ve değerlendirme motoru sıradaki adımda"
        " eklenecektir."
    )

  # ----------------------------------------------------
  # MODÜL: 3_PowerBI
  # ----------------------------------------------------
  elif secilen_modul == "Power BI":
    st.title("📊 Power BI Proje Değerlendirme")
    st.caption(
        "Power BI veri modeli (Star Schema), DAX hesaplamaları ve görsel pano"
        " hiyerarşisi incelemesi."
    )
    st.info("🚧 Bu modülün değerlendirme kuralları hazırlanmaktadır.")

  # ----------------------------------------------------
  # MODÜL: 4_MachineLearning (Python)
  # ----------------------------------------------------
  elif secilen_modul == "Machine Learning (Python)":
    st.title("🧠 Machine Learning Pipeline Değerlendirme")
    st.caption(
        "Python scriptleri (.py) ve Jupyter Notebook (.ipynb) üzerinden model"
        " pipeline analizi."
    )
    st.info("🚧 Bu modülün kod analiz motoru hazırlanmaktadır.")