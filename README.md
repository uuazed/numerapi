[![Build Status](https://travis-ci.org/uuazed/numerapi.png)](https://travis-ci.org/uuazed/numerapi)
[![codecov](https://codecov.io/gh/uuazed/numerapi/branch/master/graph/badge.svg)](https://codecov.io/gh/uuazed/numerapi)
[![PyPI](https://img.shields.io/pypi/v/numerapi.svg)](https://pypi.python.org/pypi/numerapi)

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
See `example.py`.  You can run it as `./example.py`

Some actions (like uploading predictions or staking) requires a token to verify
that it is really you interacting with Numerai's API. These tokens consists of
a `public_id` and `secret_key`. Both can be obtained by login in to Numer.ai and
going to Account -> Custom API Keys.

# Documentation
## Layout
Parameters and return values are given with Python types. Dictionary keys are
given in quotes; other names to the left of colons are for reference
convenience only. In particular, `list`s of `dict`s have names for the `dict`s;
these names will not show up in the actual data, only the actual `dict` data
itself.

## `download_current_dataset`
### Parameters
* `dest_path` (`str`, optional, default: `.`): destination folder for the
  dataset
* `dest_filename` (`str`, optional, default: `numerai_dataset_<round number>.zip`)
* `unzip (`bool`, optional, default: `True`): indication of whether the
  training data should be unzipped
### Return Values
* `path` (`string`): location of the downloaded dataset

## `get_leaderboard`
retrieves the leaderboard for the given round
### Parameters
* `round_num` (`int`, optional, defaults to current round): The round you are interested in.
### Return Values
* `participants` (`list`): information about all competitors
  * `participants` (`dict`)
    * `"concordance"` (`dict`)
      * `"pending"` (`bool`)
      * `"value"` (`bool`)
    * `"originality"` (`dict`)
      * `"pending"` (`bool`)
      * `"value"` (`bool`)
    * `"consistency"` (`float`)
    * `"liveLogloss"` (`float` or `None`)
    * `"validationLogloss"` (`float`)
    * `"paymentGeneral"` (`dict` or `None`)
      * `"nmrAmount"` (`float`)
      * `"usdAmount"` (`float`)
    * `"paymentStaking"` (`dict` or `None`)
      * `"nmrAmount"` (`float`)
      * `"usdAmount"` (`float`)
    * `"submissionId"` (`str`)
    * `"totalPayments"` (`dict`)
      * `"nmrAmount"` (`float`)
      * `"usdAmount"` (`float`)
    * `"username"` (`str`)

## `get_staking_leaderboard`
retrieves the leaderboard of the staking competition for the given round
### Parameters
* `round_num` (`int`, optional, defaults to current round): The round you are interested in.
### Return Values
* `stakes` (`list`): information about all competitors
  * `participants` (`dict`)
    * `"username"` (`str`)
    * `"consistency"` (`float`)
    * `"liveLogloss"` (`float` or `None`)
    * `"validationLogloss"` (`float`)
    * `"stake"` (`dict`)
      * `"confidence"` (`str`)
      * `"insertedAt"` (`datetime`)
      * `"soc"` (`str`)
      * `"txHash"` (`str`)
      * `"value"` (`str`)

## `get_competitions`
### Return Values
* `all_competitions` (`list`): information about all competitions
  * `competition` (`dict`)
    * `"datasetId"` (`str`)
    * `"number"` (`int`)
    * `"openTime"` (`datetime`)
    * `"resolveTime"` (`datetime`)
    * `"resolvedGeneral"` (`bool`)
    * `"resolvedStaking"` (`bool`)

## `get_current_round`
### Return Values
* `number` (`int`): number of the current round

## `get_submission_ids`
get dict with username->submission_id mapping
### Return Values
* `submission_ids` (`dict`)
  * `"username"` (`str`)
  * `"submissionId"` (`str`): ID of submission

## `submission_status`
submission status of the given submission_id or the last submission done
within the same session.
### Parameters
* `submission_id` (`str`, optional, default: `None`):
### Return Values
* `status` (`dict`)
  * `"concordance"` (`dict`):
    * `"pending"` (`bool`)
    * `"value"` (`bool`): whether the submission is concordant
  * `"originality"` (`dict`)
    * `"pending"` (`bool`)
    * `"value"` (`bool`): whether the submission is original
  * `"consistency"` (`float`): consistency of the submission
  * `"validation_logloss"` (`float`): amount of logloss for the submission

## `upload_predictions`
### Parameters
* `file_path` (`str`): path to CSV of predictions (e.g. `"path/to/file/prediction.csv"`)
### Return Values
* `submission_id`: ID of submission

## `get_user`
### Return Values
* `user` (`dict`)
  * `"apiTokens"` (`list`)
    * `token` (`dict`)
      * `"name"` (`str`)
      * `"public_id"` (`str`)
      * `"scopes"` (`list`)
        * `scope` (`str`)
  * `"assignedEthAddress"` (`str`)
  * `"availableNmr"` (`float`)
  * `"availableUsd"` (`float`)
  * `"banned"` (`bool`)
  * `"email"` (`str`)
  * `"id"` (`str`)
  * `"insertedAt"` (`datetime`)
  * `"mfaEnabled"` (`bool`)
  * `"status"` (`str`)
  * `"username"` (`str`)

## `get_payments`
### Return Values
* `payments` (`list`)
  * `payment` (`dict`)
    * `"nmrAmount"` (`str`)
    * `"usdAmount"` (`str`)
    * `"tournament"` (`str`)
    * `"round"` (`dict`)
      * `"number"` (`int`)
      * `"openTime"` (`datetime`)
      * `"resolveTime"` (`datetime`)
      * `"resolvedGeneral"` (`bool`)
      * `"resolvedStaking"` (`bool`)

## `get_transactions`
### Return Values
* `transactions` (`dict`)
  * `"nmrDeposits"` (`list`)
    * `nmrDeposit` (`dict`)
      * `"from"` (`str`)
      * `"id"` (`str`)
      * `"posted"` (`bool`)
      * `"status"` (`str`)
      * `"to"` (`str`)
      * `"txHash"` (`str`)
      * `"value"` (`str`)
  * `"nmrWithdrawals"` (`list`)
    * `nmrWithdrawal` (`dict`)
      * `"from"` (`str`)
      * `"id"` (`str`)
      * `"posted"` (`bool`)
      * `"status"` (`str`)
      * `"to"` (`str`)
      * `"txHash"` (`str`)
      * `"value"` (`str`)
  * `"usdWithdrawals"` (`list`)
    * `usdWithdrawal` (`dict`)
      * `"confirmTime"` (`datetime` or `None`)
      * `"ethAmount"` (`str`)
      * `"from"` (`str`)
      * `"posted"` (`bool`)
      * `"sendTime"` (`datetime`)
      * `"status"` (`str`)
      * `"to"` (`str`)
      * `"txHash"` (`str`)
      * `"usdAmount"` (`str`)

## `stake`
participate in the staking competition
### Parameters
* `confidence` (`float`)
* `value` (`float`): the amount of NMR you want to stake
### Return Values
* `stake` (`dict`)
  * `"id"` (`str`)
  * `"status"` (`str`)
  * `"txHash"` (`str`)
  * `"value"` (`str`)

## `get_stakes`
### Return Values
* `stakes` (`list`)
  * `stake` (`dict`)
    * `"confidence"` (`str`)
    * `"roundNumber"` (`int`)
    * `"soc"` (`float`)
    * `"insertedAt"` (`str (datetime)`)
    * `"staker"` (`str`): NMR adress used for staking
    * `"status"` (`str`)
    * `"txHash"` (`str`)
    * `"value"` (`str`)

## `raw_query`
This function allows to build your own queries and fetch results from
Numerai's GraphQL API. Checkout
https://medium.com/numerai/getting-started-with-numerais-new-tournament-api-77396e895e72
for an introduction.
### Parameters
* `query` (`str`)
* `variables` (`dict`, optional)
* `authorization` (`bool`, optional, default: `False`): indicates if a token is required
### Return Values
* `data` (`dict`)
