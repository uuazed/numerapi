import pytest
import os

from numerapi.numerapi import NumerAPI


def test_get_competitions():
    api = NumerAPI()

    # get all competions
    res = api.get_competitions()
    assert isinstance(res, list)
    assert len(res) > 80

    # get one competion
    res = api.get_competitions(67)
    assert isinstance(res, list)
    assert len(res) == 1


def test_download_current_dataset():
    api = NumerAPI()
    path = api.download_current_dataset(unzip=True)
    assert os.path.exists(path)

    directory = path.replace(".zip", "")
    filename = "numerai_tournament_data.csv"
    assert os.path.exists(os.path.join(directory, filename))


def test_get_current_round():
    api = NumerAPI()
    current_round = api.get_current_round()
    assert current_round >= 82


def test_get_leaderboard():
    api = NumerAPI()
    lb = api.get_leaderboard(67)
    assert len(lb) == 1425
