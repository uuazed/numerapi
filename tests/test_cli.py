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


@patch('numerapi.NumerAPI.list_datasets')
def test_list_datasets_default(mocked):
    result = CliRunner().invoke(cli.list_datasets)
    assert result.exit_code == 0
    mocked.assert_called_once_with(round_num=None)


@patch('numerapi.SignalsAPI.list_datasets')
def test_list_datasets_signals(mocked):
    result = CliRunner().invoke(cli.list_datasets, ['--tournament', '11'])
    assert result.exit_code == 0
    mocked.assert_called_once_with(round_num=None)


@patch('numerapi.NumerAPI.download_dataset')
def test_download_dataset(mocked):
    result = CliRunner().invoke(cli.download_dataset)
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_leaderboard')
def test_leaderboard(mocked):
    result = CliRunner().invoke(cli.leaderboard)
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_competitions')
def test_competitions(mocked):
    result = CliRunner().invoke(cli.competitions, ['--tournament', '1'])
    # just testing if calling works fine
    assert result.exit_code == 0


def test_competitions_not_supported_for_signals():
    result = CliRunner().invoke(cli.competitions, ['--tournament', '11'])
    assert result.exit_code != 0
    assert "not available" in result.output


@patch('numerapi.NumerAPI.get_current_round')
def test_current_round(mocked):
    result = CliRunner().invoke(cli.current_round, ['--tournament', '1'])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_submission_filenames')
def test_submission_filenames(mocked):
    result = CliRunner().invoke(
        cli.submission_filenames, ['--tournament', '1'])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.check_new_round')
def test_check_new_round(mocked):
    result = CliRunner().invoke(cli.check_new_round)
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


@patch('numerapi.NumerAPI.wallet_transactions')
def test_transactions(mocked):
    result = CliRunner().invoke(cli.transactions)
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.upload_predictions')
def test_submit(mocked, login, tmpdir):
    path = tmpdir.join("somefilepath")
    path.write("content")
    result = CliRunner().invoke(
        cli.submit,
        [str(path), '--model_id', '31a42870-38b6-4435-ad49-18b987ff4148'])
    assert result.exit_code == 0
    mocked.assert_called_once()
    args, kwargs = mocked.call_args
    assert args[0] == str(path)
    assert kwargs['model_id'] == '31a42870-38b6-4435-ad49-18b987ff4148'


def test_version():
    result = CliRunner().invoke(cli.version)
    # just testing if calling works fine
    assert result.exit_code == 0
