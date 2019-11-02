import pytest
import pymysql
from unittest import mock
from yami import create_app, logic
from flask import g
from datetime import datetime, timedelta, timezone
import secrets


def create_cursor_mock():
	m = mock.MagicMock()
	# do not track these magic methods
	m.__enter__ = lambda self: self
	m.__exit__ = lambda self, exc_type, exc_value, traceback: self.close()
	return m


def test_new_auction(monkeypatch):
	app = create_app({
	})
	auction = {
		"itemname": "foo",
		"quantity": 123,
		"username": "bar",
		"datetime_end": datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc),
		"price_start": 456,
		"price_prompt": 789,
		"price_step_min": 111,
		"location": "anyware",
		"description": "something",
	}
	cursor_mock = create_cursor_mock()
	cursor_mock.fetchone.return_value = (42,)
	db_mock = mock.MagicMock()
	db_mock.cursor.side_effect = [cursor_mock]

	secret_token_hex_mock = mock.MagicMock()
	secret_token_hex_mock.return_value = "0123456789abcdef"
	monkeypatch.setattr(secrets, "token_hex", secret_token_hex_mock)

	secret_token_urlsafe_mock = mock.MagicMock()
	secret_token_urlsafe_mock.return_value = "AZaz09_-"
	monkeypatch.setattr(secrets, "token_urlsafe", secret_token_urlsafe_mock)

	with app.app_context():
		g.datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
		g.db = db_mock
		auction_id, password = logic.new_auction(auction)

	assert db_mock.cursor.mock_calls == [
		mock.call(),
	]

	assert cursor_mock.mock_calls == [
		mock.call.execute(
			"INSERT INTO t_auction (type, itemname, quantity, username, datetime_start, datetime_end, datetime_update, price_start, price_prompt, price_step_min, location, description) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
			("foo", 123, "bar", datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc), datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc), datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
			456,789,111, "anyware", "something")),
		mock.call.execute("SELECT LAST_INSERT_ID() FROM t_auction"),
		mock.call.fetchone(),
		mock.call.execute(
			"INSERT INTO t_auction_password (auction_id, password) VALUES (%s, %s)",
			(42, "pbkdf2_sha256$36000$AZaz09_-$A/eop0d997YvWCSWHt9JxKihD3A0EZiXdjXdL9VRvwU=")),
		mock.call.close(),
	]
	assert cursor_mock.execute.mock_calls[0][1][1][3].tzinfo == timezone.utc
	assert cursor_mock.execute.mock_calls[0][1][1][4].tzinfo == timezone.utc
	assert cursor_mock.execute.mock_calls[0][1][1][5].tzinfo == timezone.utc

	assert auction_id == 42
	assert password == "0123456789abcdef"


