import pytest
from yami import create_app, logic
from datetime import datetime, timedelta, timezone
from flask import g
import testdb
from testdb import initdb
from unittest import mock
import secrets


def test_get_auction_info_notfound(initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
	})

	with app.app_context():
		g.datetime_now = datetime_now
		auction, bids = logic.get_auction_info(42, for_update=False)
		auctions, num_auctions = logic.get_auction_list(10, 0, False)

	assert auction is None
	assert bids is None
	assert len(auctions) == 0
	assert num_auctions == 0


def test_new_auction(initdb, monkeypatch):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)

	secret_token_hex_mock = mock.MagicMock()
	secret_token_hex_mock.return_value = "0123456789abcdef"
	monkeypatch.setattr(secrets, "token_hex", secret_token_hex_mock)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
	})

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id, password = logic.new_auction({
			"itemname": "foo",
			"quantity": 123,
			"username": "bar",
			"datetime_end": datetime_end,
			"price_start": 456,
			"price_prompt": 789,
			"price_step_min": 111,
			"location": "anyware",
			"description": "something",
		})
		auction, bids = logic.get_auction_info(auction_id, for_update=False)
		held_auctions, num_held_auctions = logic.get_auction_list(10, 0, False)
		out_of_page_held_auctions, num_held_auctions_2 = logic.get_auction_list(10, 10, False)
		ended_auctions, num_ended_auctions = logic.get_auction_list(10, 0, True)
		logic.commit()

	expected_auction = {
		"auction_id": 1,
		"type": 1,
		"itemname": "foo",
		"quantity": 123,
		"username": "bar",
		"datetime_start": datetime_now,
		"datetime_end": datetime_end,
		"datetime_update": datetime_now,
		"price_start": 456,
		"price_prompt": 789,
		"price_step_min": 111,
		"location": "anyware",
		"description": "something",
		"ended": False,
		"endtype": 0,
		"price_bid_min": 456,
		"price_current_high": None,
		"price_current_low": None,
	}
	expected_auction_in_list = expected_auction.copy()
	expected_auction_in_list["num_bids"] = 0

	assert auction_id == 1
	assert password == "0123456789abcdef"

	assert auction == expected_auction
	assert len(bids) == 0

	assert held_auctions == [expected_auction_in_list]
	assert num_held_auctions == 1
	assert len(out_of_page_held_auctions) == 0
	assert num_held_auctions_2 == 1
	assert len(ended_auctions) == 0
	assert num_ended_auctions == 0

	with app.app_context():
		g.datetime_now = datetime_end
		auction, bids = logic.get_auction_info(auction_id, for_update=False)
		held_auctions, num_held_auctions = logic.get_auction_list(10, 0, False)
		ended_auctions, num_ended_auctions = logic.get_auction_list(10, 0, True)
		logic.commit()

	expected_auction["ended"] = True
	expected_auction_in_list["ended"] = True

	assert auction == expected_auction
	assert len(bids) == 0

	assert len(held_auctions) == 0
	assert num_held_auctions == 0
	assert ended_auctions == [expected_auction_in_list]
	assert num_ended_auctions == 1


def test_bid_auction_error(initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
	})

	with app.app_context():
		g.datetime_now = datetime_now
		bid_result = logic.bid_auction({
			"auction_id": 1,
			"username": "hoge",
			"price": 100,
		})
		logic.commit()

	assert bid_result == logic.BidErrorCodes.BID_ERROR_NOT_FOUND

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id, _ = logic.new_auction({
			"itemname": "foo",
			"quantity": 123,
			"username": "bar",
			"datetime_end": datetime_end,
			"price_start": 456,
			"price_prompt": 789,
			"price_step_min": 111,
			"location": "anyware",
			"description": "something",
		})
		logic.commit()

	with app.app_context():
		g.datetime_now = datetime_now
		bid_result = logic.bid_auction({
			"auction_id": auction_id,
			"username": "hoge",
			"price": 100,
		})
		logic.commit()

	assert bid_result == logic.BidErrorCodes.BID_ERROR_ANOTHER_ONE_BIDDED_FIRST

	with app.app_context():
		g.datetime_now = datetime_end
		bid_result = logic.bid_auction({
			"auction_id": auction_id,
			"username": "hoge",
			"price": 1000,
		})
		logic.commit()

	assert bid_result == logic.BidErrorCodes.BID_ERROR_ALREADY_ENDED


