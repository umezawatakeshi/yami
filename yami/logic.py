from flask import current_app, g, request
from . import db
import tzlocal
from datetime import datetime, timedelta, timezone
import decimal
from decimal import Decimal
import hashlib
import base64
import secrets


def get_auction_list(limit, offset, ended):
	if ended:
		flipcond = " NOT"
	else:
		flipcond = ""

	with db.get_cursor() as cur:
		cur.execute("SELECT COUNT(auction_id) FROM t_auction WHERE" + flipcond + " (ended = false AND datetime_end > %s)", (g.datetime_now,))
		num_auctions = cur.fetchone()[0]

	with db.get_dict_cursor() as cur:
		cur.execute("SELECT * FROM t_auction LEFT JOIN (SELECT auction_id, MAX(price) as price_current_high, COUNT(price) as num_bids FROM t_bid GROUP BY auction_id) AS maxbid USING(auction_id) WHERE" + flipcond + " (ended = false AND datetime_end > %s) ORDER BY datetime_end ASC LIMIT %s OFFSET %s", (g.datetime_now, limit, offset))
		auctions = cur.fetchall()

	for auction in auctions:
		aware_utc_datetime(auction)
		auction["ended"] = (auction["ended"] != 0 or auction["datetime_end"] <= g.datetime_now)
		if auction["num_bids"] is None:
			auction["num_bids"] = 0
		if auction["num_bids"] < auction["quantity"]:
			auction["price_current_low"] = None
		elif auction["quantity"] > 1:
			with db.get_cursor() as cur:
				cur.execute("SELECT price FROM t_bid WHERE auction_id = %s ORDER BY price LIMIT 1 OFFSET %s", (auction["auction_id"], auction["quantity"]-1))
				row = cur.fetchone()
				if row is None:
					auction["price_current_low"] = None
				else:
					auction["price_current_low"] = row[0]
		else:
			auction["price_current_low"] = auction["price_current_high"]
		set_price_bid_min(auction)

	return auctions, num_auctions


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
		aware_utc_datetime(auction)
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
		aware_utc_datetime(bid)

	if len(bids) == 0:
		auction["price_current_high"] = None
	else:
		auction["price_current_high"] = bids[0]["price"]

	if len(bids) < auction["quantity"]:
		auction["price_current_low"] = None
	else:
		auction["price_current_low"] = bids[auction["quantity"] - 1]["price"]

	set_price_bid_min(auction)

	return auction, bids


class BidErrorCodes:
	BID_OK = 0
	BID_ERROR_NOT_FOUND = 1
	BID_ERROR_ALREADY_ENDED = 2
	BID_ERROR_ANOTHER_ONE_BIDDED_FIRST = 3

def bid_auction(newbid):
	auction, bids = get_auction_info(newbid["auction_id"], for_update=True)
	if auction is None:
		return BidErrorCodes.BID_ERROR_NOT_FOUND

	if auction["ended"]:
		return BidErrorCodes.BID_ERROR_ALREADY_ENDED

	if newbid["price"] < auction["price_bid_min"]:
		return BidErrorCodes.BID_ERROR_ANOTHER_ONE_BIDDED_FIRST

	if auction["price_prompt"] is not None and newbid["price"] >= auction["price_prompt"]:
		newbid["price"] = auction["price_prompt"]

	newbid["datetime_bid"] = g.datetime_now

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
		hammer(auction, [newbid], rest <= 1, False)
	else:
		extended = g.datetime_now + timedelta(seconds=current_app.config["YAMI_AUTO_EXTENSION"])
		if auction["datetime_end"] < extended:
			with db.get_cursor() as cur:
				cur.execute("UPDATE t_auction SET datetime_end = %s WHERE auction_id = %s", (extended, auction["auction_id"]))

	with db.get_cursor() as cur:
		cur.execute("UPDATE t_auction SET datetime_update = %s WHERE auction_id = %s", (g.datetime_now, auction["auction_id"]))

	return BidErrorCodes.BID_OK


default_password_hash_iterations = 36000
default_password_hash_digest = "sha256"

def encode_password(password, salt, iterations=None):
	if iterations is None:
		iterations = default_password_hash_iterations
	password_bytes = password.encode("ascii")
	salt_bytes = salt.encode("ascii")
	hash = hashlib.pbkdf2_hmac(default_password_hash_digest, password_bytes, salt_bytes, iterations)
	hash = base64.b64encode(hash).decode("ascii").strip()
	return "pbkdf2_%s$%d$%s$%s" % (default_password_hash_digest, iterations, salt, hash)


def check_password(password, encoded_password):
	# Currently, algorithm changing is not supported.
	# 今のところアルゴリズムの変更には対応していない
	encoded_fields = encoded_password.split("$")
	if len(encoded_fields) != 4:
		return False
	if encoded_fields[0] != "pbkdf2_sha256":
		return False
	password_bytes = password.encode("ascii")
	iterations = int(encoded_fields[1])
	salt_bytes = encoded_fields[2].encode("ascii")
	hash = hashlib.pbkdf2_hmac(default_password_hash_digest, password_bytes, salt_bytes, iterations)
	hash = base64.b64encode(hash).decode("ascii").strip()
	return hash == encoded_fields[3]


def check_auction_admin(password, saved_password):
	if check_password(password, saved_password):
		return (True, False)
	if "YAMI_ADMIN_PASSWORD" in current_app.config and check_password(password, current_app.config["YAMI_ADMIN_PASSWORD"]):
		return (True, True)
	return (False, False)


