import os
import json
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()

# Load service account JSON string from .env
service_account_info = json.loads(os.getenv("GOOGLE_CALENDAR_CREDENTIALS"))

def authenticate():
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return build("drive", "v3", credentials=credentials)

def upload_file_to_drive(file_path, mime_type=None, folder_id=None):
    service = authenticate()
    file_name = os.path.basename(file_path)

    metadata = {"name": file_name}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    uploaded_file = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, parents"
    ).execute()

    file_id = uploaded_file["id"]
    print(f"✅ File uploaded. File ID: {file_id}")
    print(f"🔗 File link: https://drive.google.com/file/d/{file_id}/view")

    if folder_id:
        print(f"📁 File was uploaded into folder: https://drive.google.com/drive/folders/{folder_id}")
    else:
        print("⚠️ No folder specified — file is in service account's private Drive")

# 📂 Put your shared folder ID here (from Drive URL)
SHARED_FOLDER_ID = os.getenv("SHARED_FOLDER_ID")
# 📄 Upload call (update path and MIME type as needed)
upload_file_to_drive("meet_links.txt", mime_type="text/plain", folder_id=SHARED_FOLDER_ID)


