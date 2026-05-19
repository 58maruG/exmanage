# -*- coding: utf-8 -*-
"""支出マスターデータ(data/expenses.json)を暗号化して docs/expenses.enc を生成する。

公開されるのはこの暗号化ファイルだけ。ダッシュボード側(docs/index.html)が
同じ方式(PBKDF2-SHA256 + AES-256-GCM)でパスワード復号する。

使い方:
    python tools/encrypt.py            # config.json の dashboard_password を使う
    python tools/encrypt.py <パスワード>  # パスワードを直接指定
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

# PBKDF2 の反復回数。ダッシュボード側(index.html)と必ず一致させること。
ITERATIONS = 200_000

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.json")
SRC_PATH = os.path.join(ROOT, "data", "expenses.json")
DST_PATH = os.path.join(ROOT, "docs", "expenses.enc")


def load_password() -> str:
    """コマンドライン引数 → config.json の順でパスワードを取得する。"""
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        return sys.argv[1]

    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        sys.exit(f"エラー: 設定ファイルが見つかりません: {CONFIG_PATH}")
    except json.JSONDecodeError as e:
        sys.exit(f"エラー: config.json の形式が不正です: {e}")

    password = (config.get("dashboard_password") or "").strip()
    if not password:
        sys.exit(
            "エラー: パスワードが未設定です。\n"
            "config.json の \"dashboard_password\" に閲覧用パスワードを設定するか、\n"
            "引数で指定してください: python tools/encrypt.py <パスワード>"
        )
    return password


def load_expenses() -> str:
    """支出マスターデータを読み込み、整形済みJSON文字列として返す。"""
    try:
        with open(SRC_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"エラー: 支出データが見つかりません: {SRC_PATH}")
    except json.JSONDecodeError as e:
        sys.exit(f"エラー: expenses.json の形式が不正です: {e}")

    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def encrypt(plaintext: str, password: str) -> dict:
    """AES-256-GCM で暗号化し、ダッシュボードが読める辞書を返す。"""
    salt = os.urandom(16)
    iv = os.urandom(12)

    kdf = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    key = kdf.derive(password.encode("utf-8"))

    # AESGCM.encrypt の戻り値は「暗号文 + 16バイト認証タグ」。
    # Web Crypto の AES-GCM も同じ並びを期待するためそのまま渡せる。
    ciphertext = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)

    return {
        "v": 1,
        "kdf": "PBKDF2-SHA256",
        "iterations": ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "data": base64.b64encode(ciphertext).decode("ascii"),
    }


def main() -> None:
    password = load_password()
    plaintext = load_expenses()
    payload = encrypt(plaintext, password)

    try:
        os.makedirs(os.path.dirname(DST_PATH), exist_ok=True)
        with open(DST_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except OSError as e:
        sys.exit(f"エラー: 暗号化ファイルの書き込みに失敗しました: {e}")

    print(f"暗号化完了: {DST_PATH}")


if __name__ == "__main__":
    main()
