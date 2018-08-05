[![Build Status](https://travis-ci.org/uuazed/numerapi.png)](https://travis-ci.org/uuazed/numerapi)
[![codecov](https://codecov.io/gh/uuazed/numerapi/branch/master/graph/badge.svg)](https://codecov.io/gh/uuazed/numerapi)
[![PyPI](https://img.shields.io/pypi/v/numerapi.svg)](https://pypi.python.org/pypi/numerapi)
[![Docs](https://readthedocs.org/projects/numerapi/badge/?version=stable)](http://numerapi.readthedocs.io/en/stable/?badge=stable)
[![Requirements Status](https://requires.io/github/uuazed/numerapi/requirements.svg?branch=master)](https://requires.io/github/uuazed/numerapi/requirements/?branch=master)

# Numerai Python API
Automatically download and upload data for the Numerai machine learning
competition.

This library is a Python client to the Numerai API. The interface is programmed
in Python and allows downloading the training data, uploading predictions, and
accessing user, submission and competitions information.

If you encounter a problem or have suggestions, feel free to open an issue.

# Installation
`pip install --upgrade numerapi`

# Usage

Numerapi can be used as a regular, importable Python module or from the command
line.

Some actions (like uploading predictions or staking) require a token to verify
that it is really you interacting with Numerai's API. These tokens consists of
a `public_id` and `secret_key`. Both can be obtained by login in to Numer.ai and
going to Account -> Custom API Keys. Tokens can be passed to the Python module
as parameters or you can be set via environment variables (`NUMERAI_PUBLIC_ID`
and `NUMERAI_SECRET_KEY`).

## Python module

Usage example:

    # some API calls do not require logging in
    napi = numerapi.NumerAPI(verbosity="info")
    # download current dataset
    napi.download_current_dataset(unzip=True)
    # get competitions
    all_competitions = napi.get_competitions()
    # get leaderboard for the current round
    leaderboard = napi.get_leaderboard()
    # leaderboard for a historic round
    leaderboard_67 = napi.get_leaderboard(round_num=67)
    # check if a new round has started
    if napi.check_new_round():
        print("new round has started wihtin the last 24hours!")
    else:
        print("no new round within the last 24 hours")

    # provide api tokens
    example_public_id = "somepublicid"
    example_secret_key = "somesecretkey"
    napi = NumerAPI(example_public_id, example_secret_key)

    # upload predictions
    submission_id = napi.upload_predictions("mypredictions.csv")
    # check submission status
    napi.submission_status()

## Command line interface

To get started with the cli interface, let's take a look at the help page:

    $ numerapi --help
    Usage: numerapi [OPTIONS] COMMAND [ARGS]...

      Wrapper around the Numerai API

    Options:
      --help  Show this message and exit.

    Commands:
      check_new_round         Check if a new round has started within the...
      competitions            Retrieves information about all competitions
      current_round           Get number of the current active round.
      dataset_url             Fetch url of the current dataset.
      download_dataset        Download dataset for the current active...
      leaderboard             Retrieves the leaderboard for the given...
      payments                List all your payments
      rankings                Get the overall rankings.
      stake                   Participate in the staking competition.
      stakes                  List all your stakes.
      staking_leaderboard     Retrieves the staking competition leaderboard...
      submission_filenames    Get filenames of your submissions
      submission_ids          Get dict with username->submission_id...
      submission_status       checks the submission status
      submission_successful   Check if the last submission passes...
      submit                  Upload predictions from file.
      tournament_name2number  Translate tournament name to tournament...
      tournament_number2name  Translate tournament number to tournament...
      tournaments             Get all active tournaments.
      transactions            List all your deposits and withdrawals.
      user                    Get all information about you!
      user_activities         Get user activities (works for all users!)
      version                 Installed numerapi version.

Each command has it's own help page, for example:

    $ numerapi submit --help
    Usage: numerapi submit [OPTIONS] PATH

      Upload predictions from file.

    Options:
      --tournament INTEGER  The ID of the tournament, defaults to 1
      --help                Show this message and exit.


# API Reference

Checkout the [detailed API docs](http://numerapi.readthedocs.io/en/latest/api/numerapi.html#module-numerapi.numerapi)
to learn about all available methods, parameters and returned values.