def test_bid_auction_prompt(initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)
	datetime_bid = datetime(2000, 6, 7, 8, 9, 10, tzinfo=timezone.utc)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
		"YAMI_PRICE_STEP_MIN": 111,
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": True,
		"YAMI_PRICE_STEP_RULE": {
			1: 1,
		}
	})

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id, _ = logic.new_auction({
			"itemname": "foo",
			"quantity": 1,
			"username": "bar",
			"datetime_end": datetime_end,
			"price_start": 456,
			"price_prompt": 789,
			"price_step_min": 111,
			"location": "anyware",
			"description": "something",
		})
		logic.commit()

	with app.app_context():
		g.datetime_now = datetime_bid
		bid_result = logic.bid_auction({
			"auction_id": auction_id,
			"username": "hoge",
			"price": 789,
		})
		auction, bids = logic.get_auction_info(auction_id, for_update=False)
		logic.commit()

	assert bid_result == logic.BidErrorCodes.BID_OK

	assert auction["ended"]
	assert auction["datetime_update"] == datetime_bid
	assert bids == [{
		"bid_id": 1,
		"auction_id": auction_id,
		"username": "hoge",
		"price": 789,
		"datetime_bid": datetime_bid,
	}]

	with app.app_context():
		g.datetime_now = datetime_bid
		bid_result = logic.bid_auction({
			"auction_id": auction_id,
			"username": "hoge",
			"price": 1000,
		})
		logic.commit()

	assert bid_result == logic.BidErrorCodes.BID_ERROR_ALREADY_ENDED


def test_bid_auction_manytimes(initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)
	datetime_bid = datetime(2000, 6, 7, 8, 9, 10, tzinfo=timezone.utc)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
		"YAMI_PRICE_STEP_MIN": 111,
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": True,
		"YAMI_PRICE_STEP_RULE": {
			1: 1,
		},
		"YAMI_AUTO_EXTENSION": 0,
	})

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id, _ = logic.new_auction({
			"itemname": "foo",
			"quantity": 2,
			"username": "bar",
			"datetime_end": datetime_end,
			"price_start": 456,
			"price_prompt": None,
			"price_step_min": 111,
			"location": "anyware",
			"description": "something",
		})
		logic.commit()

	bid_results = []
	with app.app_context():
		for i in range(5):
			g.datetime_now = datetime_bid + timedelta(days=i+1)
			bid_results.append(logic.bid_auction({
				"auction_id": auction_id,
				"username": "hoge" + str(i),
				"price": 1000 * (i+1),
			}))
		auction, bids = logic.get_auction_info(auction_id, for_update=False)
		auctions, _ = logic.get_auction_list(1, 0, False)
		logic.commit()

	for i in range(5):
		assert bid_results[i] == logic.BidErrorCodes.BID_OK

	assert not auction["ended"]
	assert auction["datetime_update"] == datetime_bid + timedelta(days=5)
	assert auction["price_current_low"] == 4000
	assert auctions[0]["price_current_low"] == 4000
	for i in range(5):
		assert bids[i] == {
			"bid_id": 5-i,
			"auction_id": auction_id,
			"username": "hoge" + str(4-i),
			"price": 1000 * (5-i),
			"datetime_bid": datetime_bid + timedelta(days=5-i),
		}


def test_bid_auction_dupprice(initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)
	datetime_bid = datetime(2000, 6, 7, 8, 9, 10, tzinfo=timezone.utc)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
		"YAMI_PRICE_STEP_MIN": 111,
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": True,
		"YAMI_PRICE_STEP_RULE": {
			1: 1,
		},
		"YAMI_AUTO_EXTENSION": 0,
	})

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id, _ = logic.new_auction({
			"itemname": "foo",
			"quantity": 2,
			"username": "bar",
			"datetime_end": datetime_end,
			"price_start": 456,
			"price_prompt": None,
			"price_step_min": 111,
			"location": "anyware",
			"description": "something",
		})
		logic.commit()

	bid_results = []
	with app.app_context():
		g.datetime_now = datetime_bid + timedelta(days=1)
		bid_results.append(logic.bid_auction({
			"auction_id": auction_id,
			"username": "hoge0",
			"price": 1000,
		}))
		g.datetime_now = datetime_bid + timedelta(days=2)
		bid_results.append(logic.bid_auction({
			"auction_id": auction_id,
			"username": "hoge1",
			"price": 1000,
		}))
		bid_results.append(logic.bid_auction({
			"auction_id": auction_id,
			"username": "hoge2",
			"price": 2000,
		}))
		auction, bids = logic.get_auction_info(auction_id, for_update=False)
		logic.commit()

	for i in range(3):
		assert bid_results[i] == logic.BidErrorCodes.BID_OK

	assert auction["price_current_low"] == 1000
	assert bids == [{
		"bid_id": 3,
		"auction_id": auction_id,
		"username": "hoge2",
		"price": 2000,
		"datetime_bid": datetime_bid + timedelta(days=2),
	},{
		"bid_id": 1,
		"auction_id": auction_id,
		"username": "hoge0",
		"price": 1000,
		"datetime_bid": datetime_bid + timedelta(days=1),
	},{
		"bid_id": 2,
		"auction_id": auction_id,
		"username": "hoge1",
		"price": 1000,
		"datetime_bid": datetime_bid + timedelta(days=2),
	}]


