import pytest
import datetime
from dateutil.tz import tzutc
from numerapi import utils


def test_parse_datetime_string():
    s = "2017-12-24T20:48:25.90349Z"
    t = datetime.datetime(2017, 12, 24, 20, 48, 25, 903499, tzinfo=tzutc())
    assert utils.parse_datetime_string(s) == t
    assert utils.parse_datetime_string(None) is None
