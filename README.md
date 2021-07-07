[![Build Status](https://travis-ci.com/uuazed/numerapi.png)](https://travis-ci.com/uuazed/numerapi)
[![codecov](https://codecov.io/gh/uuazed/numerapi/branch/master/graph/badge.svg)](https://codecov.io/gh/uuazed/numerapi)
[![PyPI](https://img.shields.io/pypi/v/numerapi.svg)](https://pypi.python.org/pypi/numerapi)
[![Docs](https://readthedocs.org/projects/numerapi/badge/?version=stable)](http://numerapi.readthedocs.io/en/stable/?badge=stable)
[![Requirements Status](https://requires.io/github/uuazed/numerapi/requirements.svg?branch=master)](https://requires.io/github/uuazed/numerapi/requirements/?branch=master)

# Numerai Python API
Automatically download and upload data for the Numerai machine learning
competition.

This library is a Python client to the Numerai API. The interface is programmed
in Python and allows downloading the training data, uploading predictions, and
accessing user, submission and competitions information. It works for both, the
main competition and the newer Numerai Signals competition.

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

### Usage example - main competition

    import numerapi
    # some API calls do not require logging in
    napi = numerapi.NumerAPI(verbosity="info")
    # download current dataset
    napi.download_current_dataset(unzip=True)
    # get competitions
    all_competitions = napi.get_competitions()
    # get current leaderboard
    leaderboard = napi.get_leaderboard()
    # check if a new round has started
    if napi.check_new_round():
        print("new round has started within the last 24hours!")
    else:
        print("no new round within the last 24 hours")

    # provide api tokens
    example_public_id = "somepublicid"
    example_secret_key = "somesecretkey"
    napi = numerapi.NumerAPI(example_public_id, example_secret_key)

    # upload predictions
    model_id = napi.get_models()['uuazed']
    napi.upload_predictions("preds.csv", model_id=model_id)
    # check submission status
    napi.submission_status(model_id)
    # increase your stake by 1.2 NMR
    napi.stake_increase(1.2)

    # convert results to a pandas dataframe
    import pandas as pd
    df = pd.DataFrame(napi.daily_user_performances("uuazed"))


### Usage example - Numerai Signals

    import numerapi

    napi = numerapi.SignalsAPI()
    # get current leaderboard
    leaderboard = napi.get_leaderboard()

    # setup API with api tokens
    example_public_id = "somepublicid"
    example_secret_key = "somesecretkey"
    napi = numerapi.SignalsAPI(example_public_id, example_secret_key)

    # upload predictions
    model_id = napi.get_models()['uuazed']
    napi.upload_predictions("preds.csv", model_id=model_id)

    # get submission status and invalid tickers
    status = napi.submission_status(model_id)
    invalid_tickers = status['invalidTickers']

    # get daily performance as pandas dataframe
    import pandas as pd
    df = pd.DataFrame(napi.daily_user_performances("uuazed"))


## Command line interface

To get started with the cli interface, let's take a look at the help page:

    $ numerapi --help
    Usage: numerapi [OPTIONS] COMMAND [ARGS]...

      Wrapper around the Numerai API

    Options:
      --help  Show this message and exit.

    Commands:
      account                         Get all information about your account!
      check-new-round                 Check if a new round has started within...
      competitions                    Retrieves information about all...
      current-round                   Get number of the current active round.
      daily-submissions-performances  Fetch daily performance of a user's...
      daily-user-performances         Fetch daily performance of a user.
      dataset-url                     Fetch url of the current dataset.
      download-dataset                Download dataset for the current active...
      leaderboard                     Get the leaderboard.
      models                          Get map of account models!
      profile                         Fetch the public profile of a user.
      stake-decrease                  Decrease your stake by `value` NMR.
      stake-drain                     Completely remove your stake.
      stake-get                       Get stake value of a user.
      stake-increase                  Increase your stake by `value` NMR.
      stakes                          List all your stakes.
      submission-filenames            Get filenames of your submissions
      submission-status               checks the submission status
      submit                          Upload predictions from file.
      transactions                    List all your deposits and withdrawals.
      user                            Get all information about you! DEPRECATED...
      version                         Installed numerapi version.


Each command has it's own help page, for example:

    $ numerapi submit --help
    Usage: numerapi submit [OPTIONS] PATH

      Upload predictions from file.

    Options:
      --tournament INTEGER  The ID of the tournament, defaults to 1
      --model_id TEXT       An account model UUID (required for accounts with
                            multiple models

      --help                Show this message and exit.


# API Reference

Checkout the [detailed API docs](http://numerapi.readthedocs.io/en/latest/api/numerapi.html#module-numerapi.numerapi)
to learn about all available methods, parameters and returned values.
