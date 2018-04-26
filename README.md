[![Build Status](https://travis-ci.org/uuazed/numerapi.png)](https://travis-ci.org/uuazed/numerapi)
[![codecov](https://codecov.io/gh/uuazed/numerapi/branch/master/graph/badge.svg)](https://codecov.io/gh/uuazed/numerapi)
[![PyPI](https://img.shields.io/pypi/v/numerapi.svg)](https://pypi.python.org/pypi/numerapi)
[![Docs](https://readthedocs.org/projects/numerapi/badge/?version=stable)](http://numerapi.readthedocs.io/en/stable/?badge=stable)

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

Some actions (like uploading predictions or staking) require a token to verify
that it is really you interacting with Numerai's API. These tokens consists of
a `public_id` and `secret_key`. Both can be obtained by login in to Numer.ai and
going to Account -> Custom API Keys.


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

# API Reference

Checkout the [detailed API docs](http://numerapi.readthedocs.io/en/latest/api/numerapi.html#module-numerapi.numerapi)
to learn about all available methods, parameters and returned values.
