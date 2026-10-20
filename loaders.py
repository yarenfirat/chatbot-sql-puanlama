import io
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
REDIRECT_URI = "https://chatbot-sql-puanlama-nscvmjabumqjqyt4bvbybb.streamlit.app"

def create_flow():
    """Her çağrıldığında PKCE (code_verifier) olmadan temiz bir Web Flow nesnesi üretir."""
    if "gcp_oauth_client" not in st.secrets:
        st.error("Google OAuth client bilgileri secrets içinde bulunamadı!")
        return None
    
    # Google Cloud'da Web application kullandığımız için "web" anahtarını kullanıyoruz
    client_config = {"web": dict(st.secrets["gcp_oauth_client"])}
    
    # autogenerate_code_verifier=False sayesinde sayfa yenilense bile "Invalid code verifier" hatası çıkmaz!
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=False
    )
    return flow

def get_oauth_drive_service():
    """OAuth ile Google Drive servisini başlatır."""
    creds = None
    
    # 1. Oturumda kayıtlı token var mı?
    if "oauth_creds" in st.session_state:
        creds_data = st.session_state["oauth_creds"]
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
    # 2. Token yoksa veya süresi geçmişse
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                st.session_state["oauth_creds"] = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes
                }
            except Exception:
                creds = None
                
        if not creds:
            # URL'de Google'dan dönen 'code' parametresi var mı kontrol et
            auth_code = st.query_params.get("code")
            
            if auth_code:
                try:
                    flow = create_flow()
                    if not flow:
                        return None
                    
                    # Kodu doğrula ve token'ı al (Verifier kapalı olduğu için hatasız geçer)
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
                    
                    # URL'deki ?code=... karmaşasını temizle ve sayfayı yenile
                    st.query_params.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Otomatik doğrulama hatası: {e}")
                    st.query_params.clear()
                    return None
            else:
                # Henüz giriş yapılmadıysa yetkilendirme linkini oluştur
                flow = create_flow()
                if not flow:
                    return None
                
                auth_url, _ = flow.authorization_url(
                    prompt='consent',
                    include_granted_scopes='true',
                    access_type='offline'
                )
                
                st.warning("Google Drive erişimi için yetkilendirme gerekiyor.")
                
                # HTML/iframe 403 hatasına takılmamak için Streamlit'in yerel link butonunu kullanıyoruz
                st.link_button("Google ile Giriş Yap", auth_url, type="primary")
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
        st.error(f"Klasör listeleme hatası: {e}")
        return {}

def get_sql_file_from_student_folder(service, student_folder_id):
    """Seçilen öğrencinin klasöründeki SQL ödev dosyasını bulur ve içeriğini okur."""
    query = f"'{student_folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        pageSize=20,
        fields="files(id, name, mimeType)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
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