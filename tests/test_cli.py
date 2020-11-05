import os
import pytest
from click.testing import CliRunner
from unittest.mock import patch

from numerapi import cli


@pytest.fixture(scope='function', name="login")
def login():
    """
    A context manager.

    Args:
    """
    os.environ["NUMERAI_PUBLIC_ID"] = "foo"
    os.environ["NUMERAI_SECRET_KEY"] = "bar"
    yield None
    # teardown
    del os.environ["NUMERAI_PUBLIC_ID"]
    del os.environ["NUMERAI_SECRET_KEY"]


@patch('numerapi.NumerAPI.download_current_dataset')
def test_download_dataset(mocked):
    """
    Download the test dataset.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.download_dataset)
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_dataset_url')
def test_dataset_url(mocked):
    """
    Test if dataset exists.

    Args:
        mocked: (str): write your description
    """
    result = CliRunner().invoke(cli.dataset_url, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_leaderboard')
def test_leaderboard(mocked):
    """
    Test the leaderboard.

    Args:
        mocked: (bool): write your description
    """
    result = CliRunner().invoke(cli.leaderboard, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_competitions')
def test_competitions(mocked):
    """
    Test if test test sets.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.competitions, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_current_round')
def test_current_round(mocked):
    """
    Round the current test.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.current_round, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_submission_ids')
def test_submission_ids(mocked):
    """
    Test if submission ids.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.submission_ids, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_leaderboard')
def test_leaderboard(mocked):
    """
    Test the leaderboard.

    Args:
        mocked: (bool): write your description
    """
    result = CliRunner().invoke(cli.leaderboard)
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_user_activities')
def test_user_activities(mocked, login):
    """
    Lists user activities.

    Args:
        mocked: (todo): write your description
        login: (todo): write your description
    """
    result = CliRunner().invoke(cli.user_activities, 'username')
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_submission_filenames')
def test_submission_filenames(mocked):
    """
    Test for submission submission.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.submission_filenames, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.check_new_round')
def test_check_new_round(mocked):
    """
    Check if a new test.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.check_new_round, ['--tournament', 1])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_account')
def test_account(mocked, login):
    """
    Test if a login.

    Args:
        mocked: (todo): write your description
        login: (todo): write your description
    """
    result = CliRunner().invoke(cli.account)
    # just testing if calling works fine
    assert result.exit_code == 0

@patch('numerapi.NumerAPI.get_models')
def test_models(mocked, login):
    """
    Test if the given models exist.

    Args:
        mocked: (todo): write your description
        login: (todo): write your description
    """
    result = CliRunner().invoke(cli.models)
    # just testing if calling works fine
    assert result.exit_code == 0

@patch('numerapi.NumerAPI.get_user')
def test_user(mocked, login):
    """
    Test if the login.

    Args:
        mocked: (todo): write your description
        login: (todo): write your description
    """
    result = CliRunner().invoke(cli.user)
    # just testing if calling works fine
    assert result.exit_code == 0

@patch('numerapi.NumerAPI.get_user')
def test_user_with_model_id(mocked, login):
    """
    Executes test test test to test.

    Args:
        mocked: (bool): write your description
        login: (todo): write your description
    """
    result = CliRunner().invoke(cli.user, ['--model_id', '31a42870-38b6-4435-ad49-18b987ff4148'])
    # just testing if calling works fine
    assert result.exit_code == 0

@patch('numerapi.NumerAPI.get_payments')
def test_payments(mocked, login):
    """
    Test for test test payload.

    Args:
        mocked: (todo): write your description
        login: (todo): write your description
    """
    result = CliRunner().invoke(cli.payments,
                                ['--model_id', '31a42870-38b6-4435-ad49-18b987ff4148'])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.submission_status')
def test_submission_status(mocked, login):
    """
    Test the status of a submission.

    Args:
        mocked: (todo): write your description
        login: (todo): write your description
    """
    result = CliRunner().invoke(cli.submission_status, ['subm_id'])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_transactions')
def test_transactions(mocked):
    """
    Executes a transaction.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.transactions,
                                ['--model_id', '31a42870-38b6-4435-ad49-18b987ff4148'])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_stakes')
def test_stakes(mocked):
    """
    Run test test test.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.stakes, ['--model_id', '31a42870-38b6-4435-ad49-18b987ff4148'])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.get_tournaments')
def test_tournaments(mocked):
    """
    Run a command line.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.tournaments)
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.tournament_number2name')
def test_tournament_number2name(mocked):
    """
    Test if a tournament number.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.tournament_number2name, ["1"])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.tournament_name2number')
def test_tournament_name2number(mocked):
    """
    Test if a tournament number.

    Args:
        mocked: (todo): write your description
    """
    result = CliRunner().invoke(cli.tournament_name2number, ["frank"])
    # just testing if calling works fine
    assert result.exit_code == 0


@patch('numerapi.NumerAPI.upload_predictions')
def test_submit(mocked, login, tmpdir):
    """
    Submit a test test.

    Args:
        mocked: (todo): write your description
        login: (todo): write your description
        tmpdir: (str): write your description
    """
    path = tmpdir.join("somefilepath")
    path.write("content")
    result = CliRunner().invoke(cli.submit,
                                [str(path), '--model_id', '31a42870-38b6-4435-ad49-18b987ff4148'])
    # just testing if calling works fine
    assert result.exit_code == 0


def test_version():
    """
    Run the test test.

    Args:
    """
    result = CliRunner().invoke(cli.version)
    # just testing if calling works fine
    assert result.exit_code == 0
