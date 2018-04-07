import pytest
import os
import datetime
import decimal
import pytz
import responses

import numerapi


@pytest.fixture(scope='function', name="api")
def api_fixture():
    api = numerapi.NumerAPI(verbosity='DEBUG')
    return api


def test_NumerAPI():
    # passing only one of public_id and secret_key is not enough
    api = numerapi.NumerAPI(public_id="foo", secret_key=None)
    assert api.token is None
    api = numerapi.NumerAPI(public_id=None, secret_key="bar")
    assert api.token is None
    # passing both works
    api = numerapi.NumerAPI(public_id="foo", secret_key="bar")
    assert api.token == ("foo", "bar")

    # invalid log level should raise
    with pytest.raises(AttributeError):
        numerapi.NumerAPI(verbosity="FOO")


def test_get_competitions(api):
    res = api.get_competitions()
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
        # us if the remaining code works
        api.stake(3, 2)
    # error should warn about not beeing logged in.
    assert "API keys required for this action" in str(err.value)


@pytest.mark.parametrize("fun", ["get_user", "get_stakes", "get_transactions",
                                 "get_payments"])
def test_unauthorized_requests(api, fun):
    with pytest.raises(ValueError) as err:
        # while this won't work because we are not authorized, it still tells
        # us if the remaining code works
        getattr(api, fun)()
    # error should warn about not beeing logged in.
    assert "API keys required for this action" in str(err.value)


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


@responses.activate
def test_upload_predictions(api, tmpdir):
    api.token = ("", "")
    # we need to mock 3 network calls: 1. auth 2. file upload and 3. submission
    data = {"data": {"submission_upload_auth": {"url": "https://uploadurl",
                                                "filename": "filename"}}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)
    responses.add(responses.PUT, "https://uploadurl")
    data = {"data": {"create_submission": {"id": "1234"}}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)

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
             "soc": "0.4",
             "insertedAt": "2018-01-01 11:11:11",
             "staker": "-",
             "status": "-",
             "value": "0.4"}
    data = {'data': {'user': {'stakeTxs': [stake]}}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)
    stakes = api.get_stakes()
    assert len(stakes) == 1
    assert stakes[0]["confidence"] == decimal.Decimal("0.4")
    assert isinstance(stakes[0]["insertedAt"], datetime.datetime)


@responses.activate
def test_get_transactions(api):
    api.token = ("", "")
    nmr = {"from": "-",
           "id": "-",
           "posted": "2018-01-01 11:11:11",
           "status": "-",
           "to": "-",
           "txHash": "-",
           "value": "0.4"}
    usd = {"ethAmount": "0.4",
           "confirmTime": "2018-01-01 11:11:11",
           "from": "-",
           "posted": "2018-01-01 11:11:11",
           "sendTime": "2018-01-01 11:11:11",
           "status": "-",
           "to": "-",
           "txHash": "",
           "usdAmount": "0.4"}
    data = {'data': {'user': {'nmrDeposits': [nmr],
                              'nmrWithdrawals': [nmr],
                              'usdWithdrawals': [usd]}}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)
    txs = api.get_transactions()
    for txtype in ['nmrDeposits', 'nmrWithdrawals']:
        assert len(txs[txtype]) == 1
        assert txs[txtype][0]["value"] == decimal.Decimal("0.4")
    assert len(txs['usdWithdrawals']) == 1
    assert txs['usdWithdrawals'][0]['usdAmount'] == decimal.Decimal("0.4")


@responses.activate
def test_check_new_round(api):
    open_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    data = {"data": {"rounds": [{"openTime": open_time.isoformat()}]}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)

    open_time = datetime.datetime(2000, 1, 1).replace(tzinfo=pytz.utc)
    data = {"data": {"rounds": [{"openTime": open_time.isoformat()}]}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)

    # first example
    assert api.check_new_round()
    # second
    assert not api.check_new_round()


@responses.activate
@pytest.mark.parametrize('''originality_pending, originality_value,
    concordance_pending, concordance_value, consistency, expected''', [
    (True, None, False, True, 80, True),
    (False, False, False, True, 80, True),
    (False, True, True, None, 80, False),
    (False, True, False, False, 80, False),
    (False, True, False, True, 50, False),
    (False, True, False, True, 58, True)])
def test_check_submission_successful(api, originality_pending,
                                     originality_value, concordance_pending,
                                     concordance_value, consistency,
                                     expected):
    api.token = ("", "")
    data = {"data": {"submissions": [
      {"originality":
          {"pending": originality_pending, "value": originality_value},
       "concordance":
          {"pending": concordance_pending, "value": concordance_value},
       "consistency": consistency
       }
    ]}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)
    assert api.check_submission_successful(submission_id="") == expected
