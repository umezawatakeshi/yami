#!/usr/bin/python3

# 時間切れによる終了処理を行う

from yami import create_app, db, yami
from datetime import datetime, timezone

app = create_app()

with app.app_context():
	datetime_now = datetime.now(timezone.utc)

	with db.get_dict_cursor() as cur:
		cur.execute("SELECT * FROM t_auction WHERE NOT ended AND datetime_end <= %s FOR UPDATE", (datetime_now,))
		auctions = cur.fetchall()

	for auction in auctions:
		yami.append_localtime(auction)
		auction["ended"] = (auction["ended"] != 0)

		with db.get_dict_cursor() as cur:
			cur.execute("SELECT * FROM t_bid WHERE auction_id = %s ORDER BY price DESC, datetime_bid ASC LIMIT %s", (auction["auction_id"], auction["quantity"],))
			bids = cur.fetchall()

		if auction["price_prompt"] is not None:
			bids = filter(lambda bid: bid["price"] < auction["price_prompt"], bids)

		yami.hammer(auction, bids, True, True)

	db.commit()
