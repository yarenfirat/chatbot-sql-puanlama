import io
import pandas as pd
from googleapiclient.http import MediaIoBaseDownload


def list_crm_student_folders(service, crm_root_id):
  """Google Drive'daki CRM ana klasörünün (1_CRM_Analytics) altındaki tüm öğrenci klasörlerini otomatik listeler.

  Dönüş: {"Öğrenci Adı Soyadı": "Klasör ID"}
  """
  try:
    query = f"'{crm_root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
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


def parse_crm_excel_content(excel_bytes):
  """Öğrencinin Excel dosyasını açar:

  - Sayfa isimlerini alır
  - Sütunları inceler
  - En alttaki kutuda ödevi görebilmen için ilk 5 örnek satırı çıkarır
  - Varsa RFM segment dağılımını hesaplar
  Tüm bunları token israfı yapmadan metne döker.
  """
  summary_lines = []
  try:
    xl = pd.ExcelFile(excel_bytes)
    sheet_names = xl.sheet_names
    summary_lines.append(
        f"Çalışma Kitabı Sayfaları: {', '.join(sheet_names)}\n"
    )

    for sheet in sheet_names:
      # Sadece ilk 50 satırı yükleyerek RAM ve token tasarrufu yapar
      df = xl.parse(sheet, nrows=50)

      summary_lines.append(f"📌 SAYFA: [{sheet}]")
      summary_lines.append(f"Sütunlar: {list(df.columns)}")

      # Arayüzde öğrencinin teslim ettiği veriyi göstermek için ilk 5 satır
      summary_lines.append("\nÖrnek Veri Satırları (İlk 5 Satır):")
      summary_lines.append(df.head(5).to_string(index=False))

      # Segment kolonu var mı kontrol et
      segment_col = None
      for col in df.columns:
        if any(
            k in str(col).lower()
            for k in ["segment", "rfm_segment", "kategori"]
        ):
          segment_col = col
          break

      if segment_col:
        dist = df[segment_col].value_counts().head(10).to_dict()
        summary_lines.append(
            f"\nHesaplanan Segment Dağılımı ({segment_col}): {dist}"
        )

      summary_lines.append("\n" + "=" * 45 + "\n")

    return "\n".join(summary_lines)

  except Exception as e:
    return f"Excel içerik analizi sırasında hata: {str(e)}"


def get_crm_excel_from_student_folder(service, student_folder_id):
  """Öğrencinin klasörüne girer:

  1. Google Dokümanlarını atlar, doğrudan .xlsx veya .xls dosyasını bulur.
  2. Dosyayı indirip özetini çıkartır.
  3. Doğrudan tıklandığında açılacak Google Drive bağlantısını (webViewLink) alır.
  Dönüş: (excel_ozeti, dosya_adi, drive_linki)
  """
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

      # 403 hatası verdiren Google Docs dokümanlarını atla
      if (
          mime.startswith("application/vnd.google-apps")
          and "spreadsheet" not in mime
      ):
        continue

      # Gerçek Excel dosyasını seç
      if name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
        target_file = f
        break

    if not target_file:
      return (
          None,
          "Klasörde .xlsx veya .xls uzantılı ödev dosyası bulunamadı.",
          None,
      )

    file_id = target_file["id"]
    file_name = target_file["name"]
    drive_link = target_file.get(
        "webViewLink", f"https://drive.google.com/file/d/{file_id}/view"
    )

    # Excel dosyasını akış olarak belleğe indir
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
      status, done = downloader.next_chunk()

    # Dosya içeriğini parse et
    excel_summary = parse_crm_excel_content(fh)
    return excel_summary, file_name, drive_link

  except Exception as e:
    return None, f"Excel okuma hatası: {str(e)}", None