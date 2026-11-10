import io
import json
import re
import zipfile
from googleapiclient.http import MediaIoBaseDownload


def list_pbi_student_folders(service, pbi_root_id):
  """Google Drive'daki Power BI ana klasörünün altındaki tüm öğrenci klasörlerini listeler."""
  try:
    query = f"'{pbi_root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    folders = {}
    page_token = None

    while True:
      response = (
          service.files()
          .list(
              q=query,
              spaces="drive",
              fields="nextPageToken, files(id, name)",
              pageSize=100,
              supportsAllDrives=True,
              includeItemsFromAllDrives=True,
              pageToken=page_token,
          )
          .execute()
      )

      for folder in response.get("files", []):
        folders[folder["name"]] = folder["id"]

      page_token = response.get("nextPageToken")
      if not page_token:
        break

    return dict(sorted(folders.items()))
  except Exception:
    return {}


def parse_pbix_content(file_bytes):
  """.pbix (ZIP) dosyasını açarak sayfa yapılarını, kullanılan görselleri ve veri modeli/DAX bilgilerini ayıklar."""
  summary_lines = []
  try:
    with zipfile.ZipFile(file_bytes, "r") as z:
      file_list = z.namelist()

      # 1. Rapor Görsel ve Sayfa Yapısı (Report/Layout)
      layout_files = [f for f in file_list if "layout" in f.lower()]
      if layout_files:
        raw_layout = z.read(layout_files[0])
        try:
          # Power BI Layout dosyaları çoğunlukla utf-16-le ile kodlanır
          layout_str = raw_layout.decode("utf-16-le", errors="ignore")
          layout_data = json.loads(layout_str)

          pages = layout_data.get("sections", [])
          summary_lines.append(f"📌 Rapordaki Sayfa Sayısı: {len(pages)}")

          for idx, page in enumerate(pages, 1):
            page_name = page.get("displayName", f"Sayfa {idx}")
            visuals = page.get("visualContainers", [])
            visual_types = []

            for v in visuals:
              config_str = v.get("config", "{}")
              try:
                cfg = json.loads(config_str)
                v_type = (
                    cfg.get("singleVisual", {}).get("visualType")
                    or cfg.get("visualType")
                    or "Bilinmeyen Görsel"
                )
                visual_types.append(v_type)
              except Exception:
                pass

            summary_lines.append(f"\n--- SAYFA {idx}: [{page_name}] ---")
            summary_lines.append(f"Toplam Görsel Sayısı: {len(visuals)}")
            if visual_types:
              # Görsel tiplerinin dağılımı
              from collections import Counter

              counts = Counter(visual_types)
              summary_lines.append(
                  f"Kullanılan Görseller: {dict(counts.most_common(8))}"
              )
        except Exception:
          summary_lines.append(
              "Report/Layout okundu fakat JSON formatı parse edilemedi."
          )

      # 2. Veri Modeli ve Şema Analizi (DataModelSchema)
      schema_files = [f for f in file_list if "datamodelschema" in f.lower()]
      if schema_files:
        raw_schema = z.read(schema_files[0])
        try:
          schema_str = raw_schema.decode("utf-16-le", errors="ignore")
          schema_data = json.loads(schema_str)
          model = schema_data.get("model", {})
          tables = model.get("tables", [])

          summary_lines.append("\n" + "=" * 45)
          summary_lines.append(
              f"📌 Veri Modeli Tablo Sayısı: {len(tables)} tablo"
          )
          table_names = [t.get("name", "İsimsiz") for t in tables]
          summary_lines.append(f"Tablolar: {', '.join(table_names[:15])}")

          # DAX Ölçüleri (Measures)
          all_measures = []
          for t in tables:
            for m in t.get("measures", []):
              m_name = m.get("name")
              m_expr = m.get("expression")
              if m_name:
                all_measures.append(f"{m_name} = {str(m_expr)[:80]}")

          if all_measures:
            summary_lines.append(
                f"\n📌 Tespit Edilen DAX Ölçüleri ({len(all_measures)} Adet):"
            )
            for m in all_measures[:8]:  # İlk 8 ölçüyü prompta ekle
              summary_lines.append(f"  • {m}")
        except Exception:
          summary_lines.append("DataModelSchema okundu ancak detay alınamadı.")

      if not summary_lines:
        summary_lines.append(
            ".pbix arşivi açıldı. İçerik dosyaları: "
            f"{', '.join(file_list[:10])}"
        )

    return "\n".join(summary_lines)

  except Exception as e:
    return f"Power BI dosyası açılırken hata: {str(e)}"


def get_pbi_file_from_student_folder(service, student_folder_id):
  """Öğrenci klasöründen .pbix veya .pdf dosyasını yakalar, içeriği ve Drive bağlantısını döndürür."""
  try:
    query = f"'{student_folder_id}' in parents and trashed = false"
    response = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id, name, mimeType, webViewLink)",
            pageSize=20,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )

    files = response.get("files", [])
    if not files:
      return None, "Klasör boş.", None

    target_file = None
    for f in files:
      name_lower = f["name"].lower()
      mime = f.get("mimeType", "")

      # Google Docs dosyalarını atla
      if mime.startswith("application/vnd.google-apps"):
        continue

      if name_lower.endswith(".pbix") or name_lower.endswith(".pdf"):
        target_file = f
        break

    if not target_file:
      return (
          None,
          "Klasörde .pbix veya .pdf uzantılı proje dosyası bulunamadı.",
          None,
      )

    file_id = target_file["id"]
    file_name = target_file["name"]
    drive_link = target_file.get(
        "webViewLink", f"https://drive.google.com/file/d/{file_id}/view"
    )

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
      status, done = downloader.next_chunk()

    if file_name.lower().endswith(".pbix"):
      pbi_summary = parse_pbix_content(fh)
    else:
      pbi_summary = (
          f"Teslim Edilen Dosya: {file_name} (PDF Rapor). Görsel panolar"
          " Drive bağlantısı üzerinden incelenebilir."
      )

    return pbi_summary, file_name, drive_link

  except Exception as e:
    return None, f"Power BI dosyası indirme hatası: {str(e)}", None