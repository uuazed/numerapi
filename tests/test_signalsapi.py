import pytest
import datetime
import responses

import pandas as pd

import numerapi
from numerapi import base_api


@pytest.fixture(scope='function', name="api")
def api_fixture():
    return numerapi.SignalsAPI(verbosity='DEBUG')


def test_get_leaderboard(api):
    lb = api.get_leaderboard(1)
    assert len(lb) == 1


@responses.activate
def test_upload_predictions(api, tmpdir):
    api.token = ("", "")
    # we need to mock 3 network calls: 1. auth 2. file upload and 3. submission
    data = {"data": {"submissionUploadSignalsAuth":
            {"url": "https://uploadurl", "filename": "filename"}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    responses.add(responses.PUT, "https://uploadurl")
    data = {"data": {"createSignalsSubmission": {"id": "1234"}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)

    path = tmpdir.join("somefilepath")
    path.write("content")
    submission_id = api.upload_predictions(str(path))

    assert submission_id == "1234"
    assert len(responses.calls) == 3

#Test pandas.DataFrame version of upload_predictions
@responses.activate
def test_upload_predictions_df(api):
    api.token = ("", "")
    # we need to mock 3 network calls: 1. auth 2. file upload and 3. submission
    data = {"data": {"submissionUploadSignalsAuth":
            {"url": "https://uploadurl", "filename": "predictions.csv"}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    responses.add(responses.PUT, "https://uploadurl")
    data = {"data": {"createSignalsSubmission": {"id": "12345"}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)

    df = pd.DataFrame.from_dict({"bloomberg_ticker":[],"signal":[]})
    submission_id = api.upload_predictions(df = df)

    assert submission_id == "12345"
    assert len(responses.calls) == 3

@responses.activate
def test_daily_submissions_performances(api):
    perf = {'date': "20200516",
            'returns': 1.256,
            'submissionTime': "20200516"}
    data = {'data': {'signalsUserProfile':
            {'dailySubmissionPerformances': [perf]}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    result = api.daily_submissions_performances("uuazed")
    assert len(result) == 1
    assert isinstance(result[0]["date"], datetime.datetime)
    assert isinstance(result[0]["submissionTime"], datetime.datetime)


@responses.activate
def test_daily_user_performances(api):
    perf = {'rank': 12,
            'sharpe': 1.256,
            'date': "20200516"}
    data = {'data': {'signalsUserProfile':
            {'dailyUserPerformances': [perf]}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    result = api.daily_user_performances("uuazed")
    assert len(result) == 1
    assert isinstance(result[0]["date"], datetime.datetime)


@responses.activate
def test_ticker_universe(api):
    data = "bloomberg_ticker\nSTOCK A\nSTOCK B\nSTOCK C"
    responses.add(responses.GET,
                  api.TICKER_UNIVERSE_URL, body=data)
    result = api.ticker_universe()
    assert "bloomberg_ticker" not in result
    assert len(result) == 3
