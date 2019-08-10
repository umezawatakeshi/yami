from flask import current_app, g, request
from . import db
from tzlocal import get_localzone
from datetime import datetime, timezone


def get_auction_list(limit, offset, ended):
	if ended:
		flipcond = " NOT"
	else:
		flipcond = ""

	with db.get_dict_cursor() as cur:
		cur.execute("SELECT * FROM t_auction LEFT JOIN (SELECT auction_id, MAX(price) as price_current_high, COUNT(price) as num_bids FROM t_bid GROUP BY auction_id) AS maxbid USING(auction_id) WHERE" + flipcond + " (ended = false AND datetime_end > %s) ORDER BY datetime_end ASC LIMIT %s OFFSET %s", (g.datetime_now, limit, offset))
		auctions = cur.fetchall()

	for auction in auctions:
		append_localtime(auction)
		if auction["num_bids"] is None:
			auction["num_bids"] = 0
		auction["ended"] = (auction["ended"] != 0 or auction["datetime_end"] <= g.datetime_now)

	return auctions


def get_auction_info(auction_id, for_update):
	if for_update:
		auction_select_decoration = " FOR UPDATE"
	else:
		auction_select_decoration = ""

	with db.get_dict_cursor() as cur:
		cur.execute("SELECT * FROM t_auction WHERE auction_id = %s" + auction_select_decoration, (auction_id,))
		auction = cur.fetchone()
		if auction is None:
			return None, None
		append_localtime(auction)
		auction["ended"] = (auction["ended"] != 0 or auction["datetime_end"] <= g.datetime_now)

	if for_update:
		bid_select_decoration = " LIMIT %s"
		bid_select_parameters = (auction_id, auction["quantity"])
	else:
		bid_select_decoration = ""
		bid_select_parameters = (auction_id,)
		
	with db.get_dict_cursor() as cur:
		cur.execute("SELECT * FROM t_bid WHERE auction_id = %s ORDER BY price DESC, datetime_bid ASC" + bid_select_decoration, bid_select_parameters)
		bids = cur.fetchall()

	for bid in bids:
		append_localtime(bid)

	if len(bids) < auction["quantity"]:
		auction["price_bid_min"] = auction["price_start"]
	else:
		auction["price_bid_min"] = bids[auction["quantity"] - 1]["price"] + auction["price_min_step"]
		if auction["price_prompt"] is not None and auction["price_bid_min"] > auction["price_prompt"]:
			auction["price_bid_min"] = auction["price_prompt"]

	return auction, bids


BID_OK = 0
BID_ERROR_NOT_FOUND = 1
BID_ERROR_ALREADY_ENDED = 2
BID_ERROR_ANOTHER_ONE_BIDDED_FIRST = 3

def bid_auction(newbid):
	auction, bids = get_auction_info(newbid["auction_id"], for_update=True)
	if auction is None:
		return BID_ERROR_NOT_FOUND

	if auction["ended"]:
		return BID_ERROR_ALREADY_ENDED

	if newbid["price"] < auction["price_bid_min"]:
		return BID_ERROR_ANOTHER_ONE_BIDDED_FIRST

	if auction["price_prompt"] is not None and newbid["price"] >= auction["price_prompt"]:
		newbid["price"] = auction["price_prompt"]

	with db.get_cursor() as cur:
		cur.execute("INSERT INTO t_bid (auction_id, username, price, datetime_bid) VALUES (%s, %s, %s, %s)", (newbid["auction_id"], newbid["username"], newbid["price"], g.datetime_now,))
		cur.execute("SELECT LAST_INSERT_ID() FROM t_bid")
		newbid["bid_id"] = cur.fetchone()[0]

	if auction["price_prompt"] is not None and newbid["price"] >= auction["price_prompt"]:
		newbid["datetime_bid"] = g.datetime_now
		rest = auction["quantity"]
		for bid in bids:
			if bid["price"] >= auction["price_prompt"]:
				rest -= 1
		hammer(auction, (newbid,), rest <= 1, False)

	db.commit()

	return BID_OK


def new_auction(auction):
	with db.get_cursor() as cur:
		cur.execute("INSERT INTO t_auction (type, itemname, quantity, username, datetime_start, datetime_end, datetime_update, price_start, price_prompt, price_min_step, location, description) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
			(auction["itemname"], auction["quantity"], auction["username"], g.datetime_now, auction["datetime_end"], g.datetime_now, auction["price_start"], auction["price_prompt"], auction["price_min_step"], auction["location"], auction["description"]))
		cur.execute("SELECT LAST_INSERT_ID() FROM t_auction")
		auction_id = cur.fetchone()[0]

	return auction_id


def check_expiration():
	with db.get_dict_cursor() as cur:
		cur.execute("SELECT * FROM t_auction WHERE NOT ended AND datetime_end <= %s FOR UPDATE", (g.datetime_now,))
		auctions = cur.fetchall()

	for auction in auctions:
		append_localtime(auction)
		auction["ended"] = (auction["ended"] != 0)

		with db.get_dict_cursor() as cur:
			cur.execute("SELECT * FROM t_bid WHERE auction_id = %s ORDER BY price DESC, datetime_bid ASC LIMIT %s", (auction["auction_id"], auction["quantity"],))
			bids = cur.fetchall()

		if auction["price_prompt"] is not None:
			bids = filter(lambda bid: bid["price"] < auction["price_prompt"], bids)

		hammer(auction, bids, True, True)

	db.commit()


def append_localtime(dic):
	appended = dict()
	for key in dic.keys():
		if key.startswith("datetime_"):
			dic[key] = dic[key].replace(tzinfo=timezone.utc)
			appended[key + "_local"] = datetime.fromtimestamp(dic[key].timestamp(), tz=get_localzone())
	dic.update(appended)
	return dic

def hammer(auction, bids, ended, expired):
	for bid in bids:
		pass

	if not ended:
		return

	with db.get_cursor() as cur:
		cur.execute("UPDATE t_auction SET ended = 1 WHERE auction_id = %s", (auction["auction_id"],))