import pytest
from yami import create_app, logic


@pytest.mark.parametrize("password, salt, iterations, result", [
	("password",    "salt",         100000, "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU="),
	("my_password", "ASrxdtCsw3E6",  36000, "pbkdf2_sha256$36000$ASrxdtCsw3E6$u1k+CFO1y2TpbgClMQFiVITT6pUIP+H9Ss8sDrfK+iU="),
	("my_password", "ASrxdtCsw3E6",   None, "pbkdf2_sha256$36000$ASrxdtCsw3E6$u1k+CFO1y2TpbgClMQFiVITT6pUIP+H9Ss8sDrfK+iU="),
])
def test_encode_password(password, salt, iterations, result):
	assert logic.encode_password(password, salt, iterations) == result


@pytest.mark.parametrize("password, encoded_password, result", [
	("password",    "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",        True ),
	("passwor",     "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",        False),
	("password",    "pbkdf2_sha256$100001$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",        False),
	("password",    "pbkdf2_sha256$100000$sugar$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",       False),
	("password",    "pbkdf2_sha512$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",        False),
	("my_password", "pbkdf2_sha256$36000$ASrxdtCsw3E6$u1k+CFO1y2TpbgClMQFiVITT6pUIP+H9Ss8sDrfK+iU=", True ),
	("password",    "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=$x",      False),
	("password",    "pbkdf2_sha256$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",               False),
])
def test_check_password(password, encoded_password, result):
	assert logic.check_password(password, encoded_password) == result


@pytest.mark.parametrize("password, encoded_password, admin_password, result", [
	("password",    "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=", None, (True,  False)),
	("passwor",     "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=", None, (False, False)),
	("password",    "pbkdf2_sha256$100001$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",
	                "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",       (True,  True)),
	("password",    "pbkdf2_sha256$100001$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",
	                "pbkdf2_sha256$100002$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",       (False, False)),
	("password",    "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",
	                "pbkdf2_sha256$100002$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU=",       (True,  False)),
])
def test_check_auction_admin(password, encoded_password, admin_password, result):
	if admin_password is None:
		app = create_app({})
	else:
		app = create_app({"YAMI_ADMIN_PASSWORD": admin_password})

	with app.app_context():
		assert logic.check_auction_admin(password, encoded_password) == result
