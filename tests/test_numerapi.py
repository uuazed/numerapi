import pytest
import os
import datetime
import decimal
import pytz
import responses

import numerapi
from numerapi import base_api


@pytest.fixture(scope='function', name="api")
def api_fixture():
    api = numerapi.NumerAPI(verbosity='DEBUG')
    return api


def test_get_competitions(api):
    res = api.get_competitions(tournament=1)
    assert isinstance(res, list)
    assert len(res) > 80


def test_download_current_dataset(api, tmpdir):
    path = api.download_current_dataset(dest_path=str(tmpdir), unzip=True)
    assert os.path.exists(path)

    directory = path.replace(".zip", "")
    filename = "numerai_tournament_data.csv"
    assert os.path.exists(os.path.join(directory, filename))

    # calling again shouldn't download again
    with responses.RequestsMock() as rsps:
        api.download_current_dataset(dest_path=str(tmpdir),
                                     dest_filename=os.path.basename(path))
        assert len(rsps.calls) == 0


def test_get_latest_data_url(api):
    # List of data types that have latest data files
    data_types = [
        "live",
        "training",
        "validation",
        "test",
        "max_test_era",
        "tournament",
        "tournament_ids",
        "example_predictions",
    ]

    extensions = ["csv", "csv.xz", "parquet"]

    # Test each combination of function and extension
    for data_type in data_types:
        with pytest.raises(ValueError):
            url = api.get_latest_data_url(data_type, extension='.txt')

        for extension in extensions:
            expected_url = f"{api.PUBLIC_DATASETS_URL}/latest_numerai_{data_type}_data.{extension}"

            url = api.get_latest_data_url(data_type, extension)
            assert url == expected_url

            url = api.get_latest_data_url(data_type, f'.{extension}')
            assert url == expected_url


def test_get_current_round(api):
    current_round = api.get_current_round()
    assert current_round >= 82


def test_v1_get_leaderboard(api):
    lb = api.get_v1_leaderboard(67, tournament=1)
    assert len(lb) == 1425


@pytest.mark.parametrize("fun", ["get_user", "get_account", "get_stakes",
                                 "get_transactions", "get_payments"])
def test_unauthorized_requests(api, fun):
    with pytest.raises(ValueError) as err:
        # while this won't work because we are not authorized, it still tells
        # us if the remaining code works
        getattr(api, fun)()
    # error should warn about not beeing logged in.
    assert "API keys required for this action" in str(err.value) or \
           "Your session is invalid or has expired." in str(err.value)


def test_get_submission_ids(api):
    ids = api.get_submission_ids()
    assert len(ids) > 0
    assert isinstance(ids, dict)


def test_error_handling(api):
    # String instead of Int
    with pytest.raises(ValueError):
        api.get_v1_leaderboard("foo")
    # round that doesn't exist
    with pytest.raises(ValueError):
        api.get_v1_leaderboard(-1)
    # unauthendicated request
    with pytest.raises(ValueError):
        # set wrong token
        api.token = ("foo", "bar")
        api.submission_status()


@responses.activate
def test_upload_predictions(api, tmpdir):
    api.token = ("", "")
    # we need to mock 3 network calls: 1. auth 2. file upload and 3. submission
    data = {"data": {"submission_upload_auth": {"url": "https://uploadurl",
                                                "filename": "filename"}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    responses.add(responses.PUT, "https://uploadurl")
    data = {"data": {"create_submission": {"id": "1234"}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)

    path = tmpdir.join("somefilepath")
    path.write("content")
    submission_id = api.upload_predictions(str(path))
    assert submission_id == "1234"
    assert len(responses.calls) == 3


@responses.activate
def test_get_stakes(api):
    api.token = ("", "")
    stake = {"confidence": "0.4",
             "roundNumber": 99,
             "tournamentId": 1,
             "soc": "0.4",
             "insertedAt": "2018-01-01 11:11:11",
             "staker": "-",
             "status": "-",
             "value": "0.4"}
    data = {'data': {'model': {'stakeTxs': [stake]}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    stakes = api.get_stakes()
    assert len(stakes) == 1
    assert stakes[0]["confidence"] == decimal.Decimal("0.4")
    assert isinstance(stakes[0]["insertedAt"], datetime.datetime)


@responses.activate
def test_check_new_round(api):
    open_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    data = {"data": {"rounds": [{"openTime": open_time.isoformat()}]}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)

    open_time = datetime.datetime(2000, 1, 1).replace(tzinfo=pytz.utc)
    data = {"data": {"rounds": [{"openTime": open_time.isoformat()}]}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)

    # first example
    assert api.check_new_round()
    # second
    assert not api.check_new_round()
