import pytest
from yami import create_app, logic


@pytest.mark.parametrize("config_price_step_min, auction_price_step_min, result", [
	(   0,    0,    0),
	(1000,    0, 1000),
	(   0, 1000, 1000),
	(1000, 1000, 1000),
])
def test_calc_price_step_min_when_zero_price(config_price_step_min, auction_price_step_min, result):
	app = create_app({
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": False,
		"YAMI_PRICE_STEP_MIN": config_price_step_min,
		"YAMI_PRICE_STEP_RULE": {
			1: "0.2",
			2: "0.4",
			4: "1",
		},
	})
	auction = {
		"price_step_min": auction_price_step_min,
		"price_start": 0,
		"price_current_low": 0,
	}
	with app.app_context():
		assert logic.calc_price_step_min(auction) == result


@pytest.mark.parametrize("price_start, result", [
	(     0,  1000),
	(  1000,  1000),
	(  9999,  1000),
	( 10000,  2000),
	( 19999,  2000),
	( 20000,  4000),
	( 39999,  4000),
	( 40000, 10000),
	( 99999, 10000),
	(100000, 20000),
])
def test_calc_price_step_min_from_start_price(price_start, result):
	app = create_app({
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": False,
		"YAMI_PRICE_STEP_MIN": 1000,
		"YAMI_PRICE_STEP_RULE": {
			1: "0.2",
			2: "0.4",
			4: "1",
		},
	})
	auction = {
		"price_step_min": 1000,
		"price_start": price_start,
	}
	with app.app_context():
		auction["price_current_low"]  = None
		assert logic.calc_price_step_min(auction) == result
		auction["price_current_low"] = 0
		assert logic.calc_price_step_min(auction) == result
		auction["price_current_low"] = 100000
		assert logic.calc_price_step_min(auction) == result


@pytest.mark.parametrize("price_current_low, result", [
	(     0,  1000),
	(  1000,  1000),
	(  9999,  1000),
	( 10000,  2000),
	( 19999,  2000),
	( 20000,  4000),
	( 39999,  4000),
	( 40000, 10000),
	( 99999, 10000),
	(100000, 20000),
])
def test_calc_price_step_min_from_current_price(price_current_low, result):
	app = create_app({
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": True,
		"YAMI_PRICE_STEP_MIN": 1000,
		"YAMI_PRICE_STEP_RULE": {
			1: "0.2",
			2: "0.4",
			4: "1",
		},
	})
	auction = {
		"price_step_min": 1000,
		"price_current_low": price_current_low,
	}
	with app.app_context():
		auction["price_start"] = 0
		assert logic.calc_price_step_min(auction) == result
		auction["price_start"] = 100000
		assert logic.calc_price_step_min(auction) == result


@pytest.mark.parametrize("price_start, price_prompt, price_current_low, result", [
	(    0,  None,  None,     0),
	(    0,  None,     0,  1000),
	(  500,  None,  None,   500),
	(  500,  None,   500,  1500),
	(  500,  2000,   500,  1500),
	(  500,  1200,   500,  1200),
	(10000,  None, 10000, 12000),
])
def test_set_price_bid_min(price_start, price_prompt, price_current_low, result):
	app = create_app({
		"YAMI_PRICE_STEP_FROM_CURRENT_PRICE": True,
		"YAMI_PRICE_STEP_MIN": 1000,
		"YAMI_PRICE_STEP_RULE": {
			1: "0.2",
			2: "0.4",
			4: "1",
		},
	})
	auction = {
		"price_step_min": 1000,
		"price_start": price_start,
		"price_prompt": price_prompt,
		"price_current_low": price_current_low,
	}
	with app.app_context():
		logic.set_price_bid_min(auction)
		assert auction["price_bid_min"] == result
