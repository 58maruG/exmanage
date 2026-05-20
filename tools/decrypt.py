# -*- coding: utf-8 -*-
"""docs/expenses.enc を復号して data/expenses.json を生成する。

使い方:
    python tools/decrypt.py <パスワード>
    python tools/decrypt.py          # DASHBOARD_PASSWORD 環境変数を使う
"""

import base64
import json
import os
import sys

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.hashes import SHA256
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    sys.exit(
        "エラー: cryptography パッケージが見つかりません。\n"
        "次のコマンドでインストールしてください: python -m pip install cryptography"
    )

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PATH = os.path.join(ROOT, "docs", "expenses.enc")
DST_PATH = os.path.join(ROOT, "data", "expenses.json")


def load_password() -> str:
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        return sys.argv[1]
    password = os.environ.get("DASHBOARD_PASSWORD", "").strip()
    if not password:
        sys.exit(
            "エラー: パスワードが未設定です。\n"
            "引数で指定するか、DASHBOARD_PASSWORD 環境変数を設定してください。"
        )
    return password


def main() -> None:
    password = load_password()

    try:
        with open(SRC_PATH, encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError:
        sys.exit(f"エラー: 暗号化ファイルが見つかりません: {SRC_PATH}")

    salt = base64.b64decode(payload["salt"])
    iv = base64.b64decode(payload["iv"])
    ciphertext = base64.b64decode(payload["data"])
    iterations = payload.get("iterations", 200_000)

    kdf = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=iterations)
    key = kdf.derive(password.encode("utf-8"))

    try:
        plaintext = AESGCM(key).decrypt(iv, ciphertext, None)
    except Exception:
        sys.exit("エラー: 復号に失敗しました。パスワードが間違っている可能性があります。")

    data = json.loads(plaintext.decode("utf-8"))

    os.makedirs(os.path.dirname(DST_PATH), exist_ok=True)
    with open(DST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"復号完了: {DST_PATH}")


if __name__ == "__main__":
    main()