def test_get_auction_list_held():
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

	app = create_app({
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": False,
		"YAMI_PRICE_STEP_MIN": 100,
		"YAMI_PRICE_STEP_RULE": {
			1: 1
		}
	})

	cursor_mock1 = create_cursor_mock()
	cursor_mock1.fetchone.return_value = (123,)
	cursor_mock2 = create_cursor_mock()
	cursor_mock2.fetchall.return_value = [{
		# no bids
		"auction_id": 5,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime(2000, 2, 3),
		"price_current_high": None,
		"num_bids": None,
	}, {
		# no bids
		"auction_id": 3,
		"quantity": 3,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime(2000, 4, 5),
		"price_current_high": None,
		"num_bids": None,
	}, {
		# 0 < num_bids < quantity
		"auction_id": 6,
		"quantity": 3,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime(2000, 6, 7),
		"price_current_high": 345,
		"num_bids": 2,
	}, {
		# num_bids == quantity
		"auction_id": 1,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime(2000, 8, 9),
		"price_current_high": 456,
		"num_bids": 1,
	}, {
		# num_bids == quantity
		"auction_id": 2,
		"quantity": 3,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime(2000, 9, 1),
		"price_current_high": 567,
		"num_bids": 3,
	}, {
		# num_bids > quantity
		"auction_id": 4,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime(2000, 10, 2),
		"price_current_high": 678,
		"num_bids": 5,
	}, {
		# num_bids > quantity
		"auction_id": 7,
		"quantity": 5,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime(2000, 11, 3),
		"price_current_high": 789,
		"num_bids": 7,
	}]
	cursor_mock3 = create_cursor_mock()
	cursor_mock3.fetchone.return_value = (123,)
	cursor_mock4 = create_cursor_mock()
	cursor_mock4.fetchone.return_value = (234,)
	db_mock = mock.MagicMock()
	db_mock.cursor.side_effect = [cursor_mock1, cursor_mock2, cursor_mock3, cursor_mock4]

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = db_mock
		auctions, num_auctions = logic.get_auction_list(10, 20, False)

	assert db_mock.cursor.mock_calls == [
		mock.call(),
		mock.call(pymysql.cursors.DictCursor),
		mock.call(),
		mock.call(),
	]

	assert cursor_mock1.mock_calls == [
		mock.call.execute("SELECT COUNT(auction_id) FROM t_auction WHERE (ended = false AND datetime_end > %s)", (datetime_now,)),
		mock.call.fetchone(),
		mock.call.close(),
	]

	assert cursor_mock2.mock_calls == [
		mock.call.execute("SELECT * FROM t_auction LEFT JOIN (SELECT auction_id, MAX(price) as price_current_high, COUNT(price) as num_bids FROM t_bid GROUP BY auction_id) AS maxbid USING(auction_id) WHERE (ended = false AND datetime_end > %s) ORDER BY datetime_end ASC LIMIT %s OFFSET %s", (datetime_now, 10, 20)),
		mock.call.fetchall(),
		mock.call.close(),
	]

	assert cursor_mock3.mock_calls == [
		mock.call.execute("SELECT price FROM t_bid WHERE auction_id = %s ORDER BY price DESC LIMIT 1 OFFSET %s", (2, 2)),
		mock.call.fetchone(),
		mock.call.close(),
	]

	assert cursor_mock4.mock_calls == [
		mock.call.execute("SELECT price FROM t_bid WHERE auction_id = %s ORDER BY price DESC LIMIT 1 OFFSET %s", (7, 4)),
		mock.call.fetchone(),
		mock.call.close(),
	]

	assert num_auctions == 123
	assert auctions == [{
		"auction_id": 5,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime(2000, 2, 3, tzinfo=timezone.utc),
		"price_current_high": None,
		"price_current_low": None,
		"price_bid_min": 10,
		"num_bids": 0,
	}, {
		"auction_id": 3,
		"quantity": 3,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime(2000, 4, 5, tzinfo=timezone.utc),
		"price_current_high": None,
		"price_current_low": None,
		"price_bid_min": 10,
		"num_bids": 0,
	}, {
		"auction_id": 6,
		"quantity": 3,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime(2000, 6, 7, tzinfo=timezone.utc),
		"price_current_high": 345,
		"price_current_low": None,
		"price_bid_min": 10,
		"num_bids": 2,
	}, {
		"auction_id": 1,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime(2000, 8, 9, tzinfo=timezone.utc),
		"price_current_high": 456,
		"price_current_low": 456,
		"price_bid_min": 556,
		"num_bids": 1,
	}, {
		"auction_id": 2,
		"quantity": 3,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime(2000, 9, 1, tzinfo=timezone.utc),
		"price_current_high": 567,
		"price_current_low": 123,
		"price_bid_min": 223,
		"num_bids": 3,
	}, {
		"auction_id": 4,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime(2000, 10, 2, tzinfo=timezone.utc),
		"price_current_high": 678,
		"price_current_low": 678,
		"price_bid_min": 778,
		"num_bids": 5,
	}, {
		"auction_id": 7,
		"quantity": 5,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime(2000, 11, 3, tzinfo=timezone.utc),
		"price_current_high": 789,
		"price_current_low": 234,
		"price_bid_min": 334,
		"num_bids": 7,
	}]
	for auction in auctions:
		assert auction["datetime_end"].tzinfo == timezone.utc


