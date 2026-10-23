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
    if "gcp_oauth_client" not in st.secrets:
        st.error("Google OAuth client bilgileri secrets içinde bulunamadı!")
        return None
    client_config = {"web": dict(st.secrets["gcp_oauth_client"])}
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=False
    )
    return flow

def get_oauth_drive_service():
    creds = None
    if "oauth_creds" in st.session_state:
        creds_data = st.session_state["oauth_creds"]
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                st.session_state["oauth_creds"] = {
                    'token': creds.token, 'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri, 'client_id': creds.client_id,
                    'client_secret': creds.client_secret, 'scopes': creds.scopes
                }
            except Exception:
                creds = None
                
        if not creds:
            auth_code = st.query_params.get("code")
            if auth_code:
                try:
                    flow = create_flow()
                    if not flow: return None
                    flow.fetch_token(code=auth_code)
                    creds = flow.credentials
                    st.session_state["oauth_creds"] = {
                        'token': creds.token, 'refresh_token': creds.refresh_token,
                        'token_uri': creds.token_uri, 'client_id': creds.client_id,
                        'client_secret': creds.client_secret, 'scopes': creds.scopes
                    }
                    st.query_params.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Otomatik doğrulama hatası: {e}")
                    st.query_params.clear()
                    return None
            else:
                flow = create_flow()
                if not flow: return None
                auth_url, _ = flow.authorization_url(prompt='consent', include_granted_scopes='true', access_type='offline')
                st.warning("Google Drive erişimi için yetkilendirme gerekiyor.")
                st.link_button("Google ile Giriş Yap", auth_url, type="primary")
                return None

    return build('drive', 'v3', credentials=creds)

