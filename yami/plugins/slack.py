from flask import current_app, render_template
import urllib


def escape(s):
	return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def is_enabled():
	return "SLACK_INCOMING_WEBHOOK_URL" in current_app.config


def request_json(jsonstr):
	req = urllib.request.Request(current_app.config["SLACK_INCOMING_WEBHOOK_URL"], jsonstr.encode(), { "Content-Type": "application/json"})
	urllib.request.urlopen(req)


def after_bid_auction(auction, bid, extended):
	if is_enabled():
		jsonstr = render_template("slack/bid.json", current_app=current_app, auction=auction, bid=bid, extended=extended, slack_escape=escape)
		request_json(jsonstr)


def after_new_auction(auction, auction_id, password):
	if is_enabled():
		jsonstr = render_template("slack/new.json", current_app=current_app, auction_id=auction_id, auction=auction, slack_escape=escape)
		request_json(jsonstr)


def after_hammer(auction, bid, ended, expired):
	if is_enabled():
		jsonstr = render_template("slack/hammer.json", current_app=current_app, auction=auction, bid=bid, ended=ended, expired=expired, slack_escape=escape)
		request_json(jsonstr)


def after_end(auction, expired):
	if is_enabled():
		jsonstr = render_template("slack/end.json", current_app=current_app, auction=auction, expired=expired, slack_escape=escape)
		request_json(jsonstr)


def after_cancel(auction, isadmin):
	if is_enabled():
		jsonstr = render_template("slack/cancel.json", current_app=current_app, auction=auction, isadmin=isadmin, slack_escape=escape)
		request_json(jsonstr)
