import pytest
from yami import create_app, logic
import tzlocal
import pytz
from datetime import datetime, timedelta, timezone


def test_aware_utc_datetime():
	src = {
		"foo":                "bar",
		"datetimefoo":        datetime(2000, 1, 1),
		"datetime_foo":       datetime(2000, 2, 1),
		"datetime_foo_local": datetime(2000, 3, 1),
		"datetime_foolocal":  datetime(2000, 4, 1),
	}
	expected = {
		"foo":                "bar",
		"datetimefoo":        datetime(2000, 1, 1),
		"datetime_foo":       datetime(2000, 2, 1, tzinfo=timezone.utc),
		"datetime_foo_local": datetime(2000, 3, 1, tzinfo=timezone.utc),
		"datetime_foolocal":  datetime(2000, 4, 1, tzinfo=timezone.utc),
	}

	logic.aware_utc_datetime(src)
	assert src == expected
	for k in ("datetime_foo", "datetime_foo_local", "datetime_foolocal"):
		assert src[k].tzinfo == timezone.utc


def test_append_localtime(monkeypatch):
	local_tz = pytz.timezone("Asia/Tokyo")
	monkeypatch.setattr(tzlocal, "get_localzone", lambda: local_tz)

	expected_tz = timezone(timedelta(hours=9))

	src = {
		"foo":                     "bar",
		"datetimefoo":             datetime(2000, 1, 1, 0, tzinfo=timezone.utc),
		"datetime_foo":            datetime(2000, 2, 1, 0, tzinfo=timezone.utc),
		"datetime_foolocal":       datetime(2000, 4, 1, 0, tzinfo=timezone.utc),
	}
	expected = {
		"foo":                     "bar",
		"datetimefoo":             datetime(2000, 1, 1, 0, tzinfo=timezone.utc),
		"datetime_foo":            datetime(2000, 2, 1, 0, tzinfo=timezone.utc),
		"datetime_foo_local":      datetime(2000, 2, 1, 9, tzinfo=expected_tz),
		"datetime_foolocal":       datetime(2000, 4, 1, 0, tzinfo=timezone.utc),
		"datetime_foolocal_local": datetime(2000, 4, 1, 9, tzinfo=expected_tz),
	}

	logic.append_localtime(src)
	assert src == expected
	for k in ("datetimefoo", "datetime_foo", "datetime_foolocal"):
		assert src[k].tzinfo == timezone.utc
	for k in ("datetime_foo_local", "datetime_foolocal_local"):
		assert src[k].utcoffset() == timedelta(hours=9)


def test_append_localtime_overwrite(monkeypatch):
	local_tz = pytz.timezone("Asia/Tokyo")
	monkeypatch.setattr(tzlocal, "get_localzone", lambda: local_tz)

	expected_tz = timezone(timedelta(hours=9))

	src = {
		"foo":                     "bar",
		"datetimefoo":             datetime(2000, 1, 1, 0, tzinfo=timezone.utc),
		"datetime_foo":            datetime(2000, 2, 1, 0, tzinfo=timezone.utc),
		"datetime_foo_local":      "bar",
		"datetime_foolocal":       datetime(2000, 4, 1, 0, tzinfo=timezone.utc),
		"datetime_foolocal_local": "bar",
	}
	expected = {
		"foo": "bar",
		"datetimefoo":             datetime(2000, 1, 1, 0, tzinfo=timezone.utc),
		"datetime_foo":            datetime(2000, 2, 1, 0, tzinfo=timezone.utc),
		"datetime_foo_local":      datetime(2000, 2, 1, 9, tzinfo=expected_tz),
		"datetime_foolocal":       datetime(2000, 4, 1, 0, tzinfo=timezone.utc),
		"datetime_foolocal_local": datetime(2000, 4, 1, 9, tzinfo=expected_tz),
	}

	logic.append_localtime(src)
	assert src == expected
	for k in ("datetimefoo", "datetime_foo", "datetime_foolocal"):
		assert src[k].tzinfo == timezone.utc
	for k in ("datetime_foo_local", "datetime_foolocal_local"):
		assert src[k].utcoffset() == timedelta(hours=9)
