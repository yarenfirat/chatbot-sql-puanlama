import io
import json
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_oauth_drive_service():
    """OAuth ile Google Drive servisini başlatır (lokal veya Streamlit uyumlu)."""
    creds = None
    
    # Eğer daha önce kaydedilmiş bir token varsa yükle
    if "oauth_creds" in st.session_state:
        creds_data = st.session_state["oauth_creds"]
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Streamlit secrets içindeki client yapılandırmasını alıyoruz
            if "gcp_oauth_client" in st.secrets:
                client_config = {"installed": dict(st.secrets["gcp_oauth_client"])}
            else:
                return None
            
            # Lokal test için InstalledAppFlow kullanıyoruz
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Yetkileri oturumda sakla
        st.session_state["oauth_creds"] = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }

    return build('drive', 'v3', credentials=creds)

        
def list_student_folders(service, parent_folder_id):
    """Drive'daki klasörleri listeler ve konsola yazdırır."""
    try:
        results = service.files().list(
            q="mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            pageSize=100,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        folders = results.get('files', [])
        print(f"DEBUG - Bulunan toplam klasör sayısı: {len(folders)}")
        
        student_folders = {f['name']: f['id'] for f in folders}
        return student_folders
        
    except Exception as e:
        print(f"DEBUG - Hata: {e}")
        return {}

def get_sql_file_from_student_folder(service, student_folder_id):
    """Seçilen öğrencinin klasöründeki SQL ödev dosyasını bulur ve içeriğini okur."""
    # Doğrudan o klasörün içindeki tüm dosyaları çekelim
    query = f"'{student_folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, pageSize=20, fields="files(id, name, mimeType)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = results.get('files', [])
    
    # .sql ile biten veya adında sql geçen dosyayı arayalım
    sql_file = next((f for f in files if f['name'].endswith('.sql') or 'sql' in f['name'].lower()), None)
    
    if not sql_file:
        return None, "Bu öğrencinin klasöründe .sql uzantılı ödev dosyası bulunamadı."
    
    file_id = sql_file['id']
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    
    return fh.read().decode('utf-8'), sql_file['name']