# DRIVE API INDEKSLEME KISITLAMASINI ASAN SABIT OGRENCI HARITASI
STUDENT_FOLDERS = {'Esra Hilal Baltacıoğlu': '1WwYuTEMkclroIiNNdMKIMWS3qvbAAW_p', 'Atalay Alıçlar': '18-2Ammg1bgMouRhySkjFA7pt3AWbaDXA', 'Berat Dinç': '1rKllAApP3p3gdCajTnHOcBVWO120tGSL', 'Havva Karsu': '1qBC6PHo_KeUO8rps-ZOdptj5bPRunlBW', 'Melek Özcan': '1AV4oShTKYPjGyJx-w4REBz3KAq3GMIqO', 'Furkan Koç': '1aYCWs1Uss0FIqZSz3DOPhbDlBpo6HHsS', 'Simge Sınav': '1ffHaxtPObmeOapk9oxaBJcjTfE-VDE9c', 'Eda Nur Demirbaş': '1I51YZJZdPy4iZ02XF19jHMkz493dpXQl', 'Minel Ceylan': '16MZptP4MktVOQpXBdU3iQ3jhq2g5xivq', 'Ceren Köker': '1roZ4IojJ9zTWaTiLcNagdZNBPrA9b7PA', 'Suna Akdaş': '1b3LXxsiHpCigqtSZJe7U74B0ULmzYWfZ', 'Meyre Damar': '1grh3Qk6AqahhxABQxMB1p5UA693vlj04', 'Gulsah İpek Baldiz': '1tthg9iS-nebfa9_zCyJhVirKayJNDWTL', 'Meral Turan': '1bi_Rom484ulh3Gcuz1RIILFnFfXx7-No', 'Büşra Koçak Silahdaroğlu': '1Iy1P-S0ST5U_284pJDYsnw29Mges0vNx', 'Zehra Susam': '1vn7-D6w6O-s0glaOjEaQCnzfghXg2Bfm', 'Burak Canbolat': '19hEG5uj2--rdV0bRqKzm8e4M2HXltj9E', 'Burak Karaca': '1kCR34DKHHNBgn70ifREJmunrElhVZxme', 'Ahmet Emin Töremen': '119XP8fcWSP2XS2ByR9ZH8yNvM0u19877', 'Ezgi Gögebakan': '1ombq0RbWzgeB5aXuTZ-hYKSnE9wQ0074', 'İremnur İlhan': '1uIRDnf3KCauqd3nLOd4b2-f25doP8j-0', 'Omer Ozlu': '1-XvHJ-OIpP4Z7_ys1ks52Wct48kpFcUZ', 'Sultan Şentekin': '1E0HYG_zkYCSTviySxvDgRdvXm6iejdQb', 'Berra Sezgin': '1Y8phb_ZkhP7CdJIfOTqmPHfdLjb-zh50', 'Sadettin Yıldırım': '1k5zbod1Bu8N_Q3S0myM4Dzo5F4ff8OhY', 'Ece Nurten': '1TEgiAXICg1so-baVVnC9cLgzzCL6VHpy', 'Fatma Canan Kaya': '1i4ZkViKg59JCjvRvzK-EXEZWtdAaQDVI', 'Sema Bozdoğan': '1x9NXTgWKWm6sBVp4N9IeuKx5ik7MPTTn', 'Ali Aytuğ Hadımlı': '1hkFX6mW9afs52LYJGm899r5K_PiWsi-K', 'Tolga Toksoy': '1tEHdDwAONdZbXy9-9bOD1mkQleBKl_T_', 'İpek Ersoy': '1lwIlSoo_w2bq-HafW2ubF8zuabGcYHdp', 'Semihcan Çelik': '1ELkF2X9KHLWbKPhe9Pe0rvaeNfjbcKzo', 'Arda Ahmet Demirci': '1KIimrOjF73kQ8_Q9NZHT7J3lDtVL-yTy', 'Sanem Aktaş': '1E432g9aK-zFaiOk_9FwrBfJ4B51Lka_W', 'Bihter Kaplan': '1kHChxwZJ9UGLDraxyENxSXp_Cf_ZNU46', 'Gizem Başak': '195JC7_wSW0Kv8Yndp8-q2gTNbSFpKspM', 'Aysel Ahmadli': '1OmdLgGgW-PF2sFbENa0ikG5RviX2wV4X', 'Şervan Çetinkaya': '1D-0K7sSbCk-tSVqjcakLRSg15xE1x14E', 'Eda Güzel': '1YLcGkwckgYbx-th9wYk3jR01IrcJdYYn', 'Melike Yaşar': '1HXAT_txO15Iec8bZqL7v9S7wWkk1Pf_8', 'Jan Ridade Gergin': '1SwF9IBIIQsvUMGdHxfFNzucG_fzTlBWA', 'Emine Dereli Bayrak': '1XfcQm7FJQXm5RgfDa9Mf0L0J4IdDDwn4', 'Yaren Sultan Özkale': '1ECu9SQwFyNOOhZF6-DNMKHr50GTkw02z', 'Sevban Yerlikaya': '1Fh2ESBoYG3iN499TXlt4a1sqx5eiTAIi', 'Oğuzhan Görkem Koçak': '11rWE2DdUlN09l7LUVIu4icGOnLkV8jpI', 'Dilan Ergin': '1XXdEQ0bhvo8X2xOYkZhwzuZhMsHthENm', 'Elif Ecem Göktürk': '1sfuKDW7E8zlEPSt_1weee6jehGQwhtSt', 'Ahmet Selim Erdemli': '1Na2G0bocOw4LrNtulezdwogQXOo3tRGd', 'Sedef Bereketoğlu': '10hKauxsRcyBJn77Ii8RPbgeji8RS-6sz', 'Merve Savaş Kurtoğlu': '1Gl7WzFNlKaPGlr0oaunKU0AyiUYYcd-0', 'Hüseyin Yanmaz': '1OxQx1CCOPw1Xa3ARjnu_UEaSgslPlP8w', 'Recep Görkem Gökmen': '1LSkG-QDKZO0g8WP-Fj3wH3E0BAFev6TR', 'Yağmur Beyaztaş': '1qX2PGJhf2GhUMuVEMzQ5tUky1qvU4K28', 'Eylül Nurhan': '1aFZwq-YAINf8-DzcCPA9uJP8r_U2rXyv', 'Ece Acar': '1oCUHwBqPgG931_4VjEihSgmeGmMmTH-4', 'Ecem Hayırcı': '1aetQKHu5HC1SAQlT7lXrL885PnRIJw6Y', 'Ömer Şevki Sevil': '13RFW6nKFwAv5uOZv-JeyZEFZZ2bKMOni', 'Fatih Can Sevencan': '1ACmVVkvkc0Ri92jndd6ytqXqZ0u7c6Gf', 'Öykü Şara Sevim': '1XYGg9FxMlISgFunWNsk1w7rNHvwbfA_G', 'Cemre Çiftçi': '1nAVSUpB4iyatanhEShDNoogXDF3tbjRH', 'Ahmet Buğra Er': '1qb-bhkr3AGXTv8KGDC6ZwvL8W7peqdyA', 'Muharrem Atakan Kavakçı': '18HDmLCyzUfhuPvXOiPcZAFCd4YJCiWfc', 'Sinem Ceylan': '1Rd794Wq00Yiw1VqSr952sw3IaZzzkB9t', 'Güneş Büşra Demir': '1C3iWJjmDYCN7i47-wZU3f5jG99WTgihl', 'Melike Düzduran': '1QHz4uKy6gbO8jkZUfLEii4LglPXcKwtZ', 'Şerife Tuncel': '1rR6snQEItQHvmeU9Ey4apcnrHNNb98Sh', 'Emre Bakır': '1FQHiM09qCm0MnPq2Zbp6XhpCEDaCS0C3', 'Emin Uslu': '1tez_sHx4Zv6k7x6ku3N7ANR22tz2qDL6', 'Nurgül Akcı': '1CNPE9Tld-3DGqLswOdrKS5wd0Ms5iBb4', 'Deniz Topak': '1Hdp47DGaNKbICP1F_tEwr_VVc6ZDfMt7', 'Esra Soner': '1Jd5vzWkR0vIKyll7kBbXYaMRXS45O-YU', 'Cansu Aykut': '1Y_VwbNnMvldChSDJ6OkOs4PZjtpL0ywF', 'Eda Nur Unal': '17p14waYK_ApKqH9TNdN22DagoOcyirjk'}

def list_student_folders():
    """Drive'da tarama yapmak yerine doğrudan koda gömülü listeyi döndürür."""
    return STUDENT_FOLDERS

def get_sql_file_from_student_folder(service, student_folder_id):
    try:
        query = f"'{student_folder_id}' in parents and name contains '.sql' and trashed=false"
        response = service.files().list(
            q=query, spaces='drive', fields='files(id, name)',
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        
        files = response.get('files', [])
        if not files:
            return None, "Bu öğrencinin klasöründe .sql uzantılı ödev dosyası bulunamadı."
            
        file_id = files[0].get('id')
        file_name = files[0].get('name')
        
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            
        fh.seek(0)
        return fh.read().decode('utf-8', errors='replace'), file_name
    except Exception as e:
        return None, f"Dosya okuma hatası: {e}"