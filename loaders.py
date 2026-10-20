import io
import json
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_oauth_drive_service():
    """OAuth ile Google Drive servisini otomatik başlatır (Streamlit URL redirect uyumlu)."""
    creds = None
    
    # 1. Oturumda kayıtlı token var mı?
    if "oauth_creds" in st.session_state:
        creds_data = st.session_state["oauth_creds"]
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
                
        if not creds:
            if "gcp_oauth_client" in st.secrets:
                client_config = {"installed": dict(st.secrets["gcp_oauth_client"])}
            else:
                st.error("Google OAuth client bilgileri secrets içinde bulunamadı!")
                return None
            
            redirect_uri = "https://chatbot-sql-puanlama-nscvmjabumqjqyt4bvbybb.streamlit.app"
            
            # Flow nesnesini session_state'de tutuyoruz ki redirect sonrasında kaybolmasın
            if "oauth_flow" not in st.session_state:
                st.session_state["oauth_flow"] = Flow.from_client_config(
                    client_config,
                    scopes=SCOPES,
                    redirect_uri=redirect_uri
                )
            
            flow = st.session_state["oauth_flow"]
            
            # URL'de Google'dan gelen bir 'code' var mı kontrol et
            query_params = st.query_params
            auth_code = query_params.get("code")
            
            if auth_code:
                try:
                    # Kodu URL'den otomatik yakaladık, token'ı alıyoruz
                    flow.fetch_token(code=auth_code)
                    creds = flow.credentials
                    st.session_state["oauth_creds"] = {
                        'token': creds.token,
                        'refresh_token': creds.refresh_token,
                        'token_uri': creds.token_uri,
                        'client_id': creds.client_id,
                        'client_secret': creds.client_secret,
                        'scopes': creds.scopes
                    }
                    if "oauth_flow" in st.session_state:
                        del st.session_state["oauth_flow"]
                    
                    # URL'deki code parametresini temizleyip sayfayı yenile
                    st.query_params.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Otomatik kod doğrulama hatası: {e}")
                    return None
            else:
                # URL'de kod yoksa kullanıcıyı giriş yapması için yönlendir
                try:
                    auth_url, _ = flow.authorization_url(prompt='consent', include_granted_scopes='true', access_type='offline')
                except Exception as e:
                    st.error(f"Auth URL oluşturulamadı: {e}")
                    return None
                
                st.warning("Google Drive erişimi için yetkilendirme gerekiyor.")
                st.markdown(f"Lütfen aşağıdaki butona tıklayarak Google hesabınızla giriş yapın:")
                st.markdown(f'<a href="{auth_url}" target="_self"><button style="background-color: #4CAF50; color: white; padding: 10px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;">Google ile Giriş Yap</button></a>', unsafe_allow_html=True)
                return None

    return build('drive', 'v3', credentials=creds)

def list_student_folders(service, parent_folder_id):
    """Drive'daki klasörleri listeler."""
    try:
        results = service.files().list(
            q="mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            pageSize=100,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        folders = results.get('files', [])
        student_folders = {f['name']: f['id'] for f in folders}
        return student_folders
    except Exception as e:
        print(f"DEBUG - Hata: {e}")
        return {}

def get_sql_file_from_student_folder(service, student_folder_id):
    """Seçilen öğrencinin klasöründeki SQL ödev dosyasını bulur ve içeriğini okur."""
    query = f"'{student_folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, pageSize=20, fields="files(id, name, mimeType)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = results.get('files', [])
    
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