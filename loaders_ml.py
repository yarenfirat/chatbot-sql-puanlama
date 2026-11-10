import io
import json
from googleapiclient.http import MediaIoBaseDownload


def list_ml_student_folders(service, ml_root_id):
  """Google Drive'daki Machine Learning ana klasörünün altındaki öğrenci klasörlerini listeler."""
  try:
    query = f"'{ml_root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
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


def parse_jupyter_notebook(raw_bytes):
  """Jupyter Notebook (.ipynb) JSON dosyasından kod ve markdown hücrelerini ayıklar.

  Gereksiz çıktı ve görsel verilerini temizler.
  """
  try:
    content_str = raw_bytes.decode("utf-8", errors="ignore")
    nb = json.loads(content_str)
    cells = nb.get("cells", [])

    parsed_lines = []
    parsed_lines.append(f"# Toplam Hücre Sayısı: {len(cells)}")

    for idx, cell in enumerate(cells, 1):
      cell_type = cell.get("cell_type", "")
      source = "".join(cell.get("source", []))

      if not source.strip():
        continue

      if cell_type == "markdown":
        parsed_lines.append(f"\n# --- [Hücre {idx} - Markdown / Açıklama] ---")
        parsed_lines.append(source)
      elif cell_type == "code":
        parsed_lines.append(f"\n# --- [Hücre {idx} - Python Kodu] ---")
        parsed_lines.append(source)

    return "\n".join(parsed_lines)
  except Exception as e:
    return f"Notebook parse edilirken hata: {str(e)}"


def get_ml_file_from_student_folder(service, student_folder_id):
  """Öğrenci klasöründen .ipynb veya .py dosyasını çeker, kodu ve Drive linkini döndürür."""
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

      # Google Docs / Sheets dokümanlarını atla
      if mime.startswith("application/vnd.google-apps"):
        continue

      # Öncelikle .ipynb dosyasını ara, yoksa .py dosyasına bak
      if name_lower.endswith(".ipynb") or name_lower.endswith(".py"):
        target_file = f
        break

    if not target_file:
      return (
          None,
          "Klasörde .ipynb veya .py uzantılı dosya bulunamadı.",
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

    raw_bytes = fh.getvalue()
    if file_name.lower().endswith(".ipynb"):
      code_content = parse_jupyter_notebook(raw_bytes)
    else:
      code_content = raw_bytes.decode("utf-8", errors="ignore")

    return code_content, file_name, drive_link

  except Exception as e:
    return None, f"ML dosyası okuma hatası: {str(e)}", None