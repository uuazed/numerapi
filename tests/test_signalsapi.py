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
    Returns an api call.

    Args:
    """
    api = numerapi.SignalsAPI(verbosity='DEBUG')
    return api


def test_get_leaderboard(api):
    """
    Retrieve the leaderboard.

    Args:
        api: (todo): write your description
    """
    lb = api.get_leaderboard(1)
    assert len(lb) == 1


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


@responses.activate
def test_daily_submissions_performances(api):
    """
    Perform submissions for submissions.

    Args:
        api: (todo): write your description
    """
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
    """
    Perform user details.

    Args:
        api: (todo): write your description
    """
    perf = {'rank': 12,
            'sharpe': 1.256,
            'date': "20200516"}
    data = {'data': {'signalsUserProfile':
            {'dailyUserPerformances': [perf]}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    result = api.daily_user_performances("uuazed")
    assert len(result) == 1
    assert isinstance(result[0]["date"], datetime.datetime)
