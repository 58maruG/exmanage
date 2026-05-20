# -*- coding: utf-8 -*-
"""Google Drive の receipt フォルダから未処理画像をダウンロードし、処理済みフォルダへ移動する。

環境変数:
    GDRIVE_CLIENT_ID       OAuth クライアントID
    GDRIVE_CLIENT_SECRET   OAuth クライアントシークレット
    GDRIVE_REFRESH_TOKEN   リフレッシュトークン
    GDRIVE_FOLDER_NAME     取り込みフォルダ名（省略時: "receipt"）
    GDRIVE_DONE_FOLDER     処理済み移動先フォルダ名（省略時: "Read receipt(仮)"）

使い方:
    python tools/gdrive_download.py
    → receipts/ フォルダに画像をダウンロードし、GDrive 上のファイルを処理済みフォルダへ移動する
"""

import json
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEIPTS_DIR = os.path.join(ROOT, "receipts")

SOURCE_FOLDER_NAME = os.environ.get("GDRIVE_FOLDER_NAME", "receipt")
DONE_FOLDER_NAME = os.environ.get("GDRIVE_DONE_FOLDER", "Read receipt")


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
    )


def find_folder(service, name):
    query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    result = service.files().list(q=query, fields="files(id, name)").execute()
    folders = result.get("files", [])
    return folders[0]["id"] if folders else None


def find_or_create_done_folder(service):
    folder_id = find_folder(service, DONE_FOLDER_NAME)
    if folder_id:
        return folder_id

    print(f"フォルダ '{DONE_FOLDER_NAME}' が見つからないため作成します...", flush=True)
    meta = {
        "name": DONE_FOLDER_NAME,
        "mimeType": "application/vnd.google-apps.folder",
    }
    result = service.files().create(body=meta, fields="id").execute()
    return result["id"]


def list_images(service, folder_id):
    query = (
        f"'{folder_id}' in parents and trashed = false and "
        "(mimeType = 'image/jpeg' or mimeType = 'image/png' or mimeType = 'image/heic')"
    )
    result = service.files().list(
        q=query, fields="files(id, name, mimeType, parents)"
    ).execute()
    return result.get("files", [])


def download_file(service, file_id, dest_path):
    request = service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def move_to_done(service, file_id, current_parents, done_folder_id):
    """ファイルを処理済みフォルダへ移動する（親を差し替え）。"""
    service.files().update(
        fileId=file_id,
        addParents=done_folder_id,
        removeParents=",".join(current_parents),
        fields="id, parents",
    ).execute()


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

    source_id = find_folder(service, SOURCE_FOLDER_NAME)
    if not source_id:
        sys.exit(f"エラー: Google Drive に '{SOURCE_FOLDER_NAME}' フォルダが見つかりません。")

    images = list_images(service, source_id)

    if not images:
        print(f"Google Drive の '{SOURCE_FOLDER_NAME}' フォルダに画像が見つかりません。")
        return

    done_folder_id = find_or_create_done_folder(service)
    os.makedirs(RECEIPTS_DIR, exist_ok=True)

    downloaded = []
    errors = []
    for img in images:
        dest = os.path.join(RECEIPTS_DIR, img["name"])
        print(f"ダウンロード中: {img['name']} ...", flush=True)
        try:
            download_file(service, img["id"], dest)
            downloaded.append(img["name"])
        except Exception as e:
            print(f"  エラー: {img['name']} のダウンロードに失敗しました: {e}", flush=True)
            errors.append(img["name"])
            continue
        try:
            move_to_done(service, img["id"], img.get("parents", [source_id]), done_folder_id)
            print(f"  → '{DONE_FOLDER_NAME}' へ移動しました", flush=True)
        except Exception as e:
            print(f"  警告: {img['name']} の移動に失敗しました（ダウンロードは完了）: {e}", flush=True)

    print(json.dumps({"downloaded": downloaded, "errors": errors}, ensure_ascii=False))


if __name__ == "__main__":
    main()