def test_get_auction_list_ended():
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": False,
		"YAMI_PRICE_STEP_MIN": 100,
		"YAMI_PRICE_STEP_RULE": {
			1: 1
		}
	})

	cursor_mock1 = create_cursor_mock()
	cursor_mock1.fetchone.return_value = (123,)
	cursor_mock2 = create_cursor_mock()
	cursor_mock2.fetchall.return_value = [{
		# ended = true, datetime_end > now
		"auction_id": 2,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 1,
		"datetime_end": datetime_now_naive + timedelta(days=1),
		"price_current_high": None,
		"num_bids": None,
	}, {
		# ended = false, datetime_end = now
		"auction_id": 3,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime_now_naive,
		"price_current_high": None,
		"num_bids": None,
	}, {
		# ended = false, datetime_end < now
		"auction_id": 1,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime_now_naive - timedelta(days=1),
		"price_current_high": None,
		"num_bids": None,
	}]
	db_mock = mock.MagicMock()
	db_mock.cursor.side_effect = [cursor_mock1, cursor_mock2]

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = db_mock
		auctions, num_auctions = logic.get_auction_list(10, 20, False)

	assert db_mock.cursor.mock_calls == [
		mock.call(),
		mock.call(pymysql.cursors.DictCursor),
	]

	assert cursor_mock1.mock_calls == [
		mock.call.execute("SELECT COUNT(auction_id) FROM t_auction WHERE (ended = false AND datetime_end > %s)", (datetime_now,)),
		mock.call.fetchone(),
		mock.call.close(),
	]

	assert cursor_mock2.mock_calls == [
		mock.call.execute("SELECT * FROM t_auction LEFT JOIN (SELECT auction_id, MAX(price) as price_current_high, COUNT(price) as num_bids FROM t_bid GROUP BY auction_id) AS maxbid USING(auction_id) WHERE (ended = false AND datetime_end > %s) ORDER BY datetime_end ASC LIMIT %s OFFSET %s", (datetime_now, 10, 20)),
		mock.call.fetchall(),
		mock.call.close(),
	]

	assert num_auctions == 123
	assert auctions == [{
		"auction_id": 2,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": True,
		"datetime_end": datetime_now + timedelta(days=1),
		"price_current_high": None,
		"price_current_low": None,
		"price_bid_min": 10,
		"num_bids": 0,
	}, {
		"auction_id": 3,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": True,
		"datetime_end": datetime_now,
		"price_current_high": None,
		"price_current_low": None,
		"price_bid_min": 10,
		"num_bids": 0,
	}, {
		"auction_id": 1,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": True,
		"datetime_end": datetime_now - timedelta(days=1),
		"price_current_high": None,
		"price_current_low": None,
		"price_bid_min": 10,
		"num_bids": 0,
	}]
	for auction in auctions:
		assert auction["datetime_end"].tzinfo == timezone.utc


def test_get_auction_info_notfound():
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	#datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
	})

	cursor_mock1 = create_cursor_mock()
	cursor_mock1.fetchone.return_value = None
	db_mock = mock.MagicMock()
	db_mock.cursor.side_effect = [cursor_mock1]

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = db_mock
		auction, bids = logic.get_auction_info(42, False)

	assert db_mock.cursor.mock_calls == [
		mock.call(pymysql.cursors.DictCursor),
	]

	assert cursor_mock1.mock_calls == [
		mock.call.execute("SELECT * FROM t_auction WHERE auction_id = %s", (42,)),
		mock.call.fetchone(),
		mock.call.close(),
	]

	assert auction == None
	assert bids == None


