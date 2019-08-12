import pytest
from yami import create_app, logic
import tzlocal
from datetime import datetime, timedelta, timezone


def test_aware_utc_datetime():
	src = {
		"foo":                "bar",
		"datetimefoo":        datetime(1900, 1, 1),
		"datetime_foo":       datetime(1900, 2, 1),
		"datetime_foo_local": datetime(1900, 3, 1),
		"datetime_foolocal":  datetime(1900, 4, 1),
	}
	expected = {
		"foo":                "bar",
		"datetimefoo":        datetime(1900, 1, 1),
		"datetime_foo":       datetime(1900, 2, 1, tzinfo=timezone.utc),
		"datetime_foo_local": datetime(1900, 3, 1, tzinfo=timezone.utc),
		"datetime_foolocal":  datetime(1900, 4, 1, tzinfo=timezone.utc),
	}

	logic.aware_utc_datetime(src)
	assert src == expected


def test_append_localtime(monkeypatch):
	tz = timezone(timedelta(hours=1))
	monkeypatch.setattr(tzlocal, "get_localzone", lambda: tz)

	src = {
		"foo":                     "bar",
		"datetimefoo":             datetime(1900, 1, 1, 0, tzinfo=timezone.utc),
		"datetime_foo":            datetime(1900, 2, 1, 0, tzinfo=timezone.utc),
		"datetime_foolocal":       datetime(1900, 4, 1, 0, tzinfo=timezone.utc),
	}
	expected = {
		"foo":                     "bar",
		"datetimefoo":             datetime(1900, 1, 1, 0, tzinfo=timezone.utc),
		"datetime_foo":            datetime(1900, 2, 1, 0, tzinfo=timezone.utc),
		"datetime_foo_local":      datetime(1900, 2, 1, 1, tzinfo=tz),
		"datetime_foolocal":       datetime(1900, 4, 1, 0, tzinfo=timezone.utc),
		"datetime_foolocal_local": datetime(1900, 4, 1, 1, tzinfo=tz),
	}

	logic.append_localtime(src)
	assert src == expected


def test_append_localtime_overwrite(monkeypatch):
	tz = timezone(timedelta(hours=1))
	monkeypatch.setattr(tzlocal, "get_localzone", lambda: tz)

	src = {
		"foo":                     "bar",
		"datetimefoo":             datetime(1900, 1, 1, 0, tzinfo=timezone.utc),
		"datetime_foo":            datetime(1900, 2, 1, 0, tzinfo=timezone.utc),
		"datetime_foo_local":      "bar",
		"datetime_foolocal":       datetime(1900, 4, 1, 0, tzinfo=timezone.utc),
		"datetime_foolocal_local": "bar",
	}
	expected = {
		"foo": "bar",
		"datetimefoo":             datetime(1900, 1, 1, 0, tzinfo=timezone.utc),
		"datetime_foo":            datetime(1900, 2, 1, 0, tzinfo=timezone.utc),
		"datetime_foo_local":      datetime(1900, 2, 1, 1, tzinfo=tz),
		"datetime_foolocal":       datetime(1900, 4, 1, 0, tzinfo=timezone.utc),
		"datetime_foolocal_local": datetime(1900, 4, 1, 1, tzinfo=tz),
	}

	logic.append_localtime(src)
	assert src == expected
