import pytest
import datetime
from dateutil.tz import tzutc
from numerapi import utils


def test_parse_datetime_string():
    s = "2017-12-24T20:48:25.90349Z"
    t = datetime.datetime(2017, 12, 24, 20, 48, 25, 903490, tzinfo=tzutc())
    assert utils.parse_datetime_string(s) == t
    assert utils.parse_datetime_string(None) is None


def test_parse_float_string():
    assert utils.parse_float_string(None) is None
    assert utils.parse_float_string("") is None
    assert utils.parse_float_string("1.23") == 1.23
    assert utils.parse_float_string("12") == 12.0
    assert utils.parse_float_string("1,000.0") == 1000.0


def test_replace():
    d = None
    assert utils.replace(d, "a", float) is None
    # empty dict
    d = {}
    assert not utils.replace(d, "a", float)
    # normal case
    d = {"a": "1"}
    utils.replace(d, "a", float)
    assert d["a"] == 1.0