@pytest.mark.parametrize("for_update", [(False,), (True,)])
def test_get_auction_info_query(for_update):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": False,
		"YAMI_PRICE_STEP_MIN": 100,
		"YAMI_PRICE_STEP_RULE": {
			1: 1
		}
	})

	cursor_mock1 = create_cursor_mock()
	cursor_mock1.fetchone.return_value = {
		"auction_id": 42,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime_now_naive + timedelta(days=1),
	}
	cursor_mock2 = create_cursor_mock()
	cursor_mock2.fetchall.return_value = [{
		"bid_id": 3,
		"price": 100,
	}, {
		"bid_id": 1,
		"price": 50,
	}]
	db_mock = mock.MagicMock()
	db_mock.cursor.side_effect = [cursor_mock1, cursor_mock2]

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = db_mock
		auction, bids = logic.get_auction_info(42, for_update)

	assert db_mock.cursor.mock_calls == [
		mock.call(pymysql.cursors.DictCursor),
		mock.call(pymysql.cursors.DictCursor),
	]

	if for_update:
		auction_select_decoration = " FOR UPDATE"
	else:
		auction_select_decoration = ""
	assert cursor_mock1.mock_calls == [
		mock.call.execute("SELECT * FROM t_auction WHERE auction_id = %s" + auction_select_decoration, (42,)),
		mock.call.fetchone(),
		mock.call.close(),
	]

	if for_update:
		bid_select_decoration = " LIMIT %s"
		bid_select_parameters = (42, 1)
	else:
		bid_select_decoration = ""
		bid_select_parameters = (42,)
	assert cursor_mock2.mock_calls == [
		mock.call.execute("SELECT * FROM t_bid WHERE auction_id = %s ORDER BY price DESC, datetime_bid ASC" + bid_select_decoration, bid_select_parameters),
		mock.call.fetchall(),
		mock.call.close(),
	]

	assert auction == {
		"auction_id": 42,
		"quantity": 1,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime_now + timedelta(days=1),
		"price_current_high": 100,
		"price_current_low": 100,
		"price_bid_min": 200,
	}
	assert bids == [{
		"bid_id": 3,
		"price": 100,
	}, {
		"bid_id": 1,
		"price": 50,
	}]


@pytest.mark.parametrize("num_bids", [0, 2, 3, 4])
def test_get_auction_info_price(num_bids):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": False,
		"YAMI_PRICE_STEP_MIN": 100,
		"YAMI_PRICE_STEP_RULE": {
			1: 1
		}
	})

	cursor_mock1 = create_cursor_mock()
	cursor_mock1.fetchone.return_value = {
		"auction_id": 42,
		"quantity": 3,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": 0,
		"datetime_end": datetime_now_naive + timedelta(days=1),
	}
	cursor_mock2 = create_cursor_mock()
	cursor_mock2.fetchall.return_value = [{
		"bid_id": i,
		"price": i * 100,
		"datetime_bid": datetime_now_naive - timedelta(hours=num_bids-i+1),
	} for i in range(num_bids, 0, -1)]
	db_mock = mock.MagicMock()
	db_mock.cursor.side_effect = [cursor_mock1, cursor_mock2]

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = db_mock
		auction, bids = logic.get_auction_info(42, False)

	assert db_mock.cursor.mock_calls == [
		mock.call(pymysql.cursors.DictCursor),
		mock.call(pymysql.cursors.DictCursor),
	]

	assert cursor_mock1.mock_calls == [
		mock.call.execute("SELECT * FROM t_auction WHERE auction_id = %s", (42,)),
		mock.call.fetchone(),
		mock.call.close(),
	]

	assert cursor_mock2.mock_calls == [
		mock.call.execute("SELECT * FROM t_bid WHERE auction_id = %s ORDER BY price DESC, datetime_bid ASC", (42,)),
		mock.call.fetchall(),
		mock.call.close(),
	]

	assert auction == {
		"auction_id": 42,
		"quantity": 3,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime_now + timedelta(days=1),
		"price_current_high": None if num_bids == 0 else num_bids * 100,
		"price_current_low": None if num_bids < 3 else (num_bids - 2) * 100,
		"price_bid_min": 10 if num_bids < 3 else (num_bids - 1) * 100,
	}
	assert bids == [{
		"bid_id": i,
		"price": i * 100,
		"datetime_bid": datetime_now - timedelta(hours=num_bids-i+1),
	} for i in range(num_bids, 0, -1)]
	for bid in bids:
		assert bid["datetime_bid"].tzinfo == timezone.utc


def test_bid_auction_notfound(monkeypatch):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	#datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
	})
	newbid = {
		"auction_id": 42,
	}

	get_auction_info_mock = mock.MagicMock()
	get_auction_info_mock.return_value = (None, None)
	monkeypatch.setattr(logic, "get_auction_info", get_auction_info_mock)

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = None
		result = logic.bid_auction(newbid)

	get_auction_info_mock.mock_calls == [
		mock.call(42, for_update=True),
	]

	assert result == logic.BidErrorCodes.BID_ERROR_NOT_FOUND


