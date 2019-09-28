#!/usr/bin/python3

# 暗号化されたパスワードを生成する
# 管理者パスワード向けに、長い salt を使うようにしてある

import sys
from yami import logic
import secrets

for password in sys.stdin:
	password = password.strip()
	salt = secrets.token_urlsafe(24)
	print(logic.encode_password(password, salt))
