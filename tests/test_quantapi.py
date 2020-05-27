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
    api = numerapi.QuantAPI(verbosity='DEBUG')
    return api


def test_get_leaderboard(api):
    lb = api.get_leaderboard(1)
    assert len(lb) == 1


@responses.activate
def test_upload_predictions(api, tmpdir):
    api.token = ("", "")
    # we need to mock 3 network calls: 1. auth 2. file upload and 3. submission
    data = {"data": {"submission_upload_quant_auth":
            {"url": "https://uploadurl", "filename": "filename"}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)
    responses.add(responses.PUT, "https://uploadurl")
    data = {"data": {"create_quant_submission": {"id": "1234"}}}
    responses.add(responses.POST, base_api.API_TOURNAMENT_URL, json=data)

    path = tmpdir.join("somefilepath")
    path.write("content")
    submission_id = api.upload_predictions(str(path))
    assert submission_id == "1234"
    assert len(responses.calls) == 3