def test_bid_auction_ended(monkeypatch):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	#datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
	})
	newbid = {
		"auction_id": 42,
	}

	get_auction_info_mock = mock.MagicMock()
	get_auction_info_mock.return_value = ({
		"auction_id": 42,
		"quantity": 3,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": True,
		"datetime_end": datetime_now - timedelta(days=1),
	}, [{
		"bid_id": 3,
		"price": 100,
	}, {
		"bid_id": 1,
		"price": 50,
	}])
	monkeypatch.setattr(logic, "get_auction_info", get_auction_info_mock)

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = None
		result = logic.bid_auction(newbid)

	get_auction_info_mock.mock_calls == [
		mock.call(42, for_update=True),
	]

	assert result == logic.BidErrorCodes.BID_ERROR_ALREADY_ENDED


def test_bid_auction_another_one_bidded_first(monkeypatch):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	#datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
	})
	newbid = {
		"auction_id": 42,
		"price": 100,
	}

	get_auction_info_mock = mock.MagicMock()
	get_auction_info_mock.return_value = ({
		"auction_id": 42,
		"quantity": 3,
		"price_start": 10,
		"price_prompt": None,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime_now - timedelta(days=1),
		"price_bid_min": 200,
	}, [{
		"bid_id": 3,
		"price": 100,
	}, {
		"bid_id": 2,
		"price": 50,
	}, {
		"bid_id": 1,
		"price": 10,
	}])
	monkeypatch.setattr(logic, "get_auction_info", get_auction_info_mock)

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = None
		result = logic.bid_auction(newbid)

	get_auction_info_mock.mock_calls == [
		mock.call(42, for_update=True),
	]

	assert result == logic.BidErrorCodes.BID_ERROR_ANOTHER_ONE_BIDDED_FIRST


@pytest.mark.parametrize("quantity, enddelta, price_prompt, price_bidded, ended, extend", [
	(3, 86400, None, 250, False, False), # enddelta > YAMI_AUTO_EXTENSION
	(3, 86400,  300, 250, False, False), # price_prompt > newbid["price"]
	(3, 86400,  250, 250, False, False), # price_prompt == newbid["price"]
	(3, 86400,  220, 220, False, False), # price_prompt < newbid["price"]
	(3,   300, None, 250, False, False), # enddelta == YAMI_AUTO_EXTENSION
	(3,   100, None, 250, False, True ), # enddelta < YAMI_AUTO_EXTENSION
	(3,   100,  100, 100, False, True ),
	(2,   100,  100, 100, True , False),
])
def test_bid_auction_ok(quantity, enddelta, price_prompt, price_bidded, ended, extend, monkeypatch):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	#datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
		"YAMI_AUTO_EXTENSION": 300,
	})
	newbid = {
		"auction_id": 42,
		"price": 250,
		"username": "bidder",
	}

	get_auction_info_mock = mock.MagicMock()
	get_auction_info_mock.return_value = ({
		"auction_id": 42,
		"quantity": quantity,
		"price_start": 10,
		"price_prompt": price_prompt,
		"price_step_min": 100,
		"ended": False,
		"datetime_end": datetime_now + timedelta(seconds=enddelta),
		"price_bid_min": 200,
	}, [{
		"bid_id": 3,
		"price": 100,
	}, {
		"bid_id": 2,
		"price": 50,
	}, {
		"bid_id": 1,
		"price": 10,
	}])
	monkeypatch.setattr(logic, "get_auction_info", get_auction_info_mock)

	end_auction_mock = mock.MagicMock()
	monkeypatch.setattr(logic, "end_auction", end_auction_mock)

	cursor_mock1 = create_cursor_mock()
	cursor_mock1.fetchone.return_value = (4,)
	cursor_mock2 = create_cursor_mock()
	cursor_mock3 = create_cursor_mock()
	db_mock = mock.MagicMock()
	db_side_effect = [cursor_mock1, cursor_mock3]
	if extend:
		db_side_effect.insert(1, cursor_mock2)
	db_mock.cursor.side_effect = db_side_effect

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = db_mock
		result = logic.bid_auction(newbid)

	assert get_auction_info_mock.mock_calls == [
		mock.call(42, for_update=True),
	]

	assert end_auction_mock.mock_calls == ([
		mock.call({
			"auction_id": 42,
			"quantity": quantity,
			"price_start": 10,
			"price_prompt": price_prompt,
			"price_step_min": 100,
			"ended": True,
			"datetime_end": datetime_now + timedelta(seconds=enddelta),
			"price_bid_min": 200,
		})
	] if ended else [
	])

	assert db_mock.cursor.mock_calls == ([
		mock.call(),
		mock.call(),
		mock.call(),
	] if extend else [
		mock.call(),
		mock.call(),
	])

	assert cursor_mock1.mock_calls == [
		mock.call.execute("INSERT INTO t_bid (auction_id, username, price, datetime_bid) VALUES (%s, %s, %s, %s)", (42, "bidder", price_bidded, datetime_now)),
		mock.call.execute("SELECT LAST_INSERT_ID() FROM t_bid"),
		mock.call.fetchone(),
		mock.call.close(),
	]

	assert cursor_mock2.mock_calls == ([
		mock.call.execute("UPDATE t_auction SET datetime_end = %s WHERE auction_id = %s", (datetime_now + timedelta(seconds=300), 42)),
		mock.call.close(),
	] if extend else [])

	assert cursor_mock3.mock_calls == [
		mock.call.execute("UPDATE t_auction SET datetime_update = %s WHERE auction_id = %s", (datetime_now, 42)),
		mock.call.close(),
	]

	assert result == logic.BidErrorCodes.BID_OK
	assert newbid["bid_id"] == 4
	assert newbid["price"] == price_bidded
	assert newbid["datetime_bid"] == datetime_now


