import json
import os
import re
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# 1. Drive Servisi ve SQL Modülleri
from loaders_sql import (
    get_oauth_drive_service,
    get_sql_file_from_student_folder,
    list_student_folders as list_sql_student_folders,
)
from raghelper_sql import evaluate_student_sql

# 2. CRM Modülleri
from loaders_crm import (
    get_crm_excel_from_student_folder,
    list_crm_student_folders,
)
from raghelper_crm import evaluate_student_crm

# 3. Power BI Modülleri
from loaders_pbi import (
    get_pbi_file_from_student_folder,
    list_pbi_student_folders,
)
from raghelper_pbi import evaluate_student_pbi

# 4. Machine Learning Modülleri
from loaders_ml import (
    get_ml_file_from_student_folder,
    list_ml_student_folders,
)
from raghelper_ml import evaluate_student_ml

# Sayfa Ayarları
st.set_page_config(
    page_title="Miuul Mentor & AI Değerlendirme Portalı",
    layout="wide",
    page_icon="🎓",
)


# Puan Ayıklama Yardımcı Fonksiyonları
def temiz_puan_ayikla_sql(report_text):
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
    dogru, toplam = int(frac_match.group(1)), int(frac_match.group(2))
    return (
        f"{dogru}/33"
        if toplam == 33
        else f"{min(33, max(0, round((dogru / toplam) * 33)))}/33"
    )
  num_match = re.search(r"\b(\d+)\b", raw_puan)
  return f"{int(num_match.group(1))}/33" if num_match else "33/33"


