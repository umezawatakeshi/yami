import pytest
from yami import create_app, logic
from datetime import datetime, timedelta, timezone
from flask import g
import testdb
from testdb import initdb


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


def test_new_auction(initdb):
	datetime_now = datetime(2000, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
	datetime_end = datetime(2000, 12, 11, 10, 9, 8, tzinfo=timezone.utc)

	app = create_app({
		"MYSQL_CONNECT_KWARGS": testdb.MYSQL_CONNECT_KWARGS,
	})

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id = logic.new_auction({
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
		"price_bid_min": 456,
		"price_current_high": None,
		"price_current_low": None,
	}
	expected_auction_in_list = expected_auction.copy()
	expected_auction_in_list["num_bids"] = 0

	assert auction_id == 1

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

	assert bid_result == logic.BID_ERROR_NOT_FOUND

	with app.app_context():
		g.datetime_now = datetime_now
		auction_id = logic.new_auction({
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

	assert bid_result == logic.BID_ERROR_ANOTHER_ONE_BIDDED_FIRST

	with app.app_context():
		g.datetime_now = datetime_end
		bid_result = logic.bid_auction({
			"auction_id": auction_id,
			"username": "hoge",
			"price": 1000,
		})
		logic.commit()

	assert bid_result == logic.BID_ERROR_ALREADY_ENDED


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
		auction_id = logic.new_auction({
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

	assert bid_result == logic.BID_OK

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

	assert bid_result == logic.BID_ERROR_ALREADY_ENDED


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
		auction_id = logic.new_auction({
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
		logic.commit()

	bid_results = []
	with app.app_context():
		for i in range(3):
			g.datetime_now = datetime_bid + timedelta(days=i+1)
			bid_results.append(logic.bid_auction({
				"auction_id": auction_id,
				"username": "hoge" + str(i),
				"price": 1000 * (i+1),
			}))
		auction, bids = logic.get_auction_info(auction_id, for_update=False)
		logic.commit()

	for i in range(3):
		assert bid_results[i] == logic.BID_OK

	assert not auction["ended"]
	assert auction["datetime_update"] == datetime_bid + timedelta(days=3)
	assert bids == [{
		"bid_id": 3,
		"auction_id": auction_id,
		"username": "hoge2",
		"price": 3000,
		"datetime_bid": datetime_bid + timedelta(days=3),
	},{
		"bid_id": 2,
		"auction_id": auction_id,
		"username": "hoge1",
		"price": 2000,
		"datetime_bid": datetime_bid + timedelta(days=2),
	},{
		"bid_id": 1,
		"auction_id": auction_id,
		"username": "hoge0",
		"price": 1000,
		"datetime_bid": datetime_bid + timedelta(days=1),
	}]


def test_bid_auction_extension(initdb):
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
		auction_id = logic.new_auction({
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
		logic.commit()

	with app.app_context():
		g.datetime_now = datetime_end - timedelta(minutes=30)
		logic.bid_auction({
			"auction_id": auction_id,
			"username": "hoge",
			"price": 1000,
		})
		auction, _ = logic.get_auction_info(auction_id, for_update=False)
		logic.commit()

	assert auction["datetime_end"] == datetime_end - timedelta(minutes=30) + timedelta(seconds=yami_auto_extension)