def test_check_expiration(monkeypatch):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	#datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
	})
	auctions = [{
		"auction_id": 1,
		"quantity": 2,
		"price_prompt": None,
		"ended": 0,
	}, {
		"auction_id": 2,
		"quantity": 2,
		"price_prompt": 100,
		"ended": 0,
	}]

	end_auction_mock = mock.MagicMock()
	monkeypatch.setattr(logic, "end_auction", end_auction_mock)

	cursor_mock1 = create_cursor_mock()
	cursor_mock1.fetchall.return_value = auctions
	cursor_mock2 = create_cursor_mock()
	cursor_mock2.fetchall.return_value = [{
		"bid_id": 1,
		"price": 100
	}, {
		"bid_id": 2,
		"price": 80
	}]
	cursor_mock3 = create_cursor_mock()
	cursor_mock4 = create_cursor_mock()
	cursor_mock4.fetchall.return_value = [{
		"bid_id": 1,
		"price": 100
	}, {
		"bid_id": 2,
		"price": 80
	}]
	cursor_mock5 = create_cursor_mock()
	db_mock = mock.MagicMock()
	db_mock.cursor.side_effect = [cursor_mock1, cursor_mock2, cursor_mock3, cursor_mock4, cursor_mock5]

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = db_mock
		logic.check_expiration()

	assert db_mock.cursor.mock_calls == [
		mock.call(pymysql.cursors.DictCursor),
		mock.call(pymysql.cursors.DictCursor),
		mock.call(),
		mock.call(pymysql.cursors.DictCursor),
		mock.call(),
	]

	assert cursor_mock1.mock_calls == [
		mock.call.execute("SELECT * FROM t_auction WHERE ended = false AND datetime_end <= %s FOR UPDATE", (datetime_now,)),
		mock.call.fetchall(),
		mock.call.close(),
	]

	assert cursor_mock2.mock_calls == [
		mock.call.execute("SELECT * FROM t_bid WHERE auction_id = %s ORDER BY price DESC, datetime_bid ASC LIMIT %s", (1, 2)),
		mock.call.fetchall(),
		mock.call.close(),
	]

	assert cursor_mock3.mock_calls == [
		mock.call.execute("UPDATE t_auction SET datetime_update = datetime_end WHERE auction_id = %s", (1,)),
		mock.call.close(),
	]

	assert cursor_mock4.mock_calls == [
		mock.call.execute("SELECT * FROM t_bid WHERE auction_id = %s ORDER BY price DESC, datetime_bid ASC LIMIT %s", (2, 2)),
		mock.call.fetchall(),
		mock.call.close(),
	]

	assert cursor_mock5.mock_calls == [
		mock.call.execute("UPDATE t_auction SET datetime_update = datetime_end WHERE auction_id = %s", (2,)),
		mock.call.close(),
	]

	assert end_auction_mock.mock_calls == [
		mock.call({
			"auction_id": 1,
			"quantity": 2,
			"price_prompt": None,
			"ended": True,
		}),
		mock.call({
			"auction_id": 2,
			"quantity": 2,
			"price_prompt": 100,
			"ended": True,
		}),
	]


