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
    """
    Return an api object.

    Args:
    """
    api = numerapi.NumerAPI(verbosity='DEBUG')
    return api


def test_get_competitions(api):
    """
    Returns a list of competitions

    Args:
        api: (todo): write your description
    """
    res = api.get_competitions(tournament=1)
    assert isinstance(res, list)
    assert len(res) > 80


def test_download_current_dataset(api, tmpdir):
    """
    Downloads the current dataset.

    Args:
        api: (todo): write your description
        tmpdir: (str): write your description
    """
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


def test_get_current_round(api):
    """
    Get the current round of the current round.

    Args:
        api: (todo): write your description
    """
    current_round = api.get_current_round()
    assert current_round >= 82


def test_v1_get_leaderboard(api):
    """
    Retrieve the leaderboard.

    Args:
        api: (todo): write your description
    """
    lb = api.get_v1_leaderboard(67, tournament=1)
    assert len(lb) == 1425


@pytest.mark.parametrize("fun", ["get_user", "get_account", "get_stakes",
                                 "get_transactions", "get_payments"])
def test_unauthorized_requests(api, fun):
    """
    Test if the api is logged in a request.

    Args:
        api: (todo): write your description
        fun: (callable): write your description
    """
    with pytest.raises(ValueError) as err:
        # while this won't work because we are not authorized, it still tells
        # us if the remaining code works
        getattr(api, fun)()
    # error should warn about not beeing logged in.
    assert "API keys required for this action" in str(err.value) or \
           "Your session is invalid or has expired." in str(err.value)


def test_get_submission_ids(api):
    """
    Get submission submission ids.

    Args:
        api: (todo): write your description
    """
    ids = api.get_submission_ids()
    assert len(ids) > 0
    assert isinstance(ids, dict)


def test_error_handling(api):
    """
    Test if api is_error.

    Args:
        api: (todo): write your description
    """
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
    """
    Upload prediction prediction prediction.

    Args:
        api: (todo): write your description
        tmpdir: (str): write your description
    """
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
    """
    Gets test information about an api.

    Args:
        api: (todo): write your description
    """
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
    """
    Test to make a new api.

    Args:
        api: (todo): write your description
    """
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
