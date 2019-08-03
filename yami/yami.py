from flask import Blueprint, current_app, g, abort, redirect, render_template, url_for, request
from . import db
from tzlocal import get_localzone
from datetime import datetime, timezone

bp = Blueprint("yami", __name__)


@bp.route("/", defaults={"page": 1})
@bp.route("/list/<int:page>")
def list(page):
	if (page <= 0):
		abort(404)

	cur = db.get_dict_cursor()
	napp = current_app.config["YAMI_NUM_AUCTIONS_PER_PAGE"]
	cur.execute("SELECT * FROM t_auction LEFT JOIN (SELECT auction_id as auction_id_bid, MAX(price) as price_current_high, COUNT(price) as num_bids FROM t_bid GROUP BY auction_id) AS maxbid ON t_auction.auction_id = maxbid.auction_id_bid WHERE NOT ended AND datetime_end > %s LIMIT %s OFFSET %s", (g.datetime_now, napp, napp * (page - 1)))
	auctions = cur.fetchall()
	cur.close()

	db.commit()

	for auction in auctions:
		append_localtime(auction)
		if (auction["num_bids"] is None):
			auction["num_bids"] = 0
		auction.pop("auction_id_bid", None)
		auction["ended"] = (auction["ended"] != 0)

	return render_template("list.html", current_app=current_app, auctions=auctions, page=page)


@bp.route("/auction/<int:auction_id>")
def info(auction_id):
	cur = db.get_dict_cursor()
	cur.execute("SELECT * FROM t_auction WHERE auction_id = %s", (auction_id,))
	auction = cur.fetchone()
	if (auction is None):
		cur.close()
		db.commit()
		abort(404)
	append_localtime(auction)
	auction["ended"] = (auction["ended"] != 0)
	cur.close()

	cur = db.get_dict_cursor()
	cur.execute("SELECT * FROM t_bid WHERE auction_id = %s ORDER BY price DESC, datetime_bid ASC", (auction_id,))
	bids = cur.fetchall()
	cur.close()

	db.commit()

	for bid in bids:
		append_localtime(bid)

	if (len(bids) < auction["quantity"]):
		price_bid_min = auction["price_start"]
	else:
		price_bid_min = bids[auction["quantity"] - 1]["price"] + auction["price_min_step"]
		if auction["price_prompt"] is not None and price_bid_min > auction["price_prompt"]:
			price_bid_min = auction["price_prompt"]

	ended = auction["ended"] or auction["datetime_end"] <= g.datetime_now

	return render_template("info.html", current_app=current_app, auction=auction, bids=bids, price_bid_min=price_bid_min, ended=ended)


@bp.route("/auction/<int:auction_id>/bid", methods=["POST"])
def bid(auction_id):
	username = request.form.get("username")
	bidtype = request.form.get("bidtype")
	price = request.form.get("price", type=int)
	price_bid_min_sent = request.form.get("price_bid_min", type=int)
	price_prompt_sent = request.form.get("price_prompt", type=int)

	if username == "":
		return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="入札者名が入力されていません。") # TODO i18n

	if bidtype == "min" or bidtype == "prompt":
		pass
	elif bidtype == "normal":
		if price is None or price < 0:
			return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="金額が入力されていません。") # TODO i18n
	else:
		abort(400)
	if price_bid_min_sent is None:
		abort(400)
	if username is None:
		abort(400)

	cur = db.get_dict_cursor()
	cur.execute("SELECT * FROM t_auction WHERE auction_id = %s FOR UPDATE", (auction_id,))
	auction = cur.fetchone()
	if (auction is None):
		cur.close()
		db.commit()
		abort(404)
	append_localtime(auction)
	auction["ended"] = (auction["ended"] != 0)
	cur.close()

	if g.datetime_now >= auction["datetime_end"] or auction["ended"]:
		return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="オークションはすでに終了しています。") # TODO i18n

	cur = db.get_dict_cursor()
	cur.execute("SELECT * FROM t_bid WHERE auction_id = %s ORDER BY price DESC, datetime_bid ASC LIMIT %s", (auction_id, auction["quantity"],))
	bids = cur.fetchall()
	cur.close()

	if (len(bids) < auction["quantity"]):
		price_bid_min = auction["price_start"]
	else:
		price_bid_min = bids[auction["quantity"] - 1]["price"] + auction["price_min_step"]
		if auction["price_prompt"] is not None and price_bid_min > auction["price_prompt"]:
			price_bid_min = auction["price_prompt"]

	if bidtype == "min":
		if (price_bid_min_sent != price_bid_min):
			return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="最低入札価格が変化しています。ほかの人がが先に入札した可能性があります。") # TODO i18n
		price = price_bid_min
	if bidtype == "prompt":
		if auction["price_prompt"] is None:
			abort(400)
		if price_prompt_sent is None:
			abort(400)
		if (price_prompt_sent != auction["price_prompt"]):
			return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="即決価格が変化しています。オークション情報が変更された可能性があります。") # TODO i18n
		price = auction["price_prompt"]

	if price < price_bid_min:
		return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="ほかの人が先に入札しました。") # TODO i18n

	if auction["price_prompt"] is not None and price >= auction["price_prompt"]:
		price = auction["price_prompt"]

	cur = db.get_cursor()
	cur.execute("INSERT INTO t_bid (auction_id, username, price, datetime_bid) VALUES (%s, %s, %s, %s)", (auction_id, username, price, g.datetime_now,))
	cur.close()

	if auction["price_prompt"] is not None and price >= auction["price_prompt"]:
		newbid = { "auction_id": auction_id, "username": username, "price": price, "datetime_bid": g.datetime_now }
		rest = auction["quantity"]
		for bid in bids:
			if bid["price"] >= auction["price_prompt"]:
				rest -= 1
		hammer(auction, (newbid,), rest <= 1, False)

	db.commit()

	return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=True, price=price)


