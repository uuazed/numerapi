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
    # invalid log level should raise
    with pytest.raises(AttributeError):
        numerapi.NumerAPI(verbosity="FOO")


def test__login(api):
    # passing only one of public_id and secret_key is not enough
    api._login(public_id="foo", secret_key=None)
    assert api.token is None
    api._login(public_id=None, secret_key="bar")
    assert api.token is None
    # passing both works
    api._login(public_id="foo", secret_key="bar")
    assert api.token == ("foo", "bar")

    # using env variables
    os.environ["NUMERAI_SECRET_KEY"] = "key"
    os.environ["NUMERAI_PUBLIC_ID"] = "id"
    api._login()
    assert api.token == ("id", "key")

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


def test_get_current_round(api):
    current_round = api.get_current_round()
    assert current_round >= 82


def test_raw_query(api):
    query = "query {dataset(tournament:8)}"
    result = api.raw_query(query)
    assert isinstance(result, dict)
    assert "data" in result


def test_v1_get_leaderboard(api):
    lb = api.get_v1_leaderboard(67, tournament=1)
    assert len(lb) == 1425


@pytest.mark.parametrize("fun", ["get_user", "get_account", "get_stakes", "get_transactions",
                                 "get_payments"])
def test_unauthorized_requests(api, fun):
    with pytest.raises(ValueError) as err:
        # while this won't work because we are not authorized, it still tells
        # us if the remaining code works
        getattr(api, fun)()
    # error should warn about not beeing logged in.
    assert "API keys required for this action" in str(err.value) or \
           "Your session is invalid or has expired." in str(err.value)

@responses.activate
def test_get_account(api):
    api.token = ("", "")
    account = {'apiTokens': [{'name': 'uploads',
                              'public_id': 'AAA',
                              'scopes': ['upload_submission']},
                             {'name': '_internal_default',
                              'public_id': 'BBB',
                              'scopes': ['upload_submission',
                                         'read_submission_info',
                                         'read_user_info']},
                             {'name': 'all',
                              'public_id': 'CCC',
                              'scopes': ['upload_submission',
                                         'stake',
                                         'read_submission_info',
                                         'read_user_info']}],
               'availableNmr': '1.010000000000000000',
               'email': 'no-reply@eu83t4nncmxv3g2.xyz',
               'id': '0c10a70a-a851-478f-a289-7a05fe397008',
               'insertedAt': "2018-01-01 11:11:11",
               'mfaEnabled': False,
               'models': [{'id': '881778ad-2ee9-4fb0-82b4-7b7c0f7ce17d',
                           'name': 'model1',
                           'submissions': [{'filename': 'predictions-pPbLKSHGiR.csv',
                                            'id': 'f2369b69-8c43-47aa-b4de-de3a9de5f52c'}],
                           'v2Stake': {'status': None, 'txHash': None}},
                          {'id': '881778ad-2ee9-4fb0-82b4-7b7c0f7ce17d',
                           'name': 'model2',
                           'submissions': [{'filename': 'predictions-pPbPOWQNGiR.csv',
                                            'id': '46a62500-87c7-4d7c-98ad-b743037e8cfd'}],
                           'v2Stake': {'status': None, 'txHash': None}}],
               'status': 'VERIFIED',
               'username': 'username1',
               'walletAddress': '0x0000000000000000000000000000'}

    data = {'data': {'account': account}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)
    res = api.get_account()
    assert isinstance(res, dict)
    assert len(res.get('models')) == 2


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
             "tournamentId": 1,
             "soc": "0.4",
             "insertedAt": "2018-01-01 11:11:11",
             "staker": "-",
             "status": "-",
             "value": "0.4"}
    data = {'data': {'model': {'stakeTxs': [stake]}}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)
    stakes = api.get_stakes()
    assert len(stakes) == 1
    assert stakes[0]["confidence"] == decimal.Decimal("0.4")
    assert isinstance(stakes[0]["insertedAt"], datetime.datetime)

@responses.activate
def test_get_models(api):
    api.token = ("", "")
    models_list = [dict(name="model_x", id="95b0d9e2-c901-4f2b-9c98-24138b0bd706"),
                   dict(name="model_y", id="2c6d63a4-013f-42d1-bbaf-bf35725d29f7")]
    data = {'data': {'account': {'models': models_list}}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)
    models = api.get_models()
    assert sorted(models.keys()) == ['model_x', 'model_y']
    assert sorted(models.values()) == ['2c6d63a4-013f-42d1-bbaf-bf35725d29f7',
                                       '95b0d9e2-c901-4f2b-9c98-24138b0bd706']

@responses.activate
def test_get_account_transactions(api):
    api.token = ("", "")
    nmr = {"from": "-",
           "posted": "2018-01-01 11:11:11",
           "status": "-",
           "to": "-",
           "txHash": "-",
           "value": "0.4"}
    data = {'data': {'account': {'nmrDeposits': [nmr], 'nmrWithdrawals': [nmr]}}}
    responses.add(responses.POST, numerapi.numerapi.API_TOURNAMENT_URL,
                  json=data)
    txs = api.get_account_transactions()
    for txtype in ['nmrDeposits', 'nmrWithdrawals']:
        assert len(txs[txtype]) == 1
        assert txs[txtype][0]["value"] == decimal.Decimal("0.4")

@responses.activate
def test_get_transactions(api):
    api.token = ("", "")
    nmr = {"from": "-",
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