def new_auction(auction):
	password = secrets.token_hex(8)
	salt = secrets.token_urlsafe(8)
	encoded_password = encode_password(password, salt)

	with db.get_cursor() as cur:
		cur.execute("INSERT INTO t_auction (type, itemname, quantity, username, datetime_start, datetime_end, datetime_update, price_start, price_prompt, price_step_min, location, description) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
			(auction["itemname"], auction["quantity"], auction["username"], g.datetime_now, auction["datetime_end"], g.datetime_now, auction["price_start"], auction["price_prompt"], auction["price_step_min"], auction["location"], auction["description"]))
		cur.execute("SELECT LAST_INSERT_ID() FROM t_auction")
		auction_id = cur.fetchone()[0]
		cur.execute("INSERT INTO t_auction_password (auction_id, password) VALUES (%s, %s)",
			(auction_id, encoded_password))

	return (auction_id, password)


class CancelErrorCodes:
	CANCEL_OK = 0
	CANCEL_ERROR_NOT_FOUND = 1
	CANCEL_ERROR_BAD_PASSWORD = 2

class EndType:
	ENDTYPE_NORMAL = 0
	ENDTYPE_CANCELED_BY_SELLER = 1
	ENDTYPE_CANCELED_BY_ADMIN = 2

def cancel_auction(auction_id, password):
	with db.get_cursor() as cur:
		cur.execute("SELECT password FROM t_auction_password WHERE auction_id = %s", (auction_id,))
		row = cur.fetchone()
	if row is None:
		return CancelErrorCodes.CANCEL_ERROR_NOT_FOUND
	encoded_password = row[0]

	checked, isadmin = check_auction_admin(password, encoded_password)
	if not checked:
		return CancelErrorCodes.CANCEL_ERROR_BAD_PASSWORD

	with db.get_cursor() as cur:
		cur.execute("UPDATE t_auction SET ended = 1, endtype = %s, datetime_update = %s WHERE auction_id = %s",
			(EndType.ENDTYPE_CANCELED_BY_ADMIN if isadmin else EndType.ENDTYPE_CANCELED_BY_SELLER, g.datetime_now, auction_id))

	return CancelErrorCodes.CANCEL_OK


def check_expiration():
	with db.get_dict_cursor() as cur:
		cur.execute("SELECT * FROM t_auction WHERE ended = false AND datetime_end <= %s FOR UPDATE", (g.datetime_now,))
		auctions = cur.fetchall()

	for auction in auctions:
		aware_utc_datetime(auction)
		auction["ended"] = (auction["ended"] != 0)

		with db.get_dict_cursor() as cur:
			cur.execute("SELECT * FROM t_bid WHERE auction_id = %s ORDER BY price DESC, datetime_bid ASC LIMIT %s", (auction["auction_id"], auction["quantity"],))
			bids = cur.fetchall()

		if auction["price_prompt"] is not None:
			bids = filter(lambda bid: bid["price"] < auction["price_prompt"], bids)

		hammer(auction, bids, True, True)

		with db.get_cursor() as cur:
			cur.execute("UPDATE t_auction SET datetime_update = datetime_end WHERE auction_id = %s", (auction["auction_id"],))

	db.commit()


def aware_utc_datetime(dic):
	for key in dic.keys():
		if key.startswith("datetime_"):
			dic[key] = dic[key].replace(tzinfo=timezone.utc)
	return dic

def append_localtime(dic):
	appended = dict()
	for key in dic.keys():
		if key.startswith("datetime_") and not key.endswith("_local"):
			appended[key + "_local"] = dic[key].astimezone(tzlocal.get_localzone())
	dic.update(appended)
	return dic

def hammer(auction, bids, ended, expired):
	for bid in bids:
		pass

	if not ended:
		return

	with db.get_cursor() as cur:
		cur.execute("UPDATE t_auction SET ended = 1 WHERE auction_id = %s", (auction["auction_id"],))

def calc_price_step_min(auction):
	price_step_min = current_app.config["YAMI_PRICE_STEP_MIN"]
	if auction["price_step_min"] > price_step_min:
		price_step_min = auction["price_step_min"]

	price_reference = auction["price_current_low"] if current_app.config["YAMI_PRICE_STEP_FROM_CURRENT_PRICE"] else auction["price_start"]
	if price_reference == 0:
		return price_step_min

	price_reference = Decimal(price_reference)
	exponent = price_reference.adjusted()
	exp10 = Decimal(1).scaleb(exponent)
	mantissa = price_reference / exp10
	rule = current_app.config["YAMI_PRICE_STEP_RULE"]
	rkeys = sorted(rule.keys())
	for i in range(len(rule) - 1):
		if mantissa >= rkeys[i] and mantissa < rkeys[i+1]:
			step_from_rule = exp10 * rule[rkeys[i]]
			break
	else:
		step_from_rule = exp10 * rule[rkeys[-1]]
	step_from_rule = int(step_from_rule)

	if step_from_rule > price_step_min:
		price_step_min = step_from_rule
	return price_step_min

def set_price_bid_min(auction):
	if auction["price_current_low"] is None:
		auction["price_bid_min"] = auction["price_start"]
	else:
		price_step_min = calc_price_step_min(auction)
		auction["price_bid_min"] = auction["price_current_low"] + price_step_min
		if auction["price_prompt"] is not None and auction["price_bid_min"] > auction["price_prompt"]:
			auction["price_bid_min"] = auction["price_prompt"]

def commit():
	db.commit()

def rollback():
	db.rollback()
