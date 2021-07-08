import os
import pytest
from click.testing import CliRunner
from unittest.mock import patch

from numerapi import cli


@pytest.fixture(scope='function', name="login")
def login():
    os.environ["NUMERAI_PUBLIC_ID"] = "foo"
    os.environ["NUMERAI_SECRET_KEY"] = "bar"
    yield None
    # teardown
    del os.environ["NUMERAI_PUBLIC_ID"]
    del os.environ["NUMERAI_SECRET_KEY"]


@patch('numerapi.NumerAPI.download_current_dataset')
def test_download_dataset(mocked):
    result = CliRunner().invoke(cli.download_dataset)
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_dataset_url')
def test_dataset_url(mocked):
    result = CliRunner().invoke(cli.dataset_url, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_leaderboard')
def test_leaderboard(mocked):
    result = CliRunner().invoke(cli.leaderboard)
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_competitions')
def test_competitions(mocked):
    result = CliRunner().invoke(cli.competitions, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_current_round')
def test_current_round(mocked):
    result = CliRunner().invoke(cli.current_round, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_submission_filenames')
def test_submission_filenames(mocked):
    result = CliRunner().invoke(cli.submission_filenames, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.check_new_round')
def test_check_new_round(mocked):
    result = CliRunner().invoke(cli.check_new_round, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_account')
def test_account(mocked, login):
    result = CliRunner().invoke(cli.account)
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_models')
def test_models(mocked, login):
    result = CliRunner().invoke(cli.models)
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_user')
def test_user(mocked, login):
    result = CliRunner().invoke(cli.user)
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_user')
def test_user_with_model_id(mocked, login):
    result = CliRunner().invoke(
        cli.user, ['--model_id', '31a42870-38b6-4435-ad49-18b987ff4148'])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.submission_status')
def test_submission_status(mocked, login):
    result = CliRunner().invoke(cli.submission_status, ['subm_id'])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_transactions')
def test_transactions(mocked):
    result = CliRunner().invoke(
        cli.transactions,
        ['--model_id', '31a42870-38b6-4435-ad49-18b987ff4148'])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.upload_predictions')
def test_submit(mocked, login, tmpdir):
    path = tmpdir.join("somefilepath")
    path.write("content")
    result = CliRunner().invoke(
        cli.submit,
        [str(path), '--model_id', '31a42870-38b6-4435-ad49-18b987ff4148'])
    # just testing if calling works fine
    assert result.exit_code == 0


def test_version():
    result = CliRunner().invoke(cli.version)
    # just testing if calling works fine
    assert result.exit_code == 0
