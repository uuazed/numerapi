import pytest
import os
import datetime
import pytz
import json
import requests_mock

from numerapi.numerapi import NumerAPI
import numerapi


@pytest.fixture(scope='function', name="api")
def api_fixture():
    api = NumerAPI(verbosity='DEBUG')
    return api


def test_get_competitions(api):
    res = api.get_competitions()
    assert isinstance(res, list)
    assert len(res) > 80


def test_download_current_dataset(api):
    path = api.download_current_dataset(unzip=True)
    assert os.path.exists(path)

    directory = path.replace(".zip", "")
    filename = "numerai_tournament_data.csv"
    assert os.path.exists(os.path.join(directory, filename))


def test_get_current_round(api):
    current_round = api.get_current_round()
    assert current_round >= 82


def test_raw_query(api):
    query = "query {dataset}"
    result = api.raw_query(query)
    assert isinstance(result, dict)
    assert "data" in result


def test_get_leaderboard(api):
    lb = api.get_leaderboard(67)
    assert len(lb) == 1425


def test_stake(api):
    with pytest.raises(ValueError) as err:
        # while this won't work because we are not authorized, it still tells
        # us if the request is formatted correctly
        api.stake(3, 2)
    # error should warn about not beeing logged in.
    assert "You must be authenticated" in str(err.value)


def test_get_staking_leaderboard(api):
    stakes = api.get_staking_leaderboard(82)
    # 115 people staked that round
    assert len(stakes) == 115


def test_get_submission_ids(api):
    ids = api.get_submission_ids()
    assert len(ids) > 0
    assert isinstance(ids, dict)


def test_error_handling(api):
    # String instead of Int
    with pytest.raises(ValueError):
        api.get_leaderboard("foo")
    # round that doesn't exist
    with pytest.raises(ValueError):
        api.get_leaderboard(-1)
    # unauthendicated request
    with pytest.raises(ValueError):
        # set wrong token
        api.token = ("foo", "bar")
        api.submission_id = 1
        api.submission_status()


def test_check_new_round(api):
    with requests_mock.mock() as m:
        open_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        data = {"data": {"rounds": [{"openTime": open_time.isoformat()}]}}
        m.post(numerapi.numerapi.API_TOURNAMENT_URL, text=json.dumps(data))
        assert api.check_new_round()

        open_time = datetime.datetime(2000, 1, 1).replace(tzinfo=pytz.utc)
        data = {"data": {"rounds": [{"openTime": open_time.isoformat()}]}}
        m.post(numerapi.numerapi.API_TOURNAMENT_URL, text=json.dumps(data))
        assert not api.check_new_round()
