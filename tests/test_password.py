import pytest
from yami import logic


@pytest.mark.parametrize("password, salt, iterations, result", [
	("password",    "salt",         100000, "pbkdf2_sha256$100000$salt$A5Si7eMyyaE+uC6bJGMWBMMd+Xi04vD70sVJlE+deaU="),
	("my_password", "ASrxdtCsw3E6",  36000, "pbkdf2_sha256$36000$ASrxdtCsw3E6$u1k+CFO1y2TpbgClMQFiVITT6pUIP+H9Ss8sDrfK+iU="),
	("my_password", "ASrxdtCsw3E6",   None, "pbkdf2_sha256$36000$ASrxdtCsw3E6$u1k+CFO1y2TpbgClMQFiVITT6pUIP+H9Ss8sDrfK+iU="),
])
def test_encode_password(password, salt, iterations, result):
	assert logic.encode_password(password, salt, iterations) == result
