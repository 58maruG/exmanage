# -*- coding: utf-8 -*-
"""Google Drive の receipts フォルダから未処理画像をダウンロードする。

環境変数:
    GDRIVE_CLIENT_ID       OAuth クライアントID
    GDRIVE_CLIENT_SECRET   OAuth クライアントシークレット
    GDRIVE_REFRESH_TOKEN   リフレッシュトークン
    GDRIVE_FOLDER_NAME     receipts フォルダ名（省略時: "receipts"）

使い方:
    python tools/gdrive_download.py
    → receipts/ フォルダに画像をダウンロードし、ファイル名一覧を標準出力する
"""

import json
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_PATH = os.path.join(ROOT, "data", "processed.json")
RECEIPTS_DIR = os.path.join(ROOT, "receipts")


def get_credentials():
    client_id = os.environ.get("GDRIVE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN", "").strip()

    missing = [k for k, v in [
        ("GDRIVE_CLIENT_ID", client_id),
        ("GDRIVE_CLIENT_SECRET", client_secret),
        ("GDRIVE_REFRESH_TOKEN", refresh_token),
    ] if not v]

    if missing:
        sys.exit(f"エラー: 環境変数が未設定です: {', '.join(missing)}")

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )


def find_receipts_folder(service):
    folder_name = os.environ.get("GDRIVE_FOLDER_NAME", "receipts")
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    result = service.files().list(q=query, fields="files(id, name)").execute()
    folders = result.get("files", [])
    if not folders:
        sys.exit(f"エラー: Google Drive に '{folder_name}' フォルダが見つかりません。")
    return folders[0]["id"]


def list_images(service, folder_id):
    query = (
        f"'{folder_id}' in parents and trashed = false and "
        "(mimeType = 'image/jpeg' or mimeType = 'image/png' or mimeType = 'image/heic')"
    )
    result = service.files().list(
        q=query, fields="files(id, name, mimeType)"
    ).execute()
    return result.get("files", [])


def load_processed_ids():
    try:
        with open(PROCESSED_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("processed", []))
    except FileNotFoundError:
        return set()


def download_file(service, file_id, dest_path):
    request = service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def main():
    creds = get_credentials()
    # httplib2 が環境変数の CA バンドルを無視するため明示的に指定する
    import httplib2
    ca_certs = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if ca_certs:
        http = httplib2.Http(ca_certs=ca_certs)
    else:
        http = httplib2.Http()
    from google_auth_httplib2 import AuthorizedHttp
    authorized_http = AuthorizedHttp(creds, http=http)
    service = build("drive", "v3", http=authorized_http)

    folder_id = find_receipts_folder(service)
    images = list_images(service, folder_id)

    if not images:
        print("Google Drive の receipts フォルダに画像が見つかりません。")
        return

    processed_ids = load_processed_ids()
    new_images = [img for img in images if img["id"] not in processed_ids]

    if not new_images:
        print("未処理の画像はありません。")
        return

    os.makedirs(RECEIPTS_DIR, exist_ok=True)

    downloaded = []
    for img in new_images:
        dest = os.path.join(RECEIPTS_DIR, img["name"])
        print(f"ダウンロード中: {img['name']} ...", flush=True)
        download_file(service, img["id"], dest)
        downloaded.append({"id": img["id"], "name": img["name"]})

    print(json.dumps({"downloaded": downloaded}, ensure_ascii=False))


if __name__ == "__main__":
    main()