def test_cancel_auction_notfound():
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	#datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
	})

	cursor_mock1 = create_cursor_mock()
	cursor_mock1.fetchone.return_value = None
	cursor_mock2 = create_cursor_mock()
	db_mock = mock.MagicMock()
	db_mock.cursor.side_effect = [cursor_mock1, cursor_mock2]

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = db_mock
		result = logic.cancel_auction(42, "password")

	assert result == logic.CancelErrorCodes.CANCEL_ERROR_NOT_FOUND

	assert db_mock.cursor.mock_calls == [
		mock.call(),
	]

	assert cursor_mock1.mock_calls == [
		mock.call.execute("SELECT password FROM t_auction_password WHERE auction_id = %s", (42,)),
		mock.call.fetchone(),
		mock.call.close(),
	]


def test_cancel_auction_badpassword():
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	#datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
	})

	cursor_mock1 = create_cursor_mock()
	cursor_mock1.fetchone.return_value = [""]
	cursor_mock2 = create_cursor_mock()
	db_mock = mock.MagicMock()
	db_mock.cursor.side_effect = [cursor_mock1, cursor_mock2]

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = db_mock
		result = logic.cancel_auction(42, "password")

	assert result == logic.CancelErrorCodes.CANCEL_ERROR_BAD_PASSWORD

	assert db_mock.cursor.mock_calls == [
		mock.call(),
	]

	assert cursor_mock1.mock_calls == [
		mock.call.execute("SELECT password FROM t_auction_password WHERE auction_id = %s", (42,)),
		mock.call.fetchone(),
		mock.call.close(),
	]


@pytest.mark.parametrize("isadmin", [
	(False),
	(True ),
])
def test_cancel_auction_ok(isadmin, monkeypatch):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	#datetime_now_naive = datetime_now.replace(tzinfo=None)

	app = create_app({
		"YAMI_ADMIN_PASSWORD": "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=" if isadmin else ""
	})

	get_auction_info_mock = mock.MagicMock()
	get_auction_info_mock.return_value = ({}, [])
	monkeypatch.setattr(logic, "get_auction_info", lambda auction_id, for_update: get_auction_info_mock(auction_id, for_update))

	cursor_mock1 = create_cursor_mock()
	cursor_mock1.fetchone.return_value = ["pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=" if not isadmin else ""]
	cursor_mock2 = create_cursor_mock()
	db_mock = mock.MagicMock()
	db_mock.cursor.side_effect = [cursor_mock1, cursor_mock2]

	with app.app_context():
		g.datetime_now = datetime_now
		g.db = db_mock
		result = logic.cancel_auction(42, "password")

	assert result == logic.CancelErrorCodes.CANCEL_OK

	assert db_mock.cursor.mock_calls == [
		mock.call(),
		mock.call(),
	]

	assert cursor_mock1.mock_calls == [
		mock.call.execute("SELECT password FROM t_auction_password WHERE auction_id = %s", (42,)),
		mock.call.fetchone(),
		mock.call.close(),
	]

	assert cursor_mock2.mock_calls == [
		mock.call.execute("UPDATE t_auction SET ended = 1, endtype = %s, datetime_update = %s WHERE auction_id = %s",
			(logic.EndType.ENDTYPE_CANCELED_BY_ADMIN if isadmin else logic.EndType.ENDTYPE_CANCELED_BY_SELLER, datetime_now, 42)),
		mock.call.close(),
	]