@bp.route("/new", methods=["GET"])
def newform():
	return render_template("newform.html", current_app=current_app)


@bp.route("/new", methods=["POST"])
def new():
	itemname = request.form.get("itemname")
	quantity = request.form.get("quantity", type=int)
	username = request.form.get("username")
	datetime_end_type = request.form.get("datetime_end_type")
	datetime_end_days = request.form.get("datetime_end_days", type=int)
	datetime_end_date = request.form.get("datetime_end_date")
	datetime_end_time = request.form.get("datetime_end_time")
	price_start = request.form.get("price_start", type=int)
	price_prompt = request.form.get("price_prompt", type=int)
	price_prompt_str = request.form.get("price_prompt")
	price_min_step = request.form.get("price_min_step", type=int)
	price_min_step_str = request.form.get("price_min_step")
	location = request.form.get("location")
	description = request.form.get("description")

	if itemname is None or itemname == "":
		abort(400)
	if quantity is None or quantity <= 0:
		abort(400)
	if username is None or username == "":
		abort(400)
	if datetime_end_type is None:
		abort(400)
	elif datetime_end_type == "duration":
		if datetime_end_days is None or datetime_end_days <= 0:
			abort(400)
		datetime_end = datetime.fromtimestamp(g.datetime_now.timestamp() + 86400 * datetime_end_days, timezone.utc)
	elif datetime_end_type == "datetime":
		datetime_end_date = datetime.strptime(datetime_end_date, "%Y-%m-%d")
		datetime_end_time = datetime.strptime(datetime_end_time, "%H:%M")
		datetime_end_local = get_localzone().localize(datetime_end_date.replace(hour=datetime_end_time.time().hour, minute=datetime_end_time.time().minute))
		datetime_end = datetime.fromtimestamp(datetime_end_local.timestamp(), tz=timezone.utc)
		if datetime_end <= g.datetime_now:
			abort(400)
	else:
		abort(400)
	if price_start is None or price_start < 0:
		abort(400)
	if price_prompt_str is None or price_prompt_str == "":
		price_prompt = None
	elif price_prompt is None or price_prompt < price_start:
		abort(400)
	if price_min_step_str is None or price_min_step_str == "":
		price_min_step = 0
	elif price_min_step is None or price_min_step <= 0:
		abort(400)
	if location is None:
		location = ""
	if description is None or description == "":
		abort(400)

	cur = db.get_cursor()
	cur.execute("INSERT INTO t_auction (type, itemname, quantity, username, datetime_start, datetime_end, datetime_update, price_start, price_prompt, price_min_step, location, description) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
		(itemname, quantity, username, g.datetime_now, datetime_end, g.datetime_now, price_start, price_prompt, price_min_step, location, description,))
	cur.execute("SELECT LAST_INSERT_ID() FROM t_auction")
	auction_id = cur.fetchone()[0]
	cur.close()

	db.commit()

	return render_template("new.html", current_app=current_app, auction_id=auction_id, succeeded=True)


def append_localtime(dic):
	appended = dict()
	for key in dic.keys():
		if (key.startswith("datetime_")):
			dic[key] = dic[key].replace(tzinfo=timezone.utc)
			appended[key + "_local"] = datetime.fromtimestamp(dic[key].timestamp(), tz=get_localzone())
	dic.update(appended)
	return dic

def hammer(auction, bids, ended, expired):
	for bid in bids:
		pass

	if not ended:
		return

	cur = db.get_cursor()
	cur.execute("UPDATE t_auction SET ended = 1 WHERE auction_id = %s", (auction["auction_id"],))
	cur.close()
