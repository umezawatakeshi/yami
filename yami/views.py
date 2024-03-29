from flask import Blueprint, current_app, g, abort, redirect, render_template, url_for, request
from . import logic
from tzlocal import get_localzone
from datetime import datetime, timedelta, timezone

bp = Blueprint("view", __name__)


@bp.route("/", defaults={"page": 1})
@bp.route("/list/<int:page>")
def held_list(page):
	return auction_list(page, False)

@bp.route("/ended/<int:page>")
def ended_list(page):
	return auction_list(page, True)

def auction_list(page, ended):
	if (page <= 0):
		abort(404)

	napp = current_app.config["YAMI_NUM_AUCTIONS_PER_PAGE"]
	auctions, num_auctions = logic.get_auction_list(napp, napp * (page - 1), ended)

	logic.commit()

	for auction in auctions:
		logic.append_localtime(auction)
	num_pages = (num_auctions + napp - 1) // napp

	return render_template("list.html", current_app=current_app, ended=ended, auctions=auctions, num_auctions=num_auctions, page=page, num_pages=num_pages)


@bp.route("/auction/<int:auction_id>")
def info(auction_id):
	auction, bids = logic.get_auction_info(auction_id, for_update=False)
	if auction is None:
		abort(404)

	logic.commit()

	logic.append_localtime(auction)
	for bid in bids:
		logic.append_localtime(bid)

	return render_template("info.html", current_app=current_app, auction=auction, bids=bids, EndType=logic.EndType)


@bp.route("/auction/<int:auction_id>/bid", methods=["POST"])
def bid(auction_id):
	class BidErrorCodes(logic.BidErrorCodes):
		BID_ERROR_NO_USERNAME = 10001
		BID_ERROR_NO_PRICE = 10002

	username = request.form.get("username")
	bidtype = request.form.get("bidtype")
	price = request.form.get("price", type=int)
	price_bid_min_sent = request.form.get("price_bid_min", type=int)
	price_prompt_sent = request.form.get("price_prompt", type=int)

	if username == "":
		return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, BidErrorCodes=BidErrorCodes, errcode=BidErrorCodes.BID_ERROR_NO_USERNAME)

	if bidtype == "normal":
		if price is None or price < 0:
			return render_template("bid.html", current_app=current_app, auction_id=auction_id, succeeded=False, BidErrorCodes=BidErrorCodes, errcode=BidErrorCodes.BID_ERROR_NO_PRICE)
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

	logic.commit()

	if ret == logic.BidErrorCodes.BID_ERROR_NOT_FOUND:
		abort(404)
	else:
		return render_template("bid.html", current_app=current_app, auction_id=auction_id, price=price, succeeded=(ret == BidErrorCodes.BID_OK), BidErrorCodes=BidErrorCodes, errcode=ret)


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
	auction["price_step_min"] = request.form.get("price_step_min", type=int)
	price_min_step_str = request.form.get("price_step_min")
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
		auction["datetime_end"] = g.datetime_now + timedelta(days=datetime_end_days)
	elif datetime_end_type == "datetime":
		datetime_end_date = datetime.strptime(datetime_end_date, "%Y-%m-%d")
		datetime_end_time = datetime.strptime(datetime_end_time, "%H:%M")
		datetime_end_local = get_localzone().localize(datetime_end_date.replace(hour=datetime_end_time.time().hour, minute=datetime_end_time.time().minute))
		auction["datetime_end"] = datetime_end_local.astimezone(timezone.utc)
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
		auction["price_step_min"] = 0
	elif auction["price_step_min"] is None or auction["price_step_min"] <= 0:
		abort(400)
	if auction["location"] is None:
		auction["location"] = ""
	if auction["description"] is None:
		auction["description"] = ""

	auction_id, password = logic.new_auction(auction)

	logic.commit()

	return render_template("new.html", current_app=current_app, auction_id=auction_id, password=password, succeeded=True)


@bp.route("/auction/<int:auction_id>/admin", methods=["POST"])
def admin(auction_id):
	admin_action = request.form.get("admin_action")
	password = request.form.get("password")

	if admin_action is None:
		abort(400)
	if password is None:
		abort(400)
	password = password.strip()

	if admin_action == "cancel":
		result = logic.cancel_auction(auction_id, password)
		logic.commit()
		if result == logic.CancelErrorCodes.CANCEL_ERROR_NOT_FOUND:
			abort(404)
		else:
			return render_template("cancel.html", current_app=current_app, auction_id=auction_id, succeeded=(result == logic.CancelErrorCodes.CANCEL_OK), CancelErrorCodes=logic.CancelErrorCodes, errcode=result)

	abort(400)
