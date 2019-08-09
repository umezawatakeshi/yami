#!/usr/bin/python3

# 時間切れによる終了処理を行う

from flask import g
from yami import create_app, logic
from datetime import datetime, timezone

app = create_app()

with app.app_context():
	g.datetime_now = datetime.now(timezone.utc)
	logic.check_expiration()
