from flask import Blueprint, current_app, g, abort, redirect, render_template, url_for, request
from . import db, logic
from tzlocal import get_localzone
from datetime import datetime, timezone

bp = Blueprint("view", __name__)


@bp.route("/", defaults={"page": 1})
@bp.route("/list/<int:page>")
def list(page):
	if (page <= 0):
		abort(404)

	napp = current_app.config["YAMI_NUM_AUCTIONS_PER_PAGE"]
	auctions = logic.get_auction_list(napp, napp * (page - 1), False)

	db.commit()

	return render_template("list.html", current_app=current_app, auctions=auctions, page=page)


@bp.route("/auction/<int:auction_id>")
def info(auction_id):
	auction, bids = logic.get_auction_info(auction_id, for_update=False)
	if auction is None:
		abort(404)

	db.commit()

	return render_template("info.html", current_app=current_app, auction=auction, bids=bids)


@bp.route("/auction/<int:auction_id>/bid", methods=["POST"])
def bid(auction_id):
	username = request.form.get("username")
	bidtype = request.form.get("bidtype")
	price = request.form.get("price", type=int)
	price_bid_min_sent = request.form.get("price_bid_min", type=int)
	price_prompt_sent = request.form.get("price_prompt", type=int)

	if username == "":
		return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="入札者名が入力されていません。") # TODO i18n

	if bidtype == "normal":
		if price is None or price < 0:
			return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="金額が入力されていません。") # TODO i18n
	elif bidtype == "min":
		price = price_bid_min_sent
	elif bidtype == "prompt":
		price = price_prompt_sent
	else:
		abort(400)
	if price_bid_min_sent is None:
		abort(400)
	if username is None:
		abort(400)

	ret = logic.bid_auction({"auction_id": auction_id, "price": price, "username": username, "datetime_bid": g.datetime_now})
	if ret == logic.BID_OK:
		return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=True, price=price)
	elif ret == logic.BID_ERROR_NOT_FOUND:
		abort(404)
	elif ret == logic.BID_ERROR_ALREADY_ENDED:
		return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="オークションはすでに終了しています。") # TODO i18n
	elif ret == logic.BID_ERROR_ANOTHER_ONE_BIDDED_FIRST:
		return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="他の人が先に入札しました。") # TODO i18n
	else:
		return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, reason="不明なアプリケーションエラーが発生しました。" + ret) # TODO i18n


@bp.route("/new", methods=["GET"])
def newform():
	return render_template("newform.html", current_app=current_app)


@bp.route("/new", methods=["POST"])
def new():
	auction = {}
	auction["itemname"] = request.form.get("itemname")
	auction["quantity"] = request.form.get("quantity", type=int)
	auction["username"] = request.form.get("username")
	datetime_end_type = request.form.get("datetime_end_type")
	datetime_end_days = request.form.get("datetime_end_days", type=int)
	datetime_end_date = request.form.get("datetime_end_date")
	datetime_end_time = request.form.get("datetime_end_time")
	auction["price_start"] = request.form.get("price_start", type=int)
	auction["price_prompt"] = request.form.get("price_prompt", type=int)
	price_prompt_str = request.form.get("price_prompt")
	auction["price_min_step"] = request.form.get("price_min_step", type=int)
	price_min_step_str = request.form.get("price_min_step")
	auction["location"] = request.form.get("location")
	auction["description"] = request.form.get("description")

	if auction["itemname"] is None or auction["itemname"] == "":
		abort(400)
	if auction["quantity"] is None or auction["quantity"] <= 0:
		abort(400)
	if auction["username"] is None or auction["username"] == "":
		abort(400)
	if datetime_end_type is None:
		abort(400)
	elif datetime_end_type == "duration":
		if datetime_end_days is None or datetime_end_days <= 0:
			abort(400)
		auction["datetime_end"] = datetime.fromtimestamp(g.datetime_now.timestamp() + 86400 * datetime_end_days, timezone.utc)
	elif datetime_end_type == "datetime":
		datetime_end_date = datetime.strptime(datetime_end_date, "%Y-%m-%d")
		datetime_end_time = datetime.strptime(datetime_end_time, "%H:%M")
		datetime_end_local = get_localzone().localize(datetime_end_date.replace(hour=datetime_end_time.time().hour, minute=datetime_end_time.time().minute))
		auction["datetime_end"] = datetime.fromtimestamp(datetime_end_local.timestamp(), tz=timezone.utc)
		if auction["datetime_end"] <= g.datetime_now:
			abort(400)
	else:
		abort(400)
	if auction["price_start"] is None or auction["price_start"] < 0:
		abort(400)
	if price_prompt_str is None or price_prompt_str == "":
		auction["price_prompt"] = None
	elif auction["price_prompt"] is None or auction["price_prompt"] < auction["price_start"]:
		abort(400)
	if price_min_step_str is None or price_min_step_str == "":
		auction["price_min_step"] = 0
	elif auction["price_min_step"] is None or auction["price_min_step"] <= 0:
		abort(400)
	if auction["location"] is None:
		auction["location"] = ""
	if auction["description"] is None or auction["description"] == "":
		abort(400)

	auction_id = logic.new_auction(auction)

	db.commit()

	return render_template("new.html", current_app=current_app, auction_id=auction_id, succeeded=True)
