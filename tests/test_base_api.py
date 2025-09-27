import os
import pytest
import responses

from numerapi import base_api


@pytest.fixture(scope='function', name="api")
def api_fixture():
    api = base_api.Api(verbosity='DEBUG')
    return api


def test_NumerAPI():
    # invalid log level should raise
    with pytest.raises(AttributeError):
        base_api.Api(verbosity="FOO")


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


def test_raw_query(api):
    query = "query {latestNmrPrice {priceUsd}}"
    result = api.raw_query(query)
    assert isinstance(result, dict)
    assert "data" in result


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
                           'submissions':
                            [{'filename': 'predictions-pPbLKSHGiR.csv',
                              'id': 'f2369b69-8c43-47aa-b4de-de3a9de5f52c'}],
                           'v2Stake': {'status': None, 'txHash': None}},
                          {'id': '881778ad-2ee9-4fb0-82b4-7b7c0f7ce17d',
                           'name': 'model2',
                           'submissions':
                           [{'filename': 'predictions-pPbPOWQNGiR.csv',
                             'id': '46a62500-87c7-4d7c-98ad-b743037e8cfd'}],
                           'v2Stake': {'status': None, 'txHash': None}}],
               'status': 'VERIFIED',
               'username': 'username1',
               'walletAddress': '0x0000000000000000000000000000'}

    data = {'data': {'account': account}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    res = api.get_account()
    assert isinstance(res, dict)
    assert len(res.get('models')) == 2


@responses.activate
def test_get_models(api):
    api.token = ("", "")
    models_list = [
        {"name": "model_x", "id": "95b0d9e2-c901-4f2b-9c98-24138b0bd706",
         "tournament": 0},
        {"name": "model_y", "id": "2c6d63a4-013f-42d1-bbaf-bf35725d29f7",
         "tournament": 0}]
    data = {'data': {'account': {'models': models_list}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    models = api.get_models()
    assert sorted(models.keys()) == ['model_x', 'model_y']
    assert sorted(models.values()) == ['2c6d63a4-013f-42d1-bbaf-bf35725d29f7',
                                       '95b0d9e2-c901-4f2b-9c98-24138b0bd706']


@responses.activate
def test_set_submission_webhook(api):
    api.token = ("", "")
    data = {
      "data": {
        "setSubmissionWebhook": "true"
      }
    }
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    res = api.set_submission_webhook(
        '2c6d63a4-013f-42d1-bbaf-bf35725d29f7',
        'https://triggerurl'
    )
    assert res