@pytest.mark.parametrize("quantity, prompt, extended", [
	(1, False, True ),
	(1, True,  False),
	(2, False, True ),
	(2, True,  True ),
])
def test_bid_auction_extension(quantity, prompt, extended, initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)
	yami_auto_extension = 3600

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
		"YAMI_PRICE_STEP_MIN": 111,
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": True,
		"YAMI_PRICE_STEP_RULE": {
			1: 1,
		},
		"YAMI_AUTO_EXTENSION": yami_auto_extension,
	})

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id, _ = logic.new_auction({
			"itemname": "foo",
			"quantity": quantity,
			"username": "bar",
			"datetime_end": datetime_end,
			"price_start": 456,
			"price_prompt": 1000,
			"price_step_min": 111,
			"location": "anyware",
			"description": "something",
		})
		logic.commit()

	with app.app_context():
		g.datetime_now = datetime_end - timedelta(minutes=30)
		logic.bid_auction({
			"auction_id": auction_id,
			"username": "hoge",
			"price": 1000 if prompt else 500,
		})
		auction, _ = logic.get_auction_info(auction_id, for_update=False)
		logic.commit()

	assert auction["datetime_end"] == datetime_end + (-timedelta(minutes=30) + timedelta(seconds=yami_auto_extension) if extended else timedelta())


def test_cancel_auction_notfound(initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
	})

	with app.app_context():
		g.datetime_now = datetime_now
		result = logic.cancel_auction(42, "")
		logic.commit()

	assert result == logic.CancelErrorCodes.CANCEL_ERROR_NOT_FOUND


def test_cancel_auction_badpassword(initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
	})

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id, _ = logic.new_auction({
			"itemname": "foo",
			"quantity": 1,
			"username": "bar",
			"datetime_end": datetime_end,
			"price_start": 456,
			"price_prompt": None,
			"price_step_min": 111,
			"location": "anyware",
			"description": "something",
		})

		g.datetime_now = datetime_now + timedelta(minutes=30)
		result = logic.cancel_auction(auction_id, "")

	assert result == logic.CancelErrorCodes.CANCEL_ERROR_BAD_PASSWORD


def test_cancel_auction_seller(initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
	})

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id, password = logic.new_auction({
			"itemname": "foo",
			"quantity": 1,
			"username": "bar",
			"datetime_end": datetime_end,
			"price_start": 456,
			"price_prompt": None,
			"price_step_min": 111,
			"location": "anyware",
			"description": "something",
		})

		g.datetime_now = datetime_now + timedelta(minutes=30)
		result = logic.cancel_auction(auction_id, password)
		auction, _ = logic.get_auction_info(auction_id, for_update=False)
		logic.commit()

	assert result == logic.CancelErrorCodes.CANCEL_OK
	assert auction["ended"] == 1
	assert auction["endtype"] == logic.EndType.ENDTYPE_CANCELED_BY_SELLER
	assert auction["datetime_update"] == datetime_now + timedelta(minutes=30)


def test_cancel_auction_admin(initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
		"YAMI_ADMIN_PASSWORD": "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU="
	})

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id, _ = logic.new_auction({
			"itemname": "foo",
			"quantity": 1,
			"username": "bar",
			"datetime_end": datetime_end,
			"price_start": 456,
			"price_prompt": None,
			"price_step_min": 111,
			"location": "anyware",
			"description": "something",
		})

		g.datetime_now = datetime_now + timedelta(minutes=30)
		result = logic.cancel_auction(auction_id, "password")
		auction, _ = logic.get_auction_info(auction_id, for_update=False)
		logic.commit()

	assert result == logic.CancelErrorCodes.CANCEL_OK
	assert auction["ended"] == 1
	assert auction["endtype"] == logic.EndType.ENDTYPE_CANCELED_BY_ADMIN
	assert auction["datetime_update"] == datetime_now + timedelta(minutes=30)