def temiz_puan_ayikla_100(report_text):
  if not report_text:
    return "0/100"
  match = re.search(r"TOPLAM PUAN:\s*([^\n\r]+)", report_text, re.IGNORECASE)
  raw_puan = match.group(1).strip() if match else report_text
  frac_match = re.search(r"(\d+)\s*/\s*(\d+)", raw_puan)
  if frac_match:
    dogru, toplam = int(frac_match.group(1)), int(frac_match.group(2))
    return (
        f"{dogru}/100"
        if toplam == 100
        else f"{min(100, max(0, round((dogru / toplam) * 100)))}/100"
    )
  num_match = re.search(r"\b(\d+)\b", raw_puan)
  return (
      f"{int(num_match.group(1))}/100"
      if (num_match and int(num_match.group(1)) <= 100)
      else "0/100"
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

# Güvenli Yönetici Girişi
st.sidebar.subheader("🔑 Yönetici Erişimi")
admin_password_input = st.sidebar.text_input(
    "Yönetici Şifresi",
    type="password",
    placeholder="Şifreyi giriniz...",
    key="global_admin_pass",
)
correct_password = st.secrets.get("admin_password")
is_admin = bool(correct_password and admin_password_input == correct_password)
service = None

if is_admin:
  st.sidebar.success("🔓 Yönetici Yetkisi Aktif")
  with st.sidebar:
    service = get_oauth_drive_service()
elif admin_password_input:
  st.sidebar.error("❌ Hatalı şifre!")

st.sidebar.markdown("---")


# ==========================================
# ALAN 1: MENTOR COCKPIT (Google Apps Script)
# ==========================================
if ana_alan == "📊 Mentor Cockpit":
  st.title("📊 Miuul Mentor Cockpit")
  st.caption("Google Apps Script üzerinde çalışan canlı mentör takip paneli.")

  cockpit_url = st.secrets.get("cockpit_url", "")

  if cockpit_url:
    col_c1, _ = st.columns([1, 4])
    with col_c1:
      st.link_button(
          "🔗 Paneli Yeni Sekmede Aç", cockpit_url, type="secondary"
      )
    st.markdown("---")
    components.iframe(cockpit_url, height=900, scrolling=True)
  else:
    st.warning("⚠️ 'cockpit_url' adresi .streamlit/secrets.toml içinde bulunamadı.")
    st.info(
        "Örnek: `cockpit_url ="
        " 'https://script.google.com/macros/s/.../exec'` şeklinde tanımlayın."
    )


# ==========================================
# ALAN 2: AI DEĞERLENDİRME HUB'I
# ==========================================
elif ana_alan == "🤖 AI Değerlendirme Hub'ı":
  secilen_modul = st.sidebar.selectbox(
      "📚 Değerlendirilecek Modülü Seçin:",
      [
          "CRM Analytics (Excel)",
          "SQL",
          "Power BI",
          "Machine Learning (Python)",
      ],
      index=1,
  )

  # ----------------------------------------------------
  # MODÜL 1: CRM ANALYTICS (EXCEL)
  # ----------------------------------------------------
  if secilen_modul == "CRM Analytics (Excel)":
    st.title("📑 CRM Analytics & Müşteri Segmentasyonu")
    st.caption(
        "Excel (.xlsx) üzerinden RFM skorları, segment eşleştirmeleri ve"
        " aksiyon kararlarının analizi."
    )

    CRM_ROOT_ID = st.secrets.get(
        "crm_folder_id", "12pr9WZ8jgtTNGBToh0LFbmwVL61XK_XM"
    )
    CACHE_CRM = "rapor_cache_crm.json"
    OUT_CSV_CRM = "tum_ogrenci_crm_puanlari.csv"
    OUT_XLSX_CRM = "tum_ogrenci_crm_puanlari.xlsx"

    if is_admin and service:
      if st.sidebar.button(
          "🚀 CRM Ödevlerini Tara ve Puanla", key="btn_scan_crm"
      ):
        folders = list_crm_student_folders(service, CRM_ROOT_ID)
        cache_data = {}
        if os.path.exists(CACHE_CRM):
          try:
            with open(CACHE_CRM, "r", encoding="utf-8") as f:
              cache_data = json.load(f)
          except Exception:
            pass

        results = []
        pbar = st.sidebar.progress(0)
        st_text = st.sidebar.empty()
        total = len(folders)
        atlanansayisi, taranansayisi = 0, 0

        for idx, (s_name, f_id) in enumerate(folders.items(), start=1):
          mevcut_puan = cache_data.get(s_name, {}).get("puan", "")
          if (
              re.match(r"^\d+/100$", str(mevcut_puan))
              and mevcut_puan != "0/100"
          ):
            atlanansayisi += 1
            results.append({"Öğrenci Adı": s_name, "Puan": mevcut_puan})
            pbar.progress(idx / total)
            continue

          taranansayisi += 1
          st_text.text(f"[{idx}/{total}] {s_name} inceleniyor...")
          ozet, msg, drive_link = get_crm_excel_from_student_folder(
              service, f_id
          )

          if ozet:
            try:
              report = evaluate_student_crm(ozet)
              puan = temiz_puan_ayikla_100(report)
            except Exception as e:
              report, puan = f"Hata: {str(e)}", "0/100"
          else:
            report, puan = f"Dosya durumu: {msg}", "Ödev Yok"

          cache_data[s_name] = {
              "puan": puan,
              "dosya_adi": msg,
              "detayli_rapor": report,
              "excel_ozet": ozet if ozet else "",
              "drive_link": drive_link,
          }
          results.append({"Öğrenci Adı": s_name, "Puan": puan})
          pbar.progress(idx / total)

        with open(CACHE_CRM, "w", encoding="utf-8") as f:
          json.dump(cache_data, f, ensure_ascii=False, indent=4)
        df_res = pd.DataFrame(results)
        df_res.to_csv(OUT_CSV_CRM, index=False, encoding="utf-8-sig")
        df_res.to_excel(OUT_XLSX_CRM, index=False)
        st_text.empty()
        pbar.empty()
        st.sidebar.success(
            f"🎉 Tamamlandı ({atlanansayisi} korundu, {taranansayisi} tarandı)!"
        )
        st.rerun()

    st.sidebar.subheader("📥 CRM Çıktıları")
    if os.path.exists(OUT_XLSX_CRM):
      with open(OUT_XLSX_CRM, "rb") as f:
        st.sidebar.download_button(
            "📊 CRM Notları (.xlsx)",
            f.read(),
            OUT_XLSX_CRM,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_crm_xl",
        )
    if os.path.exists(OUT_CSV_CRM):
      with open(OUT_CSV_CRM, "rb") as f:
        st.sidebar.download_button(
            "📄 CRM Notları (.csv)",
            f.read(),
            OUT_CSV_CRM,
            "text/csv",
            key="dl_crm_csv",
        )

    # CRM Sorgulama
    st.subheader("🔍 Öğrenci Detaylı CRM Raporu Sorgula")
    cache_crm_data = {}
    if os.path.exists(CACHE_CRM):
      try:
        with open(CACHE_CRM, "r", encoding="utf-8") as f:
          cache_crm_data = json.load(f)
      except Exception:
        pass

    q_crm = st.text_input(
        "Öğrencinin Adını Yazın:", "", key="search_crm_student"
    )
    matched_crm = [s for s in cache_crm_data.keys() if q_crm.lower() in s.lower()]

    if q_crm and matched_crm:
      sel_crm = st.selectbox(
          "Eşleşen Öğrenciler:", matched_crm, key="select_crm_student"
      )
      s_info = cache_crm_data.get(sel_crm, {})
      puan = s_info.get("puan", "-")

      st.success(f"✅ Rapor Hazır (Dosya: {s_info.get('dosya_adi', '-')})")
      col_a, col_b = st.columns(2)
      col_a.info(f"**Öğrenci:** {sel_crm}")
      col_b.info(f"**Puan:** {puan}")

      st.markdown("### 📝 Detaylı Değerlendirme Raporu")
      st.markdown(s_info.get("detayli_rapor", "Rapor bulunamadı."))

      st.markdown("---")
      col_btn, _ = st.columns([2, 3])
      if s_info.get("drive_link"):
        with col_btn:
          st.link_button(
              "📂 Orijinal Excel Dosyasını Drive'da Aç",
              s_info.get("drive_link"),
          )

      if s_info.get("excel_ozet"):
        with st.expander(
            "📑 Öğrencinin Teslim Ettiği Excel Tablolarını ve Metriklerini Gör",
            expanded=True,
        ):
          st.text(s_info.get("excel_ozet"))
    elif q_crm:
      st.info("Eşleşen öğrenci bulunamadı.")

  # ----------------------------------------------------
  # MODÜL 2: SQL (Tek Öğrenciyi Yeniden Puanlama Butonlu)
  # ----------------------------------------------------
  elif secilen_modul == "SQL":
    st.title("⚡ SQL Ödev Değerlendirme (33 Soru)")
    st.caption(
        "Northwind & CRM veri tabanı üzerinden hazırlanan 33 soruluk SQL"
        " projelerinin analizi."
    )

    CACHE_SQL = "rapor_cache.json"
    OUT_CSV_SQL = "tum_ogrenci_sql_puanlari.csv"
    OUT_XLSX_SQL = "tum_ogrenci_sql_puanlari.xlsx"

    if is_admin and service:
      if st.sidebar.button(
          "🚀 SQL Eksikleri Tara ve Puanla", key="btn_scan_sql"
      ):
        folders = list_sql_student_folders()
        cache_data = {}
        if os.path.exists(CACHE_SQL):
          try:
            with open(CACHE_SQL, "r", encoding="utf-8") as f:
              cache_data = json.load(f)
          except Exception:
            pass

        results = []
        pbar = st.sidebar.progress(0)
        st_text = st.sidebar.empty()
        total = len(folders)
        atlanansayisi, taranansayisi = 0, 0

        for idx, (s_name, f_id) in enumerate(folders.items(), start=1):
          mevcut_puan = cache_data.get(s_name, {}).get("puan", "")
          if (
              re.match(r"^\d+/33$", str(mevcut_puan))
              and mevcut_puan != "0/33"
          ):
            atlanansayisi += 1
            results.append({"Öğrenci Adı": s_name, "Puan": mevcut_puan})
            pbar.progress(idx / total)
            continue

          taranansayisi += 1
          st_text.text(f"[{idx}/{total}] {s_name} taranıyor...")
          sql_kodu, msg = get_sql_file_from_student_folder(service, f_id)

          if sql_kodu:
            try:
              report = evaluate_student_sql(sql_kodu)
              puan = temiz_puan_ayikla_sql(report)
            except Exception as e:
              report, puan = f"Hata: {str(e)}", "0/33"
          else:
            report, puan = f"Dosya durumu: {msg}", "Ödev Yok"

          cache_data[s_name] = {
              "puan": puan,
              "dosya_adi": msg,
              "detayli_rapor": report,
              "sql_kodu": sql_kodu if sql_kodu else "",
          }
          results.append({"Öğrenci Adı": s_name, "Puan": puan})
          pbar.progress(idx / total)

        with open(CACHE_SQL, "w", encoding="utf-8") as f:
          json.dump(cache_data, f, ensure_ascii=False, indent=4)
        df_res = pd.DataFrame(results)
        df_res.to_csv(OUT_CSV_SQL, index=False, encoding="utf-8-sig")
        df_res.to_excel(OUT_XLSX_SQL, index=False)
        st_text.empty()
        pbar.empty()
        st.sidebar.success(
            f"🎉 Tamamlandı ({atlanansayisi} korundu, {taranansayisi} tarandı)!"
        )
        st.rerun()

      if st.sidebar.button(
          "📥 Eksik SQL Kodlarını Çek (0 Token)", key="btn_fetch_sql_code"
      ):
        folders = list_sql_student_folders()
        cache_data = {}
        if os.path.exists(CACHE_SQL):
          try:
            with open(CACHE_SQL, "r", encoding="utf-8") as f:
              cache_data = json.load(f)
          except Exception:
            pass

        pbar = st.sidebar.progress(0)
        st_text = st.sidebar.empty()
        total = len(folders)
        guncellenen = 0

        for idx, (s_name, f_id) in enumerate(folders.items(), start=1):
          if s_name in cache_data and not cache_data[s_name].get("sql_kodu"):
            st_text.text(f"[{idx}/{total}] {s_name} SQL kodu alınıyor...")
            sql_kodu, _ = get_sql_file_from_student_folder(service, f_id)
            if sql_kodu:
              cache_data[s_name]["sql_kodu"] = sql_kodu
              guncellenen += 1
          pbar.progress(idx / total)

        with open(CACHE_SQL, "w", encoding="utf-8") as f:
          json.dump(cache_data, f, ensure_ascii=False, indent=4)
        st_text.empty()
        pbar.empty()
        st.sidebar.success(f"✅ {guncellenen} öğrencinin SQL kodu kaydedildi!")
        st.rerun()

    st.sidebar.subheader("📥 SQL Çıktıları")
    if os.path.exists(OUT_XLSX_SQL):
      with open(OUT_XLSX_SQL, "rb") as f:
        st.sidebar.download_button(
            "📊 SQL Notları (.xlsx)",
            f.read(),
            OUT_XLSX_SQL,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_sql_xl",
        )
    if os.path.exists(OUT_CSV_SQL):
      with open(OUT_CSV_SQL, "rb") as f:
        st.sidebar.download_button(
            "📄 SQL Notları (.csv)",
            f.read(),
            OUT_CSV_SQL,
            "text/csv",
            key="dl_sql_csv",
        )

    # SQL Arama ve İnceleme Ekranı
    st.subheader("🔍 Öğrenci Detaylı SQL Raporu Sorgula")
    student_folders = list_sql_student_folders()
    q_sql = st.text_input(
        "Öğrencinin Adını Yazın:", "", key="search_sql_student"
    )
    matched_sql = {
        n: fid for n, fid in student_folders.items() if q_sql.lower() in n.lower()
    }

    if q_sql and matched_sql:
      sel_sql = st.selectbox(
          "Eşleşen Öğrenciler:",
          list(matched_sql.keys()),
          key="select_sql_student",
      )
      cache_sql_data = {}
      if os.path.exists(CACHE_SQL):
        try:
          with open(CACHE_SQL, "r", encoding="utf-8") as f:
            cache_sql_data = json.load(f)
        except Exception:
          pass

      s_info = cache_sql_data.get(sel_sql)
      if s_info:
        puan = s_info.get("puan", "-")
        st.success(f"✅ Rapor Yüklendi (Dosya: {s_info.get('dosya_adi', '-')})")
        col_a, col_b = st.columns(2)
        col_a.info(f"**Öğrenci:** {sel_sql}")
        col_b.info(f"**Puan:** {puan}")

        # --- YENİ EKLENEN BUTON: TEK ÖĞRENCİYİ SIFIRDAN PUANLA ---
        if is_admin and service:
          if st.button(
              f"🔄 {sel_sql} İçin SQL'i Yeniden Değerlendir (Hafızayı Ez)",
              key="btn_recalc_single",
          ):
            with st.spinner(
                f"{sel_sql} için dosya Drive'dan indiriliyor ve yapay zeka 33"
                " soruyu baştan inceliyor..."
            ):
              fid = matched_sql.get(sel_sql)
              sql_kodu, msg = get_sql_file_from_student_folder(service, fid)

              if sql_kodu:
                yeni_rapor = evaluate_student_sql(sql_kodu)
                yeni_puan = temiz_puan_ayikla_sql(yeni_rapor)

                cache_sql_data[sel_sql] = {
                    "puan": yeni_puan,
                    "dosya_adi": msg,
                    "detayli_rapor": yeni_rapor,
                    "sql_kodu": sql_kodu,
                }
                with open(CACHE_SQL, "w", encoding="utf-8") as f:
                  json.dump(cache_sql_data, f, ensure_ascii=False, indent=4)

                st.success(f"🎉 Rapor Güncellendi! Yeni Puan: {yeni_puan}")
                st.rerun()
              else:
                st.error(f"Dosya okunamadı: {msg}")

        st.markdown("### 📝 Detaylı Değerlendirme Raporu")
        st.markdown(s_info.get("detayli_rapor", "Rapor metni bulunamadı."))

        st.markdown("---")
        sql_kodu = s_info.get("sql_kodu")
        if sql_kodu:
          with st.expander(
              "📄 Öğrencinin Yüklediği Orijinal SQL Kodunu Gör", expanded=True
          ):
            st.code(sql_kodu, language="sql")
        else:
          st.warning(
              "ℹ️ SQL kodu henüz hafızaya alınmamış. Sol menüden 'Eksik SQL"
              " Kodlarını Çek' butonuna basabilirsiniz."
          )
      else:
        st.warning("⚠️ Bu öğrenci henüz taranmamış.")
    elif q_sql:
      st.info("Eşleşen öğrenci bulunamadı.")

  # ----------------------------------------------------
  # MODÜL 3: POWER BI
  # ----------------------------------------------------
  elif secilen_modul == "Power BI":
    st.title("📊 Power BI Proje Değerlendirme")
    st.caption(
        "Power BI veri modeli (Star Schema), DAX ölçüleri ve görsel tasarım"
        " analizi."
    )

    PBI_ROOT_ID = st.secrets.get(
        "pbi_folder_id", "1OHCPzOaxie7w-vb3cgredLq_mH5Cxfiw"
    )
    CACHE_PBI = "rapor_cache_pbi.json"
    OUT_CSV_PBI = "tum_ogrenci_pbi_puanlari.csv"
    OUT_XLSX_PBI = "tum_ogrenci_pbi_puanlari.xlsx"

    if is_admin and service:
      if st.sidebar.button(
          "🚀 Power BI Projelerini Tara ve Puanla", key="btn_scan_pbi"
      ):
        folders = list_pbi_student_folders(service, PBI_ROOT_ID)
        cache_data = {}
        if os.path.exists(CACHE_PBI):
          try:
            with open(CACHE_PBI, "r", encoding="utf-8") as f:
              cache_data = json.load(f)
          except Exception:
            pass

        results = []
        pbar = st.sidebar.progress(0)
        st_text = st.sidebar.empty()
        total = len(folders)
        atlanansayisi, taranansayisi = 0, 0

        for idx, (s_name, f_id) in enumerate(folders.items(), start=1):
          mevcut_puan = cache_data.get(s_name, {}).get("puan", "")
          if (
              re.match(r"^\d+/100$", str(mevcut_puan))
              and mevcut_puan != "0/100"
          ):
            atlanansayisi += 1
            results.append({"Öğrenci Adı": s_name, "Puan": mevcut_puan})
            pbar.progress(idx / total)
            continue

          taranansayisi += 1
          st_text.text(f"[{idx}/{total}] {s_name} inceleniyor...")
          ozet, msg, drive_link = get_pbi_file_from_student_folder(
              service, f_id
          )

          if ozet:
            try:
              report = evaluate_student_pbi(ozet)
              puan = temiz_puan_ayikla_100(report)
            except Exception as e:
              report, puan = f"Hata: {str(e)}", "0/100"
          else:
            report, puan = f"Dosya durumu: {msg}", "Ödev Yok"

          cache_data[s_name] = {
              "puan": puan,
              "dosya_adi": msg,
              "detayli_rapor": report,
              "pbi_summary": ozet if ozet else "",
              "drive_link": drive_link,
          }
          results.append({"Öğrenci Adı": s_name, "Puan": puan})
          pbar.progress(idx / total)

        with open(CACHE_PBI, "w", encoding="utf-8") as f:
          json.dump(cache_data, f, ensure_ascii=False, indent=4)
        df_res = pd.DataFrame(results)
        df_res.to_csv(OUT_CSV_PBI, index=False, encoding="utf-8-sig")
        df_res.to_excel(OUT_XLSX_PBI, index=False)
        st_text.empty()
        pbar.empty()
        st.sidebar.success(
            f"🎉 Tamamlandı ({atlanansayisi} korundu, {taranansayisi} tarandı)!"
        )
        st.rerun()

    st.sidebar.subheader("📥 Power BI Çıktıları")
    if os.path.exists(OUT_XLSX_PBI):
      with open(OUT_XLSX_PBI, "rb") as f:
        st.sidebar.download_button(
            "📊 Power BI Notları (.xlsx)",
            f.read(),
            OUT_XLSX_PBI,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_pbi_xl",
        )
    if os.path.exists(OUT_CSV_PBI):
      with open(OUT_CSV_PBI, "rb") as f:
        st.sidebar.download_button(
            "📄 Power BI Notları (.csv)",
            f.read(),
            OUT_CSV_PBI,
            "text/csv",
            key="dl_pbi_csv",
        )

    # Power BI Sorgulama
    st.subheader("🔍 Öğrenci Detaylı Power BI Raporu Sorgula")
    cache_pbi_data = {}
    if os.path.exists(CACHE_PBI):
      try:
        with open(CACHE_PBI, "r", encoding="utf-8") as f:
          cache_pbi_data = json.load(f)
      except Exception:
        pass

    q_pbi = st.text_input(
        "Öğrencinin Adını Yazın:", "", key="search_pbi_student"
    )
    matched_pbi = [s for s in cache_pbi_data.keys() if q_pbi.lower() in s.lower()]

    if q_pbi and matched_pbi:
      sel_pbi = st.selectbox(
          "Eşleşen Öğrenciler:", matched_pbi, key="select_pbi_student"
      )
      s_info = cache_pbi_data.get(sel_pbi, {})
      puan = s_info.get("puan", "-")

      st.success(f"✅ Rapor Hazır (Dosya: {s_info.get('dosya_adi', '-')})")
      col_a, col_b = st.columns(2)
      col_a.info(f"**Öğrenci:** {sel_pbi}")
      col_b.info(f"**Puan:** {puan}")

      st.markdown("### 📝 Detaylı Değerlendirme Raporu")
      st.markdown(s_info.get("detayli_rapor", "Rapor metni bulunamadı."))

      st.markdown("---")
      col_btn, _ = st.columns([2, 3])
      if s_info.get("drive_link"):
        with col_btn:
          st.link_button(
              "📂 Orijinal Power BI Dosyasını Drive'da Aç",
              s_info.get("drive_link"),
          )

      if s_info.get("pbi_summary"):
        with st.expander(
            "📊 Öğrencinin Veri Modeli ve Dashboard Yapısını Gör", expanded=True
        ):
          st.code(s_info.get("pbi_summary"), language="yaml")
    elif q_pbi:
      st.info("Eşleşen öğrenci bulunamadı.")

  # ----------------------------------------------------
  # MODÜL 4: MACHINE LEARNING (PYTHON)
  # ----------------------------------------------------
  elif secilen_modul == "Machine Learning (Python)":
    st.title("🧠 Machine Learning Pipeline Değerlendirme")
    st.caption(
        "Python (.py) ve Jupyter Notebook (.ipynb) üzerinden EDA, Feature"
        " Engineering ve model pipeline analizi."
    )

    ML_ROOT_ID = st.secrets.get("ml_folder_id", "")
    CACHE_ML = "rapor_cache_ml.json"
    OUT_CSV_ML = "tum_ogrenci_ml_puanlari.csv"
    OUT_XLSX_ML = "tum_ogrenci_ml_puanlari.xlsx"

    if is_admin and service:
      if st.sidebar.button(
          "🚀 ML Projelerini Tara ve Puanla", key="btn_scan_ml"
      ):
        if not ML_ROOT_ID:
          st.sidebar.error(
              "❌ secrets.toml dosyasında 'ml_folder_id' tanımlanmamış!"
          )
        else:
          folders = list_ml_student_folders(service, ML_ROOT_ID)
          cache_data = {}
          if os.path.exists(CACHE_ML):
            try:
              with open(CACHE_ML, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            except Exception:
              pass

          results = []
          pbar = st.sidebar.progress(0)
          st_text = st.sidebar.empty()
          total = len(folders)
          atlanansayisi, taranansayisi = 0, 0

          for idx, (s_name, f_id) in enumerate(folders.items(), start=1):
            mevcut_puan = cache_data.get(s_name, {}).get("puan", "")
            if (
                re.match(r"^\d+/100$", str(mevcut_puan))
                and mevcut_puan != "0/100"
            ):
              atlanansayisi += 1
              results.append({"Öğrenci Adı": s_name, "Puan": mevcut_puan})
              pbar.progress(idx / total)
              continue

            taranansayisi += 1
            st_text.text(f"[{idx}/{total}] {s_name} inceleniyor...")
            kod, msg, drive_link = get_ml_file_from_student_folder(
                service, f_id
            )

            if kod:
              try:
                report = evaluate_student_ml(kod)
                puan = temiz_puan_ayikla_100(report)
              except Exception as e:
                report, puan = f"Hata: {str(e)}", "0/100"
            else:
              report, puan = f"Dosya durumu: {msg}", "Ödev Yok"

            cache_data[s_name] = {
                "puan": puan,
                "dosya_adi": msg,
                "detayli_rapor": report,
                "code_content": kod if kod else "",
                "drive_link": drive_link,
            }
            results.append({"Öğrenci Adı": s_name, "Puan": puan})
            pbar.progress(idx / total)

          with open(CACHE_ML, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
          df_res = pd.DataFrame(results)
          df_res.to_csv(OUT_CSV_ML, index=False, encoding="utf-8-sig")
          df_res.to_excel(OUT_XLSX_ML, index=False)
          st_text.empty()
          pbar.empty()
          st.sidebar.success(
              f"🎉 Tamamlandı ({atlanansayisi} korundu, {taranansayisi}"
              " tarandı)!"
          )
          st.rerun()

    st.sidebar.subheader("📥 ML Çıktıları")
    if os.path.exists(OUT_XLSX_ML):
      with open(OUT_XLSX_ML, "rb") as f:
        st.sidebar.download_button(
            "📊 ML Notları (.xlsx)",
            f.read(),
            OUT_XLSX_ML,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_ml_xl",
        )
    if os.path.exists(OUT_CSV_ML):
      with open(OUT_CSV_ML, "rb") as f:
        st.sidebar.download_button(
            "📄 ML Notları (.csv)",
            f.read(),
            OUT_CSV_ML,
            "text/csv",
            key="dl_ml_csv",
        )

    # ML Sorgulama
    st.subheader("🔍 Öğrenci Detaylı ML Raporu Sorgula")
    cache_ml_data = {}
    if os.path.exists(CACHE_ML):
      try:
        with open(CACHE_ML, "r", encoding="utf-8") as f:
          cache_ml_data = json.load(f)
      except Exception:
        pass

    q_ml = st.text_input("Öğrencinin Adını Yazın:", "", key="search_ml_student")
    matched_ml = [s for s in cache_ml_data.keys() if q_ml.lower() in s.lower()]

    if q_ml and matched_ml:
      sel_ml = st.selectbox(
          "Eşleşen Öğrenciler:", matched_ml, key="select_ml_student"
      )
      s_info = cache_ml_data.get(sel_ml, {})
      puan = s_info.get("puan", "-")

      st.success(f"✅ Rapor Hazır (Dosya: {s_info.get('dosya_adi', '-')})")
      col_a, col_b = st.columns(2)
      col_a.info(f"**Öğrenci:** {sel_ml}")
      col_b.info(f"**Puan:** {puan}")

      st.markdown("### 📝 Detaylı Değerlendirme Raporu")
      st.markdown(s_info.get("detayli_rapor", "Rapor metni bulunamadı."))

      st.markdown("---")
      col_btn, _ = st.columns([2, 3])
      if s_info.get("drive_link"):
        with col_btn:
          st.link_button(
              "📂 Orijinal Notebook / Python Dosyasını Drive'da Aç",
              s_info.get("drive_link"),
          )

      if s_info.get("code_content"):
        with st.expander(
            "🐍 Öğrencinin Python Pipeline / Notebook Kodunu Gör", expanded=True
        ):
          st.code(s_info.get("code_content"), language="python")
    elif q_ml:
      st.info("Eşleşen öğrenci bulunamadı.